"""Engine ownership and explicit schema initialization for local/test use."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tcm_agent.models import Base


def engine_for(url: str) -> AsyncEngine:
    """Prepare only the local SQLite parent; PostgreSQL is configured externally."""
    if url.startswith("sqlite+aiosqlite:///") and not url.endswith(":memory:"):
        Path(url.removeprefix("sqlite+aiosqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(url, pool_pre_ping=True)


async def initialize(engine: AsyncEngine) -> None:
    """Test helper; deployed environments use Alembic migrations instead."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
