import os
from collections.abc import Iterator
from pathlib import Path

import anyio
import pytest
from fastapi.testclient import TestClient

from tcm_agent.api import create_app
from tcm_agent.config import Settings
from tcm_agent.database import engine_for, initialize


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        model_mode="offline",
        database_url=f"sqlite+aiosqlite:///{tmp_path}/test.db",
        access_tokens={"alice-test-token": "alice", "bob-test-token": "bob"},
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    async def setup() -> None:
        engine = engine_for(settings.database_url)
        await initialize(engine)
        await engine.dispose()

    anyio.run(setup)
    with TestClient(create_app(settings)) as active:
        active.headers["Authorization"] = "Bearer alice-test-token"
        yield active


@pytest.fixture(autouse=True)
def isolate_provider_settings(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normal tests must never read a developer's real API credentials or local .env."""
    if request.node.get_closest_marker("live"):
        return
    for key in list(os.environ):
        if key.startswith("TCM_") and key not in {"TCM_TEST_DATABASE_URL", "TCM_RUN_LIVE"}:
            monkeypatch.delenv(key)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
