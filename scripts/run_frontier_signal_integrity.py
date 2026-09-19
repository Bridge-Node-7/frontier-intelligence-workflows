#!/usr/bin/env python3
"""Evaluate one Radiant Guardian case without determining truth or authorizing action."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from radiant_guardian import canonical_json_bytes, evaluate_case, structural_issues  # noqa: E402


def _resolve_case(root: Path, raw: str) -> tuple[Path, str]:
    candidate = Path(raw)
    if not candidate.is_absolute():
        repo = (root / candidate).resolve()
        candidate = repo if repo.is_file() else (Path.cwd() / candidate).resolve()
    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError:
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in resolved.name) or "case.json"
        relative = f"external/{safe}"
    return resolved, relative


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--case", required=True)
    parser.add_argument("--evaluated-at", required=True)
    parser.add_argument("--json-output", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: repository root does not exist: {root}", file=sys.stderr)
        return 2
    try:
        case_path, relative = _resolve_case(root, args.case)
        output = Path(args.json_output).resolve()
        try:
            output.relative_to(root)
        except ValueError:
            pass
        else:
            raise ValueError("json output must be outside the repository root")
        raw = case_path.read_bytes()
        case = json.loads(raw.decode("utf-8"))
        issues = structural_issues(case)
        if issues:
            for issue in issues:
                print(f"SCHEMA: {issue}", file=sys.stderr)
            return 3
        report = evaluate_case(case, root=root, case_path=relative, case_bytes=raw, evaluated_at=args.evaluated_at)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json_bytes(report))
        print(f"Radiant Guardian: {report['validation_status']}")
        if report["validation_status"] == "NO_RG_FINDINGS":
            print("Meaning: no configured RG integrity rule produced a finding; underlying evidence is not verified.")
        print(f"Recommendation: {report['recommendation']}")
        print("Human decision required: true")
        print(f"Output: {output}")
        return 0 if report["recommendation"] == "READY_FOR_HUMAN_REVIEW" else 1
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
