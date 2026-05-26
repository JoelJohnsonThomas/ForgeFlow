"""FinanceReconPipeline — orchestration helper for two-ledger reconciliation workflows.

⚠ TEMPLATE SCAFFOLD — NOT PRODUCTION-READY

The graph + stages + models are real, but no bank/ERP connector is wired
into the workflow. forgeflow/connectors/ ships QuickBooks + SAP clients
but neither is hooked up here; you'd also need a bank/processor data
source (Plaid? CSV import? S3 drop?) and a journal-posting tool with
double-entry validation.

Finance also has regulatory edges (immutable audit trail, signed entries,
materiality thresholds per entity, period locks) that demos skip and
production teams cannot. Treat this as a starting point, not a deliverable.

Calling .run() or .stream() raises unless dry_run=True. Set
FORGEFLOW_ALLOW_TEMPLATE_WORKFLOWS=1 to override (e.g. for integration
tests that mock the graph).
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

from forgeflow.state.workflow_state import WorkflowState
from forgeflow.workflows.finance_recon.models import ReconciliationInput

logger = logging.getLogger(__name__)

TEMPLATE_ONLY = True


def _guard_template(dry_run: bool) -> None:
    if dry_run:
        return
    if os.environ.get("FORGEFLOW_ALLOW_TEMPLATE_WORKFLOWS") == "1":
        return
    raise RuntimeError(
        "finance_recon is a template scaffold — no bank/ERP connector is wired "
        "and no journal-posting tool is registered. Use dry_run=True for "
        "evaluation, or wire QuickBooks/SAP and remove TEMPLATE_ONLY in "
        "pipeline.py. See docs/sales-ops-production.md for the reference pattern."
    )


class FinanceReconPipeline:
    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def _build_initial_state(
        self,
        recon_input: ReconciliationInput,
        user_id: str,
        role: str,
        dry_run: bool = False,
    ) -> WorkflowState:
        workflow_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())

        # Serialize dates explicitly — Pydantic .model_dump() returns date objects
        # but downstream JSON encoders need strings.
        recon_data = recon_input.model_dump(mode="json")

        tags = [
            f"user:{user_id}",
            f"role:{role}",
            "finance_recon",
            f"period:{recon_input.period_label}",
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
            current_stage="ingest",
            next_agent=None,
            lead_id=recon_input.period_label,
            lead_data=recon_data,
            proposal=None,
            approval_status=None,
            approval_token=None,
            total_tokens=0,
            total_cost_usd=0.0,
            dry_run=dry_run,
            run_metadata={
                "user_id": user_id,
                "role": role,
                "workflow_type": "finance_recon",
                "dry_run": dry_run,
                "langsmith_tags": tags,
            },
        )

    async def run(
        self,
        recon_input: ReconciliationInput,
        user_id: str = "anon",
        role: str = "accountant",
        dry_run: bool = False,
    ) -> tuple[str, str, WorkflowState]:
        _guard_template(dry_run)
        state = self._build_initial_state(recon_input, user_id, role, dry_run)
        thread_id = state["thread_id"]
        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"forgeflow/finance_recon/{recon_input.period_label}",
            "tags": state["run_metadata"]["langsmith_tags"],
        }

        final_state = await self.graph.ainvoke(state, config=config)
        logger.info(
            "Finance recon complete | period=%s | thread=%s | stage=%s",
            recon_input.period_label,
            thread_id,
            final_state.get("current_stage"),
        )
        return state["workflow_id"], thread_id, final_state

    async def stream(
        self,
        recon_input: ReconciliationInput,
        user_id: str = "anon",
        role: str = "accountant",
        dry_run: bool = False,
    ) -> AsyncIterator[dict]:
        _guard_template(dry_run)
        state = self._build_initial_state(recon_input, user_id, role, dry_run)
        thread_id = state["thread_id"]
        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"forgeflow/finance_recon/{recon_input.period_label}",
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
        resolved_by: str = "controller",
    ) -> WorkflowState:
        config = {"configurable": {"thread_id": thread_id}}
        update = {"approval_status": approval_status}
        final_state = await self.graph.ainvoke(update, config=config)
        logger.info(
            "Finance recon resumed | thread=%s | approval=%s",
            thread_id,
            approval_status,
        )
        return final_state
