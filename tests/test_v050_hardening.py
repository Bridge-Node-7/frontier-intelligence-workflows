#!/usr/bin/env python3
"""Adversarial regressions for FIW v0.5 trust-semantics hardening."""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from perception_integrity import (  # noqa: E402
    PROFILE_VERSION,
    RULESET_VERSION,
    VALIDATOR_VERSION,
    canonical_json_bytes,
    evaluate_assessment,
)
from validate_repo import (  # noqa: E402
    SECRET_PATTERNS,
    TEXT_SUFFIXES,
    secret_scan_text,
    source_text_findings,
    validate,
)

EVALUATED_AT = "2026-08-21T12:00:00Z"


def assessment() -> dict:
    return json.loads((ROOT / "templates" / "perception-integrity-assessment.json").read_text(encoding="utf-8"))


def evaluate(value: dict) -> dict:
    return evaluate_assessment(
        value,
        assessment_path="tests/synthetic-v050.json",
        assessment_bytes=canonical_json_bytes(value),
        evaluated_at=EVALUATED_AT,
    )


class V050HardeningTests(unittest.TestCase):
    def test_00_component_versions_are_v050_contract(self) -> None:
        self.assertEqual(PROFILE_VERSION, "0.4.0")
        self.assertEqual(VALIDATOR_VERSION, "0.4.0")
        self.assertEqual(RULESET_VERSION, "1.2.0")

    def test_01_clean_pi_record_reports_no_findings_not_pass(self) -> None:
        report = evaluate(assessment())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["validation_status"], "NO_FINDINGS")
        self.assertNotEqual(report["validation_status"], "PASS")
        self.assertTrue(report["human_decision_required"])

    def test_02_starter_is_intentionally_incomplete(self) -> None:
        value = json.loads((ROOT / "templates" / "perception-integrity-starter.json").read_text(encoding="utf-8"))
        report = evaluate(value)
        self.assertEqual(report["validation_status"], "REVIEW_REQUIRED")
        self.assertTrue(report["findings"])
        self.assertNotEqual(report["recommendation"], "READY_FOR_HUMAN_REVIEW")

    def test_03_terminal_punctuation_does_not_evade_overlap(self) -> None:
        value = assessment()
        value["observation"] = ["Synthetic measurement"]
        value["inference"] = ["Synthetic measurement."]
        ids = {item["finding_id"] for item in evaluate(value)["findings"]}
        self.assertIn("PI-INFERENCE-AS-OBSERVATION", ids)

    def test_04_dangling_evidence_reference_is_blocking(self) -> None:
        value = assessment()
        value["evidence_references"].append("SRC-DOES-NOT-EXIST")
        report = evaluate(value)
        finding = next(item for item in report["findings"] if item["finding_id"] == "PI-EVIDENCE-REFERENCE-UNRESOLVED")
        self.assertEqual(finding["severity"], "BLOCKING")
        self.assertEqual(report["recommendation"], "REQUIRE_CORROBORATION")

    def test_05_critical_irreversible_weak_evidence_holds(self) -> None:
        value = assessment()
        value["decision_context"]["consequence"] = "CRITICAL"
        value["decision_context"]["reversibility"] = "IRREVERSIBLE"
        value["evidence_state"]["strength"] = "WEAK"
        report = evaluate(value)
        finding = next(item for item in report["findings"] if item["finding_id"] == "PI-IRREVERSIBLE-WEAK-EVIDENCE")
        self.assertEqual(finding["severity"], "CRITICAL")
        self.assertEqual(report["recommendation"], "HOLD")

    def test_06_secret_fixture_marker_is_path_scoped(self) -> None:
        token = "AKIA" + "A" * 16
        with tempfile.TemporaryDirectory(prefix="fiw-secret-scope-") as temporary:
            root = Path(temporary)
            public = root / "README.md"
            public.write_text(f"{token} FIW_SECRET_FIXTURE\n", encoding="utf-8")
            tests = root / "tests"
            tests.mkdir()
            fixture = tests / "test_fixture.py"
            fixture.write_text(f"{token} FIW_SECRET_FIXTURE\n", encoding="utf-8")
            self.assertIn(token, secret_scan_text(public, root=root))
            self.assertNotIn(token, secret_scan_text(fixture, root=root))
            nested = root / "docs" / "tests"
            nested.mkdir(parents=True)
            nested_fixture = nested / "fixture.md"
            nested_fixture.write_text(f"{token} FIW_SECRET_FIXTURE\n", encoding="utf-8")
            self.assertIn(token, secret_scan_text(nested_fixture, root=root))

    def test_07_source_text_safety_rejects_bidi_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-unicode-") as temporary:
            path = Path(temporary) / "sample.py"
            path.write_text("# visible\u202ereordered\u202c\n", encoding="utf-8")
            findings = source_text_findings(path)
            self.assertTrue(findings)
            self.assertTrue(any("U+202E" in item for item in findings))

    def test_08_manifest_checksum_surface_is_scanned_as_text(self) -> None:
        self.assertIn(".sha256", TEXT_SUFFIXES)

    def test_08a_markdown_source_text_safety_rejects_bidi_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-unicode-md-") as temporary:
            path = Path(temporary) / "README.md"
            path.write_text("visible\u202ereordered\u202c\n", encoding="utf-8")
            findings = source_text_findings(path)
            self.assertTrue(findings)
            self.assertTrue(any("U+202E" in item for item in findings))

    def test_08aa_markdown_allows_legitimate_international_formatting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-unicode-md-intl-") as temporary:
            path = Path(temporary) / "README.md"
            family = "\U0001F468\u200d\U0001F469\u200d\U0001F467"
            persian = "\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645"
            path.write_text("\ufeffFamily " + family + " · Persian: " + persian + "\n", encoding="utf-8")
            self.assertEqual(source_text_findings(path), [])

    def test_08ab_code_still_rejects_invisible_formatting_with_remediation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-unicode-code-invisible-") as temporary:
            path = Path(temporary) / "sample.py"
            path.write_text("value = 'a\u200bb'\n", encoding="utf-8")
            findings = source_text_findings(path)
            self.assertTrue(findings)
            self.assertTrue(any("U+200B" in item for item in findings))
            self.assertTrue(any("remove or escape" in item for item in findings))

    def test_08ac_markdown_bidi_failure_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-unicode-md-help-") as temporary:
            path = Path(temporary) / "README.md"
            path.write_text("visible\u202ereordered\u202c\n", encoding="utf-8")
            findings = source_text_findings(path)
            self.assertTrue(any("spell out its Unicode code point" in item for item in findings))

    def test_08b_selected_provider_secret_patterns_are_present(self) -> None:
        for label in ("Private key material", "SendGrid API key", "Twilio API key", "Azure storage account key"):
            self.assertIn(label, SECRET_PATTERNS)

    def test_09_repository_checks_have_authoritative_status(self) -> None:
        report = validate(ROOT, check_manifest=True)
        self.assertTrue(report["passed"], report)
        for item in report["checks"]:
            self.assertIn(item["status"], {"PASS", "FAIL", "NOT_RUN"})
            self.assertEqual(item["passed"], item["status"] == "PASS")

    def test_10_missing_git_metadata_is_not_run_and_non_passing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-no-git-") as temporary:
            repo = Path(temporary) / "repo"
            shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            report = validate(repo, check_manifest=False)
            item = next(check for check in report["checks"] if check["name"] == "tracked_path_coverage")
            self.assertEqual(item["status"], "NOT_RUN")
            self.assertFalse(item["passed"])
            self.assertFalse(report["passed"])

    def test_11_refresh_metadata_runs_tests_before_manifest_write(self) -> None:
        text = (ROOT / "scripts" / "refresh_release_metadata.py").read_text(encoding="utf-8")
        self.assertIn("run_tests.py", text)
        self.assertIn("compile_sources.py", text)
        self.assertLess(text.index("run_pre_manifest_gate(root)"), text.index("write_manifests(root)"))

    def test_12_exact_release_marker_rejects_version_substring_spoof(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-version-spoof-") as temporary:
            repo = Path(temporary) / "repo"
            shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            readme = repo / "README.md"
            text = readme.read_text(encoding="utf-8").replace("**v0.5.1 — Decision-Ready Intelligence**", "**v10.5.01 — Decision-Ready Intelligence**")
            readme.write_text(text, encoding="utf-8", newline="\n")
            report = validate(repo, check_manifest=False)
            item = next(check for check in report["checks"] if check["name"] == "version_consistency")
            self.assertEqual(item["status"], "FAIL")

    def test_13_case_mismatched_markdown_link_is_rejected(self) -> None:
        import subprocess
        with tempfile.TemporaryDirectory(prefix="fiw-link-case-") as temporary:
            repo = Path(temporary) / "repo"
            shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            readme = repo / "README.md"
            text = readme.read_text(encoding="utf-8")
            self.assertIn("(LICENSE)", text)
            readme.write_text(text.replace("(LICENSE)", "(license)", 1), encoding="utf-8", newline="\n")
            report = validate(repo, check_manifest=False)
            item = next(check for check in report["checks"] if check["name"] == "markdown_links")
            self.assertEqual(item["status"], "FAIL")
            self.assertIn("case/normalization mismatch", item["detail"])

    def test_14_all_twelve_pi_controls_have_public_scenarios(self) -> None:
        text = (ROOT / "profiles" / "perception-integrity" / "CONTROL_EXAMPLES.md").read_text(encoding="utf-8")
        for number in range(1, 13):
            self.assertIn(f"PI-{number:02d}", text)

    def test_15_release_builder_check_flag_is_not_mandatory_ceremony(self) -> None:
        text = (ROOT / "scripts" / "build_release.py").read_text(encoding="utf-8")
        self.assertNotIn('action="store_true", required=True', text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
