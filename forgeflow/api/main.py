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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from forgeflow.a2a.registry import register_default_agents
from forgeflow.database import close_pool, init_pool
from forgeflow.graph.builder import compile_graph
from forgeflow.mcp.client.adapter import get_mcp_tools
from forgeflow.middleware.audit import AuditMiddleware
from forgeflow.middleware.auth import RBACMiddleware
from forgeflow.middleware.rate_limit import RateLimitMiddleware
from forgeflow.middleware.security import SecurityMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ForgeFlow API starting...")

    # Database pool
    app.state.pool = await init_pool()
    logger.info("Database pool ready")

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

    logger.info("ForgeFlow API ready")
    yield

    logger.info("ForgeFlow API shutting down...")
    await close_pool()


app = FastAPI(
    title="ForgeFlow API",
    description="Multi-Agent Enterprise Workflow Orchestrator — LangGraph + MCP + A2A",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware stack (order matters — executed bottom-up on request, top-down on response)
# Request flow:  RBAC → Security (PII redact + prompt guard) → Audit → RateLimit → handler
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RBACMiddleware)

# Routers
from forgeflow.api.routers import agents, approvals, memory, metrics, workflows

app.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])


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
