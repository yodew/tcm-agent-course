"""HTTP-boundary regressions for reliable UI retries and safe stream rendering."""

from uuid import uuid4

import httpx2
import pytest

from tcm_agent.api import create_app
from tcm_agent.config import Settings
from tcm_agent.database import engine_for, initialize
from tcm_agent.domain import Action, ConfirmRequest, TurnRequest, TurnResponse, Usage
from tcm_agent.ui_client import UIError, VisitClient


@pytest.mark.anyio
async def test_ui_retry_when_result_uncertain_preserves_request_identity() -> None:
    # Given: a response committed on the server, with a reusable UI request.
    session_id = uuid4()
    body = TurnRequest(request_id=uuid4(), expected_version=0, text="合成测试输入")
    result = TurnResponse(
        turn_id=uuid4(),
        session_id=session_id,
        version=1,
        action=Action.ASK,
        answer="请描述",
        candidates=[],
        citations=[],
        usage=Usage(),
        steps=1,
    )
    requests: list[bytes] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request.content)
        return httpx2.Response(
            200,
            text="event: accepted\ndata: {}\n\nevent: committed\ndata: "
            + result.model_dump_json()
            + "\n\nevent: done\ndata: {}\n\n",
        )

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as http:
        client = VisitClient(http, "http://test")
        # When: the browser retries the identical operation.
        first = [event async for event in client.events(session_id, body)]
        second = [event async for event in client.events(session_id, body)]
    # Then: no new key/body is invented, and both replies expose the saved result.
    assert requests[0] == requests[1]
    assert first == second
    assert [event.kind for event in first] == ["accepted", "committed", "done"]


@pytest.mark.anyio
@pytest.mark.parametrize("frames", ["event: accepted\ndata: {}\n\n", "event: done\ndata: {}\n\n"])
async def test_ui_stream_when_truncated_never_reports_success(frames: str) -> None:
    # Given: the stream closes without a committed response and done pair.
    def handle(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, text=frames)

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as http:
        client = VisitClient(http, "http://test")
        # When: the UI consumes the response.
        with pytest.raises(UIError, match="stream_incomplete"):
            _ = [
                event
                async for event in client.events(
                    uuid4(), TurnRequest(request_id=uuid4(), expected_version=0, text="合成测试")
                )
            ]
    # Then: the error leaves the caller free to retry the same operation.


@pytest.mark.anyio
async def test_ui_error_when_backend_fails_excludes_body_and_credentials() -> None:
    # Given: a misbehaving upstream returns sensitive-looking content.
    def handle(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, text="synthetic-private-body")

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as http:
        client = VisitClient(http, "http://test")
        # When: an API operation fails.
        with pytest.raises(UIError) as failure:
            await client.create()
    # Then: the browser-facing error is bounded and excludes the upstream body.
    assert str(failure.value) == "http_500"
    assert "synthetic-private-body" not in str(failure.value)


@pytest.mark.anyio
async def test_ui_stream_when_version_rejected_preserves_definitive_error_code() -> None:
    # Given: the backend explicitly rejected the stale state without committing.
    def handle(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, text='event: error\ndata: {"error":"version_conflict"}\n\n')

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as http:
        client = VisitClient(http, "http://test")
        # When: the UI consumes the failure event.
        with pytest.raises(UIError) as failure:
            _ = [
                event
                async for event in client.events(
                    uuid4(), TurnRequest(request_id=uuid4(), expected_version=0, text="合成测试")
                )
            ]
    # Then: the adapter can clear the rejected request instead of retrying forever.
    assert failure.value.code == "version_conflict"


@pytest.mark.anyio
async def test_ui_client_when_complete_visit_uses_authorized_api_state(settings: Settings) -> None:
    # Given: a real SQLite-backed application; no model or repository mocks.
    engine = engine_for(settings.database_url)
    await initialize(engine)
    await engine.dispose()
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            headers={"Authorization": "Bearer alice-test-token"},
        ) as http,
    ):
        client = VisitClient(http, "http://test")
        # When: one visit is created, submitted, confirmed, withdrawn and deleted.
        health = await client.health()
        created = await client.create()
        request = TurnRequest(request_id=uuid4(), expected_version=0, text="最近睡不好")
        events = [event async for event in client.events(created.session_id, request)]
        replay = [event async for event in client.events(created.session_id, request)]
        result = TurnResponse.model_validate_json(
            next(e.data for e in events if e.kind == "committed")
        )
        before = await client.summary(created.session_id)
        candidate = result.candidates[0]
        confirmed = await client.confirm(
            created.session_id,
            ConfirmRequest(
                expected_version=1,
                field=candidate.field,
                quote=candidate.quote,
                source_turn_id=candidate.source_turn_id,
            ),
        )
        after = await client.summary(created.session_id)
        withdrawn = await client.remove(confirmed, candidate.field)
        removed_summary = await client.summary(created.session_id)
        http.headers["Authorization"] = "Bearer bob-test-token"
        with pytest.raises(UIError, match="http_404"):
            await client.load(created.session_id)
        http.headers["Authorization"] = "Bearer alice-test-token"
        await client.delete(created.session_id)
        with pytest.raises(UIError, match="http_404"):
            await client.load(created.session_id)
    # Then: replay, provenance, confirmation, withdrawal and identity isolation hold.
    assert result.model_dump_json() == next(e.data for e in replay if e.kind == "committed")
    assert "最近睡不好" not in before
    assert "最近睡不好" in after
    assert "最近睡不好" not in removed_summary
    assert withdrawn.version == 3
    assert health.model_mode == "offline"
