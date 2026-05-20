"""Integration tests for the full sales ops pipeline (mock LLM)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.workflows.sales_ops.models import LeadInput


@pytest.fixture
def mock_graph():
    graph = MagicMock()
    final_state = {
        "workflow_id": "test-workflow-123",
        "thread_id": "test-thread-456",
        "current_stage": "done",
        "next_agent": None,
        "lead_data": {"company_name": "Stripe"},
        "analysis_scores": [{"score": 8.5, "qualified": True}],
        "research_results": [{"source": "web_search", "content": "Stripe raised $600M"}],
        "executed_actions": ["draft_proposal"],
        "errors": [],
        "messages": [],
        "proposal": {"content": "Proposal for Stripe", "pricing": "$50,000"},
        "approval_status": None,
        "approval_token": None,
        "total_tokens": 1500,
        "total_cost_usd": 0.035,
        "run_metadata": {"user_id": "test-user", "role": "sales_rep"},
        "lead_id": None,
    }
    graph.ainvoke = AsyncMock(return_value=final_state)

    async def mock_astream(*args, **kwargs):
        yield {"supervisor": {"next_agent": "researcher"}}
        yield {"researcher": {"research_results": [{"content": "Stripe data"}]}}
        yield {"analyzer": {"analysis_scores": [{"score": 8.5}]}}
        yield {"executor": {"proposal": {"content": "Test proposal"}}}

    graph.astream = mock_astream
    return graph


class TestSalesOpsPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_run_returns_ids_and_state(self, mock_graph):
        """run() should return (workflow_id, thread_id, final_state)."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        lead = LeadInput(company_name="Stripe", industry="fintech")
        workflow_id, thread_id, final_state = await pipeline.run(
            lead_input=lead,
            user_id="test-user",
            role="sales_rep",
        )

        assert workflow_id
        assert thread_id
        assert final_state["total_cost_usd"] == 0.035
        assert final_state["current_stage"] == "done"

    @pytest.mark.asyncio
    async def test_pipeline_run_invokes_graph_with_config(self, mock_graph):
        """Graph should be invoked with a configurable thread_id."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        lead = LeadInput(company_name="Snowflake")
        await pipeline.run(lead_input=lead)

        mock_graph.ainvoke.assert_called_once()
        call_kwargs = mock_graph.ainvoke.call_args[1]
        assert "config" in call_kwargs
        assert "thread_id" in call_kwargs["config"]["configurable"]

    @pytest.mark.asyncio
    async def test_pipeline_stream_yields_events(self, mock_graph):
        """stream() should yield workflow_started, node_complete, and workflow_complete events."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        lead = LeadInput(company_name="Stripe")
        events = []
        async for event in pipeline.stream(lead_input=lead, user_id="test-user"):
            events.append(event)

        assert len(events) >= 3  # started + at least one node + complete
        event_types = [e.get("event") for e in events]
        assert "workflow_started" in event_types
        assert "workflow_complete" in event_types
        assert "node_complete" in event_types

    @pytest.mark.asyncio
    async def test_pipeline_resume_approved(self, mock_graph):
        """resume() with 'approved' should invoke graph with approval_status in update."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        await pipeline.resume(thread_id="thread-001", approval_status="approved")

        mock_graph.ainvoke.assert_called_once()
        state_update = mock_graph.ainvoke.call_args[0][0]
        assert state_update["approval_status"] == "approved"

    @pytest.mark.asyncio
    async def test_pipeline_resume_rejected(self, mock_graph):
        """resume() with 'rejected' should propagate rejection status."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        await pipeline.resume(thread_id="thread-002", approval_status="rejected")

        state_update = mock_graph.ainvoke.call_args[0][0]
        assert state_update["approval_status"] == "rejected"
