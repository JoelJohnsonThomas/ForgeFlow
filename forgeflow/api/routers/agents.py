"""Agent registry routes — list agents, send A2A messages, inspect dispatch."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from forgeflow.a2a.dispatcher import NODE_TO_CAPABILITY
from forgeflow.a2a.protocol import A2AMessage
from forgeflow.a2a.registry import get_registry
from forgeflow.a2a.transport import get_transport
from forgeflow.config import get_settings

router = APIRouter()


@router.get("/")
async def list_agents():
    """List all registered agents with status and capabilities."""
    return get_registry().all_agents()


@router.get("/dispatch")
async def dispatch_info():
    """Show the current node-to-capability map + A2A dispatch toggle.

    Useful for verifying that the supervisor routing language resolves to
    registered agents — a missing capability here means a node will fall
    back to in-process invocation only (no A2A audit record).
    """
    registry = get_registry()
    resolved: dict[str, dict | None] = {}
    for node, capability in NODE_TO_CAPABILITY.items():
        candidates = registry.discover(capability)
        resolved[node] = (
            {
                "capability": capability,
                "agent_id": candidates[0].agent_id,
                "agent_name": candidates[0].name,
            }
            if candidates
            else {"capability": capability, "agent_id": None, "agent_name": None}
        )

    return {
        "dispatch_enabled": get_settings().a2a_dispatch_enabled,
        "transport": type(get_transport()).__name__,
        "node_to_agent": resolved,
    }


@router.get("/{agent_id}/status")
async def agent_status(agent_id: str):
    """Get status details for a specific agent."""
    agents = {a["agent_id"]: a for a in get_registry().all_agents()}
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents[agent_id]


@router.post("/{agent_id}/message")
async def send_a2a_message(agent_id: str, message: A2AMessage):
    """Send an A2A message directly to an agent (admin/testing endpoint)."""
    card = get_registry().get(agent_id)
    if not card:
        raise HTTPException(status_code=404, detail="Agent not found in registry")

    transport = get_transport()
    response = await transport.send(message, card.endpoint)
    return {"sent": True, "response": response.model_dump() if response else None}
