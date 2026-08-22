# Perception Integrity

Perception Integrity is a deterministic pre-decision profile within Frontier Intelligence Workflows.

It checks declared evidence conditions and traceability. It does not determine truth, verify whether a source is genuinely independent, or authorize action.

## What It Evaluates

- claim mode
- observation versus inference
- source lineage
- evidence-reference resolution
- derivative versus declared independent corroboration
- assumptions
- alternative hypotheses
- evidence state
- consequence and reversibility
- stop conditions
- public-release boundaries
- decision authority

## Result Semantics

- `NO_FINDINGS` — no configured deterministic PI rule produced a finding from the supplied declared record.
- `REVIEW_REQUIRED` — one or more configured deterministic PI rules produced findings.

`NO_FINDINGS` is not evidence verification and is not a truth determination.

## Use

Keep working evidence outside the public FIW repository.

Start from the intentionally incomplete teaching template:

```bash
mkdir -p ../fiw-work ../fiw-results
cp templates/perception-integrity-starter.json ../fiw-work/assessment.json
python scripts/run_perception_integrity.py \
  --root . \
  --assessment ../fiw-work/assessment.json \
  --evaluated-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --json-output ../fiw-results/validation.json
```

The first run is expected to produce findings. Resolve those findings by improving the declared record and rerun the assessment.

`templates/perception-integrity-assessment.json` remains a known-valid synthetic assessment for regression and advanced adopter reference.

The intentionally incomplete starter is expected to return `REVIEW_REQUIRED` and exit with code `1` on the first run; this is the teaching path, not a tool failure.

External assessment paths are represented using a sanitized external identifier rather than the original absolute path.

## Control Scenarios

[Perception Integrity Control Scenarios](CONTROL_EXAMPLES.md) gives one concise synthetic trigger for each of the twelve deterministic controls.

## Public Examples

The included examples are fictional:

- `FIW-SYN-002` — derivative repetition is not independent corroboration
- `FIW-SYN-003` — irreversible decisions with weak evidence require escalation
- `FIW-SYN-004` — incomplete decision conditions require additional evidence

The profile produces deterministic findings and bounded recommendations. Human decision authority remains required for consequential action.

## Comparison Boundary

Bounded text normalization handles Unicode compatibility forms, formatting controls used by the comparison function, whitespace, case, and terminal punctuation for duplicate observation/inference detection. It does not comprehensively detect visually confusable homoglyphs.
