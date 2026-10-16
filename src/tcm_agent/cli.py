"""Developer commands share the exact runtime used by the HTTP application."""

import json
from pathlib import Path
from uuid import uuid4

import anyio
import typer
import uvicorn
from alembic import command
from alembic.config import Config
from rich.console import Console

from tcm_agent.api import create_app
from tcm_agent.config import Settings
from tcm_agent.domain import RuntimeInput, TurnRequest, VisitSnapshot
from tcm_agent.evaluation import evaluate_retrieval
from tcm_agent.gateway import Gateway
from tcm_agent.http_client import create_client
from tcm_agent.ingestion import ingest
from tcm_agent.offline import OfflineGateway
from tcm_agent.retrieval import KnowledgeBase
from tcm_agent.runtime import AgentRuntime

app = typer.Typer(help="Python Agent course tools")
console = Console()


@app.command()
def init_db() -> None:
    """Upgrade schema with versioned migrations, never auto-create on serve."""
    command.upgrade(Config("alembic.ini"), "head")
    console.print("Schema upgraded to head.")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start API and interactive OpenAPI docs at /docs."""
    uvicorn.run(create_app(), host=host, port=port)


async def inspect_runtime(text: str) -> None:
    """Exercise the full model/tool/evidence path with no persistence."""
    settings = Settings()
    async with create_client() as client:
        gateway = (
            OfflineGateway() if settings.model_mode == "offline" else Gateway(settings, client)
        )
        runtime = AgentRuntime(
            gateway,
            KnowledgeBase.load(settings.knowledge_path),
            settings.max_steps,
            settings.context_chars,
        )
        context = RuntimeInput(
            snapshot=VisitSnapshot(
                session_id=uuid4(), version=0, facts=[], candidates=[], messages=[]
            ),
            request=TurnRequest(request_id=uuid4(), expected_version=0, text=text),
            turn_id=uuid4(),
        )
        with anyio.fail_after(settings.turn_timeout_seconds):
            result = await runtime.run(context)
        console.print_json(result.model_dump_json())


@app.command()
def run(text: str = "什么是四诊？") -> None:
    """Run one turn. Offline is a deterministic fixture, not model quality evidence."""
    anyio.run(inspect_runtime, text)


@app.command()
def evaluate(output: str = "evidence/retrieval-eval.json") -> None:
    """Evaluate retrieval against labeled queries, with explicit denominators."""
    anyio.run(evaluate_retrieval, Path(output))


@app.command()
def doctor() -> None:
    """Print safe configuration metadata only; never credentials or token maps."""
    settings = Settings()
    console.print_json(
        json.dumps(
            {
                "mode": settings.model_mode,
                "model": settings.model_name,
                "key_configured": bool(settings.model_api_key.get_secret_value()),
                "auth_identities": len(set(settings.access_tokens.values())),
                "knowledge_exists": settings.knowledge_path.is_file(),
            },
            ensure_ascii=False,
        )
    )


@app.command("ingest")
def ingest_command(manifest: str, destination: str = "data/knowledge.json") -> None:
    """Ingest an administrator-reviewed Markdown manifest into a versioned corpus."""
    console.print(
        f"Wrote {ingest(Path(manifest), Path(destination))} approved chunks to {destination}"
    )
