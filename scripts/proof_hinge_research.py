"""Bridge Node 7 frontier claim-to-proof research tool (v0.2).

Offline, synthetic, educational candidate. No external validation, no autonomous
fact verification, no equipment control, no commercial or decision authority.

Novelty is NOT established. Code combines known minimax-regret ideas with
explicit claim/provenance boundaries and set-valued observation models.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import unicodedata
from pathlib import Path

LIMIT = 1.0e12
MAX_WORLDS = 12
MAX_ACTIONS = 24
MAX_TESTS = 64
MAX_OUTCOMES_PER_WORLD = 24
MAX_VARIANTS = 16


def _name(x: object, field: str) -> str:
    if not isinstance(x, str) or not x.strip() or len(x) > 4000:
        raise ValueError(f"{field}: nonblank string required")
    return x.strip()


def _number(x: object, field: str, nonnegative: bool = False) -> float:
    if type(x) not in (int, float) or not math.isfinite(x) or abs(x) > LIMIT:
        raise ValueError(f"{field}: finite bounded number required (not bool)")
    if nonnegative and x < 0:
        raise ValueError(f"{field}: must be nonnegative")
    return float(x)


def _unique_names(seq: object, field: str, minimum: int = 1) -> tuple[str, ...]:
    if not isinstance(seq, list) or not (minimum <= len(seq) <= MAX_OUTCOMES_PER_WORLD):
        raise ValueError(f"{field}: list of {minimum}+ names required")
    result = tuple(_name(x, field) for x in seq)
    if len(set(result)) != len(result):
        raise ValueError(f"{field}: duplicate names")
    return result


def _policy(payoffs: dict, worlds: tuple[str, ...], all_worlds: tuple[str, ...]) -> dict:
    best_for_world = {w: max(p[w] for p in payoffs.values()) for w in all_worlds}
    regrets = {a: max(best_for_world[w] - p[w] for w in worlds) for a, p in payoffs.items()}
    action = min(regrets, key=lambda a: (regrets[a], a))
    return {"action": action, "worst_regret": regrets[action], "regrets": regrets}


def evaluate(case: dict) -> dict:
    if not isinstance(case, dict):
        raise ValueError("case must be a JSON object")
    case_id = _name(case.get("case_id"), "case_id")
    claim = _name(case.get("claim"), "claim")
    source = case.get("source")
    if not isinstance(source, dict):
        raise ValueError("source with kind and locator required")
    source_ref = {"kind": _name(source.get("kind"), "source.kind"),
                  "locator": _name(source.get("locator"), "source.locator"),
                  "evidence_status": "UNVERIFIED_CLAIM_OR_SYNTHETIC_EXERCISE"}
    worlds = _unique_names(case.get("worlds"), "worlds", minimum=2)
    if len(worlds) > MAX_WORLDS:
        raise ValueError("too many hypothetical worlds")
    raw_actions = case.get("actions")
    if not isinstance(raw_actions, dict) or not (2 <= len(raw_actions) <= MAX_ACTIONS):
        raise ValueError("at least two actions required")
    actions: dict[str, dict[str, float]] = {}
    for action, per_world in raw_actions.items():
        a = _name(action, "action")
        if a in actions or not isinstance(per_world, dict) or set(per_world) != set(worlds):
            raise ValueError(f"{a}: exactly one assumed payoff per world required")
        actions[a] = {w: _number(per_world[w], f"{a}.{w}") for w in worlds}
    baseline = _policy(actions, worlds, worlds)
    tests = case.get("tests")
    if not isinstance(tests, list) or not (1 <= len(tests) <= MAX_TESTS):
        raise ValueError("nonempty human-specified tests required")
    evaluated = []
    seen_tests: set[str] = set()
    for test in tests:
        if not isinstance(test, dict):
            raise ValueError("test must be an object")
        name = _name(test.get("name"), "test.name")
        if name in seen_tests:
            raise ValueError("duplicate test names")
        seen_tests.add(name)
        cost = _number(test.get("assumed_cost"), "test.assumed_cost", nonnegative=True)
        outcomes = test.get("possible_outcomes_by_world")
        if not isinstance(outcomes, dict) or set(outcomes) != set(worlds):
            raise ValueError(f"{name}: one outcome-set per world required")
        partition: dict[str, set[str]] = {}
        for world in worlds:
            labels = _unique_names(outcomes[world], f"{name}.{world}")
            for label in labels:
                partition.setdefault(label, set()).add(world)
        conditional = {
            label: _policy(actions, tuple(w for w in worlds if w in associated), worlds)
            for label, associated in sorted(partition.items())
        }
        # Adversarial/worst-case treatment: the observation may be ANY outcome
        # the model assigned to that world; this is NOT a probability model.
        after = max(p["worst_regret"] for p in conditional.values())
        gain = baseline["worst_regret"] - after
        net = gain - cost
        evaluated.append({
            "name": name, "assumed_cost": cost,
            "gross_modeled_regret_reduction": round(gain, 7),
            "net_modeled_regret_reduction": round(net, 7),
            "post_test_worst_regret": round(after, 7),
            "outcome_policy": {label: row["action"] for label, row in conditional.items()},
            "ambiguous_outcomes": [label for label, assoc in sorted(partition.items()) if len(assoc) > 1],
            "outcome_assumptions_verified": False,
        })
    evaluated.sort(key=lambda x: (-x["net_modeled_regret_reduction"], x["name"]))
    positives = [t for t in evaluated if t["net_modeled_regret_reduction"] > 0]
    result = {
        "record_kind": "bn7.frontier_research_candidate",
        "record_version": "0.2", "case_id": case_id, "claim": claim,
        "source": source_ref, "worlds_are_hypothetical": True,
        "baseline": baseline, "test_ranking": evaluated,
        "research_status": "REQUEST_EVIDENCE_FOR_REVIEW" if positives else "ABSTAIN_NO_POSITIVE_PROOF_TEST",
        "priority_test_if_assumptions_hold": positives[0]["name"] if positives else None,
        "claims_verified": False, "independent_validation": False,
        "decision_authority": "NONE", "repo_write_performed": False,
        "model_warning": "Assumed payoffs and possible observations are not calibrated probabilities, verified facts, validated economic values, or authorization to act.",
    }
    # Explicit counterfactual utility tables: not confidence intervals or measured probabilities.
    # A recommendation survives only when the SAME test ranks positively first in every
    # operator-supplied variant. Otherwise the research model abstains.
    variants = case.get("payoff_variants", [])
    if not isinstance(variants, list) or len(variants) > MAX_VARIANTS:
        raise ValueError("payoff_variants must be a bounded list")
    checked = []
    for index, variant in enumerate(variants):
        if not isinstance(variant, dict) or set(variant) != {"name", "actions"}:
            raise ValueError("variant requires only name and actions")
        label = _name(variant["name"], f"variant[{index}].name")
        if any(row["name"] == label for row in checked):
            raise ValueError("duplicate variant")
        proposed = variant["actions"]
        if not isinstance(proposed, dict) or set(proposed) != set(actions):
            raise ValueError("variant action names must match baseline")
        for a, per_world in proposed.items():
            if not isinstance(per_world, dict) or set(per_world) != set(worlds):
                raise ValueError("variant worlds must match baseline")
            for w in worlds:
                _number(per_world[w], f"variant.{label}.{a}.{w}")
        candidate = dict(case)
        candidate["actions"] = proposed
        candidate.pop("payoff_variants", None)
        recalculated = evaluate(candidate)
        checked.append({
            "name": label,
            "baseline_action": recalculated["baseline"]["action"],
            "priority_test_if_assumptions_hold": recalculated["priority_test_if_assumptions_hold"],
        })
    if variants:
        stable = result["priority_test_if_assumptions_hold"] is not None and all(
            x["priority_test_if_assumptions_hold"] == result["priority_test_if_assumptions_hold"]
            for x in checked
        )
        result["sensitivity"] = {
            "tested_counterfactual_tables": checked,
            "ranking_stable_across_supplied_tables": stable,
            "tables_are_not_probabilities_or_calibrated": True,
        }
        if not stable:
            result["research_status"] = "ABSTAIN_ASSUMPTION_SENSITIVE"
            result["priority_test_if_assumptions_hold"] = None
    return result



def _brief_text(value: object) -> str:
    """Keep user-supplied labels inert in Markdown, including HTML and link syntax."""
    text = str(value)
    normalized = "".join(
        " " if char.isspace() else (
            f"U+{ord(char):04X}" if unicodedata.category(char) in {"Cf", "Cc"} else char
        )
        for char in text
    )
    # HTML escaping blocks raw tags, Markdown escaping blocks links and images.
    escaped = html.escape(normalized, quote=False)
    return "".join("\\" + ch if ch in "\\`*_{}[]()#+-.!|>" else ch for ch in escaped)


def render_research_brief(result: dict) -> str:
    """Optional human-facing projection, derived only from the unchanged result."""
    if result.get("record_kind") != "bn7.frontier_research_candidate":
        raise ValueError("unexpected research result kind")
    status = result["research_status"]
    if status not in {"REQUEST_EVIDENCE_FOR_REVIEW", "ABSTAIN_NO_POSITIVE_PROOF_TEST", "ABSTAIN_ASSUMPTION_SENSITIVE"}:
        raise ValueError("unsupported research status")
    selected = result["priority_test_if_assumptions_hold"]
    if status == "REQUEST_EVIDENCE_FOR_REVIEW":
        heading = "Possible next evidence check (conditional)"
        action = _brief_text(selected)
        row = next(item for item in result["test_ranking"] if item["name"] == selected)
        explanation = (
            f"Under the supplied fictional payoffs and observation outcomes, "
            f"modeled net regret reduction is {row['net_modeled_regret_reduction']:g} "
            f"arbitrary utility units (including an assumed test cost of {row['assumed_cost']:g}). "
            "This is not a measured benefit, real-world probability, or verification."
        )
    elif status == "ABSTAIN_NO_POSITIVE_PROOF_TEST":
        heading = "No test priority justified by this model"
        action = "Abstain. Revisit candidate measurements and assumed consequences."
        explanation = "None of the supplied tests has positive net modeled value under the assumed worlds and costs."
    else:
        heading = "No stable test priority"
        action = "Abstain. Review the assumption differences before choosing a measurement."
        explanation = "The top-scoring test was not consistently positive and first across the supplied alternative payoff tables."

    variants = result.get("sensitivity")
    sensitivity = (
        f"{len(variants['tested_counterfactual_tables'])} alternative payoff table(s) evaluated; "
        f"ranking stable: {'yes' if variants['ranking_stable_across_supplied_tables'] else 'no'}."
        if variants else "No alternative payoff tables supplied. Ranking robustness is NOT ESTABLISHED."
    )
    lines = [
        "# Evidence research brief",
        "",
        "**Status: Synthetic research only | Not verified | Human review required**",
        "",
        f"**Case:** {_brief_text(result['case_id'])}",
        f"**Claim being examined:** {_brief_text(result['claim'])}",
        "",
        f"## {heading}",
        "",
        action,
        "",
        explanation,
        "",
        "## What must be checked",
        "",
        "- Verify whether the possible explanations and measurement outcomes represent reality.",
        "- Independently substantiate evidence rights, test accuracy, costs, and consequences.",
        "- Preserve alternative explanations and unresolved possibilities.",
        "",
        "## Assumptions and reversal",
        "",
        sensitivity,
        "",
        "**No scientific claim was verified. No equipment was operated. No decision or publication is authorized.**",
        "",
    ]
    return "\n".join(lines)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(token):
    raise ValueError(f"nonfinite JSON value not allowed: {token}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline FSI Proof-Hinge research candidate")
    parser.add_argument("input", type=Path, help="Case JSON file")
    parser.add_argument("--output", type=Path, help="Optional result file")
    parser.add_argument("--format", choices=("json", "brief"), default="json", help="JSON (default) or human research brief")
    args = parser.parse_args()
    result = evaluate(json.loads(args.input.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_reject_constant))
    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n"
               if args.format == "json" else render_research_brief(result))
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
