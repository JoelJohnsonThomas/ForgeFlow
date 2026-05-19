"""Tests for PGVectorStore with mock asyncpg pool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from forgeflow.memory.pgvector_store import PGVectorStore


FAKE_EMBEDDING = [0.1] * 1536


def _make_pool_with_row(row):
    """Build a mock asyncpg pool that returns a single row."""
    pool = MagicMock()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="SET")
    conn.fetchrow = AsyncMock(return_value=row)
    conn.fetch = AsyncMock(return_value=[row] if row else [])
    pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock(return_value=None),
    ))
    return pool


class TestPGVectorStore:
    @pytest.mark.asyncio
    async def test_store_returns_memory_id(self):
        import uuid
        fake_id = uuid.uuid4()
        pool = _make_pool_with_row({"id": fake_id})
        store = PGVectorStore(pool)

        with patch.object(store, "_get_embeddings") as mock_embed_factory:
            mock_embed = MagicMock()
            mock_embed.aembed_query = AsyncMock(return_value=FAKE_EMBEDDING)
            mock_embed_factory.return_value = mock_embed

            memory_id = await store.store("some content", namespace="test")

        assert memory_id == str(fake_id)

    @pytest.mark.asyncio
    async def test_search_returns_results_above_threshold(self):
        import uuid
        fake_id = uuid.uuid4()
        fake_row = {
            "id": fake_id,
            "content": "test content",
            "metadata": {},
            "namespace": "test",
            "similarity": 0.85,
        }
        pool = _make_pool_with_row(fake_row)
        store = PGVectorStore(pool)

        with patch.object(store, "_get_embeddings") as mock_embed_factory:
            mock_embed = MagicMock()
            mock_embed.aembed_query = AsyncMock(return_value=FAKE_EMBEDDING)
            mock_embed_factory.return_value = mock_embed

            results = await store.search("query text", k=5, min_similarity=0.5)

        assert len(results) == 1
        assert results[0]["similarity"] == 0.85
        assert results[0]["content"] == "test content"

    @pytest.mark.asyncio
    async def test_search_filters_below_threshold(self):
        import uuid
        fake_id = uuid.uuid4()
        fake_row = {
            "id": fake_id,
            "content": "irrelevant content",
            "metadata": {},
            "namespace": "test",
            "similarity": 0.1,
        }
        pool = _make_pool_with_row(fake_row)
        store = PGVectorStore(pool)

        with patch.object(store, "_get_embeddings") as mock_embed_factory:
            mock_embed = MagicMock()
            mock_embed.aembed_query = AsyncMock(return_value=FAKE_EMBEDDING)
            mock_embed_factory.return_value = mock_embed

            results = await store.search("query text", k=5, min_similarity=0.5)

        assert results == []

    @pytest.mark.asyncio
    async def test_delete_returns_true_on_success(self):
        import uuid
        pool = MagicMock()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="DELETE 1")
        pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        ))
        store = PGVectorStore(pool)
        result = await store.delete(str(uuid.uuid4()))
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self):
        import uuid
        pool = MagicMock()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="DELETE 0")
        pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        ))
        store = PGVectorStore(pool)
        result = await store.delete(str(uuid.uuid4()))
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        pool = MagicMock()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value="DELETE 3")
        pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        ))
        store = PGVectorStore(pool)
        count = await store.cleanup_expired()
        assert count == 3
