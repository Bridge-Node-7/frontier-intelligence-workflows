# FIW / PI Integration

Frontier Signal Integrity references an existing Perception Integrity validation instead of extending the closed PI assessment object.

## Required upstream pin

Each FSI case declares:

- PI assessment ID;
- PI validation path;
- SHA-256 of the exact validation bytes.

The FSI validator checks that the referenced file resolves within the repository root, the digest matches, the assessment ID matches, and `human_decision_required` remains true.

## Propagation

- upstream PI review findings propagate into FSI;
- upstream `DO_NOT_RELEASE_PUBLICLY` cannot be weakened by FSI;
- FSI findings do not silently rewrite PI evidence strength;
- all consequential downstream actions remain human-owned.
