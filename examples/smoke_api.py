# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx2[http2,brotli,zstd]>=2,<3", "tcm-agent-course"]
# [tool.uv.sources]
# tcm-agent-course = { path = "..", editable = true }
# ///
# Run against an already started API: uv run python examples/smoke_api.py
"""Real HTTP smoke: consent, turn, confirm, export, SSE, replay and deletion."""

import json
import os
from uuid import uuid4

import anyio

from tcm_agent.http_client import create_client


async def main() -> None:
    """Credentials stay in environment; evidence contains synthetic input only."""
    token = os.environ["TCM_CLIENT_TOKEN"]
    base = os.environ.get("TCM_SERVER_URL", "http://127.0.0.1:8000")
    async with create_client() as client:
        client.headers["Authorization"] = f"Bearer {token}"
        created = await client.post(base + "/sessions", json={"consent": True})
        created.raise_for_status()
        sid = created.json()["session_id"]
        body = {"request_id": str(uuid4()), "expected_version": 0, "text": "最近睡不好"}
        turn = await client.post(f"{base}/sessions/{sid}/turns", json=body)
        turn.raise_for_status()
        result = turn.json()
        replay = await client.post(f"{base}/sessions/{sid}/turns", json=body)
        assert replay.json() == result
        confirm = await client.patch(
            f"{base}/sessions/{sid}/facts",
            json={
                "expected_version": 1,
                "field": "complaint",
                "source_turn_id": result["turn_id"],
                "quote": result["candidates"][0]["quote"],
            },
        )
        confirm.raise_for_status()
        summary = await client.get(f"{base}/sessions/{sid}/summary")
        assert "最近睡不好" in summary.text
        events: list[str] = []
        async with client.stream(
            "POST",
            f"{base}/sessions/{sid}/events",
            json={"request_id": str(uuid4()), "expected_version": 2, "text": "什么是四诊？"},
        ) as stream:
            events.extend(
                [line async for line in stream.aiter_lines() if line.startswith("event:")]
            )
        records = await client.get(f"{base}/sessions/{sid}/records")
        removed = await client.delete(f"{base}/sessions/{sid}")
        assert removed.status_code == 204
        print(
            json.dumps(
                {
                    "created": created.status_code,
                    "turn": turn.status_code,
                    "replay_equal": True,
                    "confirm": confirm.status_code,
                    "summary": summary.text,
                    "events": events,
                    "records": len(records.json()),
                    "delete": removed.status_code,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    anyio.run(main)
