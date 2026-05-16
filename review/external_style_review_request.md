# AiNIR Pre-v1 Public Review Request

Please review this repository as a **pre-v1 public demo**, not as a production runtime.

## Main question

Does the repository clearly demonstrate the idea that model-generated workflow semantics must be inspected before lowering or execution?

## Run

```bash
python scripts/run_release_candidate_review.py --out-dir review_results
```

Expected result:

```text
overall_status: passed
```

## What to inspect manually

- README first impression.
- Whether the public/private boundary is clear.
- Whether the examples look broader than an email/outbox-only tool.
- Whether unsafe examples are clearly described as synthetic, non-executable fixtures.
- Whether claims are appropriately scoped as pre-v1 and non-production.

## What not to expect

- A production compiler.
- A production runtime.
- Real provider integrations.
- Complete formal verification.
- A final v1.0 release.
