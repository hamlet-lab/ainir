# Suggested GitHub Repository Settings

## Repository name

`ainir`

## Description

A semantic safety layer that blocks unsafe AI-generated program semantics before execution.

## Website

Leave blank at first, or link to a future project page.

## Topics

Recommended topics:

- `ai-safety`
- `llm`
- `code-generation`
- `intermediate-representation`
- `agentic-ai`
- `policy-as-code`
- `semantic-ir`

## Visibility

Recommended launch sequence:

1. Create the repository as private.
2. Upload and check the repo contents.
3. Run `python scripts/run_prelaunch_check.py --out-dir /tmp/ainir_prelaunch_results`.
4. Confirm the full private RC archive is not included.
5. Switch only this public demo repository to public.

Do not publish the private RC archive, full corpus, extended hardening suite, or enterprise policy packs unless deliberately releasing them later.
