import os
from pathlib import Path
from google import genai
from google.genai import types

def test_grounding():
    # Load .env
    env_file = Path('.env')
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

    api_key = os.getenv("GEMINI_API_KEY")
    model = "gemini-1.5-flash-latest"  # Using correct name
    
    print(f"Testing grounding on {model}...")
    client = genai.Client(api_key=api_key)
    
    try:
        response = client.models.generate_content(
            model=model,
            contents="Who won the most recent Super Bowl?",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        print("SUCCESS!")
        print(f"Response: {response.text[:100]}...")
        if hasattr(response, 'candidates') and response.candidates[0].grounding_metadata:
            print("Grounding metadata found!")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_grounding()
