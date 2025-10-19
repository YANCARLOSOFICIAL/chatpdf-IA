import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

PG_CONN = os.getenv("PG_CONN", "dbname=chatpdf user=postgres password=yan123 host=localhost")
conn = psycopg2.connect(PG_CONN)

with conn.cursor() as cur:
    # Get all chunks for PDF 74
    cur.execute("SELECT chunk FROM pdf_chunks_openai WHERE pdf_id = 74 ORDER BY id")
    chunks = cur.fetchall()
    
    print(f"\n📄 Total chunks for PDF 74: {len(chunks)}\n")
    
    for i, (chunk_text,) in enumerate(chunks, 1):
        print(f"{'='*80}")
        print(f"CHUNK {i}")
        print(f"{'='*80}")
        
        # Check for markers
        has_ocr = "[OCR_EXTRACTED_TEXT]" in chunk_text
        has_captions = "[IMAGE_CAPTIONS]" in chunk_text
        
        if has_captions:
            # Extract caption section
            caption_start = chunk_text.find("[IMAGE_CAPTIONS]")
            caption_section = chunk_text[caption_start:caption_start+500]
            print("\n🎨 IMAGE CAPTIONS Section:")
            print(caption_section)
        
        if has_ocr:
            print("\n📝 Has OCR_EXTRACTED_TEXT")
        
        print(f"\n📏 Length: {len(chunk_text)} chars")
        print()

conn.close()
