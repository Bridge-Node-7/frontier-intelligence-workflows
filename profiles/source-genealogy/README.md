# Source Genealogy

Source Genealogy is a deterministic public-safe FIW profile for preventing **publication multiplicity from masquerading as independent corroboration**.

It evaluates only declared relationships. It does not crawl the web, identify hidden publishers, authenticate an author, establish external truth, or authorize a consequential decision.

## What it preserves

Each source can declare:

- `ROOT` — a declared provenance root;
- `DERIVATIVE` — downstream material derived from another source;
- `TRANSLATION` — a translated derivative;
- `MIRROR` — a copied or mirrored derivative;
- `SYNDICATED` — redistributed material with the same upstream basis;
- `AI_DERIVATIVE` — AI-generated or AI-summarized material derived from a declared parent;
- `COORDINATED_PUBLICATION` — a declared coordinated derivative;
- `UNKNOWN` — lineage is not established and therefore cannot create independent corroboration.

A derivative must name `parent_source_id`. The evaluator walks parent lineage to its declared root. Five URLs from one root remain one provenance root.

## Independence is a bounded derived property

The profile derives current eligible corroboration groups from declared genealogy rather than URL count.

- shared roots collapse;
- citation dependencies collapse otherwise-separate roots for the bounded independence count;
- circular citation is surfaced and creates no new corroboration;
- roots in the same declared `coordination_group` collapse;
- translations, mirrors, syndication, and AI derivatives inherit their parent root;
- `UNKNOWN` lineage contributes zero independent corroboration;
- retracted, superseded, or unavailable roots remain visible in provenance but are excluded from current eligible corroboration.

This is deliberately conservative. A machine-derived count means only that the declared graph supports that many bounded groups. It does **not** prove real-world independence.

## Temporal and accessibility semantics

`temporal_status` is one of `CURRENT`, `SUPERSEDED`, `RETRACTED`, or `UNAVAILABLE`.

Accessibility is explicit. An unavailable source may retain a last-known URI or other declared provenance without being represented as currently accessible. Superseded and retracted material remains visible rather than being silently erased.

## Human authority

Every public-safe case requires `human_review_required: true` and a non-empty accountable `decision_owner`.

`NO_FINDINGS` means only that no configured deterministic genealogy finding was produced for the declared case. `REVIEW_REQUIRED` means the configured rules surfaced a condition requiring correction or corroboration. Neither state is a truth verdict.

## Adversarial regression surface

The repository regression suite proves the bounded mechanics against synthetic cases including:

- five URLs derived from one root;
- circular citation;
- translated and mirrored copies;
- AI-generated summaries;
- coordinated republication;
- retracted and superseded support;
- unavailable sources with retained last-known provenance;
- overstated independent-source counts;
- unknown lineage;
- parent-lineage cycles.

## CLI

```bash
python scripts/run_source_genealogy.py \
  --root . \
  --case path/to/synthetic-case.json \
  --json-output ../fiw-results/source-genealogy.json
```

Exit `0` means `NO_FINDINGS`; exit `1` means deterministic findings require attention; exit `2` means the input or output could not be handled.

## Boundary

Source Genealogy is an integrity signal for downstream FIW and Radiant Guardian review. It is not an automated truth oracle. No layer may upgrade a source's epistemic strength merely because the source was transported, repeated, translated, mirrored, summarized, or published at additional URLs.
