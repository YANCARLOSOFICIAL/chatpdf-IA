
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import hashlib
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import PyPDF2
import requests
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()

import json
from pathlib import Path

# Simple JSON metadata store for folders, document metadata (favorites, tags, folder assignments)
METADATA_PATH = Path(__file__).resolve().parent / 'metadata_store.json'

def load_metadata():
    if not METADATA_PATH.exists():
        return {"folders": [], "documents": {}}
    # Try multiple encodings to avoid decode errors from files saved on Windows
    try:
        with open(METADATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        try:
            with open(METADATA_PATH, 'r', encoding='latin-1') as f:
                return json.load(f)
        except Exception:
            # Fallback: read bytes and replace invalid chars
            with open(METADATA_PATH, 'rb') as f:
                text = f.read().decode('utf-8', errors='replace')
                return json.loads(text)

def save_metadata(data):
    with open(METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de la base de datos
PG_CONN = os.getenv("PG_CONN", "dbname=chatpdf user=postgres password=postgres host=localhost")
conn = psycopg2.connect(PG_CONN)
register_vector(conn)

# Ensure folders table and folder_id column exist
def init_db_schema():
    with conn.cursor() as cur:
        # create folders table if not exists
        cur.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        # add folder_id column to pdfs if it doesn't exist
        try:
            cur.execute("ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS folder_id INTEGER REFERENCES folders(id)")
        except Exception:
            # older Postgres versions might not support IF NOT EXISTS; try simple add and ignore error
            try:
                cur.execute("ALTER TABLE pdfs ADD COLUMN folder_id INTEGER REFERENCES folders(id)")
            except Exception:
                pass
        # create pdf_metadata table for favorites/tags/uploaded_at
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pdf_metadata (
                pdf_id INTEGER PRIMARY KEY REFERENCES pdfs(id) ON DELETE CASCADE,
                favorite BOOLEAN DEFAULT FALSE,
                tags JSONB DEFAULT '[]'::jsonb,
                uploaded_at TIMESTAMPTZ
            )
        ''')
        # add hash column to pdfs for duplicate detection
        try:
            cur.execute("ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS hash TEXT UNIQUE")
        except Exception:
            try:
                cur.execute("ALTER TABLE pdfs ADD COLUMN hash TEXT")
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS pdfs_hash_idx ON pdfs(hash)")
            except Exception:
                pass
        conn.commit()

init_db_schema()

# DB metadata helpers
def get_pdf_metadata_from_db(pdf_id):
    with conn.cursor() as cur:
        cur.execute("SELECT favorite, tags::text, uploaded_at FROM pdf_metadata WHERE pdf_id = %s", (pdf_id,))
        r = cur.fetchone()
        if not r:
            return {}
        favorite, tags_text, uploaded_at = r
        try:
            tags = json.loads(tags_text)
        except Exception:
            tags = []
        return {'favorite': bool(favorite), 'tags': tags, 'uploadedAt': uploaded_at}

def upsert_pdf_metadata_db(pdf_id, meta):
    with conn.cursor() as cur:
        # ensure uploaded_at is set if provided
        fav = meta.get('favorite')
        tags = json.dumps(meta.get('tags', [])) if 'tags' in meta else None
        uploaded = meta.get('uploadedAt')
        # try update
        cur.execute("SELECT 1 FROM pdf_metadata WHERE pdf_id = %s", (pdf_id,))
        exists = cur.fetchone()
        if exists:
            if fav is not None:
                cur.execute("UPDATE pdf_metadata SET favorite = %s WHERE pdf_id = %s", (fav, pdf_id))
            if tags is not None:
                cur.execute("UPDATE pdf_metadata SET tags = %s::jsonb WHERE pdf_id = %s", (tags, pdf_id))
            if uploaded:
                cur.execute("UPDATE pdf_metadata SET uploaded_at = %s WHERE pdf_id = %s", (uploaded, pdf_id))
        else:
            cur.execute("INSERT INTO pdf_metadata (pdf_id, favorite, tags, uploaded_at) VALUES (%s, %s, %s::jsonb, %s)", (pdf_id, fav if fav is not None else False, tags if tags is not None else '[]', uploaded))
        conn.commit()

from datetime import datetime

# Path to write a simple migration result summary (used by status endpoint)
MIGRATION_RESULT_PATH = Path(__file__).resolve().parent / 'migration_result.json'


def run_migration():
    """Run migration from metadata_store.json into DB and return a summary dict.
    This function will be used both at startup (when MIGRATE_METADATA=true) and
    via the POST /migration/run endpoint.
    """
    summary = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'folders_processed': 0,
        'folders_inserted': 0,
        'documents_processed': 0,
        'pdfs_folder_updated': 0,
        'pdf_metadata_upserted': 0,
        'notes': []
    }

    if not METADATA_PATH.exists():
        summary['notes'].append('metadata_store.json not found; nothing to migrate')
        # write result file
        try:
            with open(MIGRATION_RESULT_PATH, 'w', encoding='utf-8') as rf:
                json.dump(summary, rf, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return summary

    data = load_metadata()
    docs = data.get('documents', {})
    folders = data.get('folders', [])

    with conn.cursor() as cur:
        # insert folders if not present
        for f in folders:
            summary['folders_processed'] += 1
            try:
                # try to insert with provided id (ON CONFLICT DO NOTHING)
                cur.execute("INSERT INTO folders (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING", (int(f.get('id')), f.get('name')))
                if cur.rowcount:
                    summary['folders_inserted'] += 1
                else:
                    # If no row affected, try a plain insert (fallback)
                    pass
            except Exception:
                try:
                    cur.execute("INSERT INTO folders (name) VALUES (%s)", (f.get('name'),))
                    if cur.rowcount:
                        summary['folders_inserted'] += 1
                except Exception:
                    summary['notes'].append(f"failed to insert folder: {f}")
        conn.commit()

        # migrate each document metadata
        for pdf_id_str, meta in docs.items():
            try:
                pid = int(pdf_id_str)
            except Exception:
                continue
            summary['documents_processed'] += 1
            # folderId
            folderId = meta.get('folderId')
            if folderId:
                try:
                    cur.execute("UPDATE pdfs SET folder_id = %s WHERE id = %s", (folderId, pid))
                    summary['pdfs_folder_updated'] += cur.rowcount if cur.rowcount else 0
                except Exception:
                    summary['notes'].append(f"failed to update folder for pdf {pid}")
            # other metadata: call upsert (we count it as processed)
            try:
                upsert_pdf_metadata_db(pid, {'favorite': meta.get('favorite', False), 'tags': meta.get('tags', []), 'uploadedAt': meta.get('uploadedAt')})
                summary['pdf_metadata_upserted'] += 1
            except Exception:
                summary['notes'].append(f"failed to upsert metadata for pdf {pid}")
        conn.commit()

    # write summary to file for status endpoint
    try:
        with open(MIGRATION_RESULT_PATH, 'w', encoding='utf-8') as rf:
            json.dump(summary, rf, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return summary


# Optional one-time migration from metadata_store.json into DB at startup
def migrate_metadata_to_db():
    if os.getenv('MIGRATE_METADATA', 'false').lower() != 'true':
        return
    # run the more featureful migration that produces a summary
    run_migration()


migrate_metadata_to_db()

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def get_ollama_embedding(text, model="embeddinggemma"):
    response = requests.post(f"http://localhost:11434/api/embeddings", json={"model": model, "prompt": text})
    return response.json()["embedding"]

def get_qwen_embedding(text, api_key):
    url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "text-embedding-v2", "input": text}
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    if "output" not in data:
        print("Qwen API error response:", data)
        raise Exception(f"Qwen API error: {data}")
    return data["output"]["embeddings"][0]["embedding"]

# OpenAI Embedding
def get_openai_embedding(text, api_key, model="text-embedding-3-large"):
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": text, "dimensions": 1536}
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    if "data" not in data:
        print("OpenAI API error response:", data)
        raise Exception(f"OpenAI API error: {data}")
    embedding = data["data"][0]["embedding"]
    print(f"OpenAI embedding dimensions: {len(embedding)}")
    return embedding
def save_embedding(pdf_id, chunk, embedding, embedding_type):
    table_name = "pdf_chunks_ollama" if embedding_type == "ollama" else "pdf_chunks_openai"
    with conn.cursor() as cur:
        cur.execute(f"INSERT INTO {table_name} (pdf_id, chunk, embedding) VALUES (%s, %s, %s)", (pdf_id, chunk, embedding))
        conn.commit()

def create_pdf_entry(filename, embedding_type):
    # kept for backward compatibility
    return create_pdf_entry_with_hash(filename, embedding_type, None)


def create_pdf_entry_with_hash(filename, embedding_type, file_hash=None):
    with conn.cursor() as cur:
        if file_hash:
            cur.execute("INSERT INTO pdfs (filename, embedding_type, hash) VALUES (%s, %s, %s) RETURNING id", (filename, embedding_type, file_hash))
        else:
            cur.execute("INSERT INTO pdfs (filename, embedding_type) VALUES (%s, %s) RETURNING id", (filename, embedding_type))
        pdf_id = cur.fetchone()[0]
        conn.commit()
    return pdf_id

def get_pdf_embedding_type(pdf_id):
    with conn.cursor() as cur:
        cur.execute("SELECT embedding_type FROM pdfs WHERE id = %s", (pdf_id,))
        result = cur.fetchone()
        return result[0] if result else None

def search_similar_chunks(pdf_id, query_embedding, embedding_type, top_k=3):
    table_name = "pdf_chunks_ollama" if embedding_type == "ollama" else "pdf_chunks_openai"
    with conn.cursor() as cur:
        # Convertir la lista de Python a string de vector de PostgreSQL
        vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
        cur.execute(f"""
            SELECT chunk FROM {table_name}
            WHERE pdf_id = %s
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, (pdf_id, vector_str, top_k))
        return [row[0] for row in cur.fetchall()]

@app.post("/upload_pdf/")
async def upload_pdf(pdf: UploadFile = File(...), embedding_type: str = Form(...), file_hash: str = Form(None)):
    # Read bytes and compute hash if not provided
    file_bytes = await pdf.read()
    computed_hash = hashlib.sha256(file_bytes).hexdigest()
    file_hash = file_hash or computed_hash

    # Server-side duplicate check by hash (preferred)
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pdfs WHERE hash = %s", (file_hash,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"PDF with same content already exists")

    # Fallback: if hash column wasn't populated historically, also check filename
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pdfs WHERE filename = %s", (pdf.filename,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"PDF with filename '{pdf.filename}' already exists")

    # Heuristic: some existing PDFs might store a hash computed from extracted
    # chunks (or have NULL). Compare the incoming binary file hash against a
    # chunk-derived fingerprint for existing PDFs. If matched, update the
    # existing row to the binary file hash (so future checks are direct) and
    # reject the upload.
    with conn.cursor() as cur_all:
        cur_all.execute("SELECT id, hash FROM pdfs")
        all_rows = cur_all.fetchall()

    for existing_id, stored_hash in all_rows:
        # If stored_hash equals the incoming binary hash, we already handled it
        if stored_hash == file_hash:
            raise HTTPException(status_code=409, detail=f"PDF with same content already exists")

        # Compute chunk-based fingerprint and compare to incoming binary hash
        chunks = []
        with conn.cursor() as cur2:
            try:
                cur2.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (existing_id,))
                chunks += [r[0] for r in cur2.fetchall()]
            except Exception:
                pass
            try:
                cur2.execute("SELECT chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (existing_id,))
                chunks += [r[0] for r in cur2.fetchall()]
            except Exception:
                pass

        if not chunks:
            continue

        combined = ''.join([c or '' for c in chunks])
        chunk_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        if chunk_hash == file_hash:
            # Update the stored hash to the binary file hash for faster future checks
            with conn.cursor() as cur3:
                cur3.execute("UPDATE pdfs SET hash = %s WHERE id = %s", (file_hash, existing_id))
                conn.commit()
            raise HTTPException(status_code=409, detail=f"PDF with same content already exists (matched by stored text chunks)")

    # write temp file for text extraction
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    text = extract_text_from_pdf(tmp_path)
    os.remove(tmp_path)

    # Dividir texto en chunks simples
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    pdf_id = create_pdf_entry_with_hash(pdf.filename, embedding_type, file_hash)

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    for chunk in chunks:
        print("Chunk type:", type(chunk), "Chunk length:", len(chunk))
        if embedding_type == "ollama":
            embedding = get_ollama_embedding(chunk)
        elif embedding_type == "openai":
            embedding = get_openai_embedding(chunk, openai_api_key)
        else:
            raise Exception("Tipo de embedding no soportado")
        save_embedding(pdf_id, chunk, embedding, embedding_type)

    return {"filename": pdf.filename, "embedding_type": embedding_type, "pdf_id": pdf_id}


@app.post("/chat/")
async def chat(query: str = Form(...), pdf_id: int = Form(...), embedding_type: str = Form("ollama")):
    # Verificar que el tipo de embedding coincida con el del PDF
    pdf_embedding_type = get_pdf_embedding_type(pdf_id)
    if pdf_embedding_type and pdf_embedding_type != embedding_type:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"⚠️ Incompatibilidad de modelos: El PDF se subió con '{pdf_embedding_type.upper()}', pero intentas usar '{embedding_type.upper()}'. Por favor, sube el PDF nuevamente con el modelo correcto."
        )

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if embedding_type == "ollama":
        query_embedding = get_ollama_embedding(query)
    elif embedding_type == "openai":
        query_embedding = get_openai_embedding(query, openai_api_key)
    else:
        raise Exception("Tipo de embedding no soportado")
    chunks = search_similar_chunks(pdf_id, query_embedding, embedding_type)
    context = "\n".join(chunks)

    # Generar respuesta en lenguaje natural usando el modelo seleccionado
    if embedding_type == "ollama":
        # Usar Ollama para generar respuesta
        ollama_model = "llama2:7b-chat"  # Usar el modelo conversacional instalado
        prompt = f"Responde en lenguaje natural a la pregunta: '{query}' usando el siguiente contexto extraído del documento:\n{context}"
        ollama_response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": ollama_model, "prompt": prompt},
            stream=True
        )
        # Procesar respuesta streaming línea por línea
        fragments = []
        for line in ollama_response.iter_lines():
            if line:
                try:
                    data = line.decode("utf-8")
                    import json
                    obj = json.loads(data)
                    if "response" in obj:
                        fragments.append(obj["response"])
                except Exception:
                    continue
        answer = "".join(fragments).strip()
        if not answer:
            answer = "No se pudo generar respuesta."
    elif embedding_type == "openai":
        # Usar OpenAI para generar respuesta
        openai_model = "gpt-3.5-turbo"  # Cambia por el modelo que prefieras
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
        messages = [
            {"role": "system", "content": "Responde en lenguaje natural y de forma explicativa usando el contexto proporcionado."},
            {"role": "user", "content": f"Pregunta: {query}\nContexto: {context}"}
        ]
        payload = {"model": openai_model, "messages": messages, "max_tokens": 256}
        openai_response = requests.post(url, json=payload, headers=headers)
        answer = openai_response.json().get("choices", [{}])[0].get("message", {}).get("content", "No se pudo generar respuesta.")
    else:
        answer = "No se pudo generar respuesta."

    return {"response": answer}


# --- Metadata endpoints for frontend sync (folders, favorites, tags) ---
@app.get("/metadata/")
async def get_metadata():
    # Aggregate folders and documents metadata from DB
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM folders ORDER BY id DESC")
        folders = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
        # fetch pdf ids
        cur.execute("SELECT id FROM pdfs")
        pdf_rows = cur.fetchall()
    docs = {}
    for (pid,) in pdf_rows:
        meta = get_pdf_metadata_from_db(pid)
        if meta:
            docs[str(pid)] = meta
        else:
            docs[str(pid)] = {}
    return {'folders': folders, 'documents': docs}


@app.post('/migration/run')
async def migration_run():
    """Force migration run and return summary JSON."""
    summary = run_migration()
    return summary


@app.get('/migration/status')
async def migration_status():
    """Return last migration result summary if present, otherwise a quick DB check."""
    if MIGRATION_RESULT_PATH.exists():
        try:
            with open(MIGRATION_RESULT_PATH, 'r', encoding='utf-8') as rf:
                data = json.load(rf)
                return {'status': 'ok', 'result': data}
        except Exception:
            pass

    # Fallback: quick check of counts
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM pdfs')
        pdfs_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM pdf_metadata')
        meta_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM folders')
        folders_count = cur.fetchone()[0]

    return {'status': 'ok', 'pdfs': pdfs_count, 'pdf_metadata': meta_count, 'folders': folders_count}


@app.post("/folders/")
async def create_folder(name: str = Form(...)):
    # create folder in DB
    with conn.cursor() as cur:
        cur.execute("INSERT INTO folders (name) VALUES (%s) RETURNING id, name", (name,))
        row = cur.fetchone()
        conn.commit()
    folder = {"id": row[0], "name": row[1]}
    return folder


@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int):
    # delete folder from DB and unset folder_id on pdfs
    with conn.cursor() as cur:
        cur.execute("UPDATE pdfs SET folder_id = NULL WHERE folder_id = %s", (folder_id,))
        cur.execute("DELETE FROM folders WHERE id = %s", (folder_id,))
        conn.commit()
    return {"ok": True}


@app.get("/documents/{pdf_id}/metadata")
async def get_document_metadata(pdf_id: int):
    # Return metadata for a single PDF from DB
    with conn.cursor() as cur:
        cur.execute("SELECT folder_id FROM pdfs WHERE id = %s", (pdf_id,))
        r = cur.fetchone()
        folder_val = r[0] if r else None
    meta = get_pdf_metadata_from_db(pdf_id)
    result = meta or {}
    result['folderId'] = folder_val
    return result


@app.post("/documents/{pdf_id}/metadata")
async def set_document_metadata(pdf_id: int, metadata: str = Form(...)):
    # metadata: JSON string with keys like favorite, tags, folderId
    try:
        meta_obj = json.loads(metadata)
    except Exception:
        meta_obj = {}
    # If folderId present, update DB
    if 'folderId' in meta_obj:
        folder_id = meta_obj.get('folderId')
        with conn.cursor() as cur:
            cur.execute("UPDATE pdfs SET folder_id = %s WHERE id = %s", (folder_id, pdf_id))
            conn.commit()

    # Store other metadata in DB table pdf_metadata
    meta_to_store = {k: v for k, v in meta_obj.items() if k != 'folderId'}
    if meta_to_store:
        upsert_pdf_metadata_db(pdf_id, meta_to_store)

    # Return merged view
    with conn.cursor() as cur:
        cur.execute("SELECT folder_id FROM pdfs WHERE id = %s", (pdf_id,))
        r = cur.fetchone()
        folder_val = r[0] if r else None
    meta = get_pdf_metadata_from_db(pdf_id)
    result = meta or {}
    result['folderId'] = folder_val
    return result


@app.get("/pdfs/")
async def list_pdfs(folder_id: int = None, name: str = None, hash: str = None):
    # Fetch PDFs from database with optional folder_id or exact name filter
    with conn.cursor() as cur:
        if hash:
            # exact hash match
            cur.execute("SELECT id, filename, embedding_type, folder_id, hash FROM pdfs WHERE hash = %s ORDER BY id DESC", (hash,))
        elif name:
            # exact filename match (case-insensitive)
            cur.execute("SELECT id, filename, embedding_type, folder_id, hash FROM pdfs WHERE LOWER(filename) = LOWER(%s) ORDER BY id DESC", (name,))
        elif folder_id is None:
            cur.execute("SELECT id, filename, embedding_type, folder_id, hash FROM pdfs ORDER BY id DESC")
        else:
            cur.execute("SELECT id, filename, embedding_type, folder_id, hash FROM pdfs WHERE folder_id = %s ORDER BY id DESC", (folder_id,))
        rows = cur.fetchall()

    results = []
    for r in rows:
        pdf_id, filename, embedding_type, folder_val, file_hash = r
        meta = get_pdf_metadata_from_db(pdf_id)
        entry = {
            'id': pdf_id,
            'name': filename,
            'embeddingType': embedding_type,
            'folderId': folder_val,
            'hash': file_hash,
            'favorite': meta.get('favorite', False),
            'tags': meta.get('tags', []),
            'uploadedAt': meta.get('uploadedAt')
        }
        results.append(entry)

    return {'pdfs': results}


@app.get('/folders/')
async def list_folders():
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM folders ORDER BY id DESC")
        rows = cur.fetchall()
    folders = [{'id': r[0], 'name': r[1]} for r in rows]
    return {'folders': folders}


@app.post('/admin/fill_hashes/')
async def admin_fill_hashes():
    """Admin endpoint: compute SHA-256 fingerprints for PDFs with NULL hash
    by concatenating stored chunks (openai/ollama tables) and updating the pdfs table.
    Returns a summary of updated rows.
    """
    updated = []
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pdfs WHERE hash IS NULL")
        rows = cur.fetchall()

    for (pdf_id,) in rows:
        chunks = []
        with conn.cursor() as cur2:
            try:
                cur2.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (pdf_id,))
                chunks += [r[0] for r in cur2.fetchall()]
            except Exception:
                pass
            try:
                cur2.execute("SELECT chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (pdf_id,))
                chunks += [r[0] for r in cur2.fetchall()]
            except Exception:
                pass

        if not chunks:
            continue

        combined = ''.join([c or '' for c in chunks])
        file_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        with conn.cursor() as cur3:
            cur3.execute("UPDATE pdfs SET hash = %s WHERE id = %s", (file_hash, pdf_id))
            conn.commit()
        updated.append({'id': pdf_id, 'hash': file_hash})

    return {'updated': updated, 'count': len(updated)}
