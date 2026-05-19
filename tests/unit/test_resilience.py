"""Tests for circuit breaker and budget guard."""

from __future__ import annotations

import pytest

from forgeflow.resilience.circuit_breaker import CBState, CircuitBreaker, CircuitOpenError
from forgeflow.resilience.budget_guard import BudgetGuard, BudgetExceededError


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
