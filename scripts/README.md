# Repository Tooling

- `run_perception_integrity.py` evaluates one assessment against the public Perception Integrity contract. It does not authorize action.
- `perception_integrity.py` implements deterministic profile rules and schema validation.
- `run_tests.py` runs the repository regression suite.
- `compile_sources.py` verifies Python source syntax without creating bytecode.
- `validate_repo.py` validates repository structure, public boundaries, workflow controls, traceability, and manifests.
- `build_release.py` creates deterministic source-release evidence outside the repository.
- `refresh_release_metadata.py` refreshes committed manifests after approved source changes.
- `release_common.py` provides shared release-integrity functions.

The tooling uses only the Python standard library.
