from pathlib import Path

import pytest

from labs.benchmark import SelectionResult, command, evidence_pass, load_cases, summarize
from labs.trace_demo import run_examples
from tcm_agent.errors import ConfigurationError, DataContractError
from tcm_agent.retrieval import KnowledgeBase


@pytest.mark.anyio
async def test_trace_when_bad_decisions_rejects_at_real_runtime_boundary() -> None:
    # Given / When
    report = await run_examples()
    # Then: real policy/loop failures, not expected answers substituted by a simulator.
    assert report.runs["knowledge"].citation_ids == ["tcm-four-examinations"]
    assert report.runs["knowledge"].events[-1].kind == "validated"
    assert report.runs["unknown_tool"].error == "tool_not_allowed"
    assert report.runs["bad_arguments"].error == "invalid_tool_arguments"
    assert report.runs["duplicate_call"].error == "duplicate_tool_call_id"
    assert report.runs["fabricated_fact"].error == "ungrounded_fact"
    assert report.runs["unseen_citation"].error == "ungrounded_citation"
    assert report.runs["step_budget"].error == "step_budget_exceeded"


@pytest.mark.parametrize(
    ("selected", "relevant", "passed"),
    [
        ([], [], True),
        (["A"], [], False),
        ([], ["A"], False),
        (["A"], ["A"], True),
        (["A", "B"], ["A"], False),
    ],
)
def test_evidence_when_labels_known_scores_abstention_and_support(
    selected: list[str], relevant: list[str], passed: bool
) -> None:
    # Given / When
    actual = evidence_pass(selected, relevant)
    # Then
    assert actual is passed


def test_dataset_when_unknown_label_rejects_before_inference(tmp_path: Path) -> None:
    # Given
    path = tmp_path / "bad.json"
    path.write_text(
        '[{"case_id":"a","query":"x","category":"exact","relevant_ids":["missing"],"rationale":"x"}]'
    )
    # When / Then
    with pytest.raises(DataContractError, match="Unknown relevance"):
        load_cases(path, KnowledgeBase.load(Path("knowledge/entries.json")))


def test_live_when_opt_in_missing_refuses_without_provider_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.delenv("TCM_RUN_LIVE", raising=False)
    # When / Then
    with pytest.raises(ConfigurationError, match="requires TCM_RUN_LIVE"):
        command(live=True, limit=1)


def test_summary_when_id_prefix_differs_uses_declared_category() -> None:
    # Given: identifiers need not encode category names.
    result = SelectionResult(
        case_id="custom-01",
        category="unknown",
        system="fixed",
        selected_ids=[],
        passed=True,
        latency_ms=2,
    )
    # When
    rows = summarize([result])
    # Then
    assert {row.category for row in rows} == {"all", "unknown"}
    assert all(row.passed == 1 and row.p95_ms == 2 for row in rows)
