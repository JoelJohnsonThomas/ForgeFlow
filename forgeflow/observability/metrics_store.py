"""MetricsStore — writes run metrics to PostgreSQL for dashboard queries."""

from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)


class MetricsStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def write_metric(
        self,
        run_id: str,
        metric_name: str,
        metric_value: float,
        metric_unit: str | None = None,
        tags: dict | None = None,
    ) -> None:
        """Write a single metric data point."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO run_metrics (run_id, metric_name, metric_value, metric_unit, tags)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    run_id,
                    metric_name,
                    metric_value,
                    metric_unit,
                    tags or {},
                )
        except Exception as e:
            logger.error("MetricsStore.write_metric failed: %s", e)

    async def record_run_completion(
        self,
        run_id: str,
        latency_ms: float,
        total_tokens: int,
        total_cost_usd: float,
        success: bool,
        agent_name: str = "workflow",
    ) -> None:
        """Write the standard set of metrics for a completed workflow run."""
        tags = {"agent": agent_name, "success": str(success)}
        await self.write_metric(run_id, "latency_ms", latency_ms, "ms", tags)
        await self.write_metric(run_id, "tokens_used", total_tokens, "tokens", tags)
        await self.write_metric(run_id, "cost_usd", total_cost_usd, "usd", tags)
        await self.write_metric(run_id, "success", 1.0 if success else 0.0, "bool", tags)

    async def get_summary(self) -> dict:
        """Aggregate metrics for the observability dashboard overview."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(DISTINCT run_id)                                      AS total_runs,
                        COALESCE(AVG(CASE WHEN metric_name='success' THEN metric_value END), 0) AS success_rate,
                        COALESCE(AVG(CASE WHEN metric_name='latency_ms' THEN metric_value END), 0) AS avg_latency_ms,
                        COALESCE(SUM(CASE WHEN metric_name='cost_usd' THEN metric_value END), 0) AS total_cost_usd,
                        COALESCE(AVG(CASE WHEN metric_name='cost_usd' THEN metric_value END), 0) AS avg_cost_usd
                    FROM run_metrics
                    WHERE recorded_at > now() - INTERVAL '30 days'
                    """
                )
            return dict(row) if row else {}
        except Exception as e:
            logger.error("MetricsStore.get_summary failed: %s", e)
            return {}

    async def get_cost_by_agent(self, days: int = 7) -> list[dict]:
        """Cost breakdown by agent tag for the cost analysis dashboard page."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        tags->>'agent'              AS agent,
                        DATE(recorded_at)           AS date,
                        SUM(metric_value)           AS total_cost_usd,
                        COUNT(*)                    AS run_count
                    FROM run_metrics
                    WHERE metric_name = 'cost_usd'
                      AND recorded_at > now() - ($1 || ' days')::INTERVAL
                    GROUP BY 1, 2
                    ORDER BY 2 DESC, 3 DESC
                    """,
                    days,
                )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("MetricsStore.get_cost_by_agent failed: %s", e)
            return []
