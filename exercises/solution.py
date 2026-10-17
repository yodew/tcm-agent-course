"""Reference answers; intentionally small enough to explain without a framework."""

from tcm_agent.errors import DataContractError


def select_context(
    required: tuple[str, ...], history: tuple[str, ...], budget: int
) -> tuple[str, ...]:
    """A rejected newest message prevents skipping back to an older disconnected one."""
    remaining = budget - sum(map(len, required))
    if remaining < 0:
        raise DataContractError("required_overflow")
    selected: tuple[str, ...] = ()
    for message in reversed(history):
        if len(message) > remaining:
            break
        selected = (message, *selected)
        remaining -= len(message)
    return (*required, *selected)


def confirm_quote(version: int, approval: tuple[int, str], source: str) -> str:
    """Approval is tied to a revision and literal source; semantics remain a separate check."""
    expected, quote = approval
    if expected != version or not quote or quote not in source:
        raise DataContractError("invalid_confirmation")
    return quote


def reciprocal_rank(ranking: tuple[str, ...], relevant: frozenset[str], k: int) -> float:
    """The first relevant rank matters; duplicates and missing labels are invalid inputs."""
    if k < 1 or not relevant or len(set(ranking)) != len(ranking):
        raise DataContractError("invalid_ranking")
    return next(
        (1 / position for position, key in enumerate(ranking[:k], 1) if key in relevant), 0.0
    )


def retry_identity(original: tuple[str, str], retry: tuple[str, str]) -> bool:
    """Neither a reused ID alone nor matching content alone defines an operation replay."""
    return bool(original[0]) and bool(original[1]) and original == retry
