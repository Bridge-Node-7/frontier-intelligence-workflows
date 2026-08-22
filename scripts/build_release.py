#!/usr/bin/env python3
"""Read-only verification and deterministic FIW release package construction."""

from __future__ import annotations

import argparse
import os
import json
import shutil
import subprocess
import sys

# Keep validation and release tooling read-only with respect to Python bytecode.
sys.dont_write_bytecode = True
import tempfile
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_common import (  # noqa: E402
    PROJECT,
    IntegrityError,
    scan_repository,
    sha256_file,
    verify_manifests,
)

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def safe_release_records(root: Path):
    records, findings = scan_repository(root, include_manifests=True)
    if findings:
        raise IntegrityError("; ".join(findings))
    return records


def build_source_archive(root: Path, destination: Path, version: str) -> None:
    prefix = f"frontier-intelligence-workflows-v{version}/"
    records = safe_release_records(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for record in records:
            info = zipfile.ZipInfo(prefix + record.relative, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, record.path.read_bytes())


def verify_source_archive(destination: Path, root: Path, version: str) -> None:
    prefix = f"frontier-intelligence-workflows-v{version}/"
    records = safe_release_records(root)
    expected_names = [prefix + record.relative for record in records]
    with zipfile.ZipFile(destination, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise IntegrityError("archive contains duplicate entries")
        if names != expected_names:
            raise IntegrityError("archive order or membership does not match validated source")
        for info, record in zip(infos, records, strict=True):
            if info.filename.startswith("/") or ".." in Path(info.filename).parts:
                raise IntegrityError(f"unsafe archive path: {info.filename}")
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and (mode & 0o170000) not in {0, 0o100000}:
                raise IntegrityError(f"archive member is not a regular file: {info.filename}")
            if archive.read(info.filename) != record.path.read_bytes():
                raise IntegrityError(f"archive content mismatch: {record.relative}")


def run_validator(root: Path, output: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(root / "scripts" / "validate_repo.py"),
            "--root",
            str(root),
            "--json-output",
            str(output),
        ],
        check=True,
        env=environment,
    )


def ensure_output_outside_root(root: Path, output_dir: Path) -> None:
    root = root.resolve()
    resolved = output_dir.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return
    raise IntegrityError(
        f"release output must be outside the repository root: {resolved}; root={root}"
    )


def build_release(root: Path, output_dir: Path, commit: str) -> dict[str, str]:
    root = root.resolve()
    output_dir = output_dir.resolve()
    ensure_output_outside_root(root, output_dir)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not version or version.startswith("v"):
        raise IntegrityError("VERSION must contain SemVer without a leading v")

    manifest_ok, manifest_detail = verify_manifests(root)
    if not manifest_ok:
        raise IntegrityError(f"committed metadata verification failed: {manifest_detail}")

    output_dir.mkdir(parents=True, exist_ok=True)
    validation_report = output_dir / "validation-report.json"
    run_validator(root, validation_report)

    archive_name = f"frontier-intelligence-workflows-v{version}-source.zip"
    archive_path = output_dir / archive_name
    with tempfile.TemporaryDirectory(prefix="fiw-determinism-") as temporary:
        second_path = Path(temporary) / archive_name
        build_source_archive(root, archive_path, version)
        build_source_archive(root, second_path, version)
        verify_source_archive(archive_path, root, version)
        verify_source_archive(second_path, root, version)
        first_hash = sha256_file(archive_path)
        second_hash = sha256_file(second_path)
        if first_hash != second_hash or archive_path.read_bytes() != second_path.read_bytes():
            raise IntegrityError("repeated deterministic builds are not byte-identical")

    hash_path = output_dir / f"{archive_name}.sha256"
    hash_path.write_text(f"{first_hash}  {archive_name}\n", encoding="utf-8", newline="\n")

    evidence = f"""# Release Evidence — Frontier Intelligence Workflows v{version}

- Project: {PROJECT}
- Version: {version}
- Commit: {commit}
- Source archive: `{archive_name}`
- Source archive SHA-256: `{first_hash}`
- Deterministic ZIP timestamp: `1980-01-01T00:00:00Z`
- ZIP method: `stored` (cross-platform compressor-independent bytes)
- Repeated archive build: byte-identical

## Controls

The release gate verifies the repository file policy, rejects links and special filesystem entries, checks active identity and version consistency, resolves Markdown links, checks public-release boundaries and common secret patterns, validates the completed synthetic example, structurally checks the two approved GitHub Actions workflows, requires committed manifest parity, and confirms deterministic archive membership and bytes.

These controls validate structure and integrity. They do not determine the truth of external claims or confer qualification, certification, readiness, legal compliance, or deployment authority.
"""
    (output_dir / "RELEASE_EVIDENCE.md").write_text(evidence, encoding="utf-8", newline="\n")
    shutil.copy2(root / "REPO_MANIFEST.json", output_dir / "REPO_MANIFEST.json")
    shutil.copy2(root / "MANIFEST.sha256", output_dir / "MANIFEST.sha256")

    asset_hashes = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file():
            asset_hashes[path.name] = sha256_file(path)
    (output_dir / "ASSET_HASHES.json").write_text(
        json.dumps(asset_hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"archive": archive_name, "sha256": first_hash}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", default="../fiw-release-output")
    parser.add_argument("--check", action="store_true", help="Read-only verification mode; retained for CLI compatibility")
    parser.add_argument("--commit", default="candidate")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    result = build_release(root, output_dir, args.commit)
    print("Validation: PASS")
    print("Manifest: PASS")
    print(f"Archive build: PASS ({result['archive']})")
    print(f"Archive checksum: PASS ({result['sha256']})")
    print("Repeated deterministic build: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (IntegrityError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
