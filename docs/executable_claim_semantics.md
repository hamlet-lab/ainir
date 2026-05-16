# Executable Claim Semantics

AiNIR treats draft fields as claims, not facts.

That includes any field that appears to describe executability.

## Current RC behavior

The draft may contain `executable`, but AiNIR does not trust it as the final execution decision.

The Trust Gate and Lowering Eligibility Gate decide whether a draft can move toward lowering or handoff.

After RC Candidate Patch 2:

- `executable: false` may still describe a non-executable draft state;
- `executable: false` prevents lowering;
- unresolved holes prevent lowering;
- unresolved ambiguity prevents lowering;
- blocked or invalid drafts prevent lowering.

## Future direction

A later revision may rename this field to make its claim nature clearer, for example:

- `author_claimed_executable`;
- `requested_executable`;
- `execution_intent`.

For the RC candidate, the public docs treat `executable` as untrusted draft metadata and keep the Trust Gate as the source of truth.
