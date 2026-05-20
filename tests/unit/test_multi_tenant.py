"""Tests for the multi-tenant foundation: JWT claim, middleware state,
and the workspace_id filter on the two endpoints scoped in Phase 3.5."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.api.dependencies import get_workspace_id
from forgeflow.auth.jwt import create_access_token, decode_access_token
from forgeflow.config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "test-secret-for-mt-suite")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestJWTWorkspaceClaim:
    def test_workspace_id_roundtrips_in_jwt(self):
        ws_id = str(uuid.uuid4())
        token = create_access_token(user_id="u-1", role="manager", workspace_id=ws_id)
        claims = decode_access_token(token)
        assert claims["workspace"] == ws_id

    def test_no_workspace_means_no_claim(self):
        token = create_access_token(user_id="u-1", role="viewer")
        claims = decode_access_token(token)
        assert "workspace" not in claims


class TestWorkspaceDependency:
    @pytest.mark.asyncio
    async def test_returns_request_state_value(self):
        request = MagicMock()
        request.state.workspace_id = "ws-abc"
        result = await get_workspace_id(request)
        assert result == "ws-abc"

    @pytest.mark.asyncio
    async def test_returns_none_when_unset(self):
        request = MagicMock(spec=[])  # no .state attribute at all
        # Build a state shim that returns None for missing attrs
        state = MagicMock()
        del state.workspace_id  # ensure attribute is missing
        request.state = state
        result = await get_workspace_id(request)
        assert result is None


class TestAuditWorkspaceFilter:
    """Verify the audit search adds a workspace_id clause that varies with the dependency."""

    @pytest.mark.asyncio
    async def test_workspace_id_present_filters_by_uuid(self):
        from forgeflow.api.routers.audit import search_audit_log

        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"n": 0})
        conn.fetch = AsyncMock(return_value=[])
        pool = MagicMock()
        pool.acquire = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=conn),
                __aexit__=AsyncMock(return_value=None),
            )
        )

        ws_id = str(uuid.uuid4())
        await search_audit_log(pool=pool, workspace_id=ws_id)

        count_sql = conn.fetchrow.call_args[0][0]
        assert "workspace_id = $" in count_sql
        # The first positional param after the SQL is workspace_id
        assert uuid.UUID(ws_id) in conn.fetchrow.call_args[0]

    @pytest.mark.asyncio
    async def test_workspace_id_none_filters_to_null_rows(self):
        from forgeflow.api.routers.audit import search_audit_log

        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"n": 0})
        conn.fetch = AsyncMock(return_value=[])
        pool = MagicMock()
        pool.acquire = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=conn),
                __aexit__=AsyncMock(return_value=None),
            )
        )

        await search_audit_log(pool=pool, workspace_id=None)

        count_sql = conn.fetchrow.call_args[0][0]
        assert "workspace_id IS NULL" in count_sql


class TestAuditUUIDGuard:
    """The audit middleware must not crash when user_id is a non-UUID string
    like 'anonymous' or 'service' — the column is UUID-typed."""

    def test_is_uuid_accepts_uuid(self):
        from forgeflow.middleware.audit import _is_uuid

        assert _is_uuid(str(uuid.uuid4())) is True

    def test_is_uuid_rejects_anonymous(self):
        from forgeflow.middleware.audit import _is_uuid

        assert _is_uuid("anonymous") is False
        assert _is_uuid("service") is False
        assert _is_uuid("") is False
