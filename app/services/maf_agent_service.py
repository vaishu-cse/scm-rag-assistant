import time
from typing import Any

import requests
from agent_framework import Agent, FunctionTool
from agent_framework.openai import OpenAIChatClient

from app.config import settings
from app.database.database import SessionLocal
from app.models.user import User
from app.services.foundry_service import FoundryService
from app.config import settings

AGENT_INSTRUCTIONS = """
You are an enterprise Supply Chain Management assistant.

You have access to three tools:

1. search_scm_documents
   Use this for SCM-related information contained in the organization's
   procurement, inventory, purchasing, warehouse, logistics, and other
   SCM documentation.

2. get_user_count
   Use this when the user asks about the number of users registered
   in the application database.

3. get_weather
   Use this when the user asks for current weather information.

Always use the appropriate tool when information must come from an
external data source.

Do not invent information.

If a request requires multiple sources, use multiple tools.

After receiving tool results, provide a concise and accurate
natural-language response.
""".strip()


def search_scm_documents(query: str) -> str:
    """Search the existing Azure AI Search SCM document index."""

    start_time = time.perf_counter()

    print("\n[MAF TOOL SELECTED] search_scm_documents")
    print(f"[MAF TOOL INPUT] query: {query}")

    try:
        foundry_service = FoundryService(
            endpoint=settings.foundry_project_endpoint,
            agent_name=settings.foundry_agent_name,
        )
        documents = foundry_service.chat(query)

        elapsed = time.perf_counter() - start_time

        if not documents:
            print(
                f"[MAF TOOL RESULT] search_scm_documents | "
                f"documents_found=0 | duration={elapsed:.2f}s"
            )
            return "No relevant SCM documents were found."

        print(
            f"[MAF TOOL RESULT] search_scm_documents | "
            f"documents_found={len(documents)} | "
            f"duration={elapsed:.2f}s"
        )

        # Don't print document contents to terminal.
        # The tool result is returned to the MAF agent.
        # result = "\n\n".join(
        #     f"{document.get('title', 'SCM document')}: "
        #     f"{document.get('content', '')}"
        #     for document in documents
        # )

        # return result
        return documents

    except Exception as exc:
        elapsed = time.perf_counter() - start_time

        print(
            f"[MAF TOOL ERROR] search_scm_documents | "
            f"duration={elapsed:.2f}s | error={exc}"
        )

        return "SCM document search is currently unavailable."


def get_user_count() -> str:
    """Return the count of users in the existing application database."""

    start_time = time.perf_counter()

    print("\n[MAF TOOL SELECTED] get_user_count")

    db = SessionLocal()

    try:
        count = db.query(User).count()

        elapsed = time.perf_counter() - start_time

        print(
            f"[MAF TOOL RESULT] get_user_count | "
            f"count={count} | duration={elapsed:.2f}s"
        )

        return f"There are currently {count} registered users."

    except Exception as exc:
        elapsed = time.perf_counter() - start_time

        print(
            f"[MAF TOOL ERROR] get_user_count | "
            f"duration={elapsed:.2f}s | error={exc}"
        )

        return "The user count is currently unavailable."

    finally:
        db.close()


def get_weather(city: str) -> str:
    """Retrieve current weather for a city from WeatherAPI.com."""

    start_time = time.perf_counter()

    print("\n[MAF TOOL SELECTED] get_weather")
    print(f"[MAF TOOL INPUT] city: {city}")

    if not settings.weather_api_key:
        print("[MAF TOOL WARNING] Weather API key is not configured")
        return "Weather lookup is not configured."

    try:
        response = requests.get(
            "https://api.weatherapi.com/v1/current.json",
            params={
                "key": settings.weather_api_key,
                "q": city,
            },
            timeout=10,
        )

        if response.status_code == 400:
            print(
                f"[MAF TOOL RESULT] get_weather | "
                f"city={city} | location_not_found"
            )

            return f"Weather information could not be found for {city}."

        response.raise_for_status()

        payload = response.json()
        current = payload["current"]
        location = payload.get("location", {})

        elapsed = time.perf_counter() - start_time

        print(
            f"[MAF TOOL RESULT] get_weather | "
            f"city={location.get('name', city)} | "
            f"condition={current['condition']['text']} | "
            f"temperature={current['temp_c']} C | "
            f"duration={elapsed:.2f}s"
        )

        return (
            f"Current weather in {location.get('name', city)}: "
            f"{current['condition']['text']}, "
            f"{current['temp_c']} C, "
            f"humidity {current['humidity']}%."
        )

    except requests.RequestException as exc:
        elapsed = time.perf_counter() - start_time

        print(
            f"[MAF TOOL ERROR] get_weather | "
            f"city={city} | "
            f"duration={elapsed:.2f}s | "
            f"error={exc}"
        )

        return "Weather information is currently unavailable."

    except (KeyError, TypeError, ValueError) as exc:
        elapsed = time.perf_counter() - start_time

        print(
            f"[MAF TOOL ERROR] get_weather | "
            f"city={city} | "
            f"duration={elapsed:.2f}s | "
            f"error={exc}"
        )

        return "Weather information is currently unavailable."


class MafAgentService:
    """Microsoft Agent Framework orchestration for SCM chat."""

    def __init__(self) -> None:
        self._agent: Agent | None = None

    @property
    def agent(self) -> Agent:

        if self._agent is None:

            print("\n" + "=" * 80)
            print("[MAF INIT] Initializing Microsoft Agent Framework")
            print("=" * 80)

            if not settings.foundry_api_key:
                raise RuntimeError(
                    "FOUNDRY_API_KEY is not configured."
                )

            if not settings.foundry_model:
                raise RuntimeError(
                    "FOUNDRY_MODEL is not configured."
                )

            print(
                f"[MAF INIT] Model: {settings.foundry_model}"
            )

            print(
                "[MAF INIT] Creating Foundry OpenAI-compatible client..."
            )

            client = OpenAIChatClient(
                api_key=settings.foundry_api_key,
                base_url=(
                    f"{settings.foundry_project_endpoint}"
                    f"/api/projects/SCM-RAG-Knowledge-Assistant/openai/v1"
                ),
                model=settings.foundry_model,
            )

            tools = [
                FunctionTool(
                    name="search_scm_documents",
                    description=(
                        "Search SCM procurement, inventory, purchasing, "
                        "warehouse, logistics, and cybersecurity documents."
                    ),
                    func=search_scm_documents,
                ),
                FunctionTool(
                    name="get_user_count",
                    description=(
                        "Count users in the application's PostgreSQL database."
                    ),
                    func=get_user_count,
                ),
                FunctionTool(
                    name="get_weather",
                    description=(
                        "Get current weather for a city or location."
                    ),
                    func=get_weather,
                ),
            ]

            print("[MAF INIT] Registered tools:")
            print("  ├── search_scm_documents → Azure AI Search")
            print("  ├── get_user_count       → PostgreSQL")
            print("  └── get_weather          → Weather API")

            self._agent = Agent(
                client=client,
                instructions=AGENT_INSTRUCTIONS,
                tools=tools,
            )

            print("[MAF INIT] Agent initialized successfully")
            print("=" * 80)

        return self._agent

    async def chat(self, message: str) -> dict[str, Any]:

        start_time = time.perf_counter()

        print("\n")
        print("=" * 80)
        print("[MAF REQUEST] NEW USER REQUEST")
        print("=" * 80)
        print(f"[MAF REQUEST] User query: {message}")
        print("[MAF REQUEST] Sending query to MAF agent...")
        print("[MAF REQUEST] Agent will decide which tool(s) to use.")

        try:

            result = await self.agent.run(message)

            elapsed = time.perf_counter() - start_time

            print("\n" + "-" * 80)
            print("[MAF RESPONSE] AGENT EXECUTION COMPLETED")
            print("-" * 80)
            print(f"[MAF RESPONSE] Response ID: {result.response_id}")
            print(f"[MAF RESPONSE] Total duration: {elapsed:.2f}s")
            print(f"[MAF RESPONSE] Answer: {result.text}")
            print("=" * 80)

            return {
                "response_id": result.response_id,
                "answer": result.text,
            }

        except RuntimeError:
            print("[MAF ERROR] Runtime error")
            raise

        except Exception as exc:

            elapsed = time.perf_counter() - start_time

            print("\n" + "=" * 80)
            print("[MAF ERROR] AGENT EXECUTION FAILED")
            print(f"[MAF ERROR] Duration: {elapsed:.2f}s")
            print(f"[MAF ERROR] Error: {exc}")
            print("=" * 80)

            raise RuntimeError(
                "The assistant is temporarily unavailable. Please try again."
            ) from exc