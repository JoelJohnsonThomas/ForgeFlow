"""PostgreSQL checkpointer — persists graph state after every node execution.

Uses AsyncPostgresSaver (psycopg3) so any API worker can resume any thread_id.
Call get_checkpointer() once at startup; pass the result to compile_graph().
"""

from __future__ import annotations

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)

_checkpointer: AsyncPostgresSaver | None = None
_cm = None  # keeps the from_conn_string() context manager alive for the process lifetime


async def get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer, _cm
    if _checkpointer is not None:
        return _checkpointer

    settings = get_settings()
    logger.info("Initialising PostgreSQL checkpointer...")

    # from_conn_string is @asynccontextmanager — must __aenter__ to get the saver,
    # and the CM must outlive the saver or the underlying connection closes.
    # psycopg needs a plain libpq URL; SQLAlchemy's "+psycopg" driver suffix is rejected.
    conn_url = settings.postgres_sync_url.replace("postgresql+psycopg://", "postgresql://", 1)
    _cm = AsyncPostgresSaver.from_conn_string(conn_url)
    _checkpointer = await _cm.__aenter__()
    # Creates langgraph_checkpoints and langgraph_writes tables if they don't exist
    await _checkpointer.setup()
    logger.info("Checkpointer ready")
    return _checkpointer
