import httpx

url = 'http://127.0.0.1:8000/chat/'
form = {
    'query': '¿De qué trata este documento? Resume en una frase.',
    'pdf_id': '83',
    # don't send embedding_type to use system default
    'include_suggestions': '0'
}

try:
    r = httpx.post(url, data=form, timeout=30.0)
    print('status', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)
except Exception as e:
    print('error', e)
