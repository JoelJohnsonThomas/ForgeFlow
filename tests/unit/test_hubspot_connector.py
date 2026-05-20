"""Tests for the HubSpot connector — payload shape + association IDs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.connectors.hubspot import HubSpotConnector


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


class TestDisabled:
    @pytest.mark.asyncio
    async def test_no_token_returns_mock(self, monkeypatch):
        monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "")
        get_settings.cache_clear()
        result = await HubSpotConnector().create_contact(email="a@b.com")
        assert result["mock"] is True


class TestCreateContact:
    @pytest.mark.asyncio
    async def test_only_email_required(self, monkeypatch):
        monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()
        factory, captured = _captured({"id": "1"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await HubSpotConnector().create_contact(email="alice@example.com")

        assert captured[0]["url"].endswith("/crm/v3/objects/contacts")
        assert captured[0]["json"]["properties"] == {"email": "alice@example.com"}

    @pytest.mark.asyncio
    async def test_optional_fields_pass_through(self, monkeypatch):
        monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()
        factory, captured = _captured({"id": "1"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await HubSpotConnector().create_contact(
                email="a@b.com",
                firstname="Alice",
                lastname="Smith",
                company="Acme",
                phone="+1-555-0001",
                extra_properties={"lifecyclestage": "lead"},
            )

        props = captured[0]["json"]["properties"]
        assert props["firstname"] == "Alice"
        assert props["company"] == "Acme"
        assert props["lifecyclestage"] == "lead"


class TestCreateDealAssociations:
    @pytest.mark.asyncio
    async def test_associations_use_hubspot_defined_ids(self, monkeypatch):
        monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()
        factory, captured = _captured({"id": "deal-1"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await HubSpotConnector().create_deal(
                deal_name="Acme - Enterprise",
                amount=50_000,
                contact_id="c-1",
                company_id="co-1",
            )

        body = captured[0]["json"]
        assert body["properties"]["dealname"] == "Acme - Enterprise"
        # amount must be stringified for HubSpot properties API
        assert body["properties"]["amount"] == "50000"
        # Both associations present with correct association type IDs
        assoc_ids = {a["to"]["id"] for a in body["associations"]}
        assert assoc_ids == {"c-1", "co-1"}
        type_ids = {a["types"][0]["associationTypeId"] for a in body["associations"]}
        # 3 = contact-to-deal, 5 = company-to-deal
        assert type_ids == {3, 5}

    @pytest.mark.asyncio
    async def test_no_associations_omitted_when_unset(self, monkeypatch):
        monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()
        factory, captured = _captured({"id": "deal-1"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await HubSpotConnector().create_deal(deal_name="Standalone", amount=1000)

        body = captured[0]["json"]
        assert "associations" not in body


class TestSearchContacts:
    @pytest.mark.asyncio
    async def test_default_properties_included(self, monkeypatch):
        monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "tok")
        get_settings.cache_clear()
        factory, captured = _captured({"results": []})

        with patch("httpx.AsyncClient", side_effect=factory):
            await HubSpotConnector().search_contacts(query="Acme")

        body = captured[0]["json"]
        assert body["query"] == "Acme"
        # The default property list must include email
        assert "email" in body["properties"]
