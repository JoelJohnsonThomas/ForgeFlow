"""Tests for the GitHub connector — graceful-degradation + URL/body shape."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.connectors.github import GitHubConnector


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _captured_client_with(response_payload: dict, status_code: int = 200):
    """Return (client_factory, captured_calls). client_factory replaces httpx.AsyncClient
    and records every .request() call so tests can assert the exact request shape."""
    captured: list[dict] = []

    fake_response = MagicMock()
    fake_response.status_code = status_code
    fake_response.content = b'{}'  # non-empty so _request goes to .json()
    fake_response.json = MagicMock(return_value=response_payload)

    async def _request(method, url, params=None, json=None, headers=None):
        captured.append({"method": method, "url": url, "params": params, "json": json, "headers": headers})
        return fake_response

    fake_client = MagicMock()
    fake_client.request = AsyncMock(side_effect=_request)
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=fake_client)
    fake_cm.__aexit__ = AsyncMock(return_value=None)

    return lambda *a, **kw: fake_cm, captured


class TestDisabled:
    @pytest.mark.asyncio
    async def test_no_token_returns_mock(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "")
        get_settings.cache_clear()

        result = await GitHubConnector().create_issue("o", "r", "title", "body")

        assert result["mock"] is True
        assert result["vendor"] == "github"


class TestRequestShape:
    @pytest.mark.asyncio
    async def test_create_issue_posts_to_correct_url(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        get_settings.cache_clear()

        factory, captured = _captured_client_with({"number": 42})

        with patch("httpx.AsyncClient", side_effect=factory):
            result = await GitHubConnector().create_issue(
                "myorg", "myrepo", "Bug", "details", labels=["bug"], assignees=["alice"]
            )

        assert result["number"] == 42
        call = captured[0]
        assert call["method"] == "POST"
        assert call["url"].endswith("/repos/myorg/myrepo/issues")
        assert call["json"] == {
            "title": "Bug",
            "body": "details",
            "labels": ["bug"],
            "assignees": ["alice"],
        }
        # GitHub-specific headers should be present
        assert call["headers"]["X-GitHub-Api-Version"] == "2022-11-28"
        assert call["headers"]["Authorization"] == "Bearer ghp_test"

    @pytest.mark.asyncio
    async def test_close_issue_sends_state_closed(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        get_settings.cache_clear()

        factory, captured = _captured_client_with({"state": "closed"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await GitHubConnector().update_issue("o", "r", 7, state="closed")

        call = captured[0]
        assert call["method"] == "PATCH"
        assert call["url"].endswith("/repos/o/r/issues/7")
        assert call["json"] == {"state": "closed"}

    @pytest.mark.asyncio
    async def test_search_issues_uses_query_param(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        get_settings.cache_clear()

        factory, captured = _captured_client_with({"items": [], "total_count": 0})

        with patch("httpx.AsyncClient", side_effect=factory):
            await GitHubConnector().search_issues("repo:foo/bar is:open", per_page=10)

        assert captured[0]["url"].endswith("/search/issues")
        assert captured[0]["params"] == {"q": "repo:foo/bar is:open", "per_page": 10}

    @pytest.mark.asyncio
    async def test_review_pr_includes_event(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        get_settings.cache_clear()

        factory, captured = _captured_client_with({"id": 1})

        with patch("httpx.AsyncClient", side_effect=factory):
            await GitHubConnector().review_pull_request(
                "o", "r", 42, body="LGTM", event="APPROVE"
            )

        assert captured[0]["url"].endswith("/repos/o/r/pulls/42/reviews")
        assert captured[0]["json"] == {"body": "LGTM", "event": "APPROVE"}
