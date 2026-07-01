"""OIDC bearer verification — validate an external IdP's id_token via JWKS.

Enterprises front ForgeFlow with their own IdP (Okta, Entra ID, Auth0, Keycloak).
`POST /auth/oidc/exchange` accepts that IdP's RS256 id_token, verifies its
signature against the published JWKS plus issuer/audience/expiry, and (on
success) provisions/looks up the matching ForgeFlow user to mint local tokens.

Signing keys are fetched from the IdP's JWKS endpoint and cached by PyJWKClient.
"""

from __future__ import annotations

import logging
from typing import Any

import jwt
from jwt import PyJWKClient

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)


class OIDCError(Exception):
    """Raised when OIDC is disabled/misconfigured or the token fails validation."""


# Cache one JWKS client per URL so we don't refetch keys on every request.
_jwk_clients: dict[str, PyJWKClient] = {}


def _client(jwks_url: str) -> PyJWKClient:
    client = _jwk_clients.get(jwks_url)
    if client is None:
        client = PyJWKClient(jwks_url)
        _jwk_clients[jwks_url] = client
    return client


def verify_oidc_token(id_token: str) -> dict[str, Any]:
    """Verify an external OIDC id_token and return its claims.

    Raises OIDCError when OIDC is disabled, misconfigured, or the token is
    invalid (bad signature / issuer / audience / expiry).
    """
    s = get_settings()
    if not s.oidc_enabled:
        raise OIDCError("OIDC is not enabled")
    if not (s.oidc_jwks_url and s.oidc_issuer and s.oidc_audience):
        raise OIDCError("OIDC is enabled but OIDC_JWKS_URL/ISSUER/AUDIENCE are unset")

    try:
        signing_key = _client(s.oidc_jwks_url).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=s.oidc_audience,
            issuer=s.oidc_issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise OIDCError(f"OIDC token invalid: {exc}") from exc

    if not claims.get("sub"):
        raise OIDCError("OIDC token missing 'sub'")
    return claims
