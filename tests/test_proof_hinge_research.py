"""Synthetic tests only: model arithmetic and uncertainty behavior, never physical truth."""
import copy
import json
import subprocess
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from proof_hinge_research import evaluate, render_research_brief, _reject_constant, _unique_pairs  # noqa: E402


def fixture(name="proof-hinge-supplier.synthetic.json"):
    return json.loads((ROOT / "profiles" / "frontier-signal-integrity" / "fixtures" / "valid" / name).read_text(encoding="utf-8"))


class ProofHingeResearchTests(unittest.TestCase):
    def test_public_examples_have_approved_fictional_sources(self):
        directory = ROOT / "profiles" / "frontier-signal-integrity" / "fixtures" / "valid"
        approved = {
            "proof-hinge-supplier.synthetic.json": {
                "kind": "fictional_supplier_datasheet",
                "locator": "Synthetic supplier qualification worksheet; training example only",
            },
            "proof-hinge-qubit.synthetic.json": {
                "kind": "fictional_benchmark_summary",
                "locator": "Synthetic qubit characterization report; training example only",
            },
        }
        examples = sorted(directory.glob("proof-hinge-*.synthetic.json"))
        self.assertEqual({p.name for p in examples}, set(approved))
        for example in examples:
            case = json.loads(example.read_text(encoding="utf-8"))
            self.assertEqual(case["source"], approved[example.name])

    def test_supplier_specification_remains_unverified(self):
        r = evaluate(fixture())
        self.assertEqual(r["baseline"]["action"], "retain_pending_validation")
        self.assertEqual(r["test_ranking"][0]["net_modeled_regret_reduction"], 16)
        self.assertFalse(r["claims_verified"])
        self.assertEqual(r["decision_authority"], "NONE")

    def test_qubit_fidelity_remains_unverified(self):
        r = evaluate(fixture("proof-hinge-qubit.synthetic.json"))
        self.assertEqual(r["test_ranking"][0]["net_modeled_regret_reduction"], 92)
        self.assertFalse(r["independent_validation"])

    def test_ambiguous_tests_not_promoted(self):
        c = fixture()
        c["tests"] = [c["tests"][2]]
        self.assertEqual(evaluate(c)["research_status"], "ABSTAIN_NO_POSITIVE_PROOF_TEST")

    def test_all_ambiguous_outcomes_penalized(self):
        r = evaluate(fixture())
        t = next(x for x in r["test_ranking"] if x["name"].startswith("Review"))
        self.assertEqual(set(t["ambiguous_outcomes"]), {"unclear", "looks_consistent"})
        self.assertEqual(t["net_modeled_regret_reduction"], -2)

    def test_negative_and_boolean_cost_rejected(self):
        for invalid in (-1, True, float("inf"), float("nan")):
            c = fixture()
            c["tests"][0]["assumed_cost"] = invalid
            with self.assertRaises(ValueError):
                evaluate(c)

    def test_boolean_payoff_rejected(self):
        c = fixture()
        c["actions"]["approve_specification"]["specification_reproducible"] = False
        with self.assertRaises(ValueError):
            evaluate(c)

    def test_bounded_worlds(self):
        c = fixture()
        c["worlds"] = [f"world-{i}" for i in range(13)]
        with self.assertRaises(ValueError):
            evaluate(c)

    def test_bounded_tests(self):
        c = fixture()
        c["tests"] = [dict(c["tests"][0], name=f"test-{i}") for i in range(65)]
        with self.assertRaises(ValueError):
            evaluate(c)

    def test_duplicate_keys_fail_closed(self):
        with self.assertRaises(ValueError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=_unique_pairs)
        with self.assertRaises(ValueError):
            json.loads('{"x":NaN}', parse_constant=_reject_constant)

    def test_missing_world_in_test_fails(self):
        c = fixture()
        del c["tests"][0]["possible_outcomes_by_world"]["specification_reproducible"]
        with self.assertRaises(ValueError):
            evaluate(c)

    def test_variant_preserves_ranking_when_identical(self):
        c = fixture()
        c["payoff_variants"] = [{"name": "same", "actions": copy.deepcopy(c["actions"])}]
        r = evaluate(c)
        self.assertTrue(r["sensitivity"]["ranking_stable_across_supplied_tables"])
        self.assertEqual(r["research_status"], "REQUEST_EVIDENCE_FOR_REVIEW")

    def test_variant_reversal_abstains(self):
        c = fixture()
        v = copy.deepcopy(c["actions"])
        v["approve_specification"] = {"specification_reproducible": 0, "specification_not_reproducible": 0}
        c["payoff_variants"] = [{"name": "no upside", "actions": v}]
        r = evaluate(c)
        self.assertEqual(r["research_status"], "ABSTAIN_ASSUMPTION_SENSITIVE")
        self.assertIsNone(r["priority_test_if_assumptions_hold"])

    def test_bad_variant_rejected(self):
        c = fixture()
        c["payoff_variants"] = [{"name": "bad", "actions": {}}]
        with self.assertRaises(ValueError):
            evaluate(c)

    def test_no_authority_even_stable(self):
        c = fixture()
        c["payoff_variants"] = [{"name": "same", "actions": copy.deepcopy(c["actions"])}]
        r = evaluate(c)
        self.assertFalse(r["claims_verified"])
        self.assertEqual(r["decision_authority"], "NONE")


    def test_brief_conditional_and_no_authority(self):
        content = render_research_brief(evaluate(fixture()))
        self.assertIn("Possible next evidence check", content)
        self.assertIn("Not verified", content)
        self.assertIn("No decision or publication is authorized", content)
        self.assertIn("Ranking robustness is NOT ESTABLISHED", content)

    def test_brief_model_abstentions(self):
        case = fixture()
        case["tests"] = [case["tests"][2]]
        self.assertIn("No test priority justified", render_research_brief(evaluate(case)))
        case = fixture()
        v = copy.deepcopy(case["actions"])
        v["approve_specification"] = {"specification_reproducible": 0, "specification_not_reproducible": 0}
        case["payoff_variants"] = [{"name": "counterexample", "actions": v}]
        self.assertIn("No stable test priority", render_research_brief(evaluate(case)))

    def test_brief_escapes_untrusted_markdown_and_html(self):
        case = fixture()
        case["claim"] = '<img src=x onerror=alert(1)> ![tracking](https://example.test/x)'
        case["tests"][0]["name"] = '<script>alert(1)</script>'
        content = render_research_brief(evaluate(case))
        self.assertNotIn("<img", content)
        self.assertNotIn("<script", content)
        self.assertNotIn("![tracking]", content)
        self.assertIn("&lt;img", content)

    def test_cli_brief_and_default_json(self):
        cmd = [sys.executable, "-B", str(ROOT / "scripts" / "proof_hinge_research.py"), str(ROOT / "profiles" / "frontier-signal-integrity" / "fixtures" / "valid" / "proof-hinge-supplier.synthetic.json")]
        default = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
        self.assertEqual(json.loads(default), evaluate(fixture()))
        brief = subprocess.run(cmd + ["--format", "brief"], check=True, capture_output=True, text=True).stdout
        self.assertIn("# Evidence research brief", brief)
        self.assertIn("Human review required", brief)

    def test_brief_does_not_modify_model_output(self):
        result = evaluate(fixture())
        before = json.dumps(result, sort_keys=True)
        render_research_brief(result)
        self.assertEqual(json.dumps(result, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
