from __future__ import annotations

import argparse
from pathlib import Path
import os
import tempfile

from ainir.phase30_v1_rc_candidate import run_phase30_v1_rc_candidate_check
from ainir.phase26_private_trial import _safe_trial_temp_parent


def _default_out_dir() -> str:
    return str(_safe_trial_temp_parent() / "ainir_phase30_v1_rc_candidate")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run AiNIR v1.0 RC candidate check")
    parser.add_argument("--out-dir", default=_default_out_dir())
    parser.add_argument("--mode", choices=["quick-integrity", "full"], default="full", help="quick-integrity skips the heavier Phase 26 private-trial simulation")
    args = parser.parse_args()
    report = run_phase30_v1_rc_candidate_check(Path(args.out_dir), mode=args.mode)
    print(f"AiNIR Phase 30 v1.0 RC candidate check: {report['overall_status']}")
    print(f"decision: {report['decision']}")
    print(f"reports: {report.get('output_dir', args.out_dir)}")
    return 0 if report["overall_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
