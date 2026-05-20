"""Metrics routes — observability data for the Streamlit dashboard + Prometheus."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from forgeflow.api.dependencies import get_pool
from forgeflow.api.schemas import EvaluationSummaryResponse, MetricsSummaryResponse
from forgeflow.observability.metrics_store import MetricsStore
from forgeflow.observability.prometheus import refresh_from_db, render

router = APIRouter()


@router.get("/prometheus", include_in_schema=False)
async def prometheus_metrics(
    request: Request,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Prometheus scrape endpoint. Returns text/plain in the standard format.

    The registry is held on app.state.prom_registry and was built at startup
    in forgeflow/api/main.py. We refresh DB-backed series on every scrape.
    """
    registry = getattr(request.app.state, "prom_registry", None)
    metrics_collectors = getattr(request.app.state, "prom_metrics", None)
    if registry is None or metrics_collectors is None:
        return Response(
            content="# prometheus registry not initialised\n",
            media_type="text/plain",
            status_code=503,
        )

    await refresh_from_db(pool, metrics_collectors)
    body, content_type = render(registry)
    return Response(content=body, media_type=content_type)


@router.get("/", response_model=MetricsSummaryResponse)
async def get_metrics_summary(pool: asyncpg.Pool = Depends(get_pool)):
    """Aggregated metrics for the dashboard overview page."""
    store = MetricsStore(pool)
    summary = await store.get_summary()

    return MetricsSummaryResponse(
        total_runs=int(summary.get("total_runs", 0)),
        success_rate=float(summary.get("success_rate", 0.0)),
        avg_latency_ms=float(summary.get("avg_latency_ms", 0.0)),
        avg_cost_usd=float(summary.get("avg_cost_usd", 0.0)),
        total_cost_usd=float(summary.get("total_cost_usd", 0.0)),
    )


@router.get("/cost")
async def get_cost_breakdown(
    days: int = Query(7, ge=1, le=90),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Cost breakdown by agent and day — used by the cost analysis page."""
    store = MetricsStore(pool)
    return await store.get_cost_by_agent(days=days)


@router.get("/cost/by_workflow_type")
async def get_cost_by_workflow_type(
    days: int = Query(7, ge=1, le=90),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Cost + token breakdown by workflow_type — for multi-domain comparisons."""
    store = MetricsStore(pool)
    return await store.get_cost_by_workflow_type(days=days)


@router.get("/cost/top_runs")
async def get_top_expensive_runs(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Top N highest-cost workflow runs in the window — drill-down list."""
    store = MetricsStore(pool)
    return await store.get_top_expensive_runs(limit=limit, days=days)


@router.get("/cost/alerts")
async def get_budget_alerts(
    days: int = Query(7, ge=1, le=90),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Workflow runs that hit the budget warning (>=90%) or limit (>=100%).

    Threshold is read from settings.budget_limit_usd at call time.
    """
    from forgeflow.config import get_settings

    settings = get_settings()
    store = MetricsStore(pool)
    return await store.get_budget_alerts(
        budget_limit_usd=settings.budget_limit_usd, days=days
    )


@router.get("/evaluation", response_model=EvaluationSummaryResponse)
async def get_evaluation_summary(pool: asyncpg.Pool = Depends(get_pool)):
    """LLM-as-judge evaluation score aggregates."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(AVG(CASE WHEN metric_name='faithfulness' THEN metric_value END), 0) AS avg_faithfulness,
                    COALESCE(AVG(CASE WHEN metric_name='relevance' THEN metric_value END), 0) AS avg_relevance,
                    COALESCE(AVG(CASE WHEN metric_name='coherence' THEN metric_value END), 0) AS avg_coherence,
                    COALESCE(AVG(CASE WHEN metric_name='hallucination' THEN metric_value END), 0) AS hallucination_rate,
                    COUNT(DISTINCT run_id) AS sample_count
                FROM run_metrics
                WHERE metric_name IN ('faithfulness', 'relevance', 'coherence', 'hallucination')
                """
            )
        if row:
            return EvaluationSummaryResponse(
                avg_faithfulness=float(row["avg_faithfulness"]),
                avg_relevance=float(row["avg_relevance"]),
                avg_coherence=float(row["avg_coherence"]),
                hallucination_rate=float(row["hallucination_rate"]),
                sample_count=int(row["sample_count"]),
            )
    except Exception:
        pass

    return EvaluationSummaryResponse(
        avg_faithfulness=0.0,
        avg_relevance=0.0,
        avg_coherence=0.0,
        hallucination_rate=0.0,
        sample_count=0,
    )


@router.get("/runs")
async def list_recent_runs(
    limit: int = Query(20, ge=1, le=100),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Recent workflow runs for the dashboard table."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, thread_id, workflow_type, status, created_at, completed_at,
                   total_tokens, total_cost_usd, metadata
            FROM workflow_runs
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [
        {
            "run_id": str(r["id"]),
            "thread_id": str(r["thread_id"]),
            "workflow_type": r["workflow_type"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            "total_tokens": r["total_tokens"],
            "total_cost_usd": float(r["total_cost_usd"]),
        }
        for r in rows
    ]
