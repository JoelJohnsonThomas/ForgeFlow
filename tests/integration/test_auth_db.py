"""DB-integration tests for refresh-token rotation + reuse detection.

Runs against a live Postgres (the docker-compose DB on :5433 by default) and
skips cleanly when one isn't reachable. This is the kind of real-schema
coverage whose absence let the `resolved_by` UUID bug ship — here it exercises
forgeflow.auth.tokens against actual tables.
"""

from __future__ import annotations

import os
import socket
import uuid

import asyncpg
import pytest

from forgeflow.auth import tokens
from forgeflow.auth.tokens import RefreshError

# Captured at import (before conftest's autouse DNS stub is installed) so we can
# reach a real 127.0.0.1 instead of the stubbed public IP.
_REAL_GETADDRINFO = socket.getaddrinfo
_DSN = os.environ.get("FF_TEST_DSN", "postgresql://forgeflow:forgeflow@127.0.0.1:5433/forgeflow")


@pytest.fixture
async def pool(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _REAL_GETADDRINFO)
    try:
        p = await asyncpg.create_pool(_DSN, min_size=1, max_size=2, timeout=4)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"live Postgres not reachable ({exc})")
    async with p.acquire() as conn:
        if not await conn.fetchval("SELECT to_regclass('public.auth_refresh_tokens')"):
            await p.close()
            pytest.skip("migration 009 not applied on the target DB")
    yield p
    await p.close()


async def _make_user(pool) -> asyncpg.Record:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "INSERT INTO auth_users (username, role, auth_provider) "
            "VALUES ($1, 'sales_rep', 'local') RETURNING *",
            f"pytest-{uuid.uuid4().hex[:10]}",
        )


@pytest.mark.asyncio
async def test_rotation_and_reuse_detection(pool):
    user = await _make_user(pool)
    try:
        t1 = await tokens.issue_refresh_token(pool, user["id"])
        rotated = await tokens.rotate(pool, t1)
        t2 = rotated["refresh_token"]

        assert t2 != t1  # rotation issues a fresh token
        assert str(rotated["user"]["id"]) == str(user["id"])

        # Replaying the rotated (now-used) token is reuse → whole family revoked.
        with pytest.raises(RefreshError):
            await tokens.rotate(pool, t1)

        # ...and the successor t2 is collateral-revoked with the family.
        with pytest.raises(RefreshError):
            await tokens.rotate(pool, t2)
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM auth_users WHERE id = $1", user["id"])


@pytest.mark.asyncio
async def test_unknown_token_rejected(pool):
    with pytest.raises(RefreshError):
        await tokens.rotate(pool, "definitely-not-a-real-token")


@pytest.mark.asyncio
async def test_happy_path_multi_rotation(pool):
    """A token can be rotated repeatedly as long as each successor is used once."""
    user = await _make_user(pool)
    try:
        tok = await tokens.issue_refresh_token(pool, user["id"])
        for _ in range(3):
            tok = (await tokens.rotate(pool, tok))["refresh_token"]
        assert isinstance(tok, str) and len(tok) > 20
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM auth_users WHERE id = $1", user["id"])
