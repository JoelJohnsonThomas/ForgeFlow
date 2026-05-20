"""SupportOpsPipeline — orchestration helper for support ticket workflows."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from forgeflow.state.workflow_state import WorkflowState
from forgeflow.workflows.support_ops.models import TicketInput

logger = logging.getLogger(__name__)


class SupportOpsPipeline:
    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def _build_initial_state(
        self, ticket_input: TicketInput, user_id: str, role: str
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
            current_stage="triage",
            next_agent=None,
            lead_id=ticket_input.ticket_id,
            lead_data=ticket_input.model_dump(),
            proposal=None,
            approval_status=None,
            approval_token=None,
            total_tokens=0,
            total_cost_usd=0.0,
            run_metadata={
                "user_id": user_id,
                "role": role,
                "workflow_type": "support_ops",
                "langsmith_tags": [
                    f"user:{user_id}",
                    f"role:{role}",
                    "support_ops",
                    f"channel:{ticket_input.channel.value}",
                ],
            },
        )

    async def run(
        self, ticket_input: TicketInput, user_id: str = "anon", role: str = "support_rep"
    ) -> tuple[str, str, WorkflowState]:
        state = self._build_initial_state(ticket_input, user_id, role)
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
        self, ticket_input: TicketInput, user_id: str = "anon", role: str = "support_rep"
    ) -> AsyncIterator[dict]:
        state = self._build_initial_state(ticket_input, user_id, role)
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
