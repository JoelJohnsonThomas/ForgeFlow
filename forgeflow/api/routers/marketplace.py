"""Marketplace API — list, search, and inspect workflow templates."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from forgeflow.marketplace.registry import get_registry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/templates")
async def list_templates(
    domain: str | None = Query(None, description="Filter by workflow domain"),
    tag: str | None = Query(None, description="Filter by tag substring (case-insensitive)"),
) -> dict:
    """List discovered workflow templates."""
    registry = get_registry()
    manifests = registry.list_all()

    if domain:
        manifests = [m for m in manifests if m.domain == domain]
    if tag:
        needle = tag.lower()
        manifests = [m for m in manifests if any(needle in t.lower() for t in m.tags)]

    return {
        "total": len(manifests),
        "templates": [m.to_dict() for m in manifests],
    }


@router.get("/templates/{name}")
async def get_template(name: str) -> dict:
    """Fetch a single template manifest by name."""
    m = get_registry().get(name)
    if m is None:
        raise HTTPException(status_code=404, detail=f"template '{name}' not found")
    return m.to_dict()


@router.post("/templates/refresh")
async def refresh() -> dict:
    """Re-scan the template search paths. Useful after dropping a manifest into
    templates/community/ at runtime without an API restart."""
    registry = get_registry()
    registry.discover(refresh=True)
    return {"refreshed": True, "total": len(registry.list_all())}
