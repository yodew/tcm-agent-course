"""Deterministic Chinese-aware BM25 baseline, with optional real dense fusion."""

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import Field, TypeAdapter

from tcm_agent.domain import Contract, Evidence
from tcm_agent.errors import DataContractError


class KnowledgeEntry(Contract):
    entry_id: str
    title: str
    text: str = Field(min_length=1, max_length=1200)
    source_url: str
    version: str
    license: str
    approved: bool


class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return real provider embeddings in input order."""
        ...


def tokenize(text: str) -> list[str]:
    """Use Chinese uni/bigrams plus English words; not claimed to be semantic."""
    runs = [match.group() for match in re.finditer(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", text.lower())]
    terms: list[str] = []
    for run in runs:
        if run.isascii():
            terms.append(run)
        else:
            terms.extend(run)
            terms.extend(run[i : i + 2] for i in range(len(run) - 1))
    return terms


@dataclass(frozen=True, slots=True)
class KnowledgeBase:
    entries: tuple[KnowledgeEntry, ...]
    vectors: tuple[tuple[float, ...], ...] = ()
    embedder: Embedder | None = None

    @classmethod
    def load(cls, path: Path) -> "KnowledgeBase":
        """Only explicitly approved, licensed and uniquely identified entries enter search."""
        entries = TypeAdapter(list[KnowledgeEntry]).validate_json(path.read_bytes())
        approved = tuple(e for e in entries if e.approved and e.license.strip())
        if len({e.entry_id for e in approved}) != len(approved):
            raise DataContractError("Duplicate knowledge entry IDs")
        return cls(approved)

    async def with_embeddings(self, embedder: Embedder) -> "KnowledgeBase":
        """Build a small-corpus dense index with the same model used for queries."""
        vectors = await embedder.embed([e.title + "\n" + e.text for e in self.entries])
        return KnowledgeBase(self.entries, tuple(tuple(v) for v in vectors), embedder)

    def sparse(self, query: str) -> list[tuple[int, float]]:
        """BM25 k1=1.2, b=0.75, computed transparently for this bounded corpus."""
        if not self.entries:
            return []
        docs = [Counter(tokenize(e.title + " " + e.text)) for e in self.entries]
        avg = sum(sum(d.values()) for d in docs) / len(docs)
        scored: list[tuple[int, float]] = []
        for index, doc in enumerate(docs):
            score = 0.0
            for term in set(tokenize(query)):
                df = sum(term in d for d in docs)
                tf = doc[term]
                idf = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
                score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * sum(doc.values()) / avg))
            if score > 0:
                scored.append((index, score))
        return sorted(scored, key=lambda x: (-x[1], x[0]))

    async def search(self, query: str) -> list[Evidence]:
        """RRF uses rank, not incomparable sparse and dense score magnitudes."""
        sparse = self.sparse(query)
        ranks = [sparse]
        if self.embedder is not None and self.vectors:
            query_vector = (await self.embedder.embed([query]))[0]
            dense = sorted(
                ((i, cosine(query_vector, list(v))) for i, v in enumerate(self.vectors)),
                key=lambda x: -x[1],
            )
            ranks.append(dense[:10])
        scores: dict[int, float] = {}
        for ranking in ranks:
            for rank, (index, _) in enumerate(ranking[:10], start=1):
                scores[index] = scores.get(index, 0.0) + 1 / (60 + rank)
        return [
            Evidence(
                entry_id=self.entries[i].entry_id,
                title=self.entries[i].title,
                text=self.entries[i].text,
                source_url=self.entries[i].source_url,
                version=self.entries[i].version,
                license=self.entries[i].license,
                score=score,
            )
            for i, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:4]
        ]


def cosine(left: list[float], right: list[float]) -> float:
    """Reject dimension drift instead of silently truncating zip."""
    if len(left) != len(right) or not left:
        raise DataContractError("Embedding dimension mismatch")
    denominator = math.sqrt(sum(v * v for v in left) * sum(v * v for v in right))
    return (
        sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 0.0
    )
