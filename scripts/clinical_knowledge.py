# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python scripts/clinical_knowledge.py audit
"""Inspect the research pack without calling a model or changing the active service."""

import json
from pathlib import Path
from typing import Annotated, Final

import typer

from tcm_agent.clinical.contracts import (
    Association,
    CandidateCard,
    CollectionReceipt,
    KnowledgeAudit,
    LiteratureCard,
    Observation,
    Question,
    Source,
    Term,
)
from tcm_agent.clinical.store import ResearchKnowledge

ROOT: Final = Path(__file__).resolve().parents[1]
app = typer.Typer(help="Clinical research knowledge; clinical inference is disabled")


@app.command()
def audit() -> None:
    """Validate references, IDs and dependency graph, then report actual inventory."""
    pack = ResearchKnowledge.load(ROOT / "knowledge/clinical")
    print(pack.audit().model_dump_json(indent=2))


@app.command()
def questions(
    profile: str = "sleep", limit: Annotated[int, typer.Option(min=1, max=100)] = 12
) -> None:
    """Preview an engineering queue with a purpose for each question, not patient triage."""
    pack = ResearchKnowledge.load(ROOT / "knowledge/clinical")
    rows = pack.preview_questions(profile, frozenset())[:limit]
    print(
        json.dumps(
            {
                "clinical_use": "disabled",
                "profile": profile,
                "questions": [q.model_dump() for q in rows],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def search(query: Annotated[str, typer.Option()]) -> None:
    """Search terms literally and return provenance; do not produce a diagnosis."""
    rows = ResearchKnowledge.load(ROOT / "knowledge/clinical").search_terms(query)
    print(json.dumps([row.model_dump() for row in rows], ensure_ascii=False, indent=2))


@app.command()
def schemas() -> None:
    """Export integration contracts for the next face/tongue/pulse samples."""
    directory = ROOT / "knowledge/clinical/schema"
    contracts = (
        Observation,
        Question,
        Term,
        Source,
        LiteratureCard,
        Association,
        CandidateCard,
        CollectionReceipt,
        KnowledgeAudit,
    )
    for contract in contracts:
        (directory / (contract.__name__ + ".schema.json")).write_text(
            json.dumps(contract.model_json_schema(), ensure_ascii=False, indent=2) + "\n"
        )
    print(f"{len(contracts)} JSON Schemas exported")


if __name__ == "__main__":
    app()
