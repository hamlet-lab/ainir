# External Consumer Profiles

AiNIR may later hand verified semantic intent to external consumers. A consumer
profile describes the contract surface for such a handoff.

Consumer profiles do **not** merge external projects into AiNIR. They are named
profiles under AiNIR's own export surface.

Current profile:

- `AIVLConsumerProfile`: contract slot for future AIVL-style consumers.

Out of scope for the current public demo:

- importing downstream compiler/runtime code
- generating downstream IR
- executing downstream pipelines
- claiming production readiness


## Phase 24 grounding boundary

In the current pre-v1 public profile, AiNIR does not emit concrete downstream schema groundings. `VerifiedIntentPacket.slots.groundings` is empty, and `grounding_status.status` is `consumer_must_ground`. Future consumers must verify source/filter/projection grounding themselves.


## Public/private boundary

The public repository intentionally keeps consumer profiles small. It documents the
existence of an optional export surface and a bounded profile fixture, but it does
not publish downstream compiler mappings, training-row plans, or private strategy
notes.

Detailed external-context profiles, including AIVL-Core and LEP planning notes,
belong in the private review archive. The public demo should remain focused on
AiNIR's own Trust Gate, TrustReceipt replay, conformance fixtures, and host
lowering boundary.
