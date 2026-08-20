#!/usr/bin/env python3
"""Run FIW source tests and fail on unexpected skipped security controls."""

from __future__ import annotations

import argparse
import json
import os
import sys
import unittest
from pathlib import Path

ALLOWED_SKIPS_BY_PLATFORM = {
    "nt": {
        "test_release_tooling.ReleaseToolingTests.test_04_symbolic_link_rejected",
        "test_release_tooling.ReleaseToolingTests.test_05_symbolic_directory_rejected",
        "test_release_tooling.ReleaseToolingTests.test_06_fifo_rejected",
        "test_release_tooling.ReleaseToolingTests.test_07_control_character_path_rejected",
    },
    "posix": set(),
}


class RecordingResult(unittest.TextTestResult):
    pass


def main() -> int:
    # Prevent tests and their subprocesses from mutating the reviewed source tree.
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--json-output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), pattern="test*.py")
    runner = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult)
    result = runner.run(suite)
    skipped = {test.id(): reason for test, reason in result.skipped}
    allowed = ALLOWED_SKIPS_BY_PLATFORM.get(os.name, set())
    unexpected = sorted(set(skipped) - allowed)
    missing_platform_controls = sorted(allowed - set(skipped)) if os.name == "nt" else []
    # On Windows, platform-specific integration tests may execute instead of skip; that is stronger evidence.
    summary = {
        "platform": os.name,
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": skipped,
        "unexpected_skips": unexpected,
        "allowed_platform_skips_not_used": missing_platform_controls,
        "passed": result.wasSuccessful() and not unexpected,
    }
    if args.json_output:
        output = Path(args.json_output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if unexpected:
        print(f"Unexpected mandatory test skips: {unexpected}", file=sys.stderr)
    print(
        f"Source tests: {'PASS' if summary['passed'] else 'FAIL'} "
        f"({result.testsRun} run; {len(skipped)} platform-declared skips; {len(unexpected)} unexpected skips)"
    )
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
