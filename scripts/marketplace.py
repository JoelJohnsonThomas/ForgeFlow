"""Marketplace CLI — list / show / validate templates without booting the API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from forgeflow.marketplace.registry import TemplateManifest, get_registry


def _cmd_list(args: argparse.Namespace) -> int:
    registry = get_registry()
    rows = registry.list_all()
    if args.domain:
        rows = [r for r in rows if r.domain == args.domain]
    if not rows:
        print("No templates found.")  # noqa: T201
        return 0
    width = max(len(r.name) for r in rows)
    for r in rows:
        print(f"{r.name.ljust(width)}  {r.version:<8}  [{r.domain}]  {r.description.splitlines()[0]}")  # noqa: T201
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    m = get_registry().get(args.name)
    if m is None:
        print(f"template '{args.name}' not found")  # noqa: T201
        return 1
    print(json.dumps(m.to_dict(), indent=2))  # noqa: T201
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"not found: {path}")  # noqa: T201
        return 1
    try:
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore[import-untyped]
                data = yaml.safe_load(path.read_text()) or {}
            except ImportError:
                print("PyYAML not installed — pip install pyyaml")  # noqa: T201
                return 1
        else:
            data = json.loads(path.read_text())
        TemplateManifest.from_dict(data, source=str(path))
    except Exception as exc:
        print(f"INVALID: {exc}")  # noqa: T201
        return 1
    print(f"OK: {path}")  # noqa: T201
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ForgeFlow template marketplace CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List discovered templates")
    p_list.add_argument("--domain", help="Filter by domain")
    p_list.set_defaults(func=_cmd_list)

    p_show = sub.add_parser("show", help="Show one template manifest")
    p_show.add_argument("name")
    p_show.set_defaults(func=_cmd_show)

    p_val = sub.add_parser("validate", help="Validate a manifest file")
    p_val.add_argument("path")
    p_val.set_defaults(func=_cmd_validate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
