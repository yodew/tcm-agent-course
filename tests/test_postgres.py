import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tcm_agent.database import engine_for, initialize
from tcm_agent.domain import Action, TurnRequest, TurnResponse, Usage
from tcm_agent.errors import AgentError
from tcm_agent.operations import OperationClaim, OperationStore
from tcm_agent.repository import VisitRepository


@pytest.mark.postgres
@pytest.mark.anyio
@pytest.mark.skipif(
    not os.environ.get("TCM_TEST_DATABASE_URL"), reason="PostgreSQL explicitly opt-in"
)
async def test_postgres_when_two_snapshots_compete_commits_only_one() -> None:
    # Given: isolated schema in an explicitly supplied TEST database, never production data.
    engine = engine_for(os.environ["TCM_TEST_DATABASE_URL"])
    namespace = "course_test_" + uuid4().hex
    async with engine.begin() as db:
        await db.execute(text(f'CREATE SCHEMA "{namespace}"'))
    isolated = engine.execution_options(schema_translate_map={None: namespace})
    try:
        await initialize(isolated)
        factory = async_sessionmaker(isolated, expire_on_commit=False)
        visits = VisitRepository(factory)
        operations = OperationStore(factory, 120)
        snapshot = await visits.create("owner")
        first = await operations.claim(
            snapshot.session_id, TurnRequest(request_id=uuid4(), expected_version=0, text="first")
        )
        second = await operations.claim(
            snapshot.session_id, TurnRequest(request_id=uuid4(), expected_version=0, text="second")
        )
        assert isinstance(first, OperationClaim)
        assert isinstance(second, OperationClaim)
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
        await operations.commit(first, snapshot, response)
        # When / Then: a stale PG snapshot is rejected without partial replay completion.
        with pytest.raises(AgentError, match="version_conflict"):
            await operations.commit(second, snapshot, response)
        assert (await visits.load("owner", snapshot.session_id)).version == 1
    finally:
        async with engine.begin() as db:
            await db.execute(text(f'DROP SCHEMA "{namespace}" CASCADE'))
        await engine.dispose()
