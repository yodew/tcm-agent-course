"""Typed contracts shared by runtime, transport and storage boundaries."""

from enum import StrEnum
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    """Reject unknown fields at application boundaries."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class FactField(StrEnum):
    COMPLAINT = "complaint"
    ONSET = "onset"
    HISTORY = "history"
    MEDICATION = "medication"
    ALLERGY = "allergy"


class QuestionKey(StrEnum):
    COMPLAINT = "complaint"
    ONSET = "onset"
    HISTORY = "history"
    MEDICATION = "medication"
    ALLERGY = "allergy"
    NONE = "none"


class Action(StrEnum):
    ASK = "ask"
    KNOWLEDGE = "knowledge"
    SUMMARY = "summary"
    HANDOFF = "handoff"


class FactDraft(Contract):
    field: FactField
    quote: str = Field(min_length=1, max_length=600)


class CitationDraft(Contract):
    entry_id: str
    quote: str = Field(min_length=1, max_length=1000)


class FinalTurn(Contract):
    """Terminal tool arguments; all fields required by strict JSON schemas."""

    action: Action
    question: QuestionKey
    facts: list[FactDraft] = Field(max_length=5)
    citations: list[CitationDraft] = Field(max_length=4)


class SearchArgs(Contract):
    query: str = Field(min_length=1, max_length=300)


class EmptyArgs(Contract):
    pass


class ToolCall(Contract):
    call_id: str
    name: str
    arguments: str


class ToolResult(Contract):
    call_id: str
    output: str


class Usage(Contract):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class ModelStep(Contract):
    calls: list[ToolCall]
    usage: Usage


class Message(Contract):
    role: Literal["user", "assistant"]
    content: str


class Evidence(Contract):
    entry_id: str
    title: str
    text: str
    source_url: str
    version: str
    license: str
    score: float = 0


class Fact(Contract):
    field: FactField
    quote: str
    source_turn_id: UUID
    confirmed: bool = False


class TurnRequest(Contract):
    request_id: UUID
    expected_version: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=4000)


class TurnResponse(Contract):
    turn_id: UUID
    session_id: UUID
    version: int
    action: Action
    answer: str
    candidates: list[Fact]
    citations: list[Evidence]
    usage: Usage
    steps: int
    status: Literal["completed", "degraded"] = "completed"


class VisitSnapshot(Contract):
    session_id: UUID
    version: int
    facts: list[Fact]
    candidates: list[Fact]
    messages: list[Message]


class ConfirmRequest(Contract):
    expected_version: int = Field(ge=0)
    field: FactField
    source_turn_id: UUID
    quote: str = Field(min_length=1, max_length=600)


class RuntimeInput(Contract):
    snapshot: VisitSnapshot
    request: TurnRequest
    turn_id: UUID


class TurnRecord(Contract):
    request_text: str
    response: TurnResponse
