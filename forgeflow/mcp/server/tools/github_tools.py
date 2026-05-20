"""MCP tools wrapping the GitHub REST API.

Thin delegations to forgeflow/connectors/github.py — the API logic lives there
so the same code is reachable from non-MCP call sites (background jobs,
direct API routes, etc.).
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from forgeflow.connectors.github import GitHubConnector

logger = logging.getLogger(__name__)
router = FastMCP("github-tools")


def _client() -> GitHubConnector:
    return GitHubConnector()


@router.tool()
async def github_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """Create a GitHub issue."""
    return await _client().create_issue(owner, repo, title, body, labels, assignees)


@router.tool()
async def github_comment_issue(
    owner: str, repo: str, issue_number: int, body: str
) -> dict:
    """Post a comment on an existing issue or PR (issues + PRs share the comment endpoint)."""
    return await _client().comment_issue(owner, repo, issue_number, body)


@router.tool()
async def github_close_issue(owner: str, repo: str, issue_number: int) -> dict:
    """Close an issue (sets state='closed')."""
    return await _client().update_issue(owner, repo, issue_number, state="closed")


@router.tool()
async def github_search_issues(query: str, per_page: int = 25) -> dict:
    """Search issues using GitHub search syntax.

    Example queries:
      'repo:owner/name is:open label:bug'
      'is:pr is:open author:dependabot'
    """
    return await _client().search_issues(query, per_page=per_page)


@router.tool()
async def github_review_pr(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    event: str = "COMMENT",
) -> dict:
    """Post a PR review. event: APPROVE | REQUEST_CHANGES | COMMENT."""
    return await _client().review_pull_request(owner, repo, pr_number, body, event)


@router.tool()
async def github_get_repo(owner: str, repo: str) -> dict:
    """Fetch repository metadata (stars, language, topics, etc.)."""
    return await _client().get_repo(owner, repo)
