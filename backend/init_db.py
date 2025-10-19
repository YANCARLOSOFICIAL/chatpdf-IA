import psycopg2
from pgvector.psycopg2 import register_vector
import os
from dotenv import load_dotenv

load_dotenv()

PG_CONN = os.getenv("PG_CONN", "dbname=chatpdf user=postgres password=yan123 host=localhost")
conn = psycopg2.connect(PG_CONN)
register_vector(conn)

with conn.cursor() as cur:
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdfs (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            id SERIAL PRIMARY KEY,
            pdf_id INTEGER REFERENCES pdfs(id),
            chunk TEXT,
            embedding vector(1024)
        );
    """)
    # Nueva tabla para almacenar las imágenes extraídas de los PDFs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_images (
            id SERIAL PRIMARY KEY,
            pdf_id INTEGER REFERENCES pdfs(id) ON DELETE CASCADE,
            image_path TEXT NOT NULL,
            page_number INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    # Ensure caption column exists for storing per-image captions
    try:
        cur.execute("ALTER TABLE pdf_images ADD COLUMN IF NOT EXISTS caption TEXT")
    except Exception:
        # Older Postgres may not support IF NOT EXISTS on ALTER TABLE; attempt safely
        try:
            cur.execute("ALTER TABLE pdf_images ADD COLUMN caption TEXT")
        except Exception:
            pass
    conn.commit()

print("Tablas y extensión vector creadas correctamente.")
