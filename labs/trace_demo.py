# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python -m labs.trace_demo
"""Genuine runtime successes and rejections, with explicitly scripted decisions."""

from dataclasses import dataclass
from pathlib import Path

import anyio

from labs.trace_runtime import RunResult, context_for, trace_run
from tcm_agent.domain import Contract, Message, ModelStep, ToolCall, ToolResult, Usage
from tcm_agent.gateway import Conversation
from tcm_agent.offline import OfflineGateway
from tcm_agent.retrieval import KnowledgeBase
from tcm_agent.runtime import AgentRuntime


@dataclass(frozen=True, slots=True)
class RepeatingGateway:
    call: ToolCall

    def conversation(self, messages: list[Message]) -> Conversation:
        """Use a faulty fixed policy to exercise the host's real rejection path."""
        del messages
        return RepeatingConversation(self.call)


@dataclass(frozen=True, slots=True)
class RepeatingConversation:
    call: ToolCall

    async def step(self, observations: list[ToolResult]) -> ModelStep:
        """Repeat a proposal deliberately; the runtime must reject duplicate IDs."""
        del observations
        return ModelStep(calls=[self.call], usage=Usage())


class TraceReport(Contract):
    mode: str = "scripted-fixture; production-runtime; no-model-no-database"
    runs: dict[str, RunResult]


async def run_examples() -> TraceReport:
    """A valid search, unknown tool, malformed arguments, duplicate and budget failure."""
    knowledge = KnowledgeBase.load(Path("knowledge/entries.json"))
    runs = {
        "knowledge": await trace_run(
            AgentRuntime(OfflineGateway(), knowledge, 6, 16000), context_for("什么是四诊？")
        )
    }
    calls = {
        "unknown_tool": ToolCall(call_id="one", name="delete_all", arguments="{}"),
        "bad_arguments": ToolCall(call_id="one", name="search_knowledge", arguments='{"query":1}'),
        "duplicate_call": ToolCall(call_id="one", name="read_visit_facts", arguments="{}"),
        "fabricated_fact": ToolCall(
            call_id="one",
            name="submit_turn",
            arguments='{"action":"ask","question":"onset","facts":[{"field":"history","quote":"无既往史"}],"citations":[]}',
        ),
        "unseen_citation": ToolCall(
            call_id="one",
            name="submit_turn",
            arguments='{"action":"knowledge","question":"none","facts":[],"citations":[{"entry_id":"tcm-four-examinations","quote":"四诊"}]}',
        ),
    }
    for name, call in calls.items():
        runs[name] = await trace_run(
            AgentRuntime(RepeatingGateway(call), knowledge, 3, 16000), context_for("最近睡不好")
        )
    runs["step_budget"] = await trace_run(
        AgentRuntime(OfflineGateway(), knowledge, 1, 16000), context_for("什么是四诊？")
    )
    return TraceReport(runs=runs)


async def main() -> None:
    """Write synthetic metadata only, suitable for course evidence."""
    report = await run_examples()
    await anyio.Path("evidence/runtime-traces.json").write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    print("7 actual runtime traces written; model decisions are scripted fixtures")


if __name__ == "__main__":
    anyio.run(main)
