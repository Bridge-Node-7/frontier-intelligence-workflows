#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from radiant_guardian import evaluate_case, structural_issues  # noqa: E402

CASE_PATH = ROOT / "profiles/radiant-guardian/fixtures/valid/assessment-ready.json"


def load_case():
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


def evaluate(case):
    raw=(json.dumps(case,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
    return evaluate_case(case, root=ROOT, case_path="work/case.json", case_bytes=raw, evaluated_at="2026-09-01T23:59:00Z")


class RadiantGuardianTests(unittest.TestCase):
    def ids(self, report):
        return {x["finding_id"] for x in report["findings"]}

    def test_01_valid_synthetic_has_no_findings(self):
        report=evaluate(load_case())
        self.assertEqual(report["validation_status"], "NO_RG_FINDINGS")
        self.assertEqual(report["recommendation"], "READY_FOR_HUMAN_REVIEW")
        self.assertTrue(report["human_decision_required"])

    def test_02_signal_claim_collapse(self):
        c=load_case(); c["signal"]["asserted_as_fact"]=True
        self.assertIn("RG-SIGNAL-CLAIM-COLLAPSE", self.ids(evaluate(c)))

    def test_03_independence_overstated(self):
        c=load_case(); c["genealogy"]["declared_independent_root_count"]=3
        self.assertIn("RG-INDEPENDENCE-OVERSTATED", self.ids(evaluate(c)))

    def test_04_anchor_extension_requires_bridge(self):
        c=load_case(); c["reasoning_patterns"]=[{"pattern":"REAL_ANCHOR_EXTRAORDINARY_EXTENSION","claim_reference":"X","rationale":"x","bridge_evidence_references":[],"discriminating_test_ids":["SYN-TEST-01"]}]
        self.assertIn("RG-ANCHOR-EXTENSION-BRIDGE-MISSING", self.ids(evaluate(c)))

    def test_05_self_sealing_requires_test(self):
        c=load_case(); c["reasoning_patterns"]=[{"pattern":"SELF_SEALING_RISK","claim_reference":"X","rationale":"x","bridge_evidence_references":[],"discriminating_test_ids":[]}]
        self.assertIn("RG-SELF-SEALING-WITHOUT-DISCRIMINATOR", self.ids(evaluate(c)))

    def test_06_prediction_freeze_chronology(self):
        c=load_case(); c["predictions"][0]["frozen_at"]="2028-01-01T00:00:00Z"
        self.assertIn("RG-PREDICTION-NOT-FROZEN", self.ids(evaluate(c)))

    def test_07_prediction_resolution_complete(self):
        c=load_case(); c["predictions"][0]["ambiguous_criteria"]=[]
        self.assertIn("RG-PREDICTION-RESOLUTION-INCOMPLETE", self.ids(evaluate(c)))

    def test_08_discriminating_test_complete(self):
        c=load_case(); c["tests"][0]["hypothesis_ids"]=["SYN-H1"]
        self.assertIn("RG-DISCRIMINATING-TEST-INCOMPLETE", self.ids(evaluate(c)))

    def test_09_generated_hypothesis_not_promoted(self):
        c=load_case(); c["hypotheses"][2]["evidence_weight"]="EVIDENCE_LINKED"
        self.assertIn("RG-GENERATED-HYPOTHESIS-PROMOTED", self.ids(evaluate(c)))

    def test_10_update_receipt_complete(self):
        c=load_case(); c["update_receipts"]=[{"receipt_id":"R1","previous_state":"A","new_state":"B","evidence_delta":[],"rationale":"x","reviewer":"h","updated_at":"2026-09-01T22:00:00Z","reversal_trigger":"x"}]
        self.assertIn("RG-UPDATE-RECEIPT-INCOMPLETE", self.ids(evaluate(c)))

    def test_11_upstream_pi_unresolved(self):
        c=load_case(); c["pi_reference"]["validation_sha256"]="0"*64
        self.assertIn("RG-UPSTREAM-PI-UNRESOLVED", self.ids(evaluate(c)))

    def test_12_public_boundary_propagates(self):
        c=load_case()
        original=Path(ROOT/c["pi_reference"]["validation_path"])
        pi=json.loads(original.read_text())
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"pi.json"; pi["recommendation"]="DO_NOT_RELEASE_PUBLICLY"; pi["validation_status"]="REVIEW_REQUIRED"; p.write_text(json.dumps(pi,sort_keys=True,separators=(",",":"))+"\n")
            # Put a temporary file inside root because resolution is fail-closed to the repo.
            q=ROOT/"profiles/radiant-guardian/fixtures/valid/_temp_pi.json"
            try:
                q.write_bytes(p.read_bytes())
                import hashlib
                c["pi_reference"]["validation_path"]=q.relative_to(ROOT).as_posix(); c["pi_reference"]["validation_sha256"]=hashlib.sha256(q.read_bytes()).hexdigest()
                self.assertIn("RG-PUBLIC-BOUNDARY-VIOLATION", self.ids(evaluate(c)))
            finally:
                q.unlink(missing_ok=True)

    def test_13_proof_loop_requires_reassessment_and_learning(self):
        c=load_case(); c["proof_loop"]={"active":True,"decision_reference":"D1","action_reference":"A1","outcome_state":"OBSERVED","learning_recorded":False,"reassessment_trigger":None}
        self.assertIn("RG-PROOF-LOOP-INCOMPLETE", self.ids(evaluate(c)))

    def test_14_structural_rejects_unknown_top_level(self):
        c=load_case(); c["unknown_field"]=1
        self.assertTrue(structural_issues(c))

    def test_15_rg_syn_001_is_expected_review_case(self):
        p=ROOT/"profiles/radiant-guardian/examples/RG-SYN-001/case.json"; c=json.loads(p.read_text()); raw=p.read_bytes()
        report=evaluate_case(c,root=ROOT,case_path=p.relative_to(ROOT).as_posix(),case_bytes=raw,evaluated_at="2026-09-01T23:59:00Z")
        self.assertEqual(report["validation_status"],"RG_REVIEW_REQUIRED")
        self.assertIn("RG-UPSTREAM-PI-REVIEW-REQUIRED",self.ids(report))
        self.assertIn("RG-ANCHOR-EXTENSION-BRIDGE-MISSING",self.ids(report))
        self.assertIn("RG-INDEPENDENCE-OVERSTATED",self.ids(report))
        self.assertEqual(report["recommendation"],"REQUIRE_CORROBORATION")

    def test_16_cli_writes_outside_repo_and_returns_zero_for_valid(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"out.json"
            cp=subprocess.run([sys.executable,str(SCRIPTS/"run_radiant_guardian.py"),"--root",str(ROOT),"--case","profiles/radiant-guardian/examples/RG-SYN-002/case.json","--evaluated-at","2026-09-01T23:59:00Z","--json-output",str(out)],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr+cp.stdout)
            self.assertEqual(json.loads(out.read_text())["validation_status"],"NO_RG_FINDINGS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
