import base64
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Test with neutral prompt
image_path = r"C:\Users\pinnc\chatpdf-clean\backend\uploads\images\74\page_1.png"

with open(image_path, 'rb') as f:
    image_data = f.read()

base64_image = base64.b64encode(image_data).decode('utf-8')

openai_api_key = os.getenv('OPENAI_API_KEY')

url = "https://api.openai.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {openai_api_key}",
    "Content-Type": "application/json"
}

# Try with more neutral prompt
payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Describe what you see in this image. Focus on visual elements, composition, colors, and any objects or subjects present."
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

print("Trying with neutral prompt...")
response = requests.post(url, headers=headers, json=payload, timeout=60)

if response.status_code == 200:
    result = response.json()
    description = result['choices'][0]['message']['content']
    print("\n✅ Response:")
    print("=" * 80)
    print(description)
    print("=" * 80)
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)
