#!/usr/bin/env python3
"""Refresh committed release metadata after approved source changes."""

from __future__ import annotations

import argparse
import json
import sys

# Keep validation and release tooling read-only with respect to Python bytecode.
sys.dont_write_bytecode = True
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_common import IntegrityError, write_manifests  # noqa: E402
from validate_repo import validate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    pre = validate(root, check_manifest=False)
    if not pre["passed"]:
        for item in pre["checks"]:
            if not item["passed"]:
                print(f"FAIL: {item['name']}: {item['detail']}", file=sys.stderr)
        return 1

    document, _ = write_manifests(root)
    post = validate(root, check_manifest=True)
    if not post["passed"]:
        print(json.dumps(post, indent=2), file=sys.stderr)
        return 1
    print(f"Metadata refresh: PASS ({len(document['files'])} manifest entries)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IntegrityError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
