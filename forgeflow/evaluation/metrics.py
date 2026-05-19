"""Custom evaluation metrics beyond LLM-as-judge: latency, cost, token efficiency."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RunMetrics:
    """Metrics for a single workflow run."""

    run_id: str
    latency_ms: float
    total_tokens: int
    total_cost_usd: float
    success: bool
    stage_reached: str

    # LLM judge scores (optional — populated after evaluation)
    faithfulness: Optional[float] = None
    relevance: Optional[float] = None
    coherence: Optional[float] = None
    hallucination_flag: Optional[bool] = None

    @property
    def tokens_per_dollar(self) -> float:
        if self.total_cost_usd <= 0:
            return 0.0
        return self.total_tokens / self.total_cost_usd

    @property
    def cost_efficiency_score(self) -> float:
        """Higher = better (0-1): normalized cost per token vs $0.01 baseline."""
        if self.total_tokens == 0:
            return 0.0
        cost_per_token = self.total_cost_usd / self.total_tokens
        baseline = 0.00001  # $0.01 per 1000 tokens
        return min(1.0, baseline / max(cost_per_token, 1e-9))


@dataclass
class EvalSummary:
    """Aggregate statistics across multiple eval runs."""

    runs: list[RunMetrics] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.runs)

    @property
    def success_rate(self) -> float:
        if not self.runs:
            return 0.0
        return sum(1 for r in self.runs if r.success) / len(self.runs)

    @property
    def avg_latency_ms(self) -> float:
        latencies = [r.latency_ms for r in self.runs]
        return statistics.mean(latencies) if latencies else 0.0

    @property
    def p95_latency_ms(self) -> float:
        latencies = sorted(r.latency_ms for r in self.runs)
        if not latencies:
            return 0.0
        idx = int(len(latencies) * 0.95)
        return latencies[min(idx, len(latencies) - 1)]

    @property
    def avg_cost_usd(self) -> float:
        costs = [r.total_cost_usd for r in self.runs]
        return statistics.mean(costs) if costs else 0.0

    @property
    def avg_faithfulness(self) -> float:
        scores = [r.faithfulness for r in self.runs if r.faithfulness is not None]
        return statistics.mean(scores) if scores else 0.0

    @property
    def hallucination_rate(self) -> float:
        flagged = [r for r in self.runs if r.hallucination_flag is True]
        evaluated = [r for r in self.runs if r.hallucination_flag is not None]
        if not evaluated:
            return 0.0
        return len(flagged) / len(evaluated)

    def to_dict(self) -> dict:
        return {
            "total_runs": self.total,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "p95_latency_ms": round(self.p95_latency_ms, 1),
            "avg_cost_usd": round(self.avg_cost_usd, 6),
            "avg_faithfulness": round(self.avg_faithfulness, 3),
            "hallucination_rate": round(self.hallucination_rate, 3),
        }
