"""Tests for the Microsoft Graph connector — Teams, Outlook, Calendar."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.connectors.msgraph import MSGraphConnector


@pytest.fixture(autouse=True)
def _reset():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _captured(payload: dict, status: int = 200):
    captured: list[dict] = []

    fake_response = MagicMock()
    fake_response.status_code = status
    fake_response.content = b'{}'
    fake_response.json = MagicMock(return_value=payload)

    async def _request(method, url, params=None, json=None, headers=None):
        captured.append({"method": method, "url": url, "params": params, "json": json})
        return fake_response

    fake_client = MagicMock()
    fake_client.request = AsyncMock(side_effect=_request)
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=fake_client)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    return lambda *a, **kw: fake_cm, captured


class TestDisabled:
    @pytest.mark.asyncio
    async def test_no_token_returns_mock(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_ACCESS_TOKEN", "")
        get_settings.cache_clear()
        result = await MSGraphConnector().post_teams_channel_message("t", "c", "hi")
        assert result["mock"] is True
        assert result["vendor"] == "msgraph"


class TestTeamsChannelMessage:
    @pytest.mark.asyncio
    async def test_url_and_body_shape(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()

        factory, captured = _captured({"id": "msg-1"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await MSGraphConnector().post_teams_channel_message(
                team_id="team-123",
                channel_id="chan-456",
                text="<b>hello</b>",
                content_type="html",
            )

        assert captured[0]["url"].endswith("/teams/team-123/channels/chan-456/messages")
        assert captured[0]["json"] == {
            "body": {"content": "<b>hello</b>", "contentType": "html"}
        }


class TestTeamsAdaptiveCard:
    @pytest.mark.asyncio
    async def test_card_wrapped_in_attachment_with_html_pointer(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()

        factory, captured = _captured({"id": "msg-1"})

        card = {
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [{"type": "TextBlock", "text": "Approval needed"}],
            "actions": [
                {"type": "Action.OpenUrl", "title": "Approve", "url": "https://x/approve"}
            ],
        }

        with patch("httpx.AsyncClient", side_effect=factory):
            await MSGraphConnector().post_teams_adaptive_card(
                team_id="t", channel_id="c", card=card
            )

        body = captured[0]["json"]
        # Graph requires HTML body that references the attachment id
        assert body["body"]["contentType"] == "html"
        assert '<attachment id="1">' in body["body"]["content"]
        # Card lives in attachments[0].content
        assert body["attachments"][0]["contentType"] == "application/vnd.microsoft.card.adaptive"
        assert body["attachments"][0]["content"] == card


class TestSendMail:
    @pytest.mark.asyncio
    async def test_recipients_wrapped_correctly(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()

        factory, captured = _captured({})

        with patch("httpx.AsyncClient", side_effect=factory):
            await MSGraphConnector().send_mail(
                user_id="me",
                to_recipients=["a@x.com", "b@x.com"],
                subject="Hello",
                body="<p>hi</p>",
                cc_recipients=["c@x.com"],
            )

        assert captured[0]["url"].endswith("/users/me/sendMail")
        msg = captured[0]["json"]["message"]
        assert msg["subject"] == "Hello"
        assert msg["body"] == {"contentType": "html", "content": "<p>hi</p>"}
        assert msg["toRecipients"] == [
            {"emailAddress": {"address": "a@x.com"}},
            {"emailAddress": {"address": "b@x.com"}},
        ]
        assert msg["ccRecipients"] == [{"emailAddress": {"address": "c@x.com"}}]
        assert captured[0]["json"]["saveToSentItems"] is True


class TestListMessages:
    @pytest.mark.asyncio
    async def test_odata_query_options_passthrough(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()

        factory, captured = _captured({"value": []})

        with patch("httpx.AsyncClient", side_effect=factory):
            await MSGraphConnector().list_messages(
                user_id="me",
                top=10,
                filter_expr="isRead eq false",
                select="subject,from,receivedDateTime",
            )

        params = captured[0]["params"]
        assert params["$top"] == 10
        assert params["$filter"] == "isRead eq false"
        assert params["$select"] == "subject,from,receivedDateTime"


class TestCalendar:
    @pytest.mark.asyncio
    async def test_event_with_online_meeting(self, monkeypatch):
        monkeypatch.setenv("MSGRAPH_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()

        factory, captured = _captured({"id": "evt-1"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await MSGraphConnector().create_calendar_event(
                user_id="me",
                subject="Sync",
                start_iso="2026-06-01T15:00:00",
                end_iso="2026-06-01T15:30:00",
                attendees=["alice@example.com"],
                is_online_meeting=True,
            )

        body = captured[0]["json"]
        assert body["subject"] == "Sync"
        assert body["start"] == {"dateTime": "2026-06-01T15:00:00", "timeZone": "UTC"}
        assert body["isOnlineMeeting"] is True
        assert body["onlineMeetingProvider"] == "teamsForBusiness"
        assert body["attendees"][0]["emailAddress"]["address"] == "alice@example.com"
        assert body["attendees"][0]["type"] == "required"
