# Validation — v0.4.1

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

The gate checks repository policy, tracked-path coverage, portable paths, workflow controls, common secret patterns, local user paths, public boundaries, synthetic traceability, manifests, and deterministic release construction.

A passing result applies only to the controls executed.
