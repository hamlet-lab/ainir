# Public Launch Candidate Notes

This repository is intended to be the public-facing AiNIR demo repo.

## Goal

Make the core idea legible in 5–10 minutes:

> Model output is a claim, not a fact.

The repo should show a concrete pipeline where unsafe model-generated workflow drafts are blocked before execution.

## Public launch checklist

Before publishing:

- [ ] Run `python scripts/run_prelaunch_check.py --out-dir /tmp/ainir_prelaunch_results`.
- [ ] Confirm all checks pass.
- [ ] Confirm no private archive ZIPs are present.
- [ ] Confirm no generated folders are staged: `/tmp/ainir_prelaunch_results/`, `/tmp/ainir_negative_conformance/`, `/tmp/ainir_golden_traces/`, `/tmp/ainir_demo_results/`, `/tmp/ainir_lowering_check/`.
- [ ] Confirm `README.md` says pre-v1 and not v1 final.
- [ ] Confirm `docs/public_private_boundary.md` is present.
- [ ] Confirm the GitHub repo description and topics are set.

## GitHub description

```text
A semantic safety layer that blocks unsafe AI-generated program semantics before execution.
```

## Suggested topics

```text
ai-safety
llm
code-generation
intermediate-representation
agentic-ai
policy-as-code
semantic-ir
```

## What to keep private

Do not publish the full RC archive, extended workflow suite, enterprise policy packs, hardening corpora, or private evaluation packs unless a separate release decision is made.
