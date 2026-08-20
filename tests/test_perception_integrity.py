#!/usr/bin/env python3
"""Unit tests for the deterministic Perception Integrity rules module."""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from perception_integrity import (  # noqa: E402
    CONTROL_FINDINGS,
    canonical_json_bytes,
    evaluate_assessment,
    sha256_bytes,
    validate_schema_instance,
)
from validate_repo import validate_perception_integrity_profile  # noqa: E402

EVALUATED_AT = "2026-08-08T03:30:00Z"
ASSESSMENT_PATH = "profiles/perception-integrity/fixtures/valid/base.json"


def base_assessment() -> dict:
    return {
        "metadata": {
            "assessment_id": "PIA-FIW-SYN-TEST",
            "case_id": "FIW-SYN-TEST",
            "synthetic": True,
        },
        "subject": {"title": "Synthetic readiness claim"},
        "decision_context": {
            "consequence": "MODERATE",
            "reversibility": "REVERSIBLE",
        },
        "claim_reference": {
            "claim_id": "CLM-FIW-SYN-TEST",
            "claim_mode": "REPORTED_CLAIM",
        },
        "evidence_references": ["SRC-PRIMARY-1", "SRC-PRIMARY-2"],
        "claim_mode": "REPORTED_CLAIM",
        "source_lineage": [
            {
                "source_id": "SRC-PRIMARY-1",
                "relationship": "PRIMARY",
                "parent_id": None,
            },
            {
                "source_id": "SRC-PRIMARY-2",
                "relationship": "PRIMARY",
                "parent_id": None,
            },
        ],
        "observation": ["The supplied record contains a declared measurement."],
        "inference": ["The measurement may support a bounded readiness review."],
        "assumptions": ["The synthetic record is internally complete."],
        "alternative_hypotheses": ["The measurement may reflect a benign artifact."],
        "salience": "MEDIUM",
        "evidence_state": {
            "strength": "STRONG",
            "expires_at": "2026-12-31T23:59:59Z",
        },
        "decision_conditions": {
            "stop_conditions": ["Stop if source identity cannot be verified."],
        },
        "review_requirements": {
            "human_review_required": True,
            "decision_owner": "Synthetic Review Board",
        },
        "public_boundary": {
            "contains_sensitive_data": False,
            "public_release_allowed": True,
        },
    }


def evaluate(value: dict) -> dict:
    data = canonical_json_bytes(value)
    return evaluate_assessment(
        value,
        assessment_path=ASSESSMENT_PATH,
        assessment_bytes=data,
        evaluated_at=EVALUATED_AT,
    )


def finding_ids(report: dict) -> set[str]:
    return {item["finding_id"] for item in report["findings"]}


class PerceptionIntegrityTests(unittest.TestCase):
    def test_00_contract_contains_twelve_controls(self) -> None:
        self.assertEqual(set(CONTROL_FINDINGS), {f"PI-{n:02d}" for n in range(1, 13)})

    def test_01_clean_record_is_ready_for_human_review(self) -> None:
        report = evaluate(base_assessment())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["recommendation"], "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["validation_status"], "PASS")
        self.assertTrue(report["human_decision_required"])

    def test_02_claim_mode_mismatch(self) -> None:
        value = base_assessment()
        value["claim_reference"]["claim_mode"] = "INFERENCE"
        self.assertIn("PI-CLAIM-MODE-MISMATCH", finding_ids(evaluate(value)))

    def test_03_observation_inference_overlap(self) -> None:
        value = base_assessment()
        value["inference"] = [value["observation"][0]]
        self.assertIn("PI-INFERENCE-AS-OBSERVATION", finding_ids(evaluate(value)))

    def test_04_unresolved_lineage_cycle(self) -> None:
        value = base_assessment()
        value["source_lineage"] = [
            {"source_id": "A", "relationship": "SUMMARY", "parent_id": "B"},
            {"source_id": "B", "relationship": "SUMMARY", "parent_id": "A"},
        ]
        self.assertIn("PI-SOURCE-LINEAGE-UNRESOLVED", finding_ids(evaluate(value)))

    def test_05_derivative_corroboration(self) -> None:
        value = base_assessment()
        value["salience"] = "HIGH"
        value["source_lineage"] = [
            {"source_id": "A", "relationship": "PRIMARY", "parent_id": None},
            {"source_id": "B", "relationship": "SUMMARY", "parent_id": "A"},
        ]
        report = evaluate(value)
        self.assertIn("PI-DERIVATIVE-CORROBORATION", finding_ids(report))
        self.assertEqual(report["recommendation"], "REQUIRE_CORROBORATION")

    def test_06_material_assumption_missing(self) -> None:
        value = base_assessment()
        value["decision_context"]["consequence"] = "MAJOR"
        value["assumptions"] = []
        self.assertIn("PI-MATERIAL-ASSUMPTION-MISSING", finding_ids(evaluate(value)))

    def test_07_alternative_hypothesis_missing(self) -> None:
        value = base_assessment()
        value["claim_mode"] = "INFERENCE"
        value["claim_reference"]["claim_mode"] = "INFERENCE"
        value["alternative_hypotheses"] = []
        self.assertIn("PI-ALTERNATIVE-HYPOTHESIS-MISSING", finding_ids(evaluate(value)))

    def test_08_salience_evidence_mismatch(self) -> None:
        value = base_assessment()
        value["salience"] = "HIGH"
        value["evidence_state"]["strength"] = "WEAK"
        self.assertIn("PI-SALIENCE-EVIDENCE-MISMATCH", finding_ids(evaluate(value)))

    def test_09_expired_evidence(self) -> None:
        value = base_assessment()
        value["evidence_state"]["expires_at"] = "2026-08-08T03:29:59Z"
        report = evaluate(value)
        self.assertIn("PI-EVIDENCE-EXPIRED", finding_ids(report))
        self.assertEqual(report["recommendation"], "REASSESS_BEFORE_ACTION")

    def test_10_irreversible_weak_evidence(self) -> None:
        value = base_assessment()
        value["decision_context"]["reversibility"] = "IRREVERSIBLE"
        value["evidence_state"]["strength"] = "WEAK"
        report = evaluate(value)
        self.assertIn("PI-IRREVERSIBLE-WEAK-EVIDENCE", finding_ids(report))
        self.assertEqual(report["recommendation"], "ESCALATE_FOR_HUMAN_REVIEW")

    def test_11_human_review_and_owner_missing(self) -> None:
        value = base_assessment()
        value["review_requirements"] = {
            "human_review_required": False,
            "decision_owner": "",
        }
        ids = finding_ids(evaluate(value))
        self.assertIn("PI-HUMAN-REVIEW-MISSING", ids)
        self.assertIn("PI-DECISION-OWNER-MISSING", ids)

    def test_12_stop_condition_missing(self) -> None:
        value = base_assessment()
        value["decision_conditions"]["stop_conditions"] = []
        self.assertIn("PI-STOP-CONDITION-MISSING", finding_ids(evaluate(value)))

    def test_13_public_boundary_cannot_be_overridden(self) -> None:
        value = base_assessment()
        value["public_boundary"] = {
            "contains_sensitive_data": True,
            "public_release_allowed": True,
            "authorized_exceptions": ["Synthetic override attempt"],
        }
        report = evaluate(value)
        self.assertIn("PI-PUBLIC-BOUNDARY-VIOLATION", finding_ids(report))
        self.assertEqual(report["recommendation"], "DO_NOT_RELEASE_PUBLICLY")

    def test_14_deterministic_output_and_finding_order(self) -> None:
        value = base_assessment()
        value["review_requirements"] = {
            "human_review_required": False,
            "decision_owner": "",
        }
        value["decision_conditions"]["stop_conditions"] = []
        first = evaluate(value)
        second = evaluate(copy.deepcopy(value))
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        order = [item["finding_id"] for item in first["findings"]]
        self.assertEqual(order, sorted(order))

    def test_15_explicit_time_is_required(self) -> None:
        value = base_assessment()
        with self.assertRaises(ValueError):
            evaluate_assessment(
                value,
                assessment_path=ASSESSMENT_PATH,
                assessment_bytes=json.dumps(value).encode("utf-8"),
                evaluated_at="2026-08-08",
            )

    def test_16_repository_relative_path_is_required(self) -> None:
        value = base_assessment()
        with self.assertRaises(ValueError):
            evaluate_assessment(
                value,
                assessment_path="../outside.json",
                assessment_bytes=canonical_json_bytes(value),
                evaluated_at=EVALUATED_AT,
            )


    def test_17_validator_integration_is_dormant_without_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-pi-absent-") as temporary:
            passed, detail = validate_perception_integrity_profile(Path(temporary))
        self.assertTrue(passed, detail)
        self.assertIn("not present yet", detail)

    def test_18_partial_profile_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-pi-partial-") as temporary:
            profile = Path(temporary) / "profiles" / "perception-integrity"
            profile.mkdir(parents=True)
            passed, detail = validate_perception_integrity_profile(Path(temporary))
        self.assertFalse(passed)
        self.assertIn("incomplete", detail)

    def test_19_complete_profile_chain_passes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-pi-complete-") as temporary:
            root = Path(temporary)
            profile = root / "profiles" / "perception-integrity"
            (profile / "schema").mkdir(parents=True)
            (profile / "README.md").write_text(
                "# Perception Integrity\n\n"
                "This profile does not determine truth; a human owns every decision.\n\n"
                "Use run_perception_integrity.py to evaluate an assessment and "
                "refresh_release_metadata.py after changes.\n",
                encoding="utf-8",
                newline="\n",
            )
            for name in (
                "perception-integrity-assessment.schema.json",
                "perception-integrity-validation.schema.json",
                "perception-integrity-review.schema.json",
            ):
                schema = {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$id": f"https://example.invalid/{name}",
                    "type": "object",
                }
                (profile / "schema" / name).write_bytes(canonical_json_bytes(schema))

            cases = {
                "FIW-SYN-002": "REQUIRE_CORROBORATION",
                "FIW-SYN-003": "ESCALATE_FOR_HUMAN_REVIEW",
                "FIW-SYN-004": "REQUEST_ADDITIONAL_EVIDENCE",
            }
            for case_id, recommendation in cases.items():
                value = base_assessment()
                value["metadata"]["assessment_id"] = f"PIA-{case_id}"
                value["metadata"]["case_id"] = case_id
                if case_id == "FIW-SYN-002":
                    value["salience"] = "HIGH"
                    value["source_lineage"] = [
                        {"source_id": "A", "relationship": "PRIMARY", "parent_id": None},
                        {"source_id": "B", "relationship": "SUMMARY", "parent_id": "A"},
                    ]
                elif case_id == "FIW-SYN-003":
                    value["decision_context"]["reversibility"] = "IRREVERSIBLE"
                    value["evidence_state"]["strength"] = "WEAK"
                else:
                    value["decision_conditions"]["stop_conditions"] = []

                case_dir = profile / "examples" / case_id
                case_dir.mkdir(parents=True)
                base = case_dir / f"PIA-{case_id}"
                assessment_path = base.with_suffix(".json")
                validation_path = base.with_suffix(".validation.json")
                review_path = base.with_suffix(".review.json")
                markdown_path = base.with_suffix(".review.md")
                assessment_bytes = canonical_json_bytes(value)
                assessment_path.write_bytes(assessment_bytes)
                relative = assessment_path.relative_to(root).as_posix()
                validation = evaluate_assessment(
                    value,
                    assessment_path=relative,
                    assessment_bytes=assessment_bytes,
                    evaluated_at=EVALUATED_AT,
                )
                self.assertEqual(recommendation, validation["recommendation"])
                validation_bytes = canonical_json_bytes(validation)
                validation_path.write_bytes(validation_bytes)
                assessment_sha = sha256_bytes(assessment_bytes)
                validation_sha = sha256_bytes(validation_bytes)
                review = {
                    "assessment_sha256": assessment_sha,
                    "validation_sha256": validation_sha,
                    "reviewer_record": "Synthetic Human Reviewer",
                    "review_time": EVALUATED_AT,
                    "review_basis": ["Deterministic synthetic fixture"],
                    "accepted_findings": [],
                    "rejected_findings": [],
                    "authorized_exceptions": [],
                    "unresolved_questions": [],
                    "human_disposition": "HOLD_FOR_REVIEW",
                    "rationale": "Synthetic validation only.",
                    "stop_condition": "Stop if any digest changes.",
                    "next_review_trigger": "New evidence or changed bytes.",
                    "public_release_decision": "SYNTHETIC_DEMONSTRATION_ONLY",
                }
                review_path.write_bytes(canonical_json_bytes(review))
                markdown_path.write_text(
                    f"# {case_id} Human Review\n\n"
                    f"Assessment SHA-256: `{assessment_sha}`\n\n"
                    f"Validation SHA-256: `{validation_sha}`\n",
                    encoding="utf-8",
                    newline="\n",
                )

            passed, detail = validate_perception_integrity_profile(root)
        self.assertTrue(passed, detail)

    def test_20_repository_profile_passes(self) -> None:
        passed, detail = validate_perception_integrity_profile(ROOT)
        self.assertTrue(passed, detail)

    def test_21_schema_contracts_are_strict(self) -> None:
        schema_root = ROOT / "profiles" / "perception-integrity" / "schema"
        for path in sorted(schema_root.glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                "https://json-schema.org/draft/2020-12/schema",
                schema["$schema"],
            )
            self.assertTrue(schema["$id"].startswith("urn:bridgenode7:fiw:"))
            self.assertFalse(schema["additionalProperties"])
            self.assertGreater(len(schema["required"]), 0)
        self.assertEqual(3, len(list(schema_root.glob("*.schema.json"))))

    def test_22_repository_example_recommendations_are_exact(self) -> None:
        expected = {
            "FIW-SYN-002": "REQUIRE_CORROBORATION",
            "FIW-SYN-003": "ESCALATE_FOR_HUMAN_REVIEW",
            "FIW-SYN-004": "REQUEST_ADDITIONAL_EVIDENCE",
        }
        profile = ROOT / "profiles" / "perception-integrity" / "examples"
        for case_id, recommendation in expected.items():
            base = profile / case_id / f"PIA-{case_id}"
            validation = json.loads(
                base.with_suffix(".validation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(recommendation, validation["recommendation"])
            self.assertTrue(validation["human_decision_required"])

    def test_23_repository_review_digests_match(self) -> None:
        profile = ROOT / "profiles" / "perception-integrity" / "examples"
        for case_id in ("FIW-SYN-002", "FIW-SYN-003", "FIW-SYN-004"):
            base = profile / case_id / f"PIA-{case_id}"
            assessment_bytes = base.with_suffix(".json").read_bytes()
            validation_bytes = base.with_suffix(".validation.json").read_bytes()
            review = json.loads(base.with_suffix(".review.json").read_text(encoding="utf-8"))
            markdown = base.with_suffix(".review.md").read_text(encoding="utf-8")
            assessment_sha = sha256_bytes(assessment_bytes)
            validation_sha = sha256_bytes(validation_bytes)
            self.assertEqual(assessment_sha, review["assessment_sha256"])
            self.assertEqual(validation_sha, review["validation_sha256"])
            self.assertIn(case_id, markdown)
            self.assertIn(assessment_sha, markdown)
            self.assertIn(validation_sha, markdown)


    def test_24_repository_examples_match_runtime_schemas(self) -> None:
        schema_root = ROOT / "profiles" / "perception-integrity" / "schema"
        schemas = {
            "assessment": json.loads((schema_root / "perception-integrity-assessment.schema.json").read_text(encoding="utf-8")),
            "validation": json.loads((schema_root / "perception-integrity-validation.schema.json").read_text(encoding="utf-8")),
            "review": json.loads((schema_root / "perception-integrity-review.schema.json").read_text(encoding="utf-8")),
        }
        example_root = ROOT / "profiles" / "perception-integrity" / "examples"
        for case_id in ("FIW-SYN-002", "FIW-SYN-003", "FIW-SYN-004"):
            base = example_root / case_id / f"PIA-{case_id}"
            instances = {
                "assessment": json.loads(base.with_suffix(".json").read_text(encoding="utf-8")),
                "validation": json.loads(base.with_suffix(".validation.json").read_text(encoding="utf-8")),
                "review": json.loads(base.with_suffix(".review.json").read_text(encoding="utf-8")),
            }
            for name, instance in instances.items():
                self.assertEqual([], validate_schema_instance(instance, schemas[name]), f"{case_id} {name}")

    def test_25_valid_fixture_passes_schema_and_runtime(self) -> None:
        profile = ROOT / "profiles" / "perception-integrity"
        schema = json.loads((profile / "schema" / "perception-integrity-assessment.schema.json").read_text(encoding="utf-8"))
        path = profile / "fixtures" / "valid" / "assessment-ready.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([], validate_schema_instance(value, schema))
        result = evaluate_assessment(
            value,
            assessment_path=path.relative_to(ROOT).as_posix(),
            assessment_bytes=path.read_bytes(),
            evaluated_at=EVALUATED_AT,
        )
        self.assertEqual("READY_FOR_HUMAN_REVIEW", result["recommendation"])
        self.assertEqual([], result["findings"])

    def test_26_missing_required_owner_fixture_fails_schema(self) -> None:
        profile = ROOT / "profiles" / "perception-integrity"
        schema = json.loads((profile / "schema" / "perception-integrity-assessment.schema.json").read_text(encoding="utf-8"))
        value = json.loads((profile / "fixtures" / "invalid" / "missing-decision-owner.json").read_text(encoding="utf-8"))
        issues = validate_schema_instance(value, schema)
        self.assertTrue(any("decision_owner" in issue for issue in issues), issues)

    def test_27_unknown_property_fixture_fails_schema(self) -> None:
        profile = ROOT / "profiles" / "perception-integrity"
        schema = json.loads((profile / "schema" / "perception-integrity-assessment.schema.json").read_text(encoding="utf-8"))
        value = json.loads((profile / "fixtures" / "invalid" / "unknown-top-level-field.json").read_text(encoding="utf-8"))
        issues = validate_schema_instance(value, schema)
        self.assertTrue(any("additional property 'unexpected'" in issue for issue in issues), issues)

    def test_28_invalid_enum_fixture_fails_schema(self) -> None:
        profile = ROOT / "profiles" / "perception-integrity"
        schema = json.loads((profile / "schema" / "perception-integrity-assessment.schema.json").read_text(encoding="utf-8"))
        value = json.loads((profile / "fixtures" / "invalid" / "invalid-claim-mode.json").read_text(encoding="utf-8"))
        issues = validate_schema_instance(value, schema)
        self.assertGreaterEqual(sum("outside enum" in issue for issue in issues), 2)

    def test_29_unresolved_lineage_fixture_is_schema_valid_but_blocked(self) -> None:
        profile = ROOT / "profiles" / "perception-integrity"
        schema = json.loads((profile / "schema" / "perception-integrity-assessment.schema.json").read_text(encoding="utf-8"))
        path = profile / "fixtures" / "invalid" / "unresolved-lineage.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([], validate_schema_instance(value, schema))
        result = evaluate_assessment(value, assessment_path=path.relative_to(ROOT).as_posix(), assessment_bytes=path.read_bytes(), evaluated_at=EVALUATED_AT)
        self.assertIn("PI-SOURCE-LINEAGE-UNRESOLVED", {item["finding_id"] for item in result["findings"]})
        self.assertEqual("REQUIRE_CORROBORATION", result["recommendation"])

    def test_30_public_boundary_non_override_is_critical(self) -> None:
        profile = ROOT / "profiles" / "perception-integrity"
        schema = json.loads((profile / "schema" / "perception-integrity-assessment.schema.json").read_text(encoding="utf-8"))
        path = profile / "fixtures" / "invalid" / "sensitive-public-release.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([], validate_schema_instance(value, schema))
        result = evaluate_assessment(value, assessment_path=path.relative_to(ROOT).as_posix(), assessment_bytes=path.read_bytes(), evaluated_at=EVALUATED_AT)
        finding = next(item for item in result["findings"] if item["finding_id"] == "PI-PUBLIC-BOUNDARY-VIOLATION")
        self.assertEqual("CRITICAL", finding["severity"])
        self.assertEqual("DO_NOT_RELEASE_PUBLICLY", result["recommendation"])

    def test_31_tampered_assessment_fails_profile_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-pi-tamper-assessment-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "profiles", root / "profiles")
            base = root / "profiles" / "perception-integrity" / "examples" / "FIW-SYN-002" / "PIA-FIW-SYN-002.json"
            value = json.loads(base.read_text(encoding="utf-8"))
            value["subject"]["title"] = "Tampered synthetic title"
            base.write_bytes(canonical_json_bytes(value))
            passed, detail = validate_perception_integrity_profile(root)
        self.assertFalse(passed)
        self.assertTrue("validation JSON does not match" in detail or "digest mismatch" in detail, detail)

    def test_32_tampered_review_digest_fails_profile_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fiw-pi-tamper-review-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "profiles", root / "profiles")
            base = root / "profiles" / "perception-integrity" / "examples" / "FIW-SYN-003" / "PIA-FIW-SYN-003.review.json"
            value = json.loads(base.read_text(encoding="utf-8"))
            value["validation_sha256"] = "0" * 64
            base.write_bytes(canonical_json_bytes(value))
            passed, detail = validate_perception_integrity_profile(root)
        self.assertFalse(passed)
        self.assertIn("review validation digest mismatch", detail)

    def test_33_schema_issue_order_is_deterministic(self) -> None:
        profile = ROOT / "profiles" / "perception-integrity"
        schema = json.loads((profile / "schema" / "perception-integrity-assessment.schema.json").read_text(encoding="utf-8"))
        value = json.loads((profile / "fixtures" / "invalid" / "unknown-top-level-field.json").read_text(encoding="utf-8"))
        first = validate_schema_instance(value, schema)
        second = validate_schema_instance(value, schema)
        self.assertEqual(first, second)
        self.assertEqual(sorted(set(first)), first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
