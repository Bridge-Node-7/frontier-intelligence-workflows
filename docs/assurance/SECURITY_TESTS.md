# Security Test Baseline

The public regression suite exercises the controls FIW publicly claims.

Coverage includes:

- unapproved files and paths
- symbolic links and unsafe filesystem entries
- cross-platform path ambiguity
- oversized, binary, bytecode, and nested-archive files
- missing or stale manifests
- workflow permissions and immutable Action references
- selected common credential patterns, including bounded bearer/basic-auth forms
- path-scoped synthetic secret-fixture handling
- local user paths
- selected Trojan Source / invisible Unicode controls on code and configuration surfaces
- broken repository links using portable path semantics
- exact release-version markers
- synthetic traceability
- evidence-reference resolution
- critical/irreversible insufficient-evidence handling
- deterministic archive membership and byte equality
- output-location enforcement
- source-tree immutability
- offline Frontier Claim Experience behavior and canonical-artifact parity

These tests reduce known repository and release-integrity risks. They do not establish comprehensive security, data-loss prevention, semantic truth, or Unicode-confusable coverage for every environment.
