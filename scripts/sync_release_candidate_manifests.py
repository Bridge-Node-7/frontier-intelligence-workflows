#!/usr/bin/env python3
"""Rewrite MANIFEST.sha256 and REPO_MANIFEST.json for an open release candidate.

Intended for the release-please workflow after release-please updates version
authorities on the release PR branch. Does not run the full pre-manifest test
gate; pull_request CI still validates the branch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_common import write_manifests  # noqa: E402


def main() -> int:
    root = Path(".").resolve()
    document, _ = write_manifests(root)
    print(f"PASS: refreshed manifests ({len(document['files'])} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
