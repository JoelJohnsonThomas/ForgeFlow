"""Tests for the opt-in anonymous telemetry emitter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.telemetry.emitter import _ALLOWED_FIELDS, TelemetryEmitter


@pytest.fixture(autouse=True)
def _reset():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _fake_httpx_client():
    """Returns a fake httpx.AsyncClient context manager that records POSTs."""
    posts: list[dict] = []

    async def _post(url, json=None, headers=None):
        posts.append({"url": url, "json": json, "headers": headers})
        return MagicMock(status_code=200)

    client = MagicMock()
    client.post = AsyncMock(side_effect=_post)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm, posts


class TestOptIn:
    @pytest.mark.asyncio
    async def test_disabled_by_default_does_not_emit(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "false")
        get_settings.cache_clear()

        emitter = TelemetryEmitter.from_settings()
        assert emitter.enabled is False

        # Even calling emit with a webhook URL set does nothing when disabled
        fake_cm, posts = _fake_httpx_client()
        with patch("httpx.AsyncClient", return_value=fake_cm):
            await emitter.emit(event_name="workflow.started")

        assert posts == []

    @pytest.mark.asyncio
    async def test_enabled_without_webhook_does_not_emit(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("TELEMETRY_WEBHOOK_URL", "")
        get_settings.cache_clear()

        emitter = TelemetryEmitter.from_settings()
        assert emitter.enabled is False

        fake_cm, posts = _fake_httpx_client()
        with patch("httpx.AsyncClient", return_value=fake_cm):
            await emitter.emit(event_name="workflow.started")
        assert posts == []


class TestPIIBoundary:
    @pytest.mark.asyncio
    async def test_only_allowlisted_fields_are_sent(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("TELEMETRY_WEBHOOK_URL", "https://t.example/ingest")
        get_settings.cache_clear()

        emitter = TelemetryEmitter.from_settings()
        emitter.install_id = "install-1"

        fake_cm, posts = _fake_httpx_client()
        with patch("httpx.AsyncClient", return_value=fake_cm):
            await emitter.emit(
                event_name="workflow.completed",
                workflow_type="sales_ops",
                outcome="success",
                duration_ms=12345,
                # All of these MUST be stripped — they could carry PII
                lead_data={"company_name": "Acme"},
                user_email="alice@acme.com",
                prompt="ignore previous instructions",
                proposal_text="Hello Alice...",
            )

        assert len(posts) == 1
        payload = posts[0]["json"]
        assert payload["event_name"] == "workflow.completed"
        assert payload["workflow_type"] == "sales_ops"
        assert payload["outcome"] == "success"
        assert payload["duration_ms"] == 12345
        # Always-on context
        assert payload["install_id"] == "install-1"
        assert "version" in payload

        # Disallowed keys MUST NOT be in the payload
        for forbidden in ("lead_data", "user_email", "prompt", "proposal_text"):
            assert forbidden not in payload

    @pytest.mark.asyncio
    async def test_missing_event_name_is_dropped(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("TELEMETRY_WEBHOOK_URL", "https://t.example/ingest")
        get_settings.cache_clear()

        emitter = TelemetryEmitter.from_settings()
        fake_cm, posts = _fake_httpx_client()
        with patch("httpx.AsyncClient", return_value=fake_cm):
            await emitter.emit(workflow_type="sales_ops")  # no event_name

        assert posts == []  # dropped silently


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_webhook_failure_swallowed(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("TELEMETRY_WEBHOOK_URL", "https://broken.example/ingest")
        get_settings.cache_clear()

        emitter = TelemetryEmitter.from_settings()

        client = MagicMock()
        client.post = AsyncMock(side_effect=RuntimeError("network down"))
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=None)

        # Must NOT raise — telemetry is fire-and-forget
        with patch("httpx.AsyncClient", return_value=cm):
            await emitter.emit(event_name="workflow.started")


class TestAllowlist:
    def test_allowlist_is_frozenset(self):
        # frozenset prevents accidental runtime mutation of the PII boundary
        assert isinstance(_ALLOWED_FIELDS, frozenset)

    def test_no_user_content_fields(self):
        # If any of these slip in, the PII guarantee is broken
        for forbidden in (
            "lead_data", "payload", "company_name", "email", "prompt",
            "response", "proposal", "user_email", "ticket_body",
        ):
            assert forbidden not in _ALLOWED_FIELDS
