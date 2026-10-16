from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import anyio
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tcm_agent.config import Settings
from tcm_agent.database import engine_for, initialize
from tcm_agent.domain import Message, ModelStep, ToolResult, TurnRequest
from tcm_agent.gateway import Conversation
from tcm_agent.models import OperationRow
from tcm_agent.observability import Metrics, RateLimiter
from tcm_agent.offline import OfflineGateway
from tcm_agent.operations import OperationStore
from tcm_agent.repository import VisitRepository
from tcm_agent.retrieval import KnowledgeBase
from tcm_agent.runtime import AgentRuntime
from tcm_agent.service import Access, Services


@dataclass(frozen=True, slots=True)
class BlockedGateway:
    entered: anyio.Event

    def conversation(self, messages: list[Message]) -> Conversation:
        return BlockedConversation(self.entered)


@dataclass(frozen=True, slots=True)
class BlockedConversation:
    entered: anyio.Event

    async def step(self, observations: list[ToolResult]) -> ModelStep:
        self.entered.set()
        await anyio.sleep_forever()


@pytest.mark.anyio
async def test_turn_when_cancelled_releases_claim_and_retry_can_complete(tmp_path: Path) -> None:
    # Given: real DB and a provider boundary waiting forever, not a sleep-based race.
    settings = Settings(database_url=f"sqlite+aiosqlite:///{tmp_path}/cancel.db")
    engine = engine_for(settings.database_url)
    await initialize(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    visits = VisitRepository(factory)
    operations = OperationStore(factory, 120)
    knowledge = KnowledgeBase.load(Path("knowledge/entries.json"))
    entered = anyio.Event()
    service = Services(
        visits,
        operations,
        AgentRuntime(BlockedGateway(entered), knowledge, 6, 16000),
        Metrics.create(),
        RateLimiter(20),
        settings,
    )
    snapshot = await visits.create("owner")
    access = Access("owner", snapshot.session_id)
    request = TurnRequest(request_id=uuid4(), expected_version=0, text="睡不好")
    try:
        # When: caller cancels a running turn.
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(service.turn, access, request)
            await entered.wait()
            tasks.cancel_scope.cancel()
        # Then: same request is retryable immediately; no ghost version increment.
        async with factory() as db:
            assert await db.scalar(select(OperationRow.status)) == "failed"
        retried = Services(
            visits,
            operations,
            AgentRuntime(OfflineGateway(), knowledge, 6, 16000),
            Metrics.create(),
            RateLimiter(20),
            settings,
        )
        result = await retried.turn(access, request)
        assert result.version == 1
        assert (await visits.load("owner", snapshot.session_id)).version == 1
    finally:
        await engine.dispose()
