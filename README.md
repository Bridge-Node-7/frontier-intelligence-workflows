# Frontier Intelligence Workflows

**Turn uncertain frontier-technology claims into decision-ready intelligence.**

Frontier Intelligence Workflows (FIW) is Bridge Node 7's open, evidence-first workflow layer for consequential technology questions where evidence is incomplete. It traces claims to sources, separates observation from inference, exposes contradictions and unknowns, and identifies the smallest justified next evidence before a decision responsibly moves forward.

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

FIW deliberately uses two different status vocabularies:

- **Perception Integrity:** `NO_FINDINGS` / `REVIEW_REQUIRED` — what configured deterministic PI rules found in the declared assessment.
- **Repository and release controls:** `PASS` / `FAIL` / `NOT_RUN` — whether a machine control actually executed and satisfied its defined assertion.

`NO_FINDINGS` does **not** mean the evidence or claim was verified. It means no configured deterministic PI rule produced a finding from the declared record.

**A passing control establishes only what that control tested.**

See [Status Semantics](docs/assurance/STATUS_SEMANTICS.md).

### Upgrading from v0.4.x

- Treat existing v0.4.x assessment artifacts as **historical evidence under the contract that produced them**. Do not silently rewrite `validation_status: "PASS"` to `NO_FINDINGS`.
- When a current assessment is required, preserve the original artifact and re-run the source assessment under v0.5.x so the new result has its own version, digest, and evaluation time.
- For modified working copies, do not overwrite local changes in place. Preserve the modifications, start from the tagged v0.5.x release, reapply the changes deliberately, and run the complete repository gate before relying on the updated tree.

## Decision Contexts

FIW applies the same evidence discipline to different consequential decision contexts:

- **Capital allocators:** What deserves deeper diligence or bounded validation?
- **Industry teams:** What emerging technology deserves testing, partnership, adoption, or further qualification?
- **Mission organizations:** What capability deserves additional evidence, qualification, or strategic attention?

FIW prepares decision-ready intelligence. Accountable people retain authority over consequential decisions.

## FIW Decision Record v0.5

The [FIW Decision Record](templates/decision-record.md) is the candidate common decision contract for a bounded assessment. It records:

```text
Identity
  ↓
Decision Context
  ↓
Claims
  ↓
Evidence
  ↓
Provenance
  ↓
Uncertainty
  ↓
Assessment
  ↓
Decision Boundary
  ↓
Next Evidence
```

The record makes decision ownership, stakes, reversibility, evidence cutoff, confidence boundaries, stop conditions, and next-evidence requirements explicit. It is a candidate interoperability object, not a universal BN7 standard.

## Explore

### Frontier Technology Diligence

[FIW-SYN-005 — Frontier Technology Diligence](examples/frontier-technology-diligence/) is a fully fictional capital-allocation diligence scenario. Three reports appear to corroborate a breakthrough materials claim, but all three trace to one originating source.

**Independent corroboration is not established.**

That does not establish that the underlying fictional claim is false. It establishes only that the cited record does not independently corroborate it. The example ends at a bounded evidence-gathering decision; it does not recommend or execute an investment.

### Frontier Claim Experience

The [Frontier Claim Experience](examples/frontier-claim-experience/) demonstrates the same provenance problem interactively: several reports appear to corroborate a claim, but tracing their origins reveals that they share a single provenance root.

### Perception Integrity

[Perception Integrity](profiles/perception-integrity/) provides deterministic checks for evidence lineage, observation-versus-inference separation, assumptions, alternative hypotheses, evidence state, stop conditions, public-release boundaries, and decision authority.

Source independence is **declared and analyst-established**. FIW validates declared lineage consistency; it does not magically discover whether two real-world sources are truly independent. See the [twelve control scenarios](profiles/perception-integrity/CONTROL_EXAMPLES.md) for concise synthetic examples of each deterministic PI control.

### Synthetic Component Readiness

[FIW-SYN-001](examples/synthetic-component-readiness/) shows a complete evidence-to-decision artifact chain using fictional data.

## Where FIW Fits

Bridge Node 7 uses **Frontier Intelligence Infrastructure** as the broader architecture for consequential technology decisions under uncertainty.

- **FIW** establishes what the available evidence earns.
- Domain methods such as [Materials-to-Mission](https://github.com/Bridge-Node-7/materials-to-mission) contribute specialized evidence when relevant.
- The [Frontier Decision Engine](https://github.com/Bridge-Node-7/frontier-decision-engine) structures options, objectives, uncertainties, plausible futures, and tradeoffs when deeper decision reasoning is useful.
- Accountable people retain consequential authority.

These capabilities are modular rather than a mandatory linear pipeline.

## Use FIW

Keep nonpublic working evidence outside this public repository.

Start from the intentionally incomplete teaching template:

```bash
mkdir -p ../fiw-work ../fiw-results
cp templates/perception-integrity-starter.json ../fiw-work/assessment.json

python scripts/run_perception_integrity.py \
  --root . \
  --assessment ../fiw-work/assessment.json \
  --evaluated-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --json-output ../fiw-results/validation.json
```

The first run is expected to produce findings and exit with code `1`; that is the intended teaching result, not a tool failure. Improve the declared record, rerun it, and treat `NO_FINDINGS` only as the absence of configured deterministic findings—not as proof of the underlying claim.

`templates/perception-integrity-assessment.json` remains a known-valid synthetic assessment for regression and advanced adopter reference.

External assessments are represented with a sanitized external identifier rather than their absolute source path.

### CLI Result Contract

- Exit `0`: recommendation is `READY_FOR_HUMAN_REVIEW`.
- Exit `1`: deterministic findings require action before ordinary review.
- Exit `2`: input, path, or output handling error.
- Exit `3`: assessment fails the bounded schema contract.

Schema rejection and deterministic PI findings are intentionally separate error channels.

## Public Assurance

FIW's assurance chain is intentionally ordered by what each layer establishes:

1. **Behavioral and adversarial regression tests** — verify defined software behavior.
2. **Repository policy and public-boundary validation** — verify approved public structure and release conditions.
3. **Workflow hardening** — verify pinned dependencies, bounded permissions, and checkout behavior.
4. **Manifest integrity** — verify the published bytes match the recorded bytes.
5. **Deterministic release construction** — verify repeated source packages are byte-identical.

Manifests establish that published bytes are internally consistent with the recorded manifest. They do not establish who produced them, and FIW does not currently publish cryptographic build-provenance attestation.

Run the complete repository gate:

```bash
mkdir -p ../fiw-validation ../fiw-release
python scripts/run_tests.py --root . --json-output ../fiw-validation/source-test-summary.json
python scripts/compile_sources.py --root .
python scripts/validate_repo.py --root . --json-output ../fiw-validation/validation-report.json
python scripts/build_release.py --root . --output-dir ../fiw-release --check --commit "$(git rev-parse HEAD)"
sha256sum -c MANIFEST.sha256
git diff --check
```

A passing control establishes only what that control tests. In strict release validation, every mandatory repository control must report `PASS`; `NOT_RUN` is non-passing.

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

**v0.5.1 — Decision-Ready Intelligence**

This patch preserves the v0.5 Decision-Ready Intelligence contract while closing the Markdown internationalization defect, clarifying v0.4.x artifact migration, and refining the Frontier Claim Experience into a calmer, more legible decision journey.
