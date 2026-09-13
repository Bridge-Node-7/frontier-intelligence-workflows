# Frontier Intelligence Workflows

**Turn uncertain frontier-technology claims into decision-ready intelligence.**

Frontier Intelligence Workflows (FIW) is an open, evidence-first workflow for consequential technology questions when evidence is incomplete. It traces claims to sources, separates observation from inference, exposes contradictions and unknowns, and records the evidence needed before a decision responsibly moves forward.

**Automation checks structure, traceability, and declared evidence conditions. It does not determine truth, verify the underlying claim, make investment decisions, certify readiness, or authorize action.**

## Core Workflow

```text
Decision Question
  ↓
Claims
  ↓
Evidence
  ↓
Provenance
  ↓
Contradictions / Challenges
  ↓
Knowns · Unknowns
  ↓
Assumptions
  ↓
Assessment
  ↓
Decision Boundary
  ↓
Next Evidence
  ↓
Accountable Human
```

## Status Semantics

- **Perception Integrity:** `NO_FINDINGS` / `REVIEW_REQUIRED` describe configured deterministic findings in the declared assessment.
- **Repository controls:** `PASS` / `FAIL` / `NOT_RUN` describe whether a named machine control executed and satisfied its assertion.

`NO_FINDINGS` does not mean a claim or evidence set was verified. A passing repository control establishes only what that control tested.

See [Status Semantics](docs/assurance/STATUS_SEMANTICS.md).

## Decision Record

The [FIW Decision Record](templates/decision-record.md) is a portable record for a bounded assessment. It captures the decision context, material claims, evidence, provenance, uncertainty, decision boundary, next evidence, accountable owner, and rationale without converting uncertainty into certainty.

## Explore

### Frontier Claim Experience

The [Frontier Claim Experience](examples/frontier-claim-experience/) is a local-first synthetic example. Several reports appear to corroborate a claim, but tracing their origins reveals that they share a single provenance root.

### Frontier Technology Diligence

[FIW-SYN-005 — Frontier Technology Diligence](examples/frontier-technology-diligence/) is a fictional diligence scenario showing how repeated reporting can be distinguished from independent corroboration. It ends at a bounded evidence-gathering decision and does not recommend or execute an investment.

### Perception Integrity

[Perception Integrity](profiles/perception-integrity/) provides deterministic checks for declared evidence lineage, observation-versus-inference separation, assumptions, alternative hypotheses, evidence state, stop conditions, public-release boundaries, and decision authority.

Source independence remains analyst-established. FIW validates declared lineage consistency; it does not determine whether two real-world sources are genuinely independent.

### Radiant Guardian — Frontier Signal Integrity

[Radiant Guardian](profiles/radiant-guardian/) adds deterministic controls for frontier-signal genealogy, strategic-surprise hypotheses, self-sealing-model risk, prediction integrity, discriminating tests, update receipts, and Proof Loop reassessment. It composes with Perception Integrity and does not determine external truth.

### Synthetic Component Readiness

[FIW-SYN-001](examples/synthetic-component-readiness/) shows a complete evidence-to-decision artifact chain using fictional data.

## Use FIW

Keep nonpublic working evidence outside this public repository.

Start from the intentionally incomplete teaching template using the shell you already have.

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

The first run is expected to produce findings and exit with code `1`. Improve the declared record, rerun it, and treat `NO_FINDINGS` only as the absence of configured deterministic findings.

For an existing assessment, preserve the prior artifact and create a new result when reassessment is needed rather than silently rewriting the earlier record.

### CLI Result Contract

- Exit `0`: recommendation is `READY_FOR_HUMAN_REVIEW`.
- Exit `1`: deterministic findings require action before ordinary review.
- Exit `2`: input, path, or output handling error.
- Exit `3`: assessment fails the bounded schema contract.

## Public Assurance

FIW includes reproducible checks for software behavior, approved public structure, workflow integrity, manifest consistency, and deterministic packaging.

Run the complete repository gate from an isolated Python environment. The validation-only dependencies are pinned and are not runtime dependencies of FIW's public methods.

```bash
python -m venv ../fiw-validation-venv
source ../fiw-validation-venv/bin/activate  # Windows PowerShell: ..\fiw-validation-venv\Scripts\Activate.ps1
python -m pip install -r requirements-validation.txt
mkdir -p ../fiw-validation ../fiw-release
python scripts/run_tests.py --root . --json-output ../fiw-validation/source-test-summary.json
python scripts/compile_sources.py --root .
python scripts/validate_repo.py --root . --json-output ../fiw-validation/validation-report.json
python scripts/build_release.py --root . --output-dir ../fiw-release --check --commit "$(git rev-parse HEAD)"
sha256sum -c MANIFEST.sha256
git diff --check
```

A passing control establishes only what that control tested. Manifest checks establish byte consistency against the recorded manifest; they do not establish external truth or authorship.

## Public Boundary

FIW is designed for public-safe methods, synthetic examples, and inspectable assurance controls.

Do not place nonpublic, confidential, proprietary, credential, controlled, or operationally sensitive material in this public repository.

FIW does not certify scientific truth, technical performance, supplier qualification, production readiness, safety, regulatory approval, legal compliance, investment merit, or deployment authority.

## Security

Use GitHub private vulnerability reporting for security issues. Do not disclose sensitive security details through public repository surfaces.

See [Security](SECURITY.md), [Limitations](LIMITATIONS.md), and [Status Semantics](docs/assurance/STATUS_SEMANTICS.md).

## License

Repository code and documentation are available under the [MIT License](LICENSE).

Use of this repository does not imply Bridge Node 7 endorsement, certification, qualification, partnership, or approval.

Published by [Bridge Node 7](https://bridgenode7.com/).

## Release

**v0.6.1 — Decision-Ready Intelligence**
