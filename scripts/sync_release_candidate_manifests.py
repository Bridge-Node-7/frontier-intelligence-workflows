#!/usr/bin/env python3
"""Align VERSION and refresh manifests for an open release candidate.

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


def main() -> int:
    root = Path(".").resolve()
    manifest_path = root / ".release-please-manifest.json"
    version_path = root / "VERSION"
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
    document, _ = write_manifests(root)
    print(f"PASS: refreshed manifests ({len(document['files'])} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
