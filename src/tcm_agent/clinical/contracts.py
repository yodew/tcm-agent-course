"""Separate collection, source rights, clinical evidence and future observation inputs."""

from datetime import datetime
from typing import Literal, Self

from pydantic import Field, StrictBool, StrictFloat, StrictStr, field_validator, model_validator

from tcm_agent.domain import Contract
from tcm_agent.errors import DataContractError


class Source(Contract):
    source_id: str
    title: str
    url: str
    publisher: str
    checked_on: str
    version: str
    license: str
    license_url: str
    rights_scope: str
    uses: list[str]
    limitations: list[str]


class Citation(Contract):
    source_id: str
    locator: str


class Term(Contract):
    term_id: str
    label: str = Field(min_length=1, max_length=64)
    kind: Literal["finding", "syndrome", "disease", "location_factor", "nature_factor"]
    aliases: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(min_length=1)
    review_status: Literal["research_only"] = "research_only"


class Association(Contract):
    observation_id: str
    syndrome_id: str
    record_count: int = Field(ge=1)
    source_id: str
    evidence_kind: Literal["dataset_cooccurrence"] = "dataset_cooccurrence"
    clinical_use: Literal["disabled"] = "disabled"


class CandidateCard(Contract):
    card_id: str
    syndrome_id: str
    source_id: str
    source_record_count: int = Field(ge=1)
    associated_observation_ids: list[str]
    diagnostic_criteria: None = None
    exclusion_criteria: None = None
    differential_rules: None = None
    criteria_status: Literal["not_available_from_case_labels"] = "not_available_from_case_labels"
    clinical_use: Literal["disabled"] = "disabled"


class Question(Contract):
    question_id: str
    domain: str
    prompt: str
    target_field: str
    answer_type: Literal["text", "choice", "number", "date", "measurement"]
    options: list[str] = Field(default_factory=list)
    profiles: list[str] = Field(min_length=1)
    reason: str
    source_refs: list[Citation] = Field(min_length=1)
    priority: int = Field(ge=0, le=100)
    prerequisites: list[str] = Field(default_factory=list)
    review_status: Literal["engineering_draft"] = "engineering_draft"
    clinical_use: Literal["disabled"] = "disabled"


class Observation(Contract):
    """Neutral contract for tomorrow's samples, not an implemented provider mapping."""

    observation_id: str
    modality: Literal["inquiry", "face", "tongue", "pulse", "other"]
    feature: str
    value: StrictStr | StrictFloat | StrictBool | None
    state: Literal["present", "absent", "unknown", "not_measured", "declined"]
    observed_at: datetime
    source_id: str
    evidence_group: str = Field(min_length=1)
    unit: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    quality: Literal["unknown", "acceptable", "recollect"] = "unknown"
    confirmed: bool = False

    @field_validator("observed_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        """Cross-source observations require an explicit timezone."""
        if value.utcoffset() is None:
            raise DataContractError("Observation timestamp must include timezone")
        return value

    @model_validator(mode="after")
    def coherent_state(self) -> Self:
        """Unknown/declined/unmeasured must not carry invented observations."""
        if self.state in {"unknown", "not_measured", "declined"} and self.value is not None:
            raise DataContractError("Unobserved states require null value")
        if self.state == "present" and self.value is None:
            raise DataContractError("Present observations require a value")
        return self


class CollectionReceipt(Contract):
    source_id: str
    input_sha256: str
    input_records: int
    exported_fields: list[str]
    excluded_fields: list[str]
    source_file_url: str
    license_evidence_url: str
    license_evidence_sha256: str
    collection_date: str


class KnowledgeAudit(Contract):
    sources: int
    questions: int
    terms: int
    associations: int
    candidate_cards: int
    literature_cards: int
    single_record_cards: int
    cards_without_retained_observations: int
    raw_case_exported: Literal[False] = False
    clinical_inference_enabled: Literal[False] = False
    scope: str = "Collection, provenance and schema validation only; not clinical validation"


class LiteratureCard(Contract):
    card_id: str
    source_id: str
    topic: str
    pattern_label: str
    related_features: list[str]
    question_links: list[str]
    locator: str
    limitations: list[str]
    required_criteria: None = None
    exclusion_criteria: None = None
    evidence_kind: Literal["literature_feature_summary"] = "literature_feature_summary"
    clinical_use: Literal["disabled"] = "disabled"
