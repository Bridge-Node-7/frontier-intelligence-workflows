#!/usr/bin/env python3
"""Static contract and regression checks for the Frontier Claim Experience."""

from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIENCE = ROOT / "examples" / "frontier-claim-experience" / "index.html"
CANONICAL_ARTIFACT = ROOT / "data" / "synthetic" / "frontier-claim-experience.json"
POLICY = ROOT / "REPO_FILE_POLICY.json"


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


class FrontierClaimExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = EXPERIENCE.read_text(encoding="utf-8")
        cls.parser = _DocumentParser()
        cls.parser.feed(cls.html)
        match = re.search(
            r'<script id="fiw-case-artifact" type="application/json">\s*(.*?)\s*</script>',
            cls.html,
            re.DOTALL,
        )
        assert match is not None
        cls.artifact = json.loads(match.group(1))
        cls.canonical = json.loads(CANONICAL_ARTIFACT.read_text(encoding="utf-8"))

    def test_00_experience_is_single_file_local_first(self) -> None:
        self.assertTrue(EXPERIENCE.is_file())
        self.assertLess(EXPERIENCE.stat().st_size, 524_288)
        self.assertNotRegex(self.html, r"https?://")
        self.assertNotIn("fetch(", self.html)
        self.assertNotIn("XMLHttpRequest", self.html)
        self.assertNotIn("WebSocket", self.html)
        self.assertNotIn("sendBeacon", self.html)
        self.assertNotIn("localStorage", self.html)
        self.assertNotIn("sessionStorage", self.html)
        self.assertNotIn("indexedDB", self.html)
        self.assertNotIn("document.cookie", self.html)
        self.assertIn("connect-src 'none'", self.html)

    def test_01_accessibility_contract_is_present(self) -> None:
        self.assertIn('<html lang="en">', self.html)
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('id="case"', self.html)
        self.assertIn('role="status"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('@media (prefers-reduced-motion: reduce)', self.html)
        self.assertIn('@media (forced-colors: active)', self.html)
        self.assertIn('aria-labelledby="graph-title graph-desc"', self.html)
        self.assertIn('<fieldset>', self.html)
        self.assertIn('<legend>Decision state</legend>', self.html)
        self.assertIn('.decision-option input:focus-visible + span', self.html)
        self.assertIn('aria-controls="next-evidence"', self.html)

    def test_02_truth_and_human_authority_boundaries_are_explicit(self) -> None:
        required = (
            "A claim is not evidence. Evidence is not truth. Automation is not authority.",
            "The evidence can inform the decision. It cannot own it.",
            "No option is scored, rewarded, or treated as machine-certified truth.",
            "Human judgment is final.",
        )
        for phrase in required:
            self.assertIn(phrase, self.html)
        self.assertNotRegex(self.html.lower(), r"\b\d{1,3}%\s*(true|truth|confidence|risk)\b")
        self.assertNotIn("AI recommends", self.html)
        self.assertNotIn("reference_human_posture", self.html)
        self.assertNotIn("matches the reference human posture", self.html)

    def test_03_embedded_artifact_matches_canonical_repository_artifact(self) -> None:
        self.assertEqual(self.artifact, self.canonical)
        self.assertEqual(self.artifact["case_id"], "FIW-FCE-SYN-001")
        self.assertTrue(self.artifact["synthetic"])
        self.assertTrue(self.artifact["public_safe"])

    def test_04_signature_lineage_case_is_exact_and_bounded(self) -> None:
        self.assertEqual(self.artifact["lineage_result"]["cited_reports"], 3)
        self.assertEqual(self.artifact["lineage_result"]["provenance_roots"], 1)
        self.assertEqual(self.artifact["lineage_result"]["independent_corroboration"], "NOT_ESTABLISHED")

    def test_05_lineage_summary_is_consistent_with_source_graph(self) -> None:
        sources = self.artifact["sources"]
        roots = [item for item in sources if item["parent_id"] is None]
        reports = [item for item in sources if item["parent_id"] is not None]
        self.assertEqual(len(roots), self.artifact["lineage_result"]["provenance_roots"])
        self.assertEqual(len(reports), self.artifact["lineage_result"]["cited_reports"])
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["id"], "ROOT-1")
        source_ids = {item["id"] for item in sources}
        for item in reports:
            self.assertIn(item["parent_id"], source_ids)

    def test_06_unknown_and_next_evidence_are_actionable_not_certifying(self) -> None:
        self.assertEqual(self.artifact["critical_unknown"]["type"], "MISSING_EVIDENCE")
        self.assertTrue(self.artifact["critical_unknown"]["currently_resolvable"])
        self.assertIn("Independent lot-level qualification evidence", self.artifact["next_evidence"]["text"])
        self.assertEqual(
            self.artifact["next_evidence"]["why"],
            ["decision relevance", "discrimination ability", "reversibility", "decision-state impact"],
        )
        self.assertIn("does not certify truth", self.artifact["truth_boundary"])

    def test_07_visible_decision_states_are_scoped(self) -> None:
        values = {
            attrs.get("value")
            for tag, attrs in self.parser.tags
            if tag == "input" and attrs.get("name") == "decision"
        }
        self.assertEqual(values, {"PROCEED_WITHIN_SCOPE", "HOLD", "DO_NOT_PROCEED", "UNKNOWN"})
        self.assertNotIn('value="PASS"', self.html)
        self.assertNotIn('value="FAIL"', self.html)

    def test_08_policy_expansion_is_narrow(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        allowed = set(policy["allowed_path_globs"])
        self.assertIn("examples/frontier-claim-experience/index.html", allowed)
        self.assertIn("data/synthetic/frontier-claim-experience.json", allowed)
        self.assertNotIn("examples/**/*.html", allowed)
        self.assertNotIn("data/synthetic/*.json", allowed)
        self.assertFalse(policy["binary_files_allowed"])
        self.assertFalse(policy["nested_archives_allowed"])

    def test_09_html_has_no_remote_asset_attributes(self) -> None:
        for tag, attrs in self.parser.tags:
            for name in ("src", "href", "action"):
                value = attrs.get(name)
                if value is None or value.startswith("#"):
                    continue
                self.assertFalse(value.startswith(("http://", "https://", "//")), (tag, name, value))

    def test_10_lineage_revelation_is_progressive_for_visual_and_screen_reader_users(self) -> None:
        self.assertIn('id="lineage-relations" aria-label="Source relationships" hidden', self.html)
        self.assertIn(
            'Three cited reports support one claim. Trace origins to inspect whether the reports are independent.',
            self.html,
        )
        self.assertIn("$('lineage-relations').hidden = false;", self.html)
        self.assertIn("$('lineage-relations').hidden = true;", self.html)
        self.assertIn("$('graph-desc').textContent = 'Three cited reports resolve to one supplier-origin provenance root. Independent corroboration is not established.';", self.html)

    def test_11_root_reveal_and_controls_do_not_spoil_or_cover_the_lineage_result(self) -> None:
        self.assertIn('.root-node { opacity: 0;', self.html)
        self.assertIn('.traced .root-node { opacity: 1; }', self.html)
        self.assertIn('.graph-actions { position: absolute; left: 1rem; right: 1rem; top: 1rem; bottom: auto;', self.html)

    def test_12_human_decision_is_never_compared_with_a_preencoded_correct_answer(self) -> None:
        self.assertNotIn("reference_human_posture", self.artifact)
        self.assertIn(
            "Decision recorded. FIW does not score, reward, or certify the selected state.",
            self.html,
        )

    def test_13_case_preserves_reassessment_not_silent_rewrite(self) -> None:
        self.assertIn(
            "New evidence would create a reassessment; it would not silently rewrite this decision state.",
            self.html,
        )

    def test_14_mobile_uses_structured_lineage_summary_instead_of_tiny_graph(self) -> None:
        self.assertIn('class="mobile-lineage-map"', self.html)
        self.assertIn('.graph-card svg { display: none; }', self.html)
        self.assertIn("$('mobile-lineage-title').textContent = 'Lineage traced';", self.html)
        self.assertIn("$('mobile-lineage-detail').textContent = 'Source relationships revealed below';", self.html)

    def test_15_decision_validation_is_visible_and_accessible(self) -> None:
        self.assertIn('id="decision-error" class="validation-message" role="alert" hidden', self.html)
        self.assertIn("showDecisionError", self.html)

    def test_16_programmatic_scroll_respects_reduced_motion(self) -> None:
        self.assertIn("window.matchMedia('(prefers-reduced-motion: reduce)').matches", self.html)

    def test_17_product_promise_is_aligned_with_repository_positioning(self) -> None:
        self.assertIn(
            "Turn uncertain frontier-technology claims into decision-ready intelligence.",
            self.html,
        )
        self.assertIn("Follow the provenance.", self.html)

    def test_18_signature_provenance_reveal_is_explicit_and_progressive(self) -> None:
        self.assertIn('id="lineage-equation" hidden', self.html)
        self.assertIn("3 cited reports", self.html)
        self.assertIn("3 independent confirmations", self.html)
        self.assertIn("$('lineage-equation').hidden = false;", self.html)
        self.assertIn("$('lineage-equation').hidden = true;", self.html)

    def test_19_decision_boundary_and_receipt_are_visually_explicit(self) -> None:
        for phrase in (
            "04 · Decision Boundary",
            "Supported by the Record",
            "Not Established",
            "Critical Unknown",
            "Evidence That Could Change the State",
            "FIW Decision Record · Synthetic Session",
            "Decision Receipt",
            "Evidence cutoff",
            "Decision boundary",
        ):
            self.assertIn(phrase, self.html)

    def test_20_commercial_bridge_is_informational_and_offline(self) -> None:
        self.assertIn("Bring a consequential technology question.", self.html)
        self.assertIn("BridgeNode7.com", self.html)
        self.assertNotRegex(self.html, r"https?://")


if __name__ == "__main__":
    unittest.main()
