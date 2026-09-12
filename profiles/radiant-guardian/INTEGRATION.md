# FIW / PI Integration

Radiant Guardian references an existing Perception Integrity validation instead of extending the closed PI assessment object.

## Required upstream pin

Each RG case declares:

- PI assessment ID;
- PI validation path;
- SHA-256 of the exact validation bytes.

The RG validator checks that the referenced file resolves within the repository root, the digest matches, the assessment ID matches, and `human_decision_required` remains true.

## Propagation

- upstream PI review findings propagate into RG;
- upstream `DO_NOT_RELEASE_PUBLICLY` cannot be weakened by RG;
- RG findings do not silently rewrite PI evidence strength;
- all consequential downstream actions remain human-owned.
