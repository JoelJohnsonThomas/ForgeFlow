"""MCP tools wrapping ServiceNow Table API."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from forgeflow.connectors.servicenow import ServiceNowConnector

logger = logging.getLogger(__name__)
router = FastMCP("servicenow-tools")


def _client() -> ServiceNowConnector:
    return ServiceNowConnector()


@router.tool()
async def servicenow_create_incident(
    short_description: str,
    description: str = "",
    urgency: str = "3",
    impact: str = "3",
    category: str | None = None,
    assignment_group: str | None = None,
) -> dict:
    """Create a ServiceNow incident. urgency/impact: 1=High, 2=Medium, 3=Low."""
    return await _client().create_incident(
        short_description=short_description,
        description=description,
        urgency=urgency,
        impact=impact,
        category=category,
        assignment_group=assignment_group,
    )


@router.tool()
async def servicenow_get_incident(sys_id: str) -> dict:
    """Fetch a ServiceNow incident by sys_id."""
    return await _client().get_incident(sys_id)


@router.tool()
async def servicenow_update_incident_state(
    sys_id: str, state: str, work_notes: str | None = None
) -> dict:
    """Move an incident to a new state.

    State codes: 1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed, 8=Canceled.
    """
    return await _client().update_incident(
        sys_id=sys_id, state=state, work_notes=work_notes
    )


@router.tool()
async def servicenow_resolve_incident(
    sys_id: str, close_code: str, close_notes: str
) -> dict:
    """Resolve an incident with a close code + notes."""
    return await _client().update_incident(
        sys_id=sys_id, state="6", close_code=close_code, close_notes=close_notes
    )


@router.tool()
async def servicenow_search_incidents(query: str, limit: int = 25) -> dict:
    """Search incidents with sysparm_query syntax.

    Examples:
      'state=2^urgency=1'
      'assignment_group.name=Network^active=true'
    """
    return await _client().search_incidents(query=query, limit=limit)
