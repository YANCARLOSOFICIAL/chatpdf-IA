import requests
from pathlib import Path
from PyPDF2 import PdfReader

url = 'http://127.0.0.1:8000/pdfs/77/file'
try:
    r = requests.get(url, timeout=20)
    print('Status', r.status_code)
    if r.status_code == 200:
        out = Path('test_download_77.pdf')
        out.write_bytes(r.content)
        print('Saved', out.resolve())
        try:
            reader = PdfReader(str(out))
            print('Pages', len(reader.pages))
        except Exception as e:
            print('PyPDF2 failed:', e)
    else:
        print('Download failed, status:', r.status_code)
except Exception as e:
    print('Request error:', e)
