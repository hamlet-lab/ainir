# AiNIR docs

This directory contains architecture notes, conformance fixtures, release-candidate boundaries, and roadmap notes for the public demo.

Start here if you want to understand the system rather than the development history.

## Recommended reading path

1. [`v1_rc_candidate.md`](v1_rc_candidate.md) - v1.0 RC candidate decision and boundary.
2. [`v1_rc_scope.md`](v1_rc_scope.md) - what is frozen for RC review.
3. [`pre_v1_status.md`](pre_v1_status.md) - current scope and what AiNIR does not claim.
4. [`trust_gate.md`](trust_gate.md) - the unified decision surface.
5. [`trust_receipt_persistence.md`](trust_receipt_persistence.md) - issuing and replaying TrustReceipts.
6. [`negative_conformance_corpus.md`](negative_conformance_corpus.md) - synthetic fixtures that must be refused.
7. [`golden_traces.md`](golden_traces.md) - deterministic replay expectations.
8. [`lowering_gate.md`](lowering_gate.md) - when lowering is allowed or refused.
9. [`verified_intent_packet.md`](verified_intent_packet.md) - optional future export surface.
10. [`public_private_boundary.md`](public_private_boundary.md) - what belongs in the public repo.

## Core architecture docs

- [`architecture.md`](architecture.md)
- [`safety_registry.md`](safety_registry.md)
- [`strict_draft_ast.md`](strict_draft_ast.md)
- [`evidence_ledger.md`](evidence_ledger.md)
- [`operation_spec_registry.md`](operation_spec_registry.md)
- [`execution_context.md`](execution_context.md)
- [`transaction_binding.md`](transaction_binding.md)
- [`effect_contracts_and_semantic_roles.md`](effect_contracts_and_semantic_roles.md)

## Scope and extensibility docs

- [`workflow_registry_extension.md`](workflow_registry_extension.md)
- [`evidence_provider_interface.md`](evidence_provider_interface.md)
- [`effect_taxonomy_and_canonical_effects.md`](effect_taxonomy_and_canonical_effects.md)
- [`trust_receipt_registry_evolution.md`](trust_receipt_registry_evolution.md)
- [`executable_claim_semantics.md`](executable_claim_semantics.md)
- [`verified_intent_packet_scope.md`](verified_intent_packet_scope.md)
- [`v1_roadmap.md`](v1_roadmap.md)

## Release and publishing docs

- [`github_launch_checklist.md`](github_launch_checklist.md)
- [`github_repo_settings.md`](github_repo_settings.md)
- [`prelaunch_check.md`](prelaunch_check.md)
- [`private_archive_boundary.md`](private_archive_boundary.md)
- [`public_launch_candidate.md`](public_launch_candidate.md)

## v1.0 RC candidate docs

- [`v1_rc_candidate.md`](v1_rc_candidate.md)
- [`v1_rc_scope.md`](v1_rc_scope.md)
- [`v1_api_surface.md`](v1_api_surface.md)
- [`v1_acceptance_criteria.md`](v1_acceptance_criteria.md)
- [`v1_known_limitations.md`](v1_known_limitations.md)

## Development history

Phase-specific documents are kept for traceability. They are not required for a first read. Read them when you need to understand why a particular gate or fixture was added.

- [v1.0 RC Candidate Patch 4 - Registry and Classifier Consistency](v1_rc_candidate_patch4.md)
- [Cross-platform output paths](cross_platform_output_paths.md)

- [v1.0 RC Candidate Patch 6 - Release Identity and Cross-platform Temp Paths](v1_rc_candidate_patch6.md)
- [v1.0 RC Candidate Patch 7 - Repo-local Temp Isolation Guard](v1_rc_candidate_patch7.md)
