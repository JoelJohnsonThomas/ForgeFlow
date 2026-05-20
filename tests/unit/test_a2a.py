"""Tests for A2A protocol models and registry."""

from __future__ import annotations

from forgeflow.a2a.protocol import A2ATask, AgentCard, TaskState
from forgeflow.a2a.registry import AgentRegistry


class TestAgentCard:
    def test_card_creation(self):
        card = AgentCard(
            name="researcher",
            description="Gathers data",
            capabilities=["web_search", "data_gathering"],
            endpoint="internal://researcher",
        )
        assert card.name == "researcher"
        assert "web_search" in card.capabilities
        assert card.agent_id  # UUID auto-generated

    def test_card_serialization(self):
        card = AgentCard(
            name="analyzer",
            description="Scores leads",
            capabilities=["lead_scoring"],
            endpoint="internal://analyzer",
        )
        data = card.model_dump()
        assert data["name"] == "analyzer"
        assert isinstance(data["capabilities"], list)


class TestA2ATask:
    def test_task_lifecycle(self):
        task = A2ATask(
            sender_id="supervisor-001",
            receiver_id="researcher-001",
            method="research_company",
            params={"company": "Acme"},
        )
        assert task.state == TaskState.SUBMITTED

        task.mark_working()
        assert task.state == TaskState.WORKING

        task.mark_completed()
        assert task.state == TaskState.COMPLETED

    def test_task_failure(self):
        task = A2ATask(
            sender_id="s", receiver_id="r", method="test", params={}
        )
        task.mark_failed()
        assert task.state == TaskState.FAILED


class TestAgentRegistry:
    def test_register_and_discover(self):
        registry = AgentRegistry()
        card = AgentCard(
            agent_id="test-agent-001",
            name="test_agent",
            description="Test",
            capabilities=["web_search", "data_analysis"],
            endpoint="internal://test",
        )
        registry.register(card)

        results = registry.discover("web_search")
        assert len(results) == 1
        assert results[0].name == "test_agent"

    def test_discover_unknown_capability_returns_empty(self):
        registry = AgentRegistry()
        results = registry.discover("nonexistent_capability")
        assert results == []

    def test_get_by_id(self):
        registry = AgentRegistry()
        card = AgentCard(
            agent_id="fixed-id",
            name="known",
            description="Known agent",
            capabilities=["skill_a"],
            endpoint="internal://known",
        )
        registry.register(card)
        retrieved = registry.get("fixed-id")
        assert retrieved is not None
        assert retrieved.name == "known"

    def test_deregister(self):
        registry = AgentRegistry()
        card = AgentCard(
            agent_id="temp-agent",
            name="temp",
            description="Temp",
            capabilities=["temp_skill"],
            endpoint="internal://temp",
        )
        registry.register(card)
        assert registry.get("temp-agent") is not None

        registry.deregister("temp-agent")
        assert registry.get("temp-agent") is None
        assert registry.discover("temp_skill") == []
