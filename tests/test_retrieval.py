from pathlib import Path

import pytest

from tcm_agent.retrieval import KnowledgeBase, cosine, tokenize


@pytest.mark.anyio
async def test_search_when_chinese_term_matches_relevant_entry() -> None:
    # Given
    knowledge = KnowledgeBase.load(Path("knowledge/entries.json"))
    # When
    results = await knowledge.search("四诊望闻问切")
    # Then
    assert results[0].entry_id == "tcm-four-examinations"


@pytest.mark.anyio
async def test_search_when_no_terms_overlap_returns_empty() -> None:
    # Given
    knowledge = KnowledgeBase.load(Path("knowledge/entries.json"))
    # When
    results = await knowledge.search("zyxw987654")
    # Then
    assert results == []


def test_cosine_when_dimensions_change_fails_instead_of_truncating() -> None:
    # Given / When / Then
    with pytest.raises(ValueError, match="dimension"):
        cosine([1, 0], [1])


def test_tokenize_when_chinese_has_no_spaces_retains_bigrams() -> None:
    # Given / When
    terms = tokenize("望闻问切")
    # Then
    assert {"望闻", "闻问", "问切"}.issubset(terms)
