"""Approval routes — human-in-the-loop workflow management."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from forgeflow.api.dependencies import get_current_user, get_graph, get_pool
from forgeflow.api.schemas import ApprovalActionRequest, ApprovalRequestResponse
from forgeflow.rbac.models import UserContext
from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/pending", response_model=list[ApprovalRequestResponse])
async def list_pending_approvals(
    pool: asyncpg.Pool = Depends(get_pool),
    user: UserContext = Depends(get_current_user),
):
    """List all pending approval requests (for the approval queue UI)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM approval_requests
            WHERE status = 'pending'
              AND expires_at > now()
            ORDER BY requested_at DESC
            """
        )
    return [_row_to_schema(r) for r in rows]


@router.get("/{token}", response_model=ApprovalRequestResponse)
async def get_approval(
    token: str,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Get a specific approval request by its token."""
    row = await _fetch_by_token(pool, token)
    return _row_to_schema(row)


@router.post("/{token}/approve")
async def approve(
    token: str,
    body: ApprovalActionRequest,
    pool: asyncpg.Pool = Depends(get_pool),
    graph=Depends(get_graph),
    user: UserContext = Depends(get_current_user),
):
    """Approve a proposal — resumes the suspended LangGraph workflow."""
    row = await _fetch_by_token(pool, token)

    # Get the thread_id for this run
    async with pool.acquire() as conn:
        run_row = await conn.fetchrow(
            "SELECT thread_id FROM workflow_runs WHERE id = $1",
            row["run_id"],
        )

    if not run_row:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    thread_id = str(run_row["thread_id"])

    # Resume the graph with approved status
    pipeline = SalesOpsPipeline(graph)
    try:
        await pipeline.resume(thread_id=thread_id, approval_status="approved", resolved_by=user.user_id)
    except Exception as e:
        logger.error("Graph resume failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to resume workflow: {e}") from e

    # Update approval record
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE approval_requests
            SET status = 'approved', resolved_at = now(), resolved_by = $2, resolution_note = $3
            WHERE token = $1
            """,
            uuid.UUID(token),
            user.user_id,
            body.note,
        )
        await conn.execute(
            "UPDATE workflow_runs SET status = 'completed', completed_at = now() WHERE id = $1",
            row["run_id"],
        )

    return {"status": "approved", "thread_id": thread_id, "message": "Workflow resumed and executing"}


@router.post("/{token}/reject")
async def reject(
    token: str,
    body: ApprovalActionRequest,
    pool: asyncpg.Pool = Depends(get_pool),
    graph=Depends(get_graph),
    user: UserContext = Depends(get_current_user),
):
    """Reject a proposal — resumes the suspended workflow with rejected status."""
    row = await _fetch_by_token(pool, token)

    async with pool.acquire() as conn:
        run_row = await conn.fetchrow(
            "SELECT thread_id FROM workflow_runs WHERE id = $1",
            row["run_id"],
        )

    thread_id = str(run_row["thread_id"])

    pipeline = SalesOpsPipeline(graph)
    try:
        await pipeline.resume(thread_id=thread_id, approval_status="rejected")
    except Exception as e:
        logger.error("Graph resume (reject) failed: %s", e)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE approval_requests
            SET status = 'rejected', resolved_at = now(), resolved_by = $2, resolution_note = $3
            WHERE token = $1
            """,
            uuid.UUID(token),
            user.user_id,
            body.reason or body.note,
        )
        await conn.execute(
            "UPDATE workflow_runs SET status = 'rejected', completed_at = now() WHERE id = $1",
            row["run_id"],
        )

    return {"status": "rejected", "thread_id": thread_id}


async def _fetch_by_token(pool: asyncpg.Pool, token: str) -> dict:
    try:
        token_uuid = uuid.UUID(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid token format") from exc

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM approval_requests WHERE token = $1",
            token_uuid,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if row["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Approval already {row['status']}")

    if row["expires_at"].replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=410, detail="Approval request has expired")

    return dict(row)


def _row_to_schema(row: dict) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=str(row["id"]),
        run_id=str(row["run_id"]),
        token=str(row["token"]),
        stage=row["stage"],
        status=row["status"],
        payload=row["payload"],
        requested_at=row["requested_at"],
        expires_at=row["expires_at"],
        resolved_at=row.get("resolved_at"),
        resolution_note=row.get("resolution_note"),
    )
