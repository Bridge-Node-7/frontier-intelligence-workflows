# Limitations

Current release: `0.5.0`.

Frontier Intelligence Workflows is an evidence and integrity framework, not a universal verification system.

## Status Semantics

Perception Integrity uses `NO_FINDINGS` and `REVIEW_REQUIRED`.

`NO_FINDINGS` means only that no configured deterministic PI rule produced a finding from the supplied declared record. It does not establish that the declarations are accurate or that the underlying evidence or claim is true.

Repository and release controls use `PASS`, `FAIL`, and `NOT_RUN`. A `PASS` means that the named machine control executed and satisfied its defined assertion. `NOT_RUN` is non-passing in strict release validation.

## Automation Can Check

- declared structure and required fields
- source-lineage relationships and dangling evidence references
- bounded observation/inference overlap conditions
- declared evidence state, decision context, and stop conditions
- internal repository links
- exact release-version markers
- selected common credential patterns
- local user paths
- selected deceptive Unicode controls on public code, configuration, and Markdown surfaces
- workflow pinning and permissions
- synthetic example traceability
- manifest integrity
- deterministic release construction

## Automation Cannot Establish

- scientific truth
- whether a source is genuinely independent merely because it is declared independent
- technical performance
- supplier qualification
- production readiness
- safety
- legal compliance
- regulatory approval
- investment merit
- operational authorization

## Decision-Ready Intelligence Limitation

Decision-ready intelligence structures what the supplied evidence supports, what remains unresolved, and what evidence may be worth obtaining next. It does not inherit the authority of an investor, executive, engineer, regulator, acquisition official, safety authority, or other accountable decision owner.

## Evidence Limitation

A structurally complete record can still contain weak, biased, incomplete, stale, incorrect, or strategically misdeclared evidence.

Source quality, method, scope, contradictory evidence, independence, and reproducibility still require appropriate judgment and, where consequential, independent technical validation.

## Scanner Limitation

The repository scanner covers selected high-signal credential and source-deception patterns. It is not a complete data-loss-prevention, malware-detection, or Unicode-confusables system. Compatibility normalization does not comprehensively identify visually confusable homoglyphs.

## Scale Limitation

Perception Integrity lineage validation is designed for bounded decision records, not massive graph workloads. Large-scale relationship analysis should use a purpose-built graph/data layer if real use cases earn that requirement.

## Synthetic Examples

FIW public examples are fictional and demonstrate process only. They do not evaluate or endorse real organizations, suppliers, technologies, products, or people.

## Release Integrity

A valid manifest or deterministic archive establishes integrity against recorded bytes. It does not establish that the underlying content is true, who authored the bytes, or that the build carries cryptographic provenance attestation.

The fixed `1980-01-01T00:00:00Z` archive/manifest timestamp is a reproducibility sentinel. It is not an authorship, build, publication, or evidence timestamp.
