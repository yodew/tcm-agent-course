"""Persistent, local Chinese lexical retrieval with explicit provenance and freshness."""

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, Literal

from pydantic import TypeAdapter

from tcm_agent.clinical.documents import (
    DocumentKind,
    KnowledgeDocument,
    SearchHit,
    compile_documents,
    document_fingerprint,
)
from tcm_agent.clinical.store import ResearchKnowledge
from tcm_agent.domain import Contract
from tcm_agent.errors import DataContractError
from tcm_agent.retrieval import tokenize

INDEX_VERSION: Final = "clinical-fts5-v1"


class IndexManifest(Contract):
    index_version: str = INDEX_VERSION
    document_count: int
    content_sha256: str
    retrieval: str = "SQLite FTS5 BM25; Chinese bigrams and single-character fallback"
    clinical_inference_enabled: Literal[False] = False


def build_index(directory: Path, destination: Path) -> IndexManifest:
    """Build completely in a sibling temporary directory, then atomically replace."""
    documents = compile_documents(ResearchKnowledge.load(directory))
    manifest = IndexManifest(
        document_count=len(documents), content_sha256=document_fingerprint(documents)
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as temporary:
        staged = Path(temporary) / "index.sqlite"
        with closing(sqlite3.connect(staged)) as connection, connection:
            connection.execute("CREATE TABLE metadata (payload TEXT NOT NULL)")
            connection.execute("INSERT INTO metadata VALUES (?)", (manifest.model_dump_json(),))
            connection.execute(
                "CREATE VIRTUAL TABLE documents USING fts5("
                "document_id UNINDEXED, kind UNINDEXED, payload UNINDEXED, title, body)"
            )
            connection.executemany(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        doc.document_id,
                        doc.kind,
                        doc.model_dump_json(),
                        " ".join(tokenize(doc.title)),
                        " ".join(tokenize(doc.text)),
                    )
                    for doc in documents
                ],
            )
        staged.replace(destination)
    return manifest


def query_expression(query: str) -> str:
    """Never interpolate raw FTS syntax; prefer bigrams to reduce shared-character noise."""
    terms = set(tokenize(query))
    preferred = {term for term in terms if len(term) > 1}
    return " OR ".join('"' + term + '"' for term in sorted(preferred or terms))


@dataclass(frozen=True, slots=True)
class ClinicalIndex:
    directory: Path
    path: Path

    def manifest(self) -> IndexManifest:
        """Reject missing, obsolete or changed indexes instead of returning stale evidence."""
        if not self.path.is_file():
            raise DataContractError("Clinical index missing; run clinical_knowledge.py build-index")
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            raw = TypeAdapter(tuple[str]).validate_python(
                db.execute("SELECT payload FROM metadata").fetchone()
            )[0]
        manifest = IndexManifest.model_validate_json(raw)
        current = compile_documents(ResearchKnowledge.load(self.directory))
        if (
            manifest.index_version != INDEX_VERSION
            or manifest.content_sha256 != document_fingerprint(current)
            or manifest.document_count != len(current)
        ):
            raise DataContractError("Clinical index stale; rebuild before retrieval")
        return manifest

    def search(
        self, query: str, *, kind: DocumentKind | None = None, limit: int = 5
    ) -> list[SearchHit]:
        """Return bounded research evidence; rank is lexical relevance, never confidence."""
        if not 1 <= limit <= 20 or not query.strip() or len(query) > 300:
            raise DataContractError("Query must contain 1-300 characters; limit must be 1-20")
        self.manifest()
        expression = query_expression(query)
        if not expression:
            return []
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            rows = TypeAdapter(list[tuple[str, float]]).validate_python(
                db.execute(
                    "SELECT payload, bm25(documents, 0, 0, 0, 4, 1) AS rank "
                    "FROM documents WHERE documents MATCH ? AND (? IS NULL OR kind = ?) "
                    "ORDER BY rank, document_id LIMIT ?",
                    (expression, kind, kind, limit),
                ).fetchall()
            )
        return [
            SearchHit(document=KnowledgeDocument.model_validate_json(payload), relevance=-rank)
            for payload, rank in rows
        ]

    def document(self, document_id: str) -> KnowledgeDocument | None:
        """Resolve a stable citation ID to its full document and original references."""
        self.manifest()
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            rows = TypeAdapter(list[tuple[str]]).validate_python(
                db.execute(
                    "SELECT payload FROM documents WHERE document_id = ?", (document_id,)
                ).fetchall()
            )
        return KnowledgeDocument.model_validate_json(rows[0][0]) if rows else None


def export_documents(directory: Path, destination: Path) -> None:
    """Export portable JSONL for later vector indexing without copying raw cases."""
    documents = compile_documents(ResearchKnowledge.load(directory))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "\n".join(document.model_dump_json() for document in documents) + "\n", encoding="utf-8"
    )
    destination.with_suffix(".manifest.json").write_text(
        json.dumps(
            {"documents": len(documents), "content_sha256": document_fingerprint(documents)},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
