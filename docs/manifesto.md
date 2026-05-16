# AiNIR Manifesto

AI-generated code is not the artifact.
AI-generated semantics are the artifact.

A model can write code that looks correct while hiding safety-critical effects:

- a raw token persisted to a database,
- a real payment provider call in a beta path,
- raw PII logged for debugging,
- a hard-delete operation without approval,
- a direct email side effect inside a user creation transaction.

AiNIR makes those hidden semantics explicit.

The system does not trust model output. It treats it as a draft made of claims. Claims need evidence. Effects need capabilities. Policies need predicates. Execution needs gates.

AiNIR is therefore not a faster code generator. It is a semantic safety layer between model output and execution.
