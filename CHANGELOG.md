# Changelog

Notable public changes to Frontier Intelligence Workflows are recorded here.

## [Unreleased]

_No unreleased changes._

## [0.6.1] - 2026-09-13

Current public release.

- Validate every policy-approved JSON, YAML, and TOML artifact for syntax before a repository PASS can be reported.
- Validate every `*.schema.json` document against its declared JSON Schema metaschema in addition to FIW's offline structural checks.
- Keep repository diagnostics independent: a hostile-filesystem finding remains blocking without suppressing unrelated public-boundary controls.
- Keep machine-readable validation output optional while surfacing every blocking control directly in terminal output.
- Pin validation-only dependencies and install them in hosted validation/release workflows.
- Preserve Perception Integrity and Radiant Guardian truth boundaries, human decision authority, and the aggressive public file-policy threat model.

## [0.6.0] - 2026-09-11

Current public release.

- Add Radiant Guardian — Frontier Signal Integrity as a PI-compatible companion profile.
- Add 12 deterministic RG controls, RG-SYN-001 synthetic contested-narrative stress case, RG-SYN-002 clean frontier-technology case, prediction and Proof Loop structures, adversarial tests, and CLI.

## [0.5.2] - 2026-08-22

Previous public release.
