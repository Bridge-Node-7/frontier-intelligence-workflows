# Limitations

Current release: `0.8.0`.

Frontier Intelligence Workflows is an evidence and integrity framework, not a universal verification system.

## Status Semantics

Perception Integrity and Language Integrity use `NO_FINDINGS` and `REVIEW_REQUIRED` for their respective configured deterministic findings.

`NO_FINDINGS` means only that no configured deterministic rule in the applicable profile produced a finding from the supplied declared record. It does not establish that the declarations are accurate or that the underlying evidence or claim is true.

Repository and release controls use `PASS`, `FAIL`, and `NOT_RUN`. A `PASS` means the named control executed and satisfied its defined assertion. `NOT_RUN` is non-passing in strict release validation.

## Automation Can Check

FIW automation can check declared structure, traceability, selected language-integrity conditions, selected evidence conditions, repository integrity, approved public structure, selected credential and path patterns, workflow controls, links, manifests, and deterministic release construction.

## Automation Cannot Establish

FIW automation cannot establish scientific truth, real-world source independence, technical performance, supplier qualification, production readiness, safety, legal or regulatory approval, investment merit, or operational authorization.

## Evidence Limitation

A structurally complete record can still contain weak, biased, incomplete, stale, incorrect, or misdeclared evidence. Source quality, method, scope, contradictory evidence, independence, and reproducibility still require appropriate judgment and, where consequential, independent validation.

Language Integrity evaluates declared semantic relationships in the bounded record. It does not authenticate a source, run a production NLP extractor, convert candidate language into canonical knowledge, or authorize a consequential decision.

## Synthetic Examples

FIW public examples are fictional and demonstrate process only. They do not evaluate or endorse real organizations, suppliers, technologies, products, or people.

## Release Integrity

A valid manifest or deterministic archive establishes consistency against recorded bytes. It does not establish that the content is true, fit for a particular use, or authored by a particular party.
