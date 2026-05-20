"""Integration tests for the finance reconciliation pipeline (mock LLM)."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.workflows.finance_recon.models import LedgerSource, ReconciliationInput
from forgeflow.workflows.finance_recon.pipeline import FinanceReconPipeline


@pytest.fixture
def mock_graph():
    graph = MagicMock()
    final_state = {
        "workflow_id": "recon-wf-1",
        "thread_id": "recon-thread-1",
        "current_stage": "done",
        "next_agent": None,
        "lead_id": "2026-04",
        "lead_data": {
            "period_label": "2026-04",
            "source_a": "bank",
            "source_b": "erp",
        },
        "analysis_scores": [{"matched_count": 142, "unmatched_count": 3}],
        "research_results": [{"source_a_entries": 145, "source_b_entries": 142}],
        "executed_actions": ["journal_entries_posted"],
        "errors": [],
        "messages": [],
        "proposal": None,
        "approval_status": None,
        "approval_token": None,
        "total_tokens": 1200,
        "total_cost_usd": 0.018,
        "run_metadata": {"workflow_type": "finance_recon"},
    }
    graph.ainvoke = AsyncMock(return_value=final_state)

    async def mock_astream(*args, **kwargs):
        yield {"supervisor": {"next_agent": "researcher"}}
        yield {"researcher": {"research_results": [{"source_a_entries": 145}]}}
        yield {"analyzer": {"analysis_scores": [{"matched_count": 142}]}}
        yield {"executor": {"executed_actions": ["journal_entries_posted"]}}

    graph.astream = mock_astream
    return graph


@pytest.fixture
def sample_recon():
    return ReconciliationInput(
        period_label="2026-04",
        source_a=LedgerSource.BANK,
        source_b=LedgerSource.ERP,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        materiality_threshold_usd=100.0,
        entity="ACME US LLC",
    )


class TestFinanceReconPipeline:
    @pytest.mark.asyncio
    async def test_run_returns_ids_and_final_state(self, mock_graph, sample_recon):
        pipeline = FinanceReconPipeline(graph=mock_graph)
        wf_id, thread_id, final_state = await pipeline.run(
            sample_recon, user_id="ctrl-3", role="controller"
        )

        assert wf_id
        assert thread_id
        assert final_state["total_cost_usd"] == 0.018
        assert final_state["current_stage"] == "done"

    @pytest.mark.asyncio
    async def test_run_tags_with_workflow_type(self, mock_graph, sample_recon):
        pipeline = FinanceReconPipeline(graph=mock_graph)
        await pipeline.run(sample_recon)

        config = mock_graph.ainvoke.call_args[1]["config"]
        assert "finance_recon" in config["tags"]
        assert config["run_name"].startswith("forgeflow/finance_recon/")

    @pytest.mark.asyncio
    async def test_run_initial_state_serializes_dates(self, mock_graph, sample_recon):
        """Dates must be JSON-serializable strings in lead_data so checkpointing works."""
        pipeline = FinanceReconPipeline(graph=mock_graph)
        await pipeline.run(sample_recon)

        initial_state = mock_graph.ainvoke.call_args[0][0]
        assert initial_state["current_stage"] == "ingest"
        # mode='json' should turn date into ISO string, not date object
        assert isinstance(initial_state["lead_data"]["period_start"], str)
        assert initial_state["lead_data"]["period_start"] == "2026-04-01"

    @pytest.mark.asyncio
    async def test_stream_yields_events(self, mock_graph, sample_recon):
        pipeline = FinanceReconPipeline(graph=mock_graph)
        events = []
        async for event in pipeline.stream(sample_recon):
            events.append(event)

        types = [e.get("event") for e in events]
        assert "workflow_started" in types
        assert "workflow_complete" in types

    @pytest.mark.asyncio
    async def test_resume_with_rejection(self, mock_graph):
        pipeline = FinanceReconPipeline(graph=mock_graph)
        await pipeline.resume(thread_id="t-1", approval_status="rejected")

        update = mock_graph.ainvoke.call_args[0][0]
        assert update["approval_status"] == "rejected"
