#!/usr/bin/env python3
"""Compile FIW Python sources and validate semantic documents without bytecode."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_repo  # noqa: E402

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


def run_diagnostic_independence_regression(root: Path) -> None:
    """Prove policy failure remains blocking without suppressing independent scans."""

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

        # Build the synthetic credential marker dynamically so the regression
        # itself does not become a secret-pattern finding in reviewed source.
        marker_name = "api" + "_key"
        marker_value = "synthetic-credential-" + "1234567890"
        approved_doc = candidate / "docs" / "assurance" / "README.md"
        approved_doc.write_text(
            approved_doc.read_text(encoding="utf-8")
            + f"\n{marker_name}='{marker_value}'\n",
            encoding="utf-8",
            newline="\n",
        )

        report = validate_repo.validate(candidate, check_manifest=False)
        checks = {item["name"]: item for item in report["checks"]}
        if checks["file_policy_and_filesystem"]["status"] != "FAIL":
            raise RuntimeError("diagnostic regression did not preserve fail-closed file policy")
        if ".pytest_cache" not in checks["file_policy_and_filesystem"]["detail"]:
            raise RuntimeError("diagnostic regression did not identify the prohibited cache path")
        if "untracked local artifact" not in checks["file_policy_and_filesystem"]["detail"]:
            raise RuntimeError("diagnostic regression did not classify the local artifact")
        if checks["secret_patterns"]["status"] != "FAIL":
            raise RuntimeError("diagnostic regression suppressed an independent secret finding")
        for name in (
            "website_boundary",
            "markdown_links",
            "local_user_paths",
            "personal_contact_surface",
            "source_text_safety",
        ):
            if checks[name]["status"] == "NOT_RUN":
                raise RuntimeError(f"diagnostic regression suppressed independent control {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
