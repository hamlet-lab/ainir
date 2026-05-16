from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import tempfile

from ainir.phase25_verified_intent_contract_eval import run_phase25_verified_intent_contract_eval


def _default_out_dir() -> str:
    return str(Path(os.environ.get("AINIR_TEMP_ROOT") or tempfile.gettempdir()) / "ainir_phase25_verified_intent_contract")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run AiNIR pre-v1 Phase 25 VerifiedIntentPacket strict contract evaluation.")
    parser.add_argument("--out-dir", default=_default_out_dir())
    args = parser.parse_args()
    report = run_phase25_verified_intent_contract_eval(Path(args.out_dir))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("overall_status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
