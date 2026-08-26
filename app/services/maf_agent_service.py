import time
from typing import Any

import requests
from agent_framework.openai import OpenAIChatClient

from app.config import settings
from app.database.database import SessionLocal
from app.models.user import User
from agent_framework import (
    Agent,
    AgentSession,
    ContextProvider,
    FunctionTool,
    MCPStreamableHTTPTool,
    SessionContext,
)


# ---------------------------------------------------------------------------
# MAF Agent Instructions
# ---------------------------------------------------------------------------

AGENT_INSTRUCTIONS = """
You are an enterprise Supply Chain Management assistant.

You are responsible for understanding the user's request and deciding
which available tool or tools should be used.

You have access to the following capabilities:

1. search_scm_documents

   This tool is provided through an MCP server.

   Use it for SCM-related information contained in the organization's
   procurement, inventory, purchasing, warehouse, logistics, supplier,
   vendor management, and other SCM documentation.

   Examples:
   - Procurement process
   - Purchase requisition
   - Purchase order
   - Approval levels
   - Inventory
   - Vendor management
   - Warehouse
   - Logistics
   - Supply chain procedures

2. get_user_count

   Use this when the user asks about the number of users registered
   in the application database.

3. get_weather

   Use this when the user asks for current weather information.

Tool selection rules:

- Always use the appropriate tool when information must come from
  an external data source.
- Do not invent information.
- Do not answer SCM document-related questions from general knowledge
  when the SCM document search tool should be used.
- If a request requires multiple sources, use multiple tools.
- After receiving tool results, provide a concise and accurate
  natural-language response.
- Do not expose internal tool names, implementation details,
  API keys, or system configuration to the user.
""".strip()


# ---------------------------------------------------------------------------
# SCM Document Search Tool
# ---------------------------------------------------------------------------

def search_scm_documents(query: str) -> str:
    """
    Search SCM documents through the configured MCP/Foundry service.
    """

    start_time = time.perf_counter()

    print("\n[MAF TOOL SELECTED] search_scm_documents")
    print(f"[MAF TOOL INPUT] query: {query}")

    try:
        # The SCM search implementation is handled by FoundryService.
        #
        # MAF sees this capability through the MCP tool registered below.
        # This function is retained here as the underlying application-level
        # implementation/reference for SCM document search.

        foundry_service = FoundryService(
            endpoint=settings.foundry_project_endpoint,
            agent_name=settings.foundry_agent_name,
        )

        documents = foundry_service.chat(query)

        elapsed = time.perf_counter() - start_time

        if not documents:
            print(
                "[MAF TOOL RESULT] search_scm_documents | "
                f"documents_found=0 | duration={elapsed:.2f}s"
            )

            return "No relevant SCM documents were found."

        print(
            "[MAF TOOL RESULT] search_scm_documents | "
            f"documents_found={len(documents)} | "
            f"duration={elapsed:.2f}s"
        )

        # Do not print document contents to the terminal.
        #
        # The result is returned to the calling agent/tool layer.
        #
        # If your MCP server is responsible for formatting the result,
        # keep the MCP implementation as the source of truth.

        return documents

    except Exception as exc:
        elapsed = time.perf_counter() - start_time

        print(
            "[MAF TOOL ERROR] search_scm_documents | "
            f"duration={elapsed:.2f}s | "
            f"error={exc}"
        )

        return "SCM document search is currently unavailable."


# ---------------------------------------------------------------------------
# PostgreSQL User Count Tool
# ---------------------------------------------------------------------------

def get_user_count() -> str:
    """
    Return the number of registered users in the application database.
    """

    start_time = time.perf_counter()

    print("\n[MAF TOOL SELECTED] get_user_count")

    db = SessionLocal()

    try:
        count = db.query(User).count()

        elapsed = time.perf_counter() - start_time

        print(
            "[MAF TOOL RESULT] get_user_count | "
            f"count={count} | "
            f"duration={elapsed:.2f}s"
        )

        return f"There are currently {count} registered users."

    except Exception as exc:
        elapsed = time.perf_counter() - start_time

        print(
            "[MAF TOOL ERROR] get_user_count | "
            f"duration={elapsed:.2f}s | "
            f"error={exc}"
        )

        return "The user count is currently unavailable."

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Weather Tool
# ---------------------------------------------------------------------------

def get_weather(city: str) -> str:
    """
    Retrieve current weather information for a city from WeatherAPI.com.
    """

    start_time = time.perf_counter()

    print("\n[MAF TOOL SELECTED] get_weather")
    print(f"[MAF TOOL INPUT] city: {city}")

    if not settings.weather_api_key:
        print(
            "[MAF TOOL WARNING] Weather API key is not configured"
        )

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

        # WeatherAPI returns 400 when the location cannot be found.
        if response.status_code == 400:
            print(
                "[MAF TOOL RESULT] get_weather | "
                f"city={city} | location_not_found"
            )

            return (
                f"Weather information could not be found for {city}."
            )

        response.raise_for_status()

        payload = response.json()

        current = payload["current"]
        location = payload.get("location", {})

        elapsed = time.perf_counter() - start_time

        print(
            "[MAF TOOL RESULT] get_weather | "
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
            "[MAF TOOL ERROR] get_weather | "
            f"city={city} | "
            f"duration={elapsed:.2f}s | "
            f"error={exc}"
        )

        return "Weather information is currently unavailable."

    except (KeyError, TypeError, ValueError) as exc:
        elapsed = time.perf_counter() - start_time

        print(
            "[MAF TOOL ERROR] get_weather | "
            f"city={city} | "
            f"duration={elapsed:.2f}s | "
            f"error={exc}"
        )

        return "Weather information is currently unavailable."


# ---------------------------------------------------------------------------
# Context Provider / Memory
# ---------------------------------------------------------------------------

class UserMemoryProvider(ContextProvider):
    """
    Simple Microsoft Agent Framework memory provider.

    Stores user-specific information inside AgentSession.state
    and injects that information into future agent runs.

    Current POC memory:
        user_name

    Example:

        User:
            My name is Vaishnavi.

        Later:

        User:
            What is my name?

        Agent:
            Your name is Vaishnavi.
    """

    DEFAULT_SOURCE_ID = "user_memory"

    def __init__(self) -> None:
        super().__init__(self.DEFAULT_SOURCE_ID)

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession | None,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """
        Runs before the agent execution.

        Reads previously stored memory and injects useful context
        into the current agent execution.
        """

        memory = state.get(self.source_id, {})

        user_name = memory.get("user_name")

        if user_name:
            context.extend_instructions(
                self.source_id,
                (
                    f"The user's name is {user_name}. "
                    "Use their name naturally when appropriate."
                ),
            )

            print(
                f"[MAF MEMORY] Injected user name: {user_name}"
            )

    async def after_run(
        self,
        *,
        agent: Any,
        session: AgentSession | None,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """
        Runs after the agent execution.

        Looks for a simple 'my name is ...' statement in the
        user's input and stores the name in session state.
        """

        for message in context.input_messages:

            text = (
                message.text
                if hasattr(message, "text")
                else ""
            )

            if not isinstance(text, str):
                continue

            lower_text = text.lower()

            if "my name is" not in lower_text:
                continue

            name_part = lower_text.split(
                "my name is",
                1,
            )[1].strip()

            if not name_part:
                continue

            name = name_part.split()[0].strip(
                ".,!?"
            )

            if name:
                memory = state.setdefault(
                    self.source_id,
                    {},
                )

                memory["user_name"] = name.capitalize()

                print(
                    "[MAF MEMORY] Stored user name: "
                    f"{memory['user_name']}"
                )


# ---------------------------------------------------------------------------
# MAF Agent Service
# ---------------------------------------------------------------------------

class MafAgentService:
    """
    Microsoft Agent Framework orchestration service.

    Responsibilities:

    1. Initialize the MAF Agent.
    2. Configure the Foundry OpenAI-compatible client.
    3. Register application tools.
    4. Register the SCM MCP server.
    5. Register ContextProvider / memory.
    6. Create and reuse AgentSession instances.
    7. Execute user requests through the MAF agent.
    """

    def __init__(self) -> None:

        # Agent is initialized lazily.
        self._agent: Agent | None = None

        # -------------------------------------------------------------------
        # In-memory session store for the POC.
        #
        # Important:
        #
        # The UI must send the same session_id for every turn of a
        # conversation.
        #
        # Example:
        #
        # First request:
        #     session_id = abc123
        #
        # Second request:
        #     session_id = abc123
        #
        # Third request:
        #     session_id = abc123
        #
        # This allows the same AgentSession object to be reused.
        #
        # Production:
        #     Replace this with a persistent SessionStore,
        #     Redis, PostgreSQL, etc.
        # -------------------------------------------------------------------

        self._sessions: dict[str, AgentSession] = {}

    # -----------------------------------------------------------------------
    # Agent Initialization
    # -----------------------------------------------------------------------

    @property
    def agent(self) -> Agent:

        if self._agent is None:

            print("\n" + "=" * 80)
            print(
                "[MAF INIT] Initializing Microsoft Agent Framework"
            )
            print("=" * 80)

            # ---------------------------------------------------------------
            # Validate Foundry configuration
            # ---------------------------------------------------------------

            if not settings.foundry_api_key:
                raise RuntimeError(
                    "FOUNDRY_API_KEY is not configured."
                )

            if not settings.foundry_model:
                raise RuntimeError(
                    "FOUNDRY_MODEL is not configured."
                )

            if not settings.foundry_project_endpoint:
                raise RuntimeError(
                    "FOUNDRY_PROJECT_ENDPOINT is not configured."
                )

            print(
                f"[MAF INIT] Model: "
                f"{settings.foundry_model}"
            )

            print(
                "[MAF INIT] Creating Foundry "
                "OpenAI-compatible client..."
            )

            # ---------------------------------------------------------------
            # Foundry OpenAI-compatible client
            # ---------------------------------------------------------------

            client = OpenAIChatClient(
                api_key=settings.foundry_api_key,
                base_url=(
                    f"{settings.foundry_project_endpoint}"
                    f"/api/projects/"
                    f"SCM-RAG-Knowledge-Assistant"
                    f"/openai/v1"
                ),
                model=settings.foundry_model,
            )

            # ---------------------------------------------------------------
            # MCP Tool
            # ---------------------------------------------------------------

            if not settings.mcp_server_url:
                raise RuntimeError(
                    "MCP_SERVER_URL is not configured."
                )

            print(
                "[MAF INIT] Creating MCP SCM tool..."
            )

            mcp_tool = MCPStreamableHTTPTool(
                name="SCM MCP Server",
                url=settings.mcp_server_url,
                allowed_tools=[
                    "search_scm_documents"
                ],
                description=(
                    "MCP server providing access to the "
                    "organization's SCM documentation."
                ),
            )

            # ---------------------------------------------------------------
            # Application Tools
            # ---------------------------------------------------------------

            tools = [

                # PostgreSQL
                FunctionTool(
                    name="get_user_count",
                    description=(
                        "Count users in the application's "
                        "PostgreSQL database."
                    ),
                    func=get_user_count,
                ),

                # Weather API
                FunctionTool(
                    name="get_weather",
                    description=(
                        "Get current weather for a city or location."
                    ),
                    func=get_weather,
                ),

                # SCM MCP Server
                #
                # search_scm_documents is exposed by the MCP server.
                mcp_tool,
            ]

            print(
                "[MAF INIT] Registered tools:"
            )

            print(
                "  ├── search_scm_documents "
                "→ MCP Server → Azure AI Search"
            )

            print(
                "  ├── get_user_count "
                "→ PostgreSQL"
            )

            print(
                "  └── get_weather "
                "→ Weather API"
            )

            print(
                "[MAF INIT] MCP server: "
                f"{settings.mcp_server_url}"
            )

            # ---------------------------------------------------------------
            # Context Provider
            # ---------------------------------------------------------------

            memory_provider = UserMemoryProvider()

            print(
                "[MAF INIT] Registered context providers:"
            )

            print(
                "  └── user_memory "
                "→ AgentSession state"
            )

            # ---------------------------------------------------------------
            # Create MAF Agent
            # ---------------------------------------------------------------

            self._agent = Agent(
                client=client,
                instructions=AGENT_INSTRUCTIONS,
                tools=tools,
                context_providers=[
                    memory_provider
                ],
            )

            print(
                "[MAF INIT] Agent initialized successfully"
            )

            print("=" * 80)

        return self._agent

    # -----------------------------------------------------------------------
    # Session Management
    # -----------------------------------------------------------------------

    def _get_or_create_session(
        self,
        session_id: str | None,
    ) -> tuple[str, AgentSession]:

        # -------------------------------------------------------------------
        # Case 1:
        # No session ID supplied.
        #
        # Create a completely new session.
        # -------------------------------------------------------------------

        if not session_id:

            session = self.agent.create_session()

            session_id = session.session_id

            self._sessions[session_id] = session

            print(
                "[MAF SESSION] Created new session: "
                f"{session_id}"
            )

            return session_id, session

        # -------------------------------------------------------------------
        # Case 2:
        # Session already exists in this FastAPI process.
        #
        # Reuse the SAME AgentSession object.
        # -------------------------------------------------------------------

        session = self._sessions.get(session_id)

        if session is not None:

            print(
                "[MAF SESSION] Reusing existing session: "
                f"{session_id}"
            )

            return session_id, session

        # -------------------------------------------------------------------
        # Case 3:
        # UI supplied a session ID, but this process does not have the
        # corresponding AgentSession object.
        #
        # For the current POC:
        #
        # Recreate the session using the supplied ID.
        #
        # IMPORTANT:
        #
        # Recreating the session with the same ID does NOT restore the
        # previous conversation history if the process lost the session.
        #
        # For production, persist AgentSession state externally.
        # -------------------------------------------------------------------

        session = self.agent.create_session(
            session_id=session_id
        )

        self._sessions[session_id] = session

        print(
            "[MAF SESSION] Recreated session using supplied ID: "
            f"{session_id}"
        )

        return session_id, session

    # -----------------------------------------------------------------------
    # Chat
    # -----------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        print("\n")
        print("=" * 80)
        print("[MAF REQUEST] NEW USER REQUEST")
        print("=" * 80)

        print(
            f"[MAF REQUEST] User query: {message}"
        )

        print(
            "[MAF REQUEST] Session ID before: "
            f"{session_id}"
        )

        # ---------------------------------------------------------------
        # Retrieve or create AgentSession
        # ---------------------------------------------------------------

        session_id, session = (
            self._get_or_create_session(
                session_id
            )
        )

        print(
            "[MAF REQUEST] Session ID: "
            f"{session_id}"
        )

        print(
            "[MAF REQUEST] Sending query to MAF agent..."
        )

        print(
            "[MAF REQUEST] Agent will decide "
            "which tool(s) to use."
        )

        # ---------------------------------------------------------------
        # Execute Agent
        # ---------------------------------------------------------------

        try:

            result = await self.agent.run(
                message,
                session=session,
            )

            elapsed = time.perf_counter() - start_time

            print("\n" + "-" * 80)
            print(
                "[MAF RESPONSE] "
                "AGENT EXECUTION COMPLETED"
            )
            print("-" * 80)

            print(
                "[MAF RESPONSE] Session ID: "
                f"{session_id}"
            )

            print(
                "[MAF RESPONSE] Response ID: "
                f"{result.response_id}"
            )

            print(
                "[MAF RESPONSE] Total duration: "
                f"{elapsed:.2f}s"
            )

            print(
                "[MAF RESPONSE] Answer: "
                f"{result.text}"
            )

            # ---------------------------------------------------------------
            # Debug memory during POC
            # ---------------------------------------------------------------

            memory_state = session.state.get(
                "user_memory",
                {},
            )

            if memory_state:

                print(
                    "[MAF MEMORY] Session state: "
                    f"{memory_state}"
                )

            print("=" * 80)

            return {
                "response_id": result.response_id,
                "session_id": session_id,
                "answer": result.text,
            }

        except RuntimeError:

            print(
                "[MAF ERROR] Runtime error"
            )

            raise

        except Exception as exc:

            elapsed = time.perf_counter() - start_time

            print("\n" + "=" * 80)

            print(
                "[MAF ERROR] "
                "AGENT EXECUTION FAILED"
            )

            print(
                "[MAF ERROR] Duration: "
                f"{elapsed:.2f}s"
            )

            print(
                "[MAF ERROR] Error: "
                f"{exc}"
            )

            print("=" * 80)

            raise RuntimeError(
                "The assistant is temporarily unavailable. "
                "Please try again."
            ) from exc