import os

from dotenv import load_dotenv


load_dotenv(override=True)


class Settings:

    foundry_project_endpoint = os.getenv(
        "FOUNDRY_PROJECT_ENDPOINT"
    )

    foundry_agent_name = os.getenv(
        "FOUNDRY_AGENT_NAME"
    )

    database_url = os.getenv(
        "DATABASE_URL"
    )

    jwt_secret_key = os.getenv(
        "JWT_SECRET_KEY"
    )


settings = Settings()