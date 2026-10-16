# /// script
# requires-python = ">=3.12"
# dependencies = ["langgraph>=1,<2", "tcm-agent-course"]
# [tool.uv.sources]
# tcm-agent-course = { path = "..", editable = true }
# ///
# Run: uv run --extra graph python examples/graph_workflow.py
"""Compare explicit graph routing with the same production agent runtime."""

from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4

import anyio
from langgraph.graph import END, START, StateGraph

from tcm_agent.domain import RuntimeInput, TurnRequest, TurnResponse, VisitSnapshot
from tcm_agent.offline import OfflineGateway
from tcm_agent.policy import needs_handoff
from tcm_agent.retrieval import KnowledgeBase
from tcm_agent.runtime import AgentRuntime


class GraphState(TypedDict):
    context: RuntimeInput
    result: TurnResponse | None


async def exercise(text: str) -> TurnResponse:
    """Graph owns routing; application service still owns durable transaction commits."""
    runtime = AgentRuntime(
        OfflineGateway(), KnowledgeBase.load(Path("knowledge/entries.json")), 6, 16000
    )

    def route(state: GraphState) -> Literal["handoff", "agent"]:
        return "handoff" if needs_handoff(state["context"].request.text) else "agent"

    async def agent(state: GraphState) -> GraphState:
        return {"context": state["context"], "result": await runtime.run(state["context"])}

    def handoff(state: GraphState) -> GraphState:
        return {"context": state["context"], "result": runtime.handoff(state["context"])}

    builder = StateGraph(GraphState)
    builder.add_node("agent", agent)
    builder.add_node("handoff", handoff)
    builder.add_conditional_edges(START, route)
    builder.add_edge("agent", END)
    builder.add_edge("handoff", END)
    graph = builder.compile()
    context = RuntimeInput(
        snapshot=VisitSnapshot(session_id=uuid4(), version=0, facts=[], candidates=[], messages=[]),
        request=TurnRequest(request_id=uuid4(), expected_version=0, text=text),
        turn_id=uuid4(),
    )
    state = await graph.ainvoke({"context": context, "result": None})
    return TurnResponse.model_validate(state["result"])


async def main() -> None:
    """Drive both branches with the same graph."""
    for text in ("什么是四诊？", "我有胸痛"):
        print((await exercise(text)).model_dump_json())


if __name__ == "__main__":
    anyio.run(main)
