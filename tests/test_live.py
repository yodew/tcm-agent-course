import os
from uuid import uuid4

import anyio
import pytest

from tcm_agent.config import Settings
from tcm_agent.domain import RuntimeInput, TurnRequest, VisitSnapshot
from tcm_agent.gateway import Gateway
from tcm_agent.http_client import create_client
from tcm_agent.retrieval import KnowledgeBase
from tcm_agent.runtime import AgentRuntime


@pytest.mark.live
@pytest.mark.anyio
@pytest.mark.skipif(os.environ.get("TCM_RUN_LIVE") != "1", reason="Real provider explicitly opt-in")
async def test_live_when_provider_supports_tools_completes_grounded_turn() -> None:
    # Given: only synthetic educational input; normal configuration must select a real mode.
    settings = Settings()
    assert settings.model_mode in {"responses", "chat"}
    async with create_client() as client:
        runtime = AgentRuntime(
            Gateway(settings, client),
            KnowledgeBase.load(settings.knowledge_path),
            settings.max_steps,
            settings.context_chars,
        )
        context = RuntimeInput(
            snapshot=VisitSnapshot(
                session_id=uuid4(), version=0, facts=[], candidates=[], messages=[]
            ),
            request=TurnRequest(
                request_id=uuid4(),
                expected_version=0,
                text="请使用知识检索工具解释四诊，然后提交带引用的知识回答。",
            ),
            turn_id=uuid4(),
        )
        # When
        with anyio.fail_after(settings.turn_timeout_seconds):
            response = await runtime.run(context)
    # Then: genuine model decision, tool observation and final submission all completed.
    assert response.action == "knowledge"
    assert response.citations
    assert response.steps >= 2
