"""Workflow routes — run, stream (SSE), status, trace."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from forgeflow.api.dependencies import (
    get_current_user,
    get_graphs,
    get_pool,
    get_workspace_id,
)
from forgeflow.api.schemas import (
    AgentTraceResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowStatusResponse,
)
from forgeflow.config import get_settings
from forgeflow.notifications.slack import notify_approval_request
from forgeflow.rbac.models import UserContext
from forgeflow.workflows.finance_recon.models import ReconciliationInput
from forgeflow.workflows.finance_recon.pipeline import FinanceReconPipeline
from forgeflow.workflows.sales_ops.models import LeadInput
from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline
from forgeflow.workflows.support_ops.models import TicketInput
from forgeflow.workflows.support_ops.pipeline import SupportOpsPipeline

logger = logging.getLogger(__name__)
router = APIRouter()

# Roles allowed to read ANY run within their workspace (oversight / approval /
# admin duties). Every other role (notably sales_rep) may only read runs it
# owns — this closes the horizontal IDOR where one rep could read another rep's
# run + agent trace (prompts + LLM output) by guessing the run id.
_ELEVATED_READ_ROLES = frozenset({"admin", "manager", "viewer", "service"})


def _assert_can_read_run(user: UserContext, row_user_id: str | None) -> None:
    """Object-level authorization for a single run row.

    RBAC already proved the caller has read:workflows. This adds ownership:
    non-elevated roles may only see their own runs. Raises 404 (not 403) so we
    don't confirm the existence of a run the caller isn't allowed to see.
    """
    if user.role in _ELEVATED_READ_ROLES:
        return
    if row_user_id is not None and str(row_user_id) == str(user.user_id):
        return
    raise HTTPException(status_code=404, detail="Workflow run not found")


def _dispatch_pipeline(workflow_type: str, graph, payload: dict):
    """Pick the right (pipeline, input_model_instance) pair for a workflow type."""
    if workflow_type == "support_ops":
        return SupportOpsPipeline(graph), TicketInput(**payload)
    if workflow_type == "finance_recon":
        return FinanceReconPipeline(graph), ReconciliationInput(**payload)
    # default: sales_ops
    return SalesOpsPipeline(graph), LeadInput(**payload)


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(
    request: WorkflowRunRequest,
    graphs: dict = Depends(get_graphs),
    pool: asyncpg.Pool = Depends(get_pool),
    user: UserContext = Depends(get_current_user),
    workspace_id: str | None = Depends(get_workspace_id),
):
    """Trigger a new workflow run. Returns run_id and thread_id for tracking."""
    graph = graphs.get(request.workflow_type)
    if graph is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown workflow_type '{request.workflow_type}'",
        )

    try:
        pipeline, domain_input = _dispatch_pipeline(
            request.workflow_type, graph, request.lead_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid payload for workflow_type '{request.workflow_type}': {e}",
        ) from e

    start = time.monotonic()

    timeout_s = get_settings().workflow_run_timeout_seconds
    try:
        workflow_id, thread_id, final_state = await asyncio.wait_for(
            pipeline.run(
                domain_input,
                user_id=user.user_id,
                role=user.role,
                dry_run=request.dry_run,
            ),
            timeout=timeout_s,
        )
    except TimeoutError as e:
        # Free the worker rather than blocking on a hung LLM/tool. The run is
        # checkpointed in Postgres, so it can be inspected/resumed out-of-band.
        logger.error("Workflow run timed out after %ss", timeout_s)
        raise HTTPException(
            status_code=504,
            detail=f"Workflow exceeded the {timeout_s}s execution limit.",
        ) from e
    except Exception as e:
        logger.error("Workflow run failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    latency_ms = (time.monotonic() - start) * 1000
    stage = final_state.get("current_stage", "unknown")

    # Persist run record (tenant-scoped via workspace_id when present).
    # user_id stores the JWT subject string (e.g. "rep-1") — see migration 007,
    # which widened the column from UUID to VARCHAR. Attributing the run to its
    # owner is what backs object-level authorization on the read endpoints below.
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workflow_runs
                  (id, thread_id, workflow_type, status, input_data, output_data,
                   total_tokens, total_cost_usd, user_id, metadata, workspace_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
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
                str(user.user_id),
                {"latency_ms": round(latency_ms, 1)},
                uuid.UUID(workspace_id) if workspace_id else None,
            )
    except Exception as e:
        logger.error("Failed to persist workflow run: %s", e)

    # If the workflow suspended for human approval, create approval request
    if stage == "approve" or final_state.get("approval_token"):
        token = final_state.get("approval_token") or str(uuid.uuid4())
        proposal_payload = final_state.get("proposal") or {}
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
                    proposal_payload,
                )
        except Exception as e:
            logger.error("Failed to create approval request: %s", e)

        # Fire-and-forget Slack notification — skipped in dry-run, no-op when
        # Slack isn't configured.
        if request.dry_run:
            logger.info("Dry-run — skipping Slack approval notification")
        else:
            try:
                company = (
                    proposal_payload.get("company")
                    or request.lead_data.get("company_name")
                    or request.lead_data.get("ticket_id")
                    or request.lead_data.get("period_label")
                    or "(unknown)"
                )
                summary = (
                    f"workflow_type={request.workflow_type} | "
                    f"subject={company} | run_id={workflow_id}"
                )
                await notify_approval_request(
                    approval_token=token,
                    summary=summary,
                    payload=proposal_payload,
                )
            except Exception as e:
                logger.warning("Slack approval notification failed: %s", e)

    return WorkflowRunResponse(
        run_id=workflow_id,
        thread_id=thread_id,
        status="pending_approval" if stage == "approve" else "completed",
        message=f"Workflow {stage}. Stage: {stage}",
    )


@router.post("/stream")
async def stream_workflow(
    request: WorkflowRunRequest,
    graphs: dict = Depends(get_graphs),
    user: UserContext = Depends(get_current_user),
):
    """Stream workflow events as Server-Sent Events (SSE)."""
    graph = graphs.get(request.workflow_type)
    if graph is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown workflow_type '{request.workflow_type}'",
        )

    try:
        pipeline, domain_input = _dispatch_pipeline(
            request.workflow_type, graph, request.lead_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid payload for workflow_type '{request.workflow_type}': {e}",
        ) from e

    async def event_generator():
        try:
            async for event in pipeline.stream(
                domain_input,
                user.user_id,
                user.role,
                dry_run=request.dry_run,
            ):
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
    user: UserContext = Depends(get_current_user),
    workspace_id: str | None = Depends(get_workspace_id),
):
    """Get the current status and state of a workflow run.

    Tenant-scoped: callers carrying a workspace claim can only fetch runs
    in their workspace. Calls with no workspace_id see rows where
    workspace_id IS NULL (legacy / global runs) — this preserves
    single-tenant deployments through the migration window.

    Object-scoped: non-elevated roles (e.g. sales_rep) may only read their
    own runs — see _assert_can_read_run.
    """
    try:
        async with pool.acquire() as conn:
            if workspace_id:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM workflow_runs
                    WHERE id = $1 AND workspace_id = $2
                    """,
                    uuid.UUID(run_id),
                    uuid.UUID(workspace_id),
                )
            else:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM workflow_runs
                    WHERE id = $1 AND workspace_id IS NULL
                    """,
                    uuid.UUID(run_id),
                )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid run_id: {e}") from e

    if not row:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    r = dict(row)
    _assert_can_read_run(user, r.get("user_id"))
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
    user: UserContext = Depends(get_current_user),
    workspace_id: str | None = Depends(get_workspace_id),
):
    """Get per-agent execution traces for a workflow run.

    Tenant-scoped: we first verify the run belongs to the caller's workspace
    (or is a legacy NULL-workspace row when the caller has no workspace
    claim) before returning trace data.

    Object-scoped: traces expose prompts + LLM output, so non-elevated roles
    may only read traces of runs they own — see _assert_can_read_run.
    """
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid run_id") from exc

    try:
        async with pool.acquire() as conn:
            if workspace_id:
                owner = await conn.fetchrow(
                    "SELECT user_id FROM workflow_runs WHERE id = $1 AND workspace_id = $2",
                    run_uuid,
                    uuid.UUID(workspace_id),
                )
            else:
                owner = await conn.fetchrow(
                    "SELECT user_id FROM workflow_runs WHERE id = $1 AND workspace_id IS NULL",
                    run_uuid,
                )
            if owner is None:
                raise HTTPException(status_code=404, detail="Workflow run not found")
            _assert_can_read_run(user, dict(owner).get("user_id"))

            rows = await conn.fetch(
                "SELECT * FROM agent_traces WHERE run_id = $1 ORDER BY started_at",
                run_uuid,
            )
    except HTTPException:
        raise
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
