"""Regression tests for QA-review findings (this session).

Covers three bugs that shipped green because the suite mocks I/O:
  1. SSRF guard crashed on every redirect (httpx.URL.human_repr AttributeError).
  2. Horizontal IDOR — any role could read any run/trace by id.
  3. Schema/code type mismatch — resolved_by / user_id typed UUID but fed strings
     (the approve endpoint 500'd). Guarded via migration assertions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException

from forgeflow.api.routers.workflows import _assert_can_read_run
from forgeflow.rbac.models import UserContext
from forgeflow.security.ssrf_guard import safe_get


# --------------------------------------------------------------------------- #
# 1. SSRF guard must follow redirects without crashing on httpx.URL serialization
# --------------------------------------------------------------------------- #
class TestSSRFRedirect:
    @pytest.mark.asyncio
    async def test_safe_get_follows_redirect(self):
        """A 302 -> 200 chain must resolve. Before the fix, `.human_repr()`
        raised AttributeError on the redirect branch (httpx.URL has no such
        method). Hosts resolve to a public IP via the conftest DNS stub."""
        responses = [
            httpx.Response(302, headers={"location": "https://example.com/final"}),
            httpx.Response(200, content=b"final-body"),
        ]

        async def fake_get(self, url, headers=None):  # noqa: ANN001
            return responses.pop(0)

        with patch.object(httpx.AsyncClient, "get", new=fake_get):
            resp = await safe_get("https://example.com/start")

        assert resp.status_code == 200
        assert resp.content == b"final-body"

    @pytest.mark.asyncio
    async def test_safe_get_handles_relative_redirect(self):
        """Relative Location must join against the current URL (the join path
        is exactly where the .human_repr() crash lived)."""
        responses = [
            httpx.Response(301, headers={"location": "/moved"}),
            httpx.Response(200, content=b"ok"),
        ]

        async def fake_get(self, url, headers=None):  # noqa: ANN001
            return responses.pop(0)

        with patch.object(httpx.AsyncClient, "get", new=fake_get):
            resp = await safe_get("https://example.com/start")

        assert resp.status_code == 200


# --------------------------------------------------------------------------- #
# 2. Object-level authorization (IDOR) on run/trace reads
# --------------------------------------------------------------------------- #
class TestRunReadAuthorization:
    def test_sales_rep_cannot_read_another_users_run(self):
        rep = UserContext(user_id="rep-1", role="sales_rep")
        with pytest.raises(HTTPException) as ei:
            _assert_can_read_run(rep, row_user_id="rep-2")
        # 404 (not 403) so we don't confirm the run exists.
        assert ei.value.status_code == 404

    def test_owner_can_read_own_run(self):
        rep = UserContext(user_id="rep-1", role="sales_rep")
        _assert_can_read_run(rep, row_user_id="rep-1")  # must not raise

    @pytest.mark.parametrize("role", ["admin", "manager", "viewer", "service"])
    def test_elevated_roles_read_any_run(self, role):
        u = UserContext(user_id="someone", role=role)
        _assert_can_read_run(u, row_user_id="a-different-owner")  # must not raise

    def test_non_elevated_with_null_owner_is_denied(self):
        """A legacy run with NULL owner must not be readable by a non-elevated
        role (fail closed rather than leak un-attributed runs)."""
        rep = UserContext(user_id="rep-1", role="sales_rep")
        with pytest.raises(HTTPException):
            _assert_can_read_run(rep, row_user_id=None)


# --------------------------------------------------------------------------- #
# 3. resolved_by / user_id must be string-typed in the schema (not UUID)
# --------------------------------------------------------------------------- #
class TestStringIdMigrations:
    _versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"

    def test_resolved_by_widened_to_varchar(self):
        text = (self._versions / "006_resolved_by_text.py").read_text(encoding="utf-8")
        assert "resolved_by" in text and "VARCHAR" in text

    def test_run_user_id_widened_to_varchar(self):
        text = (self._versions / "007_run_user_id_text.py").read_text(encoding="utf-8")
        assert "user_id" in text and "VARCHAR" in text
