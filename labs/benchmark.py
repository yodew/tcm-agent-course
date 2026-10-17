# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python -m labs.benchmark
"""Compare evidence selection on a versioned corpus; no claim of clinical answer quality."""

import hashlib
import math
import os
from pathlib import Path
from time import perf_counter
from typing import Annotated, Final, Literal

import anyio
import typer
from pydantic import TypeAdapter

from labs.trace_runtime import RunResult, context_for, trace_run
from tcm_agent.config import Settings
from tcm_agent.domain import Contract
from tcm_agent.errors import ConfigurationError, DataContractError
from tcm_agent.gateway import Gateway, ModelGateway
from tcm_agent.http_client import create_client
from tcm_agent.offline import OfflineGateway
from tcm_agent.retrieval import KnowledgeBase
from tcm_agent.runtime import AgentRuntime

Category = Literal["exact", "paraphrase", "negation", "boundary", "unknown"]

RULES: Final = (
    ("四诊", "tcm-four-examinations"),
    ("主诉", "visit-complaint"),
    ("用药", "visit-medication"),
    ("证型", "tcm-syndrome"),
    ("舌象", "photo-limit"),
    ("授权", "privacy-consent"),
    ("摘要", "summary-fidelity"),
    ("知识解释", "knowledge-limits"),
)


class BenchmarkCase(Contract):
    case_id: str
    category: Category
    query: str
    relevant_ids: list[str]
    rationale: str


class SelectionResult(Contract):
    case_id: str
    category: Category
    system: str
    selected_ids: list[str]
    passed: bool
    latency_ms: float
    run: RunResult | None = None


class Aggregate(Contract):
    system: str
    category: str
    samples: int
    passed: int
    evidence_success_rate: float
    p50_ms: float
    p95_ms: float
    decision_calls: int
    input_tokens: int
    output_tokens: int


class BenchmarkReport(Contract):
    dataset_sha256: str
    corpus_sha256: str
    scope: str = "Top-1 evidence selection and unknown abstention on original synthetic questions; not full answer quality, clinical validation or market performance. No embedding/reranker."
    mode: str
    harness_version: str = "1.3.0"
    decision_model: str
    max_steps: int
    context_chars: int
    max_output_tokens: int
    per_case_deadline_seconds: float = 30
    summaries: list[Aggregate]
    results: list[SelectionResult]


def evidence_pass(selected: list[str], relevant: list[str]) -> bool:
    """Unknown questions require abstention; answerable questions require relevant evidence."""
    return bool(selected) and set(selected) <= set(relevant) if relevant else not selected


def load_cases(path: Path, knowledge: KnowledgeBase) -> list[BenchmarkCase]:
    """Reject duplicate cases and broken labels before spending provider calls."""
    cases = TypeAdapter(list[BenchmarkCase]).validate_json(path.read_bytes())
    ids = {entry.entry_id for entry in knowledge.entries}
    if not cases or len({case.case_id for case in cases}) != len(cases):
        raise DataContractError("Empty dataset or duplicate case IDs")
    if any(set(case.relevant_ids) - ids for case in cases):
        raise DataContractError("Unknown relevance label")
    return cases


def summarize(results: list[SelectionResult]) -> list[Aggregate]:
    """Use nearest-rank percentiles and separate categories rather than hiding failures."""
    aggregates: list[Aggregate] = []
    for system, category in sorted(
        {(r.system, "all") for r in results} | {(r.system, r.category) for r in results}
    ):
        rows = [r for r in results if r.system == system and category in ("all", r.category)]
        times = sorted(r.latency_ms for r in rows)
        runs = [r.run for r in rows if r.run is not None]
        passed = sum(r.passed for r in rows)
        aggregates.append(
            Aggregate(
                system=system,
                category=category,
                samples=len(rows),
                passed=passed,
                evidence_success_rate=passed / len(rows),
                p50_ms=times[math.ceil(len(times) * 0.5) - 1],
                p95_ms=times[math.ceil(len(times) * 0.95) - 1],
                decision_calls=sum(r.steps for r in runs),
                input_tokens=sum(r.input_tokens for r in runs),
                output_tokens=sum(r.output_tokens for r in runs),
            )
        )
    return aggregates


async def compare(
    cases: list[BenchmarkCase], knowledge: KnowledgeBase, runtime: AgentRuntime
) -> list[SelectionResult]:
    """All systems get identical questions; labels are used only after inference."""
    results: list[SelectionResult] = []
    for case in cases:
        started = perf_counter()
        rule = [entry_id for term, entry_id in RULES if term in case.query][:1]
        results.append(
            SelectionResult(
                case_id=case.case_id,
                category=case.category,
                system="keyword-rule",
                selected_ids=rule,
                passed=evidence_pass(rule, case.relevant_ids),
                latency_ms=round((perf_counter() - started) * 1000, 3),
            )
        )
        started = perf_counter()
        fixed = [entry.entry_id for entry in await knowledge.search(case.query)][:1]
        results.append(
            SelectionResult(
                case_id=case.case_id,
                category=case.category,
                system="fixed-bm25",
                selected_ids=fixed,
                passed=evidence_pass(fixed, case.relevant_ids),
                latency_ms=round((perf_counter() - started) * 1000, 3),
            )
        )
        run = await trace_run(runtime, context_for(case.query))
        selected = run.citation_ids
        results.append(
            SelectionResult(
                case_id=case.case_id,
                category=case.category,
                system="agent-runtime",
                selected_ids=selected,
                passed=not run.error
                and run.action == "knowledge"
                and evidence_pass(selected, case.relevant_ids),
                latency_ms=run.elapsed_ms,
                run=run,
            )
        )
    return results


def command(live: bool = False, limit: Annotated[int, typer.Option(min=1, max=40)] = 40) -> None:
    """Live requires both --live and TCM_RUN_LIVE=1; reports stay in ignored tmp/."""
    if live and os.environ.get("TCM_RUN_LIVE") != "1":
        raise ConfigurationError("Live benchmark requires TCM_RUN_LIVE=1 and --live")
    anyio.run(run_benchmark, live, limit)


async def run_benchmark(live: bool, limit: int) -> None:
    """Offline ignores local provider configuration and never accesses credentials."""
    settings = Settings() if live else Settings.model_construct()
    if live and settings.model_mode == "offline":
        raise ConfigurationError("Live benchmark requires responses or chat mode")
    corpus = Path("knowledge/entries.json")
    dataset = Path("knowledge/benchmark.json")
    knowledge = KnowledgeBase.load(corpus)
    cases = load_cases(dataset, knowledge)[:limit]
    async with create_client() as client:
        gateway: ModelGateway = Gateway(settings, client) if live else OfflineGateway()
        runtime = AgentRuntime(gateway, knowledge, settings.max_steps, settings.context_chars)
        results = await compare(cases, knowledge, runtime)
    report = BenchmarkReport(
        dataset_sha256=hashlib.sha256(await anyio.Path(dataset).read_bytes()).hexdigest(),
        corpus_sha256=hashlib.sha256(await anyio.Path(corpus).read_bytes()).hexdigest(),
        mode=settings.model_mode,
        decision_model=settings.model_name if live else "scripted-offline-v1",
        max_steps=settings.max_steps,
        context_chars=settings.context_chars,
        max_output_tokens=settings.max_output_tokens,
        summaries=summarize(results),
        results=results,
    )
    destination = Path("tmp/benchmark-live.json" if live else "evidence/benchmark.json")
    await anyio.Path(destination.parent).mkdir(parents=True, exist_ok=True)
    await anyio.Path(destination).write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(cases)} synthetic cases; mode={settings.model_mode}; output={destination}")
    for row in report.summaries:
        if row.category == "all":
            print(row.system, f"{row.passed}/{row.samples}", "evidence selection only")


if __name__ == "__main__":
    typer.run(command)
