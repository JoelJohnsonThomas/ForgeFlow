"""RBAC middleware — checks X-Role header against route permission requirements.

Production note: Replace X-Role header extraction with JWT verification.
The enforcement logic (RBACEnforcer) is the same either way.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from forgeflow.rbac.enforcer import RBACEnforcer
from forgeflow.rbac.policies import ROUTE_PERMISSION_MAP

logger = logging.getLogger(__name__)

# Routes that bypass RBAC (health checks, docs)
_OPEN_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, enforcer: RBACEnforcer | None = None) -> None:
        super().__init__(app)
        self.enforcer = enforcer or RBACEnforcer()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method

        # Skip open endpoints
        if path in _OPEN_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        # Extract simulated identity from headers
        user_id = request.headers.get("X-User-Id", "anonymous")
        role = request.headers.get("X-Role", "viewer")
        request_id = request.headers.get("X-Request-Id", "")

        # Store in request state for downstream use
        request.state.user_id = user_id
        request.state.role = role
        request.state.request_id = request_id

        # Find required permission for this route
        action, resource = self._resolve_permission(method, path)
        if action and not self.enforcer.check(role, action, resource):
            logger.warning(
                "RBAC denied: user=%s role=%s action=%s resource=%s path=%s",
                user_id,
                role,
                action,
                resource,
                path,
            )
            return JSONResponse(
                {"error": "Forbidden", "detail": f"Role '{role}' cannot {action} {resource}"},
                status_code=403,
            )

        return await call_next(request)

    def _resolve_permission(self, method: str, path: str) -> tuple[str, str]:
        """Map a request to its required (action, resource) pair."""
        for (route_method, route_prefix), (action, resource) in ROUTE_PERMISSION_MAP.items():
            if method == route_method and path.startswith(route_prefix):
                return action, resource
        return "", ""  # No restriction found
