"""Idempotency, crash recovery fencing and atomic turn commits."""

import hashlib
import time
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tcm_agent.domain import TurnRequest, TurnResponse, VisitSnapshot
from tcm_agent.errors import AgentError
from tcm_agent.models import OperationRow, VisitRow
from tcm_agent.repository import apply_turn


@dataclass(frozen=True, slots=True)
class OperationClaim:
    session_id: UUID
    request: TurnRequest
    lease: str


@dataclass(frozen=True, slots=True)
class OperationStore:
    factory: async_sessionmaker[AsyncSession]
    stale_seconds: int

    async def claim(self, session_id: UUID, request: TurnRequest) -> OperationClaim | TurnResponse:
        """Same key/different payload is forbidden; running work is never duplicated."""
        digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        lease = str(uuid4())
        try:
            async with self.factory.begin() as db:
                db.add(
                    OperationRow(
                        session_id=str(session_id),
                        request_id=str(request.request_id),
                        body_hash=digest,
                        request_text=request.text,
                        status="running",
                        lease=lease,
                        started=int(time.time()),
                        response="",
                    )
                )
        except IntegrityError:
            return await self.reclaim(OperationClaim(session_id, request, lease), digest)
        return OperationClaim(session_id, request, lease)

    async def reclaim(self, claim: OperationClaim, digest: str) -> OperationClaim | TurnResponse:
        """A new lease fences an old worker that survived a process crash timeout."""
        async with self.factory.begin() as db:
            row = await db.get(OperationRow, (str(claim.session_id), str(claim.request.request_id)))
            if row is None:
                raise AgentError("session_not_found", 404)
            if row.body_hash != digest:
                raise AgentError("idempotency_payload_conflict", 409)
            if row.status == "completed":
                return TurnResponse.model_validate_json(row.response)
            now = int(time.time())
            if row.status == "running" and now - row.started <= self.stale_seconds:
                raise AgentError("request_in_progress", 409)
            old_lease = row.lease
            updated = await db.scalar(
                update(OperationRow)
                .where(
                    OperationRow.session_id == str(claim.session_id),
                    OperationRow.request_id == str(claim.request.request_id),
                    OperationRow.lease == old_lease,
                    OperationRow.status == row.status,
                    OperationRow.started == row.started,
                )
                .values(lease=claim.lease, status="running", started=now)
                .returning(OperationRow.lease)
            )
            if updated is None:
                raise AgentError("request_in_progress", 409)
        return claim

    async def commit(
        self, claim: OperationClaim, snapshot: VisitSnapshot, response: TurnResponse
    ) -> None:
        """Result replay and new session state commit in one transaction."""
        revised = apply_turn(snapshot, response, claim.request.text)
        async with self.factory.begin() as db:
            changed = await db.scalar(
                update(VisitRow)
                .where(
                    VisitRow.id == str(claim.session_id),
                    VisitRow.version == claim.request.expected_version,
                )
                .values(version=revised.version, state=revised.model_dump_json())
                .returning(VisitRow.id)
            )
            if changed is None:
                raise AgentError("version_conflict", 409)
            fenced = await db.scalar(
                update(OperationRow)
                .where(
                    OperationRow.session_id == str(claim.session_id),
                    OperationRow.request_id == str(claim.request.request_id),
                    OperationRow.lease == claim.lease,
                    OperationRow.status == "running",
                )
                .values(status="completed", response=response.model_dump_json())
                .returning(OperationRow.lease)
            )
            if fenced is None:
                raise AgentError("operation_lease_lost", 409)

    async def fail(self, claim: OperationClaim) -> None:
        """Release only this worker's lease; never overwrite a newer or completed one."""
        async with self.factory.begin() as db:
            await db.execute(
                update(OperationRow)
                .where(
                    OperationRow.session_id == str(claim.session_id),
                    OperationRow.request_id == str(claim.request.request_id),
                    OperationRow.lease == claim.lease,
                    OperationRow.status == "running",
                )
                .values(status="failed")
            )
