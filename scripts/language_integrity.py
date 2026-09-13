#!/usr/bin/env python3
"""Deterministic Language Integrity rules for Frontier Intelligence Workflows.

The evaluator checks declared semantic relationships. It does not parse arbitrary
language, determine external truth, authenticate evidence, or authorize action.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any

sys.dont_write_bytecode = True

PROFILE_VERSION = "0.7.0"
RULESET_VERSION = "1.0.0"

FORECAST_LIKE = {"FORECAST", "DESIGN_TARGET"}
DIRECT_COMPATIBLE = {"OBSERVATION"}
SEVERITY_ORDER = {"BLOCKING": 0, "WARNING": 1, "INFO": 2}


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _finding(control_id: str, finding_id: str, message: str, field: str, severity: str = "BLOCKING") -> dict[str, str]:
    return {
        "control_id": control_id,
        "finding_id": finding_id,
        "severity": severity,
        "message": message,
        "related_field": field,
    }


def evaluate_case(case: Mapping[str, Any], *, case_path: str, case_bytes: bytes) -> dict[str, Any]:
    if not isinstance(case, Mapping):
        raise TypeError("case must be a mapping")
    if not isinstance(case_path, str) or not case_path.strip():
        raise ValueError("case_path must be a non-empty repository-relative path")
    normalized_path = case_path.replace("\\", "/")
    if normalized_path.startswith("/") or ".." in normalized_path.split("/"):
        raise ValueError("case_path must remain repository-relative")
    if not isinstance(case_bytes, bytes):
        raise TypeError("case_bytes must be exact bytes")

    metadata = _mapping(case.get("metadata"))
    claim = _mapping(case.get("claim"))
    source_records = [_mapping(item) for item in _list(case.get("source_records"))]
    source_by_id: dict[str, Mapping[str, Any]] = {}
    findings: list[dict[str, str]] = []

    for record in source_records:
        source_id = record.get("source_id")
        if isinstance(source_id, str) and source_id:
            if source_id in source_by_id:
                findings.append(_finding("LI-00", "LI-DUPLICATE-SOURCE-ID", f"Duplicate source_id {source_id!r}.", "source_records"))
            source_by_id[source_id] = record
        if record.get("temporal_status") == "SUPERSEDED":
            successor = record.get("superseded_by")
            if not isinstance(successor, str) or not successor:
                findings.append(_finding("LI-05", "LI-TEMPORAL-LINEAGE-INCOMPLETE", "A superseded source must declare its successor.", "source_records[].superseded_by"))
            elif successor not in {item.get("source_id") for item in source_records}:
                findings.append(_finding("LI-05", "LI-TEMPORAL-LINEAGE-INCOMPLETE", f"Supersession target {successor!r} is not declared.", "source_records[].superseded_by"))

    cited_ids = [item for item in _list(claim.get("source_ids")) if isinstance(item, str) and item]
    unresolved = sorted(set(cited_ids) - set(source_by_id))
    if unresolved:
        findings.append(_finding("LI-00", "LI-SOURCE-REFERENCE-UNRESOLVED", f"Claim cites undeclared sources: {', '.join(unresolved)}.", "claim.source_ids"))
    cited = [source_by_id[item] for item in cited_ids if item in source_by_id]

    if claim.get("claim_mode") == "DEMONSTRATED_RESULT" and any(record.get("assertion_type") in FORECAST_LIKE for record in cited):
        findings.append(_finding("LI-01", "LI-FORECAST-AS-RESULT", "A forecast or design target is being represented as a demonstrated result.", "claim.claim_mode"))

    quoted = [record for record in cited if record.get("assertion_type") == "QUOTED_ASSERTION"]
    for record in quoted:
        source_attribution = record.get("attributed_to")
        claim_attribution = claim.get("attributed_to")
        if not isinstance(source_attribution, str) or not source_attribution or claim_attribution != source_attribution:
            findings.append(_finding("LI-02", "LI-ATTRIBUTION-LOSS", "Quoted-assertion attribution was lost or changed in the interpreted claim.", "claim.attributed_to"))
            break

    if claim.get("claim_mode") == "INFERENCE" and claim.get("support_basis") == "DIRECT":
        findings.append(_finding("LI-03", "LI-INFERENCE-AS-DIRECT", "An inference is labeled as directly supported rather than derived.", "claim.support_basis"))

    if claim.get("claim_mode") == "DIRECT_OBSERVATION" and any(record.get("assertion_type") not in DIRECT_COMPATIBLE for record in cited):
        findings.append(_finding("LI-03", "LI-REPORTED-AS-OBSERVATION", "A non-observation source assertion is being represented as direct observation.", "claim.claim_mode"))

    roots = {
        str(record.get("root_source_id"))
        for record in cited
        if isinstance(record.get("root_source_id"), str) and str(record.get("root_source_id"))
    }
    declared_count = claim.get("declared_independent_source_count")
    if cited and declared_count != len(roots):
        findings.append(_finding("LI-04", "LI-PROVENANCE-INDEPENDENCE-OVERSTATED", f"Declared independent-source count {declared_count!r} does not equal the {len(roots)} declared provenance root(s).", "claim.declared_independent_source_count"))

    if claim.get("temporal_status") == "CURRENT" and any(record.get("temporal_status") == "SUPERSEDED" for record in cited):
        findings.append(_finding("LI-05", "LI-SUPERSEDED-AS-CURRENT", "A claim marked CURRENT cites a source record already declared SUPERSEDED.", "claim.temporal_status"))

    public_boundary = _mapping(case.get("public_boundary"))
    if metadata.get("synthetic") is not True or public_boundary.get("contains_sensitive_data") is not False or public_boundary.get("public_release_allowed") is not True:
        findings.append(_finding("LI-06", "LI-PUBLIC-BOUNDARY-VIOLATION", "The public Language Integrity profile accepts only synthetic, nonsensitive, public-release-allowed records.", "public_boundary"))

    review = _mapping(case.get("review_requirements"))
    if review.get("human_review_required") is not True or not isinstance(review.get("decision_owner"), str) or not str(review.get("decision_owner")).strip():
        findings.append(_finding("LI-07", "LI-HUMAN-REVIEW-MISSING", "Human review and an accountable decision owner are required.", "review_requirements"))

    findings.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 99), item["control_id"], item["finding_id"], item["message"]))
    status = "NO_FINDINGS" if not findings else "REVIEW_REQUIRED"
    recommendation = "READY_FOR_HUMAN_REVIEW" if not findings else "REQUIRE_CORRECTION"
    return {
        "profile": "LANGUAGE_INTEGRITY",
        "profile_version": PROFILE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "case_id": metadata.get("case_id", "UNDECLARED"),
        "case_path": normalized_path,
        "case_sha256": sha256_bytes(case_bytes),
        "derived_independent_root_count": len(roots),
        "status": status,
        "recommendation": recommendation,
        "findings": findings,
        "human_review_required": True,
        "non_claim": "No finding establishes external truth, source independence, readiness, or decision authority.",
    }
