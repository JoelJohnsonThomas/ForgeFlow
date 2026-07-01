"""Tests for Enterprise Hardening — Increment 1.

Covers: fail-fast config validation, security response headers (isolated +
wired into the real app), and concurrent object-level authorization.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from forgeflow.api.routers.workflows import _assert_can_read_run
from forgeflow.config import Settings
from forgeflow.middleware.security_headers import SecurityHeadersMiddleware
from forgeflow.rbac.models import UserContext


def _settings(**overrides) -> Settings:
    """A baseline-secure Settings, overridable per test. Explicit kwargs take
    precedence over env/.env in pydantic-settings."""
    base = dict(
        api_secret_key="a-sufficiently-strong-secret",
        dev_login_enabled=False,
        dev_login_password="",
        openai_api_key="sk-test-key",
        llm_provider="openai",
        cors_allow_origins="https://app.example.com",
        docs_enabled=False,
        otel_environment="production",
        trusted_proxy_count=1,
    )
    base.update(overrides)
    return Settings(**base)


class TestConfigValidation:
    def test_secure_production_config_passes(self):
        assert _settings().validate_runtime() == []

    def test_default_api_secret_is_flagged(self):
        problems = _settings(api_secret_key="change-me-in-production").validate_runtime()
        assert any("API_SECRET_KEY" in p for p in problems)

    def test_dev_login_in_production_is_flagged(self):
        problems = _settings(dev_login_enabled=True, dev_login_password="x").validate_runtime()
        assert any("DEV_LOGIN_ENABLED" in p for p in problems)

    def test_cors_wildcard_is_flagged(self):
        problems = _settings(cors_allow_origins="*").validate_runtime()
        assert any("CORS" in p for p in problems)

    def test_missing_llm_key_is_flagged(self):
        problems = _settings(llm_provider="openai", openai_api_key="").validate_runtime()
        assert any("OPENAI_API_KEY" in p for p in problems)

    def test_docs_enabled_in_prod_is_flagged(self):
        problems = _settings(docs_enabled=True).validate_runtime()
        assert any("DOCS_ENABLED" in p for p in problems)

    def test_is_production_label(self):
        assert _settings(otel_environment="production").is_production() is True
        assert _settings(otel_environment="staging").is_production() is True
        assert _settings(otel_environment="development").is_production() is False

    def test_dev_config_with_password_is_clean_enough(self):
        # Local dev: dev_login on with a password, development env → no fatal items.
        s = _settings(
            otel_environment="development",
            dev_login_enabled=True,
            dev_login_password="local-pass",
            docs_enabled=True,
            cors_allow_origins="http://localhost:5173",
            trusted_proxy_count=0,
        )
        assert s.validate_runtime() == []


class TestSecurityHeaders:
    @staticmethod
    def _isolated_app() -> FastAPI:
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/x")
        def x():
            return {"ok": True}

        @app.get("/docs")
        def docs():
            return {"docs": True}

        return app

    def test_hardening_headers_present(self):
        c = TestClient(self._isolated_app())
        r = c.get("/x")
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "no-referrer"
        assert "default-src 'none'" in r.headers["content-security-policy"]
        assert "max-age=" in r.headers["strict-transport-security"]

    def test_docs_path_exempt_from_csp_but_keeps_other_headers(self):
        c = TestClient(self._isolated_app())
        r = c.get("/docs")
        assert "content-security-policy" not in r.headers
        assert r.headers["x-content-type-options"] == "nosniff"

    def test_headers_wired_into_real_app(self):
        """Verify main.py actually registers the middleware (open /health path)."""
        with patch("forgeflow.api.main.init_pool", new_callable=AsyncMock), patch(
            "forgeflow.api.main.compile_graph", new_callable=AsyncMock
        ), patch(
            "forgeflow.api.main.get_mcp_tools", new_callable=AsyncMock, return_value=[]
        ), patch(
            "forgeflow.api.main.register_default_agents"
        ), patch(
            "forgeflow.api.main.ApprovalEscalationJob"
        ) as job:
            job.return_value = MagicMock(start=MagicMock(), stop=AsyncMock())
            from forgeflow.api.main import app

            with TestClient(app) as c:
                r = c.get("/health")
                assert r.status_code == 200
                assert r.headers["x-frame-options"] == "DENY"
                assert "default-src 'none'" in r.headers["content-security-policy"]


class TestConcurrentAuthorization:
    @pytest.mark.asyncio
    async def test_concurrent_ownership_checks_are_consistent(self):
        """Hammer the object-level auth check concurrently — a non-owner sales_rep
        must be denied every time, an owner allowed every time, with no leakage
        from interleaving."""
        rep = UserContext(user_id="rep-1", role="sales_rep")

        async def check(owner: str) -> int:
            await asyncio.sleep(0)  # force interleave
            try:
                _assert_can_read_run(rep, row_user_id=owner)
                return 200
            except HTTPException as e:
                return e.status_code

        owners = (["rep-1"] * 50) + (["rep-2"] * 50)
        results = await asyncio.gather(*(check(o) for o in owners))
        assert results.count(200) == 50  # only own runs
        assert results.count(404) == 50  # every foreign run denied
