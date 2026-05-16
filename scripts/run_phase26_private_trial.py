
from __future__ import annotations

import argparse
from pathlib import Path
import os
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ainir.phase26_private_trial import run_phase26_private_trial, _safe_trial_temp_parent


def _default_out_dir() -> str:
    return str(_safe_trial_temp_parent() / "ainir_phase26_private_trial")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run AiNIR Pre-v1 Phase 26 local GitHub private-trial simulation.")
    parser.add_argument("--out-dir", default=_default_out_dir())
    args = parser.parse_args()
    report = run_phase26_private_trial(args.out_dir)
    print(f"AiNIR Phase 26 private-trial simulation: {report['overall_status']}")
    print(f"decision: {report['decision']}")
    actual_out = Path(report.get('output_dir', args.out_dir))
    print(f"report: {actual_out / 'phase26_private_trial_report.json'}")
    print(f"summary: {actual_out / 'phase26_private_trial_summary.md'}")
    return 0 if report.get("overall_status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
