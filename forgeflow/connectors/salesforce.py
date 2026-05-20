"""Salesforce connector — leads, accounts, opportunities, SOQL.

Uses the Salesforce REST API v59 with an OAuth access token + the
caller-supplied instance URL. The instance URL is required because
Salesforce serves each tenant from a different subdomain
(e.g. https://acme.my.salesforce.com).

Token acquisition is out-of-band — pull an access token via the SF CLI,
JWT bearer flow, or password flow, and pass it via SALESFORCE_ACCESS_TOKEN.
Implementing the full OAuth dance in-process is tracked as a Phase 5
deployment task.

Pairs with the sales_ops workflow: replaces the mock CRM with real
Lead + Opportunity records.

Settings:
  SALESFORCE_INSTANCE_URL  — e.g. https://acme.my.salesforce.com
  SALESFORCE_ACCESS_TOKEN  — OAuth bearer token
  SALESFORCE_API_VERSION   — defaults to v59.0
"""

from __future__ import annotations

import logging
from typing import Any

from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class SalesforceConnector(BaseConnector):
    vendor = "salesforce"

    def __init__(
        self,
        instance_url: str | None = None,
        token: str | None = None,
        api_version: str | None = None,
    ) -> None:
        settings = get_settings()
        super().__init__(
            base_url=instance_url or settings.salesforce_instance_url,
            token=token if token is not None else settings.salesforce_access_token.get_secret_value(),
        )
        self.api_version = api_version or settings.salesforce_api_version

    def is_enabled(self) -> bool:
        return bool(self._token and self.base_url)

    def _api(self, path: str) -> str:
        """Prefix all sObject paths with the versioned REST root."""
        return f"/services/data/{self.api_version}{path}"

    # ---- Leads ----

    async def create_lead(
        self,
        company: str,
        last_name: str,
        first_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        status: str = "Open - Not Contacted",
        extra_fields: dict[str, Any] | None = None,
    ) -> dict:
        """Salesforce requires Company + LastName for Lead inserts."""
        payload: dict[str, Any] = {
            "Company": company,
            "LastName": last_name,
            "Status": status,
        }
        if first_name:
            payload["FirstName"] = first_name
        if email:
            payload["Email"] = email
        if phone:
            payload["Phone"] = phone
        if extra_fields:
            payload.update(extra_fields)

        return await self._request("POST", self._api("/sobjects/Lead/"), json=payload)

    async def update_lead(self, lead_id: str, fields: dict[str, Any]) -> dict:
        """Salesforce returns 204 No Content on successful update."""
        return await self._request(
            "PATCH", self._api(f"/sobjects/Lead/{lead_id}"), json=fields
        )

    async def get_lead(self, lead_id: str) -> dict:
        return await self._request("GET", self._api(f"/sobjects/Lead/{lead_id}"))

    async def convert_lead(
        self, lead_id: str, converted_status: str = "Closed - Converted"
    ) -> dict:
        """Lead conversion goes through the Sobject Collections Convert action."""
        return await self._request(
            "POST",
            self._api("/sobjects/LeadConvert"),
            json={"leadId": lead_id, "convertedStatus": converted_status},
        )

    # ---- Accounts ----

    async def create_account(
        self,
        name: str,
        industry: str | None = None,
        website: str | None = None,
        annual_revenue: float | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"Name": name}
        if industry:
            payload["Industry"] = industry
        if website:
            payload["Website"] = website
        if annual_revenue is not None:
            payload["AnnualRevenue"] = annual_revenue
        return await self._request("POST", self._api("/sobjects/Account/"), json=payload)

    # ---- Opportunities ----

    async def create_opportunity(
        self,
        name: str,
        close_date: str,  # YYYY-MM-DD
        stage: str = "Prospecting",
        amount: float | None = None,
        account_id: str | None = None,
        probability: int | None = None,
    ) -> dict:
        """Salesforce requires Name + CloseDate + StageName for Opportunity inserts."""
        payload: dict[str, Any] = {
            "Name": name,
            "CloseDate": close_date,
            "StageName": stage,
        }
        if amount is not None:
            payload["Amount"] = amount
        if account_id:
            payload["AccountId"] = account_id
        if probability is not None:
            payload["Probability"] = probability
        return await self._request(
            "POST", self._api("/sobjects/Opportunity/"), json=payload
        )

    async def update_opportunity(self, opp_id: str, fields: dict[str, Any]) -> dict:
        return await self._request(
            "PATCH", self._api(f"/sobjects/Opportunity/{opp_id}"), json=fields
        )

    # ---- SOQL ----

    async def query(self, soql: str) -> dict:
        """Run a SOQL query. Example: 'SELECT Id, Name FROM Account LIMIT 10'."""
        return await self._request(
            "GET", self._api("/query/"), params={"q": soql}
        )
