# Proof-Hinge Research Sidecar (Synthetic)

**Research-only extension of Frontier Signal Integrity (FSI); no decision authority.**

This is not an independent platform, scientific discovery system, source validator, or Frontier Decision Engine receipt. It is an optional offline calculation for FSI's existing discriminating-test work. Upstream Perception Integrity and FSI findings remain authoritative for their own limited integrity checks.

## Question

Given human-declared competing worlds, action consequences, possible test outcomes, and costs, which proposed evidence request has the greatest modeled reduction in worst-case regret?

This is a decision-theory exercise. A positive model score is not empirical value of information, a calibrated probability, a financial saving, mission qualification, or authorization to publish. Scientific novelty has not been established.

## Local demonstration

From the repository root, using Python 3.11+ without network access or external dependencies:

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/proof_hinge_research.py profiles/frontier-signal-integrity/fixtures/valid/proof-hinge-supplier.synthetic.json
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/proof_hinge_research.py profiles/frontier-signal-integrity/fixtures/valid/proof-hinge-qubit.synthetic.json
    PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_proof_hinge_research.py

Both scenarios are synthetic. Neither example establishes supplier qualification, qubit performance, or independent validation. No instrument access, uploads, secrets, or production changes are involved.

For a concise, human-readable research brief, add `--format brief` to either invocation. The optional Markdown brief leads with the current conditional evidence request or abstention, describes the assumed benefit as arbitrary fictional units, and exposes the missing verification and human-review requirements. Its generated text escapes untrusted labels. The default machine-readable JSON behavior is unchanged; this view does not create an assurance receipt or publish anything.


## Formal rule

For stipulated utility U(action,world), regret R(action,world) equals the best stipulated utility in that world minus the utility for that action.

Baseline regret: min over actions of max over worlds of R.

With an observation o: choose the action minimizing maximum regret over the worlds compatible with o.

Post-test regret: max over possible observations of the conditional minimax regret.

Net research score: baseline regret minus post-test regret minus an assumed test cost.

An observation compatible with multiple worlds remains ambiguous. There is no probability model.

## Sensitivity and abstention

An optional payoff_variants array holds fully explicit alternative utility tables. If the same positive top-ranked test does not survive in every supplied table, the model returns ABSTAIN_ASSUMPTION_SENSITIVE with no prioritized test. If no test has a positive net score, it returns ABSTAIN_NO_POSITIVE_PROOF_TEST. No variants supplied does not prove robustness.

REQUEST_EVIDENCE_FOR_REVIEW only describes a hypothetical ranking, not a PI/FSI READY_FOR_HUMAN_REVIEW result. It is not a verification, approval, qualification, or human decision. Every result explicitly states that claims are unverified and decision authority is NONE.

## Twelve-case synthetic benchmark

The test suite `tests/test_proof_hinge_benchmark.py` defines twelve public-safe, wholly fictional decision scenarios: four neutral-atom, four critical-material, and four AI-cyber-assurance cases. It runs a separate, exhaustive observation-contingent policy enumerator as an arithmetic reference to the research calculator. The 12 scenarios exercise deterministic and ambiguous measurements, two- and three-world models, cost sensitivity, hypothetical payoff-table reversal, and explicit abstention. Four additional checks enforce case count, synthetic provenance, nonauthority, and comparator semantics.

In this stipulated matrix, eight scenarios yield a positive-scoring research test, three yield no positive-scoring test, and one abstains because the recommendation reverses under an alternative payoff table. The comparison with the cheapest hypothetical test is a **mechanical same-objective comparator**, not an expert baseline, unbiased accuracy assessment, speed improvement, real economic value, customer study, or empirical validation. The deliberate construction favors fully discriminating tests in positive cases. No claims about real-world effectiveness, physical systems, or scientific originality follow from a passing check.

Reproduce locally with `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p 'test_proof_hinge*.py'`. The main repository suite also discovers these tests. No new transport contract, release authority, data ingestion, or deployed interface is introduced.

## Interfaces and future gates

Keep FSI source genealogy, Perception Integrity findings, FMA scientific-discovery assurance, and Frontier Decision Engine human decisions separate. Do not introduce an independent authority or claim an integrated interface exists.

Before any production coupling: expand beyond the included mathematical fixtures to rights-cleared, independently specified case studies, realistic imperfect test calibration, payoff uncertainty, parser abuse, source-rights compliance, and a blinded comparison to a conventional FSI unranked-test process. Require independent human reviewers for consequential use. Stop if false certainty, unstable rankings, or missing rights appear.

The code does not perform experiments, validate measurements, determine real costs, authenticate sources, or settle speculative physics.
