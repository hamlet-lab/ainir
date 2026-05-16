# AiNIR v1.0 RC Candidate

AiNIR is now packaged as a **v1.0 RC candidate public demo**.

This means the public demo scope is ready for repository-level README/CI review and release-candidate evaluation. It does **not** mean AiNIR is a v1.0 final release or production runtime.

## RC candidate decision

```text
decision: v1_0_rc_candidate
public_release_ready: pending_repository_review
production_runtime_ready: false
v1_final_ready: false
human_external_review: pending
```

## What is frozen for RC review

- Trust Gate decision surface
- TrustReceipt issue/replay shape
- public negative conformance corpus
- public golden traces
- public safety registry and operation registry shape
- public VerifiedIntentPacket export contract slot
- public/private boundary language
- launch-readiness and release-readiness checks

## What is not frozen

- production host runtime integrations
- enterprise evidence ledger backend
- external consumer adapters
- organization-level policy registry governance
- future workflow domains beyond the public demo set
- v1.0 final release wording

## Recommended next step

Confirm README rendering and GitHub Actions while the repository is still private. Only then decide whether to make the public demo visible.
