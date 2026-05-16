from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import os
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ainir.phase21_release_readiness_eval import run_phase21_launch_readiness_eval


def _default_out_dir() -> str:
    return str(Path(os.environ.get("AINIR_TEMP_ROOT") or tempfile.gettempdir()) / "ainir_phase21_launch_readiness")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run AiNIR Pre-v1 Phase 21 launch-readiness gate.")
    parser.add_argument("--out-dir", default=_default_out_dir())
    args = parser.parse_args()
    report = run_phase21_launch_readiness_eval(args.out_dir)
    print(f"AiNIR Phase 21 launch readiness: {report['overall_status']}")
    print(f"decision: {report['decision']}")
    print(f"report: {Path(args.out_dir) / 'phase21_launch_readiness_report.json'}")
    print(f"summary: {Path(args.out_dir) / 'phase21_launch_readiness_summary.md'}")
    return 0 if report.get("overall_status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
