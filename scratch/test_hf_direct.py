import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
model = "Qwen/Qwen2.5-7B-Instruct" 

url = f"https://api-inference.huggingface.co/models/{model}"

payload = {
    "inputs": "Say hello",
    "parameters": {"max_new_tokens": 10}
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
