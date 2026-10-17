"""Implement these contracts before consulting solution.py; no network or model required."""

from tcm_agent.errors import DataContractError


def select_context(
    required: tuple[str, ...], history: tuple[str, ...], budget: int
) -> tuple[str, ...]:
    """Keep required text and a contiguous newest suffix, measured in characters."""
    raise DataContractError("Exercise 1 pending")


def confirm_quote(version: int, approval: tuple[int, str], source: str) -> str:
    """Reject stale, empty and ungrounded approvals; return only the exact quote."""
    raise DataContractError("Exercise 2 pending")


def reciprocal_rank(ranking: tuple[str, ...], relevant: frozenset[str], k: int) -> float:
    """Require positive k, unique ranked IDs and nonempty labels; RR@k otherwise."""
    raise DataContractError("Exercise 3 pending")


def retry_identity(original: tuple[str, str], retry: tuple[str, str]) -> bool:
    """Same operation requires both nonempty identical ID and identical body hash."""
    raise DataContractError("Exercise 4 pending")
