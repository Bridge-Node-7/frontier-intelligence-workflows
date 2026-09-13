#!/usr/bin/env python3
"""Regression tests for the public FIW Language Integrity profile."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from language_integrity import evaluate_case  # noqa: E402
from perception_integrity import validate_schema_instance  # noqa: E402

PROFILE = ROOT / "profiles" / "language-integrity"
SCHEMA = json.loads((PROFILE / "schema" / "language-integrity-case.schema.json").read_text(encoding="utf-8"))

VALID = [
    "forecast-preserved.json",
    "quoted-attribution-preserved.json",
    "inference-labeled.json",
    "provenance-collapse-visible.json",
    "temporal-supersession-visible.json",
]
INVALID = {
    "forecast-as-result.json": "LI-FORECAST-AS-RESULT",
    "attribution-loss.json": "LI-ATTRIBUTION-LOSS",
    "inference-as-direct.json": "LI-INFERENCE-AS-DIRECT",
    "provenance-independence-overstated.json": "LI-PROVENANCE-INDEPENDENCE-OVERSTATED",
    "superseded-as-current.json": "LI-SUPERSEDED-AS-CURRENT",
}


def _load(group: str, name: str) -> tuple[dict, Path, bytes]:
    path = PROFILE / "fixtures" / group / name
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), path, raw


class LanguageIntegrityTests(unittest.TestCase):
    def test_valid_synthetic_fixtures_have_no_findings(self):
        for name in VALID:
            with self.subTest(name=name):
                case, path, raw = _load("valid", name)
                self.assertEqual(validate_schema_instance(case, SCHEMA), [])
                result = evaluate_case(case, case_path=path.relative_to(ROOT).as_posix(), case_bytes=raw)
                self.assertEqual(result["status"], "NO_FINDINGS")
                self.assertEqual(result["recommendation"], "READY_FOR_HUMAN_REVIEW")
                self.assertTrue(result["human_review_required"])

    def test_invalid_synthetic_fixtures_are_schema_valid_and_fail_semantically(self):
        for name, expected in INVALID.items():
            with self.subTest(name=name):
                case, path, raw = _load("invalid", name)
                self.assertEqual(validate_schema_instance(case, SCHEMA), [])
                result = evaluate_case(case, case_path=path.relative_to(ROOT).as_posix(), case_bytes=raw)
                ids = {item["finding_id"] for item in result["findings"]}
                self.assertIn(expected, ids)
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertEqual(result["recommendation"], "REQUIRE_CORRECTION")

    def test_provenance_root_count_is_derived_not_trusted(self):
        case, path, raw = _load("valid", "provenance-collapse-visible.json")
        result = evaluate_case(case, case_path=path.relative_to(ROOT).as_posix(), case_bytes=raw)
        self.assertEqual(result["derived_independent_root_count"], 1)

    def test_unresolved_source_reference_fails_visible(self):
        case, path, raw = _load("valid", "forecast-preserved.json")
        case["claim"]["source_ids"] = ["SRC-NOT-DECLARED"]
        altered = (json.dumps(case, sort_keys=True) + "\n").encode("utf-8")
        result = evaluate_case(case, case_path=path.relative_to(ROOT).as_posix(), case_bytes=altered)
        self.assertIn("LI-SOURCE-REFERENCE-UNRESOLVED", {item["finding_id"] for item in result["findings"]})

    def test_public_boundary_and_human_authority_fail_closed(self):
        case, path, raw = _load("valid", "forecast-preserved.json")
        case["public_boundary"]["contains_sensitive_data"] = True
        case["review_requirements"]["human_review_required"] = False
        altered = (json.dumps(case, sort_keys=True) + "\n").encode("utf-8")
        result = evaluate_case(case, case_path=path.relative_to(ROOT).as_posix(), case_bytes=altered)
        ids = {item["finding_id"] for item in result["findings"]}
        self.assertIn("LI-PUBLIC-BOUNDARY-VIOLATION", ids)
        self.assertIn("LI-HUMAN-REVIEW-MISSING", ids)

    def test_cli_contract(self):
        relative = "profiles/language-integrity/fixtures/valid/forecast-preserved.json"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "run_language_integrity.py"), "--root", str(ROOT), "--case", relative, "--json-output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "NO_FINDINGS")


if __name__ == "__main__":
    unittest.main()
