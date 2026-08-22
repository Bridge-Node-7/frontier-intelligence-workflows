# Validation — v0.5.2

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

The gate checks defined software behavior, approved repository structure, public boundaries, workflow controls, selected source-safety conditions, manifest parity, and deterministic release construction. It does not determine external truth, qualification, readiness, investment merit, or deployment authority.

In strict release validation, every mandatory repository control must report `PASS`; `NOT_RUN` is non-passing.
