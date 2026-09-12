# Radiant Guardian Status Semantics

## Validation status

- `NO_RG_FINDINGS` — no configured RG deterministic integrity rule produced a finding from the supplied declared record.
- `RG_REVIEW_REQUIRED` — one or more configured RG integrity rules produced findings.

Neither status determines whether the underlying claim is true.

## Recommendation

Possible bounded recommendations include:

- `READY_FOR_HUMAN_REVIEW`
- `REQUIRE_CORROBORATION`
- `REQUIRE_DISCRIMINATING_EVIDENCE`
- `REVISE_PREDICTION`
- `REASSESS_BEFORE_ACTION`
- `DO_NOT_RELEASE_PUBLICLY`

A recommendation is workflow guidance, never autonomous authorization.

## CLI exit contract

- exit `0` — RG recommendation is `READY_FOR_HUMAN_REVIEW`;
- exit `1` — deterministic RG findings require action before ordinary review;
- exit `2` — input/path/output handling error;
- exit `3` — case is outside the bounded RG case contract.
