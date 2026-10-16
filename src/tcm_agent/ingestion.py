"""Administrator-controlled Markdown ingestion with provenance and stable chunk IDs."""

import hashlib
import json
from pathlib import Path

from pydantic import Field, TypeAdapter

from tcm_agent.domain import Contract
from tcm_agent.errors import DataContractError
from tcm_agent.retrieval import KnowledgeEntry


class SourceSpec(Contract):
    path: Path
    title: str
    source_url: str
    version: str
    license: str = Field(min_length=1)
    approved: bool


def chunk_text(text: str, size: int = 600, overlap: int = 80) -> list[str]:
    """Bound by characters, not tokens; repeat context only within the same document."""
    if size <= overlap or overlap < 0:
        raise DataContractError("Chunk size must exceed nonnegative overlap")
    text = text.strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind("\n\n", start + size // 2, end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def ingest(manifest: Path, destination: Path) -> int:
    """License approval is administrator input, not something a model can grant."""
    specs = TypeAdapter(list[SourceSpec]).validate_json(manifest.read_bytes())
    entries: list[KnowledgeEntry] = []
    for spec in specs:
        if not spec.approved:
            continue
        text = (manifest.parent / spec.path).read_text(encoding="utf-8")
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
        for index, chunk in enumerate(chunk_text(text)):
            identity = hashlib.sha256(
                f"{spec.source_url}|{spec.version}|{content_hash}|{index}".encode()
            ).hexdigest()[:24]
            entries.append(
                KnowledgeEntry(
                    entry_id=identity,
                    title=spec.title,
                    text=chunk,
                    source_url=spec.source_url,
                    version=f"{spec.version}:{content_hash}",
                    license=spec.license,
                    approved=True,
                )
            )
    if len({entry.entry_id for entry in entries}) != len(entries):
        raise DataContractError("Duplicate manifest source/version")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps([e.model_dump(mode="json") for e in entries], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return len(entries)
