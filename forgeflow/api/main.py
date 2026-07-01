"""ForgeFlow FastAPI application — app factory with lifespan management.

Startup:
  1. Initialize asyncpg connection pool
  2. Compile LangGraph StateGraph (with PostgreSQL checkpointer)
  3. Load MCP tools from tool server (graceful fallback if unavailable)
  4. Register agents in A2A registry

Shutdown:
  1. Close connection pool
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from forgeflow.a2a.registry import register_default_agents
from forgeflow.config import Settings, get_settings
from forgeflow.database import close_pool, init_pool
from forgeflow.events.dispatcher import EventDispatcher
from forgeflow.graph.builder import compile_graph
from forgeflow.jobs.escalation import ApprovalEscalationJob, EscalationThresholds
from forgeflow.mcp.client.adapter import get_mcp_tools
from forgeflow.middleware.audit import AuditMiddleware
from forgeflow.middleware.auth import RBACMiddleware
from forgeflow.middleware.rate_limit import RateLimitMiddleware
from forgeflow.middleware.security import SecurityMiddleware
from forgeflow.middleware.security_headers import SecurityHeadersMiddleware
from forgeflow.observability.prometheus import _build_registry
from forgeflow.observability.tracing import init_tracing
from forgeflow.observability.tracing_provider import configure as configure_tracing_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ForgeFlow API starting...")

    # Fail-fast configuration validation. In production any problem aborts
    # startup (fail closed); in dev we log warnings so local work isn't blocked.
    _startup_settings = get_settings()
    _config_problems = _startup_settings.validate_runtime()
    if _config_problems:
        for _p in _config_problems:
            logger.error("CONFIG: %s", _p)
        if _startup_settings.is_production():
            raise RuntimeError(
                f"Refusing to start: {len(_config_problems)} fatal configuration "
                f"problem(s) in production — see CONFIG errors above."
            )
        logger.warning(
            "Continuing in non-production despite %d config warning(s).",
            len(_config_problems),
        )

    # Database pool
    app.state.pool = await init_pool()
    logger.info("Database pool ready")

    # Seed the demo users into the credential store so the local/dev password
    # login keeps working after the Increment-2 auth overhaul. Prod (dev login
    # off) skips this and relies on OIDC / externally-provisioned users.
    if _startup_settings.dev_login_enabled:
        await _seed_demo_users(app.state.pool, _startup_settings)

    # MCP tools (optional — agents degrade gracefully without them)
    mcp_tools = await get_mcp_tools()
    logger.info("MCP tools loaded: %d", len(mcp_tools))

    # Agent graphs — one compiled graph per workflow_type, prompts differ per domain
    app.state.graphs = {
        "sales_ops": await compile_graph(mcp_tools=mcp_tools, workflow_type="sales_ops"),
        "support_ops": await compile_graph(mcp_tools=mcp_tools, workflow_type="support_ops"),
        "finance_recon": await compile_graph(mcp_tools=mcp_tools, workflow_type="finance_recon"),
    }
    # Default exposure for code paths that still expect a single graph
    app.state.graph = app.state.graphs["sales_ops"]
    logger.info("Agent graphs compiled | types=%s", list(app.state.graphs))

    # A2A registry
    register_default_agents()
    logger.info("A2A registry populated")

    # Prometheus registry — populated lazily on each /metrics/prometheus scrape
    registry, prom_metrics = _build_registry()
    app.state.prom_registry = registry
    app.state.prom_metrics = prom_metrics
    logger.info("Prometheus registry initialised")

    # Approval escalation background task
    settings = get_settings()
    escalation_job = ApprovalEscalationJob(
        pool=app.state.pool,
        interval_seconds=settings.approval_escalation_interval_seconds,
        thresholds=EscalationThresholds(
            first_escalation_minutes=settings.approval_first_escalation_minutes,
            second_escalation_minutes=settings.approval_second_escalation_minutes,
            auto_reject_minutes=settings.approval_auto_reject_minutes,
        ),
    )
    escalation_job.start()
    app.state.escalation_job = escalation_job

    # Optional event-driven consumer (Redis Streams or Kafka)
    app.state.event_consumer = None
    if settings.events_provider in ("redis", "kafka"):
        dispatcher = EventDispatcher(graphs=app.state.graphs)
        try:
            app.state.event_consumer = await _build_event_consumer(settings, dispatcher)
            await app.state.event_consumer.start()
        except Exception as exc:
            logger.warning(
                "Event consumer (%s) failed to start; continuing without it: %s",
                settings.events_provider,
                exc,
            )
            app.state.event_consumer = None

    logger.info("ForgeFlow API ready")
    yield

    logger.info("ForgeFlow API shutting down...")
    if getattr(app.state, "event_consumer", None):
        await app.state.event_consumer.stop()
    if getattr(app.state, "escalation_job", None):
        await app.state.escalation_job.stop()
    await close_pool()


_DEMO_USERS = {
    "admin": "admin",
    "manager-1": "manager",
    "rep-1": "sales_rep",
    "viewer-1": "viewer",
}


async def _seed_demo_users(pool: Any, settings: Settings) -> None:
    """Idempotently upsert the demo users with the dev password (Argon2-hashed).
    No-op with a warning when DEV_LOGIN_PASSWORD is unset."""
    from forgeflow.auth import passwords
    from forgeflow.auth import users as user_store

    password = settings.dev_login_password.get_secret_value()
    if not password:
        logger.warning("DEV_LOGIN_PASSWORD unset — skipping demo-user seeding")
        return
    password_hash = passwords.hash_password(password)
    for username, role in _DEMO_USERS.items():
        try:
            await user_store.upsert_local_user(pool, username, password_hash, role)
        except Exception as exc:  # noqa: BLE001
            logger.warning("demo-user seed failed for %s: %s", username, exc)
    logger.info("Seeded %d demo users into the credential store", len(_DEMO_USERS))


async def _build_event_consumer(settings: Settings, dispatcher: EventDispatcher) -> Any:
    """Construct the configured event consumer. Kept out of lifespan body
    so the lazy imports don't fire when events_provider=none.

    Return type is Any because the concrete class depends on which optional
    extra is installed; both consumers expose the same start()/stop() shape."""
    if settings.events_provider == "redis":
        from forgeflow.events.redis_consumer import RedisStreamsConsumer

        return RedisStreamsConsumer(
            dispatcher=dispatcher,
            redis_url=settings.events_redis_url,
            stream=settings.events_redis_stream,
            group=settings.events_redis_group,
            consumer_name=settings.events_redis_consumer,
        )
    if settings.events_provider == "kafka":
        from forgeflow.events.kafka_consumer import KafkaConsumer

        return KafkaConsumer(
            dispatcher=dispatcher,
            bootstrap_servers=settings.events_kafka_bootstrap_servers,
            topic=settings.events_kafka_topic,
            group_id=settings.events_kafka_group_id,
        )
    raise ValueError(f"unknown events_provider: {settings.events_provider}")


_settings_for_app = get_settings()
app = FastAPI(
    title="ForgeFlow API",
    description="Multi-Agent Enterprise Workflow Orchestrator — LangGraph + MCP + A2A",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _settings_for_app.docs_enabled else None,
    redoc_url="/redoc" if _settings_for_app.docs_enabled else None,
    openapi_url="/openapi.json" if _settings_for_app.docs_enabled else None,
)
if not _settings_for_app.dev_login_enabled:
    logger.info("DEV_LOGIN_ENABLED=false — /auth/login will return 404")
if not _settings_for_app.docs_enabled:
    logger.info("DOCS_ENABLED=false — /docs and /redoc disabled")

# Pick the tracing backend (phoenix / langfuse / langsmith / none), then wire
# OTel instrumentation if the selected backend uses OTLP.
configure_tracing_provider()
init_tracing(app)

# CORS — explicit origin allowlist from config. NEVER use "*" with credentials.
_cors_origins = get_settings().cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or [],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    max_age=600,
)

# Middleware stack — Starlette runs add_middleware bottom-up on the request
# path. We want request flow: RBAC → RateLimit → Security → Audit → handler
# (so the limiter sees the verified user_id and audits record every attempt).
# That means registering in reverse: Audit, Security, RateLimit, RBAC.
app.add_middleware(AuditMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RBACMiddleware)
# Outermost (added last) so hardening headers land on EVERY response, including
# 401/403/429 returned by the inner middlewares.
app.add_middleware(SecurityHeadersMiddleware)

# Routers
from forgeflow.api.routers import (
    agents,
    approvals,
    audit,
    auth,
    marketplace,
    memory,
    metrics,
    workflows,
    workspaces,
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(marketplace.router, prefix="/marketplace", tags=["Marketplace"])
app.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
app.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "ForgeFlow", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
async def health():
    pool = getattr(app.state, "pool", None)
    graph = getattr(app.state, "graph", None)
    return JSONResponse({
        "status": "healthy",
        "database": "connected" if pool else "unavailable",
        "graph": "compiled" if graph else "not_ready",
    })
