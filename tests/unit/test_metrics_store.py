"""Tests for MetricsStore — the new cost-breakdown + alert queries."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.observability.metrics_store import MetricsStore


def _pool_with(fetch_rows: list[dict]):
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=fetch_rows)
    pool = MagicMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    return pool, conn


class TestCostByWorkflowType:
    @pytest.mark.asyncio
    async def test_returns_dicts(self):
        pool, _ = _pool_with(
            [
                {
                    "workflow_type": "sales_ops",
                    "date": datetime(2026, 5, 1).date(),
                    "total_cost_usd": 1.23,
                    "total_tokens": 50_000,
                    "run_count": 5,
                },
                {
                    "workflow_type": "support_ops",
                    "date": datetime(2026, 5, 1).date(),
                    "total_cost_usd": 0.45,
                    "total_tokens": 20_000,
                    "run_count": 3,
                },
            ]
        )
        store = MetricsStore(pool)
        result = await store.get_cost_by_workflow_type(days=7)

        assert len(result) == 2
        assert result[0]["workflow_type"] == "sales_ops"
        assert result[0]["total_cost_usd"] == 1.23

    @pytest.mark.asyncio
    async def test_swallows_errors(self):
        pool = MagicMock()
        pool.acquire.side_effect = RuntimeError("db down")
        store = MetricsStore(pool)
        result = await store.get_cost_by_workflow_type(days=7)
        assert result == []


class TestTopExpensiveRuns:
    @pytest.mark.asyncio
    async def test_iso_serializes_datetime(self):
        pool, _ = _pool_with(
            [
                {
                    "run_id": "uuid-1",
                    "workflow_type": "sales_ops",
                    "status": "done",
                    "total_cost_usd": 0.50,
                    "total_tokens": 12_345,
                    "created_at": datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
                }
            ]
        )
        store = MetricsStore(pool)
        result = await store.get_top_expensive_runs(limit=10, days=7)

        assert result[0]["run_id"] == "uuid-1"
        assert isinstance(result[0]["created_at"], str)
        assert "2026-05-19" in result[0]["created_at"]


class TestBudgetAlerts:
    @pytest.mark.asyncio
    async def test_classifies_warning_and_exceeded(self):
        pool, _ = _pool_with(
            [
                {
                    "run_id": "run-A",
                    "workflow_type": "sales_ops",
                    "status": "done",
                    "total_cost_usd": 5.00,
                    "created_at": datetime(2026, 5, 19, tzinfo=UTC),
                    "severity": "exceeded",
                },
                {
                    "run_id": "run-B",
                    "workflow_type": "support_ops",
                    "status": "done",
                    "total_cost_usd": 4.60,
                    "created_at": datetime(2026, 5, 19, tzinfo=UTC),
                    "severity": "warning",
                },
            ]
        )
        store = MetricsStore(pool)
        result = await store.get_budget_alerts(budget_limit_usd=5.0, days=7)

        severities = [r["severity"] for r in result]
        assert "exceeded" in severities
        assert "warning" in severities

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        pool = MagicMock()
        pool.acquire.side_effect = RuntimeError("nope")
        store = MetricsStore(pool)
        assert await store.get_budget_alerts(budget_limit_usd=5.0, days=7) == []
