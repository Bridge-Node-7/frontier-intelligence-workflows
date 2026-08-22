# Changelog

Notable public changes to Frontier Intelligence Workflows are recorded here.

## [Unreleased]

_No unreleased changes._

## [0.5.0] - 2026-08-22

### Added

- explicit repository-control states: `PASS`, `FAIL`, and `NOT_RUN`
- intentionally incomplete Perception Integrity starter assessment for first-run learning
- public source-text safety checks for deceptive bidirectional and selected invisible formatting characters across code, configuration, and Markdown surfaces
- evidence-reference resolution against declared source lineage
- bounded additional secret-pattern coverage
- FIW Decision Record v0.5 as a candidate common decision contract
- FIW-SYN-005, a fully fictional Frontier Technology Diligence case
- deterministic adversarial regressions for the v0.5 trust-semantics corrections
- explicit status-semantics documentation and CLI result contract

### Changed

- Perception Integrity `validation_status` from `PASS` to `NO_FINDINGS` when no configured deterministic finding is produced
- PI Profile from `0.3.0` to `0.4.0`
- PI Validator from `0.3.0` to `0.4.0`
- PI Ruleset from `1.1.0` to `1.2.0`
- critical + irreversible + weak/limited/no-evidence records now fail closed to `HOLD`
- observation/inference overlap comparison now normalizes compatibility forms and terminal punctuation for bounded duplicate detection
- metadata refresh now compiles and runs the full regression suite before writing manifests
- version consistency checks now use exact release markers rather than unanchored substring matching
- public assurance narrative now leads with behavioral tests before byte-integrity controls
- FIW positioning sharpened toward decision-ready intelligence for uncertain frontier-technology claims
- clarified FIW's modular relationship to domain evidence and the Frontier Decision Engine
- Frontier Claim Experience interactive control contrast, print treatment, and system-font declaration refined

### Security

- secret-test exemptions are path-scoped to the top-level `tests/` tree rather than globally marker-scoped
- selected Trojan Source / invisible formatting controls are rejected on code and configuration surfaces
- manifest checksum text participates in repository text scanning
- relative Markdown path case/normalization mismatches are surfaced rather than silently accepted
- additional bounded secret patterns cover private-key, SendGrid, Twilio API-key, and Azure storage-key forms

### Migration

- **Breaking PI output change:** consumers checking `validation_status == "PASS"` must migrate to `validation_status == "NO_FINDINGS"`; `REVIEW_REQUIRED` is unchanged.

### Boundaries

- `NO_FINDINGS` does not mean evidence verified or a claim proven
- source independence remains declared and analyst-established rather than automatically discovered
- manifests establish internal byte consistency, not authorship or cryptographic build provenance
- accountable people retain consequential decision authority

## [0.4.1] - 2026-08-20

### Changed

- streamlined repository documentation and navigation
- tightened the release file policy to approved public artifacts
- clarified external assessment handling and public-release boundaries
- improved Frontier Claim Experience release labeling, reduced-motion behavior, and visible validation feedback
- simplified deterministic release evidence around user-verifiable integrity outputs

### Security

- retained pinned workflows, bounded permissions, deterministic packaging, secret-pattern scanning, local-path scanning, unsafe-file rejection, and public traceability controls

## [0.4.0] - 2026-08-19

### Added

- Frontier Claim Experience
- canonical synthetic case artifact with embedded-interface parity checks
- provenance tracing from three cited reports to one provenance root
- scoped decision recording and decision-relevant missing-evidence guidance

## [0.3.0] - 2026-08-08

### Added

- Perception Integrity command-line evaluation
- reusable assessment template
- deterministic evidence and decision-condition checks

## [0.2.0] - 2026-08-08

### Added

- Perception Integrity profile
- strict schemas
- synthetic conformance cases
- deterministic evidence-lineage and public-boundary controls

## [0.1.x]

Established the public FIW foundation, synthetic evidence workflow, deterministic release tooling, manifests, portable-path controls, and pinned validation workflows.
