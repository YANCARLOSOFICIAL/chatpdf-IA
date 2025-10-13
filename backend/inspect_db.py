#!/usr/bin/env python
import os
import sys
try:
    import psycopg2
except Exception as e:
    print('psycopg2 import error:', e)
    sys.exit(1)
from dotenv import load_dotenv

load_dotenv()
PG_CONN = os.getenv('PG_CONN','dbname=chatpdf user=postgres password=postgres host=localhost')
print('Using PG_CONN:', PG_CONN)

try:
    conn = psycopg2.connect(PG_CONN)
    cur = conn.cursor()

    print('\n-- pdfs (id, filename, folder_id) --')
    cur.execute('SELECT id, filename, folder_id FROM pdfs ORDER BY id DESC LIMIT 20')
    rows = cur.fetchall()
    print('pdfs rows=', len(rows))
    for r in rows:
        print(r)

    print('\n-- folders --')
    cur.execute('SELECT id, name FROM folders ORDER BY id')
    rows = cur.fetchall()
    print('folders rows=', len(rows))
    for r in rows:
        print(r)

    print('\n-- pdf_metadata --')
    cur.execute('SELECT * FROM pdf_metadata ORDER BY pdf_id DESC LIMIT 100')
    rows = cur.fetchall()
    print('pdf_metadata rows=', len(rows))
    for r in rows:
        print(r)

    cur.close()
    conn.close()
except Exception as e:
    print('DB query error:', e)
    sys.exit(2)
