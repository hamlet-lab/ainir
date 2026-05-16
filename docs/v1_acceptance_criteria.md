# v1.0 RC Acceptance Criteria

A build remains within the v1.0 RC candidate boundary only if all criteria below pass.

## Required checks

```bash
python -m pytest -q
python -m ainir demo --out-dir /tmp/ainir_demo_results
python -m ainir negative-conformance-eval --out-dir /tmp/ainir_negative_conformance
python -m ainir golden-trace-eval --out-dir /tmp/ainir_golden_traces
python -m ainir phase25-verified-intent-contract-eval --out-dir /tmp/ainir_phase25_verified_intent_contract
python -m ainir phase26-private-trial-eval --out-dir /tmp/ainir_phase26_private_trial
python -m ainir phase30-v1-rc-candidate-check --out-dir /tmp/ainir_phase30_v1_rc_candidate
```

## Required safety behavior

- Empty drafts are invalid.
- Self-attested evidence cannot verify a claim.
- Extra effects are refused.
- Extra capabilities are refused.
- Unsupported workflow export is refused.
- Concrete downstream grounding is not invented by AiNIR.
- Blocked, invalid, stale, ambiguous, or hole-containing drafts do not lower.
- Transaction metadata with unknown fields is refused by the strict draft contract.
- Unresolved ambiguity is allowed to remain a non-executable verification state, but it cannot lower.
- TrustReceipt replay detects draft/context/registry/report mismatch.

- Trust Gate `lowering_allowed` matches the public lowerer preflight for input type, output type, and return expression allowlists.
- Trust-looking claim statuses such as `evidence_checked` and `evidence_attached` are not accepted as self-attested substitutes for ledger-bound `verified` evidence.
- `executable: false` drafts can remain non-executable verification artifacts, but they cannot lower.
- TrustReceipt replay is tamper-evident for stable receipt fields including failed gates, warning gates, lowering eligibility, and trusted-context source/purpose.

## Required status language

The repository must continue to say:

- not v1.0 final;
- not production runtime;
- private GitHub trial before public release.
