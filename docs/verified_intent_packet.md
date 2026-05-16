# VerifiedIntentPacket

`VerifiedIntentPacket` is an optional AiNIR export artifact for future verified-intent consumers.

It is not an integration, runtime adapter, compiler bridge, or production handoff path in this public demo. It is a bounded contract slot that can be used later by a downstream system if that system performs its own grounding and execution-level verification.

## Rule

A packet may only be exported after the draft passes the AiNIR Trust Gate.

A packet must not add meaning that AiNIR did not verify.

## Slots

The packet contains these conceptual slots:

- trust
- evidence bindings
- effects
- capabilities
- intent summary
- grounding status
- ambiguity status
- operation constraints
- required contracts
- security classifications
- receipt links

## Grounding boundary

In the current pre-v1 public profile, AiNIR does not emit concrete downstream schema groundings.

That means:

```json
{
  "groundings": [],
  "grounding_status": {
    "status": "consumer_must_ground",
    "required_consumer_checks": [
      "schema_grounding_required",
      "filter_matches",
      "projection_matches",
      "field_allowlist"
    ]
  }
}
```

AiNIR may verify the semantic trust boundary, but a future consumer must still verify concrete schema, field, filter, projection, and renderer semantics.

## Namespace boundary

The public packet separates AiNIR-native declarations from consumer-facing labels.

```json
{
  "effects": {
    "consumer_allowed": [],
    "consumer_required": [],
    "consumer_denied": [],
    "ainir_declared": [],
    "ainir_implied": []
  },
  "capabilities": {
    "consumer_allowed": [],
    "consumer_denied": [],
    "ainir_declared": [],
    "ainir_implied": []
  }
}
```

The runtime validator rejects contradictory allowed/denied declarations and unsupported consumer labels.

## Current profile scope

The public demo keeps this export surface intentionally narrow. It exists to show how a Trust Gate decision could become a future handoff artifact without weakening the Trust Gate itself.

It does not make AiNIR depend on any downstream project.


## Public profile limit

The public demo does not publish detailed consumer integration plans. It only
shows that a Trust Gate decision can optionally be represented as a bounded
verified-intent artifact. Any future consumer must still perform its own
schema, symbol, renderer, runtime, and execution-level verification.


## Relation to Trust Gate

`VerifiedIntentPacket` is downstream of the Trust Gate. It is not allowed to make stronger claims than the Trust Gate, registry, evidence ledger, and trusted context support.

If a consumer needs concrete schema grounding, renderer equivalence, or program-level execution proofs, it must add those checks itself and attach its own receipt.
