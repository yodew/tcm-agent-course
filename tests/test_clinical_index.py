import json
import shutil
from pathlib import Path

import pytest

from tcm_agent.clinical.documents import compile_documents
from tcm_agent.clinical.index import ClinicalIndex, build_index, export_documents
from tcm_agent.clinical.store import ResearchKnowledge
from tcm_agent.errors import DataContractError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def index(tmp_path: Path) -> ClinicalIndex:
    directory = tmp_path / "clinical"
    shutil.copytree(ROOT / "knowledge/clinical", directory)
    path = tmp_path / "research.sqlite"
    build_index(directory, path)
    return ClinicalIndex(directory, path)


def test_documents_preserve_every_source_record_and_citation() -> None:
    pack = ResearchKnowledge.load(ROOT / "knowledge/clinical")
    documents = compile_documents(pack)
    assert len(documents) == len(pack.questions) + len(pack.terms) + len(pack.cards) + len(
        pack.literature
    )
    assert len({doc.document_id for doc in documents}) == len(documents)
    assert all(doc.references and doc.clinical_use == "disabled" for doc in documents)
    assert all(ref.source.url and ref.locator for doc in documents for ref in doc.references)


def test_search_returns_literature_with_primary_source_and_locator(index: ClinicalIndex) -> None:
    hits = index.search("心脾两虚", kind="literature_reference", limit=1)
    assert len(hits) == 1
    assert "心脾两虚" in hits[0].document.title
    assert hits[0].document.references[0].source.source_id == "poon-insomnia-2012"
    assert "Table" in hits[0].document.references[0].locator
    assert hits[0].score_meaning == "lexical_relevance_not_diagnostic_probability"


def test_kind_filter_does_not_mix_questions_with_case_labels(index: ClinicalIndex) -> None:
    hits = index.search("睡眠", kind="question", limit=4)
    assert hits
    assert all(hit.document.kind == "question" for hit in hits)


def test_corpus_card_keeps_unknown_diagnostic_criteria_explicit(index: ClinicalIndex) -> None:
    hits = index.search("心脾两虚", kind="corpus_association", limit=1)
    assert hits
    assert "均未知" in hits[0].document.text
    assert "不是患病概率" in hits[0].document.text


def test_no_match_returns_empty_instead_of_invented_evidence(index: ClinicalIndex) -> None:
    assert index.search("zzzznonexistentterm987654321") == []


def test_fts_operators_are_not_executed(index: ClinicalIndex) -> None:
    assert index.search('zzzznonexistentterm987654321" OR * --') == []


@pytest.mark.parametrize(("query", "limit"), [("", 5), (" " * 5, 5), ("舌" * 301, 5), ("舌", 21)])
def test_invalid_query_is_rejected(index: ClinicalIndex, query: str, limit: int) -> None:
    with pytest.raises(DataContractError, match="Query must"):
        index.search(query, limit=limit)


def test_document_id_resolves_exact_evidence(index: ClinicalIndex) -> None:
    hit = index.search("心脾两虚", kind="literature_reference", limit=1)[0]
    assert index.document(hit.document.document_id) == hit.document
    assert index.document("does-not-exist") is None


def test_source_change_requires_rebuild(index: ClinicalIndex) -> None:
    path = index.directory / "sources.json"
    path.write_text(path.read_text().replace("CC BY 4.0", "CC BY 4.0 updated metadata"))
    with pytest.raises(DataContractError, match="stale"):
        index.search("心脾两虚")


def test_missing_index_does_not_create_empty_database(tmp_path: Path) -> None:
    path = tmp_path / "missing.sqlite"
    with pytest.raises(DataContractError, match="missing"):
        ClinicalIndex(ROOT / "knowledge/clinical", path).search("舌")
    assert not path.exists()


def test_export_is_reproducible_and_contains_retrieval_documents(tmp_path: Path) -> None:
    path = tmp_path / "documents.jsonl"
    export_documents(ROOT / "knowledge/clinical", path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 1205
    assert all(row["references"] for row in rows)
    first = path.read_bytes()
    export_documents(ROOT / "knowledge/clinical", path)
    assert path.read_bytes() == first
