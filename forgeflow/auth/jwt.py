"""JWT issuance + verification.

Hardened post-audit:
  - aud / iss / nbf / jti claims added; all verified on decode.
  - Default TTL dropped to 1 hour (was 24).
  - HS256 retained for OSS dev — flagged for RS256 + KMS migration in
    SECURITY_AUDIT.md. The signing secret is now used *only* for JWT signing;
    the old "API_SECRET as wildcard admin bearer" code path has been removed
    from middleware/auth.py.
  - Revocation hook is in-process today (set-based denylist with TTL via
    asyncio.TimerHandle). Production should swap _RevocationStore for a Redis
    SETEX-based store — interface intentionally narrow.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
DEFAULT_TTL_HOURS = 1
ISSUER = "forgeflow-api"
AUDIENCE = "forgeflow-api"


class JWTError(Exception):
    """Raised when a JWT cannot be decoded or has expired."""


class _RevocationStore:
    """In-process jti denylist with TTL eviction.

    Production should replace with Redis: SETEX jti <ttl> "" / EXISTS jti.
    The interface (revoke, is_revoked) matches what a Redis-backed impl needs.
    """

    def __init__(self) -> None:
        self._entries: dict[str, float] = {}
        self._lock = threading.Lock()

    def revoke(self, jti: str, exp_epoch: int) -> None:
        with self._lock:
            self._entries[jti] = float(exp_epoch)
            self._sweep_locked()

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            self._sweep_locked()
            return jti in self._entries

    def _sweep_locked(self) -> None:
        now = time.time()
        expired = [k for k, exp in self._entries.items() if exp <= now]
        for k in expired:
            self._entries.pop(k, None)


_revocations = _RevocationStore()


def revoke_token(jti: str, exp_epoch: int) -> None:
    """Add a jti to the denylist until its natural exp."""
    _revocations.revoke(jti, exp_epoch)


def create_access_token(
    user_id: str,
    role: str,
    workspace_id: str | None = None,
    ttl_hours: int = DEFAULT_TTL_HOURS,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Issue a signed JWT for the given identity.

    Adds aud, iss, nbf, jti so the token can be replay-detected and revoked.
    """
    settings = get_settings()
    secret = settings.api_secret_key.get_secret_value()
    if not secret or secret == "change-me-in-production":
        # Refuse to mint tokens with a placeholder secret — silent failure
        # here would let a misconfigured deploy issue tokens any attacker
        # could forge.
        raise JWTError(
            "API_SECRET_KEY is unset or placeholder — refusing to mint tokens"
        )

    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ttl_hours)).timestamp()),
        "iss": ISSUER,
        "aud": AUDIENCE,
        "jti": str(uuid.uuid4()),
    }
    if workspace_id:
        payload["workspace"] = workspace_id
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify signature + expiry + aud/iss/nbf + revocation and return claims.

    Raises JWTError on any failure.
    """
    settings = get_settings()
    secret = settings.api_secret_key.get_secret_value()

    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise JWTError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise JWTError(f"invalid token: {exc}") from exc

    if "sub" not in claims or "role" not in claims:
        raise JWTError("token missing required claims (sub, role)")

    jti = claims.get("jti", "")
    if jti and _revocations.is_revoked(jti):
        raise JWTError("token revoked")

    return claims
