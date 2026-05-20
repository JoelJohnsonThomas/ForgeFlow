"""Tests for the Salesforce connector — versioned API paths + SOQL."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.connectors.salesforce import SalesforceConnector


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
        captured.append({"method": method, "url": url, "json": json, "params": params})
        return fake_response

    fake_client = MagicMock()
    fake_client.request = AsyncMock(side_effect=_request)
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=fake_client)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    return lambda *a, **kw: fake_cm, captured


class TestEnablement:
    def test_missing_token_disabled(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://x.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "")
        get_settings.cache_clear()
        assert SalesforceConnector().is_enabled() is False

    def test_missing_instance_url_disabled(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "")
        monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()
        assert SalesforceConnector().is_enabled() is False

    def test_both_present_enabled(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://x.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()
        assert SalesforceConnector().is_enabled() is True


class TestVersionedPaths:
    @pytest.mark.asyncio
    async def test_lead_create_uses_versioned_path(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://x.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("SALESFORCE_API_VERSION", "v59.0")
        get_settings.cache_clear()

        factory, captured = _captured({"id": "00Q1", "success": True})

        with patch("httpx.AsyncClient", side_effect=factory):
            await SalesforceConnector().create_lead(
                company="Acme", last_name="Smith", first_name="Alice", email="a@b.com"
            )

        call = captured[0]
        assert call["method"] == "POST"
        assert "/services/data/v59.0/sobjects/Lead/" in call["url"]
        assert call["json"]["Company"] == "Acme"
        assert call["json"]["LastName"] == "Smith"
        assert call["json"]["FirstName"] == "Alice"
        assert call["json"]["Email"] == "a@b.com"
        assert call["json"]["Status"] == "Open - Not Contacted"  # default

    @pytest.mark.asyncio
    async def test_api_version_swap_reflected_in_path(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://x.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("SALESFORCE_API_VERSION", "v60.0")
        get_settings.cache_clear()

        factory, captured = _captured({"records": []})

        with patch("httpx.AsyncClient", side_effect=factory):
            await SalesforceConnector().query("SELECT Id FROM Lead LIMIT 1")

        assert "/services/data/v60.0/query/" in captured[0]["url"]


class TestUpdateLead:
    @pytest.mark.asyncio
    async def test_patch_with_partial_fields(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://x.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()

        factory, captured = _captured({}, status=204)

        with patch("httpx.AsyncClient", side_effect=factory):
            await SalesforceConnector().update_lead("00Q123", {"Status": "Qualified"})

        call = captured[0]
        assert call["method"] == "PATCH"
        assert call["url"].endswith("/sobjects/Lead/00Q123")
        assert call["json"] == {"Status": "Qualified"}


class TestOpportunity:
    @pytest.mark.asyncio
    async def test_create_includes_required_fields(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://x.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()

        factory, captured = _captured({"id": "0061"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await SalesforceConnector().create_opportunity(
                name="Acme - Enterprise",
                close_date="2026-12-31",
                stage="Proposal",
                amount=50_000,
                account_id="001abc",
            )

        body = captured[0]["json"]
        assert body["Name"] == "Acme - Enterprise"
        assert body["CloseDate"] == "2026-12-31"
        assert body["StageName"] == "Proposal"
        assert body["Amount"] == 50_000
        assert body["AccountId"] == "001abc"


class TestSOQL:
    @pytest.mark.asyncio
    async def test_query_sends_q_param(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "https://x.my.salesforce.com")
        monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()

        factory, captured = _captured({"records": []})

        with patch("httpx.AsyncClient", side_effect=factory):
            await SalesforceConnector().query("SELECT Id, Name FROM Lead WHERE Status='Open' LIMIT 5")

        assert captured[0]["params"] == {
            "q": "SELECT Id, Name FROM Lead WHERE Status='Open' LIMIT 5"
        }


class TestDisabled:
    @pytest.mark.asyncio
    async def test_returns_mock_when_disabled(self, monkeypatch):
        monkeypatch.setenv("SALESFORCE_INSTANCE_URL", "")
        get_settings.cache_clear()
        result = await SalesforceConnector().create_lead(company="X", last_name="Y")
        assert result["mock"] is True
        assert result["vendor"] == "salesforce"
