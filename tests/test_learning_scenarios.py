from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tcm_agent.domain import ConfirmRequest, TurnRequest, TurnResponse, VisitSnapshot


@pytest.mark.parametrize(
    "text",
    [
        "未提供过敏资料",
        "不确定是否有过敏",
        "不是持续失眠，只是偶尔晚睡",
        "前面说错了，今天重新描述",
        "没有提供用药名称",
        "希望保留原话，不推断病史",
    ],
)
def test_confirmation_when_statement_contains_uncertainty_preserves_exact_source(
    client: TestClient, text: str
) -> None:
    # Given: real API/SQLite with the explicitly fixed offline candidate policy.
    snapshot = VisitSnapshot.model_validate_json(
        client.post("/sessions", json={"consent": True}).content
    )
    request = TurnRequest(request_id=uuid4(), expected_version=0, text=text)
    turn = TurnResponse.model_validate_json(
        client.post(
            f"/sessions/{snapshot.session_id}/turns", json=request.model_dump(mode="json")
        ).content
    )
    candidate = turn.candidates[0]
    # When: user confirms the exact candidate under the current version.
    body = ConfirmRequest(
        expected_version=1,
        field=candidate.field,
        quote=candidate.quote,
        source_turn_id=candidate.source_turn_id,
    )
    response = client.patch(
        f"/sessions/{snapshot.session_id}/facts", json=body.model_dump(mode="json")
    )
    # Then: persistence preserves wording; no semantic model-understanding claim.
    confirmed = VisitSnapshot.model_validate_json(response.content)
    assert confirmed.facts[0].quote == text
    assert confirmed.facts[0].confirmed
    assert client.get(f"/sessions/{snapshot.session_id}/summary").text.count("未提供") >= 4
