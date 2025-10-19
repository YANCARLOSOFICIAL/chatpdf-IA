import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

PG_CONN = os.getenv("PG_CONN", "dbname=chatpdf user=postgres password=yan123 host=localhost")
conn = psycopg2.connect(PG_CONN)

with conn.cursor() as cur:
    cur.execute("SELECT id, filename, embedding_type FROM pdfs WHERE id = 74")
    result = cur.fetchone()
    
    if result:
        pdf_id, filename, embed_type = result
        print(f"\n📄 PDF ID {pdf_id}:")
        print(f"   Filename: {filename}")
        print(f"   Embedding: {embed_type}")
        print(f"\n🖼️ Images location:")
        print(f"   C:\\Users\\pinnc\\chatpdf-clean\\backend\\uploads\\images\\{pdf_id}\\")
    else:
        print("PDF ID 74 not found")

conn.close()
