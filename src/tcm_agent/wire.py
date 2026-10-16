"""Parse third-party responses at the boundary; preserve opaque replay items."""

import json
from typing import Literal

from pydantic import BaseModel, Field, JsonValue, ValidationError

from tcm_agent.domain import ModelStep, ToolCall, Usage
from tcm_agent.errors import AgentError


class WireUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ResponseEnvelope(BaseModel):
    status: str = "completed"
    output: list[dict[str, JsonValue]]
    usage: WireUsage = Field(default_factory=WireUsage)


class ResponseItem(BaseModel):
    type: str
    call_id: str = ""
    name: str = ""
    arguments: str = ""


class Function(BaseModel):
    name: str
    arguments: str


class ChatToolCall(BaseModel):
    id: str
    type: Literal["function"]
    function: Function


class ChatMessage(BaseModel):
    role: Literal["assistant"]
    content: str | None = None
    tool_calls: list[ChatToolCall] = Field(default_factory=list)


class ChatChoice(BaseModel):
    finish_reason: str | None = None
    message: ChatMessage


class ChatEnvelope(BaseModel):
    choices: list[ChatChoice]
    usage: WireUsage = Field(default_factory=WireUsage)


def parse_responses(raw: bytes) -> tuple[ModelStep, list[JsonValue]]:
    """Return calls plus original items, including encrypted reasoning items."""
    try:
        envelope = ResponseEnvelope.model_validate_json(raw)
        if envelope.status != "completed":
            raise AgentError("provider_incomplete")
        items = [ResponseItem.model_validate(item) for item in envelope.output]
        calls = [
            ToolCall(call_id=item.call_id, name=item.name, arguments=item.arguments)
            for item in items
            if item.type == "function_call"
        ]
        if any(not call.call_id or not call.name for call in calls):
            raise AgentError("provider_invalid_call")
        replay: list[JsonValue] = list(envelope.output)
        return ModelStep(
            calls=calls,
            usage=Usage(
                input_tokens=envelope.usage.input_tokens,
                output_tokens=envelope.usage.output_tokens,
            ),
        ), replay
    except (ValidationError, json.JSONDecodeError) as error:
        raise AgentError("provider_schema_error") from error


def parse_chat(raw: bytes) -> tuple[ModelStep, list[JsonValue]]:
    """Normalize Chat Completions without pretending its wire format is Responses."""
    try:
        envelope = ChatEnvelope.model_validate_json(raw)
        if not envelope.choices or envelope.choices[0].finish_reason in {
            "length",
            "content_filter",
        }:
            raise AgentError("provider_incomplete")
        message = envelope.choices[0].message
        calls = [
            ToolCall(call_id=c.id, name=c.function.name, arguments=c.function.arguments)
            for c in message.tool_calls
        ]
        replay: list[JsonValue] = [message.model_dump(mode="json")]
        return ModelStep(
            calls=calls,
            usage=Usage(
                input_tokens=envelope.usage.prompt_tokens,
                output_tokens=envelope.usage.completion_tokens,
            ),
        ), replay
    except ValidationError as error:
        raise AgentError("provider_schema_error") from error
