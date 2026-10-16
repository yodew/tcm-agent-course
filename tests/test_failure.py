from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tcm_agent.api import create_app
from tcm_agent.config import Settings
from tcm_agent.database import engine_for, initialize
from tcm_agent.domain import Message, ModelStep, ToolResult
from tcm_agent.errors import AgentError
from tcm_agent.gateway import Conversation


@dataclass(frozen=True, slots=True)
class FailingGateway:
    def conversation(self, messages: list[Message]) -> Conversation:
        return FailingConversation()


@dataclass(frozen=True, slots=True)
class FailingConversation:
    async def step(self, observations: list[ToolResult]) -> ModelStep:
        raise AgentError("provider_http_error")


@pytest.mark.anyio
async def test_turn_when_provider_fails_persists_degraded_result(tmp_path: Path) -> None:
    # Given
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path}/failure.db",
        access_tokens={"test-token": "owner"},
    )
    engine = engine_for(settings.database_url)
    await initialize(engine)
    await engine.dispose()
    with TestClient(create_app(settings, FailingGateway())) as client:
        client.headers["Authorization"] = "Bearer test-token"
        sid = client.post("/sessions", json={"consent": True}).json()["session_id"]
        # When
        response = client.post(
            f"/sessions/{sid}/turns",
            json={"request_id": str(uuid4()), "expected_version": 0, "text": "睡不好"},
        )
        # Then
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert client.get(f"/sessions/{sid}").json()["version"] == 1
