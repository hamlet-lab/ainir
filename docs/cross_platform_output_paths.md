# Cross-platform output paths

AiNIR commands write demo and review artifacts to an output directory. Public examples use a temporary directory so generated files do not pollute the repository checkout.

On macOS / Linux:

```bash
python -m ainir demo --out-dir "${TMPDIR:-/tmp}/ainir_demo_results"
```

On Windows PowerShell:

```powershell
python -m ainir demo --out-dir "$env:TEMP\ainir_demo_results"
```

For built-in review scripts, you may omit `--out-dir`; defaults use `tempfile.gettempdir()` and can be overridden with `AINIR_TEMP_ROOT`.

```bash
python scripts/run_phase26_private_trial.py
python scripts/run_phase30_v1_rc_candidate_check.py
```

This repository should not commit generated result folders such as `demo_results`, `prelaunch_results`, or `review_results`.

## Avoid repo-local temp roots

For private-trial and release-candidate checks, keep `TMP`, `TEMP`, and
`AINIR_TEMP_ROOT` outside the repository checkout. A repo-local temp directory
can make a trial copy see its own generated output. The Phase 26 runner now
falls back to a sibling temp copy if the OS temp directory resolves inside the
repo, and it ignores common local temp folders such as `.ainir_local_tmp/` and
`ainir_phase*_trial_*/`. Still, the recommended practice is to use the OS temp
directory or an explicit path outside the checkout.

Examples:

```bash
AINIR_TEMP_ROOT=/tmp/ainir python scripts/run_phase26_private_trial.py
```

```powershell
$env:AINIR_TEMP_ROOT = "$env:TEMP\ainir"
python scripts/run_phase26_private_trial.py
```
