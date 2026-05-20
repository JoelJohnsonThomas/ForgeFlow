"""AuditMiddleware — writes every request/response to the immutable audit_log table."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths to skip auditing (too noisy for high-frequency endpoints)
_SKIP_AUDIT = {"/health", "/metrics/prometheus", "/docs", "/openapi.json", "/redoc"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in _SKIP_AUDIT:
            return await call_next(request)

        start = time.monotonic()
        request_id = str(uuid.uuid4())
        request.state.request_id = getattr(request.state, "request_id", request_id)

        response = await call_next(request)

        latency_ms = (time.monotonic() - start) * 1000
        user_id = getattr(request.state, "user_id", "anonymous")
        role = getattr(request.state, "role", "unknown")
        outcome = "allowed" if response.status_code < 400 else (
            "denied" if response.status_code == 403 else "error"
        )

        # Write to audit log (best-effort — don't fail the request if DB is down)
        try:
            pool = getattr(request.app.state, "pool", None)
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO audit_log
                          (user_id, role, action, resource, outcome, request_id, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        user_id,
                        role,
                        request.method,
                        request.url.path,
                        outcome,
                        uuid.UUID(request_id),
                        {
                            "status_code": response.status_code,
                            "latency_ms": round(latency_ms, 1),
                            "user_agent": request.headers.get("user-agent", ""),
                        },
                    )
        except Exception as e:
            logger.error("Audit log write failed: %s", e)

        response.headers["X-Request-Id"] = request_id
        return response
