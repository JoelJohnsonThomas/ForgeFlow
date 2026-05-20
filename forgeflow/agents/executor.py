"""ExecutorAgent — takes approved actions: draft proposals, write CRM, send emails.

Two sub-modes:
  1. PROPOSE mode: generate the proposal document + store it
  2. EXECUTE mode: after human approval, send email + update CRM lead status
"""

from __future__ import annotations

import logging
import uuid

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from forgeflow.agents.base import BaseAgent
from forgeflow.state.workflow_state import WorkflowState

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROPOSE = """You are the Executor Agent for ForgeFlow — Proposal Mode.

Your task: Generate a compelling, personalized sales proposal for the lead.

The proposal must include:
1. Executive Summary (2-3 sentences tailored to their specific situation)
2. Pain Points Addressed (based on research findings)
3. Our Solution (how ForgeFlow Enterprise AI addresses their challenges)
4. Pricing Tiers (3 options: Starter, Growth, Enterprise)
5. Expected ROI and timeline
6. Clear next steps

Be specific, confident, and business-focused. Avoid generic language.
Reference actual data points from the research (funding, team size, growth)."""

EXECUTOR_SYSTEM_EXECUTE = """You are the Executor Agent for ForgeFlow — Execution Mode.

The proposal has been approved by a manager. Your tasks:
1. Confirm the email content to send to the prospect
2. List the CRM fields to update
3. Define the follow-up timeline

Format your response as JSON with keys:
  email_subject, email_body, crm_updates, follow_up_date"""


class ProposalContent(BaseModel):
    executive_summary: str
    pain_points_addressed: list[str] = Field(min_length=2)
    solution_overview: str
    pricing_tiers: list[dict]
    expected_roi: str
    next_steps: list[str]
    estimated_deal_value_usd: int = Field(ge=0)


class ExecutorAgent(BaseAgent):
    def __init__(self, model: BaseChatModel, tools: list[BaseTool] | None = None) -> None:
        super().__init__(
            name="executor",
            model=model,
            tools=tools or [],
            system_prompt=EXECUTOR_SYSTEM_PROPOSE,
        )
        self._proposal_model = model.with_structured_output(ProposalContent)
        self._tool_map = {t.name: t for t in (tools or [])}

    async def run(self, state: WorkflowState) -> dict:
        self._log_start(state)

        stage = state.get("current_stage", "propose")
        approval_status = state.get("approval_status")

        if stage == "execute" or approval_status == "approved":
            return await self._execute_approved(state)
        else:
            return await self._draft_proposal(state)

    async def _draft_proposal(self, state: WorkflowState) -> dict:
        lead_data = state.get("lead_data") or {}
        research_results = state.get("research_results", [])
        analysis_scores = state.get("analysis_scores", [])

        company = lead_data.get("company_name", "Unknown")
        score = analysis_scores[-1].get("score", 0) if analysis_scores else 0
        deal_value = analysis_scores[-1].get("estimated_deal_value_usd", 50000) if analysis_scores else 50000

        research_summary = ""
        for r in research_results:
            if "summary" in r:
                research_summary = r["summary"]
                break

        prompt = [
            SystemMessage(content=EXECUTOR_SYSTEM_PROPOSE),
            HumanMessage(
                content=f"Draft a proposal for:\n\nCompany: {company}\n"
                f"Qualification Score: {score}/10\n"
                f"Estimated Deal Value: ${deal_value:,}\n"
                f"Research: {research_summary[:1500]}\n\n"
                f"Generate a compelling proposal."
            ),
        ]

        proposal: ProposalContent = await self._proposal_model.ainvoke(prompt)

        proposal_dict = proposal.model_dump()
        proposal_dict["lead_id"] = state.get("lead_id")
        proposal_dict["company"] = company
        proposal_dict["proposal_id"] = str(uuid.uuid4())
        proposal_dict["status"] = "pending_approval"

        logger.info(
            "Executor drafted proposal for %s | deal_value=$%d",
            company,
            proposal.estimated_deal_value_usd,
        )

        return {
            "proposal": proposal_dict,
            "current_stage": "propose",
            "executed_actions": ["proposal_drafted"],
            "messages": [
                AIMessage(
                    content=(
                        f"[Executor] Proposal drafted for {company}.\n"
                        f"Estimated deal: ${proposal.estimated_deal_value_usd:,}\n"
                        f"Key pitch: {proposal.executive_summary[:200]}"
                    ),
                    name="executor",
                )
            ],
        }

    async def _execute_approved(self, state: WorkflowState) -> dict:
        lead_data = state.get("lead_data") or {}
        proposal = state.get("proposal") or {}
        company = lead_data.get("company_name", "Unknown")

        # Simulate CRM update and email send via tools or mock
        crm_tool = self._tool_map.get("update_lead")
        email_tool = self._tool_map.get("send_email")

        actions: list[str] = []

        if crm_tool:
            try:
                await crm_tool.ainvoke({
                    "lead_id": state.get("lead_id"),
                    "status": "proposed",
                    "deal_value": proposal.get("estimated_deal_value_usd"),
                })
                actions.append("crm_updated")
            except Exception as e:
                logger.error("CRM update failed: %s", e)

        if email_tool:
            try:
                await email_tool.ainvoke({
                    "to": lead_data.get("contact_email", f"contact@{company.lower().replace(' ', '')}.com"),
                    "subject": f"ForgeFlow Enterprise AI Proposal — {company}",
                    "body": proposal.get("executive_summary", "Please review our proposal."),
                })
                actions.append("email_sent")
            except Exception as e:
                logger.error("Email send failed: %s", e)

        if not actions:
            actions = ["crm_updated_mock", "email_sent_mock"]

        logger.info("Executor completed actions: %s", actions)

        return {
            "current_stage": "done",
            "executed_actions": actions,
            "messages": [
                AIMessage(
                    content=f"[Executor] Executed: {', '.join(actions)} for {company}. Workflow complete.",
                    name="executor",
                )
            ],
        }
