# AiNIR

![Status](https://img.shields.io/badge/status-v1.0%20RC%20candidate-orange)
![Runtime](https://img.shields.io/badge/runtime-not%20production-lightgrey)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)

> **Model output is a claim, not a fact.**

AiNIR is a **v1.0 release-candidate public demo** of a semantic trust layer for
inspecting AI-generated program semantics before they are lowered, handed off,
or executed by a host runtime.

A model may propose a workflow. AiNIR asks whether that proposal is trustworthy
enough to move forward: Are effects declared? Are capabilities minimal? Is the
evidence ledger-bound? Is the runtime context trusted? Are transaction
boundaries explicit? Can the draft be lowered safely?

Created by **Lee Yoon Kyu** under **[AIOE]**.

## 한국어 요약

AiNIR는 AI가 만든 workflow 출력을 곧바로 사실이나 실행 가능한 명령으로
보지 않습니다. 그 출력이 행동으로 넘어가기 전에 충분한 근거,
semantic contract, capability 경계, 신뢰할 수 있는 실행 맥락을 갖추었는지 검사하는
semantic trust layer입니다.

간단히 말하면, AiNIR는 "모델이 그럴듯한 답을 했는가?"보다 "그 답을 실행이나
handoff로 넘겨도 될 만큼 근거가 갖춰졌는가?"를 묻습니다.

이 공개 저장소는 v1.0 RC candidate 공개 데모입니다. v1.0 final이나
production runtime은 아니며, private review archive와 전체 연구 기록은
포함하지 않습니다.

## At a glance

AiNIR is a compact public demo of a trust boundary for AI-generated program
semantics, now packaged as a **v1.0 RC candidate** for bounded public review
and external evaluation.

```mermaid
flowchart TD
    A["AI-generated draft"] --> B["Strict Draft AST"]
    B --> C["Safety Registry"]
    C --> D["Evidence Ledger"]
    D --> E["Operation / Effect / Capability Gates"]
    E --> F["Trusted Context + Transaction Binding"]
    F --> G["Trust Gate"]
    G --> H{"Decision"}
    H -->|passed| I["TrustReceipt"]
    H -->|refused / invalid| J["Refusal Report"]
    I --> K["Replay Check"]
    I --> L["Lowering Eligibility"]
    L --> M["Host Enforcement Skeleton"]
```

Pipeline summary:

| Stage | What AiNIR checks |
| --- | --- |
| AI-generated draft | Treats model output as a semantic claim, not executable truth. |
| Strict Draft AST | Rejects malformed or prose-shaped workflow drafts. |
| Registries and evidence | Checks safety registry, evidence ledger, operation specs, effects, and capabilities. |
| Trusted context and transaction binding | Uses host-provided context and explicit transaction boundaries. |
| Trust Gate decision | Issues a pass/refusal decision with failed gates and reasons. |
| TrustReceipt and replay | Records replayable decisions before lowering eligibility. |
| Lowering skeleton | Allows only safe, lowerable workflows to produce a host-enforcement TypeScript skeleton. |

The public demo includes drafts that should be refused and one safe workflow that
can be lowered into a host-enforcement TypeScript skeleton.

| Example | What it checks | Expected |
| --- | --- | --- |
| `password_reset_raw_token_blocked` | synthetic secret persistence marker | refused |
| `order_payment_real_payment_blocked` | irreversible financial-effect marker | refused |
| `pii_export_raw_pii_blocked` | unprotected PII marker | refused |
| `account_deletion_hard_delete_blocked` | irreversible deletion marker | refused |
| `create_user_outbox_safe` | transaction-bound outbox pattern | passed + lowerable |

## Current status

This repository is a **v1.0 RC candidate public demo**.

It is **not a v1.0 final**. It is **not a production runtime**. It remains a
conservative pre-v1-to-v1 transition package while external review and final
scope governance remain pending.

It is not:

- a v1.0 final release;
- a production compiler;
- a production execution runtime;
- a replacement for host-level security controls;
- the full private research archive.

The larger private review package, extended workflow suite, private reports,
and enterprise policy packs are intentionally not included here.

## What this RC candidate actually claims

AiNIR does **not** claim to verify arbitrary AI-generated code semantics today.

This public RC candidate demonstrates a narrower, testable claim:

- model-generated workflow drafts are treated as semantic claims;
- known workflow profiles are checked against registered evidence, effects,
  capabilities, operation contracts, trusted context, transaction boundaries,
  and lowering gates;
- unknown workflows are refused instead of guessed;
- every public pass/refusal path is covered by negative conformance cases,
  golden traces, and TrustReceipt replay.

The longer-term infrastructure path is **profile-based**: workflow profiles,
canonical effect contracts, external evidence providers, registry versioning,
and consumer conformance packs. AiNIR becomes more useful by making those
profiles governable, not by pretending that one demo registry covers every
enterprise workflow.

## Bounded public demo scope

The public RC candidate is intentionally closed-world. It recognizes a small
workflow registry and refuses unknown workflows instead of guessing their
semantics.

This is a demo-safety boundary, not a claim that AiNIR can verify every
enterprise workflow today. Production use would require workflow registry
governance, external evidence providers, canonical effect taxonomies, registry
snapshot management, and profile-specific conformance packs. See
[`docs/positioning_and_scope.md`](docs/positioning_and_scope.md),
[`docs/v1_known_limitations.md`](docs/v1_known_limitations.md), and
[`docs/v1_roadmap.md`](docs/v1_roadmap.md).

## Quick start

Run from the repository root. The demo writes reports to your OS temp directory
so the checkout stays clean.

**macOS / Linux**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m ainir demo --out-dir "${TMPDIR:-/tmp}/ainir_demo_results"
```

**Windows PowerShell**

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m ainir demo --out-dir "$env:TEMP\ainir_demo_results"
```

Expected result:

```text
AiNIR public demo: passed
- account_deletion_hard_delete_blocked: blocked (10 critical)
- create_user_outbox_safe: passed (0 critical)
- order_payment_real_payment_blocked: blocked (15 critical)
- password_reset_raw_token_blocked: blocked (11 critical)
- pii_export_raw_pii_blocked: blocked (17 critical)
```

Run the local release-readiness simulation:

```bash
python scripts/run_phase26_private_trial.py
```

Run focused checks. On Windows PowerShell, replace `/tmp/...` with
`$env:TEMP\...`, or set `AINIR_TEMP_ROOT` before running scripts.

```bash
python -m ainir negative-conformance-eval --out-dir /tmp/ainir_negative_conformance
python -m ainir golden-trace-eval --out-dir /tmp/ainir_golden_traces
python scripts/run_prelaunch_check.py
python scripts/run_release_candidate_review.py
```

Lower the safe outbox example:

```bash
python -m ainir lower examples/create_user_outbox_safe/draft.yaml \
  --out-dir /tmp/ainir_lowering_check
```

On Windows PowerShell:

```powershell
python -m ainir lower examples/create_user_outbox_safe/draft.yaml `
  --out-dir "$env:TEMP\ainir_lowering_check"
```

## What makes AiNIR different?

AiNIR is not a JSON schema validator.

A schema can check whether a model output has the right shape. AiNIR checks
whether the claimed program semantics are eligible to move toward lowering or
handoff.

That means AiNIR looks beyond field presence. It checks evidence bindings,
safety-critical effects, capability contracts, operation specs, trusted
execution context, transaction boundaries, lowering eligibility, and replayable
trust receipts.

## Toward Warranted AI

AiNIR is a step toward **warranted AI execution**: deciding when a
model-generated claim has enough evidence, semantic contract support,
capability discipline, trusted context, and transaction binding to move toward
handoff or execution.

Guardrails often ask whether an output is allowed. Evals often ask whether an
output was good. AiNIR asks whether an AI-generated semantic claim is warranted
enough to become an action.

In this public RC candidate, that warrant remains bounded to the registered demo
workflows, bundled evidence, and explicit non-production scope.

## Related areas

AiNIR sits near runtime verification for LLM agents, evidence-gated execution,
semantic contracts for AI agents, pre-execution validation, agent governance,
tool contracts, policy-as-code, and workflow conformance testing.

It differs from output guardrails and general evals by focusing on the
claim-to-action boundary: whether a model-generated workflow claim is supported
well enough to move toward lowering, handoff, or execution.

## Trust Gate example

Unsafe drafts do not become executable artifacts. A refused draft produces a decision artifact like this:

```json
{
  "status": "refused",
  "executable": false,
  "lowering_allowed": false,
  "handoff_allowed": false,
  "failed_gates": [
    "evidence_ledger",
    "capability_contract"
  ],
  "reasons": [
    {
      "rule_id": "EVIDENCE_SELF_ATTESTED",
      "severity": "critical",
      "message": "Verified claims require ledger-bound evidence."
    }
  ]
}
```

A passed decision can issue a `TrustReceipt`. The receipt can be replayed
against the same draft, registry, context, and verifier report to check that the
decision is reproducible.

## What AiNIR checks

- **Strict intake**: malformed YAML, prose-shaped sections, hidden fields, and undeclared operation effects are refused.
- **Evidence discipline**: verified claims must bind to the bundled evidence ledger; draft self-attestation is not enough.
- **Operation contracts**: workflow roles must come from registered operation specs, not keyword guesses.
- **Effect and capability boundaries**: operations cannot add effects or capabilities outside their contract.
- **Trusted context**: `draft.environment` is untrusted metadata; policy evaluation uses host-provided context.
- **Transaction binding**: transaction-required workflows must declare ordered, contiguous transaction boundaries.
- **Lowering gate**: blocked, invalid, stale, or hole-containing drafts cannot lower.
- **TrustReceipt replay**: trust decisions can be replayed against the same
  draft, registry, context, and verifier report.

## Optional future export surface

AiNIR includes an optional `VerifiedIntentPacket` export surface for future
verified-intent consumers. In this public demo it is a **contract slot**, not an
integration.

The export surface must not add meaning that AiNIR did not verify. Concrete
downstream schema grounding remains a consumer obligation.

## Documentation

Start with:

- [`START_HERE.md`](START_HERE.md)
- [`docs/README.md`](docs/README.md)
- [`docs/v1_rc_candidate.md`](docs/v1_rc_candidate.md)
- [`docs/v1_rc_scope.md`](docs/v1_rc_scope.md)
- [`docs/pre_v1_status.md`](docs/pre_v1_status.md)
- [`docs/public_private_boundary.md`](docs/public_private_boundary.md)
- [`docs/trust_gate.md`](docs/trust_gate.md)
- [`docs/trust_receipt_persistence.md`](docs/trust_receipt_persistence.md)
- [`docs/negative_conformance_corpus.md`](docs/negative_conformance_corpus.md)
- [`docs/golden_traces.md`](docs/golden_traces.md)
- [`docs/verified_intent_packet.md`](docs/verified_intent_packet.md)
- [`docs/workflow_registry_extension.md`](docs/workflow_registry_extension.md)
- [`docs/evidence_provider_interface.md`](docs/evidence_provider_interface.md)
- [`docs/effect_taxonomy_and_canonical_effects.md`](docs/effect_taxonomy_and_canonical_effects.md)
- [`docs/trust_receipt_registry_evolution.md`](docs/trust_receipt_registry_evolution.md)
- [`docs/v1_roadmap.md`](docs/v1_roadmap.md)

For implementation history, see the phase-specific documents under `docs/`.

## Release Status

This repository is a conservative **v1.0 RC candidate public demo**. It is
**not a v1.0 final release**, **not a production runtime**, and **not a
replacement for host-level security controls**.

Public scope is intentionally bounded while external review and profile-governance work remain pending.

## Author and license

- Author / maintainer: **Lee Yoon Kyu**
- Organization / project studio: **[AIOE]**
- License: **Apache-2.0**

See `AUTHORS.md`, `NOTICE`, and `docs/github_repo_settings.md` before publishing.
