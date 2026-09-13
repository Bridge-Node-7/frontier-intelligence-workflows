#!/usr/bin/env python3
"""Hardened FIW repository-validation interface.

The mature validator implementation lives in ``validate_repo_core``. This wrapper
keeps every existing public validator symbol available while changing one bounded
operator behavior: a hostile-filesystem finding still fails closed, but it no
longer suppresses independent content scans over policy-approved records.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib

import yaml
from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for
from pathlib import Path
from typing import Iterable

# Suppress bytecode before importing the preserved validator module. Setting this
# only inside the imported module is too late for its own import cache write.
sys.dont_write_bytecode = True

import validate_repo_core as _core
from validate_repo_core import *  # noqa: F401,F403
from release_common import load_policy, scan_repository

CORE_RELATIVE = "scripts/validate_repo_core.py"

# The preserved core is part of the required trusted validator surface.
REQUIRED_FILES = set(_core.REQUIRED_FILES) | {CORE_RELATIVE}
_core.REQUIRED_FILES = REQUIRED_FILES
_CORE_VALIDATE = _core.validate


def _approved_text_files(root: Path) -> Iterable[Path]:
    """Yield approved text records even when another path violates file policy.

    The preserved core is omitted from the generic pass because the historical
    website-boundary sentinel intentionally excludes the validator implementation
    that contains its own test string. Dedicated security scans for the core are
    folded back into the report below.
    """

    records, _findings = scan_repository(root, include_manifests=True)
    for record in records:
        if record.relative == CORE_RELATIVE:
            continue
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


def _check(report: dict, name: str) -> dict:
    return next(item for item in report["checks"] if item["name"] == name)


def _fail_check(item: dict, detail: str) -> None:
    item["status"] = "FAIL"
    item["passed"] = False
    item["detail"] = detail if not item.get("detail") else f"{item['detail']}; {detail}"


def _fold_core_security_scans(report: dict, root: Path) -> None:
    """Keep the preserved implementation inside security scans while avoiding self-sentinel noise."""

    path = root / CORE_RELATIVE
    if not path.is_file():
        return
    text = _core.secret_scan_text(path, root=root)

    secret_hits = [label for label, pattern in _core.SECRET_PATTERNS.items() if pattern.search(text)]
    if secret_hits:
        _fail_check(
            _check(report, "secret_patterns"),
            f"Potential secrets in {CORE_RELATIVE}: {secret_hits}",
        )

    local_hits = [label for label, pattern in _core.LOCAL_PATH_PATTERNS.items() if pattern.search(text)]
    if local_hits:
        _fail_check(
            _check(report, "local_user_paths"),
            f"Local paths in {CORE_RELATIVE}: {local_hits}",
        )

    email_pattern = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    telephone_pattern = re.compile(
        r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?!\d)"
    )
    social_pattern = re.compile(
        r"https?://(?:www\.)?(?:linkedin\.com|instagram\.com|twitter\.com|x\.com|facebook\.com)/",
        re.IGNORECASE,
    )
    reserved_email_suffixes = (".invalid", ".example", ".test", ".localhost")
    contact_hits: list[str] = []
    for match in email_pattern.finditer(text):
        domain = match.group(0).rsplit("@", 1)[1].lower()
        if not domain.endswith(reserved_email_suffixes):
            contact_hits.append("email address")
    if telephone_pattern.search(text):
        contact_hits.append("telephone number")
    if social_pattern.search(text):
        contact_hits.append("personal social profile")
    if contact_hits:
        _fail_check(
            _check(report, "personal_contact_surface"),
            f"Personal contact surfaces in {CORE_RELATIVE}: {contact_hits}",
        )

    source_hits = _core.source_text_findings(path)
    if source_hits:
        _fail_check(
            _check(report, "source_text_safety"),
            f"Unsafe source text in {CORE_RELATIVE}: {source_hits}",
        )



def _structured_semantic_findings(root: Path) -> list[str]:
    """Parse every approved structured artifact and validate schema documents.

    This is deliberately independent from byte-integrity: updating a manifest hash
    cannot convert malformed JSON/YAML/TOML or an invalid JSON Schema into PASS.
    """

    records, _policy_findings = scan_repository(root, include_manifests=True)
    findings: list[str] = []
    for record in records:
        path = record.path
        relative = record.relative
        suffix = path.suffix.lower()
        try:
            source = path.read_text(encoding="utf-8")
            if suffix == ".json":
                document = json.loads(source)
                if relative.endswith(".schema.json"):
                    if not isinstance(document, (dict, bool)):
                        raise ValueError("JSON Schema root must be an object or boolean")
                    validator_class = validator_for(document)
                    validator_class.check_schema(document)
            elif suffix in {".yml", ".yaml"}:
                document = yaml.safe_load(source)
                if document is None:
                    raise ValueError("YAML document is empty")
            elif suffix == ".toml":
                tomllib.loads(source)
        except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError, tomllib.TOMLDecodeError, SchemaError, ValueError) as exc:
            findings.append(f"{relative}: {type(exc).__name__}: {exc}")
    return findings

def validate(root: Path, check_manifest: bool = True):
    """Run the core 19-control validator with independent diagnostic scans."""

    original_text_files = _core.text_files
    _core.text_files = _approved_text_files
    try:
        report = _CORE_VALIDATE(root, check_manifest=check_manifest)
    finally:
        _core.text_files = original_text_files

    _fold_core_security_scans(report, root)

    semantic_findings = _structured_semantic_findings(root)
    report["checks"].append({
        "name": "structured_artifact_semantics",
        "status": "PASS" if not semantic_findings else "FAIL",
        "passed": not semantic_findings,
        "detail": (
            "Every policy-approved JSON, YAML, and TOML artifact parses; every JSON Schema validates against its declared metaschema."
            if not semantic_findings
            else "; ".join(semantic_findings)
        ),
    })

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
