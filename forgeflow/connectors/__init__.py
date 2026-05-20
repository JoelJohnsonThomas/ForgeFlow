"""Real third-party connectors — replaces the mock CRM/email tools from Phase 0.

Each connector follows the same shape:
  - A `Client` class wrapping the vendor REST API via httpx
  - Graceful degradation when credentials are absent (returns mock dicts,
    logs a warning, never raises)
  - Exposed to agents through `forgeflow/mcp/server/tools/<name>_tools.py`
  - All settings live under settings.<vendor>_* in forgeflow/config.py

Authentication note: connectors currently take a single API token from
settings. For multi-tenant SaaS the per-workspace OAuth path is tracked
as a Phase 5 deployment item (see ROADMAP.md).
"""

from forgeflow.connectors.base import (
    BaseConnector,
    ConnectorDisabled,
    ConnectorError,
    mock_response,
)

__all__ = ["BaseConnector", "ConnectorDisabled", "ConnectorError", "mock_response"]
