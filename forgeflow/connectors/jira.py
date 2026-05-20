"""Jira Cloud connector — create / update / search / comment issues.

Uses the Jira Cloud REST API v3 with Basic auth (email + API token). For
on-prem Jira Server, swap auth_header() to use a bearer token — the
endpoints are otherwise compatible.

Pairs naturally with the support_ops workflow: a triaged ticket can be
created as a Jira issue and updated as the workflow progresses.

Settings:
  JIRA_BASE_URL    — e.g. https://acme.atlassian.net
  JIRA_EMAIL       — Atlassian account email
  JIRA_API_TOKEN   — API token from id.atlassian.com
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class JiraConnector(BaseConnector):
    vendor = "jira"

    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        token: str | None = None,
    ) -> None:
        settings = get_settings()
        # Jira's base_url already includes the tenant; API path is appended in each call.
        super().__init__(
            base_url=base_url or settings.jira_base_url,
            token=token if token is not None else settings.jira_api_token.get_secret_value(),
        )
        self._email = email if email is not None else settings.jira_email

    def is_enabled(self) -> bool:
        # Jira needs BOTH email and token for Basic auth
        return bool(self._token and self._email and self.base_url)

    def auth_header(self) -> dict[str, str]:
        creds = f"{self._email}:{self._token}".encode()
        encoded = base64.b64encode(creds).decode()
        return {"Authorization": f"Basic {encoded}"}

    # ---- Issues ----

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str = "",
        issue_type: str = "Task",
        priority: str | None = None,
        labels: list[str] | None = None,
        assignee_account_id: str | None = None,
    ) -> dict:
        # Jira v3 uses Atlassian Document Format (ADF) for rich text. We send
        # plain-text descriptions by wrapping in a minimal ADF paragraph.
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "description": _adf_from_text(description),
        }
        if priority:
            fields["priority"] = {"name": priority}
        if labels:
            fields["labels"] = labels
        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}

        return await self._request(
            "POST", "/rest/api/3/issue", json={"fields": fields}
        )

    async def get_issue(self, issue_key: str) -> dict:
        return await self._request("GET", f"/rest/api/3/issue/{issue_key}")

    async def update_issue(
        self,
        issue_key: str,
        summary: str | None = None,
        description: str | None = None,
        labels: list[str] | None = None,
        priority: str | None = None,
    ) -> dict:
        fields: dict[str, Any] = {}
        if summary is not None:
            fields["summary"] = summary
        if description is not None:
            fields["description"] = _adf_from_text(description)
        if labels is not None:
            fields["labels"] = labels
        if priority is not None:
            fields["priority"] = {"name": priority}

        # Jira returns 204 No Content on PUT — _request handles that as {}
        return await self._request(
            "PUT", f"/rest/api/3/issue/{issue_key}", json={"fields": fields}
        )

    async def comment_issue(self, issue_key: str, body: str) -> dict:
        return await self._request(
            "POST",
            f"/rest/api/3/issue/{issue_key}/comment",
            json={"body": _adf_from_text(body)},
        )

    async def transition_issue(self, issue_key: str, transition_id: str) -> dict:
        """Move an issue through a workflow transition (e.g. To Do -> In Progress).

        Get valid transition IDs from list_transitions().
        """
        return await self._request(
            "POST",
            f"/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
        )

    async def list_transitions(self, issue_key: str) -> dict:
        return await self._request("GET", f"/rest/api/3/issue/{issue_key}/transitions")

    async def search(self, jql: str, max_results: int = 50) -> dict:
        """JQL search. Example: 'project = ENG AND status = "To Do"'."""
        return await self._request(
            "POST",
            "/rest/api/3/search",
            json={"jql": jql, "maxResults": max_results},
        )


def _adf_from_text(text: str) -> dict[str, Any]:
    """Wrap plain text in a minimal Atlassian Document Format payload.

    For rich formatting, swap this out for a real ADF builder — the API
    surface is otherwise unchanged.
    """
    if not text:
        return {"type": "doc", "version": 1, "content": []}
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }
