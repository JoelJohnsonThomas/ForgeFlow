"""asyncpg connection pool factory — shared across all modules."""

import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from forgeflow.config import get_settings

_pool: asyncpg.Pool | None = None


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
