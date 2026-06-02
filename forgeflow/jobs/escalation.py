"""Approval escalation — ratchets stale pending approvals through
levels (0 -> 1 -> 2 -> auto-rejected) and notifies on each step.

Lifecycle:
  level 0 (default) — approval is freshly requested
  level 1            — past first_escalation_minutes without resolution
                       -> Slack ping + escalated_to = "manager"
  level 2            — past second_escalation_minutes without resolution
                       -> Slack ping + escalated_to = "director"
  auto_resolved      — past auto_reject_minutes without resolution
                       -> status = 'rejected', auto_resolved = TRUE

Each escalation:
  1. Updates escalation_level + last_escalated_at + escalated_to
  2. Posts a Slack notification (graceful no-op when Slack disabled)
  3. Logs the event for the audit trail

Started by api/main.py lifespan as a background asyncio task. The interval
is configurable via APPROVAL_ESCALATION_INTERVAL_SECONDS (default 300).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import asyncpg

from forgeflow.config import get_settings
from forgeflow.notifications.slack import slack_post

logger = logging.getLogger(__name__)


@dataclass
class EscalationThresholds:
    first_escalation_minutes: int = 30
    second_escalation_minutes: int = 120
    auto_reject_minutes: int = 1440  # 24 hours


@dataclass
class EscalationReport:
    """Counts returned from a single escalation pass."""
    promoted_to_level_1: int = 0
    promoted_to_level_2: int = 0
    auto_rejected: int = 0
    errors: int = 0


async def run_escalation_pass(
    pool: asyncpg.Pool,
    thresholds: EscalationThresholds | None = None,
) -> EscalationReport:
    """Run one pass of the escalation logic. Idempotent — safe to call repeatedly.

    Returns counts so callers (tests, ops, metrics) can verify behavior.
    """
    cfg = thresholds or EscalationThresholds()
    settings = get_settings()
    base_url = settings.api_public_url.rstrip("/")
    report = EscalationReport()

    try:
        async with pool.acquire() as conn:
            # 1. Auto-reject the oldest stale approvals first.
            #    Doing this before promotions avoids a row jumping all
            #    levels in a single pass.
            auto_rejected = await conn.fetch(
                """
                UPDATE approval_requests
                SET    status = 'rejected',
                       auto_resolved = TRUE,
                       resolved_at = now(),
                       resolution_note = 'auto-rejected: exceeded SLA'
                WHERE  status = 'pending'
                  AND  requested_at < now() - make_interval(mins => $1)
                RETURNING id::text, token::text
                """,
                cfg.auto_reject_minutes,
            )
            report.auto_rejected = len(auto_rejected)

            # 2. Promote to level 2
            promote_2 = await conn.fetch(
                """
                UPDATE approval_requests
                SET    escalation_level = 2,
                       last_escalated_at = now(),
                       escalated_to = 'director'
                WHERE  status = 'pending'
                  AND  escalation_level < 2
                  AND  requested_at < now() - make_interval(mins => $1)
                RETURNING id::text, token::text
                """,
                cfg.second_escalation_minutes,
            )
            report.promoted_to_level_2 = len(promote_2)

            # 3. Promote to level 1
            promote_1 = await conn.fetch(
                """
                UPDATE approval_requests
                SET    escalation_level = 1,
                       last_escalated_at = now(),
                       escalated_to = 'manager'
                WHERE  status = 'pending'
                  AND  escalation_level < 1
                  AND  requested_at < now() - make_interval(mins => $1)
                RETURNING id::text, token::text
                """,
                cfg.first_escalation_minutes,
            )
            report.promoted_to_level_1 = len(promote_1)
    except Exception as exc:
        logger.exception("Escalation pass failed at DB level: %s", exc)
        report.errors += 1
        return report

    # 4. Fire Slack pings outside the DB transaction so a Slack outage
    #    doesn't roll back the level promotion.
    for row in promote_1:
        await _ping(
            row["token"],
            base_url,
            "Level-1 escalation: approval is past 30 minutes — please review.",
        )
    for row in promote_2:
        await _ping(
            row["token"],
            base_url,
            "Level-2 escalation: approval is past 2 hours — director attention required.",
        )
    for row in auto_rejected:
        await _ping(
            row["token"],
            base_url,
            "Auto-rejected: approval exceeded the 24-hour SLA.",
        )

    if any(
        [report.promoted_to_level_1, report.promoted_to_level_2, report.auto_rejected]
    ):
        logger.info(
            "Escalation pass: level1=%d level2=%d auto_rejected=%d",
            report.promoted_to_level_1,
            report.promoted_to_level_2,
            report.auto_rejected,
        )

    return report


async def _ping(token: str, base_url: str, message: str) -> None:
    """Best-effort Slack notification — never raises."""
    try:
        await slack_post(text=f"{message} {base_url}/approvals/{token}")
    except Exception as exc:
        logger.warning("Escalation slack ping failed for token=%s: %s", token, exc)


class ApprovalEscalationJob:
    """Long-running background task. Wrap pool in here so we can stop cleanly."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        interval_seconds: int = 300,
        thresholds: EscalationThresholds | None = None,
    ) -> None:
        self.pool = pool
        self.interval_seconds = max(10, interval_seconds)
        self.thresholds = thresholds or EscalationThresholds()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "ApprovalEscalationJob started | interval=%ds",
            self.interval_seconds,
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        logger.info("ApprovalEscalationJob stopped")

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await run_escalation_pass(self.pool, self.thresholds)
            except Exception as exc:
                logger.exception("Escalation loop iteration failed: %s", exc)
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.interval_seconds
                )
            except TimeoutError:
                continue
