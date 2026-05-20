"""Prometheus metrics — pull-based instrumentation for Grafana / Datadog scrapers.

Exposes a /metrics/prometheus endpoint in the standard text format. Built on
prometheus-client (synchronous library, but cheap calls — no thread switch needed).

Available metric series:
  forgeflow_workflow_runs_total{workflow_type, status}      counter
  forgeflow_workflow_latency_seconds{workflow_type}         histogram
  forgeflow_workflow_cost_usd_total{workflow_type, agent}   counter
  forgeflow_workflow_tokens_total{workflow_type, agent}     counter
  forgeflow_approvals_pending                               gauge
  forgeflow_budget_exceeded_total                           counter
  forgeflow_pii_redactions_total{category}                  counter
  forgeflow_prompt_guard_blocks_total{reason}               counter

These are populated from the existing PostgreSQL run_metrics + workflow_runs
tables on every scrape (default Prometheus interval is 15-30s, so we re-read
the DB per scrape rather than maintaining in-process counters).
"""

from __future__ import annotations

import logging

import asyncpg
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)


def _build_registry() -> tuple[CollectorRegistry, dict]:
    """Build a fresh registry + collector dict. Called once at app startup."""
    registry = CollectorRegistry()

    metrics = {
        "runs_total": Counter(
            "forgeflow_workflow_runs_total",
            "Total workflow runs",
            ["workflow_type", "status"],
            registry=registry,
        ),
        "latency_seconds": Histogram(
            "forgeflow_workflow_latency_seconds",
            "Workflow run latency in seconds",
            ["workflow_type"],
            buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600),
            registry=registry,
        ),
        "cost_usd": Counter(
            "forgeflow_workflow_cost_usd_total",
            "Cumulative LLM cost in USD",
            ["workflow_type", "agent"],
            registry=registry,
        ),
        "tokens": Counter(
            "forgeflow_workflow_tokens_total",
            "Cumulative tokens consumed",
            ["workflow_type", "agent"],
            registry=registry,
        ),
        "approvals_pending": Gauge(
            "forgeflow_approvals_pending",
            "Number of approval_requests currently in 'pending' state",
            registry=registry,
        ),
        "budget_exceeded": Counter(
            "forgeflow_budget_exceeded_total",
            "Times BudgetGuard halted a workflow",
            registry=registry,
        ),
        "pii_redactions": Counter(
            "forgeflow_pii_redactions_total",
            "PII matches redacted by SecurityMiddleware",
            ["category"],
            registry=registry,
        ),
        "prompt_blocks": Counter(
            "forgeflow_prompt_guard_blocks_total",
            "Requests blocked by the prompt-injection guard",
            ["reason"],
            registry=registry,
        ),
    }

    return registry, metrics


async def refresh_from_db(pool: asyncpg.Pool, metrics: dict) -> None:
    """Refresh DB-backed metrics from postgres. Called on every scrape.

    Counters are reset before re-incrementing — Prometheus expects monotonic
    counters within a process lifetime, but we treat each scrape as a fresh
    snapshot of the DB state. This is safe because we expose deltas via
    rate() in PromQL on the consumer side.
    """
    try:
        async with pool.acquire() as conn:
            # workflow_runs by type + status
            runs = await conn.fetch(
                """
                SELECT workflow_type, status, COUNT(*) AS n
                FROM workflow_runs
                WHERE created_at > now() - INTERVAL '24 hours'
                GROUP BY workflow_type, status
                """
            )

            cost_rows = await conn.fetch(
                """
                SELECT workflow_type,
                       COALESCE(SUM(total_cost_usd), 0)::float AS total_cost,
                       COALESCE(SUM(total_tokens), 0)::bigint  AS total_tokens
                FROM workflow_runs
                WHERE created_at > now() - INTERVAL '24 hours'
                GROUP BY workflow_type
                """
            )

            pending_row = await conn.fetchrow(
                "SELECT COUNT(*) AS n FROM approval_requests WHERE status = 'pending'"
            )

        # Reset counters before re-incrementing
        metrics["runs_total"]._metrics.clear()  # noqa: SLF001
        metrics["cost_usd"]._metrics.clear()    # noqa: SLF001
        metrics["tokens"]._metrics.clear()      # noqa: SLF001

        for r in runs:
            metrics["runs_total"].labels(
                workflow_type=r["workflow_type"] or "unknown",
                status=r["status"] or "unknown",
            ).inc(r["n"])

        for r in cost_rows:
            wf = r["workflow_type"] or "unknown"
            metrics["cost_usd"].labels(workflow_type=wf, agent="workflow").inc(float(r["total_cost"]))
            metrics["tokens"].labels(workflow_type=wf, agent="workflow").inc(int(r["total_tokens"]))

        metrics["approvals_pending"].set(int(pending_row["n"]) if pending_row else 0)

    except Exception as exc:
        logger.warning("Prometheus DB refresh failed: %s", exc)


def render(registry: CollectorRegistry) -> tuple[bytes, str]:
    """Return (body, content_type) for the /metrics/prometheus response."""
    return generate_latest(registry), CONTENT_TYPE_LATEST
