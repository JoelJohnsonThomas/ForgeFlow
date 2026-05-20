"""GitHub connector — issues, PRs, releases, repo metadata.

Uses the GitHub REST API v3 with a personal access token (classic or fine-grained).
For OAuth-app / GitHub-app installations, swap auth_header() to use a JWT or
installation token — the URL surface is identical.

Required scopes for the included operations:
  - repo (read + write issues/PRs)
  - read:org (list_repos in an org)

Settings:
  GITHUB_TOKEN          — PAT or installation token
  GITHUB_BASE_URL       — defaults to https://api.github.com (override for GHES)
  GITHUB_DEFAULT_OWNER  — optional default repo owner so tool calls don't need it
"""

from __future__ import annotations

import logging
from typing import Any

from forgeflow.config import get_settings
from forgeflow.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class GitHubConnector(BaseConnector):
    vendor = "github"

    def __init__(self, token: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            base_url=base_url or settings.github_base_url,
            token=token if token is not None else settings.github_token.get_secret_value(),
        )

    def auth_header(self) -> dict[str, str]:
        # GitHub accepts `Bearer` (PAT + installation) and `token` (classic PAT)
        return {
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ---- Issues ----

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        return await self._request("POST", f"/repos/{owner}/{repo}/issues", json=payload)

    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        state: str | None = None,
        title: str | None = None,
        body: str | None = None,
        labels: list[str] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {}
        if state:
            payload["state"] = state
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if labels is not None:
            payload["labels"] = labels
        return await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            json=payload,
        )

    async def comment_issue(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict:
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )

    async def search_issues(self, query: str, per_page: int = 25) -> dict:
        """GitHub search syntax: 'repo:owner/name is:open label:bug'."""
        return await self._request(
            "GET", "/search/issues", params={"q": query, "per_page": per_page}
        )

    # ---- Pull Requests ----

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict:
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")

    async def review_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
    ) -> dict:
        """event: APPROVE | REQUEST_CHANGES | COMMENT"""
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            json={"body": body, "event": event},
        )

    # ---- Repo ----

    async def get_repo(self, owner: str, repo: str) -> dict:
        return await self._request("GET", f"/repos/{owner}/{repo}")

    async def list_repos(self, owner: str, per_page: int = 30) -> dict:
        """List repos for a user or org."""
        return await self._request(
            "GET", f"/orgs/{owner}/repos", params={"per_page": per_page}
        )
