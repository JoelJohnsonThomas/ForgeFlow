"""Tests for the SAP S/4HANA connector — Basic auth, sap-client header,
OData URL shape, and CSRF token flow."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.connectors.sap import SAPConnector


@pytest.fixture(autouse=True)
def _reset():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _captured(payload: dict, status: int = 200, headers: dict | None = None):
    captured: list[dict] = []

    fake_response = MagicMock()
    fake_response.status_code = status
    fake_response.content = b'{}'
    fake_response.json = MagicMock(return_value=payload)
    fake_response.headers = headers or {}

    async def _request(method, url, params=None, json=None, headers=None):
        captured.append({"method": method, "url": url, "params": params, "json": json, "headers": headers})
        return fake_response

    async def _head(url, headers=None):
        captured.append({"method": "HEAD", "url": url, "headers": headers})
        return fake_response

    fake_client = MagicMock()
    fake_client.request = AsyncMock(side_effect=_request)
    fake_client.head = AsyncMock(side_effect=_head)
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=fake_client)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    return lambda *a, **kw: fake_cm, captured


class TestEnablement:
    def test_missing_url_disabled(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "")
        monkeypatch.setenv("SAP_USERNAME", "u")
        monkeypatch.setenv("SAP_PASSWORD", "p")
        get_settings.cache_clear()
        assert SAPConnector().is_enabled() is False

    def test_all_present_enabled(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "https://my300000-api.s4hana.cloud.sap")
        monkeypatch.setenv("SAP_USERNAME", "u")
        monkeypatch.setenv("SAP_PASSWORD", "p")
        get_settings.cache_clear()
        assert SAPConnector().is_enabled() is True


class TestAuthHeaders:
    def test_basic_auth_plus_sap_client(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "https://x.s4hana.cloud.sap")
        monkeypatch.setenv("SAP_USERNAME", "tech_user")
        monkeypatch.setenv("SAP_PASSWORD", "secret")
        monkeypatch.setenv("SAP_CLIENT", "200")
        get_settings.cache_clear()

        header = SAPConnector().auth_header()
        expected_basic = base64.b64encode(b"tech_user:secret").decode()
        assert header["Authorization"] == f"Basic {expected_basic}"
        assert header["sap-client"] == "200"


class TestODataURLs:
    @pytest.mark.asyncio
    async def test_get_sales_order_uses_key_predicate(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "https://x.s4hana.cloud.sap")
        monkeypatch.setenv("SAP_USERNAME", "u")
        monkeypatch.setenv("SAP_PASSWORD", "p")
        get_settings.cache_clear()

        factory, captured = _captured({"d": {"results": []}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await SAPConnector().get_sales_order("0001")

        # URL must include the OData key predicate
        assert "/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder('0001')" in captured[0]["url"]
        assert "$format=json" in captured[0]["url"]

    @pytest.mark.asyncio
    async def test_search_uses_top_and_filter(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "https://x.s4hana.cloud.sap")
        monkeypatch.setenv("SAP_USERNAME", "u")
        monkeypatch.setenv("SAP_PASSWORD", "p")
        get_settings.cache_clear()

        factory, captured = _captured({"d": {"results": []}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await SAPConnector().search_sales_orders(
                filter_expr="SalesOrderType eq 'OR'", top=50, expand="to_Item"
            )

        params = captured[0]["params"]
        assert params["$filter"] == "SalesOrderType eq 'OR'"
        assert params["$top"] == 50
        assert params["$expand"] == "to_Item"
        assert params["$format"] == "json"

    @pytest.mark.asyncio
    async def test_supplier_invoice_composite_key(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "https://x.s4hana.cloud.sap")
        monkeypatch.setenv("SAP_USERNAME", "u")
        monkeypatch.setenv("SAP_PASSWORD", "p")
        get_settings.cache_clear()

        factory, captured = _captured({"d": {}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await SAPConnector().get_supplier_invoice("5105600055", "2026")

        url = captured[0]["url"]
        # Composite OData key: (SupplierInvoice='X',FiscalYear='Y')
        assert "(SupplierInvoice='5105600055',FiscalYear='2026')" in url


class TestCSRF:
    @pytest.mark.asyncio
    async def test_create_sales_order_fetches_csrf_first(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "https://x.s4hana.cloud.sap")
        monkeypatch.setenv("SAP_USERNAME", "u")
        monkeypatch.setenv("SAP_PASSWORD", "p")
        get_settings.cache_clear()

        # First call is HEAD for CSRF token, returns x-csrf-token in headers
        factory, captured = _captured(
            {"d": {}}, headers={"x-csrf-token": "ABC123"}
        )

        with patch("httpx.AsyncClient", side_effect=factory):
            await SAPConnector().create_sales_order(
                sold_to_party="0010100001",
                sales_organization="1710",
            )

        # First captured call should be HEAD for CSRF fetch
        assert captured[0]["method"] == "HEAD"
        assert captured[0]["headers"]["x-csrf-token"] == "fetch"
        # Second captured call is the actual POST with the acquired token
        assert captured[1]["method"] == "POST"


class TestDisabled:
    @pytest.mark.asyncio
    async def test_create_returns_mock(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "")
        get_settings.cache_clear()
        result = await SAPConnector().create_sales_order(
            sold_to_party="X", sales_organization="Y"
        )
        assert result["mock"] is True
        assert result["vendor"] == "sap"

    @pytest.mark.asyncio
    async def test_search_returns_mock(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "")
        get_settings.cache_clear()
        result = await SAPConnector().search_sales_orders()
        assert result["mock"] is True


class TestGenericEntitySet:
    @pytest.mark.asyncio
    async def test_path_assembles_from_service_and_set(self, monkeypatch):
        monkeypatch.setenv("SAP_BASE_URL", "https://x.s4hana.cloud.sap")
        monkeypatch.setenv("SAP_USERNAME", "u")
        monkeypatch.setenv("SAP_PASSWORD", "p")
        get_settings.cache_clear()

        factory, captured = _captured({"d": {"results": []}})

        with patch("httpx.AsyncClient", side_effect=factory):
            await SAPConnector().query_entity_set(
                service="API_PURCHASEORDER_PROCESS_SRV",
                entity_set="A_PurchaseOrder",
                filter_expr="PurchaseOrderType eq 'NB'",
                select="PurchaseOrder,Supplier",
            )

        assert "/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder" in captured[0]["url"]
        assert captured[0]["params"]["$select"] == "PurchaseOrder,Supplier"
