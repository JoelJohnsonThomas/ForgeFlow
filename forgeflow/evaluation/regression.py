"""Regression checker — compares current eval summary against a stored baseline.

CI uses this to fail a PR when quality regresses beyond tolerance. Tolerances
are intentionally generous so noise doesn't cause flaky failures; tighten them
once the baseline stabilises.

Metric semantics:
  - higher_is_better: success_rate, avg_faithfulness — current must be >= baseline - tol
  - lower_is_better:  avg_latency_ms, avg_cost_usd, hallucination_rate — current must be <= baseline + tol

Returns a list of RegressionFinding dataclasses. CI fails if any finding has
severity == 'regression' (not 'warning' or 'ok').
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from forgeflow.evaluation.metrics import EvalSummary

logger = logging.getLogger(__name__)


@dataclass
class RegressionFinding:
    metric: str
    current: float
    baseline: float
    delta: float
    severity: str  # ok | warning | regression
    explanation: str


@dataclass
class RegressionReport:
    passed: bool
    findings: list[RegressionFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "findings": [asdict(f) for f in self.findings],
        }


# Per-metric tolerances: (relative_warn, relative_fail).
# Example: success_rate warn at -2pp drop, fail at -5pp drop.
TOLERANCES: dict[str, tuple[str, float, float]] = {
    "success_rate":       ("higher_is_better", 0.02,  0.05),
    "avg_faithfulness":   ("higher_is_better", 0.03,  0.08),
    "avg_latency_ms":     ("lower_is_better",  500,   2000),  # absolute milliseconds
    "avg_cost_usd":       ("lower_is_better",  0.005, 0.02),  # absolute dollars
    "hallucination_rate": ("lower_is_better",  0.02,  0.05),
}


def check(summary: EvalSummary, baseline_path: Path) -> RegressionReport:
    """Compare summary metrics against the baseline JSON file.

    Args:
        summary: EvalSummary produced by EvalRunner.run_suite
        baseline_path: Path to the committed baseline JSON

    Returns:
        RegressionReport with a per-metric finding for each tracked dimension.
    """
    if not baseline_path.exists():
        logger.warning("Baseline file not found at %s; treating as first run", baseline_path)
        return RegressionReport(passed=True)

    with baseline_path.open() as fh:
        baseline = json.load(fh)

    current = summary.to_dict()
    findings: list[RegressionFinding] = []

    for metric, (direction, warn_tol, fail_tol) in TOLERANCES.items():
        if metric not in baseline or metric not in current:
            continue

        cur = float(current[metric])
        base = float(baseline[metric])
        delta = cur - base

        if direction == "higher_is_better":
            # negative delta = bad
            if delta >= -warn_tol:
                sev, why = "ok", f"{metric} steady or improved (delta={delta:+.4f})"
            elif delta >= -fail_tol:
                sev, why = "warning", f"{metric} slipped by {-delta:.4f} (warn tol={warn_tol})"
            else:
                sev, why = "regression", f"{metric} regressed by {-delta:.4f} (fail tol={fail_tol})"
        else:  # lower_is_better
            # positive delta = bad
            if delta <= warn_tol:
                sev, why = "ok", f"{metric} steady or improved (delta={delta:+.4f})"
            elif delta <= fail_tol:
                sev, why = "warning", f"{metric} grew by {delta:.4f} (warn tol={warn_tol})"
            else:
                sev, why = "regression", f"{metric} regressed by {delta:.4f} (fail tol={fail_tol})"

        findings.append(
            RegressionFinding(
                metric=metric,
                current=cur,
                baseline=base,
                delta=delta,
                severity=sev,
                explanation=why,
            )
        )

    passed = not any(f.severity == "regression" for f in findings)
    return RegressionReport(passed=passed, findings=findings)


def write_baseline(summary: EvalSummary, path: Path) -> None:
    """Persist current metrics as the new baseline. Used by maintainers to
    promote a known-good run after intentional quality changes."""
    path.write_text(json.dumps(summary.to_dict(), indent=2) + "\n")
    logger.info("Wrote new baseline to %s", path)
