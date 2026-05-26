"""MCP tools wrapping HubSpot CRM — used by the sales_ops workflow."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from forgeflow.connectors.hubspot import HubSpotConnector

logger = logging.getLogger(__name__)
router = FastMCP("hubspot-tools")


def _client() -> HubSpotConnector:
    return HubSpotConnector()


@router.tool()
async def hubspot_create_contact(
    email: str,
    firstname: str | None = None,
    lastname: str | None = None,
    company: str | None = None,
    phone: str | None = None,
) -> dict:
    """Create a HubSpot contact. Email is the primary identifier.

    Prefer hubspot_upsert_contact for production workflows — it's idempotent
    on email and won't duplicate on retry.
    """
    return await _client().create_contact(
        email=email, firstname=firstname, lastname=lastname, company=company, phone=phone
    )


@router.tool()
async def hubspot_upsert_contact(
    email: str,
    firstname: str | None = None,
    lastname: str | None = None,
    company: str | None = None,
    phone: str | None = None,
) -> dict:
    """Create-or-update a HubSpot contact keyed on email. Idempotent — safe
    to call from a retried workflow without producing duplicates."""
    return await _client().upsert_contact_by_email(
        email=email, firstname=firstname, lastname=lastname, company=company, phone=phone
    )


@router.tool()
async def hubspot_search_contacts(query: str, limit: int = 10) -> dict:
    """Full-text search across HubSpot contacts."""
    return await _client().search_contacts(query=query, limit=limit)


@router.tool()
async def hubspot_create_company(
    name: str, domain: str | None = None, industry: str | None = None
) -> dict:
    """Create a HubSpot company record.

    Prefer hubspot_upsert_company for production — it dedupes on domain.
    """
    return await _client().create_company(name=name, domain=domain, industry=industry)


@router.tool()
async def hubspot_upsert_company(
    name: str, domain: str, industry: str | None = None
) -> dict:
    """Create-or-update a HubSpot company keyed on domain. Searches first
    then creates if missing. Returns the company dict with id + properties."""
    return await _client().upsert_company_by_domain(
        name=name, domain=domain, industry=industry
    )


@router.tool()
async def hubspot_create_deal(
    deal_name: str,
    amount: float,
    deal_stage: str = "appointmentscheduled",
    pipeline: str = "default",
    contact_id: str | None = None,
    company_id: str | None = None,
) -> dict:
    """Create a HubSpot deal, optionally associated with a contact + company.

    For workflow-driven creation, prefer hubspot_create_deal_idempotent which
    dedupes on the workflow run_id.
    """
    return await _client().create_deal(
        deal_name=deal_name,
        amount=amount,
        deal_stage=deal_stage,
        pipeline=pipeline,
        contact_id=contact_id,
        company_id=company_id,
    )


@router.tool()
async def hubspot_create_deal_idempotent(
    run_id: str,
    deal_name: str,
    amount: float,
    deal_stage: str = "appointmentscheduled",
    pipeline: str = "default",
    contact_id: str | None = None,
    company_id: str | None = None,
) -> dict:
    """Idempotent deal creation keyed on the ForgeFlow workflow run_id.

    Requires a custom Deal property named `forgeflow_run_id` in HubSpot
    (single-line text). Searches first and returns the existing deal if
    found, so a retried workflow never duplicates pipeline records.
    """
    return await _client().find_or_create_deal_by_run_id(
        run_id=run_id,
        deal_name=deal_name,
        amount=amount,
        deal_stage=deal_stage,
        pipeline=pipeline,
        contact_id=contact_id,
        company_id=company_id,
    )


@router.tool()
async def hubspot_update_deal_stage(deal_id: str, deal_stage: str) -> dict:
    """Move a HubSpot deal to a new stage (e.g. 'closedwon')."""
    return await _client().update_deal(deal_id, {"dealstage": deal_stage})


@router.tool()
async def hubspot_add_note(
    body: str,
    contact_id: str | None = None,
    company_id: str | None = None,
    deal_id: str | None = None,
) -> dict:
    """Attach a free-text note to one or more CRM objects."""
    return await _client().create_note(
        body=body, contact_id=contact_id, company_id=company_id, deal_id=deal_id
    )
