"""Tests for the Jira connector — Basic auth + ADF body wrapping."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forgeflow.config import get_settings
from forgeflow.connectors.jira import JiraConnector, _adf_from_text


@pytest.fixture(autouse=True)
def _reset():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _captured(payload: dict, status: int = 200):
    captured: list[dict] = []

    fake_response = MagicMock()
    fake_response.status_code = status
    fake_response.content = b'{}'
    fake_response.json = MagicMock(return_value=payload)

    async def _request(method, url, params=None, json=None, headers=None):
        captured.append({"method": method, "url": url, "json": json, "headers": headers})
        return fake_response

    fake_client = MagicMock()
    fake_client.request = AsyncMock(side_effect=_request)
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=fake_client)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    return lambda *a, **kw: fake_cm, captured


class TestEnablement:
    def test_missing_email_means_disabled(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        get_settings.cache_clear()
        assert JiraConnector().is_enabled() is False

    def test_missing_token_means_disabled(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "me@acme.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "")
        get_settings.cache_clear()
        assert JiraConnector().is_enabled() is False

    def test_missing_base_url_means_disabled(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "")
        monkeypatch.setenv("JIRA_EMAIL", "me@acme.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        get_settings.cache_clear()
        assert JiraConnector().is_enabled() is False

    def test_all_three_present_means_enabled(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "me@acme.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        get_settings.cache_clear()
        assert JiraConnector().is_enabled() is True


class TestAuth:
    def test_basic_auth_header_format(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "me@acme.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "secret")
        get_settings.cache_clear()

        header = JiraConnector().auth_header()
        expected = base64.b64encode(b"me@acme.com:secret").decode()
        assert header["Authorization"] == f"Basic {expected}"


class TestADFWrapper:
    def test_empty_text_returns_empty_doc(self):
        adf = _adf_from_text("")
        assert adf["type"] == "doc"
        assert adf["content"] == []

    def test_text_wrapped_in_paragraph(self):
        adf = _adf_from_text("hello")
        assert adf["content"][0]["type"] == "paragraph"
        assert adf["content"][0]["content"][0]["text"] == "hello"


class TestCreateIssue:
    @pytest.mark.asyncio
    async def test_disabled_returns_mock(self, monkeypatch):
        monkeypatch.setenv("JIRA_EMAIL", "")
        get_settings.cache_clear()
        result = await JiraConnector().create_issue("ENG", "summary")
        assert result["mock"] is True

    @pytest.mark.asyncio
    async def test_enabled_posts_correct_payload(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "me@acme.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "secret")
        get_settings.cache_clear()

        factory, captured = _captured({"key": "ENG-1"})

        with patch("httpx.AsyncClient", side_effect=factory):
            await JiraConnector().create_issue(
                project_key="ENG",
                summary="Fix bug",
                description="It crashes",
                issue_type="Bug",
                labels=["urgent"],
            )

        call = captured[0]
        assert call["method"] == "POST"
        assert call["url"].endswith("/rest/api/3/issue")
        fields = call["json"]["fields"]
        assert fields["project"] == {"key": "ENG"}
        assert fields["summary"] == "Fix bug"
        assert fields["issuetype"] == {"name": "Bug"}
        assert fields["labels"] == ["urgent"]
        # description must be ADF, not raw string
        assert fields["description"]["type"] == "doc"


class TestSearchAndTransition:
    @pytest.mark.asyncio
    async def test_search_posts_jql(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "me@acme.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "secret")
        get_settings.cache_clear()

        factory, captured = _captured({"issues": []})

        with patch("httpx.AsyncClient", side_effect=factory):
            await JiraConnector().search("project = ENG", max_results=10)

        assert captured[0]["url"].endswith("/rest/api/3/search")
        assert captured[0]["json"] == {"jql": "project = ENG", "maxResults": 10}

    @pytest.mark.asyncio
    async def test_transition_wraps_id(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://acme.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "me@acme.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "secret")
        get_settings.cache_clear()

        factory, captured = _captured({})

        with patch("httpx.AsyncClient", side_effect=factory):
            await JiraConnector().transition_issue("ENG-7", "31")

        assert captured[0]["url"].endswith("/rest/api/3/issue/ENG-7/transitions")
        assert captured[0]["json"] == {"transition": {"id": "31"}}
