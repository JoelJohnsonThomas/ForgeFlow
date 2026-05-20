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
    """Create a HubSpot contact. Email is the primary identifier."""
    return await _client().create_contact(
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
    """Create a HubSpot company record."""
    return await _client().create_company(name=name, domain=domain, industry=industry)


@router.tool()
async def hubspot_create_deal(
    deal_name: str,
    amount: float,
    deal_stage: str = "appointmentscheduled",
    pipeline: str = "default",
    contact_id: str | None = None,
    company_id: str | None = None,
) -> dict:
    """Create a HubSpot deal, optionally associated with a contact + company."""
    return await _client().create_deal(
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
