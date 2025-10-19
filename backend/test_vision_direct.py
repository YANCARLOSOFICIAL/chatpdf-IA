import base64
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Test direct OpenAI Vision on page_1.png
image_path = r"C:\Users\pinnc\chatpdf-clean\backend\uploads\images\74\page_1.png"

print(f"Testing image: {image_path}")
print(f"File exists: {os.path.exists(image_path)}")
print(f"File size: {os.path.getsize(image_path)} bytes\n")

# Read and encode image
with open(image_path, 'rb') as f:
    image_data = f.read()

base64_image = base64.b64encode(image_data).decode('utf-8')
print(f"Base64 length: {len(base64_image)} chars\n")

# Call OpenAI Vision directly
openai_api_key = os.getenv('OPENAI_API_KEY')

url = "https://api.openai.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {openai_api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Describe en detalle TODO lo que ves en esta imagen. Si hay personas, descríbelas completamente: género, edad, características físicas, expresión, vestimenta, etc."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "high"
                    }
                }
            ]
        }
    ],
    "max_tokens": 500
}

print("Calling OpenAI Vision API...")
response = requests.post(url, headers=headers, json=payload, timeout=60)

if response.status_code == 200:
    result = response.json()
    description = result['choices'][0]['message']['content']
    print("\n✅ OpenAI Vision Response:")
    print("=" * 80)
    print(description)
    print("=" * 80)
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)
