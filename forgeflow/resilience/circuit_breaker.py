"""Circuit breaker — prevents cascading failures to downstream services.

States:
  CLOSED    — normal operation, calls pass through
  OPEN      — too many failures, calls rejected immediately
  HALF_OPEN — after recovery_timeout, one probe call allowed
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CBState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    pass


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0

    _state: CBState = field(default=CBState.CLOSED, init=False, repr=False)
    _failure_count: int = field(default=0, init=False, repr=False)
    _opened_at: float = field(default=0.0, init=False, repr=False)

    @property
    def state(self) -> CBState:
        return self._state

    def _on_success(self) -> None:
        if self._state == CBState.HALF_OPEN:
            logger.info("CircuitBreaker '%s' closed after successful probe", self.name)
        self._failure_count = 0
        self._state = CBState.CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._state = CBState.OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                "CircuitBreaker '%s' opened after %d failures",
                self.name,
                self._failure_count,
            )

    def _check_half_open(self) -> None:
        if self._state == CBState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = CBState.HALF_OPEN
                logger.info("CircuitBreaker '%s' entering HALF_OPEN", self.name)

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        self._check_half_open()
        if self._state == CBState.OPEN:
            raise CircuitOpenError(f"Circuit '{self.name}' is OPEN — refusing call")
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    async def acall(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        self._check_half_open()
        if self._state == CBState.OPEN:
            raise CircuitOpenError(f"Circuit '{self.name}' is OPEN — refusing call")
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise


# Global registry of circuit breakers (one per named service)
_registry: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    if name not in _registry:
        _registry[name] = CircuitBreaker(name=name, **kwargs)
    return _registry[name]
