# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run from the repository root: uv run python -m labs.trace_demo
"""Record bounded metadata around the real runtime; never record prompts or tool bodies."""

from dataclasses import dataclass, field
from time import perf_counter
from uuid import UUID

import anyio
from pydantic import Field

from tcm_agent.domain import (
    Contract,
    Message,
    ModelStep,
    RuntimeInput,
    ToolResult,
    TurnRequest,
    VisitSnapshot,
)
from tcm_agent.errors import AgentError
from tcm_agent.events import Progress
from tcm_agent.gateway import Conversation, ModelGateway
from tcm_agent.runtime import AgentRuntime


class TraceEvent(Contract):
    kind: str
    step: int
    calls: list[str] = Field(default_factory=list)
    observation_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class RunResult(Contract):
    action: str = ""
    citation_ids: list[str] = Field(default_factory=list)
    error: str = ""
    steps: int
    input_tokens: int
    output_tokens: int
    elapsed_ms: float
    events: list[TraceEvent]


@dataclass(frozen=True, slots=True)
class RecordingGateway:
    """A per-run accumulator; only tool names from an allowlist enter evidence."""

    inner: ModelGateway
    events: list[TraceEvent] = field(default_factory=list)

    def conversation(self, messages: list[Message]) -> Conversation:
        """Forward messages without retaining them in this recorder."""
        return RecordingConversation(self.inner.conversation(messages), self.events)


@dataclass(frozen=True, slots=True)
class RecordingConversation:
    """Append metadata after each genuine gateway invocation."""

    inner: Conversation
    events: list[TraceEvent]

    async def step(self, observations: list[ToolResult]) -> ModelStep:
        """Observe a decision, not its private reasoning, arguments or raw response."""
        result = await self.inner.step(observations)
        self.events.append(
            TraceEvent(
                kind="decision",
                step=sum(e.kind == "decision" for e in self.events) + 1,
                calls=[
                    c.name
                    if c.name in {"search_knowledge", "read_visit_facts", "submit_turn"}
                    else "rejected"
                    for c in result.calls
                ],
                observation_count=len(observations),
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
            )
        )
        return result


def context_for(text: str) -> RuntimeInput:
    """Stable synthetic IDs make examples comparable; there is no database write."""
    return RuntimeInput(
        snapshot=VisitSnapshot(
            session_id=UUID(int=1), version=0, facts=[], candidates=[], messages=[]
        ),
        request=TurnRequest(request_id=UUID(int=2), expected_version=0, text=text),
        turn_id=UUID(int=3),
    )


async def trace_run(
    runtime: AgentRuntime, context: RuntimeInput, deadline_seconds: float = 30
) -> RunResult:
    """Execute the production runtime with per-run metadata and an outer deadline."""
    recording = RecordingGateway(runtime.gateway)
    traced = AgentRuntime(recording, runtime.knowledge, runtime.max_steps, runtime.context_chars)

    async def progress(event: Progress) -> None:
        recording.events.append(TraceEvent(kind=event.kind, step=event.step))

    started = perf_counter()
    action, citations, error = "", [], ""
    try:
        with anyio.fail_after(deadline_seconds):
            response = await traced.run(context, progress)
        action = response.action.value
        citations = [entry.entry_id for entry in response.citations]
    except AgentError as failure:
        error = failure.code
    except TimeoutError:
        error = "turn_timeout"
    decisions = [event for event in recording.events if event.kind == "decision"]
    return RunResult(
        action=action,
        citation_ids=citations,
        error=error,
        steps=len(decisions),
        input_tokens=sum(e.input_tokens for e in decisions),
        output_tokens=sum(e.output_tokens for e in decisions),
        elapsed_ms=round((perf_counter() - started) * 1000, 3),
        events=recording.events,
    )
