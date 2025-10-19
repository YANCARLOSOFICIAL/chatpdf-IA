
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import hashlib
import logging
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

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        # create pdf_images table for storing extracted images
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pdf_images (
                id SERIAL PRIMARY KEY,
                pdf_id INTEGER REFERENCES pdfs(id) ON DELETE CASCADE,
                image_path TEXT NOT NULL,
                page_number INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        # Ensure caption column exists for storing per-image captions
        try:
            cur.execute("ALTER TABLE pdf_images ADD COLUMN IF NOT EXISTS caption TEXT")
        except Exception:
            try:
                cur.execute("ALTER TABLE pdf_images ADD COLUMN caption TEXT")
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
    """
    Extract text from PDF. Try PyPDF2 first; if extracted text is very small,
    fall back to OCR using pdf2image + pytesseract to handle image-based PDFs
    (scanned documents, math expressions embedded as images, etc.). We also
    attempt table extraction as a future enhancement (Camelot/Tabula), but
    that requires system dependencies and is optional.
    """
    text = ""
    # Primary extraction using PyPDF2
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    except Exception:
        text = ""

    # If little or no text extracted, try OCR on each page image
    if not text or len(text.strip()) < 50:
        try:
            from pdf2image import convert_from_path
            import pytesseract
            images = convert_from_path(file_path, dpi=200)
            ocr_text_parts = []
            for img in images:
                try:
                    ocr_text_parts.append(pytesseract.image_to_string(img, lang='eng'))
                except Exception:
                    # try without specifying lang
                    ocr_text_parts.append(pytesseract.image_to_string(img))
            ocr_text = "\n".join(ocr_text_parts)
            if ocr_text and len(ocr_text.strip()) > len(text):
                text = ocr_text
        except Exception:
            # pdf2image/pytesseract not available or failed — keep whatever text we have
            pass

    # NOTE: Table extraction with Camelot or Tabula could be integrated here
    # to parse tables into text (CSV/TSV) and append to `text`. Camelot needs
    # system dependencies (ghostscript, opencv) so we leave it as optional.

    return text

def get_ollama_embedding(text, model="embeddinggemma:latest"):
    """Call the local Ollama-compatible server but prefer Qwen embedding model
    names present in the environment. The system lists `embeddinggemma:latest`
    as available; if Qwen embedding model is desired, set the model argument
    accordingly when calling this function.
    """
    response = requests.post(f"http://localhost:11434/api/embeddings", json={"model": model, "prompt": text})
    return response.json().get("embedding")


def generate_text_with_qwen(prompt, model="qwen3:4b"):
    """Synchronous generate call to local Ollama (Qwen). Returns plain text if available."""
    try:
        resp = requests.post("http://localhost:11434/api/generate", json={"model": model, "prompt": prompt})
        if resp.ok:
            data = resp.json()
            # Ollama generate responses commonly include 'response' field
            return data.get('response') or data.get('text') or ''
    except Exception:
        pass
    return ''


def extract_images_from_pdf(file_path, pdf_id=None):
    """Extract page images from a PDF using pdf2image (if available).
    If pdf_id is provided, saves images permanently in uploads/images/{pdf_id}/ directory.
    Returns a list of tuples: [(image_path, page_number), ...]
    """
    try:
        from pdf2image import convert_from_path
    except Exception as e:
        logger.warning("pdf2image not available: %s", e)
        return []
    images = []
    try:
        logger.info("Extracting images from PDF: %s", file_path)
        pil_images = convert_from_path(file_path, dpi=200)
        logger.info("Extracted %d page images", len(pil_images))
        
        # Determine where to save images
        if pdf_id:
            # Permanent storage in uploads/images/{pdf_id}/
            base_dir = Path(__file__).resolve().parent / 'uploads' / 'images' / str(pdf_id)
            base_dir.mkdir(parents=True, exist_ok=True)
            delete_after = False
        else:
            # Temporary storage (legacy behavior)
            base_dir = Path(tempfile.gettempdir())
            delete_after = True
        
        for i, img in enumerate(pil_images):
            if pdf_id:
                img_path = base_dir / f"page_{i+1}.png"
                img.save(str(img_path), format='PNG')
                images.append((str(img_path), i+1))  # Return tuple with page number
                logger.info("Saved page %d image permanently to: %s", i+1, img_path)
            else:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_page_{i}.png")
                img.save(tmp.name, format='PNG')
                images.append((tmp.name, i+1))
                logger.info("Saved page %d image to temp: %s", i+1, tmp.name)
    except Exception as e:
        logger.exception("Failed to extract images from PDF: %s", e)
        return []
    return images


def ocr_image_file(path):
    try:
        import pytesseract
        from PIL import Image
        # Configure Tesseract path for Windows
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        logger.info("Running OCR on image: %s", path)
        result = pytesseract.image_to_string(Image.open(path)) or ''
        logger.info("OCR result length: %d chars", len(result))
        return result
    except Exception as e:
        # Log as warning instead of exception to reduce noise
        logger.warning("OCR unavailable or failed for image %s: %s", path, str(e))
        return ''


def generate_image_with_qwen(image_path, prompt, model="qwen2.5vl:latest"):
    """Send an image to a local Ollama vision-capable model. Returns the generated text.
    Tries both /api/chat (preferred for vision) and /api/generate as fallback.
    """
    try:
        import base64
        logger.info("Generating caption for image: %s with model: %s", image_path, model)
        with open(image_path, 'rb') as f:
            b = f.read()
        b64 = base64.b64encode(b).decode('ascii')
        logger.info("Image encoded to base64, length: %d chars", len(b64))
        
        # Try /api/chat endpoint first (better for vision models in newer Ollama)
        try:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [b64]
                    }
                ],
                "stream": False
            }
            resp = requests.post("http://localhost:11434/api/chat", 
                               json=payload,
                               timeout=30)
            logger.info("Ollama /api/chat response status: %d", resp.status_code)
            if resp.ok:
                data = resp.json()
                result = data.get('message', {}).get('content', '') or data.get('response', '')
                if result:
                    logger.info("Caption generated via /api/chat, length: %d chars", len(result))
                    return result
            else:
                logger.warning("Ollama /api/chat failed: %s", resp.text[:500])
        except Exception as e:
            logger.warning("Failed /api/chat, trying fallback: %s", e)
        
        # Fallback: try /api/generate with markdown image tag
        combined_prompt = f"![image](data:image/png;base64,{b64})\n\n{prompt}"
        resp = requests.post("http://localhost:11434/api/generate", 
                           json={"model": model, "prompt": combined_prompt, "stream": False},
                           timeout=30)
        logger.info("Ollama /api/generate response status: %d", resp.status_code)
        if resp.ok:
            data = resp.json()
            result = data.get('response') or data.get('text') or ''
            logger.info("Caption generated via /api/generate, length: %d chars", len(result))
            return result
        else:
            logger.warning("Ollama /api/generate also failed: %s", resp.text[:500])
            
    except Exception as e:
        logger.exception("Failed to generate image caption: %s", e)
        return ''
    return ''


def generate_image_with_openai(image_path, prompt, openai_api_key, model="gpt-4o-mini"):
    """Generate a caption/analysis for an image using OpenAI chat endpoint by embedding
    the image as a data URI in a markdown image tag inside the user message. Falls back
    cleanly on errors and returns empty string on failure.
    """
    try:
        import base64
        from PIL import Image
        from io import BytesIO

        # Load and normalize image
        img = Image.open(image_path).convert('RGB')

        # Resize/compress thumbnail to reduce token cost
        max_dim = 512
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = BytesIO()
        img.save(buf, format='JPEG', quality=30, optimize=True)
        b = buf.getvalue()
        b64 = base64.b64encode(b).decode('ascii')

        # If still too large, skip OpenAI and let caller fallback
        if len(b64) > 100000:
            logger.warning("Compressed image base64 still large (%d chars). Skipping OpenAI caption.", len(b64))
            return ''

        user_content = f"![image](data:image/jpeg;base64,{b64})\n\n{prompt}"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an assistant that describes images succinctly and extracts any visible text, formulas or chart summaries."},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 300,
            "temperature": 0.0
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        text_snippet = ''
        try:
            text_snippet = resp.text[:2000]
        except Exception:
            text_snippet = '<unreadable response body>'

        if resp.ok:
            try:
                j = resp.json()
            except Exception:
                logger.warning("OpenAI caption: response ok but JSON decode failed; raw: %s", text_snippet)
                return ''

            content = ''
            if isinstance(j, dict):
                try:
                    content = j.get('choices', [])[0].get('message', {}).get('content', '')
                except Exception:
                    content = ''
                if not content:
                    try:
                        content = j.get('output_text') or j.get('output', '')
                    except Exception:
                        content = ''

            logger.info("OpenAI caption response keys: %s", list(j.keys()) if isinstance(j, dict) else type(j))
            if content:
                logger.info("OpenAI caption generated, length=%d", len(content))
                return content
            else:
                logger.warning("OpenAI caption: no textual content found in response; raw: %s", text_snippet)
        else:
            # If OpenAI returns a context length error, treat as non-fatal and fallback
            try:
                jerr = resp.json()
                err_code = jerr.get('error', {}).get('code')
                if err_code == 'context_length_exceeded':
                    logger.warning("OpenAI context length exceeded for image; skipping OpenAI caption. Raw: %s", text_snippet)
                    return ''
            except Exception:
                pass
            logger.warning("OpenAI caption request failed (status %s): %s", resp.status_code, text_snippet)

    except Exception as e:
        logger.exception("OpenAI caption generation failed: %s", e)

    return ''


@app.post('/admin/test_image_caption/')
async def admin_test_image_caption(image: UploadFile = File(...), provider: str = Form('openai')):
    """Upload a single image and return caption from OpenAI or Ollama. Useful for debugging.
    provider: 'openai' or 'ollama'
    """
    # save temp file
    try:
        data = await image.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[1] or '.png') as tmp:
            tmp.write(data)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded image: {e}")

    result = {'provider': provider, 'filename': image.filename}
    try:
        prompt = "Describe this image briefly and highlight important visual elements. If there are any texts, formulas or charts, summarize them."
        if provider == 'openai':
            openai_api_key = os.getenv('OPENAI_API_KEY', '')
            if not openai_api_key:
                raise HTTPException(status_code=400, detail='OPENAI_API_KEY not configured')
            cap = generate_image_with_openai(tmp_path, prompt, openai_api_key)
            result['caption'] = cap
        else:
            cap = generate_image_with_qwen(tmp_path, prompt)
            result['caption'] = cap
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    return result

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
    logger.info("Extracted base text length: %d chars", len(text))
    
    # Create PDF entry first to get pdf_id for image storage
    pdf_id = create_pdf_entry_with_hash(pdf.filename, embedding_type, file_hash)
    logger.info("Created PDF entry with id=%d", pdf_id)
    
    # Extract images and produce OCR + vision captions, append to text
    try:
        # Pass pdf_id to save images permanently
        image_data = extract_images_from_pdf(tmp_path, pdf_id=pdf_id)
        logger.info("Found %d images in PDF", len(image_data))

        ocr_texts = []
        captions = []
        # Check if OCR and vision captions are enabled via env var. If OPENAI_API_KEY
        # is present, prefer OpenAI captions automatically (they are higher quality)
        openai_api_key = os.getenv('OPENAI_API_KEY', '')
        enable_ocr = os.getenv('ENABLE_OCR', 'true').lower() == 'true'  # OCR enabled by default
        enable_vision = os.getenv('ENABLE_VISION_CAPTIONS', 'false').lower() == 'true' or bool(openai_api_key)
        logger.info("Vision captions enabled=%s; OPENAI_API_KEY present=%s", enable_vision, bool(openai_api_key))

        for image_path, page_num in image_data:
            # Save image reference to database
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pdf_images (pdf_id, image_path, page_number) VALUES (%s, %s, %s)",
                    (pdf_id, image_path, page_num)
                )
                conn.commit()
            logger.info("Saved image reference for page %d: %s", page_num, image_path)
            
            # Only run OCR if enabled and Tesseract is available
            if enable_ocr:
                ocr_result = ocr_image_file(image_path)
                if ocr_result and len(ocr_result.strip()) > 10:
                    ocr_texts.append(ocr_result)
                    logger.info("OCR text added: %d chars", len(ocr_result))

            # Only generate captions if enabled (can be slow / costly with many images)
            if enable_vision:
                try:
                    caption_prompt = "Describe this image briefly and highlight important visual elements. If there are any texts, formulas or charts, summarize them."
                    cap = ''
                    # Prefer OpenAI Vision (chat completions with embedded data URI) when API key is present
                    if openai_api_key:
                        cap = generate_image_with_openai(image_path, caption_prompt, openai_api_key)
                        if cap:
                            logger.info("Caption produced by OpenAI for image: %s", image_path)
                    # Fallback to local Ollama if OpenAI not configured or failed
                    if not cap:
                        cap = generate_image_with_qwen(image_path, caption_prompt)
                        if cap:
                            logger.info("Caption produced by Ollama for image: %s", image_path)

                    if cap and len(cap.strip()) > 0:
                        captions.append(cap)
                        logger.info("Caption added: %d chars", len(cap))
                except Exception as e:
                    logger.warning("Skipping caption for image due to error: %s", e)

        if ocr_texts:
            text += "\n\n[OCR_EXTRACTED_TEXT]\n" + "\n".join(ocr_texts)
            logger.info("Appended OCR texts to document")
        if captions:
            text += "\n\n[IMAGE_CAPTIONS]\n" + "\n".join(captions)
            logger.info("Appended image captions to document")
        logger.info("Final text length after images: %d chars", len(text))
    except Exception as e:
        logger.exception("Error processing images: %s", e)
    os.remove(tmp_path)

    # Dividir texto en chunks simples
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]

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


@app.post('/upload_pdfs/')
async def upload_pdfs(pdfs: list[UploadFile] = File(...), embedding_type: str = Form(...), file_hashes: list[str] | None = Form(None)):
    """Accept multiple PDF uploads in one request. Returns per-file results.
    Expect multiple 'pdf' files and optionally multiple 'file_hashes' values in the same order.
    """
    results = []
    # Normalize file_hashes
    if file_hashes is None:
        file_hashes = [None] * len(pdfs)

    for idx, pdf in enumerate(pdfs):
        fh = None
        if idx < len(file_hashes):
            fh = file_hashes[idx]

        try:
            file_bytes = await pdf.read()
            computed_hash = hashlib.sha256(file_bytes).hexdigest()
            file_hash = fh or computed_hash

            # Quick check by hash
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM pdfs WHERE hash = %s", (file_hash,))
                if cur.fetchone():
                    results.append({'filename': pdf.filename, 'status': 'duplicate', 'reason': 'hash_exists'})
                    continue

            # Filename check
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM pdfs WHERE filename = %s", (pdf.filename,))
                if cur.fetchone():
                    results.append({'filename': pdf.filename, 'status': 'duplicate', 'reason': 'filename_exists'})
                    continue

            # Chunk-based heuristic for existing rows
            with conn.cursor() as cur_all:
                cur_all.execute("SELECT id, hash FROM pdfs")
                all_rows = cur_all.fetchall()

            matched_existing = False
            for existing_id, stored_hash in all_rows:
                if stored_hash == file_hash:
                    matched_existing = True
                    break

                # compute chunk hash
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
                    # update existing row
                    with conn.cursor() as cur3:
                        cur3.execute("UPDATE pdfs SET hash = %s WHERE id = %s", (file_hash, existing_id))
                        conn.commit()
                    matched_existing = True
                    break

            if matched_existing:
                results.append({'filename': pdf.filename, 'status': 'duplicate', 'reason': 'matched_by_chunks'})
                continue

            # If new, create entry and save embeddings
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            text = extract_text_from_pdf(tmp_path)
            logger.info("PDF '%s': Extracted base text length: %d chars", pdf.filename, len(text))
            
            # Create PDF entry first to get pdf_id for image storage
            pdf_id = create_pdf_entry_with_hash(pdf.filename, embedding_type, file_hash)
            logger.info("PDF '%s': Created PDF entry with id=%d", pdf.filename, pdf_id)
            
            # Extract images and produce OCR + vision captions, append to text
            try:
                # Pass pdf_id to save images permanently
                image_data = extract_images_from_pdf(tmp_path, pdf_id=pdf_id)
                logger.info("PDF '%s': Found %d images", pdf.filename, len(image_data))
                ocr_texts = []
                captions = []
                openai_api_key = os.getenv('OPENAI_API_KEY', '')
                enable_ocr = os.getenv('ENABLE_OCR', 'true').lower() == 'true'  # OCR enabled by default
                enable_vision = os.getenv('ENABLE_VISION_CAPTIONS', 'false').lower() == 'true' or bool(openai_api_key)
                logger.info("Vision captions enabled=%s; OPENAI_API_KEY present=%s", enable_vision, bool(openai_api_key))
                
                for image_path, page_num in image_data:
                    # Save image reference to database
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO pdf_images (pdf_id, image_path, page_number) VALUES (%s, %s, %s)",
                            (pdf_id, image_path, page_num)
                        )
                        conn.commit()
                    logger.info("PDF '%s': Saved image reference for page %d: %s", pdf.filename, page_num, image_path)
                    
                    # Only run OCR if enabled and Tesseract is available
                    if enable_ocr:
                        ocr_result = ocr_image_file(image_path)
                        if ocr_result and len(ocr_result.strip()) > 10:
                            ocr_texts.append(ocr_result)
                            logger.info("OCR text added: %d chars", len(ocr_result))
                    
                    # Only generate captions if enabled (can be slow/costly with many images)
                    if enable_vision:
                        try:
                            caption_prompt = "Describe this image briefly and highlight important visual elements. If there are any texts, formulas or charts, summarize them."
                            cap = ''
                            if openai_api_key:
                                cap = generate_image_with_openai(image_path, caption_prompt, openai_api_key)
                                if cap:
                                    logger.info("Caption produced by OpenAI for image: %s", image_path)
                            if not cap:
                                cap = generate_image_with_qwen(image_path, caption_prompt)
                                if cap:
                                    logger.info("Caption produced by Ollama for image: %s", image_path)
                            if cap and len(cap.strip()) > 0:
                                captions.append(cap)
                                logger.info("Caption added: %d chars", len(cap))
                        except Exception as e:
                            logger.warning("Skipping caption for image due to error: %s", e)
                
                if ocr_texts:
                    text += "\n\n[OCR_EXTRACTED_TEXT]\n" + "\n".join(ocr_texts)
                    logger.info("PDF '%s': Appended OCR texts", pdf.filename)
                if captions:
                    text += "\n\n[IMAGE_CAPTIONS]\n" + "\n".join(captions)
                    logger.info("PDF '%s': Appended image captions", pdf.filename)
                logger.info("PDF '%s': Final text length: %d chars", pdf.filename, len(text))
            except Exception as e:
                logger.exception("PDF '%s': Error processing images: %s", pdf.filename, e)
            os.remove(tmp_path)

            chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]

            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            for chunk in chunks:
                if embedding_type == "ollama":
                    embedding = get_ollama_embedding(chunk)
                elif embedding_type == "openai":
                    embedding = get_openai_embedding(chunk, openai_api_key)
                else:
                    raise Exception("Tipo de embedding no soportado")
                save_embedding(pdf_id, chunk, embedding, embedding_type)

            results.append({'filename': pdf.filename, 'status': 'uploaded', 'pdf_id': pdf_id})
        except HTTPException as he:
            results.append({'filename': pdf.filename, 'status': 'error', 'detail': str(he.detail)})
        except Exception as e:
            results.append({'filename': pdf.filename, 'status': 'error', 'detail': str(e)})

    return {'results': results}


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
    try:
        chunks = search_similar_chunks(pdf_id, query_embedding, embedding_type)
    except Exception as e:
        logger.exception("Error searching similar chunks for pdf_id=%s", pdf_id)
        raise HTTPException(status_code=500, detail=f"Error retrieving context for PDF: {e}")

    context = "\n".join(chunks)

    # If context is empty, include a helpful diagnostic message
    if not context.strip():
        # collect some diagnostics
        with conn.cursor() as cur:
            cur.execute("SELECT hash, embedding_type FROM pdfs WHERE id = %s", (pdf_id,))
            pdf_row = cur.fetchone()
        pdf_hash = pdf_row[0] if pdf_row else None
        pdf_embed_type = pdf_row[1] if pdf_row else None
        # count chunks available
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pdf_chunks_ollama WHERE pdf_id = %s", (pdf_id,))
            ollama_chunks = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM pdf_chunks_openai WHERE pdf_id = %s", (pdf_id,))
            openai_chunks = cur.fetchone()[0]

        detail = {
            'message': 'No context available for this PDF. It may have failed ingestion or OCR/captions were empty.',
            'pdf_id': pdf_id,
            'hash': pdf_hash,
            'pdf_embedding_type': pdf_embed_type,
            'chunks_ollama': ollama_chunks,
            'chunks_openai': openai_chunks
        }
        logger.info("Empty context diagnostics: %s", detail)
        raise HTTPException(status_code=404, detail=detail)

    # VLM-Enhanced Query Mode: Check if PDF has images stored in DB
    # If yes, load them and their stored captions for summaries. We'll also support
    # selective image loading when the user mentions a specific page number ("página 2").
    pdf_images = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT image_path, page_number, caption FROM pdf_images WHERE pdf_id = %s ORDER BY page_number",
            (pdf_id,)
        )
        pdf_images = cur.fetchall()

    if pdf_images:
        logger.info("VLM-Enhanced mode activated: found %d images for pdf_id=%d", len(pdf_images), pdf_id)
    else:
        logger.info("No images found for pdf_id=%d, using text-only mode", pdf_id)

    # Build a short per-page summary block so captions aren't lost in chunk boundaries
    image_summaries = []
    for img_path, page_num, caption in pdf_images:
        short = (caption or '').strip()
        if not short:
            short = f"Imagen en página {page_num}: sin descripción disponible."
        image_summaries.append(f"Página {page_num}: {short}")
    if image_summaries:
        # Prepend an explicit marker so models see per-page summaries early
        context = "\n[IMAGE_SUMMARIES]\n" + "\n".join(image_summaries) + "\n\n" + context

    # Detect explicit page reference in the user's query (e.g. "página 2")
    import re
    page_refs = re.findall(r"p(?:á|a)gina\s*(\d+)", query.lower())
    requested_pages = [int(p) for p in page_refs] if page_refs else []

    # Select which images to attach to the VLM request.
    if requested_pages:
        # Filter images to only those requested by page number
        selected_images = [t for t in pdf_images if t[1] in requested_pages]
        if not selected_images:
            # If requested pages not found, fall back to first 3 images
            selected_images = pdf_images[:3]
    else:
        # Default: first 5 images (each tuple is (path, page, caption))
        selected_images = pdf_images[:5]

    # Generar respuesta en lenguaje natural usando el modelo seleccionado
    if embedding_type == "ollama":
        # Usar Qwen (disponible en Ollama) para generar respuesta
        ollama_model = "qwen3:4b"  # modelo conversacional instalado en Ollama
        prompt = f"""Responde en lenguaje natural a la pregunta del usuario usando el contexto extraído del documento.

El contexto puede incluir:
- Texto extraído directamente del PDF
- Texto extraído vía OCR de imágenes (marcado con [OCR_EXTRACTED_TEXT])
- Descripciones visuales de imágenes generadas por IA (marcado con [IMAGE_CAPTIONS])

Si la pregunta es sobre imágenes, diagramas, gráficos o elementos visuales, usa las descripciones disponibles en [IMAGE_CAPTIONS] para responder de manera precisa y detallada.

Pregunta: {query}

Contexto del documento:
{context}"""
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
        # VLM-Enhanced Mode: If we have images, use OpenAI Vision to analyze them directly
        if pdf_images and openai_api_key:
            logger.info("Using VLM-enhanced mode with %d images", len(pdf_images))
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
            
            # Build messages array with text + images
            system_prompt = """Eres un asistente experto que responde preguntas sobre documentos PDF con contenido multimodal.

Tienes acceso a:
1. El texto extraído del documento (incluye OCR si es necesario)
2. Las imágenes originales del documento

Analiza tanto el texto como las imágenes para proporcionar respuestas precisas y detalladas. Cuando veas gráficos, diagramas, tablas o cualquier elemento visual, descríbelos específicamente y úsalos para responder la pregunta del usuario."""
            
            # Create user message with text context
            user_content = [
                {"type": "text", "text": f"Pregunta: {query}\n\nContexto del documento:\n{context}"}
            ]
            
            # Add images (from selected_images which respects page refs)
            for img_path, page_num, img_caption in selected_images:
                if os.path.exists(img_path):
                    try:
                        # Read and encode image
                        import base64
                        with open(img_path, 'rb') as img_file:
                            img_data = img_file.read()
                        base64_img = base64.b64encode(img_data).decode('utf-8')
                        
                        # Skip if image is too large
                        if len(base64_img) < 100000:  # ~100KB limit
                            user_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_img}",
                                    "detail": "high"
                                },
                                "meta": {"page": page_num, "caption": (img_caption or '')[:200]}
                            })
                            logger.info("Added image from page %d to VLM request", page_num)
                    except Exception as e:
                        logger.warning("Failed to load image %s: %s", img_path, e)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            payload = {
                "model": "gpt-4o-mini",  # Vision-capable model
                "messages": messages,
                "max_tokens": 500
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                answer = response.json()["choices"][0]["message"]["content"]
                logger.info("VLM-enhanced response generated successfully")
            except Exception as e:
                logger.exception("VLM-enhanced mode failed: %s", e)
                # Fallback to text-only mode
                answer = "Error al procesar imágenes. Intenta de nuevo."
        else:
            # Text-only mode (legacy)
            logger.info("Using text-only mode (no images or no API key)")
            openai_model = "gpt-4-turbo"  # Cambia por el modelo que prefieras
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
            system_prompt = """Eres un asistente que responde preguntas sobre documentos PDF.

El contexto que recibes puede incluir:
- Texto extraído directamente del PDF
- Texto extraído vía OCR de imágenes (marcado con [OCR_EXTRACTED_TEXT])
- Descripciones visuales detalladas de imágenes, diagramas y gráficos generadas por IA de visión (marcado con [IMAGE_CAPTIONS])

Cuando el usuario pregunte sobre imágenes, diagramas, tablas, gráficos o cualquier elemento visual del documento, usa las descripciones disponibles en las secciones [IMAGE_CAPTIONS] para proporcionar respuestas precisas y detalladas. No digas que no puedes ver las imágenes; en su lugar, usa las descripciones visuales proporcionadas en el contexto."""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Pregunta: {query}\n\nContexto del documento:\n{context}"}
            ]
            payload = {"model": openai_model, "messages": messages, "max_tokens": 256}
            
            try:
                openai_response = requests.post(url, json=payload, headers=headers, timeout=30)
                openai_response.raise_for_status()
                answer = openai_response.json().get("choices", [{}])[0].get("message", {}).get("content", "No se pudo generar respuesta.")
            except Exception as e:
                logger.exception("OpenAI text-only mode failed: %s", e)
                answer = "Error al generar respuesta. Intenta de nuevo."
    else:
        answer = "No se pudo generar respuesta."

    return {"response": answer}


@app.get('/pdfs/{pdf_id}/debug')
async def pdf_debug(pdf_id: int):
    """Return debugging info for a PDF: stored chunks, OCR/captions markers, hash and metadata counts."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, filename, embedding_type, hash, folder_id FROM pdfs WHERE id = %s", (pdf_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="PDF not found")
        pdf_info = {'id': row[0], 'filename': row[1], 'embedding_type': row[2], 'hash': row[3], 'folder_id': row[4]}

    # fetch chunks from both chunk tables
    chunks_ollama = []
    chunks_openai = []
    with conn.cursor() as cur:
        try:
            cur.execute("SELECT id, chunk FROM pdf_chunks_ollama WHERE pdf_id = %s ORDER BY id", (pdf_id,))
            chunks_ollama = [{'id': r[0], 'chunk': r[1]} for r in cur.fetchall()]
        except Exception:
            pass
        try:
            cur.execute("SELECT id, chunk FROM pdf_chunks_openai WHERE pdf_id = %s ORDER BY id", (pdf_id,))
            chunks_openai = [{'id': r[0], 'chunk': r[1]} for r in cur.fetchall()]
        except Exception:
            pass

    # Try to detect OCR/IMAGE caption markers inside chunks
    ocr_snippets = []
    caption_snippets = []
    for c in chunks_ollama + chunks_openai:
        ch = c.get('chunk') or ''
        if '[OCR_EXTRACTED_TEXT]' in ch:
            ocr_snippets.append(ch[ch.find('[OCR_EXTRACTED_TEXT]'):][:1000])
        if '[IMAGE_CAPTIONS]' in ch:
            caption_snippets.append(ch[ch.find('[IMAGE_CAPTIONS]'):][:1000])

    # metadata
    meta = get_pdf_metadata_from_db(pdf_id)

    return {
        'pdf': pdf_info,
        'metadata': meta,
        'chunks_ollama_count': len(chunks_ollama),
        'chunks_openai_count': len(chunks_openai),
        'ocr_snippets': ocr_snippets,
        'caption_snippets': caption_snippets,
        'chunks_ollama_sample': chunks_ollama[:3],
        'chunks_openai_sample': chunks_openai[:3]
    }


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
