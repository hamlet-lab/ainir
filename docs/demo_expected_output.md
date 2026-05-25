# Demo expected output

Run from the repository root:

```bash
python -m ainir demo --out-dir /tmp/ainir_demo_results
```

Expected output:

```text
AiNIR public demo: passed
- account_deletion_hard_delete_blocked: blocked (10 critical)
- create_user_outbox_safe: passed (0 critical)
- order_payment_real_payment_blocked: blocked (16 critical)
- password_reset_raw_token_blocked: blocked (11 critical)
- pii_export_raw_pii_blocked: blocked (17 critical)
```

The exact critical counts matter less than the shape of the result: the safe outbox fixture passes, and the four negative conformance fixtures are refused.
