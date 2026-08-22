# Perception Integrity Control Scenarios

These concise synthetic scenarios explain what each deterministic Perception Integrity control is intended to surface. They are teaching examples, not evidence that a real-world claim is true or false.

| Control | Synthetic trigger | Deterministic lesson |
|---|---|---|
| `PI-01` Claim mode consistency | The assessment says `INFERENCE` while the referenced claim says `REPORTED_CLAIM`. | Claim-mode declarations must agree before the record is reviewable. |
| `PI-02` Observation vs inference | The same sentence is placed in both observation and inference fields, including trivial punctuation variants. | A statement should not be presented simultaneously as direct observation and inference. |
| `PI-03` Lineage / evidence references | A source points to a missing parent, forms a cycle, or an evidence reference names no declared source. | The declared evidence chain must resolve internally. |
| `PI-04` Independent corroboration | Three summaries all derive from one primary source in a high-salience case. | Repetition from one provenance root is not independent corroboration. |
| `PI-05` Material assumptions | A major/critical decision record declares no material assumptions. | Consequential reasoning must expose the assumptions carrying the assessment. |
| `PI-06` Alternative hypotheses | An inferential claim has no competing explanation. | Inferential records should preserve plausible alternatives rather than collapse uncertainty too early. |
| `PI-07` Salience vs evidence | A high-salience claim is paired with `WEAK` evidence. | Declared evidentiary strength must be commensurate with the record's salience. |
| `PI-08` Evidence freshness | Controlling evidence expired before the explicit evaluation time. | Time-sensitive evidence must be reassessed before action. |
| `PI-09` Consequence / reversibility | A critical, irreversible decision is paired with weak or limited evidence. | The deterministic recommendation must fail closed to `HOLD`; human authority remains required. |
| `PI-10` Human review / owner | Human review is disabled or no accountable decision owner is named. | Consequential authority must remain attributable. |
| `PI-11` Stop conditions | The record contains no explicit condition that would halt or reconsider advancement. | A reviewable record needs a declared boundary for stopping or reassessing. |
| `PI-12` Public boundary | Sensitive content is simultaneously marked eligible for public release. | Public-release boundaries cannot be overridden by a favorable declaration. |

## Boundary

These scenarios illustrate configured deterministic rules. They do not validate the underlying evidence, discover source independence automatically, detect every possible semantic inconsistency, or authorize a consequential action.
