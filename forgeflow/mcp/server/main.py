"""ForgeFlow MCP Tool Server — FastMCP with HTTP and stdio transport modes.

Usage:
  HTTP (production):  python -m forgeflow.mcp.server.main http
  stdio (local CLI):  python -m forgeflow.mcp.server.main stdio

The HTTP transport exposes tools at POST /mcp (streamable-HTTP per MCP spec).
Agents connect via the client adapter in forgeflow/mcp/client/adapter.py.
"""

from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP

from forgeflow.config import get_settings
from forgeflow.mcp.server.tools import (
    crm_tools,
    data_tools,
    email_tools,
    github_tools,
    hubspot_tools,
    jira_tools,
    msgraph_tools,
    multimodal_tools,
    quickbooks_tools,
    salesforce_tools,
    sap_tools,
    search_tools,
    servicenow_tools,
    slack_tools,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Main MCP server — compose all tool sub-routers
mcp = FastMCP(
    name="ForgeFlow Tool Server",
    version="1.0.0",
    instructions=(
        "This server exposes enterprise tools for ForgeFlow agents: "
        "web search, CRM management, email sending, and data enrichment."
    ),
)

mcp.mount(search_tools.router, prefix="search")
mcp.mount(crm_tools.router, prefix="crm")
mcp.mount(email_tools.router, prefix="email")
mcp.mount(data_tools.router, prefix="data")
mcp.mount(slack_tools.router, prefix="slack")
mcp.mount(github_tools.router, prefix="github")
mcp.mount(jira_tools.router, prefix="jira")
mcp.mount(hubspot_tools.router, prefix="hubspot")
mcp.mount(salesforce_tools.router, prefix="salesforce")
mcp.mount(servicenow_tools.router, prefix="servicenow")
mcp.mount(sap_tools.router, prefix="sap")
mcp.mount(quickbooks_tools.router, prefix="quickbooks")
mcp.mount(msgraph_tools.router, prefix="msgraph")
mcp.mount(multimodal_tools.router, prefix="multimodal")


if __name__ == "__main__":
    settings = get_settings()
    mode = sys.argv[1] if len(sys.argv) > 1 else "http"

    if mode == "stdio":
        logger.info("Starting MCP server in stdio mode")
        mcp.run(transport="stdio")
    else:
        logger.info(
            "Starting MCP server in HTTP mode on %s:%d",
            settings.mcp_server_host,
            settings.mcp_server_port,
        )
        mcp.run(
            transport="streamable-http",
            host=settings.mcp_server_host,
            port=settings.mcp_server_port,
        )
