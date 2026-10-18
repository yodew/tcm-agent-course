# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp>=1.12,<2", "tcm-agent-course"]
# [tool.uv.sources]
# tcm-agent-course = { path = "..", editable = true }
# ///
# Build first: uv run python scripts/clinical_knowledge.py build-index
# Run: uv run --extra mcp python examples/clinical_mcp_client.py
"""Exercise actual research retrieval and citation resolution over MCP stdio."""

import sys
from pathlib import Path
from typing import Final

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent
from pydantic import TypeAdapter

from tcm_agent.clinical.documents import KnowledgeDocument, SearchHit

ROOT: Final = Path(__file__).resolve().parents[1]


async def main() -> None:
    """Verify tool discovery, typed retrieval and exact citation resolution."""
    parameters = StdioServerParameters(
        command=sys.executable, args=[str(ROOT / "examples/mcp_server.py")]
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        names = {tool.name for tool in (await session.list_tools()).tools}
        assert {"search_clinical_references", "get_clinical_document"} <= names
        result = await session.call_tool(
            "search_clinical_references",
            {"query": "心脾两虚", "kind": "literature_reference", "limit": 1},
        )
        assert not result.isError
        content = TextContent.model_validate(result.content[0])
        hits = TypeAdapter(list[SearchHit]).validate_json(content.text)
        assert len(hits) == 1
        assert "心脾两虚" in hits[0].document.title
        resolved = await session.call_tool(
            "get_clinical_document", {"document_id": hits[0].document.document_id}
        )
        assert not resolved.isError
        document = KnowledgeDocument.model_validate_json(
            TextContent.model_validate(resolved.content[0]).text
        )
        assert document == hits[0].document
        print("PASS: MCP discovery → indexed retrieval → exact evidence resolution")
        print(document.document_id, document.title)
        print("source:", document.references[0].source.url)
        print("clinical_use:", document.clinical_use)


if __name__ == "__main__":
    anyio.run(main)
