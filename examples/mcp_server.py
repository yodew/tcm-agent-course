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

from tcm_agent.clinical.documents import DocumentKind
from tcm_agent.clinical.index import ClinicalIndex
from tcm_agent.retrieval import KnowledgeBase

server = FastMCP("tcm-public-knowledge")
ROOT = Path(__file__).resolve().parents[1]
knowledge = KnowledgeBase.load(ROOT / "knowledge/entries.json")
clinical = ClinicalIndex(ROOT / "knowledge/clinical", ROOT / "data/clinical-index.sqlite")


@server.tool()
async def search_public_knowledge(query: str) -> str:
    """Search original educational entries, never patient data or medical diagnoses."""
    bounded = query[:300]
    entries = await knowledge.search(bounded)
    return "[" + ",".join(entry.model_dump_json() for entry in entries) + "]"


@server.tool()
def search_clinical_references(query: str, kind: DocumentKind | None = None, limit: int = 5) -> str:
    """Search TCM research evidence with citations; co-occurrence is not diagnostic criteria.

    Build first: uv run python scripts/clinical_knowledge.py build-index.
    Each result declares evidence kind, source limitations and disabled clinical use.
    Retrieval relevance is not diagnostic probability. No private visit data is searched.
    """
    hits = clinical.search(query, kind=kind, limit=limit)
    return "[" + ",".join(hit.model_dump_json() for hit in hits) + "]"


@server.tool()
def get_clinical_document(document_id: str) -> str:
    """Resolve an evidence ID to the full research document and source locators."""
    document = clinical.document(document_id)
    return document.model_dump_json() if document else "null"


if __name__ == "__main__":
    server.run(transport="stdio")
