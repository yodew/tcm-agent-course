from fastapi.testclient import TestClient

from tcm_agent.config import Settings
from tests.test_api import create, payload


def test_turn_when_limit_reached_replay_is_free_but_new_work_rejected(
    client: TestClient, settings: Settings
) -> None:
    # Given: exactly the configured allowance has completed.
    sid = create(client)
    first = payload()
    client.post(f"/sessions/{sid}/turns", json=first)
    for version in range(1, settings.rate_limit_per_minute):
        assert (
            client.post(f"/sessions/{sid}/turns", json=payload(version=version)).status_code == 200
        )
    # When: client retries first request, then submits new work.
    replay = client.post(f"/sessions/{sid}/turns", json=first)
    rejected = client.post(
        f"/sessions/{sid}/turns", json=payload(version=settings.rate_limit_per_minute)
    )
    # Then
    assert replay.status_code == 200
    assert rejected.status_code == 429
    assert rejected.headers["retry-after"] == "60"
