# Frontier Intelligence Workflows

**Turn uncertain technical claims into evidence-backed decisions.**

Frontier Intelligence Workflows (FIW) is an open, evidence-first framework for tracing claims to their sources, separating observation from inference, exposing contradictions and unknowns, and defining the evidence needed before a decision can responsibly move forward.

**Automation checks structure and declared evidence conditions. It does not determine truth or authorize action.**

## Core Workflow

```text
Decision
  ↓
Claim
  ↓
Evidence
  ↓
Provenance
  ↓
Challenge
  ↓
Unknown
  ↓
Next Evidence
  ↓
Judgment
```

## Explore

### Frontier Claim Experience

The [Frontier Claim Experience](examples/frontier-claim-experience/) demonstrates a common intelligence problem: several reports appear to corroborate a claim, but tracing their origins reveals that they share a single provenance root.

**Independent corroboration is not established.**

That does not mean the underlying claim is false. It means the cited reports do not independently establish it.

### Perception Integrity

[Perception Integrity](profiles/perception-integrity/) provides deterministic checks for evidence lineage, observation-versus-inference separation, assumptions, alternative hypotheses, evidence state, stop conditions, public-release boundaries, and decision authority.

### Synthetic Component Readiness

[FIW-SYN-001](examples/synthetic-component-readiness/) shows a complete evidence-to-decision artifact chain using fictional data.

## Use FIW

Keep nonpublic working evidence outside this public repository.

A working assessment can be evaluated from an external location without committing it to FIW:

```bash
mkdir -p ../fiw-work ../fiw-results
cp templates/perception-integrity-assessment.json ../fiw-work/assessment.json

python scripts/run_perception_integrity.py \
  --root . \
  --assessment ../fiw-work/assessment.json \
  --evaluated-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --json-output ../fiw-results/validation.json
```

External assessments are represented with a sanitized external identifier rather than their absolute source path.

## Public Assurance

FIW includes:

- SHA-256 manifests
- deterministic source packages
- full-SHA GitHub Actions dependencies
- bounded workflow permissions
- disabled checkout credential persistence
- portable-path and unsafe-filesystem checks
- common secret-pattern and local-path scanning
- synthetic traceability checks
- offline, no-network Frontier Claim Experience regression controls

Run the complete repository gate:

```bash
mkdir -p ../fiw-validation ../fiw-release
python scripts/run_tests.py --root . --json-output ../fiw-validation/source-test-summary.json
python scripts/compile_sources.py --root .
python scripts/validate_repo.py --root . --json-output ../fiw-validation/validation-report.json
python scripts/build_release.py --root . --output-dir ../fiw-release --check --commit "$(git rev-parse HEAD)"
sha256sum -c MANIFEST.sha256
git diff --check
```

A passing control establishes only what that control tests.

## Public Boundary

FIW is designed for public-safe methods, synthetic examples, and inspectable assurance controls.

Do not place nonpublic, confidential, proprietary, credential, controlled, or operationally sensitive material in this public repository.

FIW does not certify scientific truth, technical performance, supplier qualification, production readiness, safety, regulatory approval, legal compliance, investment merit, or deployment authority.

## Security

Use GitHub private vulnerability reporting for security issues. Do not disclose sensitive security details through public repository surfaces.

See [Security](SECURITY.md) and [Limitations](LIMITATIONS.md).

## License

Repository code and documentation are available under the [MIT License](LICENSE).

Use of this repository does not imply Bridge Node 7 endorsement, certification, qualification, partnership, or approval.

Published by [Bridge Node 7](https://bridgenode7.com/).

## Release

**v0.4.1 — Repository Refinement**

This release presents FIW as a smaller, clearer public product while preserving the evidence model, examples, deterministic controls, validation tooling, and release integrity.
