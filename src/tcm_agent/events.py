"""Progress events expose workflow state without unreviewed model text."""

from typing import Literal, Protocol

from tcm_agent.domain import Contract


class Progress(Contract):
    kind: Literal["model_step", "tool_started", "validated"]
    step: int
    tool: str = ""


class ProgressSink(Protocol):
    async def __call__(self, progress: Progress, /) -> None:
        """Publish non-sensitive workflow progress with backpressure."""
        ...
