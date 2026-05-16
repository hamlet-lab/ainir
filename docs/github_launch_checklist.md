# GitHub Launch Checklist

## Files

- [ ] Use the tracked repository contents from `hamlet-lab/ainir`.
- [ ] Do not include private archive ZIPs.
- [ ] Do not include generated check folders.
- [ ] Confirm `LICENSE` is Apache-2.0.
- [ ] Confirm `NOTICE` names Lee Yoon Kyu / [AIOE].

## Commands

Run from repository root:

```bash
python scripts/run_prelaunch_check.py --out-dir /tmp/ainir_prelaunch_results
```

Expected:

```text
overall_status: passed
```

## GitHub settings

Description:

```text
A semantic safety layer that blocks unsafe AI-generated program semantics before execution.
```

Topics:

```text
ai-safety
llm
code-generation
intermediate-representation
agentic-ai
policy-as-code
semantic-ir
```

## Launch wording

Use:

```text
AiNIR is a v1.0 RC candidate public demo for inspecting AI-generated program semantics before execution. It is not a v1.0 final release and not a production runtime.
```

Avoid:

```text
AiNIR v1.0 final
production compiler
production payment/deletion runtime
complete formal proof system
```


## v1.0 RC candidate required pre-upload command

```bash
python -m ainir phase30-v1-rc-candidate-check --out-dir /tmp/ainir_phase30_v1_rc_candidate
python scripts/run_phase26_private_trial.py --out-dir /tmp/ainir_phase26_private_trial
```

Keep the repository private until README rendering and GitHub Actions have been checked.
