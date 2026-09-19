# Frontier Signal Integrity Control Catalog v0.1

| ID | Finding | Trigger | Purpose |
|---|---|---|---|
| FSI-01 | `FSI-UPSTREAM-PI-UNRESOLVED` / `FSI-UPSTREAM-PI-REVIEW-REQUIRED` | PI validation missing, hash mismatch, ID mismatch, or already requires review | FSI cannot outrun upstream evidence integrity |
| FSI-02 | `FSI-SIGNAL-CLAIM-COLLAPSE` | Reported/inferred signal is declared as established fact | Preserve signal/claim boundary |
| FSI-03 | `FSI-INDEPENDENCE-OVERSTATED` | Independent-root count is overstated or required corroboration lacks multiple roots | Prevent repetition from becoming corroboration |
| FSI-04 | `FSI-ANCHOR-EXTENSION-BRIDGE-MISSING` | Real-anchor → unsupported-extension flag lacks bridge evidence | Prevent factual laundering across a causal gap |
| FSI-05 | `FSI-SELF-SEALING-WITHOUT-DISCRIMINATOR` | Self-sealing risk has no linked discriminating test | Preserve falsifiability and learning |
| FSI-06 | `FSI-PREDICTION-NOT-FROZEN` | Open prediction lacks frozen timestamp/window/criteria | Prevent retrospective prediction rewriting |
| FSI-07 | `FSI-PREDICTION-RESOLUTION-INCOMPLETE` | Success/failure/ambiguous/unresolved criteria are incomplete | Make resolution auditable |
| FSI-08 | `FSI-DISCRIMINATING-TEST-INCOMPLETE` | Test cannot separate at least two hypotheses with observable evidence and a decision rule | Convert debate into learning |
| FSI-09 | `FSI-GENERATED-HYPOTHESIS-PROMOTED` | AI-assisted/Creative-Psionics hypothesis receives automatic evidentiary weight | Keep creativity epistemically bounded |
| FSI-10 | `FSI-UPDATE-RECEIPT-INCOMPLETE` | Material state change lacks evidence delta, rationale, reviewer, time, or reversal trigger | Preserve belief history |
| FSI-11 | `FSI-PUBLIC-BOUNDARY-VIOLATION` | FSI permits release when upstream PI says do not release | Fail closed on public boundary |
| FSI-12 | `FSI-PROOF-LOOP-INCOMPLETE` | Active decision/action/outcome tracking lacks reassessment trigger or learning record | Make real-world outcomes improve the system |

A control finding establishes only that the configured condition fired. It does not establish the external claim's truth or falsity.
