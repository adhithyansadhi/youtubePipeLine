import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")

url = "https://router.huggingface.co/v1/chat/completions"
# Using a very common model that is often hosted by HF directly or multiple partners
model = "meta-llama/Llama-3.1-8B-Instruct" 

payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 10
}

headers = {
    "Authorization": f"Bearer {HF_TOKEN.strip()}",
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
