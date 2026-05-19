"""MCP client adapter — converts MCP server tools to LangChain BaseTool instances.

The adapter connects to the MCP HTTP server and returns a list of LangChain-
compatible tools that can be passed to BaseAgent (and bound to ChatOpenAI).

Falls back to an empty list if the MCP server is unavailable, so agents still
run in degraded mode (useful for testing without the server running).
"""

from __future__ import annotations

import logging

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)


async def get_mcp_tools() -> list:
    """Connect to the MCP server and return LangChain-compatible tools.

    Returns empty list on connection failure (graceful degradation).
    """
    settings = get_settings()
    mcp_url = f"http://{settings.mcp_server_host}:{settings.mcp_server_port}/mcp"

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(
            {
                "forgeflow": {
                    "url": mcp_url,
                    "transport": "streamable_http",
                }
            }
        )
        tools = await client.get_tools()
        logger.info("Loaded %d tools from MCP server at %s", len(tools), mcp_url)
        return tools

    except ImportError:
        logger.warning("langchain-mcp-adapters not installed — using empty tool list")
        return []
    except Exception as e:
        logger.warning(
            "MCP server at %s unavailable (%s) — running without external tools",
            mcp_url,
            e,
        )
        return []
