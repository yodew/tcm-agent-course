# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run from the repository root: uv run python -m labs.context_memory
"""Demonstrate explicit context assembly and revision-checked human confirmation."""

from dataclasses import dataclass

from tcm_agent.errors import DataContractError


def assemble(required: tuple[str, ...], recent: tuple[str, ...], max_chars: int) -> tuple[str, ...]:
    """Keep required content, then a contiguous suffix; characters are not tokens."""
    budget = max_chars - sum(len(text) for text in required)
    if budget < 0:
        raise DataContractError("Required context exceeds character budget")
    selected: tuple[str, ...] = ()
    for text in reversed(recent):
        if len(text) > budget:
            break
        selected = (text, *selected)
        budget -= len(text)
    return (*required, *selected)


@dataclass(frozen=True, slots=True)
class FactState:
    """Only explicit confirmation changes this teaching fact state."""

    version: int = 0
    confirmed: str | None = None

    def confirm(self, expected_version: int, quote: str, source: str) -> "FactState":
        """Reject stale confirmation and quotes absent from the original input."""
        if expected_version != self.version:
            raise DataContractError("Version conflict")
        if not quote or quote not in source:
            raise DataContractError("Quote lacks source evidence")
        return FactState(self.version + 1, quote)


def main() -> None:
    """Show that a candidate alone never becomes a confirmed fact."""
    state = FactState()
    print("candidate only; confirmed:", state.confirmed)
    state = state.confirm(0, "最近睡不好", "最近睡不好，想整理就诊资料")
    print("after explicit confirmation:", state)
    print("CHARACTER BUDGET ONLY:", assemble(("规则", "当前问题"), ("旧历史", "最近历史"), 10))


if __name__ == "__main__":
    main()
