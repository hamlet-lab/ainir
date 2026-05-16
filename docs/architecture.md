# Architecture

The public demo contains four small components.

```text
Draft YAML
  -> normalizer.py
  -> verifier.py + policy_core.py
  -> lowering.py
```

## Normalizer

The normalizer performs conservative alias normalization and downgrades oververified claims. It never silently repairs an unsafe draft into a safe canonical module.

## Verifier

The verifier enforces minimal trust, capability, hole, and policy rules.

## Policy Core

The policy core evaluates machine-checkable demo policies over effect IDs and workflow context.

## Lowerer

The lowerer reads the safe draft operation graph and emits a TypeScript skeleton with operation IDs, canonical operations, effects, policies, and source-order metadata.

This is deliberately not a production compiler.
