"""Integration tests for FastAPI routes (using httpx AsyncClient)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def client():
    """Create a test client with mocked graph and pool."""
    with patch("forgeflow.api.main.init_pool", new_callable=AsyncMock) as mock_pool, \
         patch("forgeflow.api.main.compile_graph", new_callable=AsyncMock) as mock_graph, \
         patch("forgeflow.api.main.get_mcp_tools", new_callable=AsyncMock, return_value=[]):

        from forgeflow.api.main import app

        # Set up mock state
        mock_pool.return_value = MagicMock()
        mock_graph.return_value = MagicMock()

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "ForgeFlow" in response.json().get("service", "")


def test_docs_accessible(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_rbac_blocks_unauthenticated():
    """Viewer role cannot execute workflows."""
    with patch("forgeflow.api.main.init_pool", new_callable=AsyncMock), \
         patch("forgeflow.api.main.compile_graph", new_callable=AsyncMock), \
         patch("forgeflow.api.main.get_mcp_tools", new_callable=AsyncMock, return_value=[]):

        from forgeflow.api.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            response = c.post(
                "/workflows/run",
                json={"lead_data": {"company_name": "Test"}},
                headers={"X-Role": "viewer"},
            )
            assert response.status_code == 403
