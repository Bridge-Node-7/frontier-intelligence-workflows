#!/usr/bin/env python3
"""Deterministic Radiant Guardian frontier-signal integrity controls.

The module validates declared integrity conditions. It does not determine
external truth, verify evidence authenticity, or authorize consequential action.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROFILE_VERSION = "0.1.0"
RULESET_VERSION = "1.0.0"
VALIDATOR_VERSION = "0.1.0"
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_TOP = {
    "metadata", "pi_reference", "signal", "genealogy", "hypotheses",
    "reasoning_patterns", "predictions", "tests", "update_receipts",
    "proof_loop", "review",
}
ALLOWED_TOP = REQUIRED_TOP
GENERATED_ORIGINS = {"AI_ASSISTED", "CREATIVE_PSIONICS"}


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not RFC3339_UTC.fullmatch(value):
        raise ValueError(f"{field} must use UTC RFC3339 YYYY-MM-DDTHH:MM:SSZ")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _finding(control: str, finding_id: str, severity: str, message: str, field: str) -> dict[str, str]:
    return {"control_id": control, "finding_id": finding_id, "severity": severity, "message": message, "related_field": field}


def structural_issues(case: Any) -> list[str]:
    """Bounded fail-closed case-contract checks; schema remains the authoring contract."""
    issues: list[str] = []
    if not isinstance(case, Mapping):
        return ["$: case must be one JSON object"]
    keys = set(case)
    missing = sorted(REQUIRED_TOP - keys)
    extra = sorted(keys - ALLOWED_TOP)
    for key in missing:
        issues.append(f"$: missing required property {key!r}")
    for key in extra:
        issues.append(f"$: additional property {key!r} is not allowed")
    if issues:
        return issues

    metadata = _map(case["metadata"])
    for key in ("rg_case_id", "version", "synthetic", "subject"):
        if key not in metadata:
            issues.append(f"$.metadata: missing {key}")
    if not _nonempty(metadata.get("rg_case_id")):
        issues.append("$.metadata.rg_case_id: non-empty string required")
    if not isinstance(metadata.get("synthetic"), bool):
        issues.append("$.metadata.synthetic: boolean required")

    pi = _map(case["pi_reference"])
    for key in ("assessment_id", "validation_path", "validation_sha256"):
        if not _nonempty(pi.get(key)):
            issues.append(f"$.pi_reference.{key}: non-empty string required")
    digest = pi.get("validation_sha256")
    if isinstance(digest, str) and not SHA256.fullmatch(digest):
        issues.append("$.pi_reference.validation_sha256: 64 lowercase hex characters required")

    signal = _map(case["signal"])
    for key in ("mode", "statement", "category", "novelty", "observability", "asserted_as_fact", "requires_independent_corroboration"):
        if key not in signal:
            issues.append(f"$.signal: missing {key}")
    if not _nonempty(signal.get("statement")):
        issues.append("$.signal.statement: non-empty string required")
    for key in ("asserted_as_fact", "requires_independent_corroboration"):
        if not isinstance(signal.get(key), bool):
            issues.append(f"$.signal.{key}: boolean required")

    genealogy = _map(case["genealogy"])
    for key in ("roots", "nodes", "edges", "declared_independent_root_count"):
        if key not in genealogy:
            issues.append(f"$.genealogy: missing {key}")
    if not isinstance(genealogy.get("declared_independent_root_count"), int):
        issues.append("$.genealogy.declared_independent_root_count: integer required")

    for field in ("hypotheses", "reasoning_patterns", "predictions", "tests", "update_receipts"):
        if not isinstance(case[field], list):
            issues.append(f"$.{field}: array required")

    proof = _map(case["proof_loop"])
    for key in ("active", "decision_reference", "action_reference", "outcome_state", "learning_recorded", "reassessment_trigger"):
        if key not in proof:
            issues.append(f"$.proof_loop: missing {key}")
    review = _map(case["review"])
    if review.get("human_review_required") is not True:
        issues.append("$.review.human_review_required: must be true")
    if not _nonempty(review.get("owner")):
        issues.append("$.review.owner: non-empty string required")
    if not isinstance(review.get("public_release_allowed"), bool):
        issues.append("$.review.public_release_allowed: boolean required")
    return sorted(set(issues))


def _resolve_repo_file(root: Path, raw: str, field: str) -> Path:
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{field} must resolve inside repository root") from exc
    if not candidate.is_file():
        raise ValueError(f"{field} does not resolve to a file: {raw}")
    return candidate


def _load_upstream_pi(root: Path, case: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    pi_ref = _map(case.get("pi_reference"))
    path_raw = pi_ref.get("validation_path")
    digest = pi_ref.get("validation_sha256")
    if not _nonempty(path_raw) or not _nonempty(digest):
        return {}, [_finding("RG-01", "RG-UPSTREAM-PI-UNRESOLVED", "BLOCKING", "PI validation reference is incomplete.", "pi_reference")]
    try:
        path = _resolve_repo_file(root, str(path_raw), "pi_reference.validation_path")
        raw = path.read_bytes()
        actual = sha256_bytes(raw)
        if actual != digest:
            findings.append(_finding("RG-01", "RG-UPSTREAM-PI-UNRESOLVED", "BLOCKING", "Referenced PI validation digest does not match exact bytes.", "pi_reference.validation_sha256"))
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("PI validation must contain one JSON object")
        if value.get("assessment_id") != pi_ref.get("assessment_id"):
            findings.append(_finding("RG-01", "RG-UPSTREAM-PI-UNRESOLVED", "BLOCKING", "Referenced PI assessment ID does not match RG declaration.", "pi_reference.assessment_id"))
        if value.get("human_decision_required") is not True:
            findings.append(_finding("RG-01", "RG-UPSTREAM-PI-UNRESOLVED", "BLOCKING", "Upstream PI validation must preserve human decision authority.", "pi_reference.validation_path"))
        if value.get("validation_status") != "NO_FINDINGS" or value.get("recommendation") != "READY_FOR_HUMAN_REVIEW":
            findings.append(_finding("RG-01", "RG-UPSTREAM-PI-REVIEW-REQUIRED", "BLOCKING", "Upstream PI validation already requires review; RG cannot mask or downgrade it.", "pi_reference.validation_path"))
        return value, findings
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        findings.append(_finding("RG-01", "RG-UPSTREAM-PI-UNRESOLVED", "BLOCKING", str(exc), "pi_reference.validation_path"))
        return {}, findings


def evaluate_case(case: Mapping[str, Any], *, root: Path, case_path: str, case_bytes: bytes, evaluated_at: str) -> dict[str, Any]:
    parse_utc(evaluated_at, "evaluated_at")
    issues = structural_issues(case)
    if issues:
        raise ValueError("case outside bounded RG contract: " + "; ".join(issues))
    findings: list[dict[str, str]] = []
    upstream, upstream_findings = _load_upstream_pi(root, case)
    findings.extend(upstream_findings)

    signal = _map(case.get("signal"))
    if signal.get("mode") != "DIRECT_OBSERVATION" and signal.get("asserted_as_fact") is True:
        findings.append(_finding("RG-02", "RG-SIGNAL-CLAIM-COLLAPSE", "BLOCKING", "A reported/inferred/interpreted signal is declared as established fact.", "signal.asserted_as_fact"))

    genealogy = _map(case.get("genealogy"))
    roots = [x for x in _list(genealogy.get("roots")) if _nonempty(x)]
    declared = genealogy.get("declared_independent_root_count")
    if declared != len(set(roots)):
        findings.append(_finding("RG-03", "RG-INDEPENDENCE-OVERSTATED", "BLOCKING", "Declared independent-root count does not equal the unique declared roots.", "genealogy.declared_independent_root_count"))
    if signal.get("requires_independent_corroboration") is True and len(set(roots)) < 2:
        findings.append(_finding("RG-03", "RG-INDEPENDENCE-OVERSTATED", "BLOCKING", "The case requires independent corroboration but fewer than two independent roots are declared.", "genealogy.roots"))

    tests = {str(_map(t).get("test_id")): _map(t) for t in _list(case.get("tests")) if _nonempty(_map(t).get("test_id"))}
    for pattern in _list(case.get("reasoning_patterns")):
        item = _map(pattern)
        kind = item.get("pattern")
        if kind == "REAL_ANCHOR_EXTRAORDINARY_EXTENSION" and not [x for x in _list(item.get("bridge_evidence_references")) if _nonempty(x)]:
            findings.append(_finding("RG-04", "RG-ANCHOR-EXTENSION-BRIDGE-MISSING", "BLOCKING", "A real-anchor → extraordinary-extension pattern lacks declared bridge evidence.", "reasoning_patterns.bridge_evidence_references"))
        if kind == "SELF_SEALING_RISK":
            linked = [x for x in _list(item.get("discriminating_test_ids")) if _nonempty(x)]
            if not linked or any(test_id not in tests for test_id in linked):
                findings.append(_finding("RG-05", "RG-SELF-SEALING-WITHOUT-DISCRIMINATOR", "BLOCKING", "Self-sealing risk lacks a resolvable discriminating test.", "reasoning_patterns.discriminating_test_ids"))

    for prediction in _list(case.get("predictions")):
        p = _map(prediction)
        pid = p.get("prediction_id") or "<unknown>"
        essentials = ("statement", "frozen_at", "window_start", "window_end")
        if p.get("status") == "OPEN" and (any(not _nonempty(p.get(k)) for k in essentials)):
            findings.append(_finding("RG-06", "RG-PREDICTION-NOT-FROZEN", "BLOCKING", f"Open prediction {pid} lacks a frozen statement/time window.", "predictions"))
        try:
            frozen = parse_utc(str(p.get("frozen_at")), f"prediction {pid}.frozen_at")
            start = parse_utc(str(p.get("window_start")), f"prediction {pid}.window_start")
            end = parse_utc(str(p.get("window_end")), f"prediction {pid}.window_end")
            if frozen > start or start > end:
                findings.append(_finding("RG-06", "RG-PREDICTION-NOT-FROZEN", "BLOCKING", f"Prediction {pid} chronology is not frozen_at ≤ window_start ≤ window_end.", "predictions"))
        except ValueError:
            findings.append(_finding("RG-06", "RG-PREDICTION-NOT-FROZEN", "BLOCKING", f"Prediction {pid} uses an invalid UTC timestamp.", "predictions"))
        criteria_fields = ("success_criteria", "failure_criteria", "ambiguous_criteria", "unresolved_criteria")
        if any(not [x for x in _list(p.get(k)) if _nonempty(x)] for k in criteria_fields):
            findings.append(_finding("RG-07", "RG-PREDICTION-RESOLUTION-INCOMPLETE", "BLOCKING", f"Prediction {pid} requires success, failure, ambiguous, and unresolved criteria.", "predictions"))

    hypothesis_ids = {str(_map(h).get("hypothesis_id")) for h in _list(case.get("hypotheses")) if _nonempty(_map(h).get("hypothesis_id"))}
    for test in _list(case.get("tests")):
        t = _map(test)
        tid = t.get("test_id") or "<unknown>"
        refs = [x for x in _list(t.get("hypothesis_ids")) if _nonempty(x)]
        if len(set(refs)) < 2 or any(x not in hypothesis_ids for x in refs) or not [x for x in _list(t.get("discriminating_evidence")) if _nonempty(x)] or not _nonempty(t.get("observable_outcome")) or not _nonempty(t.get("decision_rule")):
            findings.append(_finding("RG-08", "RG-DISCRIMINATING-TEST-INCOMPLETE", "BLOCKING", f"Test {tid} must compare at least two existing hypotheses using observable discriminating evidence and a decision rule.", "tests"))

    for hypothesis in _list(case.get("hypotheses")):
        h = _map(hypothesis)
        if h.get("origin") in GENERATED_ORIGINS and h.get("evidence_weight") != "NONE_UNTIL_EVIDENCED":
            findings.append(_finding("RG-09", "RG-GENERATED-HYPOTHESIS-PROMOTED", "BLOCKING", f"Generated hypothesis {h.get('hypothesis_id', '<unknown>')} received evidentiary weight merely from generation.", "hypotheses.evidence_weight"))

    for receipt in _list(case.get("update_receipts")):
        r = _map(receipt)
        required = ("receipt_id", "previous_state", "new_state", "rationale", "reviewer", "updated_at", "reversal_trigger")
        missing = any(not _nonempty(r.get(k)) for k in required) or not [x for x in _list(r.get("evidence_delta")) if _nonempty(x)]
        try:
            parse_utc(str(r.get("updated_at")), "update_receipt.updated_at")
        except ValueError:
            missing = True
        if missing:
            findings.append(_finding("RG-10", "RG-UPDATE-RECEIPT-INCOMPLETE", "BLOCKING", "A material update receipt lacks the complete evidence/rationale/reviewer/time/reversal record.", "update_receipts"))

    if _map(case.get("review")).get("public_release_allowed") is True and upstream.get("recommendation") == "DO_NOT_RELEASE_PUBLICLY":
        findings.append(_finding("RG-11", "RG-PUBLIC-BOUNDARY-VIOLATION", "CRITICAL", "RG cannot permit public release when upstream PI forbids it.", "review.public_release_allowed"))

    proof = _map(case.get("proof_loop"))
    if proof.get("active") is True:
        if not _nonempty(proof.get("reassessment_trigger")):
            findings.append(_finding("RG-12", "RG-PROOF-LOOP-INCOMPLETE", "WARNING", "Active Proof Loop lacks a reassessment trigger.", "proof_loop.reassessment_trigger"))
        if proof.get("outcome_state") == "OBSERVED" and proof.get("learning_recorded") is not True:
            findings.append(_finding("RG-12", "RG-PROOF-LOOP-INCOMPLETE", "WARNING", "Observed outcome must record a learning before the loop is considered complete.", "proof_loop.learning_recorded"))

    unique = {(f["control_id"], f["finding_id"], f["related_field"], f["message"]): f for f in findings}
    findings = sorted(unique.values(), key=lambda f: (0 if f["severity"] == "CRITICAL" else 1 if f["severity"] == "BLOCKING" else 2, f["control_id"], f["finding_id"], f["related_field"]))
    ids = {f["finding_id"] for f in findings}
    if "RG-PUBLIC-BOUNDARY-VIOLATION" in ids:
        recommendation = "DO_NOT_RELEASE_PUBLICLY"
    elif ids & {"RG-UPSTREAM-PI-REVIEW-REQUIRED", "RG-UPSTREAM-PI-UNRESOLVED", "RG-INDEPENDENCE-OVERSTATED"}:
        recommendation = "REQUIRE_CORROBORATION"
    elif ids & {"RG-ANCHOR-EXTENSION-BRIDGE-MISSING", "RG-SELF-SEALING-WITHOUT-DISCRIMINATOR", "RG-DISCRIMINATING-TEST-INCOMPLETE"}:
        recommendation = "REQUIRE_DISCRIMINATING_EVIDENCE"
    elif ids & {"RG-PREDICTION-NOT-FROZEN", "RG-PREDICTION-RESOLUTION-INCOMPLETE"}:
        recommendation = "REVISE_PREDICTION"
    elif findings:
        recommendation = "REASSESS_BEFORE_ACTION"
    else:
        recommendation = "READY_FOR_HUMAN_REVIEW"

    return {
        "rg_case_id": _map(case.get("metadata")).get("rg_case_id"),
        "case_path": case_path,
        "case_sha256": sha256_bytes(case_bytes),
        "evaluated_at": evaluated_at,
        "profile_version": PROFILE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "upstream_pi": {
            "assessment_id": _map(case.get("pi_reference")).get("assessment_id"),
            "validation_status": upstream.get("validation_status", "UNRESOLVED"),
            "recommendation": upstream.get("recommendation", "UNRESOLVED"),
            "validation_sha256": _map(case.get("pi_reference")).get("validation_sha256"),
        },
        "findings": findings,
        "validation_status": "RG_REVIEW_REQUIRED" if findings else "NO_RG_FINDINGS",
        "recommendation": recommendation,
        "human_decision_required": True,
    }
