"""AgentRegistry — singleton for agent discovery and health tracking.

Agents register themselves at startup with an AgentCard.
The supervisor uses capability-based discovery to find the right worker.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any

from forgeflow.a2a.protocol import AgentCard

logger = logging.getLogger(__name__)


class AgentRegistry:
    """In-memory registry with capability-based discovery and heartbeat tracking."""

    _instance: "AgentRegistry | None" = None

    def __init__(self) -> None:
        self._agents: dict[str, AgentCard] = {}
        self._capability_index: dict[str, set[str]] = defaultdict(set)
        self._heartbeats: dict[str, float] = {}
        self._run_counts: dict[str, int] = defaultdict(int)

    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, card: AgentCard) -> None:
        self._agents[card.agent_id] = card
        for cap in card.capabilities:
            self._capability_index[cap].add(card.agent_id)
        self._heartbeats[card.agent_id] = time.monotonic()
        logger.info(
            "Agent registered: %s (%s) | caps=%s",
            card.name,
            card.agent_id[:8],
            card.capabilities,
        )

    def heartbeat(self, agent_id: str) -> None:
        self._heartbeats[agent_id] = time.monotonic()

    def increment_runs(self, agent_id: str) -> None:
        self._run_counts[agent_id] += 1

    def discover(self, capability: str) -> list[AgentCard]:
        """Find all registered agents that advertise the given capability."""
        ids = self._capability_index.get(capability, set())
        return [self._agents[aid] for aid in ids if aid in self._agents]

    def get(self, agent_id: str) -> AgentCard | None:
        return self._agents.get(agent_id)

    def all_agents(self) -> list[dict[str, Any]]:
        result = []
        for agent_id, card in self._agents.items():
            last_beat = self._heartbeats.get(agent_id, 0)
            result.append({
                **card.model_dump(),
                "last_heartbeat_seconds_ago": round(time.monotonic() - last_beat, 1),
                "runs_completed": self._run_counts[agent_id],
                "healthy": (time.monotonic() - last_beat) < 60,
            })
        return result

    def deregister(self, agent_id: str) -> None:
        card = self._agents.pop(agent_id, None)
        if card:
            for cap in card.capabilities:
                self._capability_index[cap].discard(agent_id)
            self._heartbeats.pop(agent_id, None)
            logger.info("Agent deregistered: %s", agent_id)


def get_registry() -> AgentRegistry:
    return AgentRegistry.get_instance()


# Pre-registered agent cards for the four ForgeFlow agents
def register_default_agents() -> None:
    registry = get_registry()

    registry.register(AgentCard(
        agent_id="supervisor-001",
        name="supervisor",
        description="Routes workflow tasks to specialist agents",
        capabilities=["routing", "orchestration", "decision_making"],
        endpoint="internal://supervisor",
    ))
    registry.register(AgentCard(
        agent_id="researcher-001",
        name="researcher",
        description="Gathers web intelligence about companies and markets",
        capabilities=["web_search", "data_gathering", "company_research"],
        endpoint="internal://researcher",
    ))
    registry.register(AgentCard(
        agent_id="analyzer-001",
        name="analyzer",
        description="Scores and qualifies sales leads",
        capabilities=["lead_scoring", "icp_analysis", "risk_assessment"],
        endpoint="internal://analyzer",
    ))
    registry.register(AgentCard(
        agent_id="executor-001",
        name="executor",
        description="Executes actions: proposals, CRM writes, email sending",
        capabilities=["proposal_drafting", "crm_update", "email_sending"],
        endpoint="internal://executor",
    ))
