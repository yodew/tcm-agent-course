"""Explicit assignment suite; not collected by the normal tests/ project command."""

import os
from typing import Literal, Protocol, assert_never

import pytest
from pydantic import TypeAdapter

from exercises import solution, starter
from tcm_agent.errors import DataContractError


class Implementation(Protocol):
    def select_context(
        self, required: tuple[str, ...], history: tuple[str, ...], budget: int
    ) -> tuple[str, ...]: ...
    def confirm_quote(self, version: int, approval: tuple[int, str], source: str) -> str: ...
    def reciprocal_rank(
        self, ranking: tuple[str, ...], relevant: frozenset[str], k: int
    ) -> float: ...
    def retry_identity(self, original: tuple[str, str], retry: tuple[str, str]) -> bool: ...


@pytest.fixture
def implementation() -> Implementation:
    mode = TypeAdapter(Literal["starter", "solution"]).validate_python(
        os.environ.get("TCM_EXERCISE", "solution")
    )
    match mode:
        case "starter":
            return starter
        case "solution":
            return solution
        case unreachable:
            assert_never(unreachable)


def test_context_when_exact_fit_keeps_order(implementation: Implementation) -> None:
    # Given / When
    result = implementation.select_context(("规则",), ("旧", "最新"), 5)
    # Then
    assert result == ("规则", "旧", "最新")


def test_context_when_newest_overflows_never_skips_to_older(implementation: Implementation) -> None:
    # Given / When
    result = implementation.select_context(("规则",), ("旧", "很长的最新消息"), 3)
    # Then
    assert result == ("规则",)


def test_context_when_required_overflows_rejects(implementation: Implementation) -> None:
    # Given / When / Then
    with pytest.raises(DataContractError):
        implementation.select_context(("必需内容",), (), 1)


def test_confirmation_when_current_preserves_negation(implementation: Implementation) -> None:
    # Given / When
    result = implementation.confirm_quote(2, (2, "没有提供过敏资料"), "目前没有提供过敏资料")
    # Then
    assert result == "没有提供过敏资料"


@pytest.mark.parametrize("approval", [(1, "有"), (2, ""), (2, "无过敏")])
def test_confirmation_when_untrusted_rejects(
    implementation: Implementation, approval: tuple[int, str]
) -> None:
    # Given / When / Then
    with pytest.raises(DataContractError):
        implementation.confirm_quote(2, approval, "有不确定的资料")


def test_rank_when_first_hit_second_returns_half(implementation: Implementation) -> None:
    # Given / When
    result = implementation.reciprocal_rank(("X", "A", "B"), frozenset({"A", "B"}), 3)
    # Then
    assert result == 0.5


def test_rank_when_hit_outside_k_returns_zero(implementation: Implementation) -> None:
    # Given / When
    result = implementation.reciprocal_rank(("X", "A"), frozenset({"A"}), 1)
    # Then
    assert result == 0


@pytest.mark.parametrize(
    ("ranking", "relevant", "k"),
    [(("A", "A"), frozenset({"A"}), 2), (("A",), frozenset(), 1), (("A",), frozenset({"A"}), 0)],
)
def test_rank_when_contract_invalid_rejects(
    implementation: Implementation, ranking: tuple[str, ...], relevant: frozenset[str], k: int
) -> None:
    # Given / When / Then
    with pytest.raises(DataContractError):
        implementation.reciprocal_rank(ranking, relevant, k)


@pytest.mark.parametrize(
    ("retry", "expected"),
    [(("id1", "hash1"), True), (("id2", "hash1"), False), (("id1", "hash2"), False)],
)
def test_retry_when_identity_changes_is_not_replay(
    implementation: Implementation, retry: tuple[str, str], expected: bool
) -> None:
    # Given / When
    result = implementation.retry_identity(("id1", "hash1"), retry)
    # Then
    assert result is expected


def test_retry_when_empty_identity_rejects(implementation: Implementation) -> None:
    # Given / When
    result = implementation.retry_identity(("", ""), ("", ""))
    # Then
    assert result is False
