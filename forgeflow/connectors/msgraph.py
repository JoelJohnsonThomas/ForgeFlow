"""Microsoft Graph connector — Teams messages, Outlook email, calendar.

Graph is the unified API across Teams, Outlook, OneDrive, SharePoint,
Calendar, etc. Auth is OAuth 2.0 against Azure AD; this connector takes
the resulting access token (acquired externally via MSAL or client
credentials flow).

Required Graph permissions per operation:
  - Teams channel post  -> ChannelMessage.Send (delegated) or
                           Teamwork.Migrate.All (app)
  - Send Outlook mail   -> Mail.Send
  - Read Outlook mail   -> Mail.Read
  - Calendar events     -> Calendars.ReadWrite

Pairs with: HITL approval notifications (Teams alternative to Slack),
plus email-based workflows in support_ops / sales_ops.

Settings:
  MSGRAPH_ACCESS_TOKEN  — Azure AD OAuth bearer token
  MSGRAPH_TENANT_ID     — Azure AD tenant (used for token refresh — store-only)
  MSGRAPH_BASE_URL      — defaults to https://graph.microsoft.com/v1.0
"""

from __future__ import annotations

import logging
from typing import Any

from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class MSGraphConnector(BaseConnector):
    vendor = "msgraph"

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
    ) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.msgraph_base_url,
            token=(
                token
                if token is not None
                else settings.msgraph_access_token.get_secret_value()
            ),
        )

    # ---- Teams ----

    async def post_teams_channel_message(
        self,
        team_id: str,
        channel_id: str,
        text: str,
        content_type: str = "html",
    ) -> dict:
        """Post a message to a Teams channel.

        content_type: 'text' (plain) or 'html' (allows formatting + @mentions).
        """
        return await self._request(
            "POST",
            f"/teams/{team_id}/channels/{channel_id}/messages",
            json={"body": {"content": text, "contentType": content_type}},
        )

    async def post_teams_chat_message(
        self, chat_id: str, text: str, content_type: str = "html"
    ) -> dict:
        """Post a message to a 1:1 or group chat (not a channel)."""
        return await self._request(
            "POST",
            f"/chats/{chat_id}/messages",
            json={"body": {"content": text, "contentType": content_type}},
        )

    async def post_teams_adaptive_card(
        self,
        team_id: str,
        channel_id: str,
        card: dict[str, Any],
    ) -> dict:
        """Post an Adaptive Card to a Teams channel — used for HITL approval cards
        with approve/reject action buttons.

        The card argument is the full Adaptive Card JSON; this method handles the
        Graph-required wrapping under attachments[0].content.
        """
        attachment_id = "1"  # any unique-within-this-message id
        body_html = (
            f'<attachment id="{attachment_id}"></attachment>'
        )
        payload = {
            "body": {"contentType": "html", "content": body_html},
            "attachments": [
                {
                    "id": attachment_id,
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                }
            ],
        }
        return await self._request(
            "POST",
            f"/teams/{team_id}/channels/{channel_id}/messages",
            json=payload,
        )

    # ---- Outlook ----

    async def send_mail(
        self,
        user_id: str,
        to_recipients: list[str],
        subject: str,
        body: str,
        body_type: str = "html",
        cc_recipients: list[str] | None = None,
        save_to_sent: bool = True,
    ) -> dict:
        """Send an email as user_id (use 'me' for the delegated path).

        Returns {} on success (Graph returns 202 Accepted with no body).
        """
        message: dict[str, Any] = {
            "subject": subject,
            "body": {"contentType": body_type, "content": body},
            "toRecipients": [
                {"emailAddress": {"address": addr}} for addr in to_recipients
            ],
        }
        if cc_recipients:
            message["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc_recipients
            ]

        return await self._request(
            "POST",
            f"/users/{user_id}/sendMail",
            json={"message": message, "saveToSentItems": save_to_sent},
        )

    async def list_messages(
        self,
        user_id: str,
        top: int = 25,
        filter_expr: str | None = None,
        select: str | None = None,
    ) -> dict:
        """List Outlook messages for a user. Uses OData query options."""
        params: dict[str, Any] = {"$top": top}
        if filter_expr:
            params["$filter"] = filter_expr
        if select:
            params["$select"] = select
        return await self._request(
            "GET", f"/users/{user_id}/messages", params=params
        )

    # ---- Calendar ----

    async def create_calendar_event(
        self,
        user_id: str,
        subject: str,
        start_iso: str,
        end_iso: str,
        attendees: list[str] | None = None,
        body: str = "",
        is_online_meeting: bool = False,
    ) -> dict:
        """Create a calendar event with optional Teams meeting link."""
        event: dict[str, Any] = {
            "subject": subject,
            "start": {"dateTime": start_iso, "timeZone": "UTC"},
            "end": {"dateTime": end_iso, "timeZone": "UTC"},
            "body": {"contentType": "html", "content": body},
        }
        if attendees:
            event["attendees"] = [
                {
                    "emailAddress": {"address": addr},
                    "type": "required",
                }
                for addr in attendees
            ]
        if is_online_meeting:
            event["isOnlineMeeting"] = True
            event["onlineMeetingProvider"] = "teamsForBusiness"

        return await self._request(
            "POST", f"/users/{user_id}/events", json=event
        )

    # ---- User lookups (handy for resolving emails to userIds) ----

    async def get_user(self, user_id_or_upn: str) -> dict:
        """Fetch a user by Azure AD object ID, UPN, or email."""
        return await self._request("GET", f"/users/{user_id_or_upn}")
