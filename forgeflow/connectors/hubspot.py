"""HubSpot CRM connector — contacts, companies, deals, notes.

Uses the HubSpot CRM v3 API with a Private App access token. Pairs with
the sales_ops workflow: leads land as contacts + companies, and proposals
become deals in the pipeline.

Production patterns implemented:
  - upsert_contact_by_email — HubSpot's native idProperty=email upsert
  - upsert_company_by_domain — same pattern with domain
  - find_or_create_deal_by_run_id — idempotent deal via custom search

Required Private App scopes (set in HubSpot → Settings → Integrations → Private Apps):
  crm.objects.contacts.read    crm.objects.contacts.write
  crm.objects.companies.read   crm.objects.companies.write
  crm.objects.deals.read       crm.objects.deals.write

For OAuth installations (HubSpot Marketplace apps), swap to a per-tenant
token store keyed on workspace_id — same API surface from here down.

Settings:
  HUBSPOT_ACCESS_TOKEN  — Private App token from HubSpot account settings
  HUBSPOT_BASE_URL      — defaults to https://api.hubapi.com
"""

from __future__ import annotations

import logging
from typing import Any

from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector, PermanentError

logger = logging.getLogger(__name__)


class HubSpotConnector(BaseConnector):
    vendor = "hubspot"

    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.hubspot_base_url,
            token=token if token is not None else settings.hubspot_access_token.get_secret_value(),
        )

    # ---- Contacts ----

    async def create_contact(
        self,
        email: str,
        firstname: str | None = None,
        lastname: str | None = None,
        company: str | None = None,
        phone: str | None = None,
        extra_properties: dict[str, Any] | None = None,
    ) -> dict:
        properties: dict[str, Any] = {"email": email}
        if firstname:
            properties["firstname"] = firstname
        if lastname:
            properties["lastname"] = lastname
        if company:
            properties["company"] = company
        if phone:
            properties["phone"] = phone
        if extra_properties:
            properties.update(extra_properties)

        return await self._request(
            "POST", "/crm/v3/objects/contacts", json={"properties": properties}
        )

    async def get_contact(self, contact_id: str, properties: list[str] | None = None) -> dict:
        params = {"properties": ",".join(properties)} if properties else None
        return await self._request(
            "GET", f"/crm/v3/objects/contacts/{contact_id}", params=params
        )

    async def search_contacts(
        self, query: str, properties: list[str] | None = None, limit: int = 10
    ) -> dict:
        """Full-text search across default contact properties."""
        return await self._request(
            "POST",
            "/crm/v3/objects/contacts/search",
            json={
                "query": query,
                "limit": limit,
                "properties": properties or ["email", "firstname", "lastname", "company"],
            },
        )

    async def upsert_contact_by_email(
        self,
        email: str,
        firstname: str | None = None,
        lastname: str | None = None,
        company: str | None = None,
        phone: str | None = None,
        extra_properties: dict[str, Any] | None = None,
    ) -> dict:
        """Create-or-update a contact keyed on email — production idempotency.

        Uses HubSpot's native upsert via PATCH /crm/v3/objects/contacts/{email}?idProperty=email.
        Re-running the same workflow twice with the same lead email produces
        ONE contact, not two. Returns the contact dict with id + properties.

        If you need the underlying id explicitly, read result["id"].
        """
        properties: dict[str, Any] = {"email": email}
        if firstname:
            properties["firstname"] = firstname
        if lastname:
            properties["lastname"] = lastname
        if company:
            properties["company"] = company
        if phone:
            properties["phone"] = phone
        if extra_properties:
            properties.update(extra_properties)

        # PATCH with idProperty=email: HubSpot creates if missing, updates if present.
        # Returns 201 on create, 200 on update — either way, body has {id, properties}.
        try:
            return await self._request(
                "PATCH",
                f"/crm/v3/objects/contacts/{email}",
                params={"idProperty": "email"},
                json={"properties": properties},
            )
        except PermanentError as exc:
            # HubSpot returns 404 from the upsert endpoint occasionally when the
            # email format is borderline (e.g. unicode local-parts). Fall back to
            # the POST path so the workflow doesn't hard-fail.
            if exc.status_code == 404:
                logger.info("HubSpot upsert 404 for %s — falling back to POST", email)
                return await self.create_contact(
                    email, firstname, lastname, company, phone, extra_properties
                )
            raise

    # ---- Companies ----

    async def create_company(
        self, name: str, domain: str | None = None, industry: str | None = None
    ) -> dict:
        properties: dict[str, Any] = {"name": name}
        if domain:
            properties["domain"] = domain
        if industry:
            properties["industry"] = industry
        return await self._request(
            "POST", "/crm/v3/objects/companies", json={"properties": properties}
        )

    async def upsert_company_by_domain(
        self,
        name: str,
        domain: str,
        industry: str | None = None,
        extra_properties: dict[str, Any] | None = None,
    ) -> dict:
        """Create-or-update a company keyed on domain.

        HubSpot doesn't expose an idProperty PATCH for companies, so we search
        first then create/update. Returns the company dict with id + properties.
        """
        existing = await self._request(
            "POST",
            "/crm/v3/objects/companies/search",
            json={
                "filterGroups": [
                    {"filters": [{"propertyName": "domain", "operator": "EQ", "value": domain}]}
                ],
                "properties": ["name", "domain", "industry"],
                "limit": 1,
            },
        )

        properties: dict[str, Any] = {"name": name, "domain": domain}
        if industry:
            properties["industry"] = industry
        if extra_properties:
            properties.update(extra_properties)

        results = existing.get("results") or []
        if results:
            company_id = results[0]["id"]
            return await self._request(
                "PATCH",
                f"/crm/v3/objects/companies/{company_id}",
                json={"properties": properties},
            )
        return await self._request(
            "POST", "/crm/v3/objects/companies", json={"properties": properties}
        )

    # ---- Deals ----

    async def create_deal(
        self,
        deal_name: str,
        amount: float,
        deal_stage: str = "appointmentscheduled",
        pipeline: str = "default",
        contact_id: str | None = None,
        company_id: str | None = None,
    ) -> dict:
        """Create a deal. Optionally associates a primary contact + company.

        Common deal_stage values (default pipeline):
          appointmentscheduled, qualifiedtobuy, presentationscheduled,
          decisionmakerboughtin, contractsent, closedwon, closedlost
        """
        properties: dict[str, Any] = {
            "dealname": deal_name,
            "amount": str(amount),
            "dealstage": deal_stage,
            "pipeline": pipeline,
        }
        body: dict[str, Any] = {"properties": properties}

        # HubSpot associations: provide a list of {to: {id}, types: [{...}]}
        associations: list[dict[str, Any]] = []
        # Default association type IDs (HubSpot maintains these as global constants).
        # If the deployment uses custom association labels, override at the call site.
        if contact_id:
            associations.append(
                {
                    "to": {"id": contact_id},
                    "types": [
                        {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}
                    ],
                }
            )
        if company_id:
            associations.append(
                {
                    "to": {"id": company_id},
                    "types": [
                        {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}
                    ],
                }
            )
        if associations:
            body["associations"] = associations

        return await self._request("POST", "/crm/v3/objects/deals", json=body)

    async def update_deal(self, deal_id: str, properties: dict[str, Any]) -> dict:
        return await self._request(
            "PATCH",
            f"/crm/v3/objects/deals/{deal_id}",
            json={"properties": {k: (str(v) if not isinstance(v, str) else v) for k, v in properties.items()}},
        )

    async def find_or_create_deal_by_run_id(
        self,
        run_id: str,
        deal_name: str,
        amount: float,
        deal_stage: str = "appointmentscheduled",
        pipeline: str = "default",
        contact_id: str | None = None,
        company_id: str | None = None,
    ) -> dict:
        """Idempotent deal creation keyed on the ForgeFlow workflow run_id.

        Stores run_id in a custom property `forgeflow_run_id`. Searches first
        and returns the existing deal if found — so a retried workflow never
        creates duplicate pipeline records.

        One-time setup: in HubSpot, create a custom Deal property named
        `forgeflow_run_id` (single-line text). The validation script can
        do this for you.
        """
        existing = await self._request(
            "POST",
            "/crm/v3/objects/deals/search",
            json={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "forgeflow_run_id",
                                "operator": "EQ",
                                "value": run_id,
                            }
                        ]
                    }
                ],
                "properties": ["dealname", "amount", "dealstage", "forgeflow_run_id"],
                "limit": 1,
            },
        )
        results = existing.get("results") or []
        if results:
            logger.info("HubSpot deal already exists for run_id=%s — reusing", run_id)
            return results[0]

        properties: dict[str, Any] = {
            "dealname": deal_name,
            "amount": str(amount),
            "dealstage": deal_stage,
            "pipeline": pipeline,
            "forgeflow_run_id": run_id,
        }
        body: dict[str, Any] = {"properties": properties}
        associations: list[dict[str, Any]] = []
        if contact_id:
            associations.append({
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}],
            })
        if company_id:
            associations.append({
                "to": {"id": company_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}],
            })
        if associations:
            body["associations"] = associations

        return await self._request("POST", "/crm/v3/objects/deals", json=body)

    # ---- Notes (engagements) ----

    async def create_note(
        self,
        body: str,
        contact_id: str | None = None,
        company_id: str | None = None,
        deal_id: str | None = None,
    ) -> dict:
        """Attach a free-text note to a contact, company, and/or deal."""
        import time

        payload: dict[str, Any] = {
            "properties": {
                "hs_note_body": body,
                "hs_timestamp": str(int(time.time() * 1000)),
            }
        }
        associations: list[dict[str, Any]] = []
        if contact_id:
            associations.append(
                {
                    "to": {"id": contact_id},
                    "types": [
                        {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}
                    ],
                }
            )
        if company_id:
            associations.append(
                {
                    "to": {"id": company_id},
                    "types": [
                        {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 190}
                    ],
                }
            )
        if deal_id:
            associations.append(
                {
                    "to": {"id": deal_id},
                    "types": [
                        {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}
                    ],
                }
            )
        if associations:
            payload["associations"] = associations

        return await self._request("POST", "/crm/v3/objects/notes", json=payload)
