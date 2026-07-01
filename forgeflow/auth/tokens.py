"""Refresh-token service — opaque, hashed, rotating, with reuse detection.

Access tokens are short-lived JWTs (forgeflow.auth.jwt). Refresh tokens are
long-lived opaque random strings; only their SHA-256 hash is stored, so a DB
leak can't be replayed. Every refresh rotates the token within a *family*:

  * Normal refresh  → old token marked used, a new token issued in the family.
  * Replay of an already-used (or revoked) token → the ENTIRE family is revoked
    (classic refresh-token reuse detection — RFC 6819 / OAuth BCP).

This bounds the blast radius of a stolen refresh token to a single use.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)


class RefreshError(Exception):
    """Raised when a refresh token is invalid, expired, or reused."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_opaque() -> str:
    return secrets.token_urlsafe(48)


async def issue_refresh_token(
    pool: asyncpg.Pool, user_id: uuid.UUID, family_id: uuid.UUID | None = None
) -> str:
    """Mint a refresh token (new family unless one is supplied) and return the
    plaintext (stored only as a hash)."""
    token = _new_opaque()
    ttl_days = get_settings().refresh_token_ttl_days
    expires = datetime.now(UTC) + timedelta(days=ttl_days)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO auth_refresh_tokens (user_id, family_id, token_hash, expires_at)
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            family_id or uuid.uuid4(),
            _hash(token),
            expires,
        )
    return token


async def revoke_family(pool: asyncpg.Pool, family_id: uuid.UUID) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE auth_refresh_tokens SET revoked = TRUE WHERE family_id = $1",
            family_id,
        )


async def revoke_by_token(pool: asyncpg.Pool, token: str) -> None:
    """Logout: revoke the whole family the presented token belongs to."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT family_id FROM auth_refresh_tokens WHERE token_hash = $1", _hash(token)
        )
        if row:
            await conn.execute(
                "UPDATE auth_refresh_tokens SET revoked = TRUE WHERE family_id = $1",
                row["family_id"],
            )


async def rotate(pool: asyncpg.Pool, presented: str) -> dict:
    """Validate + rotate a refresh token. Returns the owning user row and a new
    refresh token: ``{"user": <record>, "refresh_token": <str>}``.

    Raises RefreshError on unknown/expired/reused tokens (reused ⇒ family revoked).
    """
    token_hash = _hash(presented)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM auth_refresh_tokens WHERE token_hash = $1", token_hash
        )
        if row is None:
            raise RefreshError("unknown refresh token")

        family_id = row["family_id"]

        # Reuse detection: a revoked or already-rotated token means someone is
        # replaying — burn the whole family so neither party can continue.
        if row["revoked"] or row["used_at"] is not None:
            await conn.execute(
                "UPDATE auth_refresh_tokens SET revoked = TRUE WHERE family_id = $1",
                family_id,
            )
            logger.warning("Refresh-token reuse detected — revoked family %s", family_id)
            raise RefreshError("refresh token reuse detected")

        if row["expires_at"] < datetime.now(UTC):
            raise RefreshError("refresh token expired")

        user = await conn.fetchrow("SELECT * FROM auth_users WHERE id = $1", row["user_id"])
        if user is None or user["disabled"]:
            raise RefreshError("user disabled or missing")

        # Rotate: mark this token used, then issue a successor in the same family.
        await conn.execute(
            "UPDATE auth_refresh_tokens SET used_at = now() WHERE id = $1", row["id"]
        )

    new_token = await issue_refresh_token(pool, user["id"], family_id=family_id)
    return {"user": user, "refresh_token": new_token}
