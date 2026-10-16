"""Small, inspectable retrieval evaluation; results are not clinical evidence."""

import json
from pathlib import Path

import anyio
from pydantic import Field, TypeAdapter

from tcm_agent.config import Settings
from tcm_agent.domain import Contract
from tcm_agent.embeddings import ProviderEmbedder
from tcm_agent.http_client import create_client
from tcm_agent.retrieval import KnowledgeBase


class RetrievalCase(Contract):
    query: str
    relevant_ids: list[str] = Field(min_length=1)


class CaseResult(Contract):
    query: str
    found: list[str]
    recall_at_4: float
    mrr_at_4: float


async def evaluate_retrieval(output: Path) -> None:
    """Compute macro recall@4 and MRR@4 with explicit denominators."""
    settings = Settings()
    knowledge = KnowledgeBase.load(settings.knowledge_path)
    raw = await anyio.Path("knowledge/eval.json").read_bytes()
    cases = TypeAdapter(list[RetrievalCase]).validate_json(raw)
    details: list[CaseResult] = []
    async with create_client() as client:
        if settings.embedding_model:
            knowledge = await knowledge.with_embeddings(ProviderEmbedder(settings, client))
        for case in cases:
            found = [e.entry_id for e in await knowledge.search(case.query)]
            relevant = set(case.relevant_ids)
            recall = len(relevant.intersection(found)) / len(relevant)
            reciprocal = next(
                (1 / rank for rank, entry in enumerate(found, 1) if entry in relevant), 0.0
            )
            details.append(
                CaseResult(query=case.query, found=found, recall_at_4=recall, mrr_at_4=reciprocal)
            )
    await anyio.Path(output.parent).mkdir(parents=True, exist_ok=True)
    report = {
        "mode": "hybrid" if settings.embedding_model else "bm25",
        "samples": len(cases),
        "recall_at_4": sum(d.recall_at_4 for d in details) / len(cases),
        "mrr_at_4": sum(d.mrr_at_4 for d in details) / len(cases),
        "cases": [d.model_dump(mode="json") for d in details],
        "scope": "Original educational corpus only; no clinical validation",
    }
    await anyio.Path(output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
