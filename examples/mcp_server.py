# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp>=1.12,<2", "tcm-agent-course"]
# [tool.uv.sources]
# tcm-agent-course = { path = "..", editable = true }
# ///
# Run from the repository: uv run --extra mcp python examples/mcp_server.py
"""Read-only stdio MCP server; deliberately exposes no private visit records."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from tcm_agent.retrieval import KnowledgeBase

server = FastMCP("tcm-public-knowledge")
knowledge = KnowledgeBase.load(Path("knowledge/entries.json"))


@server.tool()
async def search_public_knowledge(query: str) -> str:
    """Search original educational entries, never patient data or medical diagnoses."""
    bounded = query[:300]
    entries = await knowledge.search(bounded)
    return "[" + ",".join(entry.model_dump_json() for entry in entries) + "]"


if __name__ == "__main__":
    server.run(transport="stdio")
