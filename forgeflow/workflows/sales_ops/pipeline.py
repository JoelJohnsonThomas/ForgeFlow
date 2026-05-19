"""SalesOpsPipeline — orchestration helper that wraps the LangGraph invocation.

Provides a clean interface for the FastAPI layer:
  run()    — start a new workflow run (async, non-streaming)
  stream() — start a new workflow run (async generator, SSE-ready)
  resume() — resume an interrupted workflow after human approval
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, AsyncIterator

from forgeflow.state.workflow_state import WorkflowState
from forgeflow.workflows.sales_ops.models import LeadInput

logger = logging.getLogger(__name__)


class SalesOpsPipeline:
    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def _build_initial_state(
        self, lead_input: LeadInput, user_id: str, role: str
    ) -> WorkflowState:
        workflow_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())

        return WorkflowState(
            messages=[],
            research_results=[],
            analysis_scores=[],
            executed_actions=[],
            errors=[],
            workflow_id=workflow_id,
            thread_id=thread_id,
            current_stage="qualify",
            next_agent=None,
            lead_id=None,
            lead_data=lead_input.model_dump(),
            proposal=None,
            approval_status=None,
            approval_token=None,
            total_tokens=0,
            total_cost_usd=0.0,
            run_metadata={
                "user_id": user_id,
                "role": role,
                "langsmith_tags": [f"user:{user_id}", f"role:{role}", "sales_ops"],
            },
        )

    async def run(
        self, lead_input: LeadInput, user_id: str = "anon", role: str = "sales_rep"
    ) -> tuple[str, str, WorkflowState]:
        """Run workflow to completion (or first interrupt). Returns (run_id, thread_id, final_state)."""
        state = self._build_initial_state(lead_input, user_id, role)
        thread_id = state["thread_id"]

        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"forgeflow/sales_ops/{lead_input.company_name}",
            "tags": state["run_metadata"]["langsmith_tags"],
        }

        final_state = await self.graph.ainvoke(state, config=config)
        logger.info(
            "Workflow complete | thread=%s | stage=%s",
            thread_id,
            final_state.get("current_stage"),
        )
        return state["workflow_id"], thread_id, final_state

    async def stream(
        self, lead_input: LeadInput, user_id: str = "anon", role: str = "sales_rep"
    ) -> AsyncIterator[dict]:
        """Stream workflow events — yields {node, patch} dicts for SSE."""
        state = self._build_initial_state(lead_input, user_id, role)
        thread_id = state["thread_id"]

        config = {
            "configurable": {"thread_id": thread_id},
            "run_name": f"forgeflow/sales_ops/{lead_input.company_name}",
        }

        yield {"event": "workflow_started", "workflow_id": state["workflow_id"], "thread_id": thread_id}

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
        """Resume a suspended workflow after human approval/rejection."""
        config = {"configurable": {"thread_id": thread_id}}

        # Inject the approval decision into state
        update = {"approval_status": approval_status}
        final_state = await self.graph.ainvoke(update, config=config)

        logger.info(
            "Workflow resumed | thread=%s | approval=%s | stage=%s",
            thread_id,
            approval_status,
            final_state.get("current_stage"),
        )
        return final_state
