#!/usr/bin/env python3
"""Align VERSION, strip pre-tag CHANGELOG compare URLs, refresh manifests.

Intended for the release-please workflow after release-please updates version
authorities on the release PR branch. Pull-request CI still validates the branch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_common import write_manifests  # noqa: E402

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
COMPARE_HEADING_RE = re.compile(
    r"(^## \[\d+\.\d+\.\d+\])\(https://github\.com/[^\s)]+/compare/[^\s)]+\)( \(\d{4}-\d{2}-\d{2}\))",
    re.MULTILINE,
)


def main() -> int:
    root = Path(".").resolve()
    manifest_path = root / ".release-please-manifest.json"
    version_path = root / "VERSION"
    changelog_path = root / "CHANGELOG.md"
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(document.get(".", "")).strip()
    if not VERSION_RE.fullmatch(version):
        print(f"FAIL: invalid release-please manifest version {version!r}", file=sys.stderr)
        return 1
    current = version_path.read_text(encoding="utf-8").strip()
    if current != version:
        version_path.write_text(version + "\n", encoding="utf-8", newline="\n")
        print(f"PASS: aligned VERSION to {version}")
    else:
        print(f"PASS: VERSION already {version}")

    changelog = changelog_path.read_text(encoding="utf-8")
    rewritten, n = COMPARE_HEADING_RE.subn(r"\1\2", changelog, count=1)
    if n:
        changelog_path.write_text(rewritten, encoding="utf-8", newline="\n")
        print("PASS: stripped pre-tag CHANGELOG compare URL")
    else:
        print("PASS: CHANGELOG compare heading already plain or absent")

    document, _ = write_manifests(root)
    print(f"PASS: refreshed manifests ({len(document['files'])} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
