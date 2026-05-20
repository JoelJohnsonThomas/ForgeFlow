"""Tests for the BaseConnector pattern."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from forgeflow.connectors.base import (
    BaseConnector,
    ConnectorError,
    mock_response,
)


class _Fake(BaseConnector):
    vendor = "fake"


class TestMockResponse:
    def test_mock_dict_shape(self):
        result = mock_response("fake", "POST /things", foo="bar")
        assert result["mock"] is True
        assert result["vendor"] == "fake"
        assert result["operation"] == "POST /things"
        assert result["foo"] == "bar"
        assert "mock_id" in result


class TestDisabledConnector:
    @pytest.mark.asyncio
    async def test_no_token_returns_mock(self):
        c = _Fake(base_url="https://api.example.com", token=None)
        assert c.is_enabled() is False
        result = await c._request("GET", "/anything", params={"q": "x"})
        assert result["mock"] is True
        assert result["vendor"] == "fake"

    @pytest.mark.asyncio
    async def test_empty_token_returns_mock(self):
        c = _Fake(base_url="https://api.example.com", token="")
        result = await c._request("POST", "/things", json={"x": 1})
        assert result["mock"] is True


class TestEnabledConnector:
    @pytest.mark.asyncio
    async def test_success_returns_parsed_json(self):
        c = _Fake(base_url="https://api.example.com", token="t")

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.content = b'{"hello": "world"}'
        fake_response.json = MagicMock(return_value={"hello": "world"})

        fake_client = MagicMock()
        fake_client.request = AsyncMock(return_value=fake_response)
        fake_client_cm = MagicMock()
        fake_client_cm.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=fake_client_cm):
            result = await c._request("GET", "/things")

        assert result == {"hello": "world"}

    @pytest.mark.asyncio
    async def test_4xx_raises_connector_error(self):
        c = _Fake(base_url="https://api.example.com", token="t")

        fake_response = MagicMock()
        fake_response.status_code = 404
        fake_response.json = MagicMock(return_value={"message": "not found"})

        fake_client = MagicMock()
        fake_client.request = AsyncMock(return_value=fake_response)
        fake_client_cm = MagicMock()
        fake_client_cm.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=fake_client_cm), pytest.raises(
            ConnectorError
        ) as exc_info:
            await c._request("GET", "/things")

        assert exc_info.value.status_code == 404
        assert exc_info.value.vendor == "fake"

    @pytest.mark.asyncio
    async def test_transport_error_wrapped_in_connector_error(self):
        c = _Fake(base_url="https://api.example.com", token="t")

        fake_client = MagicMock()
        fake_client.request = AsyncMock(
            side_effect=httpx.ConnectError("dns lookup failed")
        )
        fake_client_cm = MagicMock()
        fake_client_cm.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=fake_client_cm), pytest.raises(
            ConnectorError
        ) as exc_info:
            await c._request("GET", "/things")

        assert exc_info.value.status_code == 0
        assert "dns lookup failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_dict(self):
        c = _Fake(base_url="https://api.example.com", token="t")

        fake_response = MagicMock()
        fake_response.status_code = 204
        fake_response.content = b""

        fake_client = MagicMock()
        fake_client.request = AsyncMock(return_value=fake_response)
        fake_client_cm = MagicMock()
        fake_client_cm.__aenter__ = AsyncMock(return_value=fake_client)
        fake_client_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=fake_client_cm):
            result = await c._request("DELETE", "/things/1")

        assert result == {}


class TestAuthHeader:
    def test_bearer_by_default(self):
        c = _Fake(base_url="https://x", token="abc123")
        assert c.auth_header() == {"Authorization": "Bearer abc123"}
