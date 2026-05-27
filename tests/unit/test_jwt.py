"""Tests for JWT token creation, verification, and the hardened auth middleware.

Updated post-SECURITY_AUDIT.md to cover:
  - aud / iss / nbf / jti enforcement
  - the removal of the API_SECRET wildcard admin shortcut
  - fail-closed behaviour on unmapped routes and missing bearer
  - revocation via /auth/logout → jti denylist
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import jwt as pyjwt
import pytest

from forgeflow.auth.jwt import (
    AUDIENCE,
    ISSUER,
    JWTError,
    create_access_token,
    decode_access_token,
    revoke_token,
)
from forgeflow.config import get_settings
from forgeflow.middleware.auth import RBACMiddleware


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "test-secret-for-jwt-suite")
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "true")
    monkeypatch.setenv("DEV_LOGIN_PASSWORD", "test-dev-password")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestTokenCreationAndDecoding:
    def test_roundtrip_carries_role_and_workspace(self):
        token = create_access_token(user_id="u-1", role="manager", workspace_id="ws-42")
        claims = decode_access_token(token)

        assert claims["sub"] == "u-1"
        assert claims["role"] == "manager"
        assert claims["workspace"] == "ws-42"
        # Hardened claims always present.
        for required in ("exp", "iat", "nbf", "iss", "aud", "jti"):
            assert required in claims

    def test_aud_and_iss_are_pinned(self):
        token = create_access_token(user_id="u-aud", role="viewer")
        claims = decode_access_token(token)
        assert claims["aud"] == AUDIENCE
        assert claims["iss"] == ISSUER

    def test_omits_workspace_claim_when_not_provided(self):
        token = create_access_token(user_id="u-2", role="viewer")
        claims = decode_access_token(token)
        assert "workspace" not in claims

    def test_expired_token_raises(self):
        secret = get_settings().api_secret_key.get_secret_value()
        token = create_access_token(user_id="u-3", role="admin", ttl_hours=1)
        payload = pyjwt.decode(
            token, secret, algorithms=["HS256"], audience=AUDIENCE, issuer=ISSUER
        )
        payload["exp"] = int(time.time()) - 60
        expired = pyjwt.encode(payload, secret, algorithm="HS256")

        with pytest.raises(JWTError, match="expired"):
            decode_access_token(expired)

    def test_invalid_signature_raises(self):
        token = create_access_token(user_id="u-4", role="admin")
        head, body, sig = token.rsplit(".", 2)
        broken = f"{head}.{body}.{'A' if sig[0] != 'A' else 'B'}{sig[1:]}"
        with pytest.raises(JWTError, match="invalid token"):
            decode_access_token(broken)

    def test_wrong_audience_raises(self):
        secret = get_settings().api_secret_key.get_secret_value()
        bad = pyjwt.encode(
            {
                "sub": "u",
                "role": "viewer",
                "iat": int(time.time()),
                "nbf": int(time.time()),
                "exp": int(time.time()) + 60,
                "iss": ISSUER,
                "aud": "someone-else",
                "jti": "x",
            },
            secret,
            algorithm="HS256",
        )
        with pytest.raises(JWTError):
            decode_access_token(bad)

    def test_missing_required_claims_raises(self):
        secret = get_settings().api_secret_key.get_secret_value()
        # Missing jti / aud / iss / nbf — pyjwt's `options={"require": [...]}` rejects.
        bad = pyjwt.encode({"sub": "u-5", "role": "viewer"}, secret, algorithm="HS256")
        with pytest.raises(JWTError):
            decode_access_token(bad)

    def test_revoked_token_rejected(self):
        token = create_access_token(user_id="u-rev", role="admin")
        claims = pyjwt.decode(
            token,
            get_settings().api_secret_key.get_secret_value(),
            algorithms=["HS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
        revoke_token(claims["jti"], claims["exp"])
        with pytest.raises(JWTError, match="revoked"):
            decode_access_token(token)

    def test_placeholder_secret_refuses_to_mint(self, monkeypatch):
        monkeypatch.setenv("API_SECRET_KEY", "change-me-in-production")
        get_settings.cache_clear()
        with pytest.raises(JWTError, match="placeholder"):
            create_access_token(user_id="u", role="admin")


class TestRBACMiddleware:
    """Cover the hardened middleware: no wildcard admin, no header fallback."""

    def _make_middleware(self):
        mw = RBACMiddleware.__new__(RBACMiddleware)
        from forgeflow.rbac.enforcer import RBACEnforcer

        mw.enforcer = RBACEnforcer()
        return mw

    def _request(self, headers: dict, path: str = "/workflows/run", method: str = "POST"):
        request = MagicMock()
        request.headers = headers
        request.url.path = path
        request.method = method
        request.state = MagicMock()
        return request

    @pytest.mark.asyncio
    async def test_missing_bearer_returns_401(self):
        mw = self._make_middleware()
        request = self._request({})
        call_next = AsyncMock()

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 401
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_secret_is_NOT_a_wildcard_admin(self):
        """Regression: SECURITY_AUDIT.md C-2 + C-3 removed this code path."""
        mw = self._make_middleware()
        secret = get_settings().api_secret_key.get_secret_value()
        request = self._request({"Authorization": f"Bearer {secret}"})
        call_next = AsyncMock()

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 401
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_legacy_x_user_id_header_is_ignored(self):
        """Regression: dev fallback removed."""
        mw = self._make_middleware()
        request = self._request({"X-User-Id": "u-1", "X-Role": "admin"})
        call_next = AsyncMock()

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_jwt_for_unmapped_route_fails_closed(self):
        mw = self._make_middleware()
        token = create_access_token(user_id="u", role="admin")
        request = self._request(
            {"Authorization": f"Bearer {token}"},
            path="/unknown/path",
            method="POST",
        )
        call_next = AsyncMock()

        response = await mw.dispatch(request, call_next)
        # admin's *:* normally allows everything, but unmapped routes are
        # rejected before the enforcer check runs.
        assert response.status_code == 403
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_admin_jwt_passes_mapped_route(self):
        mw = self._make_middleware()
        token = create_access_token(user_id="u-adm", role="admin")
        request = self._request({"Authorization": f"Bearer {token}"})
        call_next = AsyncMock(return_value=MagicMock(status_code=200))

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 200
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_viewer_blocked_from_execute(self):
        mw = self._make_middleware()
        token = create_access_token(user_id="u-view", role="viewer")
        request = self._request({"Authorization": f"Bearer {token}"})
        call_next = AsyncMock()

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 403
        call_next.assert_not_called()
