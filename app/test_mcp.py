import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    url = "http://127.0.0.1:8001/mcp"

    print(f"[TEST] Connecting to MCP server: {url}")

    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            print("[TEST] MCP connection established")

            result = await session.list_tools()

            print("\n[TEST] Available MCP tools:")

            for tool in result.tools:
                print(f"  - {tool.name}")
                print(f"    Description: {tool.description}")
                print(f"    Input: {tool.inputSchema}")

            print("\n[TEST] MCP server test completed successfully")


if __name__ == "__main__":
    asyncio.run(main())