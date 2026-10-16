"""Deterministic protocol fixture, explicitly NOT an intelligent model."""

import json
from dataclasses import dataclass

from pydantic import TypeAdapter

from tcm_agent.domain import (
    Action,
    CitationDraft,
    Evidence,
    FactDraft,
    FactField,
    FinalTurn,
    Message,
    ModelStep,
    QuestionKey,
    ToolCall,
    ToolResult,
    Usage,
)


@dataclass(frozen=True, slots=True)
class OfflineGateway:
    """Exercise application plumbing without API credentials or network charges."""

    def conversation(self, messages: list[Message]) -> "OfflineConversation":
        """Construct a deterministic fixture turn."""
        return OfflineConversation(messages[-1].content)


@dataclass(frozen=True, slots=True)
class OfflineConversation:
    text: str

    async def step(self, observations: list[ToolResult]) -> ModelStep:
        """A transparent fixed policy used only for reproducible engineering tests."""
        if not observations and any(
            word in self.text for word in ("什么", "解释", "知识", "四诊", "望闻问切")
        ):
            return ModelStep(
                calls=[
                    ToolCall(
                        call_id="lookup",
                        name="search_knowledge",
                        arguments=json.dumps({"query": self.text[:100]}),
                    )
                ],
                usage=Usage(),
            )
        citations: list[CitationDraft] = []
        action = Action.ASK
        question = QuestionKey.ONSET
        facts: list[FactDraft] = []
        if observations:
            entries = TypeAdapter(list[Evidence]).validate_json(observations[0].output)
            citations = [CitationDraft(entry_id=e.entry_id, quote=e.text) for e in entries[:1]]
            action, question = Action.KNOWLEDGE, QuestionKey.NONE
        elif any(word in self.text for word in ("摘要", "结束", "跳过")):
            action, question = Action.SUMMARY, QuestionKey.NONE
        else:
            facts = [FactDraft(field=FactField.COMPLAINT, quote=self.text[:600])]
        final = FinalTurn(action=action, question=question, facts=facts, citations=citations)
        return ModelStep(
            calls=[
                ToolCall(call_id="final", name="submit_turn", arguments=final.model_dump_json())
            ],
            usage=Usage(),
        )
