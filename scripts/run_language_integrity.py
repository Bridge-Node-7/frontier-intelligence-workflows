#!/usr/bin/env python3
"""Run the bounded FIW Language Integrity profile against one declared case."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from language_integrity import evaluate_case  # noqa: E402
from perception_integrity import validate_schema_instance  # noqa: E402

SCHEMA_RELATIVE = Path("profiles/language-integrity/schema/language-integrity-case.schema.json")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _contained(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("case must remain inside the declared root") from exc
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--case", required=True)
    parser.add_argument("--json-output")
    args = parser.parse_args()

    try:
        root = Path(args.root).resolve()
        case_path = _contained(root, root / args.case)
        schema_path = root / SCHEMA_RELATIVE
        case_bytes = case_path.read_bytes()
        case = json.loads(case_bytes.decode("utf-8"))
        schema = _load_json(schema_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"Language Integrity input error: {exc}", file=sys.stderr)
        return 2

    schema_issues = validate_schema_instance(case, schema)
    if schema_issues:
        for issue in schema_issues:
            print(f"SCHEMA: {issue}", file=sys.stderr)
        return 3

    try:
        relative = case_path.relative_to(root).as_posix()
        result = evaluate_case(case, case_path=relative, case_bytes=case_bytes)
    except (TypeError, ValueError) as exc:
        print(f"Language Integrity evaluation error: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        try:
            output = Path(args.json_output).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8", newline="\n")
        except OSError as exc:
            print(f"Language Integrity output error: {exc}", file=sys.stderr)
            return 2
    else:
        print(text, end="")

    return 0 if result["status"] == "NO_FINDINGS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
