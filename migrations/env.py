"""Async Alembic environment; model API credentials are never read here."""

from alembic import context
from sqlalchemy import Connection

import anyio

from tcm_agent.config import Settings
from tcm_agent.database import engine_for
from tcm_agent.models import Base


def migrate(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run() -> None:
    engine = engine_for(Settings().database_url)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(
        url=Settings().database_url, target_metadata=Base.metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    anyio.run(run)
