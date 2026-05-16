# Pre-v1 Status

AiNIR has reached a **v1.0 RC candidate** packaging point, but it is **not** a v1.0 final release and **not** a production runtime.

This public repository demonstrates a bounded safety pipeline around AI-generated program semantics. It is still conservative by design: it is suitable for private GitHub trial, README/CI review, and external-style evaluation, not production deployment.

## Current status

```text
status: v1.0 RC candidate / pre-v1-to-v1 transition
public_release_type: demo / launch candidate
production_runtime_ready: false
human_external_review: pending
v1_final_ready: false
```

## What can be claimed

It is accurate to describe this repository as:

> a v1.0 RC candidate public demo showing how unsafe AI-generated program-semantic drafts can be parsed, normalized, checked, refused, receipted, replayed, and only then lowered into an auditable host-enforcement skeleton.

## What should not be claimed

Do not claim that this repository is:

- a v1.0 final release;
- a production compiler;
- a production payment/deletion/email runtime;
- a complete formal proof system;
- the full private AiNIR archive;
- externally human-reviewed final software.

## Completed public hardening arc

The public candidate includes the following core surfaces:

1. Safety Registry as single source of truth
2. Strict Draft AST
3. Evidence Ledger binding
4. Operation Spec and workflow semantic profile binding
5. Trusted Execution Context separation
6. Lowering Eligibility Gate and host enforcement contract
7. Negative conformance corpus and deterministic robustness harness
8. Golden traces and replay harness
9. Public/private split and documentation hardening
10. Effect contracts and semantic role tightening
11. Terminology conformance
12. Transaction binding and semantic integrity
13. Release candidate reassessment and review package
14. Operation contract and launch runner stabilization
15. Capability least-privilege and host enforcement contract
16. Exact capability contracts
17. Final defensive conformance review
18. Trust Gate surface consolidation
19. TrustReceipt persistence and replay
20. TrustReceipt conformance integration
21. Launch readiness with TrustReceipt replay
22. Verified Intent export surface and external consumer profile slot
23. VerifiedIntentPacket export contract hardening
24. VerifiedIntentPacket semantic grounding and validator hardening
25. VerifiedIntentPacket contract strictness and registry consistency
26. Local private GitHub trial simulation
27. README and boundary polish
28. First-impression polish
29. Private archive and external context profile split
30. v1.0 RC scope freeze and candidate packaging

## RC candidate boundary

The v1.0 RC candidate freezes the public API surface for review. It does not freeze production deployment behavior, enterprise registry governance, or downstream consumer integrations.
