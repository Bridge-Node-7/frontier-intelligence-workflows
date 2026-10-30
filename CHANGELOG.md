# Changelog

Notable public changes to Frontier Intelligence Workflows are recorded here.

## [0.9.1](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/compare/v0.9.0...v0.9.1) (2026-10-30)


### Bug Fixes

* normalize FIW validator root path identity (F04) ([c354024](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/c3540249d7b1c3e0c790a2615ebfb3564b4b5f0b))


### Security

* pin reviewed public metadata policy ([#5](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/issues/5)) ([0c4aae5](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/0c4aae51bd38d3d80b67123e4fc8ff4cdcfb4612))
* repin reviewed privacy policy ([9d7bf2c](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/9d7bf2cdeb33f968d5cee9e1a954ebb21e2913e7))


### Documentation

* clarify public README scope ([#4](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/issues/4)) ([7d2c06e](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/7d2c06e1a8b02dca816fc08557ffc8290f4a46dd))
* clarify reviewed source and stable release (#29) ([049c61a](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/049c61aac5ee86f04a84dc95bff85c7bb3840420))
* clarify role in Frontier Assurance architecture (#31) ([16432dd](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/16432ddf76dd646a537a000c3536e61804ac4651))
* simplify release status wording (#30) ([39dcf97](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/39dcf97edb4ac5c2d7b37857a6c751732458d16e))


### CI

* activate immutable privacy preflight with validated release policy ([c7cd091](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/c7cd09153eb2351da47b948a8b4b8e86ceff9280))
* add release-please and repository quality gates ([e8a4e6e](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/e8a4e6ef2fe7a3cb1f5f142650ede8c569b4f80f))
* check privacy on public PR metadata edits ([232e9a2](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/232e9a26e02750e5b28aece3aa7f0e156ff36676))


### Miscellaneous

* **deps:** bump jsonschema from 4.25.1 to 4.26.0 in the validation-dependencies group (#38) ([7eb26ac](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/7eb26aca293dce4df63725c42f2c68c91c46986f))
* **deps:** bump the github-actions group with 2 updates (#39) ([a42c283](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/commit/a42c28306e5036bfe3f33c9ef4244469e4ed0f0b))

## [Unreleased]

- Completed post-v0.9.0 Frontier Signal Integrity terminology cleanup.
- Clarified Frontier Intelligence Workflows' bounded role within the Bridge Node 7 Frontier Assurance architecture.
- Refined public methodology and decision-briefing guidance to surface the supportable disposition, decision criteria, and priority tradeoffs while preserving evidence depth and accountable human decision authority.

## [0.9.0] - 2026-09-19

Current public release.

- Introduce Frontier Signal Integrity as the supported deterministic profile for hypothesis/evidence separation, corroboration integrity, prediction integrity, discriminating tests, update receipts, and reassessment.
- Preserve source genealogy, human-owned consequential decisions, and the boundary that machine validation does not establish external truth.

## [0.8.0] - 2026-09-14

Current public release line.

- Add Source Genealogy as a public-safe deterministic profile for preventing publication multiplicity from masquerading as independent corroboration.
- Model declared roots, derivatives, translations, mirrors, syndication, AI derivatives, coordinated publication, and unknown lineage without crawling the web or authenticating authorship.
- Collapse shared provenance roots, citation dependencies, and declared coordination groups for bounded corroboration counts rather than treating URL count as independent support.
- Preserve retracted, superseded, unavailable, and unknown lineage states; detect circular citation and parent-lineage cycles; and keep accountable human review mandatory.
- Add adversarial regressions for five-URLs/one-root, translation/mirror derivatives, AI summaries, coordinated reposting, retractions/supersession, unavailable sources, unknown genealogy, exaggerated independent-source counts, cycles, deterministic output, and CLI behavior.
- Preserve the boundary that Source Genealogy validates only declared relationships and does not establish external truth, authenticated authorship, qualification, readiness, or decision authority.

## [0.7.0] - 2026-09-13

Current public release.

- Add Language Integrity as a public-safe deterministic companion profile for semantic assurance before deeper decision workflows.
- Add controls and synthetic adversarial fixtures for forecast-as-result corruption, attribution loss, inference-as-direct-support collapse, overstated declared source independence, and superseded information presented as current.
- Preserve FIW v0.6.1 structured-artifact semantic validation, deterministic release integrity, human review, public/private separation, and the boundary that deterministic semantic findings do not establish external truth, canonical knowledge, readiness, or decision authority.

## [0.6.1] - 2026-09-13

Previous public release.

- Validate every policy-approved JSON, YAML, and TOML artifact for syntax before a repository PASS can be reported.
- Validate every `*.schema.json` document against its declared JSON Schema metaschema in addition to FIW's offline structural checks.
- Keep repository diagnostics independent: a hostile-filesystem finding remains blocking without suppressing unrelated public-boundary controls.
- Keep machine-readable validation output optional while surfacing every blocking control directly in terminal output.
- Pin validation-only dependencies and install them in hosted validation/release workflows.
- Preserve Perception Integrity and Frontier Signal Integrity truth boundaries, human decision authority, and the aggressive public file-policy threat model.

## [0.6.0] - 2026-09-11

Earlier public release.

- Add Frontier Signal Integrity — Frontier Signal Integrity as a PI-compatible companion profile.
- Add 12 deterministic FSI controls, FSI-SYN-001 synthetic contested-narrative stress case, FSI-SYN-002 clean frontier-technology case, prediction and Proof Loop structures, adversarial tests, and CLI.

## [0.5.2] - 2026-08-22

Earlier public release.
