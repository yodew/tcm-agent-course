# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python -m labs.crash_recovery
"""Actual process death and fencing replay, isolated from all configured user databases."""

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import anyio
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from labs.crash_worker import CrashPlan
from tcm_agent.database import engine_for, initialize
from tcm_agent.domain import Action, Contract, TurnRequest, TurnResponse, Usage
from tcm_agent.errors import AgentError, DataContractError
from tcm_agent.models import OperationRow
from tcm_agent.operations import OperationClaim, OperationStore
from tcm_agent.repository import VisitRepository


class CrashReport(Contract):
    child_exit: int
    before_expiry: str
    stale_worker: str
    version_after_stale: int
    committed_version: int
    replay_identical: bool
    scope: str = "Real SQLite child process crash; expiry timestamp controlled by SQL, no wall-clock sleep. Not PostgreSQL, failover or power-loss durability."


async def recover(directory: Path) -> CrashReport:
    """Create a private temporary database; never load Settings or model credentials."""
    url = f"sqlite+aiosqlite:///{directory}/crash.db"
    engine = engine_for(url)
    await initialize(engine)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        visits, operations = VisitRepository(factory), OperationStore(factory, 60)
        snapshot = await visits.create("synthetic-owner")
        request = TurnRequest(request_id=uuid4(), expected_version=0, text="合成崩溃演练")
        plan = CrashPlan(database_url=url, session_id=snapshot.session_id, request=request)
        plan_file = directory / "plan.json"
        await anyio.Path(plan_file).write_text(plan.model_dump_json())
        child = await anyio.to_thread.run_sync(
            lambda: subprocess.run(  # noqa: S603
                [sys.executable, "-m", "labs.crash_worker", str(plan_file)],
                capture_output=True,
                check=False,
                timeout=20,
            )
        )
        if child.returncode != 73:
            raise DataContractError("Crash worker failed before its checkpoint")
        before_expiry = ""
        try:
            await operations.claim(snapshot.session_id, request)
        except AgentError as failure:
            before_expiry = failure.code
        async with factory.begin() as db:
            row = await db.get(OperationRow, (str(snapshot.session_id), str(request.request_id)))
            if row is None:
                raise DataContractError("Committed claim did not survive child exit")
            old = OperationClaim(snapshot.session_id, request, row.lease)
            await db.execute(update(OperationRow).values(started=0))
        renewed = await operations.claim(snapshot.session_id, request)
        if not isinstance(renewed, OperationClaim):
            raise DataContractError("Expected reclaimed operation")
        response = TurnResponse(
            turn_id=uuid4(),
            session_id=snapshot.session_id,
            version=1,
            action=Action.SUMMARY,
            answer="合成确定性结果",
            candidates=[],
            citations=[],
            usage=Usage(),
            steps=0,
        )
        stale_worker = ""
        try:
            await operations.commit(old, snapshot, response)
        except AgentError as failure:
            stale_worker = failure.code
        version_after_stale = (await visits.load("synthetic-owner", snapshot.session_id)).version
        await operations.commit(renewed, snapshot, response)
        replay = await operations.claim(snapshot.session_id, request)
        return CrashReport(
            child_exit=child.returncode,
            before_expiry=before_expiry,
            stale_worker=stale_worker,
            version_after_stale=version_after_stale,
            committed_version=(await visits.load("synthetic-owner", snapshot.session_id)).version,
            replay_identical=replay == response,
        )
    finally:
        await engine.dispose()


def main() -> None:
    """Run the isolated process experiment and print path-free evidence."""
    with TemporaryDirectory(prefix="tcm-crash-") as directory:
        report = anyio.run(recover, Path(directory))
    Path("evidence/crash-recovery.json").write_text(report.model_dump_json(indent=2) + "\n")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
