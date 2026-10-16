"""Short database transactions; no network awaits while holding DB locks."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tcm_agent.domain import ConfirmRequest, Fact, Message, TurnRecord, TurnResponse, VisitSnapshot
from tcm_agent.errors import AgentError
from tcm_agent.models import OperationRow, VisitRow


@dataclass(frozen=True, slots=True)
class VisitRepository:
    factory: async_sessionmaker[AsyncSession]

    async def create(self, owner: str) -> VisitSnapshot:
        """Explicit session creation is the consent boundary."""
        snapshot = VisitSnapshot(
            session_id=uuid4(), version=0, facts=[], candidates=[], messages=[]
        )
        async with self.factory.begin() as db:
            db.add(
                VisitRow(
                    id=str(snapshot.session_id),
                    owner=owner,
                    version=0,
                    state=snapshot.model_dump_json(),
                )
            )
        return snapshot

    async def load(self, owner: str, session_id: UUID) -> VisitSnapshot:
        """Always scope reads by owner; foreign and missing IDs both return 404."""
        async with self.factory() as db:
            state = await db.scalar(
                select(VisitRow.state).where(
                    VisitRow.id == str(session_id), VisitRow.owner == owner
                )
            )
            if state is None:
                raise AgentError("session_not_found", 404)
            return VisitSnapshot.model_validate_json(state)

    async def replace(self, owner: str, snapshot: VisitSnapshot) -> None:
        """CAS prevents stale turns or confirmations from overwriting newer state."""
        async with self.factory.begin() as db:
            row = await db.scalar(
                update(VisitRow)
                .where(
                    VisitRow.id == str(snapshot.session_id),
                    VisitRow.owner == owner,
                    VisitRow.version == snapshot.version - 1,
                )
                .values(version=snapshot.version, state=snapshot.model_dump_json())
                .returning(VisitRow.id)
            )
            if row is None:
                raise AgentError("version_conflict", 409)

    async def confirm(self, owner: str, session_id: UUID, request: ConfirmRequest) -> VisitSnapshot:
        """Confirm/correct only a quote grounded in an actual input turn."""
        snapshot = await self.load(owner, session_id)
        if snapshot.version != request.expected_version:
            raise AgentError("version_conflict", 409)
        candidate = next(
            (
                f
                for f in snapshot.candidates
                if f.source_turn_id == request.source_turn_id and f.quote == request.quote
            ),
            None,
        )
        if candidate is None:
            raise AgentError("candidate_not_found", 422)
        fact = Fact(
            field=request.field,
            quote=request.quote,
            source_turn_id=request.source_turn_id,
            confirmed=True,
        )
        facts = [f for f in snapshot.facts if f.field != request.field] + [fact]
        revised = snapshot.model_copy(
            update={
                "version": snapshot.version + 1,
                "facts": facts,
                "candidates": [f for f in snapshot.candidates if f != candidate],
            }
        )
        await self.replace(owner, revised)
        return revised

    async def remove_fact(
        self, owner: str, session_id: UUID, field: str, version: int
    ) -> VisitSnapshot:
        """Explicit removal also invalidates concurrent in-flight turns."""
        snapshot = await self.load(owner, session_id)
        if snapshot.version != version:
            raise AgentError("version_conflict", 409)
        revised = snapshot.model_copy(
            update={
                "version": version + 1,
                "facts": [f for f in snapshot.facts if f.field.value != field],
            }
        )
        await self.replace(owner, revised)
        return revised

    async def delete(self, owner: str, session_id: UUID) -> None:
        """Delete state and replay payloads atomically; backups need separate retention."""
        async with self.factory.begin() as db:
            exists = await db.scalar(
                select(VisitRow.id)
                .where(VisitRow.id == str(session_id), VisitRow.owner == owner)
                .with_for_update()
            )
            if exists is None:
                raise AgentError("session_not_found", 404)
            await db.execute(delete(OperationRow).where(OperationRow.session_id == str(session_id)))
            await db.execute(
                delete(VisitRow).where(VisitRow.id == str(session_id), VisitRow.owner == owner)
            )

    async def records(self, owner: str, session_id: UUID) -> list[TurnRecord]:
        """Export source inputs and committed responses, scoped in the actual query."""
        await self.load(owner, session_id)
        async with self.factory() as db:
            rows = (
                await db.execute(
                    select(OperationRow.request_text, OperationRow.response)
                    .join(VisitRow, VisitRow.id == OperationRow.session_id)
                    .where(
                        VisitRow.owner == owner,
                        VisitRow.id == str(session_id),
                        OperationRow.status == "completed",
                    )
                    .order_by(OperationRow.started, OperationRow.request_id)
                )
            ).all()
            return [
                TurnRecord(request_text=text, response=TurnResponse.model_validate_json(raw))
                for text, raw in rows
            ]


def apply_turn(snapshot: VisitSnapshot, response: TurnResponse, text: str) -> VisitSnapshot:
    """Persist facts separately from bounded display history; proposals stay unconfirmed."""
    messages = [
        *snapshot.messages,
        Message(role="user", content=text),
        Message(role="assistant", content=response.answer),
    ]
    return snapshot.model_copy(
        update={
            "version": response.version,
            "candidates": (snapshot.candidates + response.candidates)[-30:],
            "messages": messages[-12:],
        }
    )
