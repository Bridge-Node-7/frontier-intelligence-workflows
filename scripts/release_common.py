#!/usr/bin/env python3
"""Shared, standard-library release integrity controls for FIW."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import stat
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROJECT = "Frontier Intelligence Workflows"
EXPECTED_VERSION = "0.4.1"
MANIFEST_FILES = {"REPO_MANIFEST.json", "MANIFEST.sha256"}
GENERATED_ROOT_FILES: set[str] = set()
DEFAULT_EXCLUDED_DIRS = {".git"}
WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
WINDOWS_REPARSE_POINT = 0x400


class IntegrityError(RuntimeError):
    """Raised when repository or release integrity validation fails."""


@dataclass(frozen=True)
class FileRecord:
    path: Path
    relative: str
    size_bytes: int
    sha256: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"expected a JSON object in {path}")
    return value


def load_policy(root: Path) -> dict[str, Any]:
    policy_path = root / "REPO_FILE_POLICY.json"
    if not policy_path.is_file():
        raise IntegrityError("missing REPO_FILE_POLICY.json")
    policy = load_json(policy_path)
    required_keys = {
        "schema_version",
        "release_version",
        "allowed_root_files",
        "allowed_path_globs",
        "allowed_hidden_path_globs",
        "prohibited_path_segments",
        "prohibited_suffixes",
        "max_file_size_bytes",
        "max_total_size_bytes",
        "binary_files_allowed",
        "nested_archives_allowed",
        "approved_workflow_sha256",
    }
    missing = sorted(required_keys - set(policy))
    if missing:
        raise IntegrityError(f"REPO_FILE_POLICY.json missing keys: {missing}")
    release_version = str(policy["release_version"])
    if release_version != EXPECTED_VERSION:
        raise IntegrityError(
            f"REPO_FILE_POLICY.json release_version={release_version!r}; "
            f"expected {EXPECTED_VERSION!r}"
        )
    return policy


def _contains_control_characters(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value)




def portable_path_key(relative: str) -> str:
    """Return the cross-platform comparison key for a logical repository path."""
    normalized = unicodedata.normalize("NFC", relative.replace("\\", "/"))
    return normalized.casefold()


def portable_path_error(relative: str) -> str | None:
    """Reject path forms that are unsafe or ambiguous on supported platforms."""
    if (
        not relative
        or relative.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:", relative)
    ):
        return f"UNSAFE_PORTABLE_PATH: absolute, UNC, drive-qualified, or empty path: {relative!r}"
    if "\\" in relative:
        return f"UNSAFE_PORTABLE_PATH: backslash is not allowed in logical path: {relative}"
    if _contains_control_characters(relative):
        return f"UNSAFE_PORTABLE_PATH: control character in path: {relative!r}"
    parts = relative.split("/")
    for part in parts:
        if not part or part in {".", ".."}:
            return f"UNSAFE_PORTABLE_PATH: invalid path component {part!r} in {relative}"
        if ":" in part:
            return f"UNSAFE_PORTABLE_PATH: colon or alternate-data-stream syntax in {relative}"
        if part.endswith((" ", ".")):
            return f"UNSAFE_PORTABLE_PATH: trailing space or period in {relative}"
        stripped = part.rstrip(" .")
        stem = stripped.split(".", 1)[0].upper()
        if stem in WINDOWS_RESERVED_NAMES:
            return f"UNSAFE_PORTABLE_PATH: Windows reserved device name {part!r} in {relative}"
    return None


def portable_path_errors(relative: str) -> list[str]:
    """Return all portable-path findings for a logical path."""
    finding = portable_path_error(relative)
    return [finding] if finding else []


def unsafe_filesystem_entry_reason(
    *, relative: str, is_symlink: bool, mode: int, file_attributes: int = 0
) -> str | None:
    """Return a deterministic finding for unsafe non-directory entries."""
    if is_symlink or (file_attributes & WINDOWS_REPARSE_POINT):
        return f"UNSAFE_FILESYSTEM_ENTRY: symbolic link or reparse point: {relative}"
    if stat.S_ISDIR(mode) or stat.S_ISREG(mode):
        return None
    return f"UNSAFE_FILESYSTEM_ENTRY: non-regular file: {relative}"


def _git_tracked_paths(root: Path) -> list[str]:
    """Return tracked paths when root is a Git worktree."""
    if not (root / ".git").exists():
        return []
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise IntegrityError(f"cannot enumerate tracked files: {exc}") from exc
    return [item.decode("utf-8", "strict") for item in completed.stdout.split(b"\0") if item]


def compile_python_sources(root: Path) -> list[str]:
    """Compile repository Python sources in memory without creating bytecode."""
    compiled: list[str] = []
    for directory in (root / "scripts", root / "tests"):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            relative = path.relative_to(root).as_posix()
            source = path.read_text(encoding="utf-8")
            compile(source, relative, "exec")
            compiled.append(relative)
    return compiled


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _is_hidden_path(relative: str) -> bool:
    return any(part.startswith(".") for part in Path(relative).parts)


def _is_probably_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _policy_path_error(relative: str, policy: dict[str, Any]) -> str | None:
    portable_error = portable_path_error(relative)
    if portable_error:
        return portable_error
    parts = Path(relative).parts
    lowered = [part.lower() for part in parts]
    prohibited_segments = {str(item).lower() for item in policy["prohibited_path_segments"]}
    hit = next((part for part in lowered if part in prohibited_segments), None)
    if hit:
        return f"UNAPPROVED_PATH: prohibited path segment {hit!r} in {relative}"

    suffixes = [str(item).lower() for item in policy["prohibited_suffixes"]]
    lower_rel = relative.lower()
    if any(lower_rel.endswith(suffix) for suffix in suffixes):
        return f"UNAPPROVED_FILE_TYPE: prohibited suffix for {relative}"

    if len(parts) == 1:
        allowed = relative in set(policy["allowed_root_files"])
    else:
        allowed = _matches_any(relative, policy["allowed_path_globs"])
    if not allowed:
        return (
            f"UNAPPROVED_PATH: {relative} is not allowed by REPO_FILE_POLICY.json; "
            "remove it or update the policy in the same reviewed pull request"
        )

    if _is_hidden_path(relative) and not _matches_any(relative, policy["allowed_hidden_path_globs"]):
        return f"UNAPPROVED_HIDDEN_PATH: {relative}"
    return None


def scan_repository(root: Path, include_manifests: bool = True) -> tuple[list[FileRecord], list[str]]:
    """Walk without following links and enforce public and portable file policy."""
    root = root.resolve()
    policy = load_policy(root)
    records: list[FileRecord] = []
    findings: list[str] = []
    total = 0
    seen_portable: dict[str, str] = {}

    def register_path(relative: str) -> None:
        error = portable_path_error(relative)
        if error:
            findings.append(error)
            return
        key = portable_path_key(relative)
        previous = seen_portable.get(key)
        if previous is not None and previous != relative:
            findings.append(
                f"PORTABLE_PATH_COLLISION: {previous!r} and {relative!r} collapse on supported filesystems"
            )
        else:
            seen_portable[key] = relative

    def walk(directory: Path) -> None:
        nonlocal total
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            findings.append(f"FILESYSTEM_READ_ERROR: {directory}: {exc}")
            return
        for entry in entries:
            if entry.name in DEFAULT_EXCLUDED_DIRS:
                continue
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            register_path(relative)
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as exc:
                findings.append(f"FILESYSTEM_STAT_ERROR: {relative}: {exc}")
                continue
            mode = st.st_mode
            unsafe_reason = unsafe_filesystem_entry_reason(
                relative=relative,
                is_symlink=entry.is_symlink(),
                mode=mode,
                file_attributes=getattr(st, "st_file_attributes", 0),
            )
            if unsafe_reason:
                findings.append(unsafe_reason)
                continue
            if stat.S_ISDIR(mode):
                lowered = {part.lower() for part in Path(relative).parts}
                prohibited = {str(item).lower() for item in policy["prohibited_path_segments"]}
                hit = sorted(lowered & prohibited)
                if hit:
                    findings.append(f"UNAPPROVED_DIRECTORY: prohibited path segment {hit[0]!r} in {relative}")
                    continue
                walk(path)
                continue
            if not stat.S_ISREG(mode):
                findings.append(f"UNSAFE_FILESYSTEM_ENTRY: non-regular file: {relative}")
                continue
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(root)
            except (OSError, ValueError) as exc:
                findings.append(f"UNSAFE_FILESYSTEM_ENTRY: path escapes repository: {relative}: {exc}")
                continue
            if not include_manifests and relative in MANIFEST_FILES:
                continue
            policy_error = _policy_path_error(relative, policy)
            if policy_error:
                findings.append(policy_error)
                continue
            if st.st_size > int(policy["max_file_size_bytes"]):
                findings.append(
                    f"FILE_TOO_LARGE: {relative} is {st.st_size} bytes; "
                    f"maximum is {policy['max_file_size_bytes']}"
                )
                continue
            try:
                data = path.read_bytes()
            except OSError as exc:
                findings.append(f"FILESYSTEM_READ_ERROR: {relative}: {exc}")
                continue
            if not bool(policy["binary_files_allowed"]) and not _is_probably_text(data):
                findings.append(f"BINARY_FILE_NOT_ALLOWED: {relative}")
                continue
            total += st.st_size
            records.append(FileRecord(path, relative, st.st_size, sha256_bytes(data)))

    walk(root)

    # The Git index is an independent source of truth when available. A tracked
    # path may never hide behind a generated-output or cache directory.
    try:
        tracked_paths = _git_tracked_paths(root)
    except IntegrityError as exc:
        findings.append(str(exc))
        tracked_paths = []
    for relative in tracked_paths:
        for issue in portable_path_errors(relative):
            tagged = f"TRACKED_PATH_OUTSIDE_POLICY_SCAN: {issue}"
            if tagged not in findings:
                findings.append(tagged)
        policy_error = _policy_path_error(relative, policy)
        if policy_error and policy_error not in findings:
            findings.append(policy_error)
        path = root / relative
        if not path.exists() and not path.is_symlink():
            findings.append(f"TRACKED_PATH_MISSING: {relative}")

    if total > int(policy["max_total_size_bytes"]):
        findings.append(
            f"REPOSITORY_TOO_LARGE: {total} bytes; maximum is {policy['max_total_size_bytes']}"
        )
    records.sort(key=lambda item: item.relative)
    return records, findings


def collect_manifest_entries(root: Path) -> list[dict[str, Any]]:
    records, findings = scan_repository(root, include_manifests=False)
    if findings:
        raise IntegrityError("; ".join(findings))
    return [
        {"path": item.relative, "size_bytes": item.size_bytes, "sha256": item.sha256}
        for item in records
    ]


def expected_manifest_document(version: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "project": PROJECT,
        "version": version,
        "generated_at_utc": "1980-01-01T00:00:00Z",
        "coverage": (
            "All policy-approved regular repository files except REPO_MANIFEST.json, "
            "MANIFEST.sha256 and .git/. Build output must remain outside the repository root."
        ),
        "files": entries,
    }


def expected_sha_text(entries: list[dict[str, Any]]) -> str:
    return "".join(f"{item['sha256']}  {item['path']}\n" for item in entries)


def write_manifests(root: Path) -> tuple[dict[str, Any], str]:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    entries = collect_manifest_entries(root)
    document = expected_manifest_document(version, entries)
    sha_text = expected_sha_text(entries)
    (root / "REPO_MANIFEST.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    (root / "MANIFEST.sha256").write_text(sha_text, encoding="utf-8", newline="\n")
    return document, sha_text


def verify_manifests(root: Path) -> tuple[bool, str]:
    manifest_path = root / "REPO_MANIFEST.json"
    sha_path = root / "MANIFEST.sha256"
    if not manifest_path.is_file() or not sha_path.is_file():
        return False, "REPO_MANIFEST.json and MANIFEST.sha256 are mandatory"
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    entries = collect_manifest_entries(root)
    expected_doc = expected_manifest_document(version, entries)
    expected_sha = expected_sha_text(entries)
    try:
        actual_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"invalid REPO_MANIFEST.json: {exc}"
    actual_sha = sha_path.read_text(encoding="utf-8")
    same_doc = actual_doc == expected_doc
    same_sha = actual_sha == expected_sha
    return same_doc and same_sha, f"REPO_MANIFEST match={same_doc}; MANIFEST.sha256 match={same_sha}"


def strip_yaml_comments(text: str) -> str:
    """Remove comments while preserving # inside quoted scalar text."""
    output: list[str] = []
    for raw_line in text.splitlines():
        quote: str | None = None
        escaped = False
        kept: list[str] = []
        for ch in raw_line:
            if escaped:
                kept.append(ch)
                escaped = False
                continue
            if ch == "\\" and quote == '"':
                kept.append(ch)
                escaped = True
                continue
            if ch in {"'", '"'}:
                if quote is None:
                    quote = ch
                elif quote == ch:
                    quote = None
                kept.append(ch)
                continue
            if ch == "#" and quote is None:
                break
            kept.append(ch)
        output.append("".join(kept).rstrip())
    return "\n".join(output) + "\n"


def validate_workflow_semantics(root: Path) -> list[str]:
    issues: list[str] = []
    policy = load_policy(root)
    workflows_dir = root / ".github" / "workflows"
    expected_names = set(policy["approved_workflow_sha256"])
    actual_paths = sorted(list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml")))
    actual_names = {path.name for path in actual_paths}
    if actual_names != expected_names:
        issues.append(f"WORKFLOW_SET_MISMATCH: actual={sorted(actual_names)} expected={sorted(expected_names)}")

    for path in actual_paths:
        relative = path.relative_to(root).as_posix()
        raw = path.read_text(encoding="utf-8")
        text = strip_yaml_comments(raw)
        expected_hash = policy["approved_workflow_sha256"].get(path.name)
        actual_hash = sha256_file(path)
        if expected_hash != actual_hash:
            issues.append(f"WORKFLOW_HASH_MISMATCH: {relative}")

        if re.search(r"(?m)^\s*pull_request_target\s*:", text):
            issues.append(f"FORBIDDEN_TRIGGER: {relative}: pull_request_target")
        forbidden_fragments = ["pages: write", "id-token: write", "deploy-pages", "configure-pages", "upload-pages-artifact"]
        for fragment in forbidden_fragments:
            if fragment in text:
                issues.append(f"FORBIDDEN_WORKFLOW_CAPABILITY: {relative}: {fragment}")

        action_refs = re.findall(r"(?m)^\s*(?:-\s*)?uses:\s*([^\s]+)\s*$", text)
        for action in action_refs:
            if action.startswith("./"):
                continue
            if not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", action):
                issues.append(f"MUTABLE_ACTION_REFERENCE: {relative}: {action}")

        lines = text.splitlines()
        top_permission_indexes = [index for index, line in enumerate(lines) if line == "permissions:"]
        if len(top_permission_indexes) != 1:
            issues.append(f"TOP_LEVEL_PERMISSIONS_COUNT: {relative}: {len(top_permission_indexes)}")
        else:
            top_permissions_index = top_permission_indexes[0]
            permission_lines: list[str] = []
            for line in lines[top_permissions_index + 1 :]:
                if line and not line.startswith(" "):
                    break
                if line.strip():
                    permission_lines.append(line.strip())
            if permission_lines != ["contents: read"]:
                issues.append(f"UNAPPROVED_PERMISSIONS: {relative}: {permission_lines}")
        if re.search(r"(?m)^\s*permissions:\s*(?:write-all|read-all)\s*$", text):
            issues.append(f"UNAPPROVED_PERMISSIONS_SHORTHAND: {relative}")
        if re.search(r"(?m)^\s*[A-Za-z0-9_-]+:\s*write\s*$", text):
            issues.append(f"UNAPPROVED_WRITE_PERMISSION: {relative}")

        jobs_index = next((index for index, line in enumerate(lines) if line == "jobs:"), None)
        if jobs_index is None:
            issues.append(f"MISSING_JOBS: {relative}")
            continue
        jobs: dict[str, list[str]] = {}
        current_job: str | None = None
        for line in lines[jobs_index + 1 :]:
            if re.fullmatch(r"  [A-Za-z0-9_-]+:", line):
                current_job = line.strip()[:-1]
                jobs[current_job] = []
            elif current_job is not None:
                jobs[current_job].append(line)
        if not jobs:
            issues.append(f"MISSING_JOB_DEFINITIONS: {relative}")
        for job_name, job_lines in jobs.items():
            if not any(re.fullmatch(r"    timeout-minutes:\s*\d+", line) for line in job_lines):
                issues.append(f"MISSING_JOB_TIMEOUT: {relative}:{job_name}")

        checkout_indexes = [index for index, line in enumerate(lines) if re.search(r"uses:\s*actions/checkout@", line)]
        for index in checkout_indexes:
            indent = len(lines[index]) - len(lines[index].lstrip(" "))
            block: list[str] = []
            for line in lines[index + 1 :]:
                line_indent = len(line) - len(line.lstrip(" "))
                if line.strip() and line_indent <= indent and line.lstrip().startswith("-"):
                    break
                if line.strip() and line_indent < indent:
                    break
                block.append(line)
            if not any(re.fullmatch(r"\s*persist-credentials:\s*false", line) for line in block):
                issues.append(f"CHECKOUT_CREDENTIALS_ENABLED: {relative}")

        if path.name == "validate.yml":
            if "release/**" in text:
                issues.append(f"UNAPPROVED_VALIDATE_TRIGGER: {relative}: release branch push")
            required = [
                "name: validate",
                "  validate:",
                "python scripts/run_tests.py",
                "python scripts/compile_sources.py --root .",
                "python scripts/validate_repo.py",
                "python scripts/build_release.py",
                "${RUNNER_TEMP}/fiw-release",
                "--check",
                "git diff --check",
                "git status --porcelain",
            ]
        elif path.name == "release.yml":
            required = [
                "name: release",
                "tags:",
                '      - "v*"',
                "  release:",
                "python scripts/run_tests.py",
                "python scripts/compile_sources.py --root .",
                "python scripts/validate_repo.py",
                "python scripts/build_release.py",
                "${RUNNER_TEMP}/fiw-release",
                "--check",
                "git status --porcelain",
                "actions/upload-artifact@",
            ]
        else:
            required = []
        for fragment in required:
            if fragment not in text:
                issues.append(f"WORKFLOW_CONTRACT_MISSING: {relative}: {fragment}")
    return issues
