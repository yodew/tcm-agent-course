# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run: uv run python scripts/collect_clinical_sources.py
"""Fetch only pinned public snapshots into ignored tmp/, with exact-byte verification."""

import hashlib
from pathlib import Path
from typing import Final
from urllib.parse import urlparse

import anyio
from pydantic import TypeAdapter

from tcm_agent.clinical.upstream import InputSpec
from tcm_agent.errors import DataContractError
from tcm_agent.http_client import create_client

ROOT: Final = Path(__file__).resolve().parents[1]


async def main() -> None:
    """Do not execute downloaded code, collect tokens or export raw patient narratives."""
    specs = TypeAdapter(list[InputSpec]).validate_json(
        (ROOT / "knowledge/clinical/inputs.json").read_bytes()
    )
    async with create_client() as client:
        for spec in specs:
            for url, name, expected in (
                (spec.url, spec.local_name, spec.sha256),
                (spec.license_url, spec.license_local_name, spec.license_sha256),
            ):
                if urlparse(url).hostname != "raw.githubusercontent.com" or Path(name).name != name:
                    raise DataContractError("Unexpected source host or local path")
                response = await client.get(url)
                response.raise_for_status()
                raw = response.content
                if len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != expected:
                    raise DataContractError("Source bytes differ from reviewed snapshot")
                await anyio.Path(ROOT / "tmp").mkdir(exist_ok=True)
                await anyio.Path(ROOT / "tmp" / name).write_bytes(raw)
    print(
        "Verified two data snapshots and their licensing statements; raw inputs stay in ignored tmp/"
    )


if __name__ == "__main__":
    anyio.run(main)
