# Strict Draft AST

AiNIR pre-v1 Phase 2 adds a strict intake boundary between raw provider/model YAML and semantic verification.

The public demo previously loaded YAML into a Python dictionary and let the verifier inspect it directly. That made the verifier responsible for both shape validation and semantic safety. Phase 2 separates those jobs:

```text
raw YAML
  -> load_draft
  -> parse_draft_ast
  -> DraftAST
  -> normalizer
  -> verifier
  -> lowering gate
```

## Principles

1. **Raw provider output is not a program.** It is untrusted input.
2. **Malformed draft input is invalid before semantic verification.** The verifier should not reason over prose, scalar list items, or unknown section shapes.
3. **Operations must explicitly declare effects.** A pure operation uses `effects: []`; a missing `effects` field is invalid.
4. **Identity fields are safety-critical.** `module`, `workflow`, `task`, operation ids, operation names, effect ids, capability ids, and policy ids must be safe strings.
5. **Lowering consumes AST-shaped drafts only.** A blocked, invalid, or unparsable draft is never lowered.

## Current scope

This is still a compact public-demo AST, not the full private canonical schema. It supports the bounded demo fields:

- `module`
- `workflow`
- `task`
- `operations[]`
- `claims[]`
- `evidence[]`
- `policies[]`
- `holes[]`
- `input_type`, `output_type`, `return`, `transaction`, `environment`, `executable`

## What this prevents

- YAML list roots pretending to be modules
- prose strings inside `claims`, `policies`, `holes`, or `operations`
- operations with missing effect declarations
- unsafe or whitespace-padded safety-critical identifiers
- lowerer execution over arbitrary raw dictionaries

## What remains later

Phase 2 is about strict intake shape. Later phases should add:

- evidence ledger binding beyond bundled public fixtures
- full operation-spec-role validation
- richer workflow semantic profiles
- structured policy predicate AST support
