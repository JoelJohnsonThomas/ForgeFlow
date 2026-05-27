"""RBAC middleware — JWT bearer auth only (no legacy header fallback, no
wildcard service token).

Post-audit hardening (SECURITY_AUDIT.md C-2, C-3, API5):
  - The "Bearer == API_SECRET ⇒ admin" wildcard path is gone. Service-to-
    service calls must mint a real JWT (sub="service:<name>") just like a
    user.
  - The X-User-Id / X-Role / X-Workspace-Id legacy fallback is gone. Any
    deployment that still depends on it will fail closed at the middleware,
    which is the desired behavior.
  - Routes not present in ROUTE_PERMISSION_MAP are denied by default
    (`unmapped_route_default_deny`). Set DEV_LOGIN_ENABLED=true + an explicit
    open-list to opt routes out.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from forgeflow.auth.jwt import JWTError, decode_access_token
from forgeflow.rbac.enforcer import RBACEnforcer
from forgeflow.rbac.policies import ROUTE_PERMISSION_MAP

logger = logging.getLogger(__name__)

# Routes that bypass RBAC entirely. Kept short on purpose — every addition
# here is a potential public-internet exposure.
_OPEN_PATHS = {"/", "/health", "/openapi.json"}
_OPEN_PREFIXES = ("/auth/login", "/auth/introspect", "/auth/logout")
# /docs and /redoc are open ONLY when docs_enabled — handled inline so the
# admin can flip the toggle without redeploying middleware code.


class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, enforcer: RBACEnforcer | None = None) -> None:
        super().__init__(app)
        self.enforcer = enforcer or RBACEnforcer()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method

        if self._is_open(path):
            return await call_next(request)

        # 1. Verify JWT bearer
        token = _bearer(request)
        if not token:
            return _unauthorized("missing bearer token")

        try:
            claims = decode_access_token(token)
        except JWTError as exc:
            return _unauthorized(str(exc))

        user_id = str(claims.get("sub", ""))
        role = str(claims.get("role", "viewer"))
        workspace_id = claims.get("workspace")

        request.state.user_id = user_id
        request.state.role = role
        request.state.workspace_id = workspace_id
        # Stable request id used by AuditMiddleware + downstream handlers.
        request.state.request_id = request.headers.get("X-Request-Id", "")
        # Carry the jti so handlers can revoke their own token (logout).
        request.state.jti = claims.get("jti")

        # 2. Permission check — fail closed on unmapped routes.
        action, resource = self._resolve_permission(method, path)
        if not action:
            logger.warning(
                "RBAC denied (unmapped route): user=%s role=%s method=%s path=%s",
                user_id,
                role,
                method,
                path,
            )
            return JSONResponse(
                {"error": "Forbidden", "detail": "route not authorized"},
                status_code=403,
            )

        if not self.enforcer.check(role, action, resource):
            logger.warning(
                "RBAC denied: user=%s role=%s action=%s resource=%s path=%s",
                user_id,
                role,
                action,
                resource,
                path,
            )
            return JSONResponse(
                {
                    "error": "Forbidden",
                    "detail": f"Role '{role}' cannot {action} {resource}",
                },
                status_code=403,
            )

        return await call_next(request)

    @staticmethod
    def _is_open(path: str) -> bool:
        from forgeflow.config import get_settings

        if path in _OPEN_PATHS:
            return True
        if any(path.startswith(p) for p in _OPEN_PREFIXES):
            return True
        # /docs + /redoc + /openapi.json are gated by docs_enabled in prod.
        is_docs_path = path.startswith("/docs") or path.startswith("/redoc")
        return is_docs_path and get_settings().docs_enabled

    @staticmethod
    def _resolve_permission(method: str, path: str) -> tuple[str, str]:
        """Longest-prefix match so /workflows/{id}/trace can't fall through
        to the /workflows entry's coarser permission.
        """
        best: tuple[str, str] | None = None
        best_len = -1
        for (route_method, route_prefix), perm in ROUTE_PERMISSION_MAP.items():
            if (
                method == route_method
                and path.startswith(route_prefix)
                and len(route_prefix) > best_len
            ):
                best = perm
                best_len = len(route_prefix)
        return best or ("", "")


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    return token or None


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        {"error": "Unauthorized", "detail": detail},
        status_code=401,
    )
