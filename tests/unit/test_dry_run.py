"""Tests for the dry-run flag on the executor's side-effecting path."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.language_models import BaseChatModel

from forgeflow.agents.executor import ExecutorAgent


def _fake_model() -> BaseChatModel:
    llm = MagicMock(spec=BaseChatModel)
    llm.bind_tools = MagicMock(return_value=llm)
    llm.with_structured_output = MagicMock(return_value=llm)
    return llm


def _fake_tool(name: str):
    tool = MagicMock()
    tool.name = name
    tool.ainvoke = AsyncMock(return_value={"ok": True})
    return tool


class TestExecutorDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_skips_crm_and_email_calls(self):
        # Tool names match what FastMCP exposes after .mount(prefix=...).
        crm = _fake_tool("crm_update_lead")
        email = _fake_tool("email_send_email")

        executor = ExecutorAgent(model=_fake_model(), tools=[crm, email])

        state = {
            "lead_data": {"company_name": "Acme", "contact_email": "a@acme.example"},
            "proposal": {"executive_summary": "Hello", "estimated_deal_value_usd": 50_000},
            "lead_id": "lead-1",
            "dry_run": True,
            "current_stage": "execute",
            "approval_status": "approved",
        }

        result = await executor._execute_approved(state)

        # Tools were NOT called
        crm.ainvoke.assert_not_called()
        email.ainvoke.assert_not_called()

        # Actions reflect dry-run
        assert "crm_updated_dry_run" in result["executed_actions"]
        assert "email_sent_dry_run" in result["executed_actions"]
        assert result["current_stage"] == "done"

    @pytest.mark.asyncio
    async def test_normal_run_invokes_tools(self):
        crm = _fake_tool("crm_update_lead")
        email = _fake_tool("email_send_email")

        executor = ExecutorAgent(model=_fake_model(), tools=[crm, email])

        state = {
            "lead_data": {"company_name": "Acme", "contact_email": "a@acme.example"},
            "proposal": {"executive_summary": "Hello", "estimated_deal_value_usd": 50_000},
            "lead_id": "lead-1",
            "dry_run": False,
            "current_stage": "execute",
            "approval_status": "approved",
        }

        result = await executor._execute_approved(state)

        crm.ainvoke.assert_called_once()
        email.ainvoke.assert_called_once()
        assert "crm_updated" in result["executed_actions"]
        assert "email_sent" in result["executed_actions"]

    @pytest.mark.asyncio
    async def test_dry_run_default_is_false(self):
        """A state with no dry_run key still hits the real tool path."""
        crm = _fake_tool("crm_update_lead")
        email = _fake_tool("email_send_email")

        executor = ExecutorAgent(model=_fake_model(), tools=[crm, email])

        # contact_email is required for the email path now — the old "synthesize
        # contact@<slug>.com" fallback was a footgun in production.
        state = {
            "lead_data": {"company_name": "Acme", "contact_email": "ops@acme.example"},
            "proposal": {"executive_summary": "x", "estimated_deal_value_usd": 1},
            "lead_id": "lead-1",
            "current_stage": "execute",
            "approval_status": "approved",
        }
        await executor._execute_approved(state)

        crm.ainvoke.assert_called_once()
        email.ainvoke.assert_called_once()


class TestPipelineDryRunFlag:
    @pytest.mark.asyncio
    async def test_sales_ops_initial_state_carries_dry_run(self):
        from forgeflow.workflows.sales_ops.models import LeadInput
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            return_value={
                "current_stage": "done",
                "total_tokens": 0,
                "total_cost_usd": 0.0,
            }
        )
        pipeline = SalesOpsPipeline(graph=graph)
        await pipeline.run(LeadInput(company_name="X"), dry_run=True)

        initial_state = graph.ainvoke.call_args[0][0]
        assert initial_state["dry_run"] is True
        assert "dry_run" in initial_state["run_metadata"]["langsmith_tags"]
