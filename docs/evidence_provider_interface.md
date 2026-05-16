# Evidence Provider Interface Roadmap

The public AiNIR evidence ledger is deterministic and bundled with the demo. It is designed to demonstrate the rule:

> A model cannot verify its own evidence.

In the public demo, `verified` claims must bind to known evidence records. This prevents self-attested fields such as `checked: true`, `source: claude`, or `evidence_checked` from becoming facts.

## Current public scope

The bundled ledger is fixture-backed. It is not an enterprise evidence backend.

## Future production path

A production deployment should provide evidence through explicit providers, for example:

- host policy engine evidence;
- human approval evidence;
- audit/event log evidence;
- authorization ticket evidence;
- test or verifier report evidence;
- runtime observation evidence.

Each provider should issue stable evidence records with:

- issuer id;
- evidence id;
- claim scope;
- artifact hash;
- policy version;
- timestamp or validity window;
- integrity binding;
- revocation or expiry policy.

## Non-goal for the public repo

The public repo does not implement a live evidence provider network. It demonstrates the evidence boundary and keeps fake or self-attested evidence from promoting claims.


## The bundled public ledger is not enough for production

The public ledger is deliberately self-contained so the demo is deterministic. A real deployment needs provider adapters for approval tickets, policy-engine decisions, audit/event logs, verifier reports, and human review records. Without that provider layer, most new claims should remain hypothesized or unverified.
