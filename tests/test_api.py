from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient


def create(client: TestClient) -> str:
    response = client.post("/sessions", json={"consent": True})
    assert response.status_code == 201
    return response.json()["session_id"]


def payload(text: str = "最近睡不好", version: int = 0) -> dict[str, str | int]:
    return {"request_id": str(uuid4()), "expected_version": version, "text": text}


def test_turn_when_user_confirms_then_summary_preserves_input(client: TestClient) -> None:
    # Given: a consented session and a proposal from a real API turn.
    sid = create(client)
    turn = client.post(f"/sessions/{sid}/turns", json=payload()).json()
    # When: the authenticated user confirms the proposed fact.
    confirmed = client.patch(
        f"/sessions/{sid}/facts",
        json={
            "expected_version": 1,
            "field": "complaint",
            "source_turn_id": turn["turn_id"],
            "quote": "最近睡不好",
        },
    )
    # Then: summary contains the exact confirmed fact, with unknowns still unknown.
    assert confirmed.status_code == 200
    summary = client.get(f"/sessions/{sid}/summary")
    assert "最近睡不好" in summary.text
    assert summary.text.count("未提供") == 4


def test_summary_when_proposal_unconfirmed_excludes_it(client: TestClient) -> None:
    # Given
    sid = create(client)
    client.post(f"/sessions/{sid}/turns", json=payload())
    # When
    summary = client.get(f"/sessions/{sid}/summary")
    # Then
    assert "最近睡不好" not in summary.text
    assert summary.text.count("未提供") == 5


def test_read_when_other_user_has_id_returns_404(client: TestClient) -> None:
    # Given
    sid = create(client)
    # When
    response = client.get(f"/sessions/{sid}", headers={"Authorization": "Bearer bob-test-token"})
    # Then
    assert response.status_code == 404


def test_read_when_no_token_returns_401(client: TestClient) -> None:
    # Given
    sid = create(client)
    # When
    response = client.get(f"/sessions/{sid}", headers={"Authorization": ""})
    # Then
    assert response.status_code == 401


def test_create_when_consent_missing_rejects(client: TestClient) -> None:
    # Given / When
    response = client.post("/sessions", json={"consent": False})
    # Then
    assert response.status_code == 422


def test_turn_when_replayed_has_same_result_and_version(client: TestClient) -> None:
    # Given
    sid, body = create(client), payload()
    first = client.post(f"/sessions/{sid}/turns", json=body)
    # When
    replay = client.post(f"/sessions/{sid}/turns", json=body)
    # Then
    assert first.json() == replay.json()
    assert client.get(f"/sessions/{sid}").json()["version"] == 1


def test_turn_when_key_reused_with_different_text_conflicts(client: TestClient) -> None:
    # Given
    sid, body = create(client), payload()
    client.post(f"/sessions/{sid}/turns", json=body)
    # When
    response = client.post(f"/sessions/{sid}/turns", json={**body, "text": "另一个问题"})
    # Then
    assert response.status_code == 409
    assert response.json()["error"] == "idempotency_payload_conflict"


def test_turn_when_version_stale_preserves_new_state(client: TestClient) -> None:
    # Given
    sid = create(client)
    client.post(f"/sessions/{sid}/turns", json=payload())
    # When
    response = client.post(f"/sessions/{sid}/turns", json=payload("另一个问题"))
    # Then
    assert response.status_code == 409
    assert client.get(f"/sessions/{sid}").json()["version"] == 1


def test_turn_when_concurrent_same_version_only_one_commits(client: TestClient) -> None:
    # Given
    sid = create(client)
    bodies = [payload("睡眠"), payload("饮食")]
    # When
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda b: client.post(f"/sessions/{sid}/turns", json=b), bodies))
    # Then
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert client.get(f"/sessions/{sid}").json()["version"] == 1


def test_knowledge_when_tool_retrieves_includes_real_source(client: TestClient) -> None:
    # Given
    sid = create(client)
    # When
    response = client.post(f"/sessions/{sid}/turns", json=payload("什么是四诊？"))
    # Then
    body = response.json()
    assert response.status_code == 200
    assert body["action"] == "knowledge"
    assert body["steps"] == 2
    assert body["citations"][0]["entry_id"] == "tcm-four-examinations"
    assert body["answer"] == body["citations"][0]["text"]


def test_turn_when_risk_trigger_bypasses_model(client: TestClient) -> None:
    # Given
    sid = create(client)
    # When
    response = client.post(f"/sessions/{sid}/turns", json=payload("我有胸痛"))
    # Then
    assert response.json()["action"] == "handoff"
    assert response.json()["steps"] == 0


def test_confirm_when_quote_fabricated_rejects(client: TestClient) -> None:
    # Given
    sid = create(client)
    # When
    response = client.patch(
        f"/sessions/{sid}/facts",
        json={
            "expected_version": 0,
            "field": "allergy",
            "source_turn_id": str(uuid4()),
            "quote": "无过敏",
        },
    )
    # Then
    assert response.status_code == 422


def test_delete_when_session_exists_removes_replay_data(client: TestClient) -> None:
    # Given
    sid, body = create(client), payload()
    client.post(f"/sessions/{sid}/turns", json=body)
    # When
    response = client.delete(f"/sessions/{sid}")
    # Then
    assert response.status_code == 204
    assert client.post(f"/sessions/{sid}/turns", json=body).status_code == 404


def test_events_when_turn_completed_delivers_commit_and_done(client: TestClient) -> None:
    # Given
    sid = create(client)
    # When
    response = client.post(f"/sessions/{sid}/events", json=payload())
    # Then
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: committed" in response.text
    assert "event: done" in response.text


def test_metrics_when_knowledge_turn_records_bounded_labels(client: TestClient) -> None:
    # Given
    sid = create(client)
    client.post(f"/sessions/{sid}/turns", json=payload("四诊"))
    # When
    response = client.get("/metrics")
    # Then
    assert "tcm_turns_total" in response.text
    assert sid not in response.text
    assert "四诊" not in response.text


def test_confirm_when_user_corrects_field_summary_uses_latest_fact(client: TestClient) -> None:
    # Given: a confirmed original value, then a new user statement.
    sid = create(client)
    old = client.post(f"/sessions/{sid}/turns", json=payload("最早的描述")).json()
    client.patch(
        f"/sessions/{sid}/facts",
        json={
            "expected_version": 1,
            "field": "complaint",
            "source_turn_id": old["turn_id"],
            "quote": "最早的描述",
        },
    )
    new = client.post(f"/sessions/{sid}/turns", json=payload("更正后的描述", version=2)).json()
    # When: user confirms the replacement under the same field.
    confirmed = client.patch(
        f"/sessions/{sid}/facts",
        json={
            "expected_version": 3,
            "field": "complaint",
            "source_turn_id": new["turn_id"],
            "quote": "更正后的描述",
        },
    )
    # Then: the new value replaces the old one; original source remains exportable.
    assert confirmed.status_code == 200
    summary = client.get(f"/sessions/{sid}/summary").text
    assert "更正后的描述" in summary
    assert "最早的描述" not in summary
    records = client.get(f"/sessions/{sid}/records").json()
    assert {r["request_text"] for r in records} == {"最早的描述", "更正后的描述"}


def test_remove_when_confirmed_fact_deleted_summary_returns_missing(client: TestClient) -> None:
    # Given
    sid = create(client)
    result = client.post(f"/sessions/{sid}/turns", json=payload()).json()
    client.patch(
        f"/sessions/{sid}/facts",
        json={
            "expected_version": 1,
            "field": "complaint",
            "source_turn_id": result["turn_id"],
            "quote": "最近睡不好",
        },
    )
    # When
    response = client.delete(f"/sessions/{sid}/facts/complaint?version=2")
    # Then
    assert response.status_code == 200
    assert response.json()["version"] == 3
    assert client.get(f"/sessions/{sid}/summary").text.count("未提供") == 5
