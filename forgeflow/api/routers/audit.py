"""Audit-log search API — compliance + incident investigation.

Reads from the partitioned audit_log table populated by AuditMiddleware on
every request. Supports filtering by user, role, action (HTTP method),
resource (path), outcome, and a time window. Returns paginated results
sorted by most recent first.

This is the read path; the immutable write path is in middleware/audit.py.
"""

from __future__ import annotations

import logging
from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends, Query

from forgeflow.api.dependencies import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search")
async def search_audit_log(
    user_id: str | None = Query(None, description="Exact user_id match"),
    role: str | None = Query(None, description="Exact role match"),
    action: str | None = Query(None, description="HTTP method filter (GET, POST, ...)"),
    resource: str | None = Query(None, description="Substring match on URL path"),
    outcome: str | None = Query(None, description="allowed | denied | error"),
    since: datetime | None = Query(None, description="Start of time window (ISO-8601)"),
    until: datetime | None = Query(None, description="End of time window (ISO-8601)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    """Search the audit log. Returns {total, items, limit, offset}."""

    clauses: list[str] = ["1=1"]
    params: list = []
    idx = 1

    def _add(clause: str, value) -> None:
        nonlocal idx
        clauses.append(clause.replace("$X", f"${idx}"))
        params.append(value)
        idx += 1

    if user_id:
        _add("user_id::text = $X", user_id)
    if role:
        _add("role = $X", role)
    if action:
        _add("action = $X", action.upper())
    if resource:
        _add("resource ILIKE $X", f"%{resource}%")
    if outcome:
        _add("outcome = $X", outcome)
    if since:
        _add("timestamp >= $X", since)
    if until:
        _add("timestamp < $X", until)

    where_sql = " AND ".join(clauses)

    count_sql = f"SELECT COUNT(*) AS n FROM audit_log WHERE {where_sql}"

    items_sql = f"""
        SELECT
            id,
            timestamp,
            user_id::text  AS user_id,
            role,
            action,
            resource,
            resource_id,
            outcome,
            request_id::text AS request_id,
            metadata
        FROM audit_log
        WHERE {where_sql}
        ORDER BY timestamp DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """

    try:
        async with pool.acquire() as conn:
            count_row = await conn.fetchrow(count_sql, *params)
            rows = await conn.fetch(items_sql, *params, limit, offset)
    except Exception as exc:
        logger.exception("Audit search failed: %s", exc)
        return {"total": 0, "items": [], "limit": limit, "offset": offset, "error": str(exc)}

    items = [
        {
            "id": r["id"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "user_id": r["user_id"],
            "role": r["role"],
            "action": r["action"],
            "resource": r["resource"],
            "resource_id": r["resource_id"],
            "outcome": r["outcome"],
            "request_id": r["request_id"],
            "metadata": dict(r["metadata"]) if r["metadata"] else {},
        }
        for r in rows
    ]

    return {
        "total": int(count_row["n"]) if count_row else 0,
        "items": items,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def audit_stats(
    days: int = Query(7, ge=1, le=365),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict:
    """High-level audit aggregates for the dashboard overview card."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*)                                        AS total,
                    COUNT(*) FILTER (WHERE outcome = 'denied')      AS denied,
                    COUNT(*) FILTER (WHERE outcome = 'error')       AS errors,
                    COUNT(DISTINCT user_id)                         AS distinct_users
                FROM audit_log
                WHERE timestamp > now() - ($1 || ' days')::INTERVAL
                """,
                days,
            )
            top_resources = await conn.fetch(
                """
                SELECT resource, COUNT(*) AS hits
                FROM audit_log
                WHERE timestamp > now() - ($1 || ' days')::INTERVAL
                GROUP BY resource
                ORDER BY hits DESC
                LIMIT 10
                """,
                days,
            )
    except Exception as exc:
        logger.exception("Audit stats failed: %s", exc)
        return {"error": str(exc)}

    return {
        "window_days": days,
        "total": int(row["total"]) if row else 0,
        "denied": int(row["denied"]) if row else 0,
        "errors": int(row["errors"]) if row else 0,
        "distinct_users": int(row["distinct_users"]) if row else 0,
        "top_resources": [{"resource": r["resource"], "hits": r["hits"]} for r in top_resources],
    }
