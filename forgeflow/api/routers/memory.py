"""Memory routes — store and search semantic memory vectors.

Hardening (SECURITY_AUDIT.md §6, §7):
  - Namespace is forced to start with `workspace/{workspace_id}/` (or
    `global/` for unscoped callers). Cross-tenant recall is impossible
    without an admin override.
  - Free-form metadata is preserved but provenance is added automatically
    (`written_by_user_id`, `workspace_id`) so recall can filter.
  - Recall returns only namespaces the caller is allowed to see.
"""

from __future__ import annotations

import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from forgeflow.api.dependencies import get_current_user, get_pool, get_workspace_id
from forgeflow.api.schemas import MemorySearchResult, MemoryStoreRequest, MemoryStoreResponse
from forgeflow.memory.memory_manager import MemoryManager
from forgeflow.rbac.models import UserContext

logger = logging.getLogger(__name__)
router = APIRouter()


def _namespace_prefix(workspace_id: str | None) -> str:
    return f"workspace/{workspace_id}/" if workspace_id else "global/"


def _require_owned_namespace(namespace: str, workspace_id: str | None) -> None:
    """Reject any namespace that doesn't start with the caller's prefix."""
    prefix = _namespace_prefix(workspace_id)
    if not namespace.startswith(prefix):
        raise HTTPException(
            status_code=403,
            detail=(
                f"namespace must start with '{prefix}' — "
                "cross-tenant memory access is blocked"
            ),
        )


@router.post("/store", response_model=MemoryStoreResponse)
async def store_memory(
    request: MemoryStoreRequest,
    pool: asyncpg.Pool = Depends(get_pool),
    user: UserContext = Depends(get_current_user),
    workspace_id: str | None = Depends(get_workspace_id),
):
    """Embed and store a memory in the vector store (tenant-scoped)."""
    _require_owned_namespace(request.namespace, workspace_id)

    metadata = dict(request.metadata or {})
    metadata.setdefault("written_by_user_id", user.user_id)
    if workspace_id:
        metadata.setdefault("workspace_id", workspace_id)
    metadata.setdefault("source_trust_level", "user")

    manager = MemoryManager(pool)
    try:
        memory_id = await manager.remember(
            content=request.content,
            namespace=request.namespace,
            metadata=metadata,
            ttl_hours=request.ttl_hours,
        )
    except Exception as e:
        logger.exception("memory store failed")
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {e}") from e

    return MemoryStoreResponse(memory_id=memory_id)


@router.get("/search", response_model=list[MemorySearchResult])
async def search_memory(
    q: str = Query(..., description="Search query", max_length=2000),
    k: int = Query(5, ge=1, le=20),
    namespace: str | None = Query(None, description="Restrict to namespace"),
    pool: asyncpg.Pool = Depends(get_pool),
    workspace_id: str | None = Depends(get_workspace_id),
):
    """Semantic search over stored memories — tenant-scoped.

    If the caller passes an explicit namespace it must be inside their
    prefix. If they omit it we pin to the prefix automatically so a leaked
    query string can't escape the tenant.
    """
    prefix = _namespace_prefix(workspace_id)

    if namespace is not None:
        _require_owned_namespace(namespace, workspace_id)
        search_ns = namespace
    else:
        # Force prefix even when caller omits the param.
        search_ns = prefix.rstrip("/")

    manager = MemoryManager(pool)
    try:
        results = await manager.recall(query=q, k=k, namespace=search_ns)
    except Exception as e:
        logger.exception("memory search failed")
        raise HTTPException(status_code=500, detail=f"Memory search failed: {e}") from e

    # Defensive: drop any row whose namespace escaped the prefix (covers
    # legacy unscoped memories that should not appear in tenant queries).
    safe = [r for r in results if str(r.get("namespace", "")).startswith(prefix)]

    return [
        MemorySearchResult(
            id=r["id"],
            content=r["content"],
            similarity=r["similarity"],
            namespace=r["namespace"],
            metadata=r["metadata"],
        )
        for r in safe
    ]


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    pool: asyncpg.Pool = Depends(get_pool),
    workspace_id: str | None = Depends(get_workspace_id),
):
    """Delete a specific memory by ID (only if it lives in caller's namespace)."""
    prefix = _namespace_prefix(workspace_id)

    # Fetch first to check ownership — we can't trust the id alone.
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT namespace FROM memory_vectors WHERE id::text = $1",
            memory_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    if not str(row["namespace"]).startswith(prefix):
        # Treat as not-found — don't reveal existence of another tenant's row.
        raise HTTPException(status_code=404, detail="Memory not found")

    manager = MemoryManager(pool)
    deleted = await manager.forget(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "memory_id": memory_id}
