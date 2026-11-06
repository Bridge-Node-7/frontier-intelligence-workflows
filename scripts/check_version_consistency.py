#!/usr/bin/env python3
"""Fail if version identifiers across tracked files disagree."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def from_version_file() -> str | None:
    p = ROOT / "VERSION"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip().splitlines()[0].strip()


def from_release_manifest() -> str | None:
    p = ROOT / ".release-please-manifest.json"
    if not p.exists():
        return None
    value = json.loads(p.read_text(encoding="utf-8")).get(".")
    return str(value) if value else None


def main() -> int:
    sources = {
        "VERSION": from_version_file,
        ".release-please-manifest.json": from_release_manifest,
    }
    found = {name: reader() for name, reader in sources.items()}
    missing = [name for name, value in found.items() if value is None]
    if missing:
        print(f"FAIL: missing version source: {', '.join(missing)}", file=sys.stderr)
        return 1
    for name, value in found.items():
        print(f"{name}: {value}")
    versions = {value.lstrip("v") for value in found.values()}
    if len(versions) != 1:
        print("FAIL: version identifiers disagree across files.", file=sys.stderr)
        return 1
    print(f"PASS: consistent version {versions.pop()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
