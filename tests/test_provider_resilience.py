import anyio
import httpx2
import pytest
from pydantic import SecretStr

from tcm_agent.config import Settings
from tcm_agent.errors import AgentError
from tcm_agent.gateway import NativeConversation


@pytest.mark.anyio
async def test_post_when_transient_429_retries_same_body_with_bounded_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: two transient failures followed by success at the HTTP boundary.
    bodies: list[bytes] = []
    delays: list[float] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        bodies.append(request.content)
        return httpx2.Response(429 if len(bodies) < 3 else 200, content=b"ok")

    async def record_delay(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("tcm_agent.gateway.anyio.sleep", record_delay)
    settings = Settings(model_mode="responses", model_api_key=SecretStr("synthetic-provider-key"))
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        # When
        result = await NativeConversation(settings, client, "responses").post(
            "responses", b"synthetic"
        )
    # Then: attempts repeat the same operation body and are bounded at three.
    assert result == b"ok"
    assert bodies == [b"synthetic"] * 3
    assert len(delays) == 2
    assert 0.2 <= delays[0] <= 0.3
    assert 0.4 <= delays[1] <= 0.5


@pytest.mark.anyio
async def test_post_when_503_persists_stops_after_three_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an unavailable upstream and a controlled backoff clock.
    attempts: list[int] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        attempts.append(request.content.__len__())
        return httpx2.Response(503, text="PRIVATE UPSTREAM BODY")

    async def skip_delay(delay: float) -> None:
        del delay

    monkeypatch.setattr("tcm_agent.gateway.anyio.sleep", skip_delay)
    settings = Settings(model_mode="responses", model_api_key=SecretStr("synthetic-provider-key"))
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        # When / Then
        with pytest.raises(AgentError, match=r"^provider_http_error$"):
            await NativeConversation(settings, client, "responses").post("responses", b"synthetic")
    assert len(attempts) == 3


@pytest.mark.anyio
async def test_post_when_outer_deadline_expires_does_not_restart_attempt() -> None:
    # Given: the upstream starts but never returns, under an already exhausted deadline.
    attempts: list[int] = []

    async def handle(request: httpx2.Request) -> httpx2.Response:
        attempts.append(len(request.content))
        await anyio.sleep_forever()
        raise AssertionError("unreachable")

    settings = Settings(model_mode="responses", model_api_key=SecretStr("synthetic-provider-key"))
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as client:
        # When / Then: cancellation propagates, rather than being retried as HTTP failure.
        with pytest.raises(TimeoutError), anyio.fail_after(0):
            await NativeConversation(settings, client, "responses").post("responses", b"synthetic")
    assert len(attempts) <= 1
