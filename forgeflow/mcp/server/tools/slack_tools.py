"""MCP tools: real Slack integration for posts + HITL notifications.

Thin wrappers over forgeflow.notifications.slack so the same code path is
used whether the call originates from an agent (via the MCP server) or
from the API (direct import).
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from forgeflow.notifications.slack import notify_approval_request, slack_post

logger = logging.getLogger(__name__)

router = FastMCP("slack-tools")


@router.tool()
async def slack_post_message(
    text: str,
    channel: str | None = None,
    blocks: list[dict] | None = None,
) -> dict:
    """Post a plain or block-formatted message to a Slack channel.

    Args:
        text: Fallback / notification text (required by Slack even when using blocks).
        channel: Target channel ('#forgeflow' or 'C0123456'). Falls back to settings.
        blocks: Optional Slack Block Kit blocks for rich formatting.

    Returns:
        {"ok": bool, "ts": str, "channel": str, "mock": bool, ...}
    """
    return await slack_post(text=text, channel=channel, blocks=blocks)


@router.tool()
async def slack_send_approval_card(
    approval_token: str,
    summary: str,
    payload: dict | None = None,
    channel: str | None = None,
) -> dict:
    """Send a HITL approval card with approve/reject deep-link buttons.

    Args:
        approval_token: The approval_requests.token UUID.
        summary: Human-readable description of what needs approval.
        payload: Optional dict shown as a JSON code block (proposal details, etc.).
        channel: Target Slack channel. Falls back to SLACK_DEFAULT_CHANNEL.

    Returns:
        Same shape as slack_post_message.
    """
    return await notify_approval_request(
        approval_token=approval_token,
        summary=summary,
        payload=payload,
        channel=channel,
    )
