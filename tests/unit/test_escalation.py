"""Tests for the approval escalation background job."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.jobs.escalation import (
    ApprovalEscalationJob,
    EscalationThresholds,
    run_escalation_pass,
)


def _pool_returning(level1_rows, level2_rows, autoreject_rows):
    """Build a pool whose 3 fetch calls (in order: auto-reject, level2, level1)
    return the supplied row lists. The escalation pass calls fetch in the order
    auto_reject -> promote_2 -> promote_1, so set side_effect accordingly.
    """
    conn = AsyncMock()
    conn.fetch = AsyncMock(side_effect=[autoreject_rows, level2_rows, level1_rows])
    pool = MagicMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    return pool, conn


class TestEscalationPass:
    @pytest.mark.asyncio
    async def test_counts_each_severity(self):
        pool, _ = _pool_returning(
            level1_rows=[{"id": "1", "token": "tok-1"}, {"id": "2", "token": "tok-2"}],
            level2_rows=[{"id": "3", "token": "tok-3"}],
            autoreject_rows=[{"id": "4", "token": "tok-4"}],
        )

        with patch("forgeflow.jobs.escalation.slack_post", new=AsyncMock()):
            report = await run_escalation_pass(pool)

        assert report.promoted_to_level_1 == 2
        assert report.promoted_to_level_2 == 1
        assert report.auto_rejected == 1
        assert report.errors == 0

    @pytest.mark.asyncio
    async def test_db_failure_reported_as_error(self):
        pool = MagicMock()
        pool.acquire.side_effect = RuntimeError("connection lost")

        report = await run_escalation_pass(pool)

        assert report.errors == 1
        assert report.promoted_to_level_1 == 0

    @pytest.mark.asyncio
    async def test_slack_outage_does_not_fail_pass(self):
        pool, _ = _pool_returning(
            level1_rows=[{"id": "1", "token": "tok-1"}],
            level2_rows=[],
            autoreject_rows=[],
        )

        with patch(
            "forgeflow.jobs.escalation.slack_post",
            new=AsyncMock(side_effect=RuntimeError("slack down")),
        ):
            # Should NOT raise — Slack failures are swallowed
            report = await run_escalation_pass(pool)

        assert report.promoted_to_level_1 == 1
        # DB-level promotion was already committed by the time Slack failed


class TestApprovalEscalationJob:
    @pytest.mark.asyncio
    async def test_start_and_stop_are_idempotent(self):
        pool, _ = _pool_returning([], [], [])
        with patch("forgeflow.jobs.escalation.slack_post", new=AsyncMock()):
            job = ApprovalEscalationJob(
                pool=pool,
                interval_seconds=10,
                thresholds=EscalationThresholds(),
            )
            job.start()
            assert job._task is not None
            # Calling start again is a no-op
            job.start()
            await job.stop()
            assert job._task is None
            # Stopping again is safe
            await job.stop()

    @pytest.mark.asyncio
    async def test_interval_clamped_to_minimum(self):
        pool, _ = _pool_returning([], [], [])
        job = ApprovalEscalationJob(pool=pool, interval_seconds=1)
        assert job.interval_seconds == 10  # clamped up to the floor
