
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import PyPDF2
import requests
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()

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
    with conn.cursor() as cur:
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
async def upload_pdf(pdf: UploadFile = File(...), embedding_type: str = Form(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await pdf.read())
        tmp_path = tmp.name
    text = extract_text_from_pdf(tmp_path)
    os.remove(tmp_path)

    # Dividir texto en chunks simples
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    pdf_id = create_pdf_entry(pdf.filename, embedding_type)

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
