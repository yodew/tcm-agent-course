"""Application transaction orchestration independent of HTTP and CLI."""

import logging
import time
from dataclasses import dataclass
from typing import Final, assert_never
from uuid import UUID, uuid4

import anyio

from tcm_agent.config import Settings
from tcm_agent.domain import Action, RuntimeInput, TurnRequest, TurnResponse
from tcm_agent.errors import AgentError
from tcm_agent.events import ProgressSink
from tcm_agent.observability import Metrics, RateLimiter
from tcm_agent.operations import OperationClaim, OperationStore
from tcm_agent.policy import render_summary
from tcm_agent.repository import VisitRepository
from tcm_agent.runtime import AgentRuntime

LOGGER: Final = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Access:
    owner: str
    session_id: UUID


@dataclass(frozen=True, slots=True)
class Services:
    visits: VisitRepository
    operations: OperationStore
    runtime: AgentRuntime
    metrics: Metrics
    limiter: RateLimiter
    settings: Settings

    async def turn(
        self, access: Access, request: TurnRequest, emit: ProgressSink | None = None
    ) -> TurnResponse:
        """Claim before expensive work, replay before version checks, commit via CAS."""
        snapshot = await self.visits.load(access.owner, access.session_id)
        claim = await self.operations.claim(access.session_id, request)
        match claim:
            case TurnResponse():
                return claim
            case OperationClaim():
                pass
            case unreachable:
                assert_never(unreachable)
        completed = False
        started = time.monotonic()
        try:
            if request.expected_version != snapshot.version:
                raise AgentError("version_conflict", 409)
            self.limiter.check(access.owner)
            context = RuntimeInput(snapshot=snapshot, request=request, turn_id=uuid4())
            try:
                with anyio.fail_after(self.settings.turn_timeout_seconds):
                    result = await self.runtime.run(context, emit)
            except (AgentError, TimeoutError) as error:
                match error:
                    case AgentError(status=status) if status < 500:
                        raise
                    case AgentError() | TimeoutError():
                        pass
                    case unreachable:
                        assert_never(unreachable)
                LOGGER.warning("turn_degraded error_type=%s", type(error).__name__)
                result = self.runtime.handoff(context).model_copy(
                    update={
                        "action": Action.SUMMARY,
                        "status": "degraded",
                        "answer": "模型暂不可用，以下为已确认资料。\n"
                        + render_summary(snapshot.facts),
                    }
                )
            await self.operations.commit(claim, snapshot, result)
            completed = True
            self.metrics.turns.labels(status=result.status, action=result.action.value).inc()
            self.metrics.tokens.labels(direction="input").inc(result.usage.input_tokens)
            self.metrics.tokens.labels(direction="output").inc(result.usage.output_tokens)
            return result
        finally:
            self.metrics.duration.observe(time.monotonic() - started)
            if not completed:
                with anyio.move_on_after(5, shield=True):
                    await self.operations.fail(claim)
