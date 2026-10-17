from pathlib import Path

import pytest

from labs.crash_recovery import recover


@pytest.mark.anyio
async def test_recovery_when_claiming_process_exits_fences_stale_commit_and_replays(
    tmp_path: Path,
) -> None:
    # Given: a private database and a worker that will exit without cleanup.
    # When: the real child exits and a controlled expiry allows a new claim.
    result = await recover(tmp_path)
    # Then: pending work is blocked before expiry, old commit rolls back, result replays.
    assert result.child_exit == 73
    assert result.before_expiry == "request_in_progress"
    assert result.stale_worker == "operation_lease_lost"
    assert result.version_after_stale == 0
    assert result.committed_version == 1
    assert result.replay_identical
