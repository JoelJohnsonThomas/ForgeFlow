"""Event -> workflow dispatcher.

Sits between an event-source consumer (Redis Streams, Kafka, ...) and the
existing workflow pipelines. The consumer hands each raw event to the
dispatcher; the dispatcher validates, routes by `workflow_type`, and
invokes the right SalesOpsPipeline / SupportOpsPipeline / FinanceReconPipeline.

Why a separate dispatcher: it lets us drop in new event sources without
re-implementing the pipeline-selection logic three times. The same
dispatcher serves Redis today and Kafka tomorrow.

Event envelope contract:
    {
      "workflow_type": "sales_ops" | "support_ops" | "finance_recon",
      "lead_data":     {<domain-specific payload>},
      "user_id":       "<optional>",
      "role":          "<optional>",
      "dry_run":       false                          # optional
    }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from forgeflow.workflows.finance_recon.models import ReconciliationInput
from forgeflow.workflows.finance_recon.pipeline import FinanceReconPipeline
from forgeflow.workflows.sales_ops.models import LeadInput
from forgeflow.workflows.sales_ops.pipeline import SalesOpsPipeline
from forgeflow.workflows.support_ops.models import TicketInput
from forgeflow.workflows.support_ops.pipeline import SupportOpsPipeline

logger = logging.getLogger(__name__)


@dataclass
class WorkflowTrigger:
    """A parsed, validated event ready for dispatch."""
    workflow_type: str
    payload: dict[str, Any]
    user_id: str = "events"
    role: str = "system"
    dry_run: bool = False
    source_event_id: str | None = None      # the upstream queue's message id
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchResult:
    ok: bool
    workflow_id: str | None = None
    thread_id: str | None = None
    error: str | None = None


class EventDispatcher:
    """Routes WorkflowTrigger events to the right pipeline.

    Holds references to compiled graphs (one per workflow_type) so it
    doesn't pay the compile cost per event.
    """

    def __init__(self, graphs: dict[str, Any]) -> None:
        self.graphs = graphs

    @staticmethod
    def parse_event(raw: dict[str, Any], source_event_id: str | None = None) -> WorkflowTrigger:
        """Parse + validate an event envelope. Raises ValueError on malformed input."""
        if not isinstance(raw, dict):
            raise ValueError("event must be a JSON object")
        wf = raw.get("workflow_type")
        if wf not in ("sales_ops", "support_ops", "finance_recon"):
            raise ValueError(f"unknown workflow_type: {wf!r}")
        payload = raw.get("lead_data") or raw.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("event missing 'lead_data' (or 'payload') object")

        return WorkflowTrigger(
            workflow_type=wf,
            payload=payload,
            user_id=str(raw.get("user_id", "events")),
            role=str(raw.get("role", "system")),
            dry_run=bool(raw.get("dry_run", False)),
            source_event_id=source_event_id,
            extra={k: v for k, v in raw.items() if k not in {
                "workflow_type", "lead_data", "payload", "user_id", "role", "dry_run"
            }},
        )

    async def dispatch(self, trigger: WorkflowTrigger) -> DispatchResult:
        """Resolve pipeline + input model + invoke. Catches errors so the
        consumer can ack/nack appropriately rather than crashing its loop."""
        graph = self.graphs.get(trigger.workflow_type)
        if graph is None:
            return DispatchResult(ok=False, error=f"no graph for {trigger.workflow_type}")

        try:
            pipeline, domain_input = self._select_pipeline(
                trigger.workflow_type, graph, trigger.payload
            )
        except Exception as exc:
            logger.warning(
                "event %s rejected: invalid payload for %s — %s",
                trigger.source_event_id,
                trigger.workflow_type,
                exc,
            )
            return DispatchResult(ok=False, error=f"invalid payload: {exc}")

        try:
            workflow_id, thread_id, _ = await pipeline.run(
                domain_input,
                user_id=trigger.user_id,
                role=trigger.role,
                dry_run=trigger.dry_run,
            )
        except Exception as exc:
            logger.exception(
                "event %s dispatch failed for %s: %s",
                trigger.source_event_id,
                trigger.workflow_type,
                exc,
            )
            return DispatchResult(ok=False, error=str(exc))

        logger.info(
            "event %s -> workflow %s (%s)",
            trigger.source_event_id,
            workflow_id,
            trigger.workflow_type,
        )
        return DispatchResult(ok=True, workflow_id=workflow_id, thread_id=thread_id)

    @staticmethod
    def _select_pipeline(workflow_type: str, graph: Any, payload: dict) -> tuple[Any, Any]:
        """Mirror the dispatcher used by /workflows/run."""
        if workflow_type == "support_ops":
            return SupportOpsPipeline(graph), TicketInput(**payload)
        if workflow_type == "finance_recon":
            return FinanceReconPipeline(graph), ReconciliationInput(**payload)
        return SalesOpsPipeline(graph), LeadInput(**payload)
