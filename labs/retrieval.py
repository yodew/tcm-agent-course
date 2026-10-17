# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run from the repository root: uv run python -m labs.retrieval
"""Real lexical retrieval plus explicit rank and vector arithmetic experiments."""

from pathlib import Path

from tcm_agent.errors import DataContractError
from tcm_agent.retrieval import KnowledgeBase, cosine


def fuse(rankings: tuple[tuple[str, ...], ...], constant: int = 60) -> tuple[str, ...]:
    """Fuse ranks, with deterministic ties and no incomparable score addition."""
    if constant < 0 or any(len(set(ranking)) != len(ranking) for ranking in rankings):
        raise DataContractError("Use nonnegative constant and unique IDs in each ranking")
    scores: dict[str, float] = {}
    for ranking in rankings:
        for position, entry in enumerate(ranking, start=1):
            scores[entry] = scores.get(entry, 0) + 1 / (constant + position)
    return tuple(sorted(scores, key=lambda entry: (-scores[entry], entry)))


def main() -> None:
    """Manual vectors only illustrate geometry; BM25 actually queries course documents."""
    print("MANUAL VECTORS, NOT EMBEDDINGS:", cosine([1, 0], [0, 1]))
    print("RRF arithmetic:", fuse((("A", "B", "C"), ("B", "C", "A"))))
    knowledge = KnowledgeBase.load(Path("knowledge/entries.json"))
    ranking = knowledge.sparse("四诊")
    print(
        "REAL BM25:", [(knowledge.entries[i].entry_id, round(score, 4)) for i, score in ranking[:3]]
    )


if __name__ == "__main__":
    main()
