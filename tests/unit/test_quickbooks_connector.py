"""Tests for the QuickBooks Online connector — realm scoping, minor version, query."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.connectors.quickbooks import (
    PROD_BASE,
    SANDBOX_BASE,
    QuickBooksConnector,
)


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


class TestEnablement:
    def test_missing_realm_disabled(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "")
        get_settings.cache_clear()
        assert QuickBooksConnector().is_enabled() is False

    def test_missing_token_disabled(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "123")
        get_settings.cache_clear()
        assert QuickBooksConnector().is_enabled() is False


class TestEnvironmentRouting:
    def test_sandbox_uses_sandbox_base(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "123")
        monkeypatch.setenv("QUICKBOOKS_ENVIRONMENT", "sandbox")
        get_settings.cache_clear()
        assert QuickBooksConnector().base_url == SANDBOX_BASE

    def test_production_default(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "123")
        monkeypatch.setenv("QUICKBOOKS_ENVIRONMENT", "production")
        get_settings.cache_clear()
        assert QuickBooksConnector().base_url == PROD_BASE


class TestRealmScoping:
    @pytest.mark.asyncio
    async def test_every_url_includes_realm(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "9341452009")
        get_settings.cache_clear()

        factory, captured = _captured({"Customer": {"Id": "1"}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await QuickBooksConnector().get_customer("1")

        assert "/v3/company/9341452009/customer/1" in captured[0]["url"]

    @pytest.mark.asyncio
    async def test_minor_version_in_every_request(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "1")
        monkeypatch.setenv("QUICKBOOKS_MINOR_VERSION", "70")
        get_settings.cache_clear()

        factory, captured = _captured({"Customer": {"Id": "2"}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await QuickBooksConnector().get_customer("2")

        assert captured[0]["params"]["minorversion"] == 70


class TestQuery:
    @pytest.mark.asyncio
    async def test_query_sends_sql(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "1")
        get_settings.cache_clear()

        factory, captured = _captured({"QueryResponse": {}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await QuickBooksConnector().query(
                "select * from Customer where Active=true MAXRESULTS 50"
            )

        assert captured[0]["params"]["query"].startswith("select * from Customer")
        assert "/v3/company/1/query" in captured[0]["url"]


class TestCreateCustomer:
    @pytest.mark.asyncio
    async def test_email_wrapped_in_primary_email_addr(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "1")
        get_settings.cache_clear()

        factory, captured = _captured({"Customer": {"Id": "1"}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await QuickBooksConnector().create_customer(
                display_name="Acme Co", primary_email="ops@acme.com"
            )

        body = captured[0]["json"]
        assert body["DisplayName"] == "Acme Co"
        # QBO wraps emails in PrimaryEmailAddr.Address — a string would 400
        assert body["PrimaryEmailAddr"] == {"Address": "ops@acme.com"}


class TestCreateInvoice:
    @pytest.mark.asyncio
    async def test_customer_ref_and_lines_passthrough(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "1")
        get_settings.cache_clear()

        factory, captured = _captured({"Invoice": {"Id": "55"}})

        lines = [
            {
                "Amount": 1000.0,
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {"ItemRef": {"value": "1"}},
            }
        ]

        with patch("httpx.AsyncClient", side_effect=factory):
            await QuickBooksConnector().create_invoice(
                customer_id="42", line_items=lines, memo="Q1 services"
            )

        body = captured[0]["json"]
        assert body["CustomerRef"] == {"value": "42"}
        assert body["Line"] == lines
        # Memo wraps in {value: ...} on the QBO side
        assert body["CustomerMemo"] == {"value": "Q1 services"}


class TestJournalEntry:
    @pytest.mark.asyncio
    async def test_lines_passthrough(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("QUICKBOOKS_REALM_ID", "1")
        get_settings.cache_clear()

        factory, captured = _captured({"JournalEntry": {"Id": "99"}})

        lines = [
            {
                "DetailType": "JournalEntryLineDetail",
                "Amount": 100.0,
                "JournalEntryLineDetail": {
                    "PostingType": "Debit",
                    "AccountRef": {"value": "33"},
                },
            },
            {
                "DetailType": "JournalEntryLineDetail",
                "Amount": 100.0,
                "JournalEntryLineDetail": {
                    "PostingType": "Credit",
                    "AccountRef": {"value": "34"},
                },
            },
        ]

        with patch("httpx.AsyncClient", side_effect=factory):
            await QuickBooksConnector().create_journal_entry(
                lines=lines, private_note="Recon adjustment"
            )

        body = captured[0]["json"]
        assert body["Line"] == lines
        assert body["PrivateNote"] == "Recon adjustment"


class TestDisabled:
    @pytest.mark.asyncio
    async def test_query_returns_mock(self, monkeypatch):
        monkeypatch.setenv("QUICKBOOKS_ACCESS_TOKEN", "")
        get_settings.cache_clear()
        result = await QuickBooksConnector().query("select 1")
        assert result["mock"] is True
        assert result["vendor"] == "quickbooks"
