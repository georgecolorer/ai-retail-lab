from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)
client = genai.Client()

print("Dostupne modely pro muj API klic:")
for m in client.models.list():
    if "gemini" in m.name:
        print("-", m.name)