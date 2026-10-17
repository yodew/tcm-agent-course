"""Check failure paths that the learning experiments are designed to expose."""

import pytest
from pydantic import ValidationError

from labs.context_memory import FactState, assemble
from labs.evaluation import score, task_success
from labs.model_mechanics import probabilities, request_messages
from labs.retrieval import fuse
from labs.tool_loop import Call, Finish, ScriptedDecisions, run
from labs.workflows import Task, order
from tcm_agent.errors import DataContractError


def test_probabilities_when_logits_large_are_stable_and_temperature_changes_confidence() -> None:
    # Given: logits that overflow a naive exponentiation.
    logits = (1003.0, 1002.0, 1000.0)
    # When: two positive temperatures transform the same logits.
    sharp, flat = probabilities(logits, 0.2), probabilities(logits, 2)
    # Then: normalization and ranking hold without claiming improved truthfulness.
    assert sum(sharp) == pytest.approx(1)
    assert sharp[0] > flat[0] > flat[1] > flat[2]


@pytest.mark.parametrize("temperature", [0, -1, float("nan")])
def test_probabilities_when_temperature_invalid_rejects_it(temperature: float) -> None:
    # Given: a temperature for which this arithmetic formula is undefined.
    # When/Then: reject instead of pretending to simulate a provider's greedy mode.
    with pytest.raises(DataContractError):
        probabilities((1.0,), temperature)


def test_messages_when_no_history_supplied_do_not_invent_prior_state() -> None:
    # Given: an earlier request has already been assembled independently.
    request_messages("四诊是什么？")
    # When: another request omits its history.
    second = request_messages("它包括什么？")
    # Then: the application must explicitly provide the missing context.
    assert second == ("它包括什么？",)


def test_loop_when_tool_returns_links_actual_observation_to_call_id() -> None:
    # Given: fixed decisions but a real registered tool executor.
    source = ScriptedDecisions((Call("c1", "lookup_term", '{"term":"四诊"}'), Finish("完成")))
    # When: the executor runs the fixture.
    answer, observations = run(source)
    # Then: results retain linkage; no model generation is claimed.
    assert answer == "完成"
    assert observations[0].call_id == "c1"
    assert "望、闻、问、切" in observations[0].output


@pytest.mark.parametrize(
    ("name", "arguments"), [("shell", "{}"), ("lookup_term", '{"term":"四诊","owner":"other"}')]
)
def test_loop_when_tool_or_args_untrusted_rejects_before_execution(
    name: str, arguments: str
) -> None:
    # Given: a decision source can return invalid tool calls.
    source = ScriptedDecisions((Call("c1", name, arguments),))
    # When/Then: unknown capabilities and extra arguments do not reach tools.
    with pytest.raises((DataContractError, ValidationError)):
        run(source)


def test_loop_when_call_id_repeated_rejects_duplicate() -> None:
    # Given: a source repeats an execution identifier.
    call = Call("c1", "lookup_term", '{"term":"四诊"}')
    # When/Then: repeated identifiers fail instead of silently executing again.
    with pytest.raises(DataContractError, match="repeated"):
        run(ScriptedDecisions((call, call)))


def test_loop_when_budget_spent_never_requests_another_step() -> None:
    # Given: a search followed by finish needs two decisions.
    source = ScriptedDecisions((Call("c1", "lookup_term", '{"term":"四诊"}'), Finish("完成")))
    # When/Then: a budget of one denies the next decision.
    with pytest.raises(DataContractError, match="budget"):
        run(source, max_steps=1)


def test_context_when_required_overflows_never_silently_drops_it() -> None:
    # Given: confirmed facts do not fit.
    # When/Then: fail explicitly instead of dropping mandatory context.
    with pytest.raises(DataContractError):
        assemble(("必需事实",), ("历史",), 2)


def test_confirmation_when_version_stale_rejects_old_approval() -> None:
    # Given: another confirmation has advanced the state.
    state = FactState().confirm(0, "睡不好", "最近睡不好")
    # When/Then: an earlier approval cannot overwrite the new revision.
    with pytest.raises(DataContractError, match="Version"):
        state.confirm(0, "新描述", "新描述")


def test_confirmation_when_quote_absent_rejects_fabrication() -> None:
    # Given: an unrelated source sentence.
    # When/Then: fabricated facts do not become confirmed state.
    with pytest.raises(DataContractError, match="source"):
        FactState().confirm(0, "无过敏", "最近睡不好")


@pytest.mark.parametrize(
    "tasks", [(Task("A", ("B",)), Task("B", ("A",))), (Task("A", ("missing",)),)]
)
def test_plan_when_dependencies_invalid_rejects_before_any_task(tasks: tuple[Task, ...]) -> None:
    # Given: cyclic or missing dependencies.
    # When/Then: validation rejects the plan before side effects are possible.
    with pytest.raises(DataContractError):
        order(tasks)


def test_fusion_when_rankings_disagree_rewards_cross_list_agreement() -> None:
    # Given: two retrieval rankings, with B consistently near the top.
    # When: score scales are ignored and rank evidence is fused.
    ranking = fuse((("A", "B", "C"), ("B", "C", "A")))
    # Then: B wins; averaging incomparable raw scores was unnecessary.
    assert ranking[0] == "B"


def test_evaluation_when_answer_correct_but_unauthorized_fails_task() -> None:
    # Given: correct answer text with an unauthorized write.
    # When: the task contract is evaluated.
    success = task_success(answer_correct=True, unauthorized_write=True, calls=1, budget=3)
    # Then: answer correctness cannot excuse a permission violation.
    assert not success


def test_retrieval_score_when_first_hit_second_counts_relevance_denominator() -> None:
    # Given: two relevant documents but only one retrieved in three slots.
    # When: the labeled ranking is evaluated at three.
    measured = score(("wrong", "B"), frozenset({"A", "B"}), 3)
    # Then: recall, precision and reciprocal rank answer different questions.
    assert measured.recall == 0.5
    assert measured.precision == pytest.approx(1 / 3)
    assert measured.reciprocal_rank == 0.5
