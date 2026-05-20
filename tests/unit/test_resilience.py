"""Tests for circuit breaker and budget guard."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from forgeflow.graph import nodes as graph_nodes
from forgeflow.resilience.budget_guard import BudgetExceededError, BudgetGuard
from forgeflow.resilience.circuit_breaker import CBState, CircuitBreaker, CircuitOpenError


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CBState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        def bad_func():
            raise ValueError("boom")

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(bad_func)

        assert cb.state == CBState.OPEN

    def test_open_rejects_calls(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=9999)

        def bad_func():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            cb.call(bad_func)

        with pytest.raises(CircuitOpenError):
            cb.call(lambda: "should not run")

    def test_success_resets_counter(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        def bad_func():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            cb.call(bad_func)

        assert cb._failure_count == 1

        cb.call(lambda: "ok")  # success
        assert cb._failure_count == 0
        assert cb.state == CBState.CLOSED


class TestBudgetGuard:
    def test_allows_within_budget(self):
        guard = BudgetGuard(limit_usd=5.0)
        guard.check(current_cost_usd=2.0)  # should not raise

    def test_raises_when_exceeded(self):
        guard = BudgetGuard(limit_usd=5.0)
        with pytest.raises(BudgetExceededError):
            guard.check(current_cost_usd=5.0)

    def test_raises_with_projected_cost(self):
        guard = BudgetGuard(limit_usd=5.0)
        with pytest.raises(BudgetExceededError):
            guard.check(current_cost_usd=4.0, estimated_additional=2.0)

    def test_remaining_calculation(self):
        guard = BudgetGuard(limit_usd=5.0)
        assert guard.remaining(2.0) == 3.0

    def test_remaining_never_negative(self):
        guard = BudgetGuard(limit_usd=5.0)
        assert guard.remaining(10.0) == 0.0


class TestNodeCostTracking:
    """Verify _run_with_cost_tracking wraps agents with budget + cost behavior."""

    def _make_agent(self, name="researcher", model_name="gpt-4o-mini", patch=None):
        agent = MagicMock()
        agent.name = name
        agent.model_name = model_name
        agent.safe_run = AsyncMock(
            return_value=patch
            or {
                "messages": [
                    AIMessage(
                        content="research result",
                        usage_metadata={
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "total_tokens": 150,
                        },
                    )
                ],
                "research_results": [{"summary": "ok"}],
            }
        )
        return agent

    @pytest.mark.asyncio
    async def test_budget_exceeded_short_circuits(self, monkeypatch):
        monkeypatch.setenv("BUDGET_LIMIT_USD", "0.001")
        from forgeflow.config import get_settings

        get_settings.cache_clear()

        agent = self._make_agent()
        state = {
            "total_cost_usd": 0.002,  # already over the $0.001 limit
            "total_tokens": 1000,
        }

        result = await graph_nodes._run_with_cost_tracking(agent, state)

        agent.safe_run.assert_not_called()
        assert result["next_agent"] == "FINISH"
        assert any("BudgetExceeded" in e for e in result["errors"])
        # Cost not changed when we short-circuit
        assert result["total_cost_usd"] == 0.002

        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_records_cost_from_usage_metadata(self, monkeypatch):
        monkeypatch.setenv("BUDGET_LIMIT_USD", "100.0")
        from forgeflow.config import get_settings

        get_settings.cache_clear()

        agent = self._make_agent(model_name="gpt-4o-mini")
        state = {"total_cost_usd": 0.0, "total_tokens": 0}

        result = await graph_nodes._run_with_cost_tracking(agent, state)

        agent.safe_run.assert_called_once()
        # gpt-4o-mini: input=$0.00015/1k, output=$0.0006/1k
        # 100 input + 50 output → 100/1000*0.00015 + 50/1000*0.0006 = 0.000045
        assert result["total_tokens"] == 150
        assert result["total_cost_usd"] == pytest.approx(0.000045, rel=0.01)

        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_accumulates_across_calls(self, monkeypatch):
        monkeypatch.setenv("BUDGET_LIMIT_USD", "100.0")
        from forgeflow.config import get_settings

        get_settings.cache_clear()

        agent = self._make_agent(model_name="gpt-4o-mini")
        state = {"total_cost_usd": 1.5, "total_tokens": 5000}

        result = await graph_nodes._run_with_cost_tracking(agent, state)

        assert result["total_tokens"] == 5150
        assert result["total_cost_usd"] > 1.5
        assert result["total_cost_usd"] == pytest.approx(1.5 + 0.000045, rel=0.01)

        get_settings.cache_clear()
