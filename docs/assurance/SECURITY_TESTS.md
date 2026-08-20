# Security Test Baseline

The public regression suite exercises the controls FIW publicly claims.

Coverage includes:

- unapproved files and paths
- symbolic links and unsafe filesystem entries
- cross-platform path ambiguity
- oversized, binary, bytecode, and nested-archive files
- missing or stale manifests
- workflow permissions and immutable Action references
- common credential patterns
- local user paths
- broken repository links
- synthetic traceability
- deterministic archive membership and byte equality
- output-location enforcement
- source-tree immutability
- offline Frontier Claim Experience behavior and canonical-artifact parity

These tests reduce known repository and release-integrity risks. They do not establish comprehensive security for every environment.
