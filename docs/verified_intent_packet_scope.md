# VerifiedIntentPacket Scope

`VerifiedIntentPacket` is an optional future export artifact.

It is not a downstream integration and not a runtime adapter.

## Current public scope

The public demo exports only bounded, registry-backed semantic information. It must not add concrete meaning that AiNIR did not verify.

For example, the public packet does not claim concrete downstream schema grounding:

```json
{
  "groundings": [],
  "grounding_status": {
    "status": "consumer_must_ground"
  }
}
```

## Why this is intentionally conservative

AiNIR is not currently a schema grounding engine. If it emitted concrete field mappings it had not verified, the packet would overclaim.

## Future direction

A future consumer may add its own verified grounding receipt, or AiNIR may add a separate grounding ledger/profile. Until then, concrete schema, symbol, renderer, and runtime grounding remain consumer obligations.


## Why groundings are empty in the public RC

The public RC intentionally exports `groundings: []` with `consumer_must_ground`. AiNIR has not verified downstream schema symbols such as database columns, renderer fields, or typed program variables. Emitting those fields would overclaim. A downstream consumer must perform its own schema, symbol, renderer, and runtime checks before using the packet.
