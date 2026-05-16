# Positioning and Scope

AiNIR is an attempt to put a semantic trust boundary in front of AI-generated program behavior.

The core idea is simple:

> Model output is a claim, not a fact.

A model may propose a workflow, operation, evidence reference, or capability. AiNIR does not treat that proposal as executable intent by default. It parses the draft, checks the registered semantic contracts, evaluates evidence binding, and decides whether the draft may move toward lowering, handoff, or refusal.

## What the public RC candidate covers

The public repository is a bounded v1.0 RC candidate demo. It focuses on a small set of safety-critical workflows:

- account deletion;
- password reset;
- payment ordering;
- PII export;
- newsletter signup;
- create-user-with-outbox.

This narrow scope is intentional. Unknown workflows are refused rather than guessed.

## What it does not claim

The public RC candidate does not claim to:

- verify arbitrary AI-generated code semantics;
- cover every enterprise workflow;
- provide a production evidence backend;
- provide a complete enterprise effect taxonomy;
- replace host runtime security controls;
- execute real external side effects.

Those are production-path problems, not public-demo claims.

## Why this is hard

AiNIR is not only checking whether a JSON document has the right fields. It is asking questions such as:

- What operation family is this draft claiming?
- Which effects and capabilities are required?
- Is the evidence ledger-bound, or is it model self-attestation?
- Is the execution context host-provided?
- Are transaction boundaries explicit and enforceable?
- Can the decision be replayed against the same registry snapshot?

This is why AiNIR uses registries, evidence ledgers, operation specs, Trust Gate decisions, TrustReceipts, negative conformance cases, and golden traces.

## How AiNIR can grow

AiNIR should not grow by pretending that one registry can cover every domain.

The intended path is profile-based:

1. define a workflow profile;
2. register operation specs and semantic roles;
3. define canonical effect and capability contracts;
4. bind required evidence providers;
5. add negative conformance fixtures;
6. add golden traces;
7. version the registry snapshot;
8. preserve replay semantics through TrustReceipts.

In this model, AiNIR is a semantic trust framework. Each domain profile earns trust by registering its contracts and tests.

## Public vs private scope

The public repository is a focused demo of the trust boundary.

The private archive keeps broader strategy, extended fixtures, private reports, future consumer context profiles, and long-term registry governance notes. The private archive is not the public repo and should not be published as-is.
