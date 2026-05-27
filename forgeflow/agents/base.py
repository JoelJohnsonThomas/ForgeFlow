"""BaseAgent — abstract base class for all ForgeFlow agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from forgeflow.resilience.circuit_breaker import CircuitBreaker
from forgeflow.state.workflow_state import WorkflowState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """All agents inherit from this. Provides circuit breaking and a standard interface."""

    def __init__(
        self,
        name: str,
        model: BaseChatModel,
        tools: list[BaseTool] | None = None,
        system_prompt: str = "",
    ) -> None:
        from forgeflow.security.tool_output_guard import SYSTEM_HARDENING_NOTE

        self.name = name
        self.tools = tools or []
        # Every agent inherits the indirect-PI hardening clause. Without it
        # tool outputs wrapped by tool_output_guard still flow in, but the
        # model has no policy telling it those tags are data only.
        self.system_prompt = (
            f"{system_prompt.rstrip()}\n\n{SYSTEM_HARDENING_NOTE}"
            if system_prompt
            else SYSTEM_HARDENING_NOTE
        )
        self._circuit_breaker = CircuitBreaker(name=name, failure_threshold=5, recovery_timeout=30.0)

        # Capture the underlying model identifier for cost-tracking lookups.
        # Different providers expose the name under different attribute names.
        self.model_name = (
            getattr(model, "model_name", None) or getattr(model, "model", None) or "unknown"
        )

        # Bind tools to the model so it can emit tool-call messages
        self.model = model.bind_tools(self.tools) if self.tools else model

    @abstractmethod
    async def run(self, state: WorkflowState) -> dict:
        """Execute agent logic. Returns a dict of WorkflowState updates (partial patch)."""

    async def stream(self, state: WorkflowState) -> AsyncIterator[dict]:
        """Default streaming: yields single chunk from run(). Override for token-level streaming."""
        result = await self.run(state)
        yield result

    async def safe_run(self, state: WorkflowState) -> dict:
        """Wraps run() with circuit breaker protection."""
        return await self._circuit_breaker.acall(self.run, state)

    def _log_start(self, state: WorkflowState) -> None:
        logger.info(
            "Agent '%s' starting | stage=%s | workflow=%s",
            self.name,
            state.get("current_stage"),
            state.get("workflow_id"),
        )

    def _log_finish(self, tokens: int, cost: float) -> None:
        logger.info(
            "Agent '%s' finished | tokens=%d | cost=$%.4f",
            self.name,
            tokens,
            cost,
        )
