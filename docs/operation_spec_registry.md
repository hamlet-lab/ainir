# Operation Spec Registry

Pre-v1 Phase 4 changes the public demo from keyword-based semantic profile checks to operation-spec-bound checks.

## Rule

A workflow semantic role is not satisfied merely because an operation name contains a suggestive word such as `auth`, `payment`, `grace`, or `token`.

A role is satisfied only when the operation resolves to a registered operation spec in `registries/operation_spec_registry.yaml`, and that spec declares the semantic role.

## Why this matters

Without operation specs, these drafts could be misleading:

```yaml
op: grace.period.placeholder
```

or:

```yaml
op: payment.charge.real
effects: []
```

The first looks like a grace-period check but proves nothing. The second hides a payment effect. Phase 4 blocks both patterns.

## Pipeline

```text
Strict Draft AST
→ Safety Registry normalization
→ Operation Spec Registry binding
→ Workflow semantic profile check
→ Policy/effect/trust verifier
→ Lowering eligibility gate
```

## Public-demo scope

This registry is deliberately bounded. Unknown operations in known demo workflows are blocked rather than silently accepted. A larger system can add operations by extending the registry, not by weakening verifier gates.
