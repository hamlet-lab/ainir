# TrustReceipt Registry Evolution

A TrustReceipt records the registry hash used when a Trust Gate decision was made.

This is intentional: a decision should be replayable against the same draft, context, verifier report, and registry snapshot.

## Current public scope

The public demo supports exact replay against the same registry snapshot.

If the safety registry changes, an old receipt may fail exact replay. That does not necessarily mean the old decision was wrong; it means the decision was made under a different registry snapshot.

## Future replay modes

A production system should distinguish at least three replay modes:

1. `exact_snapshot_replay` — same draft, same registry snapshot, same context;
2. `current_registry_replay` — re-evaluate against the current registry;
3. `migrated_registry_replay` — apply a signed registry migration record before replay.

## Future registry governance

A production deployment should retain registry snapshots, record migration decisions, and make receipt evolution explicit instead of silently changing historical decision semantics.
