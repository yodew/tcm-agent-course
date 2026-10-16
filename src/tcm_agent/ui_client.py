"""Typed HTTP boundary for the Chainlit UI; the API remains the state authority."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, assert_never
from uuid import UUID

import httpx2

from tcm_agent.domain import (
    ConfirmRequest,
    Contract,
    FactField,
    TurnRequest,
    TurnResponse,
    VisitSnapshot,
)
from tcm_agent.events import Progress


class UIError(RuntimeError):
    """Expose only a safe code to the browser, never response bodies or credentials."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code: str = code


class StreamEvent(Contract):
    kind: Literal["accepted", "progress", "committed", "done", "error"]
    data: str


class StreamError(Contract):
    error: str


class APIHealth(Contract):
    status: str
    model_mode: Literal["offline", "responses", "chat"]


@dataclass(frozen=True, slots=True)
class VisitClient:
    """Borrow a scoped HTTP client; credentials stay in server-side headers."""

    http: httpx2.AsyncClient
    base_url: str

    async def health(self) -> APIHealth:
        """Read the actual backend mode instead of guessing from UI settings."""
        response = await self.http.get(self.base_url + "/health")
        check_status(response)
        return APIHealth.model_validate_json(response.content)

    async def create(self) -> VisitSnapshot:
        """Create only after the user explicitly agrees to data processing."""
        response = await self.http.post(self.base_url + "/sessions", json={"consent": True})
        check_status(response)
        return VisitSnapshot.model_validate_json(response.content)

    async def load(self, session_id: UUID) -> VisitSnapshot:
        """Read the current authoritative version before a UI mutation."""
        response = await self.http.get(f"{self.base_url}/sessions/{session_id}")
        check_status(response)
        return VisitSnapshot.model_validate_json(response.content)

    async def confirm(self, session_id: UUID, body: ConfirmRequest) -> VisitSnapshot:
        """The API verifies quote provenance, ownership and optimistic version."""
        response = await self.http.patch(
            f"{self.base_url}/sessions/{session_id}/facts", json=body.model_dump(mode="json")
        )
        check_status(response)
        return VisitSnapshot.model_validate_json(response.content)

    async def remove(self, snapshot: VisitSnapshot, field: FactField) -> VisitSnapshot:
        """Withdraw a confirmed fact so corrections never silently overwrite it."""
        response = await self.http.delete(
            f"{self.base_url}/sessions/{snapshot.session_id}/facts/{field.value}",
            params={"version": snapshot.version},
        )
        check_status(response)
        return VisitSnapshot.model_validate_json(response.content)

    async def summary(self, session_id: UUID) -> str:
        """Obtain the deterministic summary without another model request."""
        response = await self.http.get(f"{self.base_url}/sessions/{session_id}/summary")
        check_status(response)
        return response.text

    async def delete(self, session_id: UUID) -> None:
        """Delete API records; Chainlit has no configured persistent data layer."""
        response = await self.http.delete(f"{self.base_url}/sessions/{session_id}")
        check_status(response)

    async def events(self, session_id: UUID, body: TurnRequest) -> AsyncIterator[StreamEvent]:
        """Consume named SSE frames; truncated streams never count as successful."""
        event_name = ""
        data: list[str] = []
        committed = False
        async with self.http.stream(
            "POST",
            f"{self.base_url}/sessions/{session_id}/events",
            json=body.model_dump(mode="json"),
            timeout=httpx2.Timeout(connect=5, read=120, write=10, pool=10),
        ) as response:
            check_status(response)
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data.append(line[5:].lstrip(" "))
                elif not line and event_name:
                    event = StreamEvent.model_validate(
                        {"kind": event_name, "data": "\n".join(data)}
                    )
                    check_event(event)
                    committed = committed or event.kind == "committed"
                    if event.kind == "done" and not committed:
                        raise UIError("stream_incomplete")
                    yield event
                    if event.kind == "done":
                        return
                    event_name, data = "", []
        raise UIError("stream_incomplete")


def check_event(event: StreamEvent) -> None:
    """Validate untrusted SSE payloads before presenting anything to the user."""
    match event.kind:
        case "progress":
            Progress.model_validate_json(event.data)
        case "committed":
            TurnResponse.model_validate_json(event.data)
        case "error":
            error = StreamError.model_validate_json(event.data)
            raise UIError(error.error)
        case "accepted" | "done":
            pass
        case unreachable:
            assert_never(unreachable)


def check_status(response: httpx2.Response) -> None:
    """Map all unsuccessful statuses to bounded messages; discard error bodies."""
    if not response.is_success:
        raise UIError(f"http_{response.status_code}")
