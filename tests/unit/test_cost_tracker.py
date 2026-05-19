"""Tests for cost tracking and budget guard."""

from __future__ import annotations

from forgeflow.observability.cost_tracker import CostTracker, calculate_cost


def test_calculate_cost_gpt4o_mini():
    cost = calculate_cost("gpt-4o-mini", input_tokens=1000, output_tokens=500)
    # 1000 * 0.000150/1000 + 500 * 0.000600/1000
    expected = 0.000150 + 0.000300
    assert abs(cost - expected) < 1e-9


def test_tracker_accumulates():
    tracker = CostTracker(model="gpt-4o-mini")
    tracker.record("researcher", 500, 200)
    tracker.record("analyzer", 300, 100)

    assert tracker.total_input_tokens == 800
    assert tracker.total_output_tokens == 300
    assert tracker.total_tokens == 1100
    assert tracker.total_cost_usd > 0


def test_tracker_by_agent():
    tracker = CostTracker(model="gpt-4o-mini")
    tracker.record("researcher", 1000, 500)
    tracker.record("researcher", 200, 100)
    tracker.record("analyzer", 300, 150)

    by_agent = tracker._by_agent()
    assert "researcher" in by_agent
    assert by_agent["researcher"]["calls"] == 2
    assert by_agent["analyzer"]["calls"] == 1


def test_tracker_summary():
    tracker = CostTracker(model="gpt-4o-mini")
    tracker.record("supervisor", 100, 50)
    summary = tracker.summary()

    assert "total_tokens" in summary
    assert "total_cost_usd" in summary
    assert "by_agent" in summary
    assert summary["call_count"] == 1
