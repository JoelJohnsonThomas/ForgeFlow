"""FastAPI dependency injection — get_pool, get_graph, get_current_user."""

from __future__ import annotations

import asyncpg
from fastapi import HTTPException, Request

from forgeflow.rbac.models import UserContext


async def get_pool(request: Request) -> asyncpg.Pool:
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool not initialised")
    return pool


async def get_graph(request: Request):
    """Backwards-compatible accessor returning the default (sales_ops) graph."""
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="Agent graph not initialised")
    return graph


async def get_graphs(request: Request) -> dict:
    """Return the dict of {workflow_type: compiled_graph}. Populated at startup."""
    graphs = getattr(request.app.state, "graphs", None)
    if not graphs:
        raise HTTPException(status_code=503, detail="Agent graphs not initialised")
    return graphs


async def get_current_user(request: Request) -> UserContext:
    return UserContext(
        user_id=getattr(request.state, "user_id", "anonymous"),
        role=getattr(request.state, "role", "viewer"),
    )
