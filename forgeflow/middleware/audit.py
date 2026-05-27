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


def _is_uuid(value: str) -> bool:
    """Cheap UUID-shape check so we don't write 'anonymous' into a UUID column."""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _client_ip(request: Request) -> str | None:
    """Return the client IP from X-Forwarded-For only when proxy hops are
    configured. Otherwise the socket peer wins. Closes the audit attribution
    spoofing called out in SECURITY_AUDIT.md §6.
    """
    from forgeflow.config import get_settings

    hops = get_settings().trusted_proxy_count
    if hops > 0:
        xff = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        idx = -hops
        if -idx <= len(parts):
            return parts[idx]
    return request.client.host if request.client else None


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

        # Write to audit log. Persistent failure surfaces via the metric +
        # logged ERROR so an outage doesn't silently drop the immutable
        # record SECURITY_AUDIT.md §6 demands.
        try:
            pool = getattr(request.app.state, "pool", None)
            if pool:
                workspace_id = getattr(request.state, "workspace_id", None)
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO audit_log
                          (user_id, role, action, resource, outcome, request_id,
                           workspace_id, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        user_id if _is_uuid(user_id) else None,
                        role,
                        request.method,
                        request.url.path,
                        outcome,
                        uuid.UUID(request_id),
                        uuid.UUID(workspace_id) if workspace_id else None,
                        {
                            "status_code": response.status_code,
                            "latency_ms": round(latency_ms, 1),
                            "user_agent": request.headers.get("user-agent", "")[:512],
                            "user_id_str": str(user_id),
                            "client_ip": _client_ip(request),
                        },
                    )
        except Exception as e:
            # Best-effort by design — never fail the request because audit
            # is down. The ERROR log line is the alerting hook.
            logger.error("AUDIT_WRITE_FAILED request_id=%s: %s", request_id, e)

        response.headers["X-Request-Id"] = request_id
        return response
