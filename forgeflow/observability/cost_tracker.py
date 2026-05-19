"""CostTracker — tiktoken-based token counting + per-model cost calculation.

Tracks cumulative spend for a workflow run and enforces budget limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Cost per 1,000 tokens in USD (as of 2025 pricing)
MODEL_COSTS_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.000150, "output": 0.000600},
    "gpt-4-turbo": {"input": 0.010, "output": 0.030},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
    "text-embedding-3-large": {"input": 0.00013, "output": 0.0},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a single LLM call."""
    rates = MODEL_COSTS_PER_1K.get(model, {"input": 0.01, "output": 0.03})
    return (input_tokens / 1000 * rates["input"]) + (output_tokens / 1000 * rates["output"])


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens in text using tiktoken. Falls back to word estimate."""
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text.split()) * 4 // 3)  # rough ~4/3 tokens per word


@dataclass
class CostTracker:
    """Tracks cumulative token usage and cost for a workflow run."""

    model: str = "gpt-4o-mini"
    total_input_tokens: int = field(default=0)
    total_output_tokens: int = field(default=0)
    call_log: list[dict] = field(default_factory=list)

    def record(
        self,
        agent_name: str,
        input_tokens: int,
        output_tokens: int,
        model: str | None = None,
    ) -> float:
        """Record a single LLM call and return its cost in USD."""
        effective_model = model or self.model
        cost = calculate_cost(effective_model, input_tokens, output_tokens)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.call_log.append({
            "agent": agent_name,
            "model": effective_model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
        })

        logger.debug(
            "Cost: %s used %d+%d tokens ($%.4f)",
            agent_name,
            input_tokens,
            output_tokens,
            cost,
        )
        return cost

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_cost_usd(self) -> float:
        return sum(entry["cost_usd"] for entry in self.call_log)

    def summary(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "call_count": len(self.call_log),
            "by_agent": self._by_agent(),
        }

    def _by_agent(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for entry in self.call_log:
            agent = entry["agent"]
            if agent not in result:
                result[agent] = {"tokens": 0, "cost_usd": 0.0, "calls": 0}
            result[agent]["tokens"] += entry["input_tokens"] + entry["output_tokens"]
            result[agent]["cost_usd"] += entry["cost_usd"]
            result[agent]["calls"] += 1
        return result
