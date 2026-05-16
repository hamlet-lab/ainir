# Evidence Ledger Binding

Pre-v1 Phase 3 makes evidence binding explicit.

AiNIR public demo no longer accepts `checked: true`, `reliability`, `source`,
`producer`, or similar fields when they are supplied inside an untrusted draft.
Those fields are treated as self-attestation. A verified claim is accepted only
when its evidence id resolves to a bundled ledger record in
`registries/evidence_ledger.yaml`.

A ledger-bound evidence record must match:

- evidence id
- evidence kind
- checked status in the ledger
- trusted producer kind
- reliability threshold
- supported module
- supported workflow
- supported claim id
- optional claim statement hash
- optional supporting artifact hash

This prevents an AI-generated draft from creating its own evidence by writing:

```yaml
checked: true
source: claude
reliability: 0.99
```

The public demo includes one bundled evidence record for the safe CreateUser
outbox example. Other verified claims should remain hypothesized unless an
external verifier/report/ledger record is supplied.
