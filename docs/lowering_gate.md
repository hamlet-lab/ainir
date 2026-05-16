# Pre-v1 Phase 6 - Lowering Eligibility Gate and Host Enforcement Contract

AiNIR public demo lowering is not an authorization mechanism by itself. It is a
post-verification transformation that may only run after the same draft passes
verification under a trusted execution context.

## Rules

1. A draft must parse into Strict Draft AST before lowering.
2. A supplied verifier report is never trusted alone.
3. The lowerer re-verifies the same draft under the trusted execution context.
4. The supplied report and fresh report must match in module, workflow, and status.
5. `blocked` or `invalid` drafts are refused.
6. Lowered TypeScript emits host runtime enforcement hooks:
   - `ctx.enforceModule?(...)`
   - `ctx.enforceOperation(...)`
7. Operation envelopes include effects, capabilities, policies, risk families,
   trusted environment, and verification status.

This keeps public demo lowering aligned with the AiNIR rule:

> verifier decides eligibility; lowerer does not create eligibility.
