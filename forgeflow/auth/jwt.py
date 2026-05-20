"""JWT issuance + verification.

Replaces the dev-only X-User-Id / X-Role header pattern. Tokens carry:
  - sub        user_id (string)
  - role       one of: admin | manager | sales_rep | viewer
  - workspace  workspace_id (for Phase 3.5 multi-tenant isolation; optional)
  - exp        expiry epoch seconds
  - iat        issued-at epoch seconds

Tokens are HS256-signed with settings.api_secret_key. In production this
should be swapped to RS256 with a key pair so verifiers don't need the signing
secret — that's a follow-up issue, not a Phase 3 blocker.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
DEFAULT_TTL_HOURS = 24


class JWTError(Exception):
    """Raised when a JWT cannot be decoded or has expired."""


def create_access_token(
    user_id: str,
    role: str,
    workspace_id: str | None = None,
    ttl_hours: int = DEFAULT_TTL_HOURS,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Issue a signed JWT for the given identity."""
    settings = get_settings()
    secret = settings.api_secret_key.get_secret_value()
    now = datetime.now(UTC)

    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ttl_hours)).timestamp()),
    }
    if workspace_id:
        payload["workspace"] = workspace_id
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, secret, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify signature + expiry and return the claims.

    Raises JWTError on any failure — invalid signature, expired token,
    malformed payload, or missing required claims.
    """
    settings = get_settings()
    secret = settings.api_secret_key.get_secret_value()

    try:
        claims = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise JWTError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise JWTError(f"invalid token: {exc}") from exc

    if "sub" not in claims or "role" not in claims:
        raise JWTError("token missing required claims (sub, role)")

    return claims
