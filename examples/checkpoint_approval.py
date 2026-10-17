# /// script
# requires-python = ">=3.12"
# dependencies = ["langgraph>=1,<2", "tcm-agent-course"]
# [tool.uv.sources]
# tcm-agent-course = { path = "..", editable = true }
# ///
# Run: uv run --extra graph python examples/checkpoint_approval.py
"""Actual LangGraph interrupt/resume, with in-memory checkpoints and no external write."""

from typing import ClassVar, TypedDict
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, ConfigDict, Field

from tcm_agent.errors import DataContractError


class ApprovalState(TypedDict):
    draft: str
    revision: int
    approved: bool


class Decision(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    approved: bool = Field(strict=True)
    revision: int


def approve(state: ApprovalState) -> ApprovalState:
    """On resume the node runs again; verify approval against the current revision."""
    decision = Decision.model_validate(
        interrupt({"draft": state["draft"], "revision": state["revision"]})
    )
    if decision.revision != state["revision"]:
        raise DataContractError("Approval revision is stale")
    return {"draft": state["draft"], "revision": state["revision"], "approved": decision.approved}


def approval_round_trip(*, stale: bool = False) -> bool:
    """Exercise a real checkpoint; memory does not survive a process restart."""
    builder = StateGraph(ApprovalState)
    builder.add_node("approval", approve)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)
    graph = builder.compile(checkpointer=InMemorySaver())
    config: RunnableConfig = {"configurable": {"thread_id": str(uuid4())}}
    graph.invoke({"draft": "合成摘要草稿", "revision": 1, "approved": False}, config)
    if not graph.get_state(config).next:
        raise DataContractError("Expected a suspended approval node")
    if stale:
        graph.update_state(config, {"revision": 2})
    result = graph.invoke(Command(resume={"approved": True, "revision": 1}), config)
    return Decision.model_validate(
        {"approved": result["approved"], "revision": result["revision"]}
    ).approved


def main() -> None:
    """Show both a successful resume and a rejected stale approval."""
    print("REAL LANGGRAPH, IN-MEMORY ONLY:", approval_round_trip())
    try:
        approval_round_trip(stale=True)
    except DataContractError:
        print("Stale approval rejected; no external operation was performed")


if __name__ == "__main__":
    main()
