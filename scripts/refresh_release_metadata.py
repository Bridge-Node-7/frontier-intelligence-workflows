#!/usr/bin/env python3
"""Refresh committed release metadata after approved source changes."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

# Keep validation and release tooling read-only with respect to Python bytecode.
sys.dont_write_bytecode = True
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_common import IntegrityError, write_manifests  # noqa: E402
from validate_repo import validate  # noqa: E402


def run_pre_manifest_gate(root: Path) -> None:
    """Test current source before writing manifests to the reviewed working tree."""
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="fiw-pre-manifest-") as temporary:
        staged = Path(temporary) / "repo"
        shutil.copytree(
            root,
            staged,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "dist"),
        )
        # Refresh only the disposable staging copy so semantic tests run against
        # internally consistent metadata before the reviewed tree is blessed.
        write_manifests(staged)
        subprocess.run(["git", "-C", str(staged), "init", "-q"], check=True, env=environment)
        subprocess.run(["git", "-C", str(staged), "add", "--intent-to-add", "-A"], check=True, env=environment)
        for command in (
            [sys.executable, "-B", str(staged / "scripts" / "compile_sources.py"), "--root", str(staged)],
            [sys.executable, "-B", str(staged / "scripts" / "run_tests.py"), "--root", str(staged)],
        ):
            subprocess.run(command, cwd=staged, env=environment, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    run_pre_manifest_gate(root)
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
    except (IntegrityError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
