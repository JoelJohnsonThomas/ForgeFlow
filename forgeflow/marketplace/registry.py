"""File-based template registry.

A template is a self-contained workflow plus its prompts + stages + Pydantic
input model, packaged as a directory with a manifest.yaml at the root.
Built-in templates (sales_ops, support_ops, finance_recon) ship in this
repo under templates/builtin/; users drop their own under templates/community/
or fetch from GitHub at install time.

Why file-based vs. a hosted server: for the open-source release a hosted
registry creates ops burden + lock-in. Templates are git-distributable —
clone a repo, point ForgeFlow at it, done. A hosted index can sit on top
of the same manifest format later without breaking installs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TemplateManifest:
    """The schema every template ships in its manifest.yaml.

    YAML is parsed into a dict and then constructed here — keeps the
    type system honest without forcing a YAML dependency at import time.
    """
    name: str
    version: str
    description: str
    domain: str                  # sales_ops | support_ops | finance_recon | custom
    author: str = ""
    homepage: str = ""
    tags: list[str] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    requires_connectors: list[str] = field(default_factory=list)
    requires_extras: list[str] = field(default_factory=list)
    license: str = "Apache-2.0"

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str = "") -> TemplateManifest:
        """Construct from a raw dict (e.g. parsed manifest.yaml).

        Raises ValueError when required fields are missing — callers catch
        this to fail listing of an invalid template rather than the whole
        registry walk.
        """
        required = ["name", "version", "description", "domain"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            raise ValueError(
                f"manifest at {source or '?'} missing required fields: {missing}"
            )
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            domain=data["domain"],
            author=data.get("author", ""),
            homepage=data.get("homepage", ""),
            tags=list(data.get("tags") or []),
            stages=list(data.get("stages") or []),
            input_schema=dict(data.get("input_schema") or {}),
            requires_connectors=list(data.get("requires_connectors") or []),
            requires_extras=list(data.get("requires_extras") or []),
            license=data.get("license", "Apache-2.0"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "domain": self.domain,
            "author": self.author,
            "homepage": self.homepage,
            "tags": self.tags,
            "stages": self.stages,
            "input_schema": self.input_schema,
            "requires_connectors": self.requires_connectors,
            "requires_extras": self.requires_extras,
            "license": self.license,
        }


class TemplateRegistry:
    """Walks one or more search-path roots to discover template manifests.

    Each search root is expected to contain template directories at its top
    level, each holding a manifest.yaml. The walker is shallow on purpose —
    it stops at depth 2 so we don't accidentally pick up the chart's
    Helm files or unrelated YAML.
    """

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        self.search_paths = search_paths or [
            Path(__file__).resolve().parent.parent.parent / "templates" / "builtin",
            Path(__file__).resolve().parent.parent.parent / "templates" / "community",
        ]
        self._cache: dict[str, TemplateManifest] | None = None

    def discover(self, refresh: bool = False) -> dict[str, TemplateManifest]:
        """Scan search paths and return {name: manifest}.

        Subsequent calls return the cached result; pass refresh=True after
        installing a new template.
        """
        if self._cache is not None and not refresh:
            return self._cache

        found: dict[str, TemplateManifest] = {}
        for root in self.search_paths:
            if not root.is_dir():
                continue
            for child in sorted(root.iterdir()):
                if not child.is_dir():
                    continue
                manifest = self._load_one(child)
                if manifest is None:
                    continue
                if manifest.name in found:
                    logger.warning(
                        "Duplicate template name '%s' — second occurrence at %s ignored",
                        manifest.name,
                        child,
                    )
                    continue
                found[manifest.name] = manifest

        self._cache = found
        return found

    def get(self, name: str) -> TemplateManifest | None:
        return self.discover().get(name)

    def list_all(self) -> list[TemplateManifest]:
        return sorted(self.discover().values(), key=lambda m: (m.domain, m.name))

    def list_by_domain(self, domain: str) -> list[TemplateManifest]:
        return [m for m in self.list_all() if m.domain == domain]

    def install_from_dict(
        self,
        manifest: dict[str, Any],
        dest_root: Path | None = None,
    ) -> TemplateManifest:
        """Install a template by writing its manifest to disk.

        Used by the API endpoint that accepts a template payload — the
        full template directory upload is out of scope for the marketplace
        foundation; only the manifest is registered here. The actual
        prompts/stages/pipeline files are still expected to live in the
        package source.
        """
        m = TemplateManifest.from_dict(manifest, source="install_from_dict")
        target_root = dest_root or self.search_paths[-1]   # community root
        target_dir = target_root / m.name
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "manifest.json").write_text(
            json.dumps(m.to_dict(), indent=2) + "\n"
        )
        self.discover(refresh=True)
        return m

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_one(self, template_dir: Path) -> TemplateManifest | None:
        """Try YAML first, then JSON, then bail out without polluting the cache."""
        yaml_path = template_dir / "manifest.yaml"
        json_path = template_dir / "manifest.json"
        try:
            if yaml_path.exists():
                data = _load_yaml(yaml_path)
            elif json_path.exists():
                data = json.loads(json_path.read_text())
            else:
                return None
        except Exception as exc:
            logger.warning("Failed to read manifest in %s: %s", template_dir, exc)
            return None

        try:
            return TemplateManifest.from_dict(data, source=str(template_dir))
        except ValueError as exc:
            logger.warning("Invalid manifest in %s: %s", template_dir, exc)
            return None


def _load_yaml(path: Path) -> dict[str, Any]:
    """Tiny YAML loader — uses PyYAML when available, falls back to a
    JSON-only path that still works for manifests written in JSON.

    PyYAML is already a transitive dep via langgraph; this lazy import keeps
    the marketplace module importable in stripped-down installs.
    """
    try:
        import yaml  # type: ignore[import-untyped]
        return yaml.safe_load(path.read_text()) or {}
    except ImportError:
        # Try parsing as JSON (some users write JSON in manifest.yaml)
        return json.loads(path.read_text())


_singleton: TemplateRegistry | None = None


def get_registry() -> TemplateRegistry:
    global _singleton
    if _singleton is None:
        _singleton = TemplateRegistry()
    return _singleton
