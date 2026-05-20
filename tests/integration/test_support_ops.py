"""Integration tests for the support ops pipeline (mock LLM)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.workflows.support_ops.models import TicketChannel, TicketInput
from forgeflow.workflows.support_ops.pipeline import SupportOpsPipeline


@pytest.fixture
def mock_graph():
    graph = MagicMock()
    final_state = {
        "workflow_id": "support-wf-1",
        "thread_id": "support-thread-1",
        "current_stage": "done",
        "next_agent": None,
        "lead_id": "TICKET-42",
        "lead_data": {
            "ticket_id": "TICKET-42",
            "customer_name": "Acme Inc",
            "subject": "Login fails",
            "body": "Cannot sign in.",
            "channel": "email",
        },
        "analysis_scores": [{"severity": 3, "category": "bug", "customer_sentiment": "frustrated"}],
        "research_results": [{"summary": "Customer is on enterprise tier"}],
        "executed_actions": ["reply_drafted"],
        "errors": [],
        "messages": [],
        "proposal": None,
        "approval_status": None,
        "approval_token": None,
        "total_tokens": 800,
        "total_cost_usd": 0.012,
        "run_metadata": {"workflow_type": "support_ops"},
    }
    graph.ainvoke = AsyncMock(return_value=final_state)

    async def mock_astream(*args, **kwargs):
        yield {"supervisor": {"next_agent": "researcher"}}
        yield {"researcher": {"research_results": [{"summary": "Enterprise tier"}]}}
        yield {"analyzer": {"analysis_scores": [{"severity": 3}]}}
        yield {"executor": {"executed_actions": ["reply_drafted"]}}

    graph.astream = mock_astream
    return graph


@pytest.fixture
def sample_ticket():
    return TicketInput(
        ticket_id="TICKET-42",
        customer_name="Acme Inc",
        customer_email="ops@acme.example",
        subject="Login fails after password reset",
        body="After resetting my password I cannot sign in. Browser says 'invalid token'.",
        channel=TicketChannel.EMAIL,
        product="ForgeFlow Cloud",
        customer_tier="enterprise",
        previous_ticket_count=2,
    )


class TestSupportOpsPipeline:
    @pytest.mark.asyncio
    async def test_run_returns_ids_and_final_state(self, mock_graph, sample_ticket):
        pipeline = SupportOpsPipeline(graph=mock_graph)
        wf_id, thread_id, final_state = await pipeline.run(
            sample_ticket, user_id="agent-7", role="support_rep"
        )

        assert wf_id
        assert thread_id
        assert final_state["total_cost_usd"] == 0.012
        assert final_state["current_stage"] == "done"

    @pytest.mark.asyncio
    async def test_run_tags_with_workflow_type(self, mock_graph, sample_ticket):
        pipeline = SupportOpsPipeline(graph=mock_graph)
        await pipeline.run(sample_ticket)

        mock_graph.ainvoke.assert_called_once()
        config = mock_graph.ainvoke.call_args[1]["config"]
        assert "support_ops" in config["tags"]
        assert config["run_name"].startswith("forgeflow/support_ops/")

    @pytest.mark.asyncio
    async def test_run_initial_state_has_ticket_data(self, mock_graph, sample_ticket):
        pipeline = SupportOpsPipeline(graph=mock_graph)
        await pipeline.run(sample_ticket)

        initial_state = mock_graph.ainvoke.call_args[0][0]
        assert initial_state["current_stage"] == "triage"
        assert initial_state["lead_id"] == "TICKET-42"
        assert initial_state["lead_data"]["customer_tier"] == "enterprise"
        assert initial_state["run_metadata"]["workflow_type"] == "support_ops"

    @pytest.mark.asyncio
    async def test_stream_yields_events(self, mock_graph, sample_ticket):
        pipeline = SupportOpsPipeline(graph=mock_graph)
        events = []
        async for event in pipeline.stream(sample_ticket):
            events.append(event)

        types = [e.get("event") for e in events]
        assert "workflow_started" in types
        assert "workflow_complete" in types
        assert "node_complete" in types

    @pytest.mark.asyncio
    async def test_resume_with_approval(self, mock_graph):
        pipeline = SupportOpsPipeline(graph=mock_graph)
        await pipeline.resume(thread_id="t-1", approval_status="approved")

        update = mock_graph.ainvoke.call_args[0][0]
        assert update["approval_status"] == "approved"
