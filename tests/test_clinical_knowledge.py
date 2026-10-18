from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tcm_agent.clinical.contracts import CandidateCard, Citation, Observation
from tcm_agent.clinical.curation import curate, labels, term_key
from tcm_agent.clinical.store import ResearchKnowledge
from tcm_agent.clinical.upstream import MTCMBAnswer, MTCMBRow, TCMEvalRow
from tcm_agent.errors import DataContractError


@pytest.fixture
def knowledge() -> ResearchKnowledge:
    return ResearchKnowledge.load(Path("knowledge/clinical"))


def test_curation_when_labels_repeat_counts_records_once_and_preserves_negation() -> None:
    # Given: synthetic explicit labels, not real case narratives or inferred diagnoses.
    rows = [
        TCMEvalRow.model_validate(
            {"Clinical Information": "无口渴;无口渴;舌淡", "TCM Syndrome": "合成证A;合成证B"}
        )
        for _ in range(2)
    ]
    # When
    result = curate(rows, [])
    # Then: duplicates within a record never inflate co-occurrence or source citations.
    assert {t.label for t in result.terms if t.kind == "finding"} == {"无口渴", "舌淡"}
    assert all(edge.record_count == 2 for edge in result.associations)
    assert all(len(t.citations) == 2 for t in result.terms)
    assert all(card.diagnostic_criteria is None for card in result.cards)


def test_curation_when_feature_identifying_or_singleton_excludes_from_export() -> None:
    # Given
    rows = [
        TCMEvalRow.model_validate(
            {"Clinical Information": "张先生;电话123456789;舌淡;稀有观察", "TCM Syndrome": "合成证"}
        ),
        TCMEvalRow.model_validate(
            {"Clinical Information": "张先生;电话123456789;舌淡", "TCM Syndrome": "合成证"}
        ),
    ]
    # When
    result = curate(rows, [])
    # Then
    assert {t.label for t in result.terms if t.kind == "finding"} == {"舌淡"}


def test_labels_when_negation_and_kind_overlap_never_merge_semantics() -> None:
    # Given / When
    result = labels("无口渴；口渴; 无口渴")
    # Then
    assert set(result) == {"无口渴", "口渴"}
    assert term_key("disease", "合成词") != term_key("syndrome", "合成词")


def test_projection_when_upstream_has_narrative_never_exports_it() -> None:
    # Given
    raw = {
        "Clinical Information": "舌淡",
        "TCM Syndrome": "合成证",
        "Clinical Data": "IDENTIFYING NARRATIVE",
        "TCM Syndrome reasoning": "UNVERIFIED REASONING",
    }
    # When
    row = TCMEvalRow.model_validate(raw)
    # Then: the parsed contract has only the two permitted fields.
    assert set(row.model_dump()) == {"information", "syndrome"}


def test_mtcmb_when_projected_keeps_disease_and_pattern_distinct() -> None:
    # Given
    row = MTCMBRow(
        answer=MTCMBAnswer.model_validate(
            {"疾病名称": "合成病", "证名": "合成证", "病位证素": "表", "病性证素": "寒"}
        )
    )
    # When
    result = curate([], [row])
    # Then: no case-based diagnostic links are derived from vocabulary-only source.
    assert {t.kind for t in result.terms} == {
        "disease",
        "syndrome",
        "location_factor",
        "nature_factor",
    }
    assert result.associations == ()
    assert result.cards == ()


def test_knowledge_when_loaded_is_not_clinically_ready(knowledge: ResearchKnowledge) -> None:
    # Given / When / Then
    with pytest.raises(DataContractError, match="Clinical inference is disabled"):
        knowledge.require_clinical_ready()


def test_candidate_when_json_tries_to_enable_clinical_use_rejects() -> None:
    # Given
    raw = {
        "card_id": "x",
        "syndrome_id": "x",
        "source_id": "x",
        "source_record_count": 1,
        "associated_observation_ids": [],
        "clinical_use": "enabled",
    }
    # When / Then
    with pytest.raises(ValidationError):
        CandidateCard.model_validate(raw)


def test_questions_when_parent_addressed_unlocks_children_without_repeating(
    knowledge: ResearchKnowledge,
) -> None:
    # Given
    before = {q.question_id for q in knowledge.preview_questions("sleep", frozenset())}
    # When
    after = {q.question_id for q in knowledge.preview_questions("sleep", frozenset({"sleep.main"}))}
    # Then: addressed includes unknown/declined; it never means a negative finding.
    assert "sleep.awakening" not in before
    assert "sleep.main" not in after
    assert "sleep.awakening" in after


def test_questions_when_dependencies_cycle_rejects_pack(knowledge: ResearchKnowledge) -> None:
    # Given
    question = knowledge.questions[0]
    changed = question.model_copy(update={"prerequisites": [question.question_id]})
    # When / Then
    with pytest.raises(DataContractError, match="Cyclic"):
        replace(knowledge, questions=(changed, *knowledge.questions[1:])).audit()


def test_knowledge_when_source_unknown_rejects_pack(knowledge: ResearchKnowledge) -> None:
    # Given
    term = knowledge.terms[0].model_copy(
        update={"citations": [Citation(source_id="missing", locator="x")]}
    )
    # When / Then
    with pytest.raises(DataContractError, match="Unknown citation"):
        replace(knowledge, terms=(term, *knowledge.terms[1:])).audit()


@pytest.mark.parametrize("state", ["unknown", "not_measured", "declined"])
def test_observation_when_unobserved_cannot_carry_a_result(state: str) -> None:
    # Given
    raw = {
        "observation_id": "one",
        "modality": "tongue",
        "feature": "color",
        "value": "red",
        "state": state,
        "observed_at": "2026-10-18T10:00:00+08:00",
        "source_id": "provider",
        "evidence_group": "image-one",
    }
    # When / Then
    with pytest.raises(ValidationError, match="null value"):
        Observation.model_validate(raw)


def test_observation_when_timezone_absent_rejects() -> None:
    # Given: a source record without a timezone.
    raw = {
        "observation_id": "one",
        "modality": "pulse",
        "feature": "rate",
        "value": None,
        "state": "not_measured",
        "observed_at": "2026-10-18T00:00:00",
        "source_id": "provider",
        "evidence_group": "recording-one",
    }
    # When / Then
    with pytest.raises(ValidationError, match="timezone"):
        Observation.model_validate(raw)


def test_observation_when_unmeasured_preserves_unknown_not_false() -> None:
    # Given / When
    result = Observation(
        observation_id="one",
        modality="pulse",
        feature="rate",
        value=None,
        state="not_measured",
        observed_at=datetime(2026, 10, 18, tzinfo=UTC),
        source_id="provider",
        evidence_group="recording-one",
    )
    # Then
    assert result.value is None
    assert result.state == "not_measured"


def test_knowledge_when_association_count_exceeds_source_records_rejects(
    knowledge: ResearchKnowledge,
) -> None:
    # Given: a corrupted association count that would inflate apparent evidence.
    edge = knowledge.associations[0].model_copy(update={"record_count": 1000000})
    # When / Then
    with pytest.raises(DataContractError, match="Invalid association"):
        replace(knowledge, associations=(edge, *knowledge.associations[1:])).audit()
