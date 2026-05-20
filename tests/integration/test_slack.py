"""Tests for the Slack notification helper.

We verify two paths:
  - graceful degradation when SLACK_BOT_TOKEN is unset (returns mock=True)
  - block-kit payload shape for an approval card (sent to a fake WebClient)
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.notifications.slack import notify_approval_request, slack_post


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_post_without_token_returns_mock(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "")
        get_settings.cache_clear()

        result = await slack_post("hello world")
        assert result["mock"] is True
        assert result["ok"] is True
        assert result["ts"].startswith("mock-")

    @pytest.mark.asyncio
    async def test_post_with_non_bot_token_returns_mock(self, monkeypatch):
        # Slack bot tokens must start with 'xoxb-'; anything else is rejected
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxp-user-token")
        get_settings.cache_clear()

        result = await slack_post("hello", channel="#x")
        assert result["mock"] is True

    @pytest.mark.asyncio
    async def test_approval_request_without_token_returns_mock(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "")
        get_settings.cache_clear()

        result = await notify_approval_request(
            approval_token="abc-123",
            summary="Approve proposal for Acme",
        )
        assert result["mock"] is True


class TestRealSlackPath:
    @pytest.mark.asyncio
    async def test_post_calls_chat_postmessage(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
        monkeypatch.setenv("SLACK_DEFAULT_CHANNEL", "#forgeflow")
        get_settings.cache_clear()

        fake_response = {"ok": True, "ts": "1234567890.123456", "channel": "C123"}
        fake_client = MagicMock()
        fake_client.chat_postMessage = MagicMock(return_value=fake_response)
        fake_module = MagicMock()
        fake_module.WebClient = MagicMock(return_value=fake_client)

        with patch.dict(sys.modules, {"slack_sdk": fake_module}):
            result = await slack_post("hello", channel="#forgeflow")

        assert result["mock"] is False
        assert result["ok"] is True
        assert result["ts"] == "1234567890.123456"
        fake_client.chat_postMessage.assert_called_once_with(
            channel="#forgeflow",
            text="hello",
            blocks=None,
        )

    @pytest.mark.asyncio
    async def test_approval_card_includes_approve_reject_buttons(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
        monkeypatch.setenv("SLACK_DEFAULT_CHANNEL", "#forgeflow")
        monkeypatch.setenv("API_PUBLIC_URL", "https://example.com")
        get_settings.cache_clear()

        fake_response = {"ok": True, "ts": "999.1", "channel": "C123"}
        fake_client = MagicMock()
        fake_client.chat_postMessage = MagicMock(return_value=fake_response)
        fake_module = MagicMock()
        fake_module.WebClient = MagicMock(return_value=fake_client)

        with patch.dict(sys.modules, {"slack_sdk": fake_module}):
            await notify_approval_request(
                approval_token="tok-42",
                summary="Approve Acme proposal",
                payload={"deal_value": 50_000},
            )

        kwargs = fake_client.chat_postMessage.call_args.kwargs
        blocks = kwargs["blocks"]
        assert any(b["type"] == "actions" for b in blocks)
        action_block = next(b for b in blocks if b["type"] == "actions")
        button_urls = [el["url"] for el in action_block["elements"]]
        assert "https://example.com/approvals/tok-42/approve" in button_urls
        assert "https://example.com/approvals/tok-42/reject" in button_urls

    @pytest.mark.asyncio
    async def test_post_failure_returns_error(self, monkeypatch):
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
        get_settings.cache_clear()

        fake_client = MagicMock()
        fake_client.chat_postMessage = MagicMock(side_effect=RuntimeError("boom"))
        fake_module = MagicMock()
        fake_module.WebClient = MagicMock(return_value=fake_client)

        with patch.dict(sys.modules, {"slack_sdk": fake_module}):
            result = await slack_post("hello", channel="#x")

        assert result["ok"] is False
        assert "boom" in result["error"]
