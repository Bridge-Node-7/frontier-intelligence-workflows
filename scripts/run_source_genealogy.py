#!/usr/bin/env python3
"""Run the bounded Source Genealogy profile against one declared JSON case."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from source_genealogy import evaluate_case


def _relative_case_path(root: Path, path: Path) -> str:
    root_resolved = root.resolve()
    path_resolved = path.resolve()
    try:
        return path_resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        return f"external/{path.name}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate declared source genealogy without crawling or authenticating external sources.")
    parser.add_argument("--root", default=".", help="Repository root used only for stable case-path labeling.")
    parser.add_argument("--case", required=True, help="JSON Source Genealogy case.")
    parser.add_argument("--json-output", help="Optional result path. Existing files are replaced explicitly.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    case_path = Path(args.case)
    try:
        case_bytes = case_path.read_bytes()
        case = json.loads(case_bytes.decode("utf-8"))
        if not isinstance(case, dict):
            raise ValueError("case JSON must be an object")
        result = evaluate_case(
            case,
            case_path=_relative_case_path(root, case_path),
            case_bytes=case_bytes,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"SOURCE_GENEALOGY_INPUT_ERROR: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        output = Path(args.json_output)
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8", newline="\n")
        except OSError as exc:
            print(f"SOURCE_GENEALOGY_OUTPUT_ERROR: {exc}", file=sys.stderr)
            return 2
    else:
        print(rendered, end="")

    return 0 if result["status"] == "NO_FINDINGS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
