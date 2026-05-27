"""Token-bucket rate limiter.

Hardening (SECURITY_AUDIT.md A-2, A-4):
  - Runs AFTER RBACMiddleware so the key includes the verified user_id +
    workspace_id; bypassing identity no longer gets you a fresh bucket.
  - Anonymous routes (login/health) key on the client IP so a single host
    cannot exhaust the global "anonymous" bucket.
  - Buckets are tiered:
        anon       — 10/min  per IP   (login, openapi)
        mutating   — 30/min  per user (POST/PUT/PATCH/DELETE)
        read       — 120/min per user (GET)
  - Per-replica; SECURITY_AUDIT.md A-4 tracks the Redis migration.
"""

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

_WINDOW_S = 60.0
_LIMITS = {
    "anon": 10,
    "mutating": 30,
    "read": 120,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        bucket_key, tier = self._key_for(request)
        limit = _LIMITS[tier]
        now = time.monotonic()

        bucket = [ts for ts in self._buckets[bucket_key] if now - ts < _WINDOW_S]
        self._buckets[bucket_key] = bucket

        if len(bucket) >= limit:
            logger.warning("Rate limit hit | key=%s tier=%s limit=%d", bucket_key, tier, limit)
            retry_after = int(_WINDOW_S - (now - bucket[0])) if bucket else int(_WINDOW_S)
            return JSONResponse(
                {"error": "Rate limit exceeded", "retry_after_seconds": max(1, retry_after)},
                status_code=429,
                headers={"Retry-After": str(max(1, retry_after))},
            )

        bucket.append(now)
        return await call_next(request)

    @staticmethod
    def _key_for(request: Request) -> tuple[str, str]:
        from forgeflow.config import get_settings

        path = request.url.path
        method = request.method.upper()

        # Anonymous tier: login + health + openapi — key on IP, not user_id.
        if path.startswith("/auth/") or path in {"/health", "/openapi.json"}:
            return f"anon|{_client_ip(request, get_settings().trusted_proxy_count)}", "anon"

        user_id = getattr(request.state, "user_id", None) or "anonymous"
        workspace_id = getattr(request.state, "workspace_id", "") or ""
        # Route class is the first path segment so /workflows/run + /workflows
        # share a budget — stops a hot list-call from starving the run endpoint.
        route_class = path.split("/", 2)[1] if "/" in path else path

        tier = "mutating" if method in {"POST", "PUT", "PATCH", "DELETE"} else "read"
        key = f"{tier}|{workspace_id}|{user_id}|{route_class}"
        return key, tier


def _client_ip(request: Request, trusted_proxy_count: int) -> str:
    if trusted_proxy_count > 0:
        xff = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        idx = -trusted_proxy_count
        if -idx <= len(parts):
            return parts[idx]
    return request.client.host if request.client else "unknown"
