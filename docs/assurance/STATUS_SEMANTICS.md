# Status Semantics

FIW deliberately separates assessment findings from repository-control execution states.

## Perception Integrity

- `NO_FINDINGS` — no configured deterministic PI rule produced a finding from the supplied declared record.
- `REVIEW_REQUIRED` — one or more configured deterministic PI rules produced findings.

`NO_FINDINGS` does not establish that the declarations are accurate, the evidence is independently verified, the claim is true, or an action is authorized.

## Repository and Release Controls

- `PASS` — the named machine control executed and satisfied its defined assertion.
- `FAIL` — the named machine control executed and did not satisfy its defined assertion.
- `NOT_RUN` — the named control could not execute because a prerequisite or evidence source was unavailable.

`status` is authoritative. Where the compatibility field `passed` is present, it is derived mechanically as:

```text
passed = (status == "PASS")
```

In strict release validation, every mandatory control must report `PASS`. `FAIL` and `NOT_RUN` are both non-passing.

## CLI Exit Contract

For `scripts/run_perception_integrity.py`:

- exit `0` — recommendation is `READY_FOR_HUMAN_REVIEW`;
- exit `1` — deterministic findings require action before ordinary review;
- exit `2` — input, path, or output handling error;
- exit `3` — assessment is outside the bounded assessment schema.

Schema rejection and deterministic PI findings are intentionally distinct channels.
