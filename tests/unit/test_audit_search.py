"""Tests for the audit-log search router."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.api.routers.audit import audit_stats, search_audit_log


def _mock_pool(count: int, rows: list[dict]):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"n": count})
    conn.fetch = AsyncMock(return_value=rows)
    pool = MagicMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    return pool, conn


class TestSearchAuditLog:
    @pytest.mark.asyncio
    async def test_returns_paginated_envelope(self):
        pool, _ = _mock_pool(count=3, rows=[])
        result = await search_audit_log(pool=pool)

        assert result["total"] == 3
        assert result["items"] == []
        assert result["limit"] == 50
        assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_filters_compose_into_where_clause(self):
        from datetime import datetime
        pool, conn = _mock_pool(count=0, rows=[])

        await search_audit_log(
            user_id="u-1",
            role="manager",
            action="POST",
            resource="/workflows",
            outcome="denied",
            since=datetime(2026, 5, 1),
            until=datetime(2026, 5, 20),
            limit=100,
            offset=10,
            pool=pool,
        )

        count_sql = conn.fetchrow.call_args[0][0]
        # Every filter must produce a clause; substring presence is enough
        assert "user_id::text" in count_sql
        assert "role" in count_sql
        assert "action" in count_sql
        assert "resource ILIKE" in count_sql
        assert "outcome" in count_sql

    @pytest.mark.asyncio
    async def test_returns_serialized_rows(self):
        from datetime import datetime
        pool, _ = _mock_pool(
            count=1,
            rows=[
                {
                    "id": 42,
                    "timestamp": datetime(2026, 5, 19, 14, 0, tzinfo=UTC),
                    "user_id": "u-1",
                    "role": "manager",
                    "action": "POST",
                    "resource": "/workflows/run",
                    "resource_id": None,
                    "outcome": "allowed",
                    "request_id": "req-1",
                    "metadata": {"status_code": 200},
                }
            ],
        )
        result = await search_audit_log(pool=pool, action="POST")

        assert result["total"] == 1
        assert result["items"][0]["resource"] == "/workflows/run"
        assert result["items"][0]["outcome"] == "allowed"
        assert result["items"][0]["metadata"] == {"status_code": 200}
        # Timestamps are ISO-formatted for JSON safety
        assert isinstance(result["items"][0]["timestamp"], str)

    @pytest.mark.asyncio
    async def test_db_error_returns_structured_error(self):
        pool = MagicMock()
        pool.acquire.side_effect = RuntimeError("connection refused")

        result = await search_audit_log(pool=pool)

        assert result["total"] == 0
        assert result["items"] == []
        assert "error" in result


class TestAuditStats:
    @pytest.mark.asyncio
    async def test_aggregates_and_top_resources(self):
        pool = MagicMock()
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(
            return_value={"total": 100, "denied": 5, "errors": 2, "distinct_users": 7}
        )
        conn.fetch = AsyncMock(
            return_value=[
                {"resource": "/workflows/run", "hits": 30},
                {"resource": "/metrics", "hits": 25},
            ]
        )
        pool.acquire = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=conn),
                __aexit__=AsyncMock(return_value=None),
            )
        )

        result = await audit_stats(pool=pool, days=7)

        assert result["total"] == 100
        assert result["denied"] == 5
        assert result["distinct_users"] == 7
        assert len(result["top_resources"]) == 2
        assert result["top_resources"][0]["resource"] == "/workflows/run"
