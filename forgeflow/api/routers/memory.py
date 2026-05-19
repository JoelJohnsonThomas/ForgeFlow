"""Memory routes — store and search semantic memory vectors."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from forgeflow.api.dependencies import get_pool
from forgeflow.api.schemas import MemorySearchResult, MemoryStoreRequest, MemoryStoreResponse
from forgeflow.memory.memory_manager import MemoryManager

router = APIRouter()


@router.post("/store", response_model=MemoryStoreResponse)
async def store_memory(
    request: MemoryStoreRequest,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Embed and store a memory in the vector store."""
    manager = MemoryManager(pool)
    try:
        memory_id = await manager.remember(
            content=request.content,
            namespace=request.namespace,
            metadata=request.metadata,
            ttl_hours=request.ttl_hours,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {e}")

    return MemoryStoreResponse(memory_id=memory_id)


@router.get("/search", response_model=list[MemorySearchResult])
async def search_memory(
    q: str = Query(..., description="Search query"),
    k: int = Query(5, ge=1, le=20, description="Number of results"),
    namespace: str | None = Query(None, description="Restrict to namespace"),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Semantic search over stored memories."""
    manager = MemoryManager(pool)
    try:
        results = await manager.recall(query=q, k=k, namespace=namespace)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory search failed: {e}")

    return [
        MemorySearchResult(
            id=r["id"],
            content=r["content"],
            similarity=r["similarity"],
            namespace=r["namespace"],
            metadata=r["metadata"],
        )
        for r in results
    ]


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Delete a specific memory by ID."""
    manager = MemoryManager(pool)
    deleted = await manager.forget(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "memory_id": memory_id}
