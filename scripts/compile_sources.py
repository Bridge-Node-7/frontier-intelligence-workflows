#!/usr/bin/env python3
"""Compile FIW sources, validate schemas, and provide hardened repository validation."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_repo as base_validator  # noqa: E402
from release_common import load_policy, scan_repository  # noqa: E402

SUPPORTED_SCHEMA_URI = "https://json-schema.org/draft/2020-12/schema"
JSON_SCHEMA_TYPES = {"null", "boolean", "object", "array", "number", "string", "integer"}
SCHEMA_MAP_KEYWORDS = {"properties", "patternProperties", "$defs", "dependentSchemas"}
SCHEMA_SINGLE_KEYWORDS = {
    "additionalProperties",
    "unevaluatedProperties",
    "propertyNames",
    "contains",
    "not",
    "if",
    "then",
    "else",
}
SCHEMA_ARRAY_KEYWORDS = {"allOf", "anyOf", "oneOf", "prefixItems"}
NONNEGATIVE_INTEGER_KEYWORDS = {
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "minContains",
    "maxContains",
    "minProperties",
    "maxProperties",
}


def _schema_error(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def _validate_schema_node(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, bool):
        return
    if not isinstance(value, dict):
        _schema_error(errors, path, "schema node must be an object or boolean")
        return

    schema_type = value.get("type")
    if schema_type is not None:
        types = schema_type if isinstance(schema_type, list) else [schema_type]
        if not types or any(
            not isinstance(item, str) or item not in JSON_SCHEMA_TYPES for item in types
        ):
            _schema_error(errors, f"{path}.type", f"unsupported type declaration {schema_type!r}")
        elif len(set(types)) != len(types):
            _schema_error(errors, f"{path}.type", "type array contains duplicates")

    required = value.get("required")
    if required is not None:
        if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
            _schema_error(errors, f"{path}.required", "must be an array of strings")
        elif len(set(required)) != len(required):
            _schema_error(errors, f"{path}.required", "contains duplicate property names")

    enum = value.get("enum")
    if enum is not None and (not isinstance(enum, list) or not enum):
        _schema_error(errors, f"{path}.enum", "must be a non-empty array")

    pattern = value.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            _schema_error(errors, f"{path}.pattern", "must be a string")
        else:
            try:
                re.compile(pattern)
            except re.error as exc:
                _schema_error(errors, f"{path}.pattern", f"invalid regular expression: {exc}")

    reference = value.get("$ref")
    if reference is not None and (not isinstance(reference, str) or not reference.strip()):
        _schema_error(errors, f"{path}.$ref", "must be a non-empty string")

    for keyword in NONNEGATIVE_INTEGER_KEYWORDS:
        if keyword in value:
            candidate = value[keyword]
            if isinstance(candidate, bool) or not isinstance(candidate, int) or candidate < 0:
                _schema_error(errors, f"{path}.{keyword}", "must be a non-negative integer")

    for keyword in SCHEMA_MAP_KEYWORDS:
        if keyword not in value:
            continue
        mapping = value[keyword]
        if not isinstance(mapping, dict):
            _schema_error(errors, f"{path}.{keyword}", "must be an object of schemas")
            continue
        for name, child in mapping.items():
            if not isinstance(name, str):
                _schema_error(errors, f"{path}.{keyword}", "schema map keys must be strings")
                continue
            _validate_schema_node(child, f"{path}.{keyword}[{name!r}]", errors)

    if "items" in value:
        items = value["items"]
        if isinstance(items, list):
            _schema_error(errors, f"{path}.items", "Draft 2020-12 tuple schemas must use prefixItems")
        else:
            _validate_schema_node(items, f"{path}.items", errors)

    for keyword in SCHEMA_SINGLE_KEYWORDS:
        if keyword in value:
            _validate_schema_node(value[keyword], f"{path}.{keyword}", errors)

    for keyword in SCHEMA_ARRAY_KEYWORDS:
        if keyword not in value:
            continue
        children = value[keyword]
        if not isinstance(children, list) or not children:
            _schema_error(errors, f"{path}.{keyword}", "must be a non-empty array of schemas")
            continue
        for index, child in enumerate(children):
            _validate_schema_node(child, f"{path}.{keyword}[{index}]", errors)


def validate_schema_text(text: str, relative: str) -> list[str]:
    errors: list[str] = []
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{relative}: invalid JSON: {exc}"]
    if not isinstance(document, dict):
        return [f"{relative}: root schema must be a JSON object"]
    if document.get("$schema") != SUPPORTED_SCHEMA_URI:
        errors.append(
            f"{relative}: $schema must be {SUPPORTED_SCHEMA_URI!r}; "
            f"observed {document.get('$schema')!r}"
        )
    schema_id = document.get("$id")
    if schema_id is not None and (not isinstance(schema_id, str) or not schema_id.strip()):
        errors.append(f"{relative}: $id must be a non-empty string when present")
    _validate_schema_node(document, relative, errors)
    return errors


def validate_schema_documents(root: Path) -> tuple[list[str], list[str]]:
    schemas: list[str] = []
    errors: list[str] = []
    for path in sorted(root.rglob("*.schema.json")):
        if ".git" in path.relative_to(root).parts:
            continue
        relative = path.relative_to(root).as_posix()
        schemas.append(relative)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{relative}: cannot read: {exc}")
            continue
        errors.extend(validate_schema_text(text, relative))
    if not schemas:
        errors.append("No *.schema.json documents were found.")
    return schemas, errors


def run_schema_negative_regressions() -> None:
    malformed = validate_schema_text("{\n", "synthetic-malformed.schema.json")
    if not malformed or "invalid JSON" not in malformed[0]:
        raise RuntimeError("schema parser negative regression did not fail closed")
    structurally_invalid = validate_schema_text(
        json.dumps(
            {
                "$schema": SUPPORTED_SCHEMA_URI,
                "type": "object",
                "properties": [],
            }
        ),
        "synthetic-structural.schema.json",
    )
    if not structurally_invalid or not any("properties" in item for item in structurally_invalid):
        raise RuntimeError("schema structural negative regression did not fail closed")


def approved_text_files(root: Path) -> Iterable[Path]:
    """Yield policy-approved text files while preserving separate filesystem findings."""
    records, _findings = scan_repository(root, include_manifests=True)
    for record in records:
        path = record.path
        if path.suffix.lower() in base_validator.TEXT_SUFFIXES or path.name in base_validator.TEXT_NAMES:
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


def validate_repository(root: Path, *, check_manifest: bool = True) -> dict[str, Any]:
    """Run the 19-control validator while keeping independent scans independent."""
    original_text_files = base_validator.text_files
    base_validator.text_files = approved_text_files
    try:
        report = base_validator.validate(root, check_manifest=check_manifest)
    finally:
        base_validator.text_files = original_text_files

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


def run_diagnostic_independence_regression(root: Path) -> None:
    """Prove a prohibited local artifact fails policy without suppressing other scans."""
    with tempfile.TemporaryDirectory(prefix="fiw-diagnostic-regression-") as temporary:
        candidate = Path(temporary) / "repo"
        shutil.copytree(
            root,
            candidate,
            ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "validation-report.json"),
            symlinks=True,
        )
        subprocess.run(["git", "-C", str(candidate), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(candidate), "add", "-A"], check=True)

        cache = candidate / ".pytest_cache" / "private-client-data.txt"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("nonpublic local artifact\n", encoding="utf-8", newline="\n")

        approved_doc = candidate / "docs" / "assurance" / "README.md"
        approved_doc.write_text(
            approved_doc.read_text(encoding="utf-8")
            + "\napi_key='this-is-a-realistic-secret-value'\n",
            encoding="utf-8",
            newline="\n",
        )

        report = validate_repository(candidate, check_manifest=False)
        checks = {item["name"]: item for item in report["checks"]}
        if checks["file_policy_and_filesystem"]["status"] != "FAIL":
            raise RuntimeError("diagnostic regression did not preserve fail-closed file policy")
        if ".pytest_cache" not in checks["file_policy_and_filesystem"]["detail"]:
            raise RuntimeError("diagnostic regression did not identify the prohibited cache path")
        if "untracked local artifact" not in checks["file_policy_and_filesystem"]["detail"]:
            raise RuntimeError("diagnostic regression did not classify the local artifact")
        if checks["secret_patterns"]["status"] != "FAIL":
            raise RuntimeError("diagnostic regression suppressed an independent secret finding")
        for name in ("website_boundary", "markdown_links", "local_user_paths", "personal_contact_surface", "source_text_safety"):
            if checks[name]["status"] == "NOT_RUN":
                raise RuntimeError(f"diagnostic regression suppressed independent control {name}")


def _print_repository_report(report: dict[str, Any]) -> None:
    for item in report["checks"]:
        print(f"[{item['status']}] {item['name']}: {item['detail']}")
    print(
        f"Validation: {'PASS' if report['passed'] else 'FAIL'} "
        f"({report['summary']['passed']}/{report['summary']['total']})"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--validate-repository",
        action="store_true",
        help="Run hardened 19-control repository validation after source/schema preflight.",
    )
    parser.add_argument("--json-output", help="Write hardened repository validation JSON outside the repository root.")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    compiled: list[str] = []
    for directory_name in ("scripts", "tests"):
        directory = root / directory_name
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            relative = path.relative_to(root).as_posix()
            compile(path.read_text(encoding="utf-8"), relative, "exec")
            compiled.append(relative)

    run_schema_negative_regressions()
    schemas, schema_errors = validate_schema_documents(root)
    if schema_errors:
        for issue in schema_errors:
            print(f"Schema document FAIL: {issue}")
        return 1

    run_diagnostic_independence_regression(root)
    print(
        f"Schema documents: PASS ({len(schemas)} files; parser and structural "
        "negative regressions fail closed)"
    )
    print("Validation diagnostics: PASS (policy failure does not suppress independent scans)")
    print(f"Python syntax: PASS ({len(compiled)} files; no bytecode written)")

    if not args.validate_repository:
        return 0

    report = validate_repository(root, check_manifest=True)
    _print_repository_report(report)
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
            print(
                f"ERROR: validation report must be written outside the repository root: {output}",
                file=sys.stderr,
            )
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
