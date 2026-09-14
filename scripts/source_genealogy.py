#!/usr/bin/env python3
"""Deterministic source-genealogy analysis for Frontier Intelligence Workflows.

The evaluator reasons only over declared provenance relationships. It does not
crawl the web, authenticate a publisher, determine external truth, or decide
whether evidence is sufficient for a consequential action.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

sys.dont_write_bytecode = True

PROFILE_VERSION = "0.8.0"
RULESET_VERSION = "1.0.0"

RELATIONS = {
    "ROOT",
    "DERIVATIVE",
    "TRANSLATION",
    "MIRROR",
    "SYNDICATED",
    "AI_DERIVATIVE",
    "COORDINATED_PUBLICATION",
    "UNKNOWN",
}
DERIVATIVE_RELATIONS = RELATIONS - {"ROOT", "UNKNOWN"}
TEMPORAL_STATES = {"CURRENT", "SUPERSEDED", "RETRACTED", "UNAVAILABLE"}
DEGRADED_STATES = {"SUPERSEDED", "RETRACTED", "UNAVAILABLE"}
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


class _UnionFind:
    def __init__(self, values: list[str]):
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        a = self.find(left)
        b = self.find(right)
        if a == b:
            return
        canonical, other = sorted((a, b))
        self.parent[other] = canonical


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
    records = [_mapping(item) for item in _list(case.get("sources"))]
    findings: list[dict[str, str]] = []
    source_by_id: dict[str, Mapping[str, Any]] = {}

    for record in records:
        source_id = record.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            findings.append(_finding("SG-00", "SG-SOURCE-ID-MISSING", "Every source requires a non-empty source_id.", "sources[].source_id"))
            continue
        if source_id in source_by_id:
            findings.append(_finding("SG-00", "SG-DUPLICATE-SOURCE-ID", f"Duplicate source_id {source_id!r}.", "sources[].source_id"))
            continue
        source_by_id[source_id] = record

    root_cache: dict[str, str | None] = {}
    cycle_nodes: set[str] = set()

    def root_for(source_id: str, trail: tuple[str, ...] = ()) -> str | None:
        if source_id in root_cache:
            return root_cache[source_id]
        if source_id in trail:
            start = trail.index(source_id)
            cycle_nodes.update(trail[start:] + (source_id,))
            return None
        record = source_by_id.get(source_id)
        if record is None:
            return None
        relation = record.get("relation")
        if relation == "ROOT":
            root_cache[source_id] = source_id
            return source_id
        if relation == "UNKNOWN":
            root_cache[source_id] = None
            return None
        if relation not in DERIVATIVE_RELATIONS:
            root_cache[source_id] = None
            return None
        parent = record.get("parent_source_id")
        if not isinstance(parent, str) or not parent or parent not in source_by_id:
            root_cache[source_id] = None
            return None
        resolved = root_for(parent, trail + (source_id,))
        root_cache[source_id] = resolved
        return resolved

    for source_id, record in source_by_id.items():
        relation = record.get("relation")
        temporal = record.get("temporal_status")
        accessible = record.get("accessible")
        parent = record.get("parent_source_id")

        if relation not in RELATIONS:
            findings.append(_finding("SG-01", "SG-RELATION-INVALID", f"Source {source_id!r} has unsupported relation {relation!r}.", "sources[].relation"))
        elif relation in DERIVATIVE_RELATIONS and (not isinstance(parent, str) or not parent):
            findings.append(_finding("SG-01", "SG-PARENT-MISSING", f"{relation} source {source_id!r} must name parent_source_id.", "sources[].parent_source_id"))
        elif relation in DERIVATIVE_RELATIONS and parent not in source_by_id:
            findings.append(_finding("SG-01", "SG-PARENT-UNRESOLVED", f"Source {source_id!r} names undeclared parent {parent!r}.", "sources[].parent_source_id"))
        elif relation == "ROOT" and parent not in {None, ""}:
            findings.append(_finding("SG-01", "SG-ROOT-HAS-PARENT", f"ROOT source {source_id!r} must not name a parent.", "sources[].parent_source_id"))
        elif relation == "UNKNOWN":
            findings.append(_finding("SG-02", "SG-LINEAGE-UNKNOWN", f"Source {source_id!r} has unknown lineage and cannot establish independent corroboration.", "sources[].relation", "WARNING"))

        if temporal not in TEMPORAL_STATES:
            findings.append(_finding("SG-03", "SG-TEMPORAL-STATE-INVALID", f"Source {source_id!r} has unsupported temporal_status {temporal!r}.", "sources[].temporal_status"))
        if temporal == "UNAVAILABLE" and accessible is True:
            findings.append(_finding("SG-03", "SG-ACCESSIBILITY-CONTRADICTION", f"Source {source_id!r} is declared UNAVAILABLE but accessible=true.", "sources[].accessible"))
        if accessible not in {True, False}:
            findings.append(_finding("SG-03", "SG-ACCESSIBILITY-UNDECLARED", f"Source {source_id!r} must explicitly declare accessible true or false.", "sources[].accessible", "WARNING"))
        if temporal == "SUPERSEDED":
            successor = record.get("superseded_by")
            if not isinstance(successor, str) or not successor or successor not in source_by_id:
                findings.append(_finding("SG-03", "SG-SUPERSESSION-INCOMPLETE", f"Superseded source {source_id!r} must name a declared successor.", "sources[].superseded_by"))

        root_for(source_id)

    if cycle_nodes:
        findings.append(_finding(
            "SG-01",
            "SG-DERIVATION-CYCLE",
            "Parent-source lineage contains a cycle: " + ", ".join(sorted(cycle_nodes)) + ".",
            "sources[].parent_source_id",
        ))

    resolved_roots = sorted({root for root in root_cache.values() if root is not None})
    uf = _UnionFind(resolved_roots)
    citation_edges: list[tuple[str, str]] = []
    citation_graph: dict[str, set[str]] = defaultdict(set)

    for source_id, record in source_by_id.items():
        source_root = root_for(source_id)
        for cited in _list(record.get("cites")):
            if not isinstance(cited, str) or not cited:
                continue
            if cited not in source_by_id:
                findings.append(_finding("SG-04", "SG-CITATION-UNRESOLVED", f"Source {source_id!r} cites undeclared source {cited!r}.", "sources[].cites"))
                continue
            citation_graph[source_id].add(cited)
            cited_root = root_for(cited)
            if source_root and cited_root and source_root != cited_root:
                uf.union(source_root, cited_root)
                citation_edges.append((source_id, cited))

    # Any directed citation cycle is visible and cannot manufacture corroboration.
    citation_cycle_nodes: set[str] = set()

    def walk_citations(node: str, stack: tuple[str, ...], done: set[str]) -> None:
        if node in stack:
            start = stack.index(node)
            citation_cycle_nodes.update(stack[start:] + (node,))
            return
        if node in done:
            return
        for neighbor in citation_graph.get(node, set()):
            walk_citations(neighbor, stack + (node,), done)
        done.add(node)

    done: set[str] = set()
    for source_id in source_by_id:
        walk_citations(source_id, (), done)
    if citation_cycle_nodes:
        findings.append(_finding(
            "SG-04",
            "SG-CIRCULAR-CITATION",
            "Circular citation is present and does not create independent corroboration: " + ", ".join(sorted(citation_cycle_nodes)) + ".",
            "sources[].cites",
            "WARNING",
        ))

    coordination_groups: dict[str, list[str]] = defaultdict(list)
    for source_id, record in source_by_id.items():
        group = record.get("coordination_group")
        root = root_for(source_id)
        if isinstance(group, str) and group and root:
            coordination_groups[group].append(root)
    for roots in coordination_groups.values():
        unique = sorted(set(roots))
        for root in unique[1:]:
            uf.union(unique[0], root)

    cited_ids = [value for value in _list(claim.get("source_ids")) if isinstance(value, str) and value]
    unresolved_claim_sources = sorted(set(cited_ids) - set(source_by_id))
    if unresolved_claim_sources:
        findings.append(_finding("SG-00", "SG-CLAIM-SOURCE-UNRESOLVED", "Claim cites undeclared sources: " + ", ".join(unresolved_claim_sources) + ".", "claim.source_ids"))

    cited_records = [source_by_id[source_id] for source_id in cited_ids if source_id in source_by_id]
    cited_roots = {root_for(source_id) for source_id in cited_ids if source_id in source_by_id}
    cited_roots.discard(None)

    degraded_roots = {
        root
        for root in cited_roots
        if source_by_id.get(root, {}).get("temporal_status") in DEGRADED_STATES
        or source_by_id.get(root, {}).get("accessible") is not True
    }
    for source_id in cited_ids:
        record = source_by_id.get(source_id)
        if record is None:
            continue
        temporal = record.get("temporal_status")
        if temporal == "RETRACTED":
            findings.append(_finding("SG-05", "SG-RETRACTED-SUPPORT", f"Claim cites retracted source {source_id!r}.", "claim.source_ids"))
        elif temporal == "SUPERSEDED":
            findings.append(_finding("SG-05", "SG-SUPERSEDED-SUPPORT", f"Claim cites superseded source {source_id!r}; preserve it as history, not current corroboration.", "claim.source_ids", "WARNING"))
        elif temporal == "UNAVAILABLE":
            findings.append(_finding("SG-05", "SG-UNAVAILABLE-SUPPORT", f"Claim cites unavailable source {source_id!r}; last-known provenance is retained without asserting current accessibility.", "claim.source_ids", "WARNING"))

    eligible_roots = sorted(root for root in cited_roots if root not in degraded_roots)
    eligible_groups = sorted({uf.find(root) for root in eligible_roots}) if eligible_roots else []
    declared_count = claim.get("declared_independent_source_count")
    if not isinstance(declared_count, int) or isinstance(declared_count, bool) or declared_count < 0:
        findings.append(_finding("SG-06", "SG-INDEPENDENCE-COUNT-INVALID", "Claim must declare a non-negative integer independent-source count.", "claim.declared_independent_source_count"))
    elif declared_count != len(eligible_groups):
        finding_id = "SG-INDEPENDENCE-OVERSTATED" if declared_count > len(eligible_groups) else "SG-INDEPENDENCE-COUNT-MISMATCH"
        findings.append(_finding(
            "SG-06",
            finding_id,
            f"Declared independent-source count {declared_count} does not equal the {len(eligible_groups)} eligible provenance group(s) derived from declared genealogy.",
            "claim.declared_independent_source_count",
        ))

    public_boundary = _mapping(case.get("public_boundary"))
    if metadata.get("synthetic") is not True or public_boundary.get("contains_sensitive_data") is not False or public_boundary.get("public_release_allowed") is not True:
        findings.append(_finding("SG-07", "SG-PUBLIC-BOUNDARY-VIOLATION", "The public Source Genealogy profile accepts only synthetic, nonsensitive, public-release-allowed cases.", "public_boundary"))

    review = _mapping(case.get("review_requirements"))
    if review.get("human_review_required") is not True or not isinstance(review.get("decision_owner"), str) or not str(review.get("decision_owner")).strip():
        findings.append(_finding("SG-08", "SG-HUMAN-REVIEW-MISSING", "Human review and an accountable decision owner are required.", "review_requirements"))

    group_members: dict[str, set[str]] = defaultdict(set)
    for root in resolved_roots:
        group_members[uf.find(root)].add(root)

    source_states = []
    for source_id in sorted(source_by_id):
        record = source_by_id[source_id]
        root = root_for(source_id)
        source_states.append({
            "source_id": source_id,
            "relation": record.get("relation"),
            "root_source_id": root,
            "temporal_status": record.get("temporal_status"),
            "accessible": record.get("accessible"),
            "corroboration_eligible": bool(
                root
                and record.get("temporal_status") == "CURRENT"
                and record.get("accessible") is True
                and root not in degraded_roots
            ),
        })

    findings.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 99), item["control_id"], item["finding_id"], item["message"]))
    status = "NO_FINDINGS" if not findings else "REVIEW_REQUIRED"
    recommendation = "READY_FOR_HUMAN_REVIEW" if not findings else "REQUIRE_CORROBORATION"
    return {
        "profile": "SOURCE_GENEALOGY",
        "profile_version": PROFILE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "case_id": metadata.get("case_id", "UNDECLARED"),
        "case_path": normalized_path,
        "case_sha256": sha256_bytes(case_bytes),
        "declared_source_count": len(cited_records),
        "derived_provenance_roots": sorted(cited_roots),
        "eligible_independent_groups": eligible_groups,
        "derived_independent_source_count": len(eligible_groups),
        "genealogy_groups": [
            {"group_id": group, "root_source_ids": sorted(members)}
            for group, members in sorted(group_members.items())
        ],
        "citation_dependency_edges": [list(edge) for edge in sorted(set(citation_edges))],
        "source_states": source_states,
        "status": status,
        "recommendation": recommendation,
        "findings": findings,
        "human_review_required": True,
        "non_claim": "Genealogy analysis preserves declared provenance relationships; it does not establish external truth, authenticated authorship, real-world independence, or decision authority.",
    }
