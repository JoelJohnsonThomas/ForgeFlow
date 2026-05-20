"""RBAC middleware — JWT bearer auth with X-Role header fallback for dev.

Identity resolution order, first match wins:
  1. Authorization: Bearer <JWT> — verified via forgeflow.auth.jwt.decode_access_token
  2. X-User-Id + X-Role headers — legacy dev path, removed once all clients migrate

Either path sets request.state.user_id / .role / .workspace_id, then the
RBACEnforcer checks the route permission. JWT-decoded values supersede any
forged headers, so a deployed system can drop the X-Role path safely.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from forgeflow.auth.jwt import JWTError, decode_access_token
from forgeflow.config import get_settings
from forgeflow.rbac.enforcer import RBACEnforcer
from forgeflow.rbac.policies import ROUTE_PERMISSION_MAP

logger = logging.getLogger(__name__)

# Routes that bypass RBAC (health checks, docs, auth itself)
_OPEN_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
_OPEN_PREFIXES = ("/auth/",)


class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, enforcer: RBACEnforcer | None = None) -> None:
        super().__init__(app)
        self.enforcer = enforcer or RBACEnforcer()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method

        # Skip open endpoints
        if (
            path in _OPEN_PATHS
            or path.startswith("/docs")
            or path.startswith("/openapi")
            or any(path.startswith(p) for p in _OPEN_PREFIXES)
        ):
            return await call_next(request)

        # 1. Try JWT bearer
        user_id, role, workspace_id, jwt_error = self._extract_from_jwt(request)

        # 2. Fall back to legacy headers if no JWT was provided (not on failure)
        if user_id is None and jwt_error is None:
            user_id = request.headers.get("X-User-Id", "anonymous")
            role = request.headers.get("X-Role", "viewer")
            workspace_id = request.headers.get("X-Workspace-Id")

        # 3. If a JWT was provided but failed, reject the request
        if jwt_error is not None:
            return JSONResponse(
                {"error": "Unauthorized", "detail": jwt_error},
                status_code=401,
            )

        request.state.user_id = user_id
        request.state.role = role
        request.state.workspace_id = workspace_id
        request.state.request_id = request.headers.get("X-Request-Id", "")

        # Permission check
        action, resource = self._resolve_permission(method, path)
        if action and not self.enforcer.check(role or "viewer", action, resource):
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

    def _extract_from_jwt(
        self, request: Request
    ) -> tuple[str | None, str | None, str | None, str | None]:
        """Return (user_id, role, workspace_id, error). All None if no Bearer header."""
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return None, None, None, None

        token = auth.split(" ", 1)[1].strip()
        if not token:
            return None, None, None, "missing token after 'Bearer'"

        # Allow the API secret to act as a wildcard for service-to-service
        # calls (CI, scheduled jobs). Same shape as JWT — just a literal match.
        settings = get_settings()
        if token == settings.api_secret_key.get_secret_value():
            return "service", "admin", None, None

        try:
            claims = decode_access_token(token)
        except JWTError as exc:
            return None, None, None, str(exc)

        return (
            str(claims.get("sub", "")),
            str(claims.get("role", "viewer")),
            claims.get("workspace"),
            None,
        )

    def _resolve_permission(self, method: str, path: str) -> tuple[str, str]:
        """Map a request to its required (action, resource) pair."""
        for (route_method, route_prefix), (action, resource) in ROUTE_PERMISSION_MAP.items():
            if method == route_method and path.startswith(route_prefix):
                return action, resource
        return "", ""  # No restriction found
