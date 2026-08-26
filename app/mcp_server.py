import json
import time

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.services.foundry_service import FoundryService


mcp = FastMCP(
    name="SCM Knowledge MCP Server"
)


@mcp.tool()
def search_scm_documents(query: str) -> str:
    """
    Search the organization's SCM documentation.

    Use this for procurement, inventory, purchasing,
    warehouse, logistics, and other SCM-related questions.
    """

    start_time = time.perf_counter()

    print("\n[MCP TOOL CALLED] search_scm_documents")
    print(f"[MCP TOOL INPUT] query: {query}")

    try:
        foundry_service = FoundryService(
            endpoint=settings.foundry_project_endpoint,
            agent_name=settings.foundry_agent_name,
        )

        documents = foundry_service.chat(query)

        elapsed = time.perf_counter() - start_time

        if not documents:
            print(
                "[MCP TOOL RESULT] search_scm_documents | "
                f"documents_found=0 | duration={elapsed:.2f}s"
            )

            return "No relevant SCM documents were found."

        print(
            "[MCP TOOL RESULT] search_scm_documents | "
            f"documents_found={len(documents)} | "
            f"duration={elapsed:.2f}s"
        )

        # Convert the result into text that can safely travel
        # through MCP.
        if isinstance(documents, str):
            return documents

        return json.dumps(
            documents,
            ensure_ascii=False,
            default=str,
        )

    except Exception as exc:

        elapsed = time.perf_counter() - start_time

        print(
            "[MCP TOOL ERROR] search_scm_documents | "
            f"duration={elapsed:.2f}s | error={exc}"
        )

        return "SCM document search is currently unavailable."


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        mcp.streamable_http_app(),
        host="127.0.0.1",
        port=8001,
    )