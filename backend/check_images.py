import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

PG_CONN = os.getenv("PG_CONN", "dbname=chatpdf user=postgres password=yan123 host=localhost")
conn = psycopg2.connect(PG_CONN)

with conn.cursor() as cur:
    # Check images in DB
    cur.execute("SELECT id, pdf_id, image_path, page_number FROM pdf_images WHERE pdf_id = 74")
    images = cur.fetchall()
    
    print(f"\n✅ Found {len(images)} images for PDF ID 74:\n")
    for img_id, pdf_id, path, page in images:
        exists = "✅" if os.path.exists(path) else "❌ FILE MISSING"
        print(f"  Page {page}: {path} {exists}")
    
    # Check chunks
    cur.execute("SELECT COUNT(*) FROM pdf_chunks_openai WHERE pdf_id = 74")
    chunk_count = cur.fetchone()[0]
    print(f"\n✅ Total chunks for PDF 74: {chunk_count}")
    
    # Check a sample chunk
    cur.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = 74 LIMIT 1")
    sample = cur.fetchone()
    if sample:
        chunk_text = sample[0]
        has_ocr = "[OCR_EXTRACTED_TEXT]" in chunk_text
        has_captions = "[IMAGE_CAPTIONS]" in chunk_text
        print(f"\n📄 Sample chunk (first 200 chars):")
        print(f"   {chunk_text[:200]}...")
        print(f"\n🔍 Markers:")
        print(f"   [OCR_EXTRACTED_TEXT]: {'✅ Found' if has_ocr else '❌ Not found'}")
        print(f"   [IMAGE_CAPTIONS]: {'✅ Found' if has_captions else '❌ Not found'}")

conn.close()
