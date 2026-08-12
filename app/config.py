import os

from dotenv import load_dotenv


load_dotenv()


class Settings:

    foundry_project_endpoint = os.getenv(
        "FOUNDRY_PROJECT_ENDPOINT"
    )

    foundry_agent_name = os.getenv(
        "FOUNDRY_AGENT_NAME"
    )


settings = Settings()