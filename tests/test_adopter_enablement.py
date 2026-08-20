#!/usr/bin/env python3
"""Regression tests for the FIW operational assessment path."""
from __future__ import annotations

import copy
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

from perception_integrity import canonical_json_bytes, evaluate_assessment, validate_schema_instance  # noqa: E402
from run_perception_integrity import main as run_pi  # noqa: E402
from validate_repo import SECRET_PATTERNS, TEXT_SUFFIXES  # noqa: E402

EVALUATED_AT = "2026-08-08T12:00:00Z"


def template() -> dict:
    return json.loads((ROOT / "templates/perception-integrity-assessment.json").read_text(encoding="utf-8"))


def evaluate(value: dict) -> dict:
    return evaluate_assessment(
        value,
        assessment_path="templates/perception-integrity-assessment.json",
        assessment_bytes=canonical_json_bytes(value),
        evaluated_at=EVALUATED_AT,
    )


class AdopterEnablementTests(unittest.TestCase):
    def test_00_template_is_schema_valid(self) -> None:
        schema = json.loads(
            (ROOT / "profiles/perception-integrity/schema/perception-integrity-assessment.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(validate_schema_instance(template(), schema), [])

    def test_01_cli_emits_deterministic_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-adopter-") as temporary:
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            arguments = [
                "--root", str(ROOT),
                "--assessment", "templates/perception-integrity-assessment.json",
                "--evaluated-at", EVALUATED_AT,
            ]
            self.assertEqual(run_pi([*arguments, "--json-output", str(first)]), 0)
            self.assertEqual(run_pi([*arguments, "--json-output", str(second)]), 0)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            report = json.loads(first.read_text(encoding="utf-8"))
            self.assertTrue(report["human_decision_required"])
            self.assertEqual(report["recommendation"], "READY_FOR_HUMAN_REVIEW")
            self.assertEqual(report["profile_version"], "0.3.0")
            self.assertEqual(report["ruleset_version"], "1.1.0")
            self.assertEqual(report["validator_version"], "0.3.0")
            validation_schema = json.loads(
                (ROOT / "profiles/perception-integrity/schema/perception-integrity-validation.schema.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(validate_schema_instance(report, validation_schema), [])

    def test_02_unicode_nfc_nfd_collision_is_detected(self) -> None:
        value = template()
        value["observation"] = ["Caf\u00e9 measurement"]
        value["inference"] = ["Cafe\u0301 measurement"]
        findings = {item["finding_id"] for item in evaluate(value)["findings"]}
        self.assertIn("PI-INFERENCE-AS-OBSERVATION", findings)

    def test_03_inner_whitespace_collision_is_detected(self) -> None:
        value = template()
        value["observation"] = ["Synthetic   measurement"]
        value["inference"] = ["Synthetic measurement"]
        findings = {item["finding_id"] for item in evaluate(value)["findings"]}
        self.assertIn("PI-INFERENCE-AS-OBSERVATION", findings)

    def test_04_zero_width_collision_is_detected(self) -> None:
        value = template()
        value["observation"] = ["Synthetic measurement"]
        value["inference"] = ["Synthetic\u200b measurement"]
        findings = {item["finding_id"] for item in evaluate(value)["findings"]}
        self.assertIn("PI-INFERENCE-AS-OBSERVATION", findings)

    def test_05_secret_patterns_cover_adopter_formats(self) -> None:
        samples = (
            ("AWS secret access key", "aws" + "_secret_access_key = " + "A" * 40),
            ("GitHub token", "github" + "_pat_" + "A" * 24),
            ("Slack token", "xox" + "b-" + "A" * 20),
            ("Stripe secret", "sk_" + "live_" + "A" * 24),
            ("OpenAI key", "sk-" + "proj-" + "A" * 24),
            ("Google API key", "AIza" + "A" * 32),
            ("JWT", "eyJ" + "A" * 12 + "." + "B" * 12 + "." + "C" * 12),
            ("Connection URI", "postgres" + "ql://user:secret@example.invalid/db"),
            ("Assigned secret", "pass" + "word = " + "SuperSecretValue123"),
            ("Assigned secret", "api" + "_key: " + "AnotherSecretValue456"),
        )
        for label, value in samples:
            with self.subTest(label=label, sample=value[:12]):
                self.assertIsNotNone(SECRET_PATTERNS[label].search(value))

    def test_06_public_collaboration_surface_is_minimal(self) -> None:
        self.assertFalse((ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").exists())
        issue_dir = ROOT / ".github" / "ISSUE_TEMPLATE"
        issue_files = sorted(path for path in issue_dir.rglob("*") if path.is_file()) if issue_dir.is_dir() else []
        self.assertEqual(issue_files, [])
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
        self.assertIn("private vulnerability reporting", security)

    def test_07_public_docs_expose_external_working_model(self) -> None:
        combined = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in ("README.md", "profiles/perception-integrity/README.md"))
        self.assertIn("run_perception_integrity.py", combined)
        self.assertIn("outside this public repository", combined)

    def test_08_cli_returns_one_for_actionable_findings(self) -> None:
        assessment = ROOT / "profiles/perception-integrity/fixtures/invalid/sensitive-public-release.json"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "validation.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_perception_integrity.py"),
                    "--root",
                    str(ROOT),
                    "--assessment",
                    str(assessment.relative_to(ROOT)),
                    "--evaluated-at",
                    "2026-08-08T12:00:00Z",
                    "--json-output",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommendation"], "DO_NOT_RELEASE_PUBLICLY")

    def test_09_cli_returns_three_for_schema_invalid_input(self) -> None:
        assessment = ROOT / "profiles/perception-integrity/fixtures/invalid/unknown-top-level-field.json"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "validation.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_perception_integrity.py"),
                    "--root",
                    str(ROOT),
                    "--assessment",
                    str(assessment.relative_to(ROOT)),
                    "--evaluated-at",
                    "2026-08-08T12:00:00Z",
                    "--json-output",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 3)
            self.assertFalse(out.exists())

    def test_10_cli_rejects_output_inside_repository(self) -> None:
        output = ROOT / "adopter-output-must-not-exist.json"
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_perception_integrity.py"),
                    "--root",
                    str(ROOT),
                    "--assessment",
                    "templates/perception-integrity-assessment.json",
                    "--evaluated-at",
                    "2026-08-08T12:00:00Z",
                    "--json-output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())
        finally:
            output.unlink(missing_ok=True)

    def test_11_cli_accepts_explicit_external_assessment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-external-assessment-") as td:
            external = Path(td) / "external-assessment.json"
            external.write_bytes(
                (ROOT / "templates/perception-integrity-assessment.json").read_bytes()
            )
            output = Path(td) / "external-validation.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_perception_integrity.py"),
                    "--root",
                    str(ROOT),
                    "--assessment",
                    str(external),
                    "--evaluated-at",
                    "2026-08-08T12:00:00Z",
                    "--json-output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(report["assessment_path"].startswith("external/"))
            self.assertTrue(report["human_decision_required"])

    def test_12_cli_returns_two_for_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-malformed-assessment-") as td:
            assessment = Path(td) / "malformed.json"
            assessment.write_text("{not-json", encoding="utf-8")
            output = Path(td) / "validation.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_perception_integrity.py"),
                    "--root",
                    str(ROOT),
                    "--assessment",
                    str(assessment),
                    "--evaluated-at",
                    "2026-08-08T12:00:00Z",
                    "--json-output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_13_cli_returns_two_for_missing_assessment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-missing-assessment-") as td:
            missing = Path(td) / "missing.json"
            output = Path(td) / "validation.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_perception_integrity.py"),
                    "--root",
                    str(ROOT),
                    "--assessment",
                    str(missing),
                    "--evaluated-at",
                    "2026-08-08T12:00:00Z",
                    "--json-output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())


    def test_14_public_html_surface_is_in_validator_text_scan(self) -> None:
        self.assertIn(".html", TEXT_SUFFIXES)

    def test_15_external_assessment_does_not_leak_absolute_source_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-external-privacy-") as td:
            external = Path(td) / "working-assessment.json"
            external.write_bytes((ROOT / "templates/perception-integrity-assessment.json").read_bytes())
            output = Path(td) / "validation.json"
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/run_perception_integrity.py"), "--root", str(ROOT), "--assessment", str(external), "--evaluated-at", "2026-08-08T12:00:00Z", "--json-output", str(output)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            raw = output.read_text(encoding="utf-8")
            self.assertNotIn(str(external.resolve()), raw)
            report = json.loads(raw)
            self.assertEqual(report["assessment_path"], "external/working-assessment.json")


if __name__ == "__main__":
    unittest.main()
