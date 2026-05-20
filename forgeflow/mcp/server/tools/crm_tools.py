"""MCP tools: mock CRM (simulates Salesforce-style lead management)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

router = FastMCP("crm-tools")

# In-memory CRM store (replace with real Salesforce/HubSpot integration)
_leads_db: dict[str, dict] = {}


@router.tool()
async def create_lead(
    company_name: str,
    contact_name: str = "",
    contact_email: str = "",
    industry: str = "",
    source: str = "forgeflow_ai",
) -> dict:
    """Create a new lead record in the CRM.

    Args:
        company_name: Company or organization name
        contact_name: Primary contact full name
        contact_email: Primary contact email address
        industry: Industry vertical
        source: Lead source attribution

    Returns:
        Created lead record with generated ID
    """
    lead_id = str(uuid.uuid4())
    lead = {
        "id": lead_id,
        "company_name": company_name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "industry": industry,
        "source": source,
        "status": "raw",
        "created_at": datetime.now(datetime.UTC).isoformat(),
        "updated_at": datetime.now(datetime.UTC).isoformat(),
    }
    _leads_db[lead_id] = lead
    logger.info("CRM: Created lead %s for %s", lead_id, company_name)
    return lead


@router.tool()
async def update_lead(
    lead_id: str,
    status: str | None = None,
    qualification_score: float | None = None,
    deal_value: int | None = None,
    notes: str | None = None,
) -> dict:
    """Update an existing lead record in the CRM.

    Args:
        lead_id: UUID of the lead to update
        status: New status (raw/qualified/disqualified/proposed/won/lost)
        qualification_score: AI-generated score 0-10
        deal_value: Estimated deal value in USD
        notes: Additional notes to append

    Returns:
        Updated lead record
    """
    if lead_id not in _leads_db:
        # Create a stub if not found (handles test cases)
        _leads_db[lead_id] = {"id": lead_id, "status": "unknown"}

    lead = _leads_db[lead_id]
    if status:
        lead["status"] = status
    if qualification_score is not None:
        lead["qualification_score"] = qualification_score
    if deal_value is not None:
        lead["deal_value_usd"] = deal_value
    if notes:
        lead.setdefault("notes", [])
        lead["notes"].append({"text": notes, "at": datetime.now(datetime.UTC).isoformat()})

    lead["updated_at"] = datetime.now(datetime.UTC).isoformat()
    logger.info("CRM: Updated lead %s | status=%s", lead_id, lead.get("status"))
    return lead


@router.tool()
async def get_lead(lead_id: str) -> dict:
    """Retrieve a lead record from the CRM by ID.

    Args:
        lead_id: UUID of the lead

    Returns:
        Lead record dict or error
    """
    if lead_id not in _leads_db:
        return {"error": f"Lead {lead_id} not found"}
    return _leads_db[lead_id]
