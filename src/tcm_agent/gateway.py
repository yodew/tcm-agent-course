"""Per-run native tool conversations; no hidden fallback or provider-side storage."""

import json
import random
from dataclasses import dataclass, field
from typing import Literal, Protocol, assert_never

import anyio
import httpx2
from pydantic import JsonValue, TypeAdapter

from tcm_agent.config import Settings
from tcm_agent.domain import Message, ModelStep, ToolResult
from tcm_agent.errors import AgentError
from tcm_agent.tool_schema import SYSTEM_PROMPT, TOOLS
from tcm_agent.wire import parse_chat, parse_responses


class Conversation(Protocol):
    async def step(self, observations: list[ToolResult]) -> ModelStep:
        """Consume tool outputs and obtain the next model decision."""
        ...


class ModelGateway(Protocol):
    def conversation(self, messages: list[Message]) -> Conversation:
        """Each turn has isolated provider replay state."""
        ...


@dataclass(frozen=True, slots=True)
class Gateway:
    settings: Settings
    client: httpx2.AsyncClient

    def conversation(self, messages: list[Message]) -> Conversation:
        """Construct an isolated wire transcript."""
        mode = self.settings.model_mode
        if mode == "offline":
            raise AgentError("offline_gateway_mismatch", 500)
        transcript: list[JsonValue] = [m.model_dump(mode="json") for m in messages]
        if mode == "chat":
            transcript.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        return NativeConversation(self.settings, self.client, mode, transcript)


@dataclass(frozen=True, slots=True)
class NativeConversation:
    """Mutable wire transcript owned by exactly one request."""

    settings: Settings
    client: httpx2.AsyncClient
    mode: Literal["responses", "chat"]
    transcript: list[JsonValue] = field(default_factory=list)

    async def step(self, observations: list[ToolResult]) -> ModelStep:
        """Use protocol-specific schemas and call-result linkage."""
        tool_specs: list[dict[str, JsonValue]] = [
            {
                "type": "function",
                "name": name,
                "description": description,
                "parameters": TypeAdapter(JsonValue).validate_python(schema.model_json_schema()),
                "strict": True,
            }
            for name, description, schema in TOOLS
        ]
        payload: dict[str, JsonValue] = {
            "model": self.settings.model_name,
            "parallel_tool_calls": False,
        }
        match self.mode:
            case "responses":
                self.transcript.extend(
                    {"type": "function_call_output", "call_id": r.call_id, "output": r.output}
                    for r in observations
                )
                payload.update(
                    input=self.transcript,
                    instructions=SYSTEM_PROMPT,
                    tools=list(tool_specs),
                    store=False,
                    max_output_tokens=self.settings.max_output_tokens,
                )
                if self.settings.responses_include_reasoning:
                    payload["include"] = ["reasoning.encrypted_content"]
                raw = await self.post("responses", json.dumps(payload).encode())
                result, replay = parse_responses(raw)
            case "chat":
                self.transcript.extend(
                    {"role": "tool", "tool_call_id": r.call_id, "content": r.output}
                    for r in observations
                )
                tools: list[JsonValue] = [
                    {"type": "function", "function": {k: v for k, v in spec.items() if k != "type"}}
                    for spec in tool_specs
                ]
                payload.update(
                    messages=self.transcript,
                    tools=tools,
                )
                payload[self.settings.chat_token_parameter] = self.settings.max_output_tokens
                raw = await self.post("chat/completions", json.dumps(payload).encode())
                result, replay = parse_chat(raw)
            case unreachable:
                assert_never(unreachable)
        self.transcript.extend(replay)
        return result

    async def post(self, endpoint: str, body: bytes) -> bytes:
        """Retry transient HTTP errors at most twice within the outer deadline."""
        if len(body) > self.settings.context_chars * 4:
            raise AgentError("wire_context_budget_exceeded", 413)
        headers = {
            "Authorization": f"Bearer {self.settings.model_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        for attempt in range(3):
            try:
                response = await self.client.post(
                    f"{self.settings.model_base_url.rstrip('/')}/{endpoint}",
                    content=body,
                    headers=headers,
                )
            except httpx2.TransportError as error:
                raise AgentError("provider_transport_error") from error
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                delay: float = 0.2 * (2.0**attempt) + random.uniform(0, 0.1)  # noqa: S311
                await anyio.sleep(min(2.0, delay))
                continue
            if response.status_code >= 300:
                raise AgentError("provider_http_error")
            return response.content
        raise AgentError("provider_retries_exhausted")
