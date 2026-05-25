"""Tests for the event dispatcher + Redis consumer parsing path.

The actual Redis/Kafka client integration is mocked — we own the
dispatcher contract; the consumers are thin glue around that.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.events.dispatcher import EventDispatcher, WorkflowTrigger

# --------------------------------------------------------------------------
# parse_event
# --------------------------------------------------------------------------

class TestParseEvent:
    def test_minimal_sales_ops(self):
        trigger = EventDispatcher.parse_event(
            {
                "workflow_type": "sales_ops",
                "lead_data": {"company_name": "Acme"},
            }
        )
        assert isinstance(trigger, WorkflowTrigger)
        assert trigger.workflow_type == "sales_ops"
        assert trigger.payload == {"company_name": "Acme"}
        assert trigger.user_id == "events"      # default
        assert trigger.role == "system"
        assert trigger.dry_run is False

    def test_carries_user_role_dry_run(self):
        trigger = EventDispatcher.parse_event(
            {
                "workflow_type": "support_ops",
                "lead_data": {"ticket_id": "T-1", "customer_name": "X", "subject": "y", "body": "z"},
                "user_id": "alice",
                "role": "support_rep",
                "dry_run": True,
            },
            source_event_id="1700000000-0",
        )
        assert trigger.user_id == "alice"
        assert trigger.role == "support_rep"
        assert trigger.dry_run is True
        assert trigger.source_event_id == "1700000000-0"

    def test_accepts_payload_alias_for_lead_data(self):
        trigger = EventDispatcher.parse_event(
            {"workflow_type": "sales_ops", "payload": {"company_name": "X"}}
        )
        assert trigger.payload == {"company_name": "X"}

    def test_extra_fields_captured(self):
        trigger = EventDispatcher.parse_event(
            {
                "workflow_type": "sales_ops",
                "lead_data": {"company_name": "X"},
                "trace_id": "trace-abc",
                "source_system": "salesforce",
            }
        )
        assert trigger.extra == {"trace_id": "trace-abc", "source_system": "salesforce"}

    def test_rejects_unknown_workflow_type(self):
        with pytest.raises(ValueError, match="unknown workflow_type"):
            EventDispatcher.parse_event(
                {"workflow_type": "marketing_ops", "lead_data": {}}
            )

    def test_rejects_missing_payload(self):
        with pytest.raises(ValueError, match="missing 'lead_data'"):
            EventDispatcher.parse_event({"workflow_type": "sales_ops"})

    def test_rejects_non_object_event(self):
        with pytest.raises(ValueError, match="must be a JSON object"):
            EventDispatcher.parse_event("not a dict")  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------

class TestDispatch:
    @pytest.mark.asyncio
    async def test_unknown_workflow_type_returns_error(self):
        d = EventDispatcher(graphs={})
        trigger = WorkflowTrigger(workflow_type="sales_ops", payload={"company_name": "X"})
        result = await d.dispatch(trigger)
        assert result.ok is False
        assert "no graph for sales_ops" in result.error

    @pytest.mark.asyncio
    async def test_invalid_payload_returns_structured_error(self):
        d = EventDispatcher(graphs={"sales_ops": MagicMock()})
        # LeadInput requires company_name — empty payload triggers validation
        trigger = WorkflowTrigger(workflow_type="sales_ops", payload={})
        result = await d.dispatch(trigger)
        assert result.ok is False
        assert "invalid payload" in result.error

    @pytest.mark.asyncio
    async def test_successful_dispatch_returns_workflow_id(self, monkeypatch):
        # Stub the pipeline so we don't actually run the graph
        from forgeflow.events import dispatcher as disp_mod

        fake_pipeline = MagicMock()
        fake_pipeline.run = AsyncMock(return_value=("wf-1", "th-1", {"current_stage": "done"}))

        def fake_select(workflow_type, graph, payload):
            from forgeflow.workflows.sales_ops.models import LeadInput
            return fake_pipeline, LeadInput(**payload)

        monkeypatch.setattr(disp_mod.EventDispatcher, "_select_pipeline", staticmethod(fake_select))

        d = EventDispatcher(graphs={"sales_ops": MagicMock()})
        trigger = WorkflowTrigger(
            workflow_type="sales_ops",
            payload={"company_name": "Acme"},
            user_id="eve",
            role="bot",
            dry_run=True,
        )
        result = await d.dispatch(trigger)

        assert result.ok is True
        assert result.workflow_id == "wf-1"
        assert result.thread_id == "th-1"
        # Verify the pipeline was called with the right kwargs
        call_kwargs = fake_pipeline.run.call_args.kwargs
        assert call_kwargs["user_id"] == "eve"
        assert call_kwargs["role"] == "bot"
        assert call_kwargs["dry_run"] is True

    @pytest.mark.asyncio
    async def test_pipeline_exception_becomes_error_result(self, monkeypatch):
        from forgeflow.events import dispatcher as disp_mod

        fake_pipeline = MagicMock()
        fake_pipeline.run = AsyncMock(side_effect=RuntimeError("LLM down"))

        def fake_select(workflow_type, graph, payload):
            from forgeflow.workflows.sales_ops.models import LeadInput
            return fake_pipeline, LeadInput(**payload)

        monkeypatch.setattr(disp_mod.EventDispatcher, "_select_pipeline", staticmethod(fake_select))

        d = EventDispatcher(graphs={"sales_ops": MagicMock()})
        result = await d.dispatch(
            WorkflowTrigger(workflow_type="sales_ops", payload={"company_name": "X"})
        )

        assert result.ok is False
        assert "LLM down" in result.error
