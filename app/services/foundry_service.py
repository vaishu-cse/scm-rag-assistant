import os
from openai import OpenAI
import requests
from dotenv import load_dotenv
load_dotenv()

class FoundryService:

    def __init__(self, endpoint: str, agent_name: str):
        self.agent_name = agent_name

        api_key = os.getenv("FOUNDRY_API_KEY")

        if not api_key:
            raise ValueError("FOUNDRY_API_KEY is not configured")

        # Project endpoint:
        # https://<resource>.services.ai.azure.com/api/projects/<project>
        #
        # OpenAI-compatible endpoint:
        # https://<resource>.services.ai.azure.com/api/projects/<project>/openai/v1

        base_url = f"{endpoint.rstrip('/')}/openai/v1"

        self.openai = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        print("FOUNDRY ENDPOINT:", base_url)
        print("AGENT NAME:", agent_name)

    def chat(self, message: str):

        response = self.openai.responses.create(
            extra_body={
                "agent_reference": {
                    "name": self.agent_name,
                    "type": "agent_reference",
                }
            },
            input=message,
        )

        return {
            "response_id": response.id,
            "answer": response.output_text,
        }

    def upload_document(self, file_path: str):
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        api_key = os.getenv("AZURE_SEARCH_API_KEY")

        if not endpoint or not api_key:
            raise ValueError("Azure Search configuration is missing")

        url = (
            f"{endpoint}/knowledgesources('scm-documentation')/files"
            f"?api-version=2026-05-01-preview"
        )

        with open(file_path, "rb") as file:
            response = requests.post(
                url,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/octet-stream",
                },
                data=file,
            )

        if response.status_code not in (200, 201, 202):
            raise Exception(
                f"Knowledge source upload failed: "
                f"{response.status_code} - {response.text}"
            )

        return response.json()