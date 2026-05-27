"""Base connector — graceful-degradation API client wrapper.

Every real connector inherits from BaseConnector. The contract:

  1. is_enabled() reads from settings; when False, every API method returns
     a mock_response dict instead of hitting the vendor. Lets dev/CI/demos
     proceed without real credentials.
  2. Subclasses implement vendor-specific methods on top of _request().
  3. _request() now includes retry-with-backoff for transient failures
     (429, 502, 503, 504, transport errors). Permanent errors (other 4xx)
     fail fast.
  4. RetryableError vs PermanentError lets agent code branch on what
     can be re-driven by the workflow vs what needs human attention.

The MCP tool wrappers in forgeflow/mcp/server/tools/<vendor>_tools.py
delegate to a connector instance — no API-client code lives in the tool
modules themselves.
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default retry policy for transient failures. Override per-connector via
# the class-level constants if a vendor publishes different guidance.
_RETRYABLE_STATUS = frozenset({429, 502, 503, 504})
_MAX_ATTEMPTS = 4
_BASE_BACKOFF_S = 0.5
_MAX_BACKOFF_S = 16.0


class ConnectorError(RuntimeError):
    """Vendor returned an error; details are in .status_code + .body."""

    def __init__(self, status_code: int, body: Any, vendor: str) -> None:
        super().__init__(f"{vendor} returned {status_code}: {body}")
        self.status_code = status_code
        self.body = body
        self.vendor = vendor


class RetryableError(ConnectorError):
    """Transient failure — workflow can re-drive the call. 429, 503, etc."""


class PermanentError(ConnectorError):
    """Caller should not retry — auth, validation, or a deleted resource."""


class ConnectorDisabled(RuntimeError):
    """The connector is disabled because credentials are missing. Callers
    typically use is_enabled() to branch instead of catching this."""


def mock_response(vendor: str, operation: str, **fields: Any) -> dict:
    """Return a stub response shaped like a successful vendor reply.

    Every mock dict carries ``{"mock": True, "vendor": ..., "operation": ...,
    "mock_id": "<uuid>"}`` so callers can identify simulated calls in logs.
    """
    return {
        "mock": True,
        "vendor": vendor,
        "operation": operation,
        "mock_id": str(uuid.uuid4()),
        **fields,
    }


def _backoff_seconds(attempt: int, retry_after: float | None) -> float:
    """Respect Retry-After when present; otherwise exponential + jitter."""
    if retry_after is not None and retry_after > 0:
        return min(retry_after, _MAX_BACKOFF_S)
    raw = min(_BASE_BACKOFF_S * (2 ** (attempt - 1)), _MAX_BACKOFF_S)
    # Full-jitter — recommended by AWS Architecture Blog. Avoids thundering herd.
    return random.uniform(0, raw)


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None  # HTTP-date form is rare in practice; ignore for now


class BaseConnector:
    """Shared HTTP plumbing — child classes set base_url + auth_header().

    Subclass-tunable retry policy:
      retryable_status  — set of HTTP status codes that trigger retry
      max_attempts      — total attempts including the first
      base_backoff_s    — first backoff before jitter
    """

    vendor: str = "base"  # overridden by subclasses
    timeout_seconds: float = 30.0
    retryable_status: frozenset[int] = _RETRYABLE_STATUS
    max_attempts: int = _MAX_ATTEMPTS

    def __init__(self, base_url: str, token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token or ""

    def is_enabled(self) -> bool:
        """Return True when the connector has credentials to talk to the vendor."""
        return bool(self._token)

    def auth_header(self) -> dict[str, str]:
        """Default Bearer scheme. Override for Basic, OAuth, custom, etc."""
        return {"Authorization": f"Bearer {self._token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        extra_headers: dict | None = None,
    ) -> dict:
        """Run one HTTP request with retry-with-backoff. Returns parsed JSON.

        Raises:
          PermanentError on non-retryable 4xx (caller's responsibility to fix).
          RetryableError on transient failures that exhausted retries.

        Mocks the response when is_enabled() is False.
        """
        if not self.is_enabled():
            return mock_response(
                self.vendor,
                f"{method} {path}",
                params=params or {},
                json=json or {},
            )

        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json", **self.auth_header()}
        if extra_headers:
            headers.update(extra_headers)

        # SSRF guard — vendor base_urls are config-controlled, but `path`
        # is sometimes built from LLM/agent input (issue numbers, repo
        # slugs, …). Re-validate every outbound URL.
        try:
            from forgeflow.security.ssrf_guard import SSRFBlocked, check_url

            check_url(url)
        except SSRFBlocked as exc:
            logger.warning("SSRF-blocked %s call to %s: %s", self.vendor, url, exc)
            raise PermanentError(0, f"SSRF block: {exc}", self.vendor) from exc

        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds, follow_redirects=False
                ) as client:
                    response = await client.request(
                        method, url, params=params, json=json, headers=headers
                    )
            except httpx.HTTPError as exc:
                # Transport error — always retry (covers connect/read timeouts)
                last_exc = exc
                if attempt < self.max_attempts:
                    sleep_s = _backoff_seconds(attempt, None)
                    logger.warning(
                        "%s transport error to %s (attempt %d/%d): %s — retrying in %.2fs",
                        self.vendor, url, attempt, self.max_attempts, exc, sleep_s,
                    )
                    await asyncio.sleep(sleep_s)
                    continue
                logger.exception("%s transport error to %s after %d attempts", self.vendor, url, attempt)
                raise RetryableError(0, str(exc), self.vendor) from exc

            if response.status_code < 400:
                if not response.content:
                    return {}
                try:
                    return response.json()
                except ValueError:
                    return {"raw": response.text}

            # Parse body for the error path
            try:
                body = response.json()
            except ValueError:
                body = response.text

            if response.status_code in self.retryable_status and attempt < self.max_attempts:
                retry_after = _parse_retry_after(response.headers.get("retry-after"))
                sleep_s = _backoff_seconds(attempt, retry_after)
                logger.warning(
                    "%s returned %d for %s %s (attempt %d/%d, retry-after=%s) — retrying in %.2fs",
                    self.vendor, response.status_code, method, path,
                    attempt, self.max_attempts, retry_after, sleep_s,
                )
                await asyncio.sleep(sleep_s)
                continue

            # Final disposition
            if response.status_code in self.retryable_status:
                logger.warning(
                    "%s returned %d for %s %s — retries exhausted: %s",
                    self.vendor, response.status_code, method, path, body,
                )
                raise RetryableError(response.status_code, body, self.vendor)

            logger.warning(
                "%s returned %d for %s %s: %s",
                self.vendor, response.status_code, method, path, body,
            )
            raise PermanentError(response.status_code, body, self.vendor)

        # Defensive — loop always returns or raises above.
        assert last_exc is not None
        raise RetryableError(0, str(last_exc), self.vendor) from last_exc
