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
    conn.commit()

print("Tablas y extensión vector creadas correctamente.")
