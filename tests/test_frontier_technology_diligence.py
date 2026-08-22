#!/usr/bin/env python3
"""Regression tests for FIW-SYN-005 and the FIW Decision Record v0.5 contract."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "data" / "synthetic" / "FIW-SYN-005-frontier-technology-diligence.json"
EXAMPLE_README = ROOT / "examples" / "frontier-technology-diligence" / "README.md"
COMPLETED_RECORD = ROOT / "examples" / "frontier-technology-diligence" / "decision-record.md"
TEMPLATE = ROOT / "templates" / "decision-record.md"


class FrontierTechnologyDiligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = json.loads(CASE_PATH.read_text(encoding="utf-8"))

    def test_00_case_is_explicitly_synthetic(self) -> None:
        self.assertEqual(self.case["case_id"], "FIW-SYN-005")
        self.assertTrue(self.case["synthetic"])
        self.assertEqual(self.case["title"], "Frontier Technology Diligence")

    def test_01_derivative_reports_do_not_become_independent_corroboration(self) -> None:
        provenance = self.case["provenance"]
        reports = provenance["reports"]
        roots = {report["provenance_root"] for report in reports}
        self.assertEqual(len(reports), 3)
        self.assertEqual(provenance["apparent_report_count"], 3)
        self.assertEqual(provenance["independent_provenance_roots"], 1)
        self.assertEqual(roots, {"SRC-ROOT-01"})
        self.assertFalse(self.case["independent_corroboration_established"])
        self.assertTrue(all(not report["independent"] for report in reports))

    def test_02_decision_boundary_is_bounded(self) -> None:
        boundary = self.case["decision_boundary"]
        self.assertIn("commission_bounded_validation", boundary["currently_justified"])
        self.assertIn("hold_pending_evidence", boundary["currently_justified"])
        self.assertIn("investment_recommendation", boundary["not_authorized"])
        self.assertIn("capital_commitment", boundary["not_authorized"])
        self.assertTrue(self.case["human_disposition"]["requires_human_authority"])

    def test_03_next_evidence_is_material_and_nonempty(self) -> None:
        next_evidence = self.case["next_evidence"]
        self.assertGreaterEqual(len(next_evidence), 3)
        combined = " ".join(next_evidence).casefold()
        self.assertIn("independent", combined)
        self.assertIn("manufacturing", combined)

    def test_04_public_example_states_the_provenance_limit_and_investment_boundary(self) -> None:
        text = EXAMPLE_README.read_text(encoding="utf-8").casefold()
        self.assertIn("entirely fictional", text)
        self.assertIn("independent corroboration is not established", text)
        self.assertIn("does not recommend or execute an investment", text)

    def test_05_completed_record_preserves_unknowns_and_human_authority(self) -> None:
        text = COMPLETED_RECORD.read_text(encoding="utf-8").casefold()
        for phrase in (
            "## unknowns",
            "## assumptions",
            "## decision boundary",
            "## next evidence",
            "## human disposition",
            "independent corroboration is not established",
        ):
            self.assertIn(phrase, text)

    def test_06_decision_record_template_has_required_v05_sections(self) -> None:
        text = TEMPLATE.read_text(encoding="utf-8").casefold()
        for phrase in (
            "decision owner",
            "stakes / consequence of error",
            "reversibility",
            "evidence cutoff / review date",
            "## claims under review",
            "## evidence",
            "## provenance",
            "## challenges",
            "## knowns",
            "## unknowns",
            "## assumptions",
            "## assessment",
            "## decision boundary",
            "## next evidence",
            "## human disposition",
        ):
            self.assertIn(phrase, text)

    def test_07_readme_explains_three_customer_contexts_and_bounded_architecture(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8").casefold()
        for phrase in (
            "decision-ready intelligence",
            "capital allocators",
            "industry teams",
            "mission organizations",
            "frontier intelligence infrastructure",
            "materials-to-mission",
            "frontier decision engine",
            "accountable people retain consequential authority",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
