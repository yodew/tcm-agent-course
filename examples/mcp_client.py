# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp>=1.12,<2"]
# ///
# Run from the repository: uv run --extra mcp python examples/mcp_client.py
"""Initialize, discover and call a real stdio MCP server."""

import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


async def main() -> None:
    """A real subprocess round trip, not a mocked tool list."""
    parameters = StdioServerParameters(command=sys.executable, args=["examples/mcp_server.py"])
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        print("tools:", [tool.name for tool in tools.tools])
        result = await session.call_tool("search_public_knowledge", {"query": "四诊"})
        for content in result.content:
            if isinstance(content, TextContent):
                print(content.text)


if __name__ == "__main__":
    anyio.run(main)
