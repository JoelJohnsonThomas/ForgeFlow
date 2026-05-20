"""Base connector — graceful-degradation API client wrapper.

Every real connector inherits from BaseConnector. The contract:

  1. is_enabled() reads from settings; when False, every API method returns
     a mock_response dict instead of hitting the vendor. This lets dev/CI
     runs and demos proceed without real credentials, and prevents a
     missing token from cascading into 500s.
  2. Subclasses implement _request() (one shared httpx call). Individual
     API methods become one-liners that build the URL + params.
  3. ConnectorError wraps vendor errors with a consistent shape so agent
     code can catch a single exception class.

The MCP tool wrappers in forgeflow/mcp/server/tools/<vendor>_tools.py
delegate to a connector instance — no API-client code lives in the tool
modules themselves.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ConnectorError(RuntimeError):
    """Vendor returned an error; details are in .status_code + .body."""

    def __init__(self, status_code: int, body: Any, vendor: str) -> None:
        super().__init__(f"{vendor} returned {status_code}: {body}")
        self.status_code = status_code
        self.body = body
        self.vendor = vendor


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


class BaseConnector:
    """Shared HTTP plumbing — child classes set base_url + auth_header()."""

    vendor: str = "base"  # overridden by subclasses
    timeout_seconds: float = 30.0

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
        """Run one HTTP request and return parsed JSON. Raises ConnectorError on 4xx/5xx.

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

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.request(
                    method, url, params=params, json=json, headers=headers
                )
        except httpx.HTTPError as exc:
            logger.exception("%s transport error to %s: %s", self.vendor, url, exc)
            raise ConnectorError(0, str(exc), self.vendor) from exc

        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = response.text
            logger.warning(
                "%s returned %d for %s %s: %s",
                self.vendor,
                response.status_code,
                method,
                path,
                body,
            )
            raise ConnectorError(response.status_code, body, self.vendor)

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}
