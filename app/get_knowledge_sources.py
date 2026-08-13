import os
import requests
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_API_KEY")

url = (
    f"{endpoint}/knowledgesources('scm-documentation')"
    f"?api-version=2026-05-01-preview"
)

response = requests.get(
    url,
    headers={
        "api-key": key
    }
)

print("STATUS:", response.status_code)
print("RESPONSE:")
print(response.text)