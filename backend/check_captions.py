import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('PG_CONN'))
cur = conn.cursor()
cur.execute("SELECT id, page_number, caption IS NOT NULL AS has_caption, length(coalesce(caption,'')) FROM pdf_images WHERE pdf_id = 74 ORDER BY page_number")
rows = cur.fetchall()
print('PDF 74 image captions:')
for r in rows:
    print(f'  image_id={r[0]} page={r[1]} has_caption={r[2]} len={r[3]}')
    if r[3] > 0:
        cur2 = conn.cursor()
        cur2.execute("SELECT caption FROM pdf_images WHERE id = %s", (r[0],))
        print('   ->', cur2.fetchone()[0][:300])
        cur2.close()

cur.close(); conn.close()
