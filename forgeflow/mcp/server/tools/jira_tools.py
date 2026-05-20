"""MCP tools wrapping Jira Cloud — used by the support_ops workflow."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from forgeflow.connectors.jira import JiraConnector

logger = logging.getLogger(__name__)
router = FastMCP("jira-tools")


def _client() -> JiraConnector:
    return JiraConnector()


@router.tool()
async def jira_create_issue(
    project_key: str,
    summary: str,
    description: str = "",
    issue_type: str = "Task",
    priority: str | None = None,
    labels: list[str] | None = None,
) -> dict:
    """Create a Jira issue. project_key is the short prefix (e.g. 'ENG', 'SUP')."""
    return await _client().create_issue(
        project_key=project_key,
        summary=summary,
        description=description,
        issue_type=issue_type,
        priority=priority,
        labels=labels,
    )


@router.tool()
async def jira_get_issue(issue_key: str) -> dict:
    """Fetch a Jira issue by its key (e.g. 'ENG-123')."""
    return await _client().get_issue(issue_key)


@router.tool()
async def jira_comment_issue(issue_key: str, body: str) -> dict:
    """Add a comment to a Jira issue."""
    return await _client().comment_issue(issue_key, body)


@router.tool()
async def jira_transition_issue(issue_key: str, transition_id: str) -> dict:
    """Move an issue through a workflow transition."""
    return await _client().transition_issue(issue_key, transition_id)


@router.tool()
async def jira_search(jql: str, max_results: int = 50) -> dict:
    """JQL search. Example: 'project = ENG AND status = \"In Progress\"'."""
    return await _client().search(jql, max_results=max_results)
