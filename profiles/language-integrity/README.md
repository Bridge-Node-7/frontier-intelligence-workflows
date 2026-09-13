# Language Integrity

Language Integrity is a deterministic Frontier Intelligence Workflows profile for checking whether declared claim semantics remain faithful to declared source semantics before a record moves deeper into an assurance or decision workflow.

It is a **public method and contract**, not a production NLP extractor. It does not parse arbitrary documents, determine truth, authenticate sources, infer source independence, promote knowledge, or authorize decisions.

## What it checks

The v0.7.0 profile makes five common language failures explicit:

1. **Forecast as result** — a forecast or design target must not become a demonstrated result.
2. **Attribution loss** — a quoted assertion must preserve the declared speaker/attribution.
3. **Inference as direct support** — an inference must not be labeled as direct evidentiary support.
4. **Provenance independence overstatement** — multiple reports sharing one declared root count as one declared independent root.
5. **Superseded as current** — a claim marked current must not rely on a cited source record already declared superseded.

The profile also fails visibly on unresolved cited-source references, incomplete supersession lineage, public-boundary violations, or missing human review.

## Contract

Each case declares:

```text
Synthetic metadata
  ↓
Source assertions + declared provenance roots
  ↓
Claim interpretation
  ↓
Temporal state
  ↓
Public boundary
  ↓
Human review requirement
  ↓
Deterministic Language Integrity findings
```

`NO_FINDINGS` means only that none of the configured deterministic rules produced a finding from the supplied declarations. It does **not** mean the underlying source is true, independent, current, complete, or sufficient for consequential action.

## Synthetic examples

Valid fixtures preserve each distinction. Matching invalid fixtures demonstrate the corresponding failure:

- `forecast-preserved.json` / `forecast-as-result.json`
- `quoted-attribution-preserved.json` / `attribution-loss.json`
- `inference-labeled.json` / `inference-as-direct.json`
- `provenance-collapse-visible.json` / `provenance-independence-overstated.json`
- `temporal-supersession-visible.json` / `superseded-as-current.json`

All fixtures are fictional and public-safe.

## Run

```text
python scripts/run_language_integrity.py \
  --root . \
  --case profiles/language-integrity/fixtures/valid/forecast-preserved.json
```

Exit `0` means `NO_FINDINGS`; exit `1` means configured findings require correction/review; exit `2` is an input/output handling failure; exit `3` means the record is outside the bounded schema.

## Boundary

Language Integrity deliberately stops before canonical knowledge, mission authority, or decision authority. A machine may identify a semantic mismatch; an accountable human remains responsible for source interpretation, evidence judgment, knowledge promotion, and consequential decisions.
