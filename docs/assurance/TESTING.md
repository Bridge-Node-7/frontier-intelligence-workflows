# Validation — v0.5.1

FIW validation is reproducible from a clean checkout.

## Complete Gate

```bash
mkdir -p ../fiw-validation ../fiw-release
python scripts/run_tests.py --root . --json-output ../fiw-validation/source-test-summary.json
python scripts/compile_sources.py --root .
python scripts/validate_repo.py --root . --json-output ../fiw-validation/validation-report.json
python scripts/build_release.py --root . --output-dir ../fiw-release --check --commit "$(git rev-parse HEAD)"
sha256sum -c MANIFEST.sha256
git diff --check
```

Validation output belongs outside the repository source tree.

## Evidence Hierarchy

### Source Correctness

- Python source compilation
- complete regression suite
- v0.5 adversarial regressions

### Repository Correctness

- exact file policy
- tracked-path coverage when Git metadata is available
- public/private boundary
- link and version consistency
- selected secret, path, and source-text safety checks across public code/configuration/Markdown surfaces
- deterministic relative-link resolution with exact published path case/normalization enforcement

### Integrity

- manifest parity
- strict release validation
- every mandatory repository control reports `PASS`; `NOT_RUN` is non-passing

### Reproducibility

- deterministic archive membership
- deterministic archive bytes
- archive checksum verification

The gate checks defined software and repository properties. It does not determine external truth, qualification, readiness, investment merit, or deployment authority.

The fixed 1980 timestamp in deterministic metadata is a reproducibility sentinel, not provenance time.
