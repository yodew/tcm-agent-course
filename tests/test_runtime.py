from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest

from tcm_agent.domain import (
    Action,
    CitationDraft,
    FactDraft,
    FactField,
    FinalTurn,
    Message,
    ModelStep,
    QuestionKey,
    RuntimeInput,
    ToolCall,
    ToolResult,
    TurnRequest,
    Usage,
    VisitSnapshot,
)
from tcm_agent.errors import AgentError
from tcm_agent.gateway import Conversation
from tcm_agent.retrieval import KnowledgeBase
from tcm_agent.runtime import AgentRuntime


@dataclass(frozen=True, slots=True)
class ScriptGateway:
    call: ToolCall

    def conversation(self, messages: list[Message]) -> Conversation:
        return ScriptConversation(self.call)


@dataclass(frozen=True, slots=True)
class ScriptConversation:
    call: ToolCall

    async def step(self, observations: list[ToolResult]) -> ModelStep:
        return ModelStep(calls=[self.call], usage=Usage())


def context() -> RuntimeInput:
    return RuntimeInput(
        snapshot=VisitSnapshot(session_id=uuid4(), version=0, facts=[], candidates=[], messages=[]),
        request=TurnRequest(request_id=uuid4(), expected_version=0, text="睡不好"),
        turn_id=uuid4(),
    )


def runtime(call: ToolCall) -> AgentRuntime:
    return AgentRuntime(
        ScriptGateway(call), KnowledgeBase.load(Path("knowledge/entries.json")), 3, 16000
    )


@pytest.mark.anyio
async def test_final_when_fact_not_in_current_input_rejects() -> None:
    # Given
    final = FinalTurn(
        action=Action.ASK,
        question=QuestionKey.ONSET,
        facts=[FactDraft(field=FactField.HISTORY, quote="无既往史")],
        citations=[],
    )
    # When / Then
    with pytest.raises(AgentError, match="ungrounded_fact"):
        await runtime(
            ToolCall(call_id="one", name="submit_turn", arguments=final.model_dump_json())
        ).run(context())


@pytest.mark.anyio
async def test_final_when_citation_not_retrieved_rejects() -> None:
    # Given
    final = FinalTurn(
        action=Action.KNOWLEDGE,
        question=QuestionKey.NONE,
        facts=[],
        citations=[CitationDraft(entry_id="tcm-four-examinations", quote="四诊")],
    )
    # When / Then
    with pytest.raises(AgentError, match="ungrounded_citation"):
        await runtime(
            ToolCall(call_id="one", name="submit_turn", arguments=final.model_dump_json())
        ).run(context())


@pytest.mark.anyio
async def test_call_when_tool_unknown_has_no_side_effects() -> None:
    # Given / When / Then
    with pytest.raises(AgentError, match="tool_not_allowed"):
        await runtime(ToolCall(call_id="one", name="delete_all_patients", arguments="{}")).run(
            context()
        )


@pytest.mark.anyio
async def test_call_when_arguments_invalid_fails_at_boundary() -> None:
    # Given / When / Then
    with pytest.raises(AgentError, match="invalid_tool_arguments"):
        await runtime(
            ToolCall(call_id="one", name="search_knowledge", arguments='{"query":1}')
        ).run(context())


@pytest.mark.anyio
async def test_loop_when_duplicate_call_id_stops() -> None:
    # Given / When / Then
    with pytest.raises(AgentError, match="duplicate_tool_call_id"):
        await runtime(ToolCall(call_id="one", name="read_visit_facts", arguments="{}")).run(
            context()
        )
