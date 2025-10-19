import os
import base64
import requests
from dotenv import load_dotenv
import psycopg2

load_dotenv()
PG_CONN = os.getenv("PG_CONN", "dbname=chatpdf user=postgres password=yan123 host=localhost")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

conn = psycopg2.connect(PG_CONN)

# Neutral prompt that avoids identification requests and focuses on visual description
NEUTRAL_PROMPT = (
    "Describe neutrally and objectively what you see in this image. "
    "Focus on composition, objects, and non-identifying visual characteristics (clothing, posture, setting) "
    "without naming or identifying individuals."
)

with conn.cursor() as cur:
    cur.execute("SELECT id, pdf_id, image_path, page_number FROM pdf_images ORDER BY pdf_id, page_number")
    rows = cur.fetchall()

for img_id, pdf_id, image_path, page_number in rows:
    print(f"Processing PDF {pdf_id} page {page_number}: {image_path}")
    if not os.path.exists(image_path):
        print("  - file missing, skipping")
        continue

    with open(image_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": NEUTRAL_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}}
            ]}
        ],
        "max_tokens": 250
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        res = r.json()
        caption = res['choices'][0]['message']['content'].strip()
        print("  - caption length:", len(caption))
        # Save caption in DB
        with conn.cursor() as cur:
            cur.execute("UPDATE pdf_images SET caption = %s WHERE id = %s", (caption, img_id))
            conn.commit()
    except Exception as e:
        print("  - failed to generate caption:", e)

conn.close()
print("Done")
