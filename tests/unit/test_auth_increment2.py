"""Unit tests for Increment-2 auth primitives: Argon2 passwords, TOTP MFA,
and OIDC (JWKS) verification. DB-backed refresh-token rotation is covered in
tests/integration/test_auth_db.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
import pyotp
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from forgeflow.auth import mfa, passwords
from forgeflow.auth.oidc import OIDCError, verify_oidc_token


class TestPasswords:
    def test_hash_and_verify_roundtrip(self):
        h = passwords.hash_password("s3cr3t-pw")
        assert h != "s3cr3t-pw"  # never stored in plaintext
        assert passwords.verify_password(h, "s3cr3t-pw") is True

    def test_wrong_password_fails(self):
        h = passwords.hash_password("correct")
        assert passwords.verify_password(h, "wrong") is False

    def test_none_or_garbage_hash_is_false_not_error(self):
        assert passwords.verify_password(None, "x") is False
        assert passwords.verify_password("not-a-hash", "x") is False

    def test_hashes_are_salted_and_unique(self):
        assert passwords.hash_password("same") != passwords.hash_password("same")


class TestMfa:
    def test_verify_live_code(self):
        secret = mfa.generate_secret()
        code = pyotp.TOTP(secret).now()
        assert mfa.verify_code(secret, code) is True

    def test_wrong_code_fails(self):
        secret = mfa.generate_secret()
        assert mfa.verify_code(secret, "000000") is False

    def test_missing_inputs_are_false(self):
        assert mfa.verify_code(None, "123456") is False
        assert mfa.verify_code(mfa.generate_secret(), None) is False

    def test_provisioning_uri_shape(self):
        uri = mfa.provisioning_uri("rep-1", mfa.generate_secret())
        assert uri.startswith("otpauth://totp/")
        assert "ForgeFlow" in uri


class TestOidc:
    @staticmethod
    def _keypair():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        pub = key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return priv, pub

    @staticmethod
    def _settings(**over):
        base = dict(
            oidc_enabled=True,
            oidc_issuer="https://idp.example.com",
            oidc_audience="forgeflow",
            oidc_jwks_url="https://idp.example.com/jwks",
        )
        base.update(over)
        return SimpleNamespace(**base)

    def _token(self, priv, **over):
        now = datetime.now(UTC)
        claims = {
            "sub": "user-123",
            "iss": "https://idp.example.com",
            "aud": "forgeflow",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "email": "alice@example.com",
        }
        claims.update(over)
        return jwt.encode(claims, priv, algorithm="RS256")

    def test_disabled_raises(self):
        with patch(
            "forgeflow.auth.oidc.get_settings",
            return_value=self._settings(oidc_enabled=False),
        ), pytest.raises(OIDCError):
            verify_oidc_token("whatever")

    def test_valid_token_returns_claims(self):
        priv, pub = self._keypair()
        token = self._token(priv)
        fake_client = MagicMock()
        fake_client.get_signing_key_from_jwt.return_value = SimpleNamespace(key=pub)
        with patch("forgeflow.auth.oidc.get_settings", return_value=self._settings()), patch(
            "forgeflow.auth.oidc._client", return_value=fake_client
        ):
            claims = verify_oidc_token(token)
        assert claims["sub"] == "user-123"
        assert claims["email"] == "alice@example.com"

    def test_wrong_audience_rejected(self):
        priv, pub = self._keypair()
        token = self._token(priv, aud="some-other-app")
        fake_client = MagicMock()
        fake_client.get_signing_key_from_jwt.return_value = SimpleNamespace(key=pub)
        with patch("forgeflow.auth.oidc.get_settings", return_value=self._settings()), patch(
            "forgeflow.auth.oidc._client", return_value=fake_client
        ), pytest.raises(OIDCError):
            verify_oidc_token(token)

    def test_expired_token_rejected(self):
        priv, pub = self._keypair()
        past = datetime.now(UTC) - timedelta(hours=1)
        token = self._token(priv, exp=int(past.timestamp()), iat=int(past.timestamp()))
        fake_client = MagicMock()
        fake_client.get_signing_key_from_jwt.return_value = SimpleNamespace(key=pub)
        with patch("forgeflow.auth.oidc.get_settings", return_value=self._settings()), patch(
            "forgeflow.auth.oidc._client", return_value=fake_client
        ), pytest.raises(OIDCError):
            verify_oidc_token(token)
