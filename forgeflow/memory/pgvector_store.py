"""PGVectorStore — semantic memory using PostgreSQL + pgvector extension.

Embeddings: text-embedding-3-small (1536 dimensions, cost-efficient)
Index: ivfflat with cosine distance (good for <1M vectors)
Namespaces: logical partitions e.g. "leads/uuid", "market/saas", "workflow/uuid"
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import asyncpg

from forgeflow.config import get_settings

logger = logging.getLogger(__name__)


class PGVectorStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool
        self._embeddings = None  # Lazy-loaded to avoid import at module level

    def _get_embeddings(self):
        if self._embeddings is None:
            from langchain_openai import OpenAIEmbeddings
            settings = get_settings()
            self._embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key.get_secret_value(),
            )
        return self._embeddings

    async def store(
        self,
        content: str,
        namespace: str = "default",
        metadata: dict | None = None,
        ttl_hours: int | None = None,
    ) -> str:
        """Embed content and store in memory_vectors. Returns the memory ID."""
        embeddings = self._get_embeddings()
        embedding = await embeddings.aembed_query(content)

        expires_at = None
        if ttl_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        async with self.pool.acquire() as conn:
            # Register pgvector codec
            await conn.execute("SET search_path TO public")
            row = await conn.fetchrow(
                """
                INSERT INTO memory_vectors (namespace, content, embedding, metadata, expires_at)
                VALUES ($1, $2, $3::vector, $4, $5)
                RETURNING id
                """,
                namespace,
                content,
                str(embedding),
                metadata or {},
                expires_at,
            )
        memory_id = str(row["id"])
        logger.debug("Stored memory %s in namespace '%s'", memory_id, namespace)
        return memory_id

    async def search(
        self,
        query: str,
        k: int = 5,
        namespace: str | None = None,
        min_similarity: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Find the k most semantically similar memories to query.

        Uses cosine similarity (1 - cosine distance).
        """
        embeddings = self._get_embeddings()
        query_embedding = await embeddings.aembed_query(query)
        embedding_str = str(query_embedding)

        async with self.pool.acquire() as conn:
            if namespace:
                rows = await conn.fetch(
                    """
                    SELECT id, content, metadata, namespace,
                           1 - (embedding <=> $1::vector) AS similarity
                    FROM memory_vectors
                    WHERE namespace = $2
                      AND (expires_at IS NULL OR expires_at > now())
                    ORDER BY embedding <=> $1::vector
                    LIMIT $3
                    """,
                    embedding_str,
                    namespace,
                    k,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, content, metadata, namespace,
                           1 - (embedding <=> $1::vector) AS similarity
                    FROM memory_vectors
                    WHERE expires_at IS NULL OR expires_at > now()
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    embedding_str,
                    k,
                )

        results = []
        for row in rows:
            sim = float(row["similarity"])
            if sim >= min_similarity:
                results.append({
                    "id": str(row["id"]),
                    "content": row["content"],
                    "metadata": dict(row["metadata"]),
                    "namespace": row["namespace"],
                    "similarity": sim,
                })

        return results

    async def delete(self, memory_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM memory_vectors WHERE id = $1",
                uuid.UUID(memory_id),
            )
        return result != "DELETE 0"

    async def cleanup_expired(self) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM memory_vectors WHERE expires_at IS NOT NULL AND expires_at < now()"
            )
        count = int(result.split()[-1])
        if count > 0:
            logger.info("Cleaned up %d expired memory vectors", count)
        return count
