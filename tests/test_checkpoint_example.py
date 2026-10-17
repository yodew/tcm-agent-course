"""Exercise the actual optional framework rather than a checkpoint mock."""

import pytest

from tcm_agent.errors import DataContractError


def test_checkpoint_when_approved_resumes_real_suspended_node() -> None:
    # Given: the optional framework is installed.
    pytest.importorskip("langgraph")
    from examples.checkpoint_approval import approval_round_trip  # noqa: PLC0415

    # When: the synthetic draft is approved with its current revision.
    approved = approval_round_trip()
    # Then: a real interrupt/resume round trip completes.
    assert approved


def test_checkpoint_when_revision_changes_rejects_old_approval() -> None:
    # Given: the optional framework and a pending approval.
    pytest.importorskip("langgraph")
    from examples.checkpoint_approval import approval_round_trip  # noqa: PLC0415

    # When/Then: resuming after a state update must not authorize the old draft.
    with pytest.raises(DataContractError, match="stale"):
        approval_round_trip(stale=True)
