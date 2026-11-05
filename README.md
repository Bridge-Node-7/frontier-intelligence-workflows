# Frontier Intelligence Workflows

**Turn uncertain frontier-technology claims into decision-ready intelligence.**

Frontier Intelligence Workflows (FIW) is an open, evidence-first method for consequential technology questions. It traces claims to sources, separates observation from inference, exposes contradictions and unknowns, and records the evidence needed before a decision moves forward.

[Latest release](https://github.com/Bridge-Node-7/frontier-intelligence-workflows/releases/latest) · Quickstart below · [Partner](https://bridgenode7.com/partner/)

Automation checks structure, traceability, and declared evidence conditions. It does not determine truth, verify the underlying claim, make investment decisions, certify readiness, or authorize action.

## Core workflow

```text
Decision Question
  → Claims → Evidence → Provenance
  → Contradictions / Challenges
  → Knowns · Unknowns → Assumptions
  → Assessment → Decision Boundary
  → Next Evidence → Accountable Human
```

## Decision artifacts

- [FIW Decision Record](templates/decision-record.md) — portable record for a bounded assessment: context, claims, evidence, provenance, uncertainty, decision boundary, next evidence, accountable owner, and rationale.
- [Decision-Ready Brief](templates/decision-ready-brief.md) — human-facing handoff: supportable disposition or next move, strongest countercase, decision hinge, criteria and tradeoffs, minimum sufficient commitment, material unknowns, stop conditions, and reconsideration triggers. Advisory preparation; the accountable human decides.

Real case inputs and generated results remain in the authorized working environment unless explicitly approved for public release.

## Explore

| Path | What it shows |
|---|---|
| [Frontier Claim Experience](examples/frontier-claim-experience/) | Local-first synthetic example: apparent corroboration that shares one provenance root |
| [Frontier Technology Diligence](examples/frontier-technology-diligence/) | Fictional diligence scenario: repeated reporting vs independent corroboration |
| [Perception Integrity](profiles/perception-integrity/) | Deterministic checks for declared lineage, observation vs inference, assumptions, stop conditions, and decision authority |
| [Language Integrity](profiles/language-integrity/) | Preserves declared source meaning: forecast vs result, attribution, inference labeling, provenance-root collapse, supersession |
| [Source Genealogy](profiles/source-genealogy/) | Collapses declared derivatives, mirrors, translations, syndication, and coordinated publication to provenance roots |
| [Frontier Signal Integrity](profiles/frontier-signal-integrity/) | Frontier-signal genealogy, surprise hypotheses, prediction integrity, discriminating tests, update receipts, Proof Loop reassessment |
| [FIW-SYN-001 — Synthetic Component Readiness](examples/synthetic-component-readiness/) | Complete evidence-to-decision artifact chain using fictional data |

## Status semantics

- **Perception / Language Integrity:** `NO_FINDINGS` / `REVIEW_REQUIRED` describe configured deterministic findings in the declared assessment.
- **Repository controls:** `PASS` / `FAIL` / `NOT_RUN` describe whether a named machine control executed and satisfied its assertion.

See [Status Semantics](docs/assurance/STATUS_SEMANTICS.md).

## Use FIW

Use a separate working directory in the environment authorized for assessment inputs and generated results.

### macOS, Linux, or Git Bash

```bash
mkdir -p ../fiw-work ../fiw-results
cp templates/perception-integrity-starter.json ../fiw-work/assessment.json

python scripts/run_perception_integrity.py \
  --root . \
  --assessment ../fiw-work/assessment.json \
  --evaluated-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --json-output ../fiw-results/validation.json
```

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force ../fiw-work, ../fiw-results | Out-Null
Copy-Item templates/perception-integrity-starter.json ../fiw-work/assessment.json
$evaluatedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

python scripts/run_perception_integrity.py `
  --root . `
  --assessment ../fiw-work/assessment.json `
  --evaluated-at $evaluatedAt `
  --json-output ../fiw-results/validation.json
```

The first run is expected to produce findings and exit with code `1`. Improve the declared record and rerun. Preserve prior artifacts when reassessment is needed.

### CLI result contract

- Exit `0`: `READY_FOR_HUMAN_REVIEW`
- Exit `1`: deterministic findings require action before ordinary review
- Exit `2`: input, path, or output handling error
- Exit `3`: assessment fails the bounded schema contract

## Verification

Use `python3` (3.11+). Keep the virtualenv **outside** the clone.

```bash
python3 -m venv ../fiw-validation-venv
source ../fiw-validation-venv/bin/activate  # Windows PowerShell: ..\fiw-validation-venv\Scripts\Activate.ps1
python3 -m pip install -r requirements-validation.txt
mkdir -p ../fiw-validation ../fiw-release
python3 scripts/run_tests.py --root . --json-output ../fiw-validation/source-test-summary.json
python3 scripts/compile_sources.py --root .
python3 scripts/validate_repo.py --root . --json-output ../fiw-validation/validation-report.json
python3 scripts/build_release.py --root . --output-dir ../fiw-release --check --commit "$(git rev-parse HEAD)"
sha256sum -c MANIFEST.sha256
git diff --check
```

## Assurance boundary

Automation checks structure, traceability, and declared evidence conditions. Scientific truth, readiness certification, investment decisions, and authorization to act remain with accountable human processes. See [boundary notes](LIMITATIONS.md).

## Security

Private vulnerability reporting via GitHub. See [Security](SECURITY.md).

## License

[MIT License](LICENSE). Published by [Bridge Node 7](https://bridgenode7.com/).

## Release

**v0.9.4 — Frontier Signal Integrity** <!-- x-release-please-version -->
This is the latest stable distribution milestone.

`main` is the current reviewed source. Distribution milestones live on the repository Releases page and in CHANGELOG.
