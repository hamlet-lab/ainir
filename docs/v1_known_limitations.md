# v1.0 RC Known Limitations

AiNIR v1.0 RC candidate is intentionally bounded.

## Not production runtime

AiNIR does not execute real external effects. It emits host-enforcement skeletons for review and demonstration.

## No enterprise registry governance yet

The public demo includes bounded registries. It does not include the governance process for adding, signing, retiring, or delegating registry entries across an organization.

## No real evidence backend

The public evidence ledger is bundled and deterministic. A production deployment would need an external evidence ledger backend and issuer policy.

## No downstream integration

`VerifiedIntentPacket` is an optional export artifact. The public demo does not integrate with downstream compilers, runtimes, renderers, or workflow engines.

## Conservative workflow coverage

The public examples focus on a small set of safety-critical workflows. New workflows require explicit operation specs, safety profiles, and conformance fixtures.

## Host enforcement is required

Lowered TypeScript skeletons rely on a host runtime to implement enforcement hooks such as `enforceOperation`, `enforceTransaction`, and `runTransaction`.

## Bounded workflow registry

The public RC candidate is closed-world. Unknown workflows are refused with `W001.unknown_workflow` until a workflow profile, operation specs, effect/capability contracts, evidence requirements, transaction rules, negative conformance fixtures, and golden traces are registered.

See `docs/workflow_registry_extension.md`.

## Fixture-backed evidence ledger

The public evidence ledger is deterministic and bundled. It demonstrates evidence binding and self-attestation refusal, but it is not an enterprise evidence provider backend.

See `docs/evidence_provider_interface.md`.

## Bounded effect taxonomy

The public safety registry is conservative and intentionally small. It is not a complete enterprise effect taxonomy. Future deployments should use canonical effect contracts and registry-governed aliases rather than relying on open-ended string matching.

See `docs/effect_taxonomy_and_canonical_effects.md`.

## Exact registry replay only

TrustReceipt replay currently targets exact registry-snapshot replay. Registry migration and current-registry replay are future work.

See `docs/trust_receipt_registry_evolution.md`.

## Executable field is not the source of truth

Draft-level `executable` metadata is a claim. Trust Gate and Lowering Eligibility decide whether a draft can move toward lowering.

See `docs/executable_claim_semantics.md`.

## VerifiedIntentPacket is intentionally conservative

The public `VerifiedIntentPacket` surface does not emit concrete downstream schema groundings. Future consumers must perform their own schema, symbol, renderer, runtime, and execution-level verification.

See `docs/verified_intent_packet_scope.md`.


## No arbitrary-code semantic guarantee

AiNIR v1.0 RC candidate demonstrates a registry-backed trust gate for bounded workflow profiles. It does not claim to infer all hidden semantics of arbitrary AI-generated code. Expanding coverage requires registered workflow profiles, canonical effects, evidence providers, and conformance packs.
