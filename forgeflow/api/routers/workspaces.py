"""Workspace management routes — multi-tenant administration.

Workspaces are the tenant root. Every tenant-scoped row in the database
(workflow_runs, approval_requests, leads, proposals, run_metrics,
memory_vectors, audit_log) carries a nullable workspace_id pointing here.

This router exposes the minimal admin surface needed to bootstrap a tenant.
Full multi-tenant query scoping is in-progress — see ROADMAP.md Phase 3.5.
"""

from __future__ import annotations

import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from forgeflow.api.dependencies import get_pool

logger = logging.getLogger(__name__)
router = APIRouter()


class WorkspaceCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=256)
    settings: dict = Field(default_factory=dict)


class WorkspaceResponse(BaseModel):
    id: str
    slug: str
    name: str
    settings: dict
    created_at: str
    archived: bool


@router.get("/", response_model=list[WorkspaceResponse])
async def list_workspaces(pool: asyncpg.Pool = Depends(get_pool)):
    """List all workspaces (admin-only via RBAC)."""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id::text, slug, name, settings, created_at, archived_at
                FROM workspaces
                ORDER BY created_at DESC
                """
            )
    except Exception as exc:
        logger.exception("workspace list failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [
        WorkspaceResponse(
            id=r["id"],
            slug=r["slug"],
            name=r["name"],
            settings=dict(r["settings"]) if r["settings"] else {},
            created_at=r["created_at"].isoformat() if r["created_at"] else "",
            archived=r["archived_at"] is not None,
        )
        for r in rows
    ]


@router.post("/", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Create a new workspace (admin-only)."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO workspaces (slug, name, settings)
                VALUES ($1, $2, $3)
                RETURNING id::text, slug, name, settings, created_at, archived_at
                """,
                body.slug,
                body.name,
                body.settings,
            )
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(
            status_code=409, detail=f"workspace slug '{body.slug}' already exists"
        ) from exc
    except Exception as exc:
        logger.exception("workspace create failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return WorkspaceResponse(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        settings=dict(row["settings"]) if row["settings"] else {},
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
        archived=row["archived_at"] is not None,
    )


@router.get("/{slug}", response_model=WorkspaceResponse)
async def get_workspace(slug: str, pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, slug, name, settings, created_at, archived_at
            FROM workspaces WHERE slug = $1
            """,
            slug,
        )
    if row is None:
        raise HTTPException(status_code=404, detail=f"workspace '{slug}' not found")

    return WorkspaceResponse(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        settings=dict(row["settings"]) if row["settings"] else {},
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
        archived=row["archived_at"] is not None,
    )
