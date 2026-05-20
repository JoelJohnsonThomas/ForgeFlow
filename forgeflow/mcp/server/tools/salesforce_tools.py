"""MCP tools wrapping Salesforce — used by the sales_ops workflow."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from forgeflow.connectors.salesforce import SalesforceConnector

logger = logging.getLogger(__name__)
router = FastMCP("salesforce-tools")


def _client() -> SalesforceConnector:
    return SalesforceConnector()


@router.tool()
async def salesforce_create_lead(
    company: str,
    last_name: str,
    first_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    status: str = "Open - Not Contacted",
) -> dict:
    """Create a Salesforce Lead. Company + LastName are required by SF."""
    return await _client().create_lead(
        company=company,
        last_name=last_name,
        first_name=first_name,
        email=email,
        phone=phone,
        status=status,
    )


@router.tool()
async def salesforce_update_lead_status(lead_id: str, status: str) -> dict:
    """Update a Lead's Status (e.g. 'Working - Contacted', 'Qualified', 'Disqualified')."""
    return await _client().update_lead(lead_id, {"Status": status})


@router.tool()
async def salesforce_get_lead(lead_id: str) -> dict:
    """Fetch a Salesforce Lead by Id."""
    return await _client().get_lead(lead_id)


@router.tool()
async def salesforce_create_opportunity(
    name: str,
    close_date: str,
    stage: str = "Prospecting",
    amount: float | None = None,
    account_id: str | None = None,
) -> dict:
    """Create a Salesforce Opportunity. close_date is ISO format (YYYY-MM-DD)."""
    return await _client().create_opportunity(
        name=name,
        close_date=close_date,
        stage=stage,
        amount=amount,
        account_id=account_id,
    )


@router.tool()
async def salesforce_query(soql: str) -> dict:
    """Run an arbitrary SOQL query. Example: 'SELECT Id, Name FROM Account LIMIT 10'."""
    return await _client().query(soql)
