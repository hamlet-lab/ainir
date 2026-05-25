# Safety Registry — Single Source of Truth

AiNIR public demo is now in **pre-v1 architecture hardening**. The central rule is:

> Normalizer, verifier, policy core, and lowerer must read safety-critical aliases, workflows, effect families, safety-critical operation patterns, evidence rules, workflow profiles, and TypeScript reserved words from one registry.

The registry lives in:

```text
registries/safety_registry.yaml
src/ainir/registries/safety_registry.yaml
src/ainir/safety_registry.py
```

The duplicated local tables previously present in `normalizer.py`, `policy_core.py`, `verifier.py`, and `lowering.py` are no longer the authority.

## What the registry controls

- canonical workflow names and aliases
- effect aliases
- allowlisted external effects
- safety-critical effect families
- safety-critical operation-name patterns
- effect/capability contracts
- trusted evidence producers and bundled evidence ids
- workflow semantic profiles
- semantic role markers
- TypeScript reserved words

## Why this exists

The earlier public demo could be missed by small spelling changes such as:

```text
payment.charge.real -> payment.finalize.production
source: model -> source: claude
account.hard_delete -> account.delete.permanent
```

Those bugs came from scattered string heuristics. The registry does not make the public demo a production verifier, but it removes split-brain allowlists and makes safety decisions auditable.

## Current scope

This is Phase 1 only. It does not claim full v1.0 readiness. It is the foundation for later phases:

1. strict draft AST
2. evidence ledger binding
3. operation spec registry
4. workflow semantic profile enforcement
5. registry-driven policy core
6. lowering eligibility gate and host enforcement contract
7. negative conformance corpus and deterministic robustness harness
