"""ExecutorAgent — takes approved actions: draft proposals, write CRM, send emails.

Two sub-modes:
  1. PROPOSE mode: generate the proposal document + store it
  2. EXECUTE mode: after human approval, send email + update CRM lead status
"""

from __future__ import annotations

import logging
import uuid
from typing import cast

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
    def __init__(
        self,
        model: BaseChatModel,
        tools: list[BaseTool] | None = None,
        system_prompt: str | None = None,
    ) -> None:
        super().__init__(
            name="executor",
            model=model,
            tools=tools or [],
            system_prompt=system_prompt or EXECUTOR_SYSTEM_PROPOSE,
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
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"Draft a proposal for:\n\nCompany: {company}\n"
                f"Qualification Score: {score}/10\n"
                f"Estimated Deal Value: ${deal_value:,}\n"
                f"Research: {research_summary[:1500]}\n\n"
                f"Generate a compelling proposal."
            ),
        ]

        proposal = cast(ProposalContent, await self._proposal_model.ainvoke(prompt))

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
        dry_run = bool(state.get("dry_run"))
        workflow_id = state.get("workflow_id", "")

        actions: list[str] = []

        # Cap deal value — LLM-controlled "estimated_deal_value_usd" can be
        # nudged through prompt injection. Workspace-level override lives in
        # workspaces.settings.max_deal_value_usd; we fall back to $1M.
        ws_settings = state.get("workspace_settings") or {}
        max_deal = float(ws_settings.get("max_deal_value_usd", 1_000_000))
        dv = proposal.get("estimated_deal_value_usd")
        if isinstance(dv, (int, float)) and dv > max_deal:
            logger.warning("Capping deal_value | requested=%s cap=%s", dv, max_deal)
            proposal["estimated_deal_value_usd"] = max_deal

        allowed_domains = list(ws_settings.get("email_allowed_domains") or [])

        if dry_run:
            actions = ["crm_updated_dry_run", "email_sent_dry_run"]
            logger.info("Executor DRY-RUN — skipped CRM + email side effects for %s", company)
        else:
            actions.extend(await self._sync_to_crm(state, lead_data, proposal, company, workflow_id))
            actions.extend(
                await self._send_proposal_email(
                    lead_data, proposal, company, allowed_domains=allowed_domains
                )
            )
            if not actions:
                # Last-resort: nothing was configured. Mark as mock so audit is honest.
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

    async def _sync_to_crm(
        self,
        state: WorkflowState,
        lead_data: dict,
        proposal: dict,
        company: str,
        workflow_id: str,
    ) -> list[str]:
        """Sync the lead + deal to a real CRM when configured; mock otherwise.

        Detection order:
          1. HubSpot — if HUBSPOT_ACCESS_TOKEN is set, call hubspot_upsert_contact
             + hubspot_upsert_company + hubspot_create_deal_idempotent. Idempotent
             on email + domain + workflow_id, so retried workflows don't dupe.
          2. update_lead tool — generic mock CRM via MCP for demo flows.
          3. Nothing — return empty (caller marks as mock).
        """
        from forgeflow.config import get_settings

        actions: list[str] = []
        settings = get_settings()
        # SecretStr is always present; the value can be empty string (no token).
        hubspot_token = settings.hubspot_access_token.get_secret_value()

        if hubspot_token:
            # Real CRM path. Each step is wrapped so a partial failure still
            # records what succeeded — audit log + downstream retry both benefit.
            email = lead_data.get("contact_email") or f"contact@{_safe_domain(company)}"
            domain = lead_data.get("domain") or _safe_domain(company)
            deal_value = float(proposal.get("estimated_deal_value_usd") or 0)

            # FastMCP mounts tools as "{prefix}_{function_name}", so the
            # registered names are hubspot_hubspot_upsert_contact etc.
            upsert_contact = self._tool_map.get("hubspot_hubspot_upsert_contact")
            upsert_company = self._tool_map.get("hubspot_hubspot_upsert_company")
            create_deal = self._tool_map.get("hubspot_hubspot_create_deal_idempotent")
            add_note = self._tool_map.get("hubspot_hubspot_add_note")

            contact_id: str | None = None
            company_id: str | None = None

            if upsert_contact:
                try:
                    contact = await upsert_contact.ainvoke({
                        "email": email,
                        "firstname": lead_data.get("contact_firstname"),
                        "lastname": lead_data.get("contact_lastname"),
                        "company": company,
                    })
                    contact_id = contact.get("id")
                    actions.append("hubspot_contact_upserted")
                except Exception as e:
                    logger.error("HubSpot contact upsert failed for %s: %s", email, e)
                    actions.append("hubspot_contact_failed")

            if upsert_company:
                try:
                    co = await upsert_company.ainvoke({
                        "name": company,
                        "domain": domain,
                        "industry": lead_data.get("industry"),
                    })
                    company_id = co.get("id")
                    actions.append("hubspot_company_upserted")
                except Exception as e:
                    logger.error("HubSpot company upsert failed for %s: %s", domain, e)
                    actions.append("hubspot_company_failed")

            if create_deal and deal_value > 0:
                try:
                    await create_deal.ainvoke({
                        "run_id": workflow_id,
                        "deal_name": f"{company} — ForgeFlow proposal",
                        "amount": deal_value,
                        "deal_stage": "presentationscheduled",
                        "contact_id": contact_id,
                        "company_id": company_id,
                    })
                    actions.append("hubspot_deal_created")
                except Exception as e:
                    logger.error("HubSpot deal create failed for run %s: %s", workflow_id, e)
                    actions.append("hubspot_deal_failed")

            if add_note and (contact_id or company_id):
                try:
                    await add_note.ainvoke({
                        "body": (
                            f"ForgeFlow run {workflow_id} — proposal drafted.\n\n"
                            f"{proposal.get('executive_summary', '')[:500]}"
                        ),
                        "contact_id": contact_id,
                        "company_id": company_id,
                    })
                    actions.append("hubspot_note_added")
                except Exception as e:
                    logger.error("HubSpot note add failed: %s", e)
            return actions

        # Demo path — generic mock CRM tool via MCP (prefixed by FastMCP)
        crm_tool = self._tool_map.get("crm_update_lead")
        if crm_tool:
            try:
                await crm_tool.ainvoke({
                    "lead_id": state.get("lead_id"),
                    "status": "proposed",
                    "deal_value": proposal.get("estimated_deal_value_usd"),
                })
                actions.append("crm_updated")
            except Exception as e:
                logger.error("Mock CRM update failed: %s", e)
        return actions

    async def _send_proposal_email(
        self,
        lead_data: dict,
        proposal: dict,
        company: str,
        allowed_domains: list[str] | None = None,
    ) -> list[str]:
        """Send the proposal email.

        Recipient is taken from lead_data only — never from LLM output. The
        per-workspace `allowed_domains` allowlist (SECURITY_AUDIT.md C-5)
        defaults to the recipient's own domain when no workspace policy is
        configured, so a misconfigured tenant still can't blast unrelated
        addresses.
        """
        actions: list[str] = []
        email_tool = self._tool_map.get("email_send_email")
        to_address = lead_data.get("contact_email")

        if not to_address:
            logger.warning("Email skipped — no contact_email on lead for %s", company)
            return ["email_skipped_no_address"]

        if not email_tool:
            return actions

        # Default allowlist = the recipient's own domain. Tightens the blast
        # radius even when the tenant hasn't set an explicit allowlist.
        domain = to_address.rsplit("@", 1)[-1] if "@" in to_address else ""
        domains = list(allowed_domains or ([domain] if domain else []))

        try:
            await email_tool.ainvoke({
                "to": to_address,
                "subject": f"ForgeFlow Enterprise AI Proposal — {company}",
                "body": proposal.get("executive_summary", "Please review our proposal."),
                "allowed_domains": domains,
            })
            actions.append("email_sent")
        except Exception as e:
            logger.error("Email send failed: %s", e)
            actions.append("email_failed")
        return actions


def _safe_domain(company: str) -> str:
    """Derive a defensible default domain from a company name.

    Stripped to ascii alphanumerics + lowercased + .com. Used only when the
    caller didn't supply one — should be replaced by real enrichment data in
    production input."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "", company.lower()) or "example"
    return f"{slug}.com"
