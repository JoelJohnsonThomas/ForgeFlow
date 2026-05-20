"""QuickBooks Online connector — customers, invoices, accounts, journal entries, query.

QBO is OAuth-2.0-only — there is no API-key path. Tokens are obtained
through the OAuth Authorization Code flow at Intuit; this connector takes
the resulting access_token (+ refresh handled externally) plus the realmId
(QuickBooks company ID).

Every URL is realm-scoped: /v3/company/{realmId}/...

Pairs with the finance_recon workflow: invoices and journal entries can
be read for reconciliation, and adjusting entries can be posted back.

Settings:
  QUICKBOOKS_ACCESS_TOKEN   — Intuit OAuth access token
  QUICKBOOKS_REALM_ID       — Company ID (numeric, from Intuit OAuth callback)
  QUICKBOOKS_ENVIRONMENT    — 'sandbox' or 'production' (default: production)
  QUICKBOOKS_MINOR_VERSION  — Intuit API minor version (default: 65)
"""

from __future__ import annotations

import logging
from typing import Any

from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


PROD_BASE = "https://quickbooks.api.intuit.com"
SANDBOX_BASE = "https://sandbox-quickbooks.api.intuit.com"


class QuickBooksConnector(BaseConnector):
    vendor = "quickbooks"

    def __init__(
        self,
        token: str | None = None,
        realm_id: str | None = None,
        environment: str | None = None,
        minor_version: int | None = None,
    ) -> None:
        settings = get_settings()
        env = environment or settings.quickbooks_environment
        base_url = SANDBOX_BASE if env == "sandbox" else PROD_BASE

        super().__init__(
            base_url=base_url,
            token=(
                token
                if token is not None
                else settings.quickbooks_access_token.get_secret_value()
            ),
        )
        self._realm = realm_id if realm_id is not None else settings.quickbooks_realm_id
        self._minor_version = (
            minor_version
            if minor_version is not None
            else settings.quickbooks_minor_version
        )

    def is_enabled(self) -> bool:
        return bool(self._token and self._realm)

    def auth_header(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    def _path(self, suffix: str) -> str:
        return f"/v3/company/{self._realm}/{suffix.lstrip('/')}"

    def _default_params(self) -> dict[str, Any]:
        return {"minorversion": self._minor_version}

    # ---- Query (SQL-like) ----

    async def query(self, sql: str) -> dict:
        """Run a QBO query. Example: 'select * from Customer where Active=true MAXRESULTS 50'."""
        params = {**self._default_params(), "query": sql}
        return await self._request("GET", self._path("query"), params=params)

    # ---- Customer ----

    async def create_customer(
        self,
        display_name: str,
        primary_email: str | None = None,
        company_name: str | None = None,
        notes: str | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"DisplayName": display_name}
        if primary_email:
            payload["PrimaryEmailAddr"] = {"Address": primary_email}
        if company_name:
            payload["CompanyName"] = company_name
        if notes:
            payload["Notes"] = notes
        return await self._request(
            "POST",
            self._path("customer"),
            params=self._default_params(),
            json=payload,
        )

    async def get_customer(self, customer_id: str) -> dict:
        return await self._request(
            "GET",
            self._path(f"customer/{customer_id}"),
            params=self._default_params(),
        )

    # ---- Invoice ----

    async def create_invoice(
        self,
        customer_id: str,
        line_items: list[dict[str, Any]],
        txn_date: str | None = None,
        due_date: str | None = None,
        memo: str | None = None,
    ) -> dict:
        """Create an invoice. Each line item must include Amount + DetailType
        + SalesItemLineDetail (with ItemRef.value pointing to a QBO Item).

        Example line:
          {
            "Amount": 100.0,
            "DetailType": "SalesItemLineDetail",
            "SalesItemLineDetail": {"ItemRef": {"value": "1"}}
          }
        """
        payload: dict[str, Any] = {
            "CustomerRef": {"value": customer_id},
            "Line": line_items,
        }
        if txn_date:
            payload["TxnDate"] = txn_date
        if due_date:
            payload["DueDate"] = due_date
        if memo:
            payload["CustomerMemo"] = {"value": memo}

        return await self._request(
            "POST",
            self._path("invoice"),
            params=self._default_params(),
            json=payload,
        )

    async def get_invoice(self, invoice_id: str) -> dict:
        return await self._request(
            "GET",
            self._path(f"invoice/{invoice_id}"),
            params=self._default_params(),
        )

    # ---- Account ----

    async def list_accounts(self, account_type: str | None = None) -> dict:
        """List Chart of Accounts entries. account_type filters by AccountType
        (e.g. 'Bank', 'Income', 'Expense')."""
        if account_type:
            sql = f"select * from Account where AccountType = '{account_type}' MAXRESULTS 100"
        else:
            sql = "select * from Account MAXRESULTS 100"
        return await self.query(sql)

    # ---- Journal Entry ----

    async def create_journal_entry(
        self,
        lines: list[dict[str, Any]],
        txn_date: str | None = None,
        private_note: str | None = None,
    ) -> dict:
        """Post a journal entry. Lines must balance debits = credits.

        Example line:
          {
            "DetailType": "JournalEntryLineDetail",
            "Amount": 100.00,
            "JournalEntryLineDetail": {
              "PostingType": "Debit",
              "AccountRef": {"value": "33"}
            }
          }
        """
        payload: dict[str, Any] = {"Line": lines}
        if txn_date:
            payload["TxnDate"] = txn_date
        if private_note:
            payload["PrivateNote"] = private_note
        return await self._request(
            "POST",
            self._path("journalentry"),
            params=self._default_params(),
            json=payload,
        )
