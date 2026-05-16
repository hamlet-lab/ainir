
# AiNIR Trust Receipt

A Trust Receipt is an audit-friendly summary of an AiNIR Trust Gate decision.
It records the draft hash, safety registry hash, verifier report hash, trusted
execution context, failed gates, and lowering eligibility.

The receipt is not a production attestation and is not an external consumer
integration. It is a pre-v1 review artifact for explaining why a model-generated
semantic draft was passed, refused, or marked invalid.


## Stable receipt projection

TrustReceipt replay compares a stable projection of the receipt. The projection includes decision status, draft and registry hashes, verifier report hash, trusted context source/purpose, failed/warning gates, and lowering eligibility. Runtime timestamps are excluded.
