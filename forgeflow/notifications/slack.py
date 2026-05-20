"""Slack notification helpers — shared by MCP tools and API approval handler.

Both call paths route through the same gate:
  1. If SLACK_BOT_TOKEN is unset or slack_sdk is not installed -> log + return mock.
  2. Otherwise wrap the sync slack_sdk.WebClient in asyncio.to_thread.

The API uses this directly (skipping the MCP roundtrip) when creating
approval_requests rows so the channel notification fires synchronously
with the database insert.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)


def _client() -> Any | None:
    settings = get_settings()
    if not settings.is_slack_enabled():
        return None
    try:
        from slack_sdk import WebClient
    except ImportError:
        logger.warning("slack_sdk not installed; install with: pip install slack-sdk")
        return None
    return WebClient(token=settings.slack_bot_token.get_secret_value())


def _channel(channel: str | None) -> str:
    if channel:
        return channel
    return get_settings().slack_default_channel or "#forgeflow"


async def slack_post(
    text: str,
    channel: str | None = None,
    blocks: list[dict] | None = None,
) -> dict:
    """Post a message to Slack. Returns a result dict with `ok`, `ts`, `mock` keys."""
    target = _channel(channel)
    client = _client()

    if client is None:
        logger.info("Slack disabled — would post to %s: %s", target, text[:80])
        return {
            "ok": True,
            "mock": True,
            "ts": f"mock-{uuid.uuid4().hex[:12]}",
            "channel": target,
        }

    try:
        response = await asyncio.to_thread(
            client.chat_postMessage,
            channel=target,
            text=text,
            blocks=blocks,
        )
        return {
            "ok": bool(response.get("ok")),
            "mock": False,
            "ts": response.get("ts", ""),
            "channel": response.get("channel", target),
        }
    except Exception as exc:
        logger.exception("Slack post failed")
        return {"ok": False, "mock": False, "ts": "", "channel": target, "error": str(exc)}


async def notify_approval_request(
    approval_token: str,
    summary: str,
    payload: dict | None = None,
    channel: str | None = None,
) -> dict:
    """Post a HITL approval request card to Slack with approve/reject deep-links."""
    settings = get_settings()
    base_url = settings.api_public_url.rstrip("/")
    approval_url = f"{base_url}/approvals/{approval_token}"

    blocks: list[dict] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*ForgeFlow approval needed*\n{summary}",
            },
        }
    ]

    if payload:
        import json as _json

        truncated = _json.dumps(payload, indent=2, default=str)[:2500]
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{truncated}```"},
            }
        )

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "style": "primary",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "url": f"{approval_url}/approve",
                },
                {
                    "type": "button",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "url": f"{approval_url}/reject",
                },
            ],
        }
    )

    return await slack_post(
        text=f"ForgeFlow approval needed: {summary}",
        channel=channel,
        blocks=blocks,
    )
