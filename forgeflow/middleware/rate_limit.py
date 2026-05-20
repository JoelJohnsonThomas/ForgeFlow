"""Token-bucket rate limiter — per user_id, enforced at middleware level."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Rate limit: 60 requests per minute per user
_REQUESTS_PER_MINUTE = 60
_BUCKET_WINDOW = 60.0  # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, requests_per_minute: int = _REQUESTS_PER_MINUTE) -> None:
        super().__init__(app)
        self.rpm = requests_per_minute
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        user_id = getattr(request.state, "user_id", "anonymous")
        now = time.monotonic()

        # Remove timestamps older than the window
        self._buckets[user_id] = [
            ts for ts in self._buckets[user_id] if now - ts < _BUCKET_WINDOW
        ]

        if len(self._buckets[user_id]) >= self.rpm:
            logger.warning("Rate limit hit for user=%s", user_id)
            return JSONResponse(
                {"error": "Rate limit exceeded", "retry_after_seconds": _BUCKET_WINDOW},
                status_code=429,
            )

        self._buckets[user_id].append(now)
        return await call_next(request)
