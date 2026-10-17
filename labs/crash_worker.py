# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Internal worker: launched only by uv run python -m labs.crash_recovery
"""Abruptly exit after a committed operation claim in a temporary course database."""

import os
import sys
from uuid import UUID

import anyio
from sqlalchemy.ext.asyncio import async_sessionmaker

from tcm_agent.database import engine_for
from tcm_agent.domain import Contract, TurnRequest
from tcm_agent.operations import OperationStore


class CrashPlan(Contract):
    database_url: str
    session_id: UUID
    request: TurnRequest


async def claim_then_exit() -> None:
    """os._exit deliberately bypasses cleanup, only against the parent-created temp DB."""
    plan = CrashPlan.model_validate_json(await anyio.Path(sys.argv[1]).read_bytes())
    engine = engine_for(plan.database_url)
    operations = OperationStore(async_sessionmaker(engine, expire_on_commit=False), 60)
    await operations.claim(plan.session_id, plan.request)
    os._exit(73)


if __name__ == "__main__":
    anyio.run(claim_then_exit)
