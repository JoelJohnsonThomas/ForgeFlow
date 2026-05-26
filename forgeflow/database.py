"""asyncpg connection pool factory — shared across all modules."""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg

from forgeflow.config import get_settings

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Per-connection setup. Registers a JSON/JSONB codec so dict bindings
    flow directly into JSONB columns and reads come back as dicts — without
    this, every write to audit_log.metadata (and similar) silently fails
    with 'expected str, got dict'."""
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def init_pool() -> asyncpg.Pool:
    global _pool
    settings = get_settings()
    # Strip the +asyncpg prefix that asyncpg doesn't understand
    dsn = settings.postgres_url.replace("postgresql+asyncpg://", "postgresql://")
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=3,
        max_size=20,
        command_timeout=60,
        statement_cache_size=0,  # required for pgBouncer compatibility
        init=_init_connection,
    )
    return _pool


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        await init_pool()
    assert _pool is not None
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
