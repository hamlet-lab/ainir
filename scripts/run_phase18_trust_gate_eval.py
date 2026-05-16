from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ainir.phase18_trust_gate_eval import run_phase18_trust_gate_eval


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AiNIR Pre-v1 Phase 18 Trust Gate evaluation.")
    parser.add_argument("--out-dir", default="phase18_trust_gate_results")
    args = parser.parse_args()
    summary = run_phase18_trust_gate_eval(args.out_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get("overall_status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
