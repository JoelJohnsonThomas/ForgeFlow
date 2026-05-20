"""Tests for JWT token creation, verification, and the auth middleware path."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeflow.auth.jwt import JWTError, create_access_token, decode_access_token
from forgeflow.config import get_settings
from forgeflow.middleware.auth import RBACMiddleware


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "test-secret-for-jwt-suite")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestTokenCreationAndDecoding:
    def test_roundtrip_carries_role_and_workspace(self):
        token = create_access_token(
            user_id="u-1",
            role="manager",
            workspace_id="ws-42",
        )
        claims = decode_access_token(token)

        assert claims["sub"] == "u-1"
        assert claims["role"] == "manager"
        assert claims["workspace"] == "ws-42"
        assert "exp" in claims
        assert "iat" in claims

    def test_omits_workspace_claim_when_not_provided(self):
        token = create_access_token(user_id="u-2", role="viewer")
        claims = decode_access_token(token)

        assert "workspace" not in claims

    def test_expired_token_raises(self):
        token = create_access_token(user_id="u-3", role="admin", ttl_hours=1)

        # Tamper with `exp` by re-issuing in the past via direct encode
        import jwt as pyjwt
        settings = get_settings()
        secret = settings.api_secret_key.get_secret_value()
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
        payload["exp"] = int(time.time()) - 60
        expired = pyjwt.encode(payload, secret, algorithm="HS256")

        with pytest.raises(JWTError, match="expired"):
            decode_access_token(expired)

    def test_invalid_signature_raises(self):
        token = create_access_token(user_id="u-4", role="admin")
        # Flip a character in the signature segment
        head, body, sig = token.rsplit(".", 2)
        broken = f"{head}.{body}.{'A' if sig[0] != 'A' else 'B'}{sig[1:]}"

        with pytest.raises(JWTError, match="invalid token"):
            decode_access_token(broken)

    def test_missing_required_claims_raises(self):
        # Build a token without 'role' to ensure decode_access_token defends
        import jwt as pyjwt
        secret = get_settings().api_secret_key.get_secret_value()
        bad = pyjwt.encode({"sub": "u-5"}, secret, algorithm="HS256")

        with pytest.raises(JWTError, match="missing required claims"):
            decode_access_token(bad)


class TestRBACMiddlewareWithJWT:
    """The middleware now prefers JWT but accepts X-Role as a fallback."""

    def _make_middleware(self):
        mw = RBACMiddleware.__new__(RBACMiddleware)
        from forgeflow.rbac.enforcer import RBACEnforcer
        mw.enforcer = RBACEnforcer()
        return mw

    def _request(self, headers: dict):
        request = MagicMock()
        request.headers = headers
        request.url.path = "/workflows/run"
        request.method = "POST"
        request.state = MagicMock()
        return request

    def test_extracts_identity_from_valid_jwt(self):
        token = create_access_token(user_id="u-1", role="sales_rep", workspace_id="ws-1")
        mw = self._make_middleware()
        request = self._request({"Authorization": f"Bearer {token}"})

        user_id, role, workspace, error = mw._extract_from_jwt(request)
        assert user_id == "u-1"
        assert role == "sales_rep"
        assert workspace == "ws-1"
        assert error is None

    def test_invalid_jwt_returns_error_message(self):
        mw = self._make_middleware()
        request = self._request({"Authorization": "Bearer not-a-real-token"})

        user_id, role, workspace, error = mw._extract_from_jwt(request)
        assert user_id is None
        assert error is not None and "invalid" in error.lower()

    def test_no_auth_header_returns_all_none(self):
        mw = self._make_middleware()
        request = self._request({})

        user_id, role, workspace, error = mw._extract_from_jwt(request)
        assert (user_id, role, workspace, error) == (None, None, None, None)

    def test_api_secret_key_acts_as_service_token(self):
        mw = self._make_middleware()
        secret = get_settings().api_secret_key.get_secret_value()
        request = self._request({"Authorization": f"Bearer {secret}"})

        user_id, role, _, error = mw._extract_from_jwt(request)
        assert user_id == "service"
        assert role == "admin"
        assert error is None

    @pytest.mark.asyncio
    async def test_middleware_rejects_expired_token(self):
        import jwt as pyjwt
        secret = get_settings().api_secret_key.get_secret_value()
        expired = pyjwt.encode(
            {"sub": "u", "role": "viewer", "exp": int(time.time()) - 60},
            secret,
            algorithm="HS256",
        )

        mw = self._make_middleware()
        request = self._request({"Authorization": f"Bearer {expired}"})
        call_next = AsyncMock()

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 401
        call_next.assert_not_called()
