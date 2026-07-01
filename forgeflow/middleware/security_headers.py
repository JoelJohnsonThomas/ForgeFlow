"""SecurityHeadersMiddleware — defense-in-depth HTTP response headers.

Adds the standard hardening headers to every response (including error
responses from inner middlewares, since this runs outermost). A strict
Content-Security-Policy is applied to API responses; /docs and /redoc are
exempted from CSP because Swagger/ReDoc load assets + inline scripts from a
CDN and a strict policy would break the interactive docs.

These headers are cheap, universally recommended (OWASP Secure Headers), and
close a class of clickjacking / MIME-sniffing / referrer-leak issues.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# API responses are JSON and never embed third-party resources, so the tightest
# possible policy is correct here.
_STRICT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

_STATIC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    # Harmless over plain HTTP; enforced by browsers only over HTTPS.
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        headers = response.headers
        for key, value in _STATIC_HEADERS.items():
            headers.setdefault(key, value)

        path = request.url.path
        if not (path.startswith("/docs") or path.startswith("/redoc")):
            headers.setdefault("Content-Security-Policy", _STRICT_CSP)

        return response
