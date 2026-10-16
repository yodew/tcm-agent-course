import json
from typing import Literal

import httpx2
import pytest
from pydantic import SecretStr

from tcm_agent.config import Settings
from tcm_agent.domain import Message, ToolResult
from tcm_agent.errors import AgentError
from tcm_agent.gateway import Gateway
from tcm_agent.wire import parse_chat, parse_responses


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["responses", "chat"])
async def test_native_protocol_when_tool_result_returned_preserves_linkage(
    mode: Literal["responses", "chat"],
) -> None:
    # Given: HTTP-level fake, not a mocked runtime or tool dispatcher.
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        if mode == "responses":
            return httpx2.Response(
                200,
                json={
                    "status": "completed",
                    "output": [
                        {
                            "type": "reasoning",
                            "id": "r1",
                            "encrypted_content": "opaque",
                            "summary": [],
                        },
                        {
                            "type": "function_call",
                            "id": "fc1",
                            "call_id": "call1",
                            "name": "read_visit_facts",
                            "arguments": "{}",
                        },
                    ],
                    "usage": {"input_tokens": 10, "output_tokens": 2},
                },
            )
        return httpx2.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "id": "call1",
                                    "function": {"name": "read_visit_facts", "arguments": "{}"},
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        )

    config = Settings(model_mode=mode, model_name="contract", model_api_key=SecretStr("test-key"))
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        conversation = Gateway(config, client).conversation([Message(role="user", content="hi")])
        await conversation.step([])
        # When: runtime returns a result for call1.
        step = await conversation.step([ToolResult(call_id="call1", output="[]")])
    # Then: actual outgoing JSON uses the selected protocol, preserving replay items.
    body = json.loads(requests[-1].content)
    assert step.usage.input_tokens == 10
    if mode == "responses":
        assert requests[-1].url.path == "/v1/responses"
        assert body["store"] is False
        assert body["input"][-1] == {
            "type": "function_call_output",
            "call_id": "call1",
            "output": "[]",
        }
        assert body["input"][-3]["encrypted_content"] == "opaque"
        assert body["tools"][0]["name"] == "search_knowledge"
    else:
        assert requests[-1].url.path == "/v1/chat/completions"
        assert body["messages"][-1]["tool_call_id"] == "call1"
        assert body["tools"][0]["function"]["name"] == "search_knowledge"


@pytest.mark.anyio
async def test_provider_when_401_does_not_retry_or_expose_body() -> None:
    # Given
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(401, text="SECRET UPSTREAM PAYLOAD")

    config = Settings(model_mode="responses", model_api_key=SecretStr("test-key"))
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        # When / Then
        with pytest.raises(AgentError, match=r"^provider_http_error$"):
            await (
                Gateway(config, client).conversation([Message(role="user", content="hi")]).step([])
            )
    assert len(requests) == 1


def test_parse_when_response_incomplete_rejects() -> None:
    # Given / When / Then
    with pytest.raises(AgentError, match="provider_incomplete"):
        parse_responses(b'{"status":"incomplete","output":[]}')


def test_parse_when_chat_length_exhausted_rejects() -> None:
    # Given / When / Then
    with pytest.raises(AgentError, match="provider_incomplete"):
        parse_chat(
            b'{"choices":[{"finish_reason":"length","message":{"role":"assistant","content":"partial"}}]}'
        )


def test_parse_when_schema_missing_output_rejects() -> None:
    # Given / When / Then
    with pytest.raises(AgentError, match="provider_schema_error"):
        parse_responses(b'{"choices":[]}')
