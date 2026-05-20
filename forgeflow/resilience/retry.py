"""Retry decorator with exponential backoff using tenacity."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_RETRYABLE = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
    ConnectionError,
    TimeoutError,
)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retryable: tuple[type[Exception], ...] = _RETRYABLE,
) -> Any:
    """Decorator factory: wraps a sync or async function with retry logic."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retryable),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


async def retry_async(
    func: Callable,
    *args: Any,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    **kwargs: Any,
) -> Any:
    """Programmatic async retry (useful when you can't use a decorator)."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(_RETRYABLE),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    ):
        with attempt:
            return await func(*args, **kwargs)
