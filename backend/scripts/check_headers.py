import requests

urls = ['http://127.0.0.1:8000/pdfs/77/file','http://127.0.0.1:8000/pdfs/77/images/1']
for url in urls:
    try:
        r = requests.get(url, timeout=5)
        print('\nURL:', url)
        print('Status:', r.status_code)
        for k,v in r.headers.items():
            if k.lower().startswith('access-control') or k.lower() in ('content-type','content-length'):
                print(f'{k}: {v}')
    except Exception as e:
        print('\nURL:', url)
        print('Error:', e)
