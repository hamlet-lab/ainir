# Trusted Execution Context

Pre-v1 Phase 5 separates runtime context from model-authored draft metadata.

A draft may contain a field such as:

```yaml
environment: production
```

AiNIR treats that field as **untrusted metadata**. It can be reported for audit, but it cannot relax policy gates.

Policy evaluation receives a `TrustedExecutionContext` from the runtime or CLI:

```bash
python -m ainir verify examples/create_user_outbox_safe/draft.yaml --env test
```

Supported public-demo trusted environments are defined in `registries/safety_registry.yaml`:

- `public_demo`
- `test`
- `staging`
- `production`

In the public demo, `public_demo` and `test` are test-like contexts. Real/live external effects are blocked in those contexts regardless of what the draft claims.

This prevents environment spoofing stresss such as:

```yaml
environment: production
operations:
  - op: email.send.real
    effects:
      - effect.external.notification.email.real
```

The trusted context boundary is deliberately small here, but the rule is core to AiNIR:

> Runtime context is supplied by the execution system, not by the model draft.
