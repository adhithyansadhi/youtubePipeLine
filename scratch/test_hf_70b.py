import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")

url = "https://router.huggingface.co/v1/chat/completions"
model = "meta-llama/Llama-3.3-70B-Instruct" 

payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Tell me a joke about robots."}],
    "max_tokens": 50
}

headers = {
    "Authorization": f"Bearer {HF_TOKEN.strip()}",
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
