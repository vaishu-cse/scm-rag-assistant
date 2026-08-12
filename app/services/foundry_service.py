import os
from openai import OpenAI
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