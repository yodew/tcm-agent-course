"""Load the separate research pack and refuse accidental clinical promotion."""

from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from pydantic import TypeAdapter

from tcm_agent.clinical.contracts import (
    Association,
    CandidateCard,
    KnowledgeAudit,
    LiteratureCard,
    Question,
    Source,
    Term,
)
from tcm_agent.errors import DataContractError


@dataclass(frozen=True, slots=True)
class ResearchKnowledge:
    sources: tuple[Source, ...]
    questions: tuple[Question, ...]
    terms: tuple[Term, ...]
    associations: tuple[Association, ...]
    cards: tuple[CandidateCard, ...]
    literature: tuple[LiteratureCard, ...]

    @classmethod
    def load(cls, directory: Path) -> "ResearchKnowledge":
        """Parse immutable contracts and validate cross-file links before use."""
        pack = cls(
            TypeAdapter(tuple[Source, ...]).validate_json(
                (directory / "sources.json").read_bytes()
            ),
            TypeAdapter(tuple[Question, ...]).validate_json(
                (directory / "questions.json").read_bytes()
            ),
            TypeAdapter(tuple[Term, ...]).validate_json((directory / "terms.json").read_bytes()),
            TypeAdapter(tuple[Association, ...]).validate_json(
                (directory / "associations.json").read_bytes()
            ),
            TypeAdapter(tuple[CandidateCard, ...]).validate_json(
                (directory / "candidate_cards.json").read_bytes()
            ),
            TypeAdapter(tuple[LiteratureCard, ...]).validate_json(
                (directory / "literature_cards.json").read_bytes()
            ),
        )
        pack.audit()
        return pack

    def audit(self) -> KnowledgeAudit:
        """Validate IDs, kinds, citation sources and disabled clinical status."""
        sources = {s.source_id for s in self.sources}
        terms = {t.term_id: t for t in self.terms}
        question_ids = {q.question_id for q in self.questions}
        card_counts = {(c.syndrome_id, c.source_id): c.source_record_count for c in self.cards}
        if (
            len(sources) != len(self.sources)
            or len(terms) != len(self.terms)
            or len(question_ids) != len(self.questions)
            or len({c.card_id for c in self.cards}) != len(self.cards)
            or len(card_counts) != len(self.cards)
            or len({c.card_id for c in self.literature}) != len(self.literature)
            or len({(e.observation_id, e.syndrome_id, e.source_id) for e in self.associations})
            != len(self.associations)
        ):
            raise DataContractError("Duplicate knowledge IDs")
        references = [ref for term in self.terms for ref in term.citations]
        references.extend(ref for question in self.questions for ref in question.source_refs)
        if any(ref.source_id not in sources for ref in references):
            raise DataContractError("Unknown citation source")
        if any(set(question.prerequisites) - question_ids for question in self.questions):
            raise DataContractError("Unknown question prerequisite")
        try:
            tuple(
                TopologicalSorter(
                    {q.question_id: set(q.prerequisites) for q in self.questions}
                ).static_order()
            )
        except CycleError as error:
            raise DataContractError("Cyclic question prerequisites") from error
        if any(
            edge.source_id not in sources
            or edge.observation_id not in terms
            or edge.syndrome_id not in terms
            or (edge.syndrome_id, edge.source_id) not in card_counts
            or edge.record_count > card_counts[(edge.syndrome_id, edge.source_id)]
            for edge in self.associations
        ):
            raise DataContractError("Invalid association reference or count")
        if any(
            terms[edge.observation_id].kind != "finding"
            or terms[edge.syndrome_id].kind != "syndrome"
            for edge in self.associations
        ):
            raise DataContractError("Association kind mismatch")
        edge_keys = {
            (edge.observation_id, edge.syndrome_id, edge.source_id) for edge in self.associations
        }
        for card in self.cards:
            if (
                card.source_id not in sources
                or (card.syndrome_id in terms and terms[card.syndrome_id].kind != "syndrome")
                or any(
                    (key, card.syndrome_id, card.source_id) not in edge_keys
                    for key in card.associated_observation_ids
                )
                or card.syndrome_id not in terms
                or any(key not in terms for key in card.associated_observation_ids)
            ):
                raise DataContractError("Unknown candidate card reference")
        if any(
            card.source_id not in sources or set(card.question_links) - question_ids
            for card in self.literature
        ):
            raise DataContractError("Unknown literature reference")
        return KnowledgeAudit(
            sources=len(self.sources),
            questions=len(self.questions),
            terms=len(self.terms),
            associations=len(self.associations),
            candidate_cards=len(self.cards),
            literature_cards=len(self.literature),
            single_record_cards=sum(card.source_record_count == 1 for card in self.cards),
            cards_without_retained_observations=sum(
                not card.associated_observation_ids for card in self.cards
            ),
        )

    def preview_questions(self, profile: str, answered: frozenset[str]) -> tuple[Question, ...]:
        """Engineering-only queue; unknown/declined fields count as addressed, not negative."""
        if profile not in {p for q in self.questions for p in q.profiles}:
            raise DataContractError("Unknown question profile")
        if answered - {q.question_id for q in self.questions}:
            raise DataContractError("Unknown answered question ID")
        selected = [
            q
            for q in self.questions
            if profile in q.profiles
            and q.question_id not in answered
            and set(q.prerequisites) <= answered
        ]
        return tuple(sorted(selected, key=lambda q: (q.priority, q.question_id)))

    def search_terms(self, query: str) -> tuple[Term, ...]:
        """Literal research lookup; this does not identify a patient's syndrome."""
        if not query.strip():
            raise DataContractError("Empty research lookup")
        return tuple(t for t in self.terms if query in t.label or query in t.aliases)

    def require_clinical_ready(self) -> None:
        """A collected dataset is never promoted by a Boolean in a JSON file."""
        raise DataContractError(
            "Clinical inference is disabled: criteria and clinical validation unavailable"
        )
