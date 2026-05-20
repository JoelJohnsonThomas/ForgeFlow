"""Workflow routes — run, stream (SSE), status, trace."""

from __future__ import annotations

import json
import logging
import time
import uuid

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from forgeflow.api.dependencies import get_current_user, get_graph, get_pool
from forgeflow.api.schemas import (
    AgentTraceResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowStatusResponse,
)
from forgeflow.rbac.models import UserContext
from forgeflow.workflows.sales_ops.models import LeadInput
from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(
    request: WorkflowRunRequest,
    graph=Depends(get_graph),
    pool: asyncpg.Pool = Depends(get_pool),
    user: UserContext = Depends(get_current_user),
):
    """Trigger a new workflow run. Returns run_id and thread_id for tracking."""
    lead_input = LeadInput(
        company_name=request.lead_data.get("company_name", "Unknown"),
        **{k: v for k, v in request.lead_data.items() if k != "company_name"},
    )

    pipeline = SalesOpsPipeline(graph)
    start = time.monotonic()

    try:
        workflow_id, thread_id, final_state = await pipeline.run(
            lead_input=lead_input,
            user_id=user.user_id,
            role=user.role,
        )
    except Exception as e:
        logger.error("Workflow run failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    latency_ms = (time.monotonic() - start) * 1000
    stage = final_state.get("current_stage", "unknown")

    # Persist run record
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workflow_runs
                  (id, thread_id, workflow_type, status, input_data, output_data,
                   total_tokens, total_cost_usd, user_id, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                uuid.UUID(workflow_id),
                uuid.UUID(thread_id),
                request.workflow_type,
                "pending_approval" if stage == "approve" else (
                    "completed" if stage == "done" else "running"
                ),
                request.lead_data,
                {"final_stage": stage},
                final_state.get("total_tokens", 0),
                final_state.get("total_cost_usd", 0.0),
                user.user_id,
                {"latency_ms": round(latency_ms, 1)},
            )
    except Exception as e:
        logger.error("Failed to persist workflow run: %s", e)

    # If the workflow suspended for human approval, create approval request
    if stage == "approve" or final_state.get("approval_token"):
        token = final_state.get("approval_token") or str(uuid.uuid4())
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO approval_requests (run_id, token, stage, payload)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                    """,
                    uuid.UUID(workflow_id),
                    uuid.UUID(token),
                    "propose",
                    final_state.get("proposal") or {},
                )
        except Exception as e:
            logger.error("Failed to create approval request: %s", e)

    return WorkflowRunResponse(
        run_id=workflow_id,
        thread_id=thread_id,
        status="pending_approval" if stage == "approve" else "completed",
        message=f"Workflow {stage}. Stage: {stage}",
    )


@router.post("/stream")
async def stream_workflow(
    request: WorkflowRunRequest,
    graph=Depends(get_graph),
    user: UserContext = Depends(get_current_user),
):
    """Stream workflow events as Server-Sent Events (SSE)."""
    lead_input = LeadInput(company_name=request.lead_data.get("company_name", "Unknown"))
    pipeline = SalesOpsPipeline(graph)

    async def event_generator():
        try:
            async for event in pipeline.stream(lead_input, user.user_id, user.role):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/{run_id}", response_model=WorkflowStatusResponse)
async def get_workflow(
    run_id: str,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Get the current status and state of a workflow run."""
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_runs WHERE id = $1",
                uuid.UUID(run_id),
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid run_id: {e}") from e

    if not row:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    r = dict(row)
    return WorkflowStatusResponse(
        run_id=str(r["id"]),
        thread_id=str(r["thread_id"]),
        status=r["status"],
        current_stage=r.get("metadata", {}).get("final_stage", "unknown"),
        total_tokens=r["total_tokens"],
        total_cost_usd=float(r["total_cost_usd"]),
        created_at=r["created_at"],
        completed_at=r.get("completed_at"),
        lead_data=r.get("input_data"),
    )


@router.get("/{run_id}/trace", response_model=list[AgentTraceResponse])
async def get_trace(
    run_id: str,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Get per-agent execution traces for a workflow run."""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM agent_traces WHERE run_id = $1 ORDER BY started_at",
                uuid.UUID(run_id),
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return [
        AgentTraceResponse(
            id=str(r["id"]),
            agent_name=r["agent_name"],
            stage=r["stage"],
            started_at=r["started_at"],
            completed_at=r.get("completed_at"),
            tokens_used=r["tokens_used"],
            cost_usd=float(r["cost_usd"]),
            error=r.get("error"),
            output_patch=r.get("output_patch"),
        )
        for r in rows
    ]
