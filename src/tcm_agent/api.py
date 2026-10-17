"""FastAPI composition root; lifespan owns every external resource."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker

from tcm_agent.config import Settings
from tcm_agent.database import engine_for
from tcm_agent.embeddings import ProviderEmbedder
from tcm_agent.errors import AgentError
from tcm_agent.gateway import Gateway, ModelGateway
from tcm_agent.http_client import create_client
from tcm_agent.observability import Metrics, RateLimiter
from tcm_agent.offline import OfflineGateway
from tcm_agent.operations import OperationStore
from tcm_agent.repository import VisitRepository
from tcm_agent.retrieval import KnowledgeBase
from tcm_agent.routes import build_router
from tcm_agent.runtime import AgentRuntime
from tcm_agent.service import Services


def create_app(settings: Settings | None = None, gateway: ModelGateway | None = None) -> FastAPI:
    """Support explicit dependency injection for offline and wire-contract tests."""
    config = settings or Settings()
    resources: list[Services] = []

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncGenerator[None]:
        if not config.access_tokens:
            raise AgentError("configure_access_tokens_before_serving", 500)
        engine = engine_for(config.database_url)
        try:
            async with create_client() as client:
                factory = async_sessionmaker(engine, expire_on_commit=False)
                knowledge = KnowledgeBase.load(config.knowledge_path)
                if config.embedding_model:
                    knowledge = await knowledge.with_embeddings(ProviderEmbedder(config, client))
                model = gateway or (
                    OfflineGateway() if config.model_mode == "offline" else Gateway(config, client)
                )
                resources.append(
                    Services(
                        VisitRepository(factory),
                        OperationStore(factory, int(config.turn_timeout_seconds) + 30),
                        AgentRuntime(model, knowledge, config.max_steps, config.context_chars),
                        Metrics.create(),
                        RateLimiter(config.rate_limit_per_minute),
                        config,
                    )
                )
                yield
        finally:
            resources.clear()
            await engine.dispose()

    app = FastAPI(
        title="中医就诊准备 Agent",
        version="1.3.0",
        lifespan=lifespan,
        description="整理资料、核对事实与知识解释。offline 模式是确定性工程夹具。",
    )
    app.include_router(build_router(config, lambda: resources[0]))

    @app.exception_handler(AgentError)
    async def agent_error(_request: Request, error: AgentError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if error.status == 401 else {}
        if error.status == 429:
            headers["Retry-After"] = "60"
        return JSONResponse(
            status_code=error.status, content={"error": error.code}, headers=headers
        )

    return app
