#!/usr/bin/env python3
"""Adversarial regression tests for FIW Source Genealogy."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from source_genealogy import evaluate_case  # noqa: E402


def source(
    source_id: str,
    *,
    relation: str = "ROOT",
    parent: str | None = None,
    temporal: str = "CURRENT",
    accessible: bool = True,
    cites: list[str] | None = None,
    coordination_group: str | None = None,
    superseded_by: str | None = None,
) -> dict:
    record = {
        "source_id": source_id,
        "relation": relation,
        "temporal_status": temporal,
        "accessible": accessible,
        "cites": list(cites or []),
    }
    if parent is not None:
        record["parent_source_id"] = parent
    if coordination_group is not None:
        record["coordination_group"] = coordination_group
    if superseded_by is not None:
        record["superseded_by"] = superseded_by
    return record


def case_for(sources: list[dict], source_ids: list[str], declared_count: int) -> dict:
    return {
        "metadata": {"case_id": "SG-SYN-001", "synthetic": True},
        "sources": sources,
        "claim": {
            "source_ids": source_ids,
            "declared_independent_source_count": declared_count,
        },
        "review_requirements": {
            "human_review_required": True,
            "decision_owner": "Synthetic Human Reviewer",
        },
        "public_boundary": {
            "contains_sensitive_data": False,
            "public_release_allowed": True,
        },
    }


def evaluate(case: dict) -> dict:
    raw = (json.dumps(case, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return evaluate_case(case, case_path="tests/synthetic-source-genealogy.json", case_bytes=raw)


class SourceGenealogyTests(unittest.TestCase):
    def test_five_urls_from_one_root_remain_one_root(self):
        sources = [
            source("ROOT-A"),
            source("MIRROR-A", relation="MIRROR", parent="ROOT-A"),
            source("TRANSLATION-A", relation="TRANSLATION", parent="ROOT-A"),
            source("SYNDICATED-A", relation="SYNDICATED", parent="ROOT-A"),
            source("DERIVATIVE-A", relation="DERIVATIVE", parent="ROOT-A"),
        ]
        result = evaluate(case_for(sources, [item["source_id"] for item in sources], 1))
        self.assertEqual(result["status"], "NO_FINDINGS")
        self.assertEqual(result["derived_provenance_roots"], ["ROOT-A"])
        self.assertEqual(result["derived_independent_source_count"], 1)

    def test_circular_citation_creates_no_extra_independence(self):
        sources = [
            source("ROOT-A", cites=["ROOT-B"]),
            source("ROOT-B", cites=["ROOT-A"]),
        ]
        result = evaluate(case_for(sources, ["ROOT-A", "ROOT-B"], 1))
        self.assertEqual(result["derived_independent_source_count"], 1)
        self.assertIn("SG-CIRCULAR-CITATION", {item["finding_id"] for item in result["findings"]})
        self.assertEqual(result["recommendation"], "REQUIRE_CORROBORATION")

    def test_translation_and_mirror_inherit_root(self):
        sources = [
            source("ROOT-A"),
            source("T-A", relation="TRANSLATION", parent="ROOT-A"),
            source("M-A", relation="MIRROR", parent="ROOT-A"),
        ]
        result = evaluate(case_for(sources, ["T-A", "M-A"], 1))
        states = {item["source_id"]: item for item in result["source_states"]}
        self.assertEqual(states["T-A"]["root_source_id"], "ROOT-A")
        self.assertEqual(states["M-A"]["root_source_id"], "ROOT-A")
        self.assertEqual(result["derived_independent_source_count"], 1)

    def test_ai_summary_cannot_create_new_provenance(self):
        sources = [
            source("ROOT-A"),
            source("AI-SUMMARY", relation="AI_DERIVATIVE", parent="ROOT-A"),
        ]
        result = evaluate(case_for(sources, ["ROOT-A", "AI-SUMMARY"], 1))
        self.assertEqual(result["derived_provenance_roots"], ["ROOT-A"])
        self.assertEqual(result["derived_independent_source_count"], 1)

    def test_coordinated_publications_collapse_to_one_independence_group(self):
        sources = [
            source("ROOT-A", coordination_group="CAMPAIGN-1"),
            source("ROOT-B", coordination_group="CAMPAIGN-1"),
            source("ROOT-C", coordination_group="CAMPAIGN-1"),
        ]
        result = evaluate(case_for(sources, ["ROOT-A", "ROOT-B", "ROOT-C"], 1))
        self.assertEqual(set(result["derived_provenance_roots"]), {"ROOT-A", "ROOT-B", "ROOT-C"})
        self.assertEqual(result["derived_independent_source_count"], 1)

    def test_retracted_and_superseded_support_remain_visible_but_degraded(self):
        sources = [
            source("OLD-A", temporal="SUPERSEDED", superseded_by="NEW-A"),
            source("NEW-A"),
            source("RETRACTED-B", temporal="RETRACTED"),
        ]
        result = evaluate(case_for(sources, ["OLD-A", "RETRACTED-B"], 0))
        ids = {item["finding_id"] for item in result["findings"]}
        self.assertIn("SG-SUPERSEDED-SUPPORT", ids)
        self.assertIn("SG-RETRACTED-SUPPORT", ids)
        self.assertEqual(result["derived_independent_source_count"], 0)
        self.assertEqual(set(result["derived_provenance_roots"]), {"OLD-A", "RETRACTED-B"})

    def test_unavailable_source_preserves_last_known_provenance_without_access_claim(self):
        unavailable = source("ROOT-A", temporal="UNAVAILABLE", accessible=False)
        unavailable["last_known_uri"] = "https://example.invalid/last-known-source"
        result = evaluate(case_for([unavailable], ["ROOT-A"], 0))
        self.assertEqual(result["derived_provenance_roots"], ["ROOT-A"])
        self.assertEqual(result["derived_independent_source_count"], 0)
        state = result["source_states"][0]
        self.assertIs(state["accessible"], False)
        self.assertIs(state["corroboration_eligible"], False)
        self.assertIn("SG-UNAVAILABLE-SUPPORT", {item["finding_id"] for item in result["findings"]})

    def test_url_multiplicity_cannot_overstate_independent_count(self):
        sources = [
            source("ROOT-A"),
            source("M1", relation="MIRROR", parent="ROOT-A"),
            source("M2", relation="MIRROR", parent="ROOT-A"),
            source("M3", relation="SYNDICATED", parent="ROOT-A"),
            source("M4", relation="TRANSLATION", parent="ROOT-A"),
        ]
        result = evaluate(case_for(sources, [item["source_id"] for item in sources], 5))
        self.assertEqual(result["derived_independent_source_count"], 1)
        self.assertIn("SG-INDEPENDENCE-OVERSTATED", {item["finding_id"] for item in result["findings"]})

    def test_unknown_lineage_cannot_be_counted_as_independent(self):
        result = evaluate(case_for([source("UNK", relation="UNKNOWN")], ["UNK"], 0))
        self.assertEqual(result["derived_independent_source_count"], 0)
        self.assertIn("SG-LINEAGE-UNKNOWN", {item["finding_id"] for item in result["findings"]})

    def test_parent_cycle_fails_closed(self):
        sources = [
            source("A", relation="DERIVATIVE", parent="B"),
            source("B", relation="DERIVATIVE", parent="A"),
        ]
        result = evaluate(case_for(sources, ["A", "B"], 0))
        self.assertIn("SG-DERIVATION-CYCLE", {item["finding_id"] for item in result["findings"]})
        self.assertEqual(result["derived_independent_source_count"], 0)

    def test_cli_result_contract(self):
        payload = case_for([source("ROOT-A")], ["ROOT-A"], 1)
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            case_path = temp_path / "case.json"
            output = temp_path / "result.json"
            case_path.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_source_genealogy.py"),
                    "--root",
                    str(ROOT),
                    "--case",
                    str(case_path),
                    "--json-output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["profile"], "SOURCE_GENEALOGY")
            self.assertEqual(result["profile_version"], "0.8.0")
            self.assertEqual(result["status"], "NO_FINDINGS")

    def test_result_is_deterministic_for_identical_bytes(self):
        payload = case_for([source("ROOT-A")], ["ROOT-A"], 1)
        raw = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
        first = evaluate_case(deepcopy(payload), case_path="x.json", case_bytes=raw)
        second = evaluate_case(deepcopy(payload), case_path="x.json", case_bytes=raw)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
