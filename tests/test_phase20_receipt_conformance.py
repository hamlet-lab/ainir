from __future__ import annotations

from pathlib import Path

from ainir.golden_trace_harness import run_golden_traces
from ainir.phase20_receipt_conformance_eval import run_phase20_receipt_conformance_eval


def test_golden_traces_include_trust_receipt_replay(tmp_path: Path) -> None:
    summary = run_golden_traces("golden_traces.yaml", tmp_path / "golden")
    assert summary["overall_status"] == "passed"
    assert summary["trace_count"] == summary["receipt_replay_passed"]
    for result in summary["results"]:
        assert result["trust_receipt_status"] == "replayed"


def test_phase20_receipt_conformance_eval(tmp_path: Path) -> None:
    summary = run_phase20_receipt_conformance_eval(tmp_path / "phase20")
    assert summary["overall_status"] == "passed"
    assert summary["passed"] == summary["case_count"]
