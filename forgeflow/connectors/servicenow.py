"""ServiceNow Table API connector — incidents, change requests, comments.

Uses the ServiceNow Table API with Basic auth (username + password). For
OAuth, swap auth_header() to use the bearer token — same URL surface.

Pairs naturally with an incident-management workflow built on top of the
support_ops template: a triaged support ticket can spawn a ServiceNow
incident, and the executor can move it through the standard
New -> In Progress -> Resolved transitions.

Settings:
  SERVICENOW_INSTANCE_URL  — e.g. https://acme.service-now.com
  SERVICENOW_USERNAME      — Service account username
  SERVICENOW_PASSWORD      — Service account password
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class ServiceNowConnector(BaseConnector):
    vendor = "servicenow"

    def __init__(
        self,
        instance_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        settings = get_settings()
        super().__init__(
            base_url=instance_url or settings.servicenow_instance_url,
            token=(
                password
                if password is not None
                else settings.servicenow_password.get_secret_value()
            ),
        )
        self._username = (
            username if username is not None else settings.servicenow_username
        )

    def is_enabled(self) -> bool:
        return bool(self._token and self._username and self.base_url)

    def auth_header(self) -> dict[str, str]:
        creds = f"{self._username}:{self._token}".encode()
        encoded = base64.b64encode(creds).decode()
        return {"Authorization": f"Basic {encoded}"}

    # ---- Incidents ----

    async def create_incident(
        self,
        short_description: str,
        description: str = "",
        urgency: str = "3",  # 1=High, 2=Medium, 3=Low
        impact: str = "3",
        category: str | None = None,
        caller_id: str | None = None,
        assignment_group: str | None = None,
    ) -> dict:
        """Create a new ServiceNow incident in the `incident` table."""
        payload: dict[str, Any] = {
            "short_description": short_description,
            "description": description,
            "urgency": urgency,
            "impact": impact,
        }
        if category:
            payload["category"] = category
        if caller_id:
            payload["caller_id"] = caller_id
        if assignment_group:
            payload["assignment_group"] = assignment_group

        return await self._request("POST", "/api/now/table/incident", json=payload)

    async def get_incident(self, sys_id: str) -> dict:
        return await self._request("GET", f"/api/now/table/incident/{sys_id}")

    async def update_incident(
        self,
        sys_id: str,
        state: str | None = None,
        work_notes: str | None = None,
        comments: str | None = None,
        close_code: str | None = None,
        close_notes: str | None = None,
    ) -> dict:
        """Update an incident. state codes: 1=New, 2=In Progress, 6=Resolved, 7=Closed."""
        payload: dict[str, Any] = {}
        if state is not None:
            payload["state"] = state
        if work_notes is not None:
            payload["work_notes"] = work_notes
        if comments is not None:
            payload["comments"] = comments
        if close_code is not None:
            payload["close_code"] = close_code
        if close_notes is not None:
            payload["close_notes"] = close_notes

        return await self._request(
            "PATCH", f"/api/now/table/incident/{sys_id}", json=payload
        )

    async def search_incidents(
        self,
        query: str,
        limit: int = 25,
        fields: list[str] | None = None,
    ) -> dict:
        """Search incidents using sysparm_query syntax.

        Example query: 'state=2^assignment_group.name=Network'
        """
        params: dict[str, Any] = {
            "sysparm_query": query,
            "sysparm_limit": limit,
        }
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        return await self._request(
            "GET", "/api/now/table/incident", params=params
        )

    # ---- Change Requests ----

    async def create_change_request(
        self,
        short_description: str,
        description: str = "",
        risk: str = "3",       # 1=High, 2=Moderate, 3=Low
        priority: str = "3",
        change_type: str = "normal",
    ) -> dict:
        payload: dict[str, Any] = {
            "short_description": short_description,
            "description": description,
            "risk": risk,
            "priority": priority,
            "type": change_type,
        }
        return await self._request(
            "POST", "/api/now/table/change_request", json=payload
        )

    # ---- Generic table reads ----

    async def query_table(
        self,
        table: str,
        sysparm_query: str = "",
        limit: int = 25,
        fields: list[str] | None = None,
    ) -> dict:
        """Generic Table API query — useful for any sObject ServiceNow exposes."""
        params: dict[str, Any] = {"sysparm_limit": limit}
        if sysparm_query:
            params["sysparm_query"] = sysparm_query
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        return await self._request("GET", f"/api/now/table/{table}", params=params)
