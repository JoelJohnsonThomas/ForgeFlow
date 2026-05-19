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


async def get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    settings = get_settings()
    logger.info("Initialising PostgreSQL checkpointer...")

    _checkpointer = AsyncPostgresSaver.from_conn_string(settings.postgres_sync_url)
    # Creates langgraph_checkpoints and langgraph_writes tables if they don't exist
    await _checkpointer.setup()
    logger.info("Checkpointer ready")
    return _checkpointer
