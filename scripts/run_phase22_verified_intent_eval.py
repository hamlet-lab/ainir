from __future__ import annotations

import argparse
import json
from pathlib import Path

from ainir.phase22_verified_intent_eval import run_phase22_verified_intent_eval
from ainir.temp_paths import ainir_temp_str


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=ainir_temp_str("ainir_phase22_verified_intent_results"))
    args = parser.parse_args()
    summary = run_phase22_verified_intent_eval(args.out_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["overall_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
