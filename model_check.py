import requests
import time

API_KEY = "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"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 🔥 Known FREE / usable models (dynamic availability)
models = [
    "google/gemini-2.0-flash-001",
    "mistralai/mistral-7b-instruct",
    "meta-llama/llama-3-8b-instruct",
    "nousresearch/nous-hermes-2-mixtral",
    "openchat/openchat-3.5",
    "gryphe/mythomist-7b",
    "deepseek/deepseek-chat",
    "deepseek/deepseek-coder",
    "qwen/qwen-7b-chat",
    "qwen/qwen-14b-chat"
]

def test_model(model):
    url = "https://openrouter.ai/api/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Say hello"}
        ],
        "max_tokens": 20
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"✅ WORKING: {model}")
            return "working"

        elif response.status_code == 429:
            print(f"⚠ RATE LIMITED: {model}")
            return "rate_limited"

        elif response.status_code == 402:
            print(f"💰 NO CREDITS: {model}")
            return "paid"

        else:
            print(f"❌ FAILED ({response.status_code}): {model}")
            return "failed"

    except Exception as e:
        print(f"❌ ERROR: {model} → {e}")
        return "error"


print("\n🔍 Testing models...\n")

working_models = []

for model in models:
    status = test_model(model)

    if status == "working":
        working_models.append(model)

    time.sleep(1)

print("\n🎯 FINAL WORKING MODELS:\n")
for m in working_models:
    print("👉", m)