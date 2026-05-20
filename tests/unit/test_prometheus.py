"""Tests for the Prometheus metrics endpoint plumbing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.observability.prometheus import _build_registry, refresh_from_db, render


class TestPrometheusRegistry:
    def test_build_registry_creates_all_series(self):
        registry, metrics = _build_registry()

        expected = {
            "runs_total",
            "latency_seconds",
            "cost_usd",
            "tokens",
            "approvals_pending",
            "budget_exceeded",
            "pii_redactions",
            "prompt_blocks",
        }
        assert expected <= set(metrics.keys())

    def test_render_returns_prometheus_text_format(self):
        registry, metrics = _build_registry()
        metrics["budget_exceeded"].inc()
        metrics["runs_total"].labels(workflow_type="sales_ops", status="done").inc(3)

        body, content_type = render(registry)
        text = body.decode("utf-8")

        assert "forgeflow_budget_exceeded_total 1.0" in text
        assert 'workflow_type="sales_ops"' in text
        assert 'status="done"' in text
        assert "text/plain" in content_type


class TestRefreshFromDB:
    @pytest.mark.asyncio
    async def test_refresh_populates_metrics_from_db_rows(self):
        registry, metrics = _build_registry()

        # Mock pool + connection
        conn = AsyncMock()
        conn.fetch = AsyncMock(
            side_effect=[
                [
                    {"workflow_type": "sales_ops", "status": "done", "n": 5},
                    {"workflow_type": "support_ops", "status": "running", "n": 2},
                ],
                [
                    {"workflow_type": "sales_ops", "total_cost": 1.23, "total_tokens": 5000},
                ],
            ]
        )
        conn.fetchrow = AsyncMock(return_value={"n": 4})

        pool = MagicMock()
        pool.acquire = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=conn),
                __aexit__=AsyncMock(return_value=None),
            )
        )

        await refresh_from_db(pool, metrics)

        body, _ = render(registry)
        text = body.decode("utf-8")

        # Run counters populated
        assert 'workflow_type="sales_ops",status="done"' in text
        assert 'workflow_type="support_ops",status="running"' in text
        # Approvals gauge populated
        assert "forgeflow_approvals_pending 4.0" in text

    @pytest.mark.asyncio
    async def test_refresh_swallows_db_errors(self):
        """A broken DB should not blow up the metrics endpoint."""
        registry, metrics = _build_registry()

        pool = MagicMock()
        pool.acquire.side_effect = RuntimeError("pool exhausted")

        # Should not raise
        await refresh_from_db(pool, metrics)
