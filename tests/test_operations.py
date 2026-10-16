from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from tcm_agent.database import engine_for, initialize
from tcm_agent.domain import Action, TurnRequest, TurnResponse, Usage
from tcm_agent.errors import AgentError
from tcm_agent.models import OperationRow
from tcm_agent.operations import OperationClaim, OperationStore
from tcm_agent.repository import VisitRepository


@asynccontextmanager
async def stores(tmp_path: Path) -> AsyncGenerator[tuple[VisitRepository, OperationStore]]:
    engine = engine_for(f"sqlite+aiosqlite:///{tmp_path}/ops.db")
    await initialize(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield VisitRepository(factory), OperationStore(factory, 60)
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_commit_when_lease_reclaimed_rejects_old_worker_and_rolls_back(
    tmp_path: Path,
) -> None:
    # Given: a crashed/expired worker, followed by a new lease.
    async with stores(tmp_path) as (visits, operations):
        snapshot = await visits.create("owner")
        request = TurnRequest(request_id=uuid4(), expected_version=0, text="synthetic")
        old = await operations.claim(snapshot.session_id, request)
        assert isinstance(old, OperationClaim)
        async with operations.factory.begin() as db:
            await db.execute(update(OperationRow).values(started=0))
        current = await operations.claim(snapshot.session_id, request)
        assert isinstance(current, OperationClaim)
        response = TurnResponse(
            turn_id=uuid4(),
            session_id=snapshot.session_id,
            version=1,
            action=Action.SUMMARY,
            answer="synthetic",
            candidates=[],
            citations=[],
            usage=Usage(),
            steps=0,
        )
        # When: stale worker tries to commit.
        with pytest.raises(AgentError, match="operation_lease_lost"):
            await operations.commit(old, snapshot, response)
        # Then: session update rolled back; current lease can still commit atomically.
        assert (await visits.load("owner", snapshot.session_id)).version == 0
        await operations.commit(current, snapshot, response)
        replay = await operations.claim(snapshot.session_id, request)
        assert replay == response


@pytest.mark.anyio
async def test_claim_when_other_worker_running_rejects_duplicate(tmp_path: Path) -> None:
    # Given
    async with stores(tmp_path) as (visits, operations):
        snapshot = await visits.create("owner")
        request = TurnRequest(request_id=uuid4(), expected_version=0, text="synthetic")
        await operations.claim(snapshot.session_id, request)
        # When / Then
        with pytest.raises(AgentError, match="request_in_progress"):
            await operations.claim(snapshot.session_id, request)
