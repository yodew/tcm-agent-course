"""Deterministic projections and descriptive co-occurrence; no diagnostic weights inferred."""

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Literal

from tcm_agent.clinical.contracts import Association, CandidateCard, Citation, Term
from tcm_agent.clinical.upstream import MTCMBRow, TCMEvalRow

TermKind = Literal["finding", "syndrome", "disease", "location_factor", "nature_factor"]


def labels(text: str) -> tuple[str, ...]:
    """Split explicit source separators only; never drop negation or infer synonyms."""
    return tuple(
        sorted(
            {
                part.strip()
                for part in re.split(r"[;；、]", unicodedata.normalize("NFKC", text))
                if part.strip()
            }
        )
    )


def safe_feature(label: str) -> bool:
    """Conservative export filter; not a guarantee that arbitrary records are anonymous."""
    return bool(re.fullmatch(r"[\u4e00-\u9fff]{2,24}", label)) and not any(
        word in label
        for word in ("患者", "姓名", "住址", "医院", "先生", "女士", "电话", "岁", "身份证", "出生")
    )


def term_key(kind: TermKind, label: str) -> str:
    """Keep disease, pattern and symptom identities distinct even if labels coincide."""
    return kind + "-" + hashlib.sha256(f"{kind}:{label}".encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class TermBuilder:
    """Accumulate provenance from several inputs without merging unlike term kinds."""

    terms: dict[str, Term] = field(default_factory=dict)

    def add(self, label: str, kind: TermKind, citation: Citation) -> str:
        """Merge exact normalized labels only, with all source locators retained."""
        key = term_key(kind, label)
        old = self.terms.get(key)
        citations = [] if old is None else list(old.citations)
        if citation not in citations:
            citations.append(citation)
        self.terms[key] = Term(term_id=key, label=label, kind=kind, citations=citations)
        return key


@dataclass(frozen=True, slots=True)
class CuratedRows:
    terms: tuple[Term, ...]
    associations: tuple[Association, ...]
    cards: tuple[CandidateCard, ...]
    excluded_features: int


def curate(tcmeval: list[TCMEvalRow], mtcmb: list[MTCMBRow]) -> CuratedRows:
    """Use training labels only; shared frequencies are descriptive corpus properties."""
    vocabulary = TermBuilder()
    features = [set(labels(row.information)) for row in tcmeval]
    prevalence = Counter(feature for row in features for feature in row)
    accepted = {
        feature for feature, count in prevalence.items() if count >= 2 and safe_feature(feature)
    }
    counts: Counter[tuple[str, str]] = Counter()
    syndrome_counts: Counter[str] = Counter()
    for index, row in enumerate(tcmeval):
        syndromes = labels(row.syndrome)
        for syndrome in syndromes:
            sid = vocabulary.add(
                syndrome,
                "syndrome",
                Citation(
                    source_id="tcmeval-sdt-train",
                    locator=f"Train_TCM_Data_v1.json#/{index}/TCM Syndrome",
                ),
            )
            syndrome_counts[sid] += 1
            for feature in sorted(features[index] & accepted):
                fid = vocabulary.add(
                    feature,
                    "finding",
                    Citation(
                        source_id="tcmeval-sdt-train",
                        locator=f"Train_TCM_Data_v1.json#/{index}/Clinical Information",
                    ),
                )
                counts[(fid, sid)] += 1
    for index, row in enumerate(mtcmb):
        entries: tuple[tuple[TermKind, str, str], ...] = (
            ("disease", row.answer.disease, "疾病名称"),
            ("syndrome", row.answer.syndrome, "证名"),
            ("location_factor", row.answer.location, "病位证素"),
            ("nature_factor", row.answer.nature, "病性证素"),
        )
        for kind, raw, original_key in entries:
            for label in labels(raw):
                vocabulary.add(
                    label,
                    kind,
                    Citation(
                        source_id="mtcmb-diagnosis",
                        locator=f"TCM-Diagnosis.jsonl#line={index + 1}/answer/{original_key}",
                    ),
                )
    edges = tuple(
        Association(
            observation_id=fid, syndrome_id=sid, record_count=count, source_id="tcmeval-sdt-train"
        )
        for (fid, sid), count in sorted(counts.items())
    )
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for edge in edges:
        grouped[edge.syndrome_id].append(edge.observation_id)
    cards = tuple(
        CandidateCard(
            card_id="corpus-" + sid,
            syndrome_id=sid,
            source_id="tcmeval-sdt-train",
            source_record_count=count,
            associated_observation_ids=grouped[sid],
        )
        for sid, count in sorted(syndrome_counts.items())
    )
    return CuratedRows(
        tuple(vocabulary.terms[key] for key in sorted(vocabulary.terms)),
        edges,
        cards,
        len(prevalence) - len(accepted),
    )
