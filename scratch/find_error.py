import hashlib
from google import genai
from google.genai import types
from config import get_settings

def get_hash(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

settings = get_settings()
api_key = settings.gemini_api_key

print("API Key exists:", bool(api_key))

client = genai.Client(api_key=api_key)

try:
    print("Testing gemini-2.5-flash-lite...")
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents="Hello",
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    print("Success:", response.text)
except Exception as e:
    err_str = str(e)
    h = get_hash(err_str)
    print("Exception class:", type(e).__name__)
    print("Exception string:", err_str)
    print("SHA-256 Hash:", h)
