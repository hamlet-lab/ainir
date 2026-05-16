from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ainir.phase20_receipt_conformance_eval import run_phase20_receipt_conformance_eval


def _default_out_dir() -> str:
    return str(Path(os.environ.get("AINIR_TEMP_ROOT") or tempfile.gettempdir()) / "ainir_phase20_receipt_conformance")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run AiNIR Pre-v1 Phase 20 TrustReceipt conformance integration checks.")
    parser.add_argument("--out-dir", default=_default_out_dir())
    args = parser.parse_args()
    summary = run_phase20_receipt_conformance_eval(args.out_dir)
    print(f"AiNIR Phase 20 receipt conformance eval: {summary['overall_status']}")
    print(f"cases: {summary['passed']}/{summary['case_count']} passed")
    print(f"report: {Path(args.out_dir) / 'phase20_receipt_conformance_eval_report.json'}")
    return 0 if summary["overall_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
