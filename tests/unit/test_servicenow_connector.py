"""Tests for the ServiceNow connector — Basic auth + sysparm queries."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.connectors.servicenow import ServiceNowConnector


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
        captured.append({"method": method, "url": url, "json": json, "params": params, "headers": headers})
        return fake_response

    fake_client = MagicMock()
    fake_client.request = AsyncMock(side_effect=_request)
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=fake_client)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    return lambda *a, **kw: fake_cm, captured


class TestEnablement:
    def test_missing_password_disabled(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_INSTANCE_URL", "https://acme.service-now.com")
        monkeypatch.setenv("SERVICENOW_USERNAME", "svc")
        monkeypatch.setenv("SERVICENOW_PASSWORD", "")
        get_settings.cache_clear()
        assert ServiceNowConnector().is_enabled() is False

    def test_missing_username_disabled(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_INSTANCE_URL", "https://acme.service-now.com")
        monkeypatch.setenv("SERVICENOW_USERNAME", "")
        monkeypatch.setenv("SERVICENOW_PASSWORD", "pw")
        get_settings.cache_clear()
        assert ServiceNowConnector().is_enabled() is False

    def test_missing_url_disabled(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_INSTANCE_URL", "")
        monkeypatch.setenv("SERVICENOW_USERNAME", "svc")
        monkeypatch.setenv("SERVICENOW_PASSWORD", "pw")
        get_settings.cache_clear()
        assert ServiceNowConnector().is_enabled() is False

    def test_all_present_enabled(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_INSTANCE_URL", "https://acme.service-now.com")
        monkeypatch.setenv("SERVICENOW_USERNAME", "svc")
        monkeypatch.setenv("SERVICENOW_PASSWORD", "pw")
        get_settings.cache_clear()
        assert ServiceNowConnector().is_enabled() is True


class TestBasicAuth:
    def test_header_is_base64_user_pass(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_INSTANCE_URL", "https://x.service-now.com")
        monkeypatch.setenv("SERVICENOW_USERNAME", "svc")
        monkeypatch.setenv("SERVICENOW_PASSWORD", "secret")
        get_settings.cache_clear()

        header = ServiceNowConnector().auth_header()
        expected = base64.b64encode(b"svc:secret").decode()
        assert header["Authorization"] == f"Basic {expected}"


class TestCreateIncident:
    @pytest.mark.asyncio
    async def test_disabled_returns_mock(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_USERNAME", "")
        get_settings.cache_clear()
        result = await ServiceNowConnector().create_incident("something")
        assert result["mock"] is True
        assert result["vendor"] == "servicenow"

    @pytest.mark.asyncio
    async def test_posts_to_incident_table(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_INSTANCE_URL", "https://x.service-now.com")
        monkeypatch.setenv("SERVICENOW_USERNAME", "svc")
        monkeypatch.setenv("SERVICENOW_PASSWORD", "pw")
        get_settings.cache_clear()

        factory, captured = _captured({"result": {"sys_id": "abc"}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await ServiceNowConnector().create_incident(
                short_description="Disk full",
                description="/var is 99% full",
                urgency="1",
                impact="2",
                assignment_group="Infra",
            )

        call = captured[0]
        assert call["method"] == "POST"
        assert call["url"].endswith("/api/now/table/incident")
        assert call["json"]["short_description"] == "Disk full"
        assert call["json"]["urgency"] == "1"
        assert call["json"]["assignment_group"] == "Infra"


class TestUpdateIncident:
    @pytest.mark.asyncio
    async def test_resolve_sets_state_6_and_close_code(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_INSTANCE_URL", "https://x.service-now.com")
        monkeypatch.setenv("SERVICENOW_USERNAME", "svc")
        monkeypatch.setenv("SERVICENOW_PASSWORD", "pw")
        get_settings.cache_clear()

        factory, captured = _captured({"result": {}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await ServiceNowConnector().update_incident(
                "abc123",
                state="6",
                close_code="Solved (Permanently)",
                close_notes="rotated logs",
            )

        call = captured[0]
        assert call["method"] == "PATCH"
        assert call["url"].endswith("/api/now/table/incident/abc123")
        assert call["json"]["state"] == "6"
        assert call["json"]["close_code"] == "Solved (Permanently)"
        assert call["json"]["close_notes"] == "rotated logs"


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_uses_sysparm_query(self, monkeypatch):
        monkeypatch.setenv("SERVICENOW_INSTANCE_URL", "https://x.service-now.com")
        monkeypatch.setenv("SERVICENOW_USERNAME", "svc")
        monkeypatch.setenv("SERVICENOW_PASSWORD", "pw")
        get_settings.cache_clear()

        factory, captured = _captured({"result": []})

        with patch("httpx.AsyncClient", side_effect=factory):
            await ServiceNowConnector().search_incidents(
                "state=2^urgency=1", limit=10, fields=["sys_id", "short_description"]
            )

        params = captured[0]["params"]
        assert params["sysparm_query"] == "state=2^urgency=1"
        assert params["sysparm_limit"] == 10
        assert params["sysparm_fields"] == "sys_id,short_description"
