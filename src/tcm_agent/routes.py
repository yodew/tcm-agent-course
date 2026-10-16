"""Authenticated API surface; identity is never accepted from request bodies."""

import secrets
from collections.abc import Callable
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from tcm_agent.config import Settings
from tcm_agent.domain import (
    ConfirmRequest,
    Contract,
    FactField,
    TurnRecord,
    TurnRequest,
    TurnResponse,
    VisitSnapshot,
)
from tcm_agent.errors import AgentError
from tcm_agent.policy import render_summary
from tcm_agent.service import Access, Services
from tcm_agent.streaming import stream_turn


class CreateVisit(Contract):
    consent: Literal[True]


class Health(Contract):
    status: str
    model_mode: str


def build_router(settings: Settings, get_services: Callable[[], Services]) -> APIRouter:  # noqa: C901
    # The complexity count includes independent HTTP route declarations.
    """Inject typed resources with an app-local closure, not untyped app.state."""
    router = APIRouter()
    bearer = HTTPBearer(auto_error=False)

    def owner(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str:
        if credentials is None:
            raise AgentError("authentication_required", 401)
        for token, identity in settings.access_tokens.items():
            if secrets.compare_digest(credentials.credentials.encode(), token.encode()):
                return identity
        raise AgentError("invalid_token", 401)

    @router.get("/health")
    async def health() -> Health:
        return Health(status="ok", model_mode=settings.model_mode)

    @router.post("/sessions", status_code=201)
    async def create(_body: CreateVisit, identity: Annotated[str, Depends(owner)]) -> VisitSnapshot:
        return await get_services().visits.create(identity)

    @router.get("/sessions/{session_id}")
    async def read(session_id: UUID, identity: Annotated[str, Depends(owner)]) -> VisitSnapshot:
        return await get_services().visits.load(identity, session_id)

    @router.delete("/sessions/{session_id}", status_code=204)
    async def delete(session_id: UUID, identity: Annotated[str, Depends(owner)]) -> Response:
        await get_services().visits.delete(identity, session_id)
        return Response(status_code=204)

    @router.post("/sessions/{session_id}/turns")
    async def turn(
        session_id: UUID, body: TurnRequest, identity: Annotated[str, Depends(owner)]
    ) -> TurnResponse:
        return await get_services().turn(Access(identity, session_id), body)

    @router.patch("/sessions/{session_id}/facts")
    async def confirm(
        session_id: UUID, body: ConfirmRequest, identity: Annotated[str, Depends(owner)]
    ) -> VisitSnapshot:
        return await get_services().visits.confirm(identity, session_id, body)

    @router.delete("/sessions/{session_id}/facts/{field}")
    async def remove_fact(
        session_id: UUID,
        field: FactField,
        version: Annotated[int, Query(ge=0)],
        identity: Annotated[str, Depends(owner)],
    ) -> VisitSnapshot:
        return await get_services().visits.remove_fact(identity, session_id, field.value, version)

    @router.get("/sessions/{session_id}/summary", response_class=PlainTextResponse)
    async def summary(session_id: UUID, identity: Annotated[str, Depends(owner)]) -> str:
        snapshot = await get_services().visits.load(identity, session_id)
        return render_summary(snapshot.facts)

    @router.get("/sessions/{session_id}/records")
    async def records(
        session_id: UUID, identity: Annotated[str, Depends(owner)]
    ) -> list[TurnRecord]:
        return await get_services().visits.records(identity, session_id)

    @router.post("/sessions/{session_id}/events")
    async def stream(
        session_id: UUID, body: TurnRequest, identity: Annotated[str, Depends(owner)]
    ) -> StreamingResponse:
        await get_services().visits.load(identity, session_id)
        frames = stream_turn(get_services(), Access(identity, session_id), body)
        return StreamingResponse(
            frames,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.get("/metrics")
    async def metrics(_identity: Annotated[str, Depends(owner)]) -> Response:
        return Response(
            content=generate_latest(get_services().metrics.registry),
            headers={"Content-Type": CONTENT_TYPE_LATEST},
        )

    return router
