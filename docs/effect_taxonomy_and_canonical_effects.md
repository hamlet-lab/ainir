# Effect Taxonomy and Canonical Effects

AiNIR v1.0 RC Candidate uses a small public safety registry to classify effect families.

The public demo includes pattern-based safety-critical detection for known fixture families, but production systems should prefer **canonical effect contracts** over open-ended string guessing.

## Current public scope

The public demo blocks known safety-critical patterns such as:

- irreversible financial-effect markers;
- unprotected PII markers;
- synthetic secret persistence markers;
- irreversible deletion markers;
- undeclared external/system-level effect markers.

This is enough for the bounded examples, but it is not a complete enterprise effect taxonomy.

## Risk of string-only classification

A string classifier can never enumerate every possible spelling of a risky effect. A production path should avoid relying on terms like `real`, `live`, or `production` alone.

## Future production path

Production effect handling should move toward:

1. canonical effect ids only;
2. registry-declared effect families;
3. operation specs that declare implied effect families;
4. explicit aliases registered in the safety registry;
5. unknown effect ids resolved as `review_required` or refused;
6. signed or versioned registry snapshots.

## Public repo claim

The public repo demonstrates conservative effect and capability boundaries for a bounded demo. It does not claim to classify arbitrary enterprise effect names.


## Canonical contracts over string guessing

The public registry uses conservative patterns for the demo, but production should prefer canonical effect contracts over open-ended name inference. Unknown or alias-like effects should be refused or sent to review until the registry explicitly maps them to a family, risk class, evidence requirement, and capability contract.
