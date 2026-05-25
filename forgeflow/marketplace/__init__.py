"""Workflow template marketplace — discover, validate, install templates."""

from forgeflow.marketplace.registry import (
    TemplateManifest,
    TemplateRegistry,
    get_registry,
)

__all__ = ["TemplateManifest", "TemplateRegistry", "get_registry"]
