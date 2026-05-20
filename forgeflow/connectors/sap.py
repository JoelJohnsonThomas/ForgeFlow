"""SAP S/4HANA Cloud connector — OData v2 for sales orders, invoices, business partners.

Targets the SAP OData v2 APIs published under `/sap/opu/odata/sap/`. Each
business object lives in its own service (API_SALES_ORDER_SRV,
API_BUSINESS_PARTNER, API_SUPPLIER_INVOICE_PROCESS_SRV, etc.) and exposes
collections like `A_SalesOrder` and `A_BusinessPartner`.

Auth options:
  1. Basic auth (test tenants + on-prem with simple users)
  2. OAuth 2.0 client credentials (production S/4HANA Cloud)
  3. X.509 client certificates

This connector defaults to Basic auth (simpler, more portable across
tenant flavors). For OAuth, swap auth_header() to use a token cache.

The SAP OData layer also requires a CSRF token for any write operation
(POST/PATCH/DELETE). We fetch it lazily on the first write and reuse it.

Pairs with the finance_recon workflow: real supplier invoices can be
read directly from S/4HANA instead of mocked.

Settings:
  SAP_BASE_URL    — e.g. https://my300000-api.s4hana.cloud.sap
  SAP_USERNAME    — service technical user (e.g. SAP_API_USER)
  SAP_PASSWORD    — password / client secret
  SAP_CLIENT      — SAP client number (defaults to 100)
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector, ConnectorError, mock_response

logger = logging.getLogger(__name__)


class SAPConnector(BaseConnector):
    vendor = "sap"
    timeout_seconds: float = 60.0  # SAP can be slow; bump the default

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        client: str | None = None,
    ) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.sap_base_url,
            token=(
                password
                if password is not None
                else settings.sap_password.get_secret_value()
            ),
        )
        self._username = username if username is not None else settings.sap_username
        self._client = client if client is not None else settings.sap_client
        self._csrf_token: str | None = None

    def is_enabled(self) -> bool:
        return bool(self._token and self._username and self.base_url)

    def auth_header(self) -> dict[str, str]:
        creds = f"{self._username}:{self._token}".encode()
        encoded = base64.b64encode(creds).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "sap-client": self._client,
            "Accept": "application/json",
        }
        if self._csrf_token:
            headers["x-csrf-token"] = self._csrf_token
        return headers

    # ---- CSRF token (required for OData writes) ----

    async def _fetch_csrf_token(self) -> None:
        """Issue a HEAD request with x-csrf-token: fetch to get a write token.

        SAP returns the token in the response header; we cache it on self
        for subsequent write operations.
        """
        if not self.is_enabled():
            return

        url = f"{self.base_url}/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner"
        headers = {
            **self.auth_header(),
            "x-csrf-token": "fetch",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.head(url, headers=headers)
            self._csrf_token = response.headers.get("x-csrf-token", "")
            if self._csrf_token:
                logger.debug("SAP CSRF token acquired")
        except httpx.HTTPError as exc:
            logger.warning("SAP CSRF token fetch failed: %s", exc)

    # ---- Sales Orders ----

    async def get_sales_order(self, sales_order_id: str) -> dict:
        path = (
            f"/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder('{sales_order_id}')"
            "?$format=json"
        )
        return await self._request("GET", path)

    async def search_sales_orders(
        self,
        filter_expr: str | None = None,
        top: int = 25,
        expand: str | None = None,
    ) -> dict:
        """Filter syntax is OData v2: e.g. `SalesOrderType eq 'OR'`."""
        params: dict[str, Any] = {"$format": "json", "$top": top}
        if filter_expr:
            params["$filter"] = filter_expr
        if expand:
            params["$expand"] = expand
        return await self._request(
            "GET", "/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder", params=params
        )

    async def create_sales_order(
        self,
        sold_to_party: str,
        sales_organization: str,
        distribution_channel: str = "10",
        division: str = "00",
        items: list[dict[str, Any]] | None = None,
    ) -> dict:
        if not self.is_enabled():
            return mock_response(
                self.vendor,
                "POST sales_order",
                sold_to_party=sold_to_party,
            )

        # SAP requires a CSRF token for writes
        if not self._csrf_token:
            await self._fetch_csrf_token()

        body: dict[str, Any] = {
            "SoldToParty": sold_to_party,
            "SalesOrganization": sales_organization,
            "DistributionChannel": distribution_channel,
            "OrganizationDivision": division,
        }
        if items:
            body["to_Item"] = {"results": items}

        return await self._request(
            "POST",
            "/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder",
            json=body,
        )

    # ---- Business Partners ----

    async def get_business_partner(self, bp_id: str) -> dict:
        return await self._request(
            "GET",
            f"/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner('{bp_id}')",
            params={"$format": "json"},
        )

    async def search_business_partners(
        self, filter_expr: str | None = None, top: int = 25
    ) -> dict:
        params: dict[str, Any] = {"$format": "json", "$top": top}
        if filter_expr:
            params["$filter"] = filter_expr
        return await self._request(
            "GET",
            "/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner",
            params=params,
        )

    # ---- Supplier Invoices ----

    async def get_supplier_invoice(self, invoice_id: str, fiscal_year: str) -> dict:
        """Composite key: SupplierInvoice + FiscalYear."""
        path = (
            "/sap/opu/odata/sap/API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice"
            f"(SupplierInvoice='{invoice_id}',FiscalYear='{fiscal_year}')"
            "?$format=json"
        )
        return await self._request("GET", path)

    async def search_supplier_invoices(
        self, filter_expr: str | None = None, top: int = 25
    ) -> dict:
        params: dict[str, Any] = {"$format": "json", "$top": top}
        if filter_expr:
            params["$filter"] = filter_expr
        return await self._request(
            "GET",
            "/sap/opu/odata/sap/API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice",
            params=params,
        )

    # ---- Generic OData entity-set reader ----

    async def query_entity_set(
        self,
        service: str,
        entity_set: str,
        filter_expr: str | None = None,
        top: int = 25,
        select: str | None = None,
    ) -> dict:
        """Read any OData entity set without a dedicated method.

        Example: query_entity_set('API_PURCHASEORDER_PROCESS_SRV',
                                  'A_PurchaseOrder',
                                  filter_expr="PurchaseOrderType eq 'NB'")
        """
        params: dict[str, Any] = {"$format": "json", "$top": top}
        if filter_expr:
            params["$filter"] = filter_expr
        if select:
            params["$select"] = select
        return await self._request(
            "GET", f"/sap/opu/odata/sap/{service}/{entity_set}", params=params
        )

    # ---- Override _request to expose CSRF errors ----

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        extra_headers: dict | None = None,
    ) -> dict:
        """Wraps the base _request to refresh CSRF tokens once on 403/CSRF errors."""
        try:
            return await super()._request(
                method, path, params=params, json=json, extra_headers=extra_headers
            )
        except ConnectorError as exc:
            # SAP returns 403 with header x-csrf-token: required if our cached
            # token expired. Refresh once and retry.
            if exc.status_code == 403 and method.upper() != "GET":
                logger.info("SAP CSRF token rejected; refreshing and retrying")
                self._csrf_token = None
                await self._fetch_csrf_token()
                return await super()._request(
                    method, path, params=params, json=json, extra_headers=extra_headers
                )
            raise
