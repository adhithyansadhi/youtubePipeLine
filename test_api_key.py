"""
Quick test: Verify your Gemini API key is working.
"""
import os
import sys
from pathlib import Path

# Load .env manually
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}" if len(API_KEY) > 12 else f"API Key: {API_KEY}")
print(f"Model:   {MODEL}")
print("-" * 50)

if not API_KEY or API_KEY == "your_gemini_api_key_here":
    print("ERROR: No valid API key found in .env")
    sys.exit(1)

try:
    from google import genai
    client = genai.Client(api_key=API_KEY)
    
    print(f"Sending test prompt to {MODEL}...")
    response = client.models.generate_content(
        model=MODEL,
        contents="Reply with exactly: GEMINI_OK. Nothing else.",
    )
    
    reply = response.text.strip()
    print(f"Response: {reply}")
    print("-" * 50)
    
    if "GEMINI_OK" in reply:
        print("SUCCESS: API key is working correctly!")
    else:
        print("WARNING: Got a response but it was unexpected. API key works though.")
    
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
    sys.exit(1)
