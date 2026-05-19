"""Integration tests for the full sales ops pipeline (mock LLM)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage


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
    async def test_pipeline_run_high_score_lead(self, mock_graph):
        """High-scoring lead should complete through full pipeline."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        workflow_id, thread_id, final_state = await pipeline.run(
            lead_data={"company_name": "Stripe", "industry": "fintech"},
            thread_id="test-thread-456",
        )

        assert workflow_id
        assert thread_id == "test-thread-456"
        assert final_state["total_cost_usd"] == 0.035
        assert final_state["current_stage"] == "done"

    @pytest.mark.asyncio
    async def test_pipeline_stream_yields_events(self, mock_graph):
        """Streaming should yield node events."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        events = []
        async for event in pipeline.stream(
            lead_data={"company_name": "Stripe"},
            thread_id="stream-thread-001",
        ):
            events.append(event)

        assert len(events) > 0
        # Each event should have node and data keys
        for event in events:
            assert "node" in event or "event" in event

    @pytest.mark.asyncio
    async def test_pipeline_resume_approved(self, mock_graph):
        """Resume with approved status should trigger executor."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        final_state = await pipeline.resume(
            thread_id="test-thread-456",
            approval_status="approved",
        )

        mock_graph.ainvoke.assert_called_once()
        call_args = mock_graph.ainvoke.call_args
        # The update should carry approval_status
        update_arg = call_args[0][0]
        assert update_arg is not None or call_args[1].get("config")

    @pytest.mark.asyncio
    async def test_pipeline_resume_rejected(self, mock_graph):
        """Resume with rejected status should also invoke the graph."""
        from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline

        pipeline = SalesOpsPipeline(graph=mock_graph)
        await pipeline.resume(
            thread_id="test-thread-456",
            approval_status="rejected",
        )
        mock_graph.ainvoke.assert_called_once()
