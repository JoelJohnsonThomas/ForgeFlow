"""User store — DB access for the users table (Increment 2 auth).

Thin, typed helpers over asyncpg so the router and lifespan seeding never write
raw SQL inline. All lookups return asyncpg.Record or None.
"""

from __future__ import annotations

import uuid

import asyncpg


async def get_by_username(pool: asyncpg.Pool, username: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM auth_users WHERE username = $1", username)


async def get_by_id(pool: asyncpg.Pool, user_id: uuid.UUID) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM auth_users WHERE id = $1", user_id)


async def get_by_external_subject(pool: asyncpg.Pool, subject: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM auth_users WHERE external_subject = $1", subject
        )


async def upsert_local_user(
    pool: asyncpg.Pool,
    username: str,
    password_hash: str,
    role: str,
    workspace_id: uuid.UUID | None = None,
) -> asyncpg.Record:
    """Create or update a local (password) user. Used for demo-user seeding."""
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            INSERT INTO auth_users (username, password_hash, role, workspace_id, auth_provider)
            VALUES ($1, $2, $3, $4, 'local')
            ON CONFLICT (username) DO UPDATE
              SET password_hash = EXCLUDED.password_hash,
                  role          = EXCLUDED.role,
                  workspace_id  = EXCLUDED.workspace_id,
                  updated_at    = now()
            RETURNING *
            """,
            username,
            password_hash,
            role,
            workspace_id,
        )


async def provision_oidc_user(
    pool: asyncpg.Pool, subject: str, username: str, role: str
) -> asyncpg.Record:
    """Look up an OIDC user by 'sub', creating one on first login (JIT provisioning)."""
    existing = await get_by_external_subject(pool, subject)
    if existing is not None:
        return existing
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            INSERT INTO auth_users (username, role, auth_provider, external_subject)
            VALUES ($1, $2, 'oidc', $3)
            ON CONFLICT (username) DO UPDATE
              SET external_subject = EXCLUDED.external_subject, updated_at = now()
            RETURNING *
            """,
            username,
            role,
            subject,
        )


async def set_mfa_secret(pool: asyncpg.Pool, user_id: uuid.UUID, secret: str) -> None:
    """Stage a TOTP secret (not yet enabled — enabled after first verify)."""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE auth_users SET mfa_secret = $2, updated_at = now() WHERE id = $1",
            user_id,
            secret,
        )


async def enable_mfa(pool: asyncpg.Pool, user_id: uuid.UUID) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE auth_users SET mfa_enabled = TRUE, updated_at = now() WHERE id = $1",
            user_id,
        )
