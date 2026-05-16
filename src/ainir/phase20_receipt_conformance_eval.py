from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .golden_trace_harness import run_golden_traces
from .phase19_trust_receipt_eval import run_phase19_trust_receipt_eval
from .temp_paths import recreate_output_dir

ROOT = Path(__file__).resolve().parents[2]


def run_phase20_receipt_conformance_eval(out_dir: str | Path = "phase20_receipt_conformance_results") -> dict[str, Any]:
    """Run the Phase 20 TrustReceipt conformance integration checks.

    Phase 19 made receipt issue/replay possible. Phase 20 makes receipt replay a
    first-class conformance expectation in golden traces and release checks.
    """
    out = recreate_output_dir(out_dir, protected_roots=[ROOT])

    golden = run_golden_traces("golden_traces.yaml", out / "golden_traces", "public_demo")
    phase19 = run_phase19_trust_receipt_eval(out / "phase19_receipt_replay")

    receipt_failures = []
    for result in golden.get("results", []):
        if result.get("trust_receipt_status") != "replayed":
            receipt_failures.append({
                "trace_id": result.get("trace_id"),
                "trust_receipt_status": result.get("trust_receipt_status"),
                "notes": result.get("notes"),
            })

    cases = [
        {
            "case_id": "golden_traces_include_trust_receipt_replay",
            "expected": "passed",
            "actual": golden.get("overall_status"),
            "passed": golden.get("overall_status") == "passed" and not receipt_failures,
            "details": {"receipt_failures": receipt_failures},
        },
        {
            "case_id": "phase19_receipt_replay_regressions_still_pass",
            "expected": "passed",
            "actual": phase19.get("overall_status"),
            "passed": phase19.get("overall_status") == "passed",
        },
    ]
    summary = {
        "phase": "pre_v1_phase20_trust_receipt_conformance_integration",
        "overall_status": "passed" if all(c["passed"] for c in cases) else "failed",
        "case_count": len(cases),
        "passed": sum(1 for c in cases if c["passed"]),
        "failed": sum(1 for c in cases if not c["passed"]),
        "golden_trace_count": golden.get("trace_count"),
        "golden_receipt_replay_passed": golden.get("receipt_replay_passed"),
        "cases": cases,
    }
    (out / "phase20_receipt_conformance_eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
