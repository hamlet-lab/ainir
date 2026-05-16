# Pre-launch Check

Run:

```bash
python scripts/run_prelaunch_check.py --out-dir /tmp/ainir_prelaunch_results
```

The check runs the public launch candidate pipeline:

1. unit/regression tests;
2. public demo;
3. negative conformance corpus;
4. golden trace replay;
5. safe outbox lowering;
6. empty draft rejection;
7. missing examples rejection.

The generated report is written to:

```text
/tmp/ainir_prelaunch_results/prelaunch_report.json
/tmp/ainir_prelaunch_results/prelaunch_summary.md
```

Generated check results are ignored by Git via `.gitignore` and should not be committed unless deliberately archived.
