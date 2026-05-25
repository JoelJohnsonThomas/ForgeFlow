"""Tests for the workflow template marketplace."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forgeflow.marketplace.registry import TemplateManifest, TemplateRegistry


@pytest.fixture
def empty_registry(tmp_path: Path) -> TemplateRegistry:
    """A registry pointing at an empty temp dir — isolates from the
    repo's built-in manifests so test assertions are deterministic."""
    builtin = tmp_path / "builtin"
    community = tmp_path / "community"
    builtin.mkdir()
    community.mkdir()
    return TemplateRegistry(search_paths=[builtin, community])


class TestManifestSchema:
    def test_minimum_fields_parse(self):
        m = TemplateManifest.from_dict(
            {
                "name": "test",
                "version": "0.1.0",
                "description": "x",
                "domain": "custom",
            }
        )
        assert m.name == "test"
        assert m.license == "Apache-2.0"  # default
        assert m.tags == []

    def test_missing_field_raises_with_filename(self):
        with pytest.raises(ValueError, match="missing required fields"):
            TemplateManifest.from_dict(
                {"name": "x", "version": "0.1.0"}, source="foo.yaml"
            )

    def test_roundtrip(self):
        data = {
            "name": "my_workflow",
            "version": "1.2.3",
            "description": "test",
            "domain": "sales_ops",
            "tags": ["a", "b"],
            "requires_connectors": ["salesforce"],
            "input_schema": {"company": {"type": "string"}},
        }
        m = TemplateManifest.from_dict(data)
        out = m.to_dict()
        for key, val in data.items():
            assert out[key] == val


class TestRegistryDiscovery:
    def test_empty_path_returns_no_templates(self, empty_registry):
        assert empty_registry.list_all() == []

    def test_discovers_json_manifests(self, empty_registry, tmp_path):
        target = tmp_path / "community" / "my_template"
        target.mkdir()
        (target / "manifest.json").write_text(
            json.dumps(
                {
                    "name": "my_template",
                    "version": "0.1.0",
                    "description": "demo",
                    "domain": "custom",
                }
            )
        )

        items = empty_registry.list_all()
        assert len(items) == 1
        assert items[0].name == "my_template"

    def test_invalid_manifest_is_skipped_not_raising(self, empty_registry, tmp_path):
        bad = tmp_path / "community" / "broken"
        bad.mkdir()
        (bad / "manifest.json").write_text("{ not valid json")

        # No exception, just an empty result
        assert empty_registry.list_all() == []

    def test_duplicate_name_keeps_first_occurrence(self, empty_registry, tmp_path):
        for root in ("builtin", "community"):
            d = tmp_path / root / "dupe"
            d.mkdir()
            (d / "manifest.json").write_text(
                json.dumps(
                    {
                        "name": "dupe",
                        "version": root,
                        "description": root,
                        "domain": "custom",
                    }
                )
            )

        items = empty_registry.list_all()
        assert len(items) == 1
        # builtin scanned before community per the search_paths order
        assert items[0].version == "builtin"

    def test_list_by_domain(self, empty_registry, tmp_path):
        for name, domain in [("a", "sales_ops"), ("b", "support_ops"), ("c", "sales_ops")]:
            d = tmp_path / "community" / name
            d.mkdir()
            (d / "manifest.json").write_text(
                json.dumps(
                    {
                        "name": name,
                        "version": "0.1.0",
                        "description": name,
                        "domain": domain,
                    }
                )
            )

        sales = empty_registry.list_by_domain("sales_ops")
        assert {m.name for m in sales} == {"a", "c"}


class TestInstallFromDict:
    def test_writes_manifest_json_and_refreshes_cache(self, empty_registry):
        registry = empty_registry
        # Prime the cache
        registry.discover()
        m = registry.install_from_dict(
            {
                "name": "installed",
                "version": "0.1.0",
                "description": "demo",
                "domain": "custom",
            }
        )

        assert m.name == "installed"
        assert registry.get("installed") is not None
        # File written to community root (last entry in search_paths)
        written = registry.search_paths[-1] / "installed" / "manifest.json"
        assert written.exists()
