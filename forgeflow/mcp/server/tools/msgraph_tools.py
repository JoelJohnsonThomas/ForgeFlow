"""MCP tools wrapping Microsoft Graph — Teams + Outlook + Calendar."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from forgeflow.connectors.msgraph import MSGraphConnector

logger = logging.getLogger(__name__)
router = FastMCP("msgraph-tools")


def _client() -> MSGraphConnector:
    return MSGraphConnector()


@router.tool()
async def msgraph_post_teams_message(
    team_id: str,
    channel_id: str,
    text: str,
    content_type: str = "html",
) -> dict:
    """Post a message to a Teams channel. content_type: 'text' or 'html'."""
    return await _client().post_teams_channel_message(
        team_id=team_id, channel_id=channel_id, text=text, content_type=content_type
    )


@router.tool()
async def msgraph_post_teams_chat(
    chat_id: str, text: str, content_type: str = "html"
) -> dict:
    """Post a message to a 1:1 or group chat (not a channel)."""
    return await _client().post_teams_chat_message(
        chat_id=chat_id, text=text, content_type=content_type
    )


@router.tool()
async def msgraph_post_adaptive_card(
    team_id: str, channel_id: str, card: dict[str, Any]
) -> dict:
    """Post an Adaptive Card to a Teams channel.

    Useful for HITL approval cards with approve/reject action buttons —
    Teams alternative to the Slack Block Kit cards in notifications/slack.py.
    """
    return await _client().post_teams_adaptive_card(
        team_id=team_id, channel_id=channel_id, card=card
    )


@router.tool()
async def msgraph_send_mail(
    user_id: str,
    to_recipients: list[str],
    subject: str,
    body: str,
    body_type: str = "html",
    cc_recipients: list[str] | None = None,
) -> dict:
    """Send an Outlook email as user_id (use 'me' for the delegated path)."""
    return await _client().send_mail(
        user_id=user_id,
        to_recipients=to_recipients,
        subject=subject,
        body=body,
        body_type=body_type,
        cc_recipients=cc_recipients,
    )


@router.tool()
async def msgraph_list_messages(
    user_id: str,
    top: int = 25,
    filter_expr: str | None = None,
    select: str | None = None,
) -> dict:
    """List Outlook messages for a user. filter_expr uses OData syntax."""
    return await _client().list_messages(
        user_id=user_id, top=top, filter_expr=filter_expr, select=select
    )


@router.tool()
async def msgraph_create_event(
    user_id: str,
    subject: str,
    start_iso: str,
    end_iso: str,
    attendees: list[str] | None = None,
    body: str = "",
    is_online_meeting: bool = False,
) -> dict:
    """Create a calendar event with optional Teams meeting link.

    Times are ISO-8601; timezone is UTC. attendees are email addresses.
    """
    return await _client().create_calendar_event(
        user_id=user_id,
        subject=subject,
        start_iso=start_iso,
        end_iso=end_iso,
        attendees=attendees,
        body=body,
        is_online_meeting=is_online_meeting,
    )


@router.tool()
async def msgraph_get_user(user_id_or_upn: str) -> dict:
    """Resolve a user by Azure AD object ID, UPN, or primary email."""
    return await _client().get_user(user_id_or_upn)
