# Transaction Binding and Semantic Integrity

AiNIR public demo now treats transaction declarations as machine-checkable
semantic contracts, not comments.

A workflow that requires an atomic boundary must declare a transaction binding:

```yaml
transaction:
  id: tx.create_user
  mode: atomic
  includes:
    - op.insert_user
    - op.insert_outbox_event
```

The verifier checks that:

1. the transaction is an object;
2. the transaction id is a safe identifier;
3. `mode` is an allowed host-enforced atomic mode;
4. `includes` is a non-empty list of existing operation ids;
5. included operations are unique, task-ordered, and contiguous;
6. workflow-required semantic roles occur inside the same transaction;
7. role order constraints hold, for example `create_user` before `outbox_event`;
8. transaction-required policies such as `policy.transactional_outbox_required` are present.

The lowerer also exposes transaction metadata to the host runtime:

```ts
await ctx.enforceTransaction?.(txEnvelope, state);
await ctx.runTransaction?.(txEnvelope, state, async () => {
  await ctx.enforceOperation(opEnvelope, state);
  await ctx.call(operationId, state);
});
```

This still is not production application code. It is a source-mapped skeleton that
makes the host runtime contract explicit.
