"""MemoryManager — unified interface over PGVector (semantic) + Relational stores.

Agents call remember() to persist and recall() to retrieve.
Namespaces partition memory: leads/{id}, market/{industry}, workflow/{id}.
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg

from forgeflow.memory.pgvector_store import PGVectorStore
from forgeflow.memory.relational_store import RelationalStore

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.vector = PGVectorStore(pool)
        self.relational = RelationalStore(pool)

    async def remember(
        self,
        content: str,
        namespace: str = "default",
        metadata: dict | None = None,
        ttl_hours: int | None = None,
    ) -> str:
        """Store a piece of information in semantic memory.

        Args:
            content: Text to embed and store
            namespace: Logical partition (e.g. "leads/uuid", "market/saas")
            metadata: Arbitrary key-value context tags
            ttl_hours: Optional expiry in hours

        Returns:
            Memory ID string
        """
        return await self.vector.store(
            content=content,
            namespace=namespace,
            metadata=metadata or {},
            ttl_hours=ttl_hours,
        )

    async def recall(
        self,
        query: str,
        k: int = 5,
        namespace: str | None = None,
        min_similarity: float = 0.35,
    ) -> list[dict[str, Any]]:
        """Retrieve semantically similar memories.

        Args:
            query: Natural-language query
            k: Number of results to return
            namespace: Restrict search to this namespace (optional)
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of {content, similarity, metadata, namespace} dicts
        """
        return await self.vector.search(
            query=query,
            k=k,
            namespace=namespace,
            min_similarity=min_similarity,
        )

    async def forget(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        return await self.vector.delete(memory_id)

    async def format_context(self, memories: list[dict]) -> str:
        """Format retrieved memories as a readable context string for agent prompts."""
        if not memories:
            return "No relevant memories found."
        parts = []
        for i, m in enumerate(memories, 1):
            sim = m.get("similarity", 0)
            parts.append(f"{i}. [{sim:.0%} match] {m['content']}")
        return "\n".join(parts)
