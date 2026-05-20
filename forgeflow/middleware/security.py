"""SecurityMiddleware — PII redaction + prompt-injection guard at the API edge.

Runs on every JSON POST request:
  1. Parse the body, walk the JSON tree, scan every string leaf.
  2. If any leaf scores RiskLevel.HIGH on the prompt guard → return 400.
  3. Replace PII matches in-place with [REDACTED:<category>] tokens.
  4. Repack the redacted body and pass it on. Downstream handlers never see raw PII.

Skipped paths: /health, /docs, /openapi.json, /metrics/prometheus. These are
read-only or platform endpoints and don't carry user content.

The middleware is intentionally side-effect-light: it logs PII categories
seen (not values) and the prompt-guard reasons, but does not call the
audit_log table directly — that's the responsibility of AuditMiddleware
which runs later in the chain.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from forgeflow.security.pii_redactor import redact
from forgeflow.security.prompt_guard import RiskLevel, scan_prompt

logger = logging.getLogger(__name__)

_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
_SKIP_PREFIXES = ("/metrics",)


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self._should_skip(request):
            return await call_next(request)

        if request.method.upper() not in {"POST", "PUT", "PATCH"}:
            return await call_next(request)

        raw_body = await request.body()
        if not raw_body:
            return await call_next(request)

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Not JSON — pass through untouched (file uploads, form data, etc.)
            return await call_next(request)

        # Scan + redact recursively
        try:
            sanitized, pii_categories, high_risk_reasons = _walk(payload)
        except Exception:
            logger.exception("SecurityMiddleware scan failed; passing through")
            return await call_next(request)

        if high_risk_reasons:
            logger.warning(
                "Blocked high-risk prompt | path=%s reasons=%s",
                request.url.path,
                high_risk_reasons,
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "request_blocked",
                    "detail": "Prompt injection detected. Rephrase your request.",
                    "reasons": high_risk_reasons,
                },
            )

        if pii_categories:
            logger.info(
                "PII redacted | path=%s categories=%s",
                request.url.path,
                sorted(set(pii_categories)),
            )

        # Replace the body in the request so downstream handlers see the sanitized version.
        new_body = json.dumps(sanitized).encode("utf-8")
        request._body = new_body  # noqa: SLF001  Starlette caches body here

        return await call_next(request)

    def _should_skip(self, request: Request) -> bool:
        path = request.url.path
        if path in _SKIP_PATHS:
            return True
        return any(path.startswith(p) for p in _SKIP_PREFIXES)


def _walk(value: Any) -> tuple[Any, list[str], list[str]]:
    """Recursively scan and redact strings inside a JSON-like structure.

    Returns ``(redacted_value, pii_categories_seen, high_risk_reasons)``.
    """
    pii: list[str] = []
    risks: list[str] = []

    if isinstance(value, str):
        score = scan_prompt(value)
        if score.level == RiskLevel.HIGH:
            risks.extend(score.reasons)
        redacted, matches = redact(value)
        pii.extend(m.category for m in matches)
        return redacted, pii, risks

    if isinstance(value, list):
        out_list: list[Any] = []
        for item in value:
            new_item, sub_pii, sub_risks = _walk(item)
            out_list.append(new_item)
            pii.extend(sub_pii)
            risks.extend(sub_risks)
        return out_list, pii, risks

    if isinstance(value, dict):
        out_dict: dict[Any, Any] = {}
        for k, v in value.items():
            new_v, sub_pii, sub_risks = _walk(v)
            out_dict[k] = new_v
            pii.extend(sub_pii)
            risks.extend(sub_risks)
        return out_dict, pii, risks

    # int, float, bool, None — pass through untouched
    return value, pii, risks
