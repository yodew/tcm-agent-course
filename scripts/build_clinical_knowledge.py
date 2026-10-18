# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python scripts/build_clinical_knowledge.py
"""Rebuild source-derived labels from pinned local inputs; no upstream code execution."""

import hashlib
import json
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from tcm_agent.clinical.contracts import CollectionReceipt
from tcm_agent.clinical.curation import curate
from tcm_agent.clinical.store import ResearchKnowledge
from tcm_agent.clinical.upstream import InputSpec, MTCMBRow, TCMEvalRow
from tcm_agent.errors import DataContractError

ROOT: Final = Path(__file__).resolve().parents[1]


def main() -> None:
    """Reject changed source bytes before parsing only the approved projection fields."""
    directory = ROOT / "knowledge/clinical"
    specs = TypeAdapter(list[InputSpec]).validate_json((directory / "inputs.json").read_bytes())
    receipts: list[CollectionReceipt] = []
    for spec in specs:
        raw = (ROOT / "tmp" / spec.local_name).read_bytes()
        license_bytes = (ROOT / "tmp" / spec.license_local_name).read_bytes()
        if (
            hashlib.sha256(raw).hexdigest() != spec.sha256
            or hashlib.sha256(license_bytes).hexdigest() != spec.license_sha256
        ):
            raise DataContractError("Pinned upstream snapshot changed")
    first, second = specs
    tcmeval = TypeAdapter(list[TCMEvalRow]).validate_json(
        (ROOT / "tmp" / first.local_name).read_bytes()
    )
    mtcmb = [
        MTCMBRow.model_validate_json(line)
        for line in (ROOT / "tmp" / second.local_name).read_text().splitlines()
        if line.strip()
    ]
    result = curate(tcmeval, mtcmb)
    outputs = {
        "terms.json": result.terms,
        "associations.json": result.associations,
        "candidate_cards.json": result.cards,
    }
    for filename, records in outputs.items():
        (directory / filename).write_text(
            json.dumps([r.model_dump(mode="json") for r in records], ensure_ascii=False, indent=2)
            + "\n"
        )
    for spec, count in zip(specs, (len(tcmeval), len(mtcmb)), strict=True):
        receipts.append(
            CollectionReceipt(
                source_id=spec.source_id,
                input_sha256=spec.sha256,
                input_records=count,
                exported_fields=[
                    "Clinical Information (filtered terms, aggregates)",
                    "TCM Syndrome",
                ]
                if spec is first
                else ["answer.疾病名称", "answer.证名", "answer.病位证素", "answer.病性证素"],
                excluded_fields=[
                    "raw clinical narratives",
                    "reasoning",
                    "prescriptions",
                    "test/validation splits",
                    "question text",
                ],
                source_file_url=spec.url,
                license_evidence_url=spec.license_url,
                license_evidence_sha256=spec.license_sha256,
                collection_date="2026-10-18",
            )
        )
    (directory / "receipts.json").write_text(
        json.dumps([r.model_dump() for r in receipts], ensure_ascii=False, indent=2) + "\n"
    )
    report = ResearchKnowledge.load(directory).audit()
    (ROOT / "evidence/clinical-knowledge-audit.json").write_text(
        report.model_dump_json(indent=2) + "\n"
    )
    print(report.model_dump_json(indent=2))
    print("Excluded low-frequency/long/sensitive-looking feature labels:", result.excluded_features)


if __name__ == "__main__":
    main()
