import requests
from PIL import Image, ImageDraw
import tempfile, os

# Create a simple one-page PDF using Pillow
img = Image.new('RGB', (612, 792), (255, 255, 255))
d = ImageDraw.Draw(img)
d.text((72, 72), "Test PDF for upload", fill=(0, 0, 0))

with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
    tmp_name = tmp.name
img.save(tmp_name, "PDF")

files = {'pdf': open(tmp_name, 'rb')}
data = {'embedding_type': 'openai'}

print('Uploading test PDF:', tmp_name)
try:
    resp = requests.post('http://127.0.0.1:8000/upload_pdf/', files=files, data=data, timeout=30)
    print('Status code:', resp.status_code)
    try:
        print('Response JSON:', resp.json())
    except Exception:
        print('Response text:', resp.text)
except Exception as e:
    print('Request failed:', e)
finally:
    try:
        files['pdf'].close()
    except Exception:
        pass
    try:
        os.remove(tmp_name)
    except Exception:
        pass
