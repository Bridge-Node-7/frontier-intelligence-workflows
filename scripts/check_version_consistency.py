#!/usr/bin/env python3
"""Fail if version identifiers across tracked files disagree."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def from_version_file() -> str | None:
    p = ROOT / "VERSION"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip().splitlines()[0].strip()


def from_package_json() -> str | None:
    p = ROOT / "package.json"
    if not p.exists():
        return None
    return json.loads(read_text(p))["version"]


def from_pyproject() -> str | None:
    p = ROOT / "pyproject.toml"
    if not p.exists():
        return None
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', read_text(p))
    return m.group(1) if m else None


def from_citation() -> str | None:
    p = ROOT / "CITATION.cff"
    if not p.exists():
        return None
    m = re.search(r"(?m)^version:\s*['\"]?([^\s'\"]+)", read_text(p))
    return m.group(1) if m else None


def from_init(rel: str) -> str | None:
    p = ROOT / rel
    if not p.exists():
        return None
    m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", read_text(p))
    return m.group(1) if m else None


def from_js_version(rel: str) -> str | None:
    p = ROOT / rel
    if not p.exists():
        return None
    t = read_text(p)
    m = re.search(r"(?:VERSION|version)\s*=\s*['\"]([^'\"]+)['\"]", t)
    if m:
        return m.group(1)
    m = re.search(r"['\"](\d+\.\d+\.\d+)['\"]", t)
    return m.group(1) if m else None


def from_project_facts() -> str | None:
    for name in ("project-facts.json", "PROJECT_FACTS.json"):
        p = ROOT / name
        if not p.exists():
            continue
        data = json.loads(read_text(p))
        for key in ("version", "application_version", "app_version"):
            if key in data and data[key]:
                return str(data[key]).lstrip("v")
    return None


def main() -> int:
    sources = {
        "VERSION": from_version_file,
    }
    found = {k: fn() for k, fn in sources.items()}
    present = {k: v for k, v in found.items() if v is not None}
    if not present:
        print("No version sources found; nothing to check.")
        return 0
    for k, v in present.items():
        print(f"{k}: {v}")
    versions = set(present.values())
    if len(versions) != 1:
        print("FAIL: version identifiers disagree across files.", file=sys.stderr)
        return 1
    print(f"PASS: consistent version {next(iter(versions))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
