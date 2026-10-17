# /// script
# requires-python = ">=3.12"
# dependencies = ["tcm-agent-course"]
# [tool.uv.sources]
# tcm-agent-course = { path = "..", editable = true }
# ///
# Run: uv run python examples/load_probe.py
"""A small real loopback HTTP probe; isolated database, ephemeral port and transient token."""

import math
import multiprocessing
import secrets
import socket
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import uuid4

import anyio
import httpx2
import uvicorn

from tcm_agent.api import create_app
from tcm_agent.config import Settings
from tcm_agent.database import engine_for, initialize
from tcm_agent.domain import Contract, TurnRequest, TurnResponse
from tcm_agent.http_client import create_client
from tcm_agent.ui_client import UIError, VisitClient, check_status


class ProbeResult(Contract):
    ok: bool
    elapsed_ms: float
    error: str = ""


class ProbeReport(Contract):
    mode: str = "offline"
    samples: int
    concurrency: int
    passed: int
    failed: int
    p50_ms: float
    p95_ms: float
    total_ms: float
    results: list[ProbeResult]
    scope: str = "24 independent sessions, concurrency=4, actual loopback HTTP turn latency only; setup/delete excluded per sample. Rate limit raised to 1000/min only in isolated probe; not provider capacity or production SLO."


def serve(settings: Settings, listener: socket.socket) -> None:
    """Spawned worker receives trusted explicit config and one loopback socket."""
    config = uvicorn.Config(create_app(settings), log_level="critical", access_log=False)
    uvicorn.Server(config).run(sockets=[listener])


async def initialize_database(url: str) -> None:
    """Prepare only the private probe database."""
    engine = engine_for(url)
    try:
        await initialize(engine)
    finally:
        await engine.dispose()


async def probe(base_url: str, token: str) -> ProbeReport:
    """Run actual HTTP requests with bounded concurrency and explicit failure accounting."""
    results: list[ProbeResult] = []
    limiter = anyio.CapacityLimiter(4)
    async with create_client() as http:
        http.headers["Authorization"] = "Bearer " + token
        client = VisitClient(http, base_url)
        with anyio.fail_after(10):
            health = await client.health()
        if health.model_mode != "offline":
            raise UIError("probe_requires_offline")

        async def one() -> None:
            async with limiter:
                snapshot = await client.create()
                started = perf_counter()
                try:
                    body = TurnRequest(request_id=uuid4(), expected_version=0, text="什么是四诊？")
                    response = await http.post(
                        f"{base_url}/sessions/{snapshot.session_id}/turns",
                        json=body.model_dump(mode="json"),
                    )
                    check_status(response)
                    turn = TurnResponse.model_validate_json(response.content)
                    ok = (
                        turn.status == "completed"
                        and bool(turn.citations)
                        and turn.citations[0].entry_id == "tcm-four-examinations"
                    )
                    results.append(
                        ProbeResult(
                            ok=ok,
                            elapsed_ms=(perf_counter() - started) * 1000,
                            error="" if ok else "unexpected_result",
                        )
                    )
                except (UIError, httpx2.TransportError) as error:
                    results.append(
                        ProbeResult(
                            ok=False,
                            elapsed_ms=(perf_counter() - started) * 1000,
                            error=type(error).__name__,
                        )
                    )
                finally:
                    await client.delete(snapshot.session_id)

        started = perf_counter()
        async with anyio.create_task_group() as group:
            for _ in range(24):
                group.start_soon(one)
        total = (perf_counter() - started) * 1000
    times = sorted(row.elapsed_ms for row in results)
    passed = sum(row.ok for row in results)
    return ProbeReport(
        samples=len(results),
        concurrency=4,
        passed=passed,
        failed=len(results) - passed,
        p50_ms=times[math.ceil(len(times) * 0.5) - 1],
        p95_ms=times[math.ceil(len(times) * 0.95) - 1],
        total_ms=total,
        results=results,
    )


def main() -> None:
    """Cleanly stop the child before removing the private database directory."""
    with TemporaryDirectory(prefix="tcm-probe-") as temporary, socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(32)
        url = f"sqlite+aiosqlite:///{temporary}/probe.db"
        token = secrets.token_urlsafe(32)
        settings = Settings.model_construct(
            database_url=url, access_tokens={token: "probe"}, rate_limit_per_minute=1000
        )
        anyio.run(initialize_database, url)
        child = multiprocessing.get_context("spawn").Process(
            target=serve, args=(settings, listener)
        )
        child.start()
        try:
            report = anyio.run(probe, f"http://127.0.0.1:{listener.getsockname()[1]}", token)
        finally:
            child.terminate()
            child.join(timeout=5)
            if child.is_alive():
                child.kill()
                child.join(timeout=2)
    Path("evidence/load-probe.json").write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Actual HTTP probe: {report.passed}/{report.samples}; concurrency={report.concurrency}; p95={report.p95_ms:.2f}ms; offline only"
    )


if __name__ == "__main__":
    main()
