"""BudgetGuard — raises BudgetExceededError before an LLM call if cost limit reached."""

from __future__ import annotations

import logging

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    pass


class BudgetGuard:
    def __init__(self, limit_usd: float | None = None) -> None:
        self.limit_usd = limit_usd or get_settings().budget_limit_usd

    def check(self, current_cost_usd: float, estimated_additional: float = 0.0) -> None:
        projected = current_cost_usd + estimated_additional
        if projected >= self.limit_usd:
            raise BudgetExceededError(
                f"Budget exceeded: ${projected:.4f} >= limit ${self.limit_usd:.4f}. "
                "Workflow halted to prevent runaway costs."
            )
        remaining = self.limit_usd - current_cost_usd
        if remaining < self.limit_usd * 0.1:
            logger.warning(
                "Budget nearly exhausted: $%.4f spent, $%.4f remaining",
                current_cost_usd,
                remaining,
            )

    def remaining(self, current_cost_usd: float) -> float:
        return max(0.0, self.limit_usd - current_cost_usd)
