"""SupportOpsPipeline — orchestration helper for support ticket workflows.

⚠ TEMPLATE SCAFFOLD — NOT PRODUCTION-READY

This workflow has the full LangGraph + supervisor + worker shape, but no
ticketing connector is wired (Zendesk, Intercom, Freshdesk, Linear, Front
are all unwired). Real production use requires:

  1. A ticketing connector in forgeflow/connectors/ (none exists yet)
  2. MCP tools that wrap it (knowledge base search, ticket update, reply send)
  3. Idempotency on ticket replies (don't double-send)
  4. The runbook + Fly.io deployment treatment that sales_ops has

Calling .run() or .stream() raises unless dry_run=True. Set
FORGEFLOW_ALLOW_TEMPLATE_WORKFLOWS=1 to override (e.g. for integration
tests that mock the graph). Don't override in production.

See docs/sales-ops-production.md for what "production-ready" actually
means and forgeflow/workflows/sales_ops/ for the reference implementation.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

from forgeflow.state.workflow_state import WorkflowState
from forgeflow.workflows.support_ops.models import TicketInput

logger = logging.getLogger(__name__)

TEMPLATE_ONLY = True


def _guard_template(dry_run: bool) -> None:
    """Raise unless the caller is in dry_run or has explicitly opted in.

    The opt-in env flag exists so integration tests + the React app's
    'send a sample run' path keep working without spraying half-implemented
    side effects at a real customer."""
    if dry_run:
        return
    if os.environ.get("FORGEFLOW_ALLOW_TEMPLATE_WORKFLOWS") == "1":
        return
    raise RuntimeError(
        "support_ops is a template scaffold — no ticketing connector is wired. "
        "Use dry_run=True for evaluation, or wire a Zendesk/Intercom/Freshdesk "
        "connector and remove TEMPLATE_ONLY in pipeline.py. "
        "See docs/sales-ops-production.md for the reference pattern."
    )


class SupportOpsPipeline:
    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def _build_initial_state(
        self,
        ticket_input: TicketInput,
        user_id: str,
        role: str,
        dry_run: bool = False,
    ) -> WorkflowState:
        workflow_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())

        tags = [
            f"user:{user_id}",
            f"role:{role}",
            "support_ops",
            f"channel:{ticket_input.channel.value}",
        ]
        if dry_run:
            tags.append("dry_run")

        return WorkflowState(
            messages=[],
            research_results=[],
            analysis_scores=[],
            executed_actions=[],
            errors=[],
            workflow_id=workflow_id,
            thread_id=thread_id,
            current_stage="triage",
            next_agent=None,
            lead_id=ticket_input.ticket_id,
            lead_data=ticket_input.model_dump(),
            proposal=None,
            approval_status=None,
            approval_token=None,
            total_tokens=0,
            total_cost_usd=0.0,
            dry_run=dry_run,
            run_metadata={
                "user_id": user_id,
                "role": role,
                "workflow_type": "support_ops",
                "dry_run": dry_run,
                "langsmith_tags": tags,
            },
        )

    async def run(
        self,
        ticket_input: TicketInput,
        user_id: str = "anon",
        role: str = "support_rep",
        dry_run: bool = False,
    ) -> tuple[str, str, WorkflowState]:
        _guard_template(dry_run)
        state = self._build_initial_state(ticket_input, user_id, role, dry_run)
        thread_id = state["thread_id"]

        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"forgeflow/support_ops/{ticket_input.ticket_id}",
            "tags": state["run_metadata"]["langsmith_tags"],
        }

        final_state = await self.graph.ainvoke(state, config=config)
        logger.info(
            "Support workflow complete | ticket=%s | thread=%s | stage=%s",
            ticket_input.ticket_id,
            thread_id,
            final_state.get("current_stage"),
        )
        return state["workflow_id"], thread_id, final_state

    async def stream(
        self,
        ticket_input: TicketInput,
        user_id: str = "anon",
        role: str = "support_rep",
        dry_run: bool = False,
    ) -> AsyncIterator[dict]:
        _guard_template(dry_run)
        state = self._build_initial_state(ticket_input, user_id, role, dry_run)
        thread_id = state["thread_id"]
        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"forgeflow/support_ops/{ticket_input.ticket_id}",
        }

        yield {
            "event": "workflow_started",
            "workflow_id": state["workflow_id"],
            "thread_id": thread_id,
        }

        async for event in self.graph.astream(state, config=config):
            for node_name, state_patch in event.items():
                yield {
                    "event": "node_complete",
                    "node": node_name,
                    "thread_id": thread_id,
                    "patch": {k: v for k, v in state_patch.items() if k != "messages"},
                }

        yield {"event": "workflow_complete", "thread_id": thread_id}

    async def resume(
        self,
        thread_id: str,
        approval_status: str,
        resolved_by: str = "manager",
    ) -> WorkflowState:
        config = {"configurable": {"thread_id": thread_id}}
        update = {"approval_status": approval_status}
        final_state = await self.graph.ainvoke(update, config=config)
        logger.info(
            "Support workflow resumed | thread=%s | approval=%s",
            thread_id,
            approval_status,
        )
        return final_state
