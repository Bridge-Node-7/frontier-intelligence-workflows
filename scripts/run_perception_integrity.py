#!/usr/bin/env python3
"""Evaluate one Perception Integrity assessment without authorizing action."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from perception_integrity import (  # noqa: E402
    canonical_json_bytes,
    evaluate_assessment,
    validate_schema_instance,
)


def _assessment_source(root: Path, raw_value: str) -> tuple[Path, str]:
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        repository_candidate = (root / candidate).resolve()
        if repository_candidate.is_file():
            candidate = repository_candidate
        else:
            candidate = (Path.cwd() / candidate).resolve()
    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        safe_name = "".join(
            character if character.isalnum() or character in "._-" else "_"
            for character in resolved.name
        ) or "assessment.json"
        return resolved, f"external/{safe_name}"
    return resolved, relative.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--assessment", required=True, help="Assessment JSON path; repository or explicit external file")
    parser.add_argument("--evaluated-at", required=True, help="UTC RFC3339 timestamp")
    parser.add_argument("--json-output", required=True, help="Output path outside the repository")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: repository root does not exist: {root}", file=sys.stderr)
        return 2
    try:
        assessment_path, relative = _assessment_source(root, args.assessment)
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
            raise ValueError("json output must be outside the repository root")

        assessment_bytes = assessment_path.read_bytes()
        assessment = json.loads(assessment_bytes.decode("utf-8"))
        if not isinstance(assessment, dict):
            raise ValueError("assessment JSON must contain one object")
        schema_path = root / "profiles/perception-integrity/schema/perception-integrity-assessment.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        issues = validate_schema_instance(assessment, schema)
        if issues:
            for issue in issues:
                print(f"SCHEMA: {issue}", file=sys.stderr)
            return 3
        report = evaluate_assessment(
            assessment,
            assessment_path=relative,
            assessment_bytes=assessment_bytes,
            evaluated_at=args.evaluated_at,
        )
        validation_schema_path = root / "profiles/perception-integrity/schema/perception-integrity-validation.schema.json"
        validation_schema = json.loads(validation_schema_path.read_text(encoding="utf-8"))
        output_issues = validate_schema_instance(report, validation_schema)
        if output_issues:
            for issue in output_issues:
                print(f"OUTPUT_SCHEMA: {issue}", file=sys.stderr)
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json_bytes(report))
        print(f"Perception Integrity: {report['validation_status']}")
        print(f"Recommendation: {report['recommendation']}")
        print("Human decision required: true")
        print(f"Output: {output}")
        return 0 if report["recommendation"] == "READY_FOR_HUMAN_REVIEW" else 1
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
