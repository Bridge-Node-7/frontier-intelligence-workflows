#!/usr/bin/env python3
"""Hardened FIW repository-validation interface.

The mature validator implementation lives in ``validate_repo_core``. This wrapper
keeps every existing public validator symbol available while changing one bounded
operator behavior: a hostile-filesystem finding still fails closed, but it no
longer suppresses independent content scans over policy-approved records.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

import validate_repo_core as _core
from validate_repo_core import *  # noqa: F401,F403
from release_common import load_policy, scan_repository

# The core file is part of the required trusted validator surface.
REQUIRED_FILES = set(_core.REQUIRED_FILES) | {"scripts/validate_repo_core.py"}
_core.REQUIRED_FILES = REQUIRED_FILES
_CORE_VALIDATE = _core.validate


def _approved_text_files(root: Path) -> Iterable[Path]:
    """Yield approved text records even when another path violates file policy."""

    records, _findings = scan_repository(root, include_manifests=True)
    for record in records:
        path = record.path
        if path.suffix.lower() in _core.TEXT_SUFFIXES or path.name in _core.TEXT_NAMES:
            yield path


def _tracked_paths(root: Path) -> set[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return set()
    return {
        item.decode("utf-8", errors="strict")
        for item in completed.stdout.split(b"\0")
        if item
    }


def _operator_classification(root: Path) -> list[str]:
    """Classify prohibited directories without changing whether they fail policy."""

    try:
        policy = load_policy(root)
    except Exception:
        return []
    prohibited = {str(item).casefold() for item in policy.get("prohibited_path_segments", [])}
    tracked = _tracked_paths(root)
    classified: list[str] = []
    for path in sorted(
        (candidate for candidate in root.rglob("*") if candidate.is_dir()),
        key=lambda candidate: candidate.as_posix(),
    ):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if relative == ".git" or relative.startswith(".git/"):
            continue
        if not any(part.casefold() in prohibited for part in Path(relative).parts):
            continue
        tracked_under = any(
            tracked_path == relative or tracked_path.startswith(relative + "/")
            for tracked_path in tracked
        )
        state = (
            "tracked policy violation"
            if tracked_under
            else "untracked local artifact — remove it and re-run"
        )
        classified.append(f"{relative}: {state}")
    return classified


def validate(root: Path, check_manifest: bool = True):
    """Run the core 19-control validator with independent diagnostic scans."""

    original_text_files = _core.text_files
    _core.text_files = _approved_text_files
    try:
        report = _CORE_VALIDATE(root, check_manifest=check_manifest)
    finally:
        _core.text_files = original_text_files

    file_policy = next(
        (item for item in report["checks"] if item["name"] == "file_policy_and_filesystem"),
        None,
    )
    if file_policy is not None and file_policy["status"] == "FAIL":
        classifications = _operator_classification(root)
        if classifications:
            file_policy["detail"] += "; operator classification: " + "; ".join(classifications)

    report["passed"] = all(item["status"] == "PASS" for item in report["checks"])
    report["summary"] = {
        "passed": sum(1 for item in report["checks"] if item["status"] == "PASS"),
        "total": len(report["checks"]),
    }
    return report


def main() -> int:
    original_validate = _core.validate
    _core.validate = validate
    try:
        return _core.main()
    finally:
        _core.validate = original_validate


if __name__ == "__main__":
    raise SystemExit(main())
