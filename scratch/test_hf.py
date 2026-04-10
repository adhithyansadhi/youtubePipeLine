import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
print(f"Token length: {len(HF_TOKEN) if HF_TOKEN else 0}")
print(f"Token prefix: {HF_TOKEN[:7] if HF_TOKEN else 'None'}")

url = "https://router.huggingface.co/v1/chat/completions"
# Use a very common model
model = "meta-llama/Llama-2-7b-hf" # Wait, Llama 2 is gated too.
model = "Qwen/Qwen2.5-0.5B-Instruct" # Very small, very likely free and ungated

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
