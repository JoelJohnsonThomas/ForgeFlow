"""Tests for the A2A dispatcher — registry lookup + transport handoff."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from forgeflow.a2a.dispatcher import (
    NODE_TO_CAPABILITY,
    _discover_for_node,
    dispatch_node,
)
from forgeflow.a2a.protocol import AgentCard
from forgeflow.a2a.registry import AgentRegistry, get_registry, register_default_agents
from forgeflow.config import get_settings


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch):
    """Each test gets a fresh singleton — prevents cross-test pollution."""
    AgentRegistry._instance = None  # noqa: SLF001
    register_default_agents()
    get_settings.cache_clear()
    yield
    AgentRegistry._instance = None  # noqa: SLF001
    get_settings.cache_clear()


class TestDiscovery:
    def test_known_node_resolves_to_registered_agent(self):
        card = _discover_for_node("researcher")
        assert card is not None
        assert card.name == "researcher"

    def test_unknown_node_returns_none(self):
        assert _discover_for_node("human_approval") is None
        assert _discover_for_node("totally_bogus") is None

    def test_capability_mapping_covers_all_worker_nodes(self):
        for node in ("researcher", "analyzer", "executor", "supervisor"):
            assert node in NODE_TO_CAPABILITY


class TestDispatchNode:
    @pytest.mark.asyncio
    async def test_dispatch_records_heartbeat_and_run_count(self, monkeypatch):
        monkeypatch.setenv("A2A_DISPATCH_ENABLED", "true")
        get_settings.cache_clear()

        registry = get_registry()
        before = next(a for a in registry.all_agents() if a["name"] == "researcher")
        before_runs = before["runs_completed"]

        # Stub transport.send so we don't actually queue
        from forgeflow.a2a import dispatcher as disp_mod

        async def _stub_send(message, endpoint):
            return None

        fake_transport = AsyncMock()
        fake_transport.send = AsyncMock(side_effect=_stub_send)
        monkeypatch.setattr(disp_mod, "get_transport", lambda: fake_transport)

        task_id = await dispatch_node(
            "researcher",
            {"workflow_id": "wf-1", "thread_id": "th-1", "current_stage": "qualify"},
        )

        assert task_id is not None
        after = next(a for a in registry.all_agents() if a["name"] == "researcher")
        assert after["runs_completed"] == before_runs + 1
        # Transport got exactly one message
        assert fake_transport.send.call_count == 1

    @pytest.mark.asyncio
    async def test_dispatch_disabled_returns_none(self, monkeypatch):
        monkeypatch.setenv("A2A_DISPATCH_ENABLED", "false")
        get_settings.cache_clear()

        task_id = await dispatch_node("researcher", {})
        assert task_id is None

    @pytest.mark.asyncio
    async def test_unknown_node_returns_none(self):
        assert await dispatch_node("human_approval", {}) is None

    @pytest.mark.asyncio
    async def test_no_registered_agent_returns_none(self, monkeypatch):
        """If discovery finds no agent for the capability, dispatch is a no-op."""
        monkeypatch.setenv("A2A_DISPATCH_ENABLED", "true")
        get_settings.cache_clear()

        registry = get_registry()
        # Wipe researcher registrations
        for card in list(registry._agents.values()):  # noqa: SLF001
            if card.name == "researcher":
                registry.deregister(card.agent_id)

        assert await dispatch_node("researcher", {}) is None

    @pytest.mark.asyncio
    async def test_dispatch_never_raises_on_transport_error(self, monkeypatch):
        monkeypatch.setenv("A2A_DISPATCH_ENABLED", "true")
        get_settings.cache_clear()

        from forgeflow.a2a import dispatcher as disp_mod

        bad_transport = AsyncMock()
        bad_transport.send = AsyncMock(side_effect=RuntimeError("transport down"))
        monkeypatch.setattr(disp_mod, "get_transport", lambda: bad_transport)

        # Must not raise — dispatcher is best-effort observability
        result = await dispatch_node("researcher", {"workflow_id": "wf-x"})
        assert result is None


class TestExtensibility:
    def test_can_register_new_agent_for_existing_capability(self):
        registry = get_registry()
        registry.register(
            AgentCard(
                agent_id="researcher-002",
                name="researcher-fallback",
                description="A second researcher for failover",
                capabilities=["web_search"],
                endpoint="internal://researcher-002",
            )
        )

        # Discovery returns both
        candidates = registry.discover("web_search")
        names = {c.name for c in candidates}
        assert "researcher" in names
        assert "researcher-fallback" in names
