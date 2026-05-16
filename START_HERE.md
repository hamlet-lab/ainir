# Start here

AiNIR is a **v1.0 RC candidate semantic trust layer** for bounded public review and final scope review.

The public demo is built around one rule:

> **Model output is a claim, not a fact.**

AiNIR is not trying to make every model draft pass. It is trying to expose unsupported or unsafe program semantics before they can be lowered or handed to a host runtime.

## 0. Understand the scope

Read [`docs/positioning_and_scope.md`](docs/positioning_and_scope.md) if you want the precise claim: this is a bounded v1.0 RC candidate demo, not a production verifier for arbitrary AI-generated code.

## 1. Install

Run from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 2. Run the demo

```bash
python -m ainir demo --out-dir /tmp/ainir_demo_results  # Windows PowerShell: $env:TEMP\ainir_demo_results
```

You should see one safe example pass and four negative conformance examples refused.

## 3. Inspect a Trust Gate decision

```bash
python -m ainir trust-gate examples/create_user_outbox_safe/draft.yaml --json --out-dir /tmp/ainir_trust_gate
```

A Trust Gate decision answers:

- Is the draft structurally valid?
- Which gates passed or failed?
- Is lowering allowed?
- Can a TrustReceipt be issued and replayed?

## 4. Run the release-readiness simulation

```bash
python scripts/run_phase26_private_trial.py
```

This checks the public candidate in a fresh temporary copy and confirms the checkout stays clean.

## 5. Run focused checks

```bash
python -m ainir negative-conformance-eval --out-dir /tmp/ainir_negative_conformance  # Windows: $env:TEMP\ainir_negative_conformance
python -m ainir golden-trace-eval --out-dir /tmp/ainir_golden_traces  # Windows: $env:TEMP\ainir_golden_traces
python scripts/run_prelaunch_check.py
python scripts/run_release_candidate_review.py
```

## 6. Inspect the examples

- `examples/password_reset_raw_token_blocked/draft.yaml`
- `examples/order_payment_real_payment_blocked/draft.yaml`
- `examples/pii_export_raw_pii_blocked/draft.yaml`
- `examples/account_deletion_hard_delete_blocked/draft.yaml`
- `examples/create_user_outbox_safe/draft.yaml`

## 7. Read the docs in order

1. `docs/README.md`
2. `docs/trust_gate.md`
3. `docs/trust_receipt_persistence.md`
4. `docs/negative_conformance_corpus.md`
5. `docs/golden_traces.md`
6. `docs/public_private_boundary.md`

## 8. Read the RC candidate scope and roadmap

- `docs/v1_rc_candidate.md`
- `docs/v1_rc_scope.md`
- `docs/v1_api_surface.md`
- `docs/v1_known_limitations.md`
- `docs/v1_acceptance_criteria.md`
- `docs/v1_roadmap.md`
- `docs/workflow_registry_extension.md`
- `docs/evidence_provider_interface.md`
- `docs/effect_taxonomy_and_canonical_effects.md`
- `docs/trust_receipt_registry_evolution.md`

## 9. Read before publishing

- `docs/pre_v1_status.md`
- `docs/public_private_boundary.md`
- `docs/private_archive_boundary.md`
- `docs/github_launch_checklist.md`

Keep the repository private until README rendering, GitHub Actions, and the v1.0 RC candidate check are confirmed.


## Windows PowerShell output paths

Most examples use `/tmp/...` for brevity. On Windows PowerShell, use `$env:TEMP\...` instead, or set `AINIR_TEMP_ROOT` before running review scripts. See `docs/cross_platform_output_paths.md`.
