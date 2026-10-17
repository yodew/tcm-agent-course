# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run from the repository root: uv run python -m labs.evaluation
"""Measure labeled retrieval and task outcomes without inventing a judge score."""

from dataclasses import dataclass

from tcm_agent.errors import DataContractError


@dataclass(frozen=True, slots=True)
class RetrievalScore:
    recall: float
    precision: float
    reciprocal_rank: float


def score(ranking: tuple[str, ...], relevant: frozenset[str], k: int) -> RetrievalScore:
    """Precision@k uses k slots; this experiment requires nonempty relevance labels."""
    if k <= 0 or not relevant or len(set(ranking)) != len(ranking):
        raise DataContractError("Use positive k, nonempty labels and unique ranking IDs")
    top = ranking[:k]
    hits = len(set(top) & relevant)
    reciprocal = next(
        (1 / rank for rank, entry in enumerate(top, start=1) if entry in relevant), 0.0
    )
    return RetrievalScore(hits / len(relevant), hits / k, reciprocal)


def task_success(answer_correct: bool, unauthorized_write: bool, calls: int, budget: int) -> bool:
    """Task success also requires respecting permissions and execution budget."""
    return answer_correct and not unauthorized_write and 0 <= calls <= budget


def main() -> None:
    """Print transparent labeled examples; they do not estimate real-world quality."""
    print("LABELED EXAMPLE:", score(("wrong", "B", "A"), frozenset({"A", "B"}), 3))
    print(
        "right answer but unauthorized:",
        task_success(answer_correct=True, unauthorized_write=True, calls=1, budget=3),
    )
    print(
        "right answer within budget:",
        task_success(answer_correct=True, unauthorized_write=False, calls=2, budget=3),
    )


if __name__ == "__main__":
    main()
