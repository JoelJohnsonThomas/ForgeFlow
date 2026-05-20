"""SupervisorAgent — routes workflow to the correct worker using structured LLM output.

The supervisor never calls tools directly. It reads the current stage + message
history and emits a RoutingDecision that the conditional edge uses to pick the
next node. This keeps routing logic deterministic and auditable.
"""

from __future__ import annotations

import logging
from typing import Literal, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from forgeflow.agents.base import BaseAgent
from forgeflow.state.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM = """You are the Supervisor Agent for ForgeFlow, a sales operations AI system.

Your job is to coordinate a team of specialist agents to process sales leads:
- researcher: Gathers web data about a company (funding, size, market)
- analyzer: Scores the lead (0-10), flags risks, determines ICP fit
- executor: Drafts proposals, writes to CRM, sends emails
- human_approval: Pauses for a human manager to review the proposal

Workflow stages:
1. qualify   → route to researcher (gather company intelligence)
2. research  → route to analyzer (score the lead)
3. analyze   → if score >= 4.0: route to executor (draft proposal); else FINISH (disqualified)
4. propose   → route to human_approval (await manager review)
5. approve   → route to executor (send proposal, update CRM)
6. done      → FINISH

Route to FINISH only when the workflow is complete or the lead is disqualified.
Always include a brief reasoning for your routing decision."""

WORKERS = Literal["researcher", "analyzer", "executor", "human_approval", "FINISH"]


class RoutingDecision(BaseModel):
    next: WORKERS
    reasoning: str


class SupervisorAgent(BaseAgent):
    def __init__(self, model: BaseChatModel) -> None:
        super().__init__(name="supervisor", model=model, tools=[], system_prompt=SUPERVISOR_SYSTEM)
        # Supervisor uses structured output — no tool binding needed
        self._structured_model = model.with_structured_output(RoutingDecision)

    async def run(self, state: WorkflowState) -> dict:
        self._log_start(state)

        stage = state.get("current_stage", "qualify")
        errors = state.get("errors", [])
        analysis = state.get("analysis_scores", [])

        # Build context summary for routing
        context_parts = [f"Current stage: {stage}"]

        if analysis:
            latest = analysis[-1]
            score = latest.get("score", 0)
            context_parts.append(f"Qualification score: {score}/10")
            if score < 4.0:
                context_parts.append("Lead scored below threshold — consider FINISH (disqualified)")

        if errors:
            context_parts.append(f"Recent errors: {errors[-1]}")

        approval = state.get("approval_status")
        if approval:
            context_parts.append(f"Approval status: {approval}")

        context = "\n".join(context_parts)

        prompt = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nWhat is the next routing decision?"),
        ]

        decision = cast(RoutingDecision, await self._structured_model.ainvoke(prompt))

        logger.info(
            "Supervisor routing: %s → %s | reason: %s",
            stage,
            decision.next,
            decision.reasoning,
        )

        # Determine next stage name for state
        stage_map = {
            "researcher": "research",
            "analyzer": "analyze",
            "executor": "propose" if stage in ("analyze", "research") else "execute",
            "human_approval": "approve",
            "FINISH": "done",
        }
        next_stage = stage_map.get(decision.next, stage)

        return {
            "next_agent": decision.next,
            "current_stage": next_stage,
            "messages": [
                AIMessage(
                    content=f"[Supervisor] Routing to {decision.next}: {decision.reasoning}",
                    name="supervisor",
                )
            ],
        }
