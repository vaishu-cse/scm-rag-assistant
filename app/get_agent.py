import os
import requests
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
api_key = os.getenv("FOUNDRY_API_KEY")
agent_name = os.getenv("FOUNDRY_AGENT_NAME")

url = f"{endpoint}/agents/{agent_name}"

response = requests.get(
    url,
    headers={
        "api-key": api_key,
        "Content-Type": "application/json",
    },
    params={
        "api-version": "v1"
    },
)

print("STATUS:", response.status_code)
print("RESPONSE:")
print(response.text)