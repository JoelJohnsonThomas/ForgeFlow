"""Integration tests for MCP server tool invocation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMCPSearchTools:
    @pytest.mark.asyncio
    async def test_web_search_mock_mode(self):
        """web_search returns mock results when Tavily is not configured."""
        with patch("forgeflow.mcp.server.tools.search_tools.get_settings") as mock_settings:
            settings = MagicMock()
            settings.is_tavily_enabled.return_value = False
            mock_settings.return_value = settings

            from forgeflow.mcp.server.tools.search_tools import web_search

            results = await web_search("Stripe funding", max_results=3)

        assert isinstance(results, list)
        assert len(results) >= 1
        assert "content" in results[0]

    @pytest.mark.asyncio
    async def test_scrape_url_returns_text(self):
        """scrape_url should return cleaned text from an HTTP response."""
        fake_html = "<html><body><p>Stripe is a fintech company.</p><script>ignored</script></body></html>"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_resp = MagicMock()
            mock_resp.text = fake_html
            mock_resp.raise_for_status = MagicMock()

            async_client = AsyncMock()
            async_client.__aenter__ = AsyncMock(return_value=async_client)
            async_client.__aexit__ = AsyncMock(return_value=None)
            async_client.get = AsyncMock(return_value=mock_resp)
            mock_client_class.return_value = async_client

            from forgeflow.mcp.server.tools.search_tools import scrape_url

            text = await scrape_url("https://stripe.com")

        assert "Stripe" in text
        assert "ignored" not in text  # Script tags stripped

    @pytest.mark.asyncio
    async def test_scrape_url_handles_error(self):
        """scrape_url should return error string on failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            async_client = AsyncMock()
            async_client.__aenter__ = AsyncMock(return_value=async_client)
            async_client.__aexit__ = AsyncMock(return_value=None)
            async_client.get = AsyncMock(side_effect=Exception("connection refused"))
            mock_client_class.return_value = async_client

            from forgeflow.mcp.server.tools.search_tools import scrape_url

            result = await scrape_url("https://unreachable.example.com")

        assert "Error" in result or "error" in result.lower()


class TestMCPCRMTools:
    @pytest.mark.asyncio
    async def test_create_lead(self):
        """create_lead should return a lead dict with an id."""
        from forgeflow.mcp.server.tools.crm_tools import create_lead

        result = await create_lead(
            company_name="Acme Corp",
            contact_email="ceo@acme.com",
            industry="saas",
        )

        assert "id" in result
        assert result["company_name"] == "Acme Corp"
        assert result["status"] == "raw"

    @pytest.mark.asyncio
    async def test_update_lead_status(self):
        """update_lead should change lead status."""
        from forgeflow.mcp.server.tools.crm_tools import create_lead, update_lead

        created = await create_lead(company_name="BetaCorp")
        lead_id = created["id"]

        updated = await update_lead(lead_id=lead_id, status="qualified")
        assert updated["status"] == "qualified"

    @pytest.mark.asyncio
    async def test_get_lead(self):
        """get_lead should retrieve a previously created lead."""
        from forgeflow.mcp.server.tools.crm_tools import create_lead, get_lead

        created = await create_lead(company_name="GammaCorp", industry="healthcare")
        lead_id = created["id"]

        retrieved = await get_lead(lead_id=lead_id)
        assert retrieved["company_name"] == "GammaCorp"
        assert retrieved["id"] == lead_id

    @pytest.mark.asyncio
    async def test_get_lead_not_found(self):
        """get_lead should return error dict for missing lead."""
        from forgeflow.mcp.server.tools.crm_tools import get_lead

        result = await get_lead(lead_id="nonexistent-id-123")
        assert "error" in result


class TestMCPEmailTools:
    @pytest.mark.asyncio
    async def test_draft_email(self):
        """draft_email should return a draft dict with subject and body."""
        from forgeflow.mcp.server.tools.email_tools import draft_email

        result = await draft_email(
            to="ceo@stripe.com",
            subject="Partnership Proposal",
            context="Stripe is a leading fintech company",
        )

        assert "draft_id" in result
        assert "subject" in result
        assert "body" in result

    @pytest.mark.asyncio
    async def test_send_email(self):
        """send_email should return a success confirmation with message_id."""
        from forgeflow.mcp.server.tools.email_tools import send_email

        result = await send_email(
            to="ceo@stripe.com",
            subject="Partnership Proposal",
            body="Dear CEO, we'd like to propose a partnership...",
            allowed_domains=["stripe.com"],
        )

        assert "message_id" in result
        assert result.get("success") is True
