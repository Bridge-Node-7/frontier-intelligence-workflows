#!/usr/bin/env python3
"""Deterministic Perception Integrity rules for Frontier Intelligence Workflows.

This module evaluates structure and declared evidence conditions. It does
not determine whether a claim is true and it never authorizes action.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

sys.dont_write_bytecode = True

PROFILE_VERSION = "0.3.0"
RULESET_VERSION = "1.1.0"
VALIDATOR_VERSION = "0.3.0"

CLAIM_MODES = {
    "DIRECT_OBSERVATION",
    "REPORTED_CLAIM",
    "INFERENCE",
    "INTERPRETATION",
    "FORECAST",
    "RECOMMENDATION",
}
SOURCE_RELATIONSHIPS = {
    "PRIMARY",
    "REPUBLICATION",
    "SUMMARY",
    "COMMENTARY",
    "TRANSLATION",
    "WRAPPER_PAGE",
    "PRESS_REPORT",
    "AI_DERIVATION",
    "UNKNOWN",
}
CONSEQUENCES = {"LOW", "MODERATE", "MAJOR", "CRITICAL"}
REVERSIBILITY = {
    "REVERSIBLE",
    "PARTIALLY_REVERSIBLE",
    "DIFFICULT_TO_REVERSE",
    "IRREVERSIBLE",
}
SALIENCE = {"LOW", "MEDIUM", "HIGH"}
EVIDENCE_STRENGTH = {"NONE", "WEAK", "LIMITED", "MODERATE", "STRONG"}
SEVERITY_ORDER = {"CRITICAL": 0, "BLOCKING": 1, "WARNING": 2, "INFO": 3}
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

CONTROL_FINDINGS: dict[str, tuple[str, ...]] = {
    "PI-01": ("PI-CLAIM-MODE-MISMATCH",),
    "PI-02": ("PI-INFERENCE-AS-OBSERVATION",),
    "PI-03": ("PI-SOURCE-LINEAGE-UNRESOLVED",),
    "PI-04": ("PI-DERIVATIVE-CORROBORATION",),
    "PI-05": ("PI-MATERIAL-ASSUMPTION-MISSING",),
    "PI-06": ("PI-ALTERNATIVE-HYPOTHESIS-MISSING",),
    "PI-07": ("PI-SALIENCE-EVIDENCE-MISMATCH",),
    "PI-08": ("PI-EVIDENCE-EXPIRED",),
    "PI-09": ("PI-IRREVERSIBLE-WEAK-EVIDENCE",),
    "PI-10": ("PI-HUMAN-REVIEW-MISSING", "PI-DECISION-OWNER-MISSING"),
    "PI-11": ("PI-STOP-CONDITION-MISSING",),
    "PI-12": ("PI-PUBLIC-BOUNDARY-VIOLATION",),
}


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON bytes with a final LF."""
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest for exact bytes."""
    return hashlib.sha256(data).hexdigest()


def parse_utc(value: str, *, field: str) -> datetime:
    """Parse the contract's explicit UTC RFC3339 representation."""
    if not isinstance(value, str) or not RFC3339_UTC.fullmatch(value):
        raise ValueError(f"{field} must use UTC RFC3339 YYYY-MM-DDTHH:MM:SSZ")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _normalize_text(value: str) -> str:
    """Normalize text for semantic comparisons without changing stored evidence bytes."""
    normalized = unicodedata.normalize("NFC", value)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Cf")
    return re.sub(r"\s+", " ", normalized).strip()


def _text_items(value: Any) -> list[str]:
    return [
        normalized
        for item in _list(value)
        if isinstance(item, str) and (normalized := _normalize_text(item))
    ]


def _finding(
    control_id: str,
    finding_id: str,
    severity: str,
    message: str,
    related_field: str,
) -> dict[str, str]:
    return {
        "control_id": control_id,
        "finding_id": finding_id,
        "severity": severity,
        "message": message,
        "related_field": related_field,
    }


def _lineage_findings(assessment: Mapping[str, Any]) -> list[dict[str, str]]:
    sources = _list(assessment.get("source_lineage"))
    if not sources:
        return [
            _finding(
                "PI-03",
                "PI-SOURCE-LINEAGE-UNRESOLVED",
                "BLOCKING",
                "No source-lineage records were declared.",
                "source_lineage",
            )
        ]

    ids: list[str] = []
    parents: dict[str, str | None] = {}
    unresolved = False
    for item in sources:
        record = _mapping(item)
        source_id = record.get("source_id")
        relationship = record.get("relationship")
        parent_id = record.get("parent_id")
        if not isinstance(source_id, str) or not source_id.strip():
            unresolved = True
            continue
        source_id = source_id.strip()
        ids.append(source_id)
        if relationship not in SOURCE_RELATIONSHIPS:
            unresolved = True
        if parent_id is not None and (not isinstance(parent_id, str) or not parent_id.strip()):
            unresolved = True
            parent_id = None
        parents[source_id] = parent_id.strip() if isinstance(parent_id, str) else None

    if len(ids) != len(set(ids)):
        unresolved = True
    known = set(ids)
    if any(parent is not None and parent not in known for parent in parents.values()):
        unresolved = True

    for start in known:
        seen: set[str] = set()
        current: str | None = start
        while current is not None:
            if current in seen:
                unresolved = True
                break
            seen.add(current)
            current = parents.get(current)

    if unresolved:
        return [
            _finding(
                "PI-03",
                "PI-SOURCE-LINEAGE-UNRESOLVED",
                "BLOCKING",
                "Source lineage contains a missing, duplicate, invalid, or cyclic reference.",
                "source_lineage",
            )
        ]
    return []


def _recommendation(findings: list[dict[str, str]]) -> str:
    ids = {item["finding_id"] for item in findings}
    if "PI-PUBLIC-BOUNDARY-VIOLATION" in ids:
        return "DO_NOT_RELEASE_PUBLICLY"
    if any(item["severity"] == "CRITICAL" for item in findings):
        return "HOLD"
    if ids & {"PI-SOURCE-LINEAGE-UNRESOLVED", "PI-DERIVATIVE-CORROBORATION"}:
        return "REQUIRE_CORROBORATION"
    completeness = {
        "PI-CLAIM-MODE-MISMATCH",
        "PI-INFERENCE-AS-OBSERVATION",
        "PI-MATERIAL-ASSUMPTION-MISSING",
        "PI-ALTERNATIVE-HYPOTHESIS-MISSING",
        "PI-SALIENCE-EVIDENCE-MISMATCH",
        "PI-HUMAN-REVIEW-MISSING",
        "PI-DECISION-OWNER-MISSING",
        "PI-STOP-CONDITION-MISSING",
    }
    if ids & completeness:
        return "REQUEST_ADDITIONAL_EVIDENCE"
    if "PI-EVIDENCE-EXPIRED" in ids:
        return "REASSESS_BEFORE_ACTION"
    if "PI-IRREVERSIBLE-WEAK-EVIDENCE" in ids:
        return "ESCALATE_FOR_HUMAN_REVIEW"
    return "READY_FOR_HUMAN_REVIEW"


def validate_schema_instance(
    value: Any,
    schema: Mapping[str, Any],
    *,
    path: str = "$",
) -> list[str]:
    """Validate the bounded JSON-Schema subset used by the PI profile.

    This is intentionally not a general-purpose JSON Schema implementation. It
    enforces the exact frozen keywords used by the three public PI schemas and
    returns stable, sorted issue strings for deterministic testing.
    """
    issues: list[str] = []

    def type_matches(candidate: Any, expected: str) -> bool:
        if expected == "object":
            return isinstance(candidate, Mapping)
        if expected == "array":
            return isinstance(candidate, list)
        if expected == "string":
            return isinstance(candidate, str)
        if expected == "boolean":
            return isinstance(candidate, bool)
        if expected == "null":
            return candidate is None
        if expected == "integer":
            return isinstance(candidate, int) and not isinstance(candidate, bool)
        if expected == "number":
            return isinstance(candidate, (int, float)) and not isinstance(candidate, bool)
        return False

    def walk(candidate: Any, rule: Mapping[str, Any], current: str) -> None:
        if "const" in rule and candidate != rule["const"]:
            issues.append(f"{current}: value does not match const")

        if "enum" in rule and candidate not in rule["enum"]:
            issues.append(f"{current}: value is outside enum")

        declared_type = rule.get("type")
        if declared_type is not None:
            allowed = [declared_type] if isinstance(declared_type, str) else list(declared_type)
            if not any(type_matches(candidate, item) for item in allowed):
                issues.append(f"{current}: expected type {'|'.join(allowed)}")
                return

        if isinstance(candidate, Mapping):
            properties = rule.get("properties", {})
            required = rule.get("required", [])
            for name in required:
                if name not in candidate:
                    issues.append(f"{current}: missing required property {name!r}")
            if rule.get("additionalProperties") is False:
                for name in candidate:
                    if name not in properties:
                        issues.append(f"{current}: additional property {name!r} is not allowed")
            for name, child_rule in properties.items():
                if name in candidate:
                    walk(candidate[name], child_rule, f"{current}.{name}")

        elif isinstance(candidate, list):
            minimum = rule.get("minItems")
            if isinstance(minimum, int) and len(candidate) < minimum:
                issues.append(f"{current}: requires at least {minimum} item(s)")
            item_rule = rule.get("items")
            if isinstance(item_rule, Mapping):
                for index, item in enumerate(candidate):
                    walk(item, item_rule, f"{current}[{index}]")

        elif isinstance(candidate, str):
            minimum = rule.get("minLength")
            if isinstance(minimum, int) and len(candidate) < minimum:
                issues.append(f"{current}: requires minimum length {minimum}")
            pattern = rule.get("pattern")
            if isinstance(pattern, str) and re.fullmatch(pattern, candidate) is None:
                issues.append(f"{current}: does not match required pattern")
            declared_format = rule.get("format")
            if declared_format == "date-time":
                try:
                    parse_utc(candidate, field=current)
                except ValueError:
                    issues.append(f"{current}: invalid UTC date-time")
            elif declared_format == "date":
                try:
                    datetime.strptime(candidate, "%Y-%m-%d")
                except ValueError:
                    issues.append(f"{current}: invalid date")
            elif declared_format == "sha256":
                if re.fullmatch(r"[0-9a-f]{64}", candidate) is None:
                    issues.append(f"{current}: invalid SHA-256")
            elif declared_format == "uri":
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*:.+", candidate) is None:
                    issues.append(f"{current}: invalid URI")

        minimum = rule.get("minimum")
        if isinstance(minimum, (int, float)) and isinstance(candidate, (int, float)):
            if candidate < minimum:
                issues.append(f"{current}: below minimum {minimum}")

    walk(value, schema, path)
    return sorted(set(issues))

def evaluate_assessment(
    assessment: Mapping[str, Any],
    *,
    assessment_path: str,
    assessment_bytes: bytes,
    evaluated_at: str,
) -> dict[str, Any]:
    """Evaluate one declared assessment deterministically.

    The caller supplies exact committed bytes and an explicit evaluation time.
    The result is advisory and never replaces human review or decision ownership.
    """
    if not isinstance(assessment, Mapping):
        raise TypeError("assessment must be a mapping")
    if not isinstance(assessment_path, str) or not assessment_path.strip():
        raise ValueError("assessment_path must be a non-empty repository-relative path")
    if assessment_path.startswith(("/", "\\")) or ".." in assessment_path.replace("\\", "/").split("/"):
        raise ValueError("assessment_path must remain repository-relative")
    if not isinstance(assessment_bytes, bytes):
        raise TypeError("assessment_bytes must be exact bytes")

    evaluated = parse_utc(evaluated_at, field="evaluated_at")
    findings: list[dict[str, str]] = []

    metadata = _mapping(assessment.get("metadata"))
    assessment_id = metadata.get("assessment_id")
    if not isinstance(assessment_id, str) or not assessment_id.strip():
        assessment_id = "UNDECLARED"

    claim_mode = assessment.get("claim_mode")
    claim_reference = _mapping(assessment.get("claim_reference"))
    declared_mode = claim_reference.get("claim_mode")
    if claim_mode not in CLAIM_MODES or declared_mode != claim_mode:
        findings.append(
            _finding(
                "PI-01",
                "PI-CLAIM-MODE-MISMATCH",
                "BLOCKING",
                "The assessment and claim reference do not declare the same supported claim mode.",
                "claim_mode",
            )
        )

    observations = {item.casefold() for item in _text_items(assessment.get("observation"))}
    inferences = {item.casefold() for item in _text_items(assessment.get("inference"))}
    if observations & inferences:
        findings.append(
            _finding(
                "PI-02",
                "PI-INFERENCE-AS-OBSERVATION",
                "BLOCKING",
                "At least one statement is declared as both observation and inference.",
                "observation",
            )
        )

    findings.extend(_lineage_findings(assessment))

    sources = [_mapping(item) for item in _list(assessment.get("source_lineage"))]
    independent_roots = {
        str(item.get("source_id"))
        for item in sources
        if item.get("relationship") == "PRIMARY" and item.get("parent_id") in (None, "")
    }
    context = _mapping(assessment.get("decision_context"))
    consequence = context.get("consequence")
    reversibility = context.get("reversibility")
    salience = assessment.get("salience")
    high_stakes = consequence in {"MAJOR", "CRITICAL"} or salience == "HIGH"
    if high_stakes and len(independent_roots) < 2:
        findings.append(
            _finding(
                "PI-04",
                "PI-DERIVATIVE-CORROBORATION",
                "BLOCKING",
                "A high-salience or consequential record has fewer than two independent primary roots.",
                "source_lineage",
            )
        )

    if consequence not in CONSEQUENCES or reversibility not in REVERSIBILITY:
        findings.append(
            _finding(
                "PI-09",
                "PI-IRREVERSIBLE-WEAK-EVIDENCE",
                "WARNING",
                "Consequence or reversibility is not declared using the frozen vocabulary.",
                "decision_context",
            )
        )

    assumptions = _text_items(assessment.get("assumptions"))
    if consequence in {"MAJOR", "CRITICAL"} and not assumptions:
        findings.append(
            _finding(
                "PI-05",
                "PI-MATERIAL-ASSUMPTION-MISSING",
                "BLOCKING",
                "A major or critical decision record has no material assumptions.",
                "assumptions",
            )
        )

    alternatives = _text_items(assessment.get("alternative_hypotheses"))
    if claim_mode in {"INFERENCE", "INTERPRETATION", "FORECAST", "RECOMMENDATION"} and not alternatives:
        findings.append(
            _finding(
                "PI-06",
                "PI-ALTERNATIVE-HYPOTHESIS-MISSING",
                "BLOCKING",
                "An inferential claim has no alternative hypothesis.",
                "alternative_hypotheses",
            )
        )

    evidence_state = _mapping(assessment.get("evidence_state"))
    strength = evidence_state.get("strength")
    if salience not in SALIENCE or strength not in EVIDENCE_STRENGTH:
        findings.append(
            _finding(
                "PI-07",
                "PI-SALIENCE-EVIDENCE-MISMATCH",
                "BLOCKING",
                "Salience or evidence strength is not declared using the frozen vocabulary.",
                "evidence_state",
            )
        )
    elif salience == "HIGH" and strength in {"NONE", "WEAK", "LIMITED"}:
        findings.append(
            _finding(
                "PI-07",
                "PI-SALIENCE-EVIDENCE-MISMATCH",
                "BLOCKING",
                "High salience is not supported by the declared evidence strength.",
                "evidence_state.strength",
            )
        )

    expires_at = evidence_state.get("expires_at")
    if isinstance(expires_at, str) and expires_at:
        try:
            if parse_utc(expires_at, field="evidence_state.expires_at") < evaluated:
                findings.append(
                    _finding(
                        "PI-08",
                        "PI-EVIDENCE-EXPIRED",
                        "WARNING",
                        "Controlling evidence was expired at the explicit evaluation time.",
                        "evidence_state.expires_at",
                    )
                )
        except ValueError:
            findings.append(
                _finding(
                    "PI-08",
                    "PI-EVIDENCE-EXPIRED",
                    "WARNING",
                    "Evidence expiration is not a valid explicit UTC timestamp.",
                    "evidence_state.expires_at",
                )
            )

    if (
        consequence == "CRITICAL" or reversibility == "IRREVERSIBLE"
    ) and strength in {"NONE", "WEAK", "LIMITED"}:
        findings.append(
            _finding(
                "PI-09",
                "PI-IRREVERSIBLE-WEAK-EVIDENCE",
                "WARNING",
                "Critical or irreversible action is paired with weak evidence.",
                "decision_context",
            )
        )

    review = _mapping(assessment.get("review_requirements"))
    if review.get("human_review_required") is not True:
        findings.append(
            _finding(
                "PI-10",
                "PI-HUMAN-REVIEW-MISSING",
                "BLOCKING",
                "Human review is not explicitly required.",
                "review_requirements.human_review_required",
            )
        )
    owner = review.get("decision_owner")
    if not isinstance(owner, str) or not owner.strip():
        findings.append(
            _finding(
                "PI-10",
                "PI-DECISION-OWNER-MISSING",
                "BLOCKING",
                "A human decision owner is not declared.",
                "review_requirements.decision_owner",
            )
        )

    conditions = _mapping(assessment.get("decision_conditions"))
    if not _text_items(conditions.get("stop_conditions")):
        findings.append(
            _finding(
                "PI-11",
                "PI-STOP-CONDITION-MISSING",
                "BLOCKING",
                "No explicit stop condition is declared.",
                "decision_conditions.stop_conditions",
            )
        )

    boundary = _mapping(assessment.get("public_boundary"))
    contains_sensitive = boundary.get("contains_sensitive_data") is True
    public_allowed = boundary.get("public_release_allowed") is True
    if contains_sensitive and public_allowed:
        findings.append(
            _finding(
                "PI-12",
                "PI-PUBLIC-BOUNDARY-VIOLATION",
                "CRITICAL",
                "Sensitive content is marked as eligible for public release.",
                "public_boundary",
            )
        )

    findings.sort(
        key=lambda item: (
            SEVERITY_ORDER[item["severity"]],
            item["finding_id"],
            item["related_field"],
        )
    )
    recommendation = _recommendation(findings)
    return {
        "assessment_id": assessment_id,
        "assessment_path": assessment_path,
        "assessment_sha256": sha256_bytes(assessment_bytes),
        "profile_version": PROFILE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "evaluated_at": evaluated_at,
        "findings": findings,
        "recommendation": recommendation,
        "validation_status": "PASS" if not findings else "REVIEW_REQUIRED",
        "human_decision_required": True,
    }
