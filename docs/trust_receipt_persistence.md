# TrustReceipt Persistence and Replay

AiNIR Trust Gate decisions are not meant to be ephemeral console output.
Phase 19 adds a small persistence and replay surface for TrustReceipt artifacts.

A persisted TrustReceipt records stable hashes for:

- the canonicalized draft payload
- the safety registry
- the verifier report
- the trusted execution context, including source and purpose
- the Trust Gate status
- failed and warning gate summaries
- lowering eligibility status and stable findings

Replay recomputes the Trust Gate decision against the current draft and current
registry. A receipt is accepted only if the stable fields reproduce.

## Commands

Issue a receipt:

```bash
python -m ainir trust-receipt-issue examples/create_user_outbox_safe/draft.yaml \
  --out-dir /tmp/ainir_trust_receipts
```

Replay it:

```bash
python -m ainir trust-receipt-replay /tmp/ainir_trust_receipts/<receipt>.receipt.json
```

Run the Phase 19 conformance check:

```bash
python -m ainir phase19-trust-receipt-eval --out-dir /tmp/ainir_phase19_receipt_eval
```

## Important limits

A TrustReceipt is not a production signature and not a substitute for external
review. It is a deterministic pre-v1 replay artifact. If the draft, registry, verifier report, trusted context, failed gate summary, warning gate summary, or lowering eligibility projection changes, replay must fail.
