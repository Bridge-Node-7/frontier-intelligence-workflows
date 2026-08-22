#!/usr/bin/env python3
"""Validate Frontier Intelligence Workflows with fail-closed public-release controls."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata

# Keep validation and release tooling read-only with respect to Python bytecode.
sys.dont_write_bytecode = True
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_common import (  # noqa: E402
    EXPECTED_VERSION,
    PROJECT,
    IntegrityError,
    load_policy,
    portable_path_key,
    scan_repository,
    validate_workflow_semantics,
    verify_manifests,
)

from perception_integrity import (  # noqa: E402
    PROFILE_VERSION as PI_PROFILE_VERSION,
    RULESET_VERSION as PI_RULESET_VERSION,
    VALIDATOR_VERSION as PI_VALIDATOR_VERSION,
    canonical_json_bytes as pi_canonical_json_bytes,
    evaluate_assessment as evaluate_pi_assessment,
    sha256_bytes as pi_sha256_bytes,
    validate_schema_instance as validate_pi_schema_instance,
)

TEXT_SUFFIXES = {".md", ".txt", ".py", ".yml", ".yaml", ".json", ".csv", ".toml", ".html", ".sha256"}
TEXT_NAMES = {"LICENSE", "VERSION", ".gitattributes", ".gitignore"}
REQUIRED_FILES = {
    ".gitattributes",
    ".gitignore",
    ".github/dependabot.yml",
    ".github/workflows/validate.yml",
    ".github/workflows/release.yml",
    "CHANGELOG.md",
    "LICENSE",
    "LIMITATIONS.md",
    "MANIFEST.sha256",
    "NOTICE.md",
    "README.md",
    "REPO_FILE_POLICY.json",
    "REPO_MANIFEST.json",
    "SECURITY.md",
    "VERSION",
    "docs/assurance/README.md",
    "docs/assurance/SECURITY_TESTS.md",
    "docs/assurance/TESTING.md",
    "docs/assurance/STATUS_SEMANTICS.md",
    "profiles/perception-integrity/CONTROL_EXAMPLES.md",
    "scripts/build_release.py",
    "scripts/compile_sources.py",
    "scripts/perception_integrity.py",
    "scripts/refresh_release_metadata.py",
    "scripts/release_common.py",
    "scripts/run_tests.py",
    "scripts/run_perception_integrity.py",
    "scripts/validate_repo.py",
    "tests/test_release_tooling.py",
    "tests/test_adopter_enablement.py",
    "tests/test_frontier_claim_experience.py",
    "tests/test_perception_integrity.py",
    "tests/test_frontier_technology_diligence.py",
    "tests/test_v050_hardening.py",
    "profiles/perception-integrity/README.md",
    "profiles/perception-integrity/schema/perception-integrity-assessment.schema.json",
    "profiles/perception-integrity/schema/perception-integrity-validation.schema.json",
    "profiles/perception-integrity/schema/perception-integrity-review.schema.json",
    "profiles/perception-integrity/examples/FIW-SYN-002/PIA-FIW-SYN-002.json",
    "profiles/perception-integrity/examples/FIW-SYN-002/PIA-FIW-SYN-002.validation.json",
    "profiles/perception-integrity/examples/FIW-SYN-002/PIA-FIW-SYN-002.review.json",
    "profiles/perception-integrity/examples/FIW-SYN-002/PIA-FIW-SYN-002.review.md",
    "profiles/perception-integrity/examples/FIW-SYN-003/PIA-FIW-SYN-003.json",
    "profiles/perception-integrity/examples/FIW-SYN-003/PIA-FIW-SYN-003.validation.json",
    "profiles/perception-integrity/examples/FIW-SYN-003/PIA-FIW-SYN-003.review.json",
    "profiles/perception-integrity/examples/FIW-SYN-003/PIA-FIW-SYN-003.review.md",
    "profiles/perception-integrity/examples/FIW-SYN-004/PIA-FIW-SYN-004.json",
    "profiles/perception-integrity/examples/FIW-SYN-004/PIA-FIW-SYN-004.validation.json",
    "profiles/perception-integrity/examples/FIW-SYN-004/PIA-FIW-SYN-004.review.json",
    "profiles/perception-integrity/examples/FIW-SYN-004/PIA-FIW-SYN-004.review.md",
    "profiles/perception-integrity/fixtures/valid/assessment-ready.json",
    "profiles/perception-integrity/fixtures/invalid/missing-decision-owner.json",
    "profiles/perception-integrity/fixtures/invalid/unknown-top-level-field.json",
    "profiles/perception-integrity/fixtures/invalid/invalid-claim-mode.json",
    "profiles/perception-integrity/fixtures/invalid/unresolved-lineage.json",
    "profiles/perception-integrity/fixtures/invalid/sensitive-public-release.json",
    "templates/evidence-card.md",
    "templates/ai-governance-gate.md",
    "templates/decision-ready-brief.md",
    "templates/decision-record.md",
    "templates/perception-integrity-starter.json",
    "templates/perception-integrity-assessment.json",
    "templates/perception-integrity-assessment.md",
    "examples/synthetic-component-readiness/README.md",
    "examples/synthetic-component-readiness/source-record.md",
    "examples/synthetic-component-readiness/release-decision.md",
    "examples/frontier-claim-experience/README.md",
    "examples/frontier-claim-experience/index.html",
    "examples/frontier-technology-diligence/README.md",
    "examples/frontier-technology-diligence/decision-record.md",
    "data/synthetic/frontier-claim-experience.json",
    "data/synthetic/FIW-SYN-005-frontier-technology-diligence.json",
    "docs/evidence-cards/FIW-SYN-001-evidence-card.md",
    "docs/governance/FIW-SYN-001-governance-review.md",
    "docs/briefs/FIW-SYN-001-decision-ready-brief.md",
}
ALLOWED_OLD_NAME_FILES: set[str] = set()
EXAMPLE_FILES = {
    "examples/synthetic-component-readiness/README.md",
    "examples/synthetic-component-readiness/source-record.md",
    "examples/synthetic-component-readiness/release-decision.md",
    "docs/evidence-cards/FIW-SYN-001-evidence-card.md",
    "docs/governance/FIW-SYN-001-governance-review.md",
    "docs/briefs/FIW-SYN-001-decision-ready-brief.md",
}
FORBIDDEN_PATHS = {
    "release-artifacts",
}
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "AWS secret access key": re.compile(
        r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*[\x22\x27]?[A-Za-z0-9/+=]{40}[\x22\x27]?"
    ),
    "GitHub token": re.compile(r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}"),
    "Slack token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "Stripe secret": re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{16,}"),
    "OpenAI key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "Bearer credential": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    "Basic-auth URL": re.compile(r"(?i)https?://[^\s/:@]+:[^\s/@]+@[^\s/]+"),
    "Private key material": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "SendGrid API key": re.compile(r"SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
    "Twilio API key": re.compile(r"SK[0-9a-fA-F]{32}"),
    "Azure storage account key": re.compile(r"(?i)AccountKey=[A-Za-z0-9+/=]{32,}"),
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "Connection URI": re.compile(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s]+"),
    "Private key header": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |PGP )?PRIVATE KEY-----"),
    "Assigned secret": re.compile(
        r"(?ix)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret[_-]?key)"
        r"\s*[:=]\s*(?:[\"'][^\"'\s]{8,}[\"']|[A-Za-z0-9_./+=:@-]{12,})"
    ),
}
SOURCE_SAFETY_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".toml", ".html", ".sh"}
UNSAFE_SOURCE_CODEPOINTS = {
    *range(0x202A, 0x202F),  # bidi embeddings / overrides / PDF
    *range(0x2066, 0x206A),  # bidi isolates
    0x061C, 0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0xFEFF,
}

LOCAL_PATH_PATTERNS = {
    "Windows user path": re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s]+", re.IGNORECASE),
    "macOS user path": re.compile(r"/" + r"Users/[^/\s]+/"),
    "Linux user path": re.compile(r"/home/[A-Za-z0-9._-]+/"),
}
PLACEHOLDER_RE = re.compile(
    r"\b(?:TBD|TODO|TBC|FIXME|REPLACE_ME)\b|\[(?:write|insert|replace|add)[^\]]*\]",
    re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def secret_scan_text(path: Path, *, root: Path) -> str:
    """Return scanner text; fixture-marker exemptions are limited to top-level tests/."""
    text = read_text(path)
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return text
    if not relative.parts or relative.parts[0] != "tests":
        return text
    return "\n".join(
        line for line in text.splitlines() if "FIW_SECRET_FIXTURE" not in line
    )


def source_text_findings(path: Path) -> list[str]:
    """Reject selected source-deception controls on public code, config, and Markdown surfaces."""
    if path.suffix.lower() not in SOURCE_SAFETY_SUFFIXES:
        return []
    findings: list[str] = []
    for index, character in enumerate(read_text(path)):
        codepoint = ord(character)
        if codepoint in UNSAFE_SOURCE_CODEPOINTS:
            findings.append(
                f"{path.as_posix()}: U+{codepoint:04X} {unicodedata.name(character, 'UNNAMED')} at character {index}"
            )
    return findings


def text_files(root: Path) -> Iterable[Path]:
    records, findings = scan_repository(root, include_manifests=True)
    if findings:
        raise IntegrityError("; ".join(findings))
    for record in records:
        path = record.path
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES:
            yield path


def normalize_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " \"" in target or " '" in target:
        target = target.split(" ", 1)[0]
    target = target.split("#", 1)[0].split("?", 1)[0]
    return unquote(target)


def resolve_portable_candidate(root: Path, base: Path, target: str) -> tuple[Path | None, list[tuple[str, str]]]:
    """Resolve lexically and deterministically while preserving written path spelling."""
    root_resolved = root.resolve()
    try:
        base_relative = base.resolve().relative_to(root_resolved)
    except ValueError:
        return None, []
    target_path = PurePosixPath(target.replace("\\", "/"))
    if target_path.is_absolute():
        return None, []
    parts: list[str] = []
    for part in (*PurePosixPath(base_relative.as_posix()).parts, *target_path.parts):
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                return None, []
            parts.pop()
            continue
        parts.append(part)
    current = root_resolved
    mismatches: list[tuple[str, str]] = []
    for part in parts:
        if not current.is_dir():
            return None, mismatches
        entries = list(current.iterdir())
        exact_matches = [entry for entry in entries if entry.name == part]
        if len(exact_matches) == 1:
            current = exact_matches[0]
            continue
        portable_matches = [
            entry for entry in entries
            if portable_path_key(entry.name) == portable_path_key(part)
        ]
        if len(portable_matches) != 1:
            return None, mismatches
        actual = portable_matches[0].name
        mismatches.append((part, actual))
        current = portable_matches[0]
    return current, mismatches


PI_PROFILE_RELATIVE = "profiles/perception-integrity"
PI_SCHEMA_RELATIVES = (
    "schema/perception-integrity-assessment.schema.json",
    "schema/perception-integrity-validation.schema.json",
    "schema/perception-integrity-review.schema.json",
)
PI_CASE_EXPECTATIONS = {
    "FIW-SYN-002": "REQUIRE_CORROBORATION",
    "FIW-SYN-003": "ESCALATE_FOR_HUMAN_REVIEW",
    "FIW-SYN-004": "REQUEST_ADDITIONAL_EVIDENCE",
}
PI_REVIEW_REQUIRED_FIELDS = {
    "assessment_sha256",
    "validation_sha256",
    "reviewer_record",
    "review_time",
    "review_basis",
    "accepted_findings",
    "rejected_findings",
    "authorized_exceptions",
    "unresolved_questions",
    "human_disposition",
    "rationale",
    "stop_condition",
    "next_review_trigger",
    "public_release_decision",
}


def _pi_json_object(path: Path, issues: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"{path.as_posix()}: invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        issues.append(f"{path.as_posix()}: expected a JSON object")
        return None
    return value


def validate_perception_integrity_profile(root: Path) -> tuple[bool, str]:
    """Validate the optional PI profile and its exact artifact chains."""
    profile = root / PI_PROFILE_RELATIVE
    if not profile.exists():
        return True, "Perception Integrity integration is active; profile artifacts are not present yet."
    if not profile.is_dir():
        return False, f"{PI_PROFILE_RELATIVE} must be a directory"

    required = {"README.md", *PI_SCHEMA_RELATIVES}
    for case_id in PI_CASE_EXPECTATIONS:
        base = f"examples/{case_id}/PIA-{case_id}"
        required.update(
            {
                f"{base}.json",
                f"{base}.validation.json",
                f"{base}.review.json",
                f"{base}.review.md",
            }
        )
    missing = sorted(rel for rel in required if not (profile / rel).is_file())
    if missing:
        return False, f"Perception Integrity profile is incomplete; missing: {missing}"

    issues: list[str] = []
    readme = read_text(profile / "README.md")
    for phrase in (
        "Perception Integrity",
        "run_perception_integrity.py",
        "does not determine truth",
        "human",
    ):
        if phrase.casefold() not in readme.casefold():
            issues.append(f"README.md: missing required orientation phrase {phrase!r}")

    schema_objects: dict[str, dict[str, Any]] = {}
    for relative in PI_SCHEMA_RELATIVES:
        schema = _pi_json_object(profile / relative, issues)
        if schema is None:
            continue
        schema_objects[relative] = schema
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            issues.append(f"{relative}: unsupported or missing $schema")
        if not isinstance(schema.get("$id"), str) or not schema["$id"].strip():
            issues.append(f"{relative}: missing non-empty $id")

    for case_id, expected_recommendation in PI_CASE_EXPECTATIONS.items():
        base = profile / "examples" / case_id / f"PIA-{case_id}"
        assessment_path = base.with_suffix(".json")
        validation_path = base.with_suffix(".validation.json")
        review_path = base.with_suffix(".review.json")
        markdown_path = base.with_suffix(".review.md")

        assessment = _pi_json_object(assessment_path, issues)
        validation = _pi_json_object(validation_path, issues)
        review = _pi_json_object(review_path, issues)
        if assessment is None or validation is None or review is None:
            continue

        schema_checks = (
            ("assessment", assessment, PI_SCHEMA_RELATIVES[0]),
            ("validation", validation, PI_SCHEMA_RELATIVES[1]),
            ("review", review, PI_SCHEMA_RELATIVES[2]),
        )
        for label, instance, schema_relative in schema_checks:
            schema = schema_objects.get(schema_relative)
            if schema is None:
                continue
            for schema_issue in validate_pi_schema_instance(instance, schema):
                issues.append(f"{case_id}: {label} schema: {schema_issue}")

        assessment_bytes = assessment_path.read_bytes()
        validation_bytes = validation_path.read_bytes()
        review_bytes = review_path.read_bytes()
        relative_assessment = assessment_path.relative_to(root).as_posix()
        evaluated_at = validation.get("evaluated_at")
        try:
            expected_validation = evaluate_pi_assessment(
                assessment,
                assessment_path=relative_assessment,
                assessment_bytes=assessment_bytes,
                evaluated_at=evaluated_at,
            )
        except (TypeError, ValueError) as exc:
            issues.append(f"{case_id}: assessment evaluation failed: {exc}")
            continue

        if validation != expected_validation:
            issues.append(f"{case_id}: validation JSON does not match deterministic evaluation")
        if validation_bytes != pi_canonical_json_bytes(validation):
            issues.append(f"{case_id}: validation JSON is not canonical UTF-8/LF JSON")
        if review_bytes != pi_canonical_json_bytes(review):
            issues.append(f"{case_id}: review JSON is not canonical UTF-8/LF JSON")
        if validation.get("recommendation") != expected_recommendation:
            issues.append(
                f"{case_id}: recommendation={validation.get('recommendation')!r}; "
                f"expected {expected_recommendation!r}"
            )
        if validation.get("profile_version") != PI_PROFILE_VERSION:
            issues.append(f"{case_id}: profile version mismatch")
        if validation.get("ruleset_version") != PI_RULESET_VERSION:
            issues.append(f"{case_id}: ruleset version mismatch")
        if validation.get("validator_version") != PI_VALIDATOR_VERSION:
            issues.append(f"{case_id}: validator version mismatch")

        missing_review = sorted(PI_REVIEW_REQUIRED_FIELDS - set(review))
        if missing_review:
            issues.append(f"{case_id}: review fields missing: {missing_review}")
        assessment_sha = pi_sha256_bytes(assessment_bytes)
        validation_sha = pi_sha256_bytes(validation_bytes)
        if review.get("assessment_sha256") != assessment_sha:
            issues.append(f"{case_id}: review assessment digest mismatch")
        if review.get("validation_sha256") != validation_sha:
            issues.append(f"{case_id}: review validation digest mismatch")

        try:
            markdown = markdown_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(f"{case_id}: cannot read review Markdown: {exc}")
        else:
            for token in (case_id, assessment_sha, validation_sha):
                if token not in markdown:
                    issues.append(f"{case_id}: review Markdown missing {token}")

    if issues:
        return False, "; ".join(issues)
    return True, "Perception Integrity profile artifact chains are deterministic and digest-linked."


def validate(root: Path, check_manifest: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool | None, detail: str) -> None:
        status = "NOT_RUN" if passed is None else ("PASS" if passed else "FAIL")
        checks.append({
            "name": name,
            "status": status,
            "passed": status == "PASS",
            "detail": detail,
        })

    try:
        policy = load_policy(root)
        records, filesystem_findings = scan_repository(root, include_manifests=True)
    except IntegrityError as exc:
        policy = {}
        records = []
        filesystem_findings = [str(exc)]
    check(
        "file_policy_and_filesystem",
        not filesystem_findings,
        "All release paths are policy-approved regular files." if not filesystem_findings else "; ".join(filesystem_findings),
    )

    record_paths = {item.relative for item in records}
    missing = sorted(REQUIRED_FILES - record_paths)
    check("required_files", not missing, "All required files are present." if not missing else f"Missing: {missing}")

    forbidden_present = sorted(rel for rel in FORBIDDEN_PATHS if (root / rel).exists())
    check(
        "forbidden_legacy_paths",
        not forbidden_present,
        "No legacy release, Pages, or inactive ownership paths remain." if not forbidden_present else f"Present: {forbidden_present}",
    )

    tracked_issues: list[str] = []
    git_probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    git_metadata_available = git_probe.returncode == 0 and git_probe.stdout.strip() == "true"
    if git_metadata_available:
        tracked = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if tracked.returncode != 0:
            tracked_issues.append(f"git ls-files failed: {tracked.stderr.decode(errors='replace').strip()}")
        else:
            tracked_paths = {item.decode("utf-8", errors="strict") for item in tracked.stdout.split(b"\0") if item}
            unscanned = sorted(tracked_paths - record_paths)
            if unscanned:
                tracked_issues.append(f"TRACKED_PATH_OUTSIDE_POLICY_SCAN: {unscanned}")
    if not git_metadata_available:
        check("tracked_path_coverage", None, "Git metadata is unavailable; tracked-path coverage was not run.")
    else:
        check(
            "tracked_path_coverage",
            not tracked_issues,
            "Every tracked path is covered by the public file-policy scan." if not tracked_issues else "; ".join(tracked_issues),
        )

    version_path = root / "VERSION"
    version = read_text(version_path).strip() if version_path.is_file() else ""
    version_ok = bool(re.fullmatch(r"\d+\.\d+\.\d+", version)) and version == EXPECTED_VERSION
    check("version_format", version_ok, f"VERSION={version!r}; expected {EXPECTED_VERSION!r} without a leading v.")

    exact_release_markers = {
        "README.md": re.compile(rf"^\*\*v{re.escape(EXPECTED_VERSION)} — Decision-Ready Intelligence\*\*$", re.MULTILINE),
        "LIMITATIONS.md": re.compile(rf"^Current release: `{re.escape(EXPECTED_VERSION)}`\.$", re.MULTILINE),
        "CHANGELOG.md": re.compile(rf"^## \[{re.escape(EXPECTED_VERSION)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", re.MULTILINE),
        "docs/assurance/TESTING.md": re.compile(rf"^# Validation — v{re.escape(EXPECTED_VERSION)}$", re.MULTILINE),
    }
    version_gaps = [
        rel for rel, pattern in exact_release_markers.items()
        if not (root / rel).is_file() or pattern.search(read_text(root / rel)) is None
    ]
    check(
        "version_consistency",
        not version_gaps,
        f"Current release files contain exact {EXPECTED_VERSION} release markers."
        if not version_gaps
        else f"Missing or malformed exact release markers in: {version_gaps}",
    )

    broken_product_url: list[str] = []
    bad_url = "bridgenode7.com/frontier-intelligence-workflows"
    website_scan_error: str | None = None
    try:
        for path in text_files(root):
            rel = path.relative_to(root).as_posix()
            if rel in {"scripts/validate_repo.py", "tests/test_release_tooling.py"}:
                continue
            if bad_url in read_text(path):
                broken_product_url.append(rel)
    except IntegrityError as exc:
        website_scan_error = str(exc)
    if website_scan_error is not None:
        check("website_boundary", None, f"Website-boundary scan was not run: {website_scan_error}")
    else:
        check("website_boundary", not broken_product_url, "No nonexistent FIW website route is referenced." if not broken_product_url else f"Broken route found in: {broken_product_url}")

    readme = read_text(root / "README.md") if (root / "README.md").is_file() else ""
    readme_phrases = [
        PROJECT,
        "Turn uncertain frontier-technology claims into decision-ready intelligence.",
        "Automation checks structure, traceability, and declared evidence conditions. It does not determine truth, verify the underlying claim, make investment decisions, certify readiness, or authorize action.",
        "Keep nonpublic working evidence outside this public repository.",
        "FIW-SYN-001",
        "Perception Integrity",
        "Frontier Claim Experience",
    ]
    missing_phrases = [phrase for phrase in readme_phrases if phrase not in readme]
    check("readme_orientation", not missing_phrases, "README contains required orientation and boundaries." if not missing_phrases else f"Missing README phrases: {missing_phrases}")

    broken_links: list[str] = []
    markdown_scan_error: str | None = None
    try:
        for path in text_files(root):
            if path.suffix.lower() != ".md":
                continue
            rel = path.relative_to(root).as_posix()
            for match in MARKDOWN_LINK_RE.finditer(read_text(path)):
                target = normalize_link_target(match.group(1))
                if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                candidate, mismatches = resolve_portable_candidate(root, path.parent, target)
                if candidate is None:
                    raw_candidate = (path.parent / target).resolve()
                    try:
                        raw_candidate.relative_to(root.resolve())
                    except ValueError:
                        broken_links.append(f"{rel}: link escapes repository: {target}")
                    else:
                        broken_links.append(f"{rel}: {target}")
                elif mismatches:
                    mismatch_text = ", ".join(f"{written!r}->{actual!r}" for written, actual in mismatches)
                    broken_links.append(f"{rel}: path case/normalization mismatch for {target}: {mismatch_text}")
    except IntegrityError as exc:
        markdown_scan_error = str(exc)
    if markdown_scan_error is not None:
        check("markdown_links", None, f"Markdown-link scan was not run: {markdown_scan_error}")
    else:
        check("markdown_links", not broken_links, "All relative Markdown links resolve with portable path semantics." if not broken_links else f"Broken links: {broken_links}")

    security_text = read_text(root / "SECURITY.md") if (root / "SECURITY.md").is_file() else ""
    security_private_reporting = (
        "private vulnerability reporting" in security_text.lower()
        and "do not post sensitive security details publicly" in security_text.lower()
    )
    issue_dir = root / ".github" / "ISSUE_TEMPLATE"
    issue_files = sorted(path.relative_to(root).as_posix() for path in issue_dir.rglob("*") if path.is_file()) if issue_dir.is_dir() else []
    pr_template = root / ".github" / "PULL_REQUEST_TEMPLATE.md"
    intake_ok = security_private_reporting and not issue_files and not pr_template.exists()
    check(
        "intake_consistency",
        intake_ok,
        "Public collaboration intake is absent and private vulnerability reporting remains available."
        if intake_ok
        else f"security_private={security_private_reporting}; issue_files={issue_files}; pull_request_template={pr_template.exists()}",
    )
    secret_hits: list[str] = []
    local_path_hits: list[str] = []
    personal_contact_hits: list[str] = []
    source_safety_hits: list[str] = []
    scan_error: str | None = None
    email_pattern = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    telephone_pattern = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
    social_pattern = re.compile(r"https?://(?:www\.)?(?:linkedin\.com|instagram\.com|twitter\.com|x\.com|facebook\.com)/", re.IGNORECASE)
    reserved_email_suffixes = (".invalid", ".example", ".test", ".localhost")
    try:
        for path in text_files(root):
            rel = path.relative_to(root).as_posix()
            text = secret_scan_text(path, root=root)
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    secret_hits.append(f"{rel}: {label}")
            for label, pattern in LOCAL_PATH_PATTERNS.items():
                if pattern.search(text):
                    local_path_hits.append(f"{rel}: {label}")
            for match in email_pattern.finditer(text):
                domain = match.group(0).rsplit("@", 1)[1].lower()
                if domain.endswith(reserved_email_suffixes):
                    continue
                personal_contact_hits.append(f"{rel}: email address")
            if telephone_pattern.search(text):
                personal_contact_hits.append(f"{rel}: telephone number")
            if social_pattern.search(text):
                personal_contact_hits.append(f"{rel}: personal social profile")
            source_safety_hits.extend(
                f"{rel}: {item.split(': ', 1)[-1]}" for item in source_text_findings(path)
            )
    except IntegrityError as exc:
        scan_error = str(exc)
    if scan_error is not None:
        check("secret_patterns", None, f"Secret-pattern scan was not run: {scan_error}")
        check("local_user_paths", None, f"Local-path scan was not run: {scan_error}")
        check("personal_contact_surface", None, f"Personal-contact scan was not run: {scan_error}")
        check("source_text_safety", None, f"Source-text safety scan was not run: {scan_error}")
    else:
        check("secret_patterns", not secret_hits, "No configured secret patterns found." if not secret_hits else f"Potential secrets: {secret_hits}")
        check("local_user_paths", not local_path_hits, "No local user paths found." if not local_path_hits else f"Local paths: {local_path_hits}")
        check("personal_contact_surface", not personal_contact_hits, "No personal contact information or personal social-profile links found." if not personal_contact_hits else f"Personal contact surfaces: {personal_contact_hits}")
        check("source_text_safety", not source_safety_hits, "No selected deceptive Unicode controls found on public code/configuration/Markdown surfaces." if not source_safety_hits else f"Unsafe source text: {source_safety_hits}")

    boundary = read_text(root / "NOTICE.md") if (root / "NOTICE.md").is_file() else ""
    boundary_terms = [
        "intended for unrestricted publication",
        "protecting sensitive information",
        "does not grant trademark rights",
        "Do not place nonpublic",
    ]
    missing_boundary = [term for term in boundary_terms if term.lower() not in boundary.lower()]
    check(
        "public_private_boundary",
        not missing_boundary,
        "NOTICE states the public-release and information-protection boundary."
        if not missing_boundary
        else f"Missing boundary terms: {missing_boundary}",
    )

    example_missing = sorted(rel for rel in EXAMPLE_FILES if not (root / rel).is_file())
    example_issues: list[str] = []
    for rel in sorted(EXAMPLE_FILES):
        path = root / rel
        if not path.is_file():
            continue
        text = read_text(path)
        if "FIW-SYN-001" not in text:
            example_issues.append(f"{rel}: missing case ID")
        if PLACEHOLDER_RE.search(text):
            example_issues.append(f"{rel}: unresolved placeholder")
    all_example_text = "\n".join(read_text(root / rel) for rel in EXAMPLE_FILES if (root / rel).is_file())
    required_ids = ["SRC-FIW-SYN-001", "EVC-FIW-SYN-001", "GOV-FIW-SYN-001", "BRF-FIW-SYN-001", "DEC-FIW-SYN-001"]
    missing_ids = [item for item in required_ids if item not in all_example_text]
    required_file_ids = {
        "examples/synthetic-component-readiness/source-record.md": "SRC-FIW-SYN-001",
        "docs/evidence-cards/FIW-SYN-001-evidence-card.md": "EVC-FIW-SYN-001",
        "docs/governance/FIW-SYN-001-governance-review.md": "GOV-FIW-SYN-001",
        "docs/briefs/FIW-SYN-001-decision-ready-brief.md": "BRF-FIW-SYN-001",
        "examples/synthetic-component-readiness/release-decision.md": "DEC-FIW-SYN-001",
    }
    for rel, required_id in required_file_ids.items():
        path = root / rel
        if path.is_file() and required_id not in read_text(path):
            example_issues.append(f"{rel}: missing own artifact ID {required_id}")
    example_ok = not example_missing and not example_issues and not missing_ids
    check(
        "synthetic_example_traceability",
        example_ok,
        "FIW-SYN-001 is complete and traceable." if example_ok else f"Missing files={example_missing}; issues={example_issues}; missing IDs={missing_ids}",
    )

    pi_ok, pi_detail = validate_perception_integrity_profile(root)
    check("perception_integrity_profile", pi_ok, pi_detail)
    workflow_issues = validate_workflow_semantics(root) if policy else ["workflow policy unavailable"]
    check("workflow_controls", not workflow_issues, "Only approved pinned workflows with bounded permissions are present." if not workflow_issues else "; ".join(workflow_issues))

    if check_manifest:
        try:
            manifest_ok, manifest_detail = verify_manifests(root)
        except IntegrityError as exc:
            manifest_ok, manifest_detail = False, str(exc)
        check("manifest_consistency", manifest_ok, manifest_detail)

    passed = all(item["status"] == "PASS" for item in checks)
    return {
        "project": PROJECT,
        "version": version,
        "passed": passed,
        "summary": {"passed": sum(1 for item in checks if item["passed"]), "total": len(checks)},
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--json-output", help="Write machine-readable validation report")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: repository root does not exist: {root}", file=sys.stderr)
        return 2

    report = validate(root, check_manifest=True)
    for item in report["checks"]:
        status = item["status"]
        print(f"[{status}] {item['name']}: {item['detail']}")
    print(f"Validation: {'PASS' if report['passed'] else 'FAIL'} ({report['summary']['passed']}/{report['summary']['total']})")

    if args.json_output:
        output = Path(args.json_output)
        if not output.is_absolute():
            output = (Path.cwd() / output).resolve()
        else:
            output = output.resolve()
        try:
            output.relative_to(root)
        except ValueError:
            pass
        else:
            print(f"ERROR: validation report must be written outside the repository root: {output}", file=sys.stderr)
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
