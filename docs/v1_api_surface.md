# v1.0 RC API Surface

This is the public-facing API surface frozen for v1.0 RC review.

## CLI surface

- `ainir verify`
- `ainir trust-gate`
- `ainir trust-receipt-issue`
- `ainir trust-receipt-replay`
- `ainir lower`
- `ainir demo`
- `ainir negative-conformance-eval`
- `ainir golden-trace-eval`
- `ainir verified-intent-export`
- `ainir phase21-launch-readiness-eval`
- `ainir phase25-verified-intent-contract-eval`
- `ainir phase26-private-trial-eval`
- `ainir phase30-v1-rc-candidate-check`

Phase-specific commands remain public-demo review helpers. They are not a long-term stable production API.

## Artifact surface

- `TrustGateDecision`
- `TrustReceipt`
- `TrustReceiptReplayReport`
- `VerifiedIntentPacket`
- TypeScript host-enforcement skeleton for eligible safe drafts

## Registry surface

- `registries/safety_registry.yaml`
- `registries/operation_spec_registry.yaml`
- `registries/evidence_ledger.yaml`
- `registries/external_consumer_profiles.yaml`

The public RC candidate treats these registries as review artifacts. Production registry governance is out of scope.
