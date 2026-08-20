# Perception Integrity

Perception Integrity is a deterministic pre-decision profile within Frontier Intelligence Workflows.

It checks declared evidence conditions. It does not determine truth or authorize action.

## What It Evaluates

- claim mode
- observation versus inference
- source lineage
- derivative versus independent corroboration
- assumptions
- alternative hypotheses
- evidence state
- consequence and reversibility
- stop conditions
- public-release boundaries
- decision authority

## Use

Keep working evidence outside the public FIW repository.

```bash
mkdir -p ../fiw-work ../fiw-results
cp templates/perception-integrity-assessment.json ../fiw-work/assessment.json
python scripts/run_perception_integrity.py   --root .   --assessment ../fiw-work/assessment.json   --evaluated-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"   --json-output ../fiw-results/validation.json
```

External assessment paths are represented using a sanitized external identifier rather than the original absolute path.

## Public Examples

The included examples are fictional:

- `FIW-SYN-002` — derivative repetition is not independent corroboration
- `FIW-SYN-003` — irreversible decisions with weak evidence require escalation
- `FIW-SYN-004` — incomplete decision conditions require additional evidence

The profile produces deterministic findings and bounded recommendations. Human decision authority remains required for consequential action.
