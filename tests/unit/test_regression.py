"""Tests for the evaluation regression checker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forgeflow.evaluation.metrics import EvalSummary, RunMetrics
from forgeflow.evaluation.regression import check, write_baseline


def _summary_with(**metrics) -> EvalSummary:
    """Build an EvalSummary whose .to_dict() returns the requested metrics.

    The regression checker only reads .to_dict() output, so we patch
    individual runs to hit the requested aggregate values.
    """
    summary = EvalSummary(
        runs=[
            RunMetrics(
                run_id="r1",
                latency_ms=metrics.get("avg_latency_ms", 10_000),
                total_tokens=1000,
                total_cost_usd=metrics.get("avg_cost_usd", 0.03),
                success=metrics.get("success_rate", 1.0) >= 0.5,
                stage_reached="done",
                faithfulness=metrics.get("avg_faithfulness", 0.9),
                relevance=0.85,
                coherence=0.85,
                hallucination_flag=metrics.get("hallucination_rate", 0.0) > 0.5,
            )
        ]
    )
    return summary


@pytest.fixture
def tmp_baseline(tmp_path: Path) -> Path:
    p = tmp_path / "baseline.json"
    p.write_text(
        json.dumps(
            {
                "success_rate": 0.8,
                "avg_latency_ms": 10_000.0,
                "avg_cost_usd": 0.03,
                "avg_faithfulness": 0.9,
                "hallucination_rate": 0.05,
            }
        )
    )
    return p


class TestRegressionCheck:
    def test_steady_metrics_pass(self, tmp_baseline):
        summary = _summary_with(
            success_rate=0.8,
            avg_latency_ms=10_000,
            avg_cost_usd=0.03,
            avg_faithfulness=0.9,
            hallucination_rate=0.0,
        )
        report = check(summary, tmp_baseline)
        assert report.passed is True

    def test_small_drop_in_success_is_warning_not_failure(self, tmp_baseline):
        # success rate drops by 0.03 — past warn (0.02) but before fail (0.05)
        baseline_data = json.loads(tmp_baseline.read_text())
        baseline_data["success_rate"] = 1.0  # baseline at 100%
        tmp_baseline.write_text(json.dumps(baseline_data))

        summary = EvalSummary(
            runs=[
                RunMetrics(
                    run_id=f"r{i}",
                    latency_ms=10_000,
                    total_tokens=1000,
                    total_cost_usd=0.03,
                    success=i < 97,  # 97/100 = 0.97 success rate
                    stage_reached="done",
                    faithfulness=0.9,
                    hallucination_flag=False,
                )
                for i in range(100)
            ]
        )
        report = check(summary, tmp_baseline)
        success_finding = next(f for f in report.findings if f.metric == "success_rate")
        assert success_finding.severity == "warning"
        assert report.passed is True

    def test_large_regression_fails(self, tmp_baseline):
        summary = _summary_with(
            success_rate=0.4,
            avg_latency_ms=10_000,
            avg_cost_usd=0.03,
            avg_faithfulness=0.9,
            hallucination_rate=0.0,
        )
        report = check(summary, tmp_baseline)
        finding = next(f for f in report.findings if f.metric == "success_rate")
        assert finding.severity == "regression"
        assert report.passed is False

    def test_latency_grew_past_fail_tolerance_fails(self, tmp_baseline):
        # baseline avg_latency_ms = 10000, fail tol = 2000
        summary = _summary_with(avg_latency_ms=15_000)
        report = check(summary, tmp_baseline)
        finding = next(f for f in report.findings if f.metric == "avg_latency_ms")
        assert finding.severity == "regression"
        assert report.passed is False

    def test_cost_drop_is_an_improvement_not_a_regression(self, tmp_baseline):
        summary = _summary_with(avg_cost_usd=0.001)  # huge improvement
        report = check(summary, tmp_baseline)
        finding = next(f for f in report.findings if f.metric == "avg_cost_usd")
        assert finding.severity == "ok"

    def test_missing_baseline_passes(self, tmp_path):
        nonexistent = tmp_path / "missing.json"
        summary = _summary_with()
        report = check(summary, nonexistent)
        assert report.passed is True


class TestWriteBaseline:
    def test_persists_summary_dict(self, tmp_path):
        target = tmp_path / "new_baseline.json"
        summary = _summary_with()
        write_baseline(summary, target)

        loaded = json.loads(target.read_text())
        assert "success_rate" in loaded
        assert "avg_latency_ms" in loaded
