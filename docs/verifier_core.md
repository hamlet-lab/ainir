# Principled Verifier Core (public demo)

The public AiNIR verifier is intentionally small, but it is no longer only a set
of ad-hoc example checks. It uses a bounded safety model with these gates:

1. **Strict draft shape**: a draft must be a YAML object with `module`,
   `workflow`, `task`, and non-empty `operations`.
2. **Safe identifiers**: safety-critical identifiers cannot contain unsafe
   characters or leading/trailing whitespace.
3. **Canonical workflow boundary**: only the public demo workflow set is allowed.
4. **Evidence boundary**: `checked: true` written by a model is not enough.
   Verified claims require non-self-attested checked evidence metadata.
5. **Implied effects**: safety-critical operation names such as `payment.charge.real`,
   `http.call`, `email.marketing.real`, or `account.delete.permanent` cannot hide
   behind `effects: []`.
6. **Risk families**: raw tokens, raw PII, real payment, real email in request
   workflows, irreversible deletion marker, and unknown real external effects are
   blocked or review-required.
7. **Workflow semantic profile**: known workflows cannot pass as semantic-empty
   no-op drafts.
8. **Lowering eligibility**: only `passed` drafts may be lowered.

This is still a compact public demo, not the full private RC verifier or a
production compiler. Its job is to demonstrate the trust boundary:

> Model output is a claim, not a fact.
