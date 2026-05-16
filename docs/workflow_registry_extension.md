# Workflow Registry Extension

AiNIR v1.0 RC Candidate uses a **bounded public workflow registry**.

The public demo intentionally recognizes a small set of safety-critical workflows:

- `CreateUser`
- `PasswordReset`
- `NewsletterSignup`
- `PIIExportRequest`
- `AccountDeletion`
- `OrderPayment`

Unknown workflows are refused with `W001.unknown_workflow`.

This is a safety choice, not a claim that the public demo can verify every possible enterprise workflow. If AiNIR does not know the workflow profile, it cannot know the required operation roles, effects, capabilities, policies, transaction boundaries, or negative conformance cases.

## Why unknown workflows are refused

For an unknown workflow, AiNIR would otherwise have to guess:

- which effects are safety-critical;
- which capabilities are minimal;
- which evidence is required;
- whether a transaction boundary is required;
- what counts as a semantic-empty workflow;
- which lowering and handoff surfaces are allowed.

Guessing here would weaken the Trust Gate.

## Future extension path

A production deployment needs a workflow profile authoring path. A new workflow should be added with:

1. canonical workflow id and aliases;
2. operation spec registry entries;
3. required semantic roles;
4. required and forbidden effect families;
5. exact capability contracts;
6. evidence requirements;
7. transaction requirements, if any;
8. negative conformance cases;
9. golden trace expectations;
10. receipt replay expectations.

## Production note

The public RC candidate is closed-world. A production deployment may add a `review_required` state for unknown workflows, but it should not silently pass them.


## Operational risk of bypass

A closed-world registry is safe for a public demo, but a production deployment must avoid making registration so painful that teams bypass the gate. Unknown workflow decisions should eventually support `hold` or `review_required` modes with clear next actions:

- define the workflow profile;
- add operation specs;
- define effect and capability contracts;
- attach evidence requirements;
- add negative conformance cases;
- add golden traces.
