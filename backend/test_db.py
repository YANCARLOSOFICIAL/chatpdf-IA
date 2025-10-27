import psycopg2
import json

try:
    conn = psycopg2.connect(host='localhost', database='chatpdf', user='postgres', password='postgres')
    cur = conn.cursor()
    
    # Count chunks
    cur.execute('SELECT COUNT(*) FROM pdf_chunks_ollama')
    ollama_count = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM pdf_chunks_openai')
    openai_count = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM pdf_chunk_spans')
    spans_count = cur.fetchone()[0]
    
    print(f"✓ Ollama chunks: {ollama_count}")
    print(f"✓ OpenAI chunks: {openai_count}")
    print(f"✓ Chunk spans: {spans_count}")
    
    # Get last few PDFs
    cur.execute('SELECT id, filename FROM pdfs ORDER BY id DESC LIMIT 3')
    pdfs = cur.fetchall()
    print(f"\nÚltimos PDFs:")
    for pdf_id, filename in pdfs:
        cur.execute('SELECT COUNT(*) FROM pdf_chunks_ollama WHERE pdf_id = %s', (pdf_id,))
        count = cur.fetchone()[0]
        print(f"  PDF {pdf_id}: {filename} - {count} chunks")
        
        # Get chunks for this PDF
        cur.execute('SELECT id, chunk FROM pdf_chunks_ollama WHERE pdf_id = %s LIMIT 1', (pdf_id,))
        chunk_result = cur.fetchone()
        if chunk_result:
            chunk_id, chunk_text = chunk_result
            print(f"    Sample chunk {chunk_id}: {chunk_text[:100]}...")
            
            # Check if this chunk has a span
            cur.execute('SELECT page_number, x, y, width, height FROM pdf_chunk_spans WHERE chunk_id = %s AND pdf_id = %s', (chunk_id, pdf_id))
            span = cur.fetchone()
            if span:
                print(f"    ✓ Span found: Page {span[0]}, bbox=({span[1]:.1f}, {span[2]:.1f}, {span[3]:.1f}x{span[4]:.1f})")
            else:
                print(f"    ✗ NO SPAN for this chunk!")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
