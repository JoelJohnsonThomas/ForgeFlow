"""A2A dispatcher — bridges the LangGraph node layer to the A2A registry.

The supervisor still emits a `next_agent` string for LangGraph's conditional
edge, but each worker node also records the dispatch as a formal A2ATask
through this module. This gives:

  - A real audit trail of which agent ran when, traceable to capability
  - The foundation for moving any single agent out-of-process: the same
    dispatch call site sends via HTTPTransport with no node-code change
  - Heartbeats and run-counts in the registry that drive /agents UI

A2A dispatch is opt-in via settings.a2a_dispatch_enabled (default True for
in-memory; safe to flip off if hot-path latency becomes a concern).

Mapping (agent name -> first capability) lives here so the supervisor's
routing language ("researcher", "analyzer", "executor") doesn't leak into
A2A protocol concepts (capabilities are stable; agent names can be renamed).
"""

from __future__ import annotations

import logging
from typing import Any

from forgeflow.a2a.protocol import A2ATask, AgentCard
from forgeflow.a2a.registry import get_registry
from forgeflow.a2a.transport import get_transport
from forgeflow.config import get_settings

logger = logging.getLogger(__name__)


# Worker node name -> primary capability used for registry lookup.
# The supervisor decides which worker to run; this maps that decision into
# a capability so we never rely on hard-coded agent IDs.
NODE_TO_CAPABILITY: dict[str, str] = {
    "researcher": "web_search",
    "analyzer": "lead_scoring",
    "executor": "proposal_drafting",
    "supervisor": "routing",
}


def _discover_for_node(node_name: str) -> AgentCard | None:
    """Resolve a worker node name to a registered AgentCard.

    Returns None when:
      - the node is not in NODE_TO_CAPABILITY (e.g. human_approval)
      - no agent is registered for that capability yet (early startup race)
    """
    capability = NODE_TO_CAPABILITY.get(node_name)
    if capability is None:
        return None

    candidates = get_registry().discover(capability)
    if not candidates:
        return None
    return candidates[0]


async def dispatch_node(node_name: str, state: dict[str, Any]) -> str | None:
    """Record an A2A dispatch for a node invocation.

    Returns the A2ATask.task_id if dispatch happened, None if dispatch is
    disabled or no matching agent is registered.

    This is fire-and-forget by design — it must NOT raise even if the
    registry or transport is broken. The actual LangGraph node call
    proceeds regardless.
    """
    if not get_settings().a2a_dispatch_enabled:
        return None

    card = _discover_for_node(node_name)
    if card is None:
        return None

    try:
        # The "sender" for in-process dispatch is the supervisor singleton —
        # there's no other peer to act as the originator within one process.
        supervisor_cards = get_registry().discover("routing")
        sender_id = supervisor_cards[0].agent_id if supervisor_cards else "internal"

        task = A2ATask(
            sender_id=sender_id,
            receiver_id=card.agent_id,
            method=f"forgeflow/{node_name}",
            params={
                "workflow_id": state.get("workflow_id"),
                "thread_id": state.get("thread_id"),
                "stage": state.get("current_stage"),
            },
        )
        registry = get_registry()
        registry.heartbeat(card.agent_id)
        registry.increment_runs(card.agent_id)

        transport = get_transport()
        from forgeflow.a2a.protocol import A2AMessage

        await transport.send(A2AMessage.task_request(task), card.endpoint)

        logger.debug(
            "A2A dispatch: %s -> %s (task=%s)",
            node_name,
            card.agent_id,
            task.id[:8],
        )
        return task.id
    except Exception as exc:
        # Dispatch is a best-effort observability layer — never block the run
        logger.warning("A2A dispatch failed for %s: %s", node_name, exc)
        return None
