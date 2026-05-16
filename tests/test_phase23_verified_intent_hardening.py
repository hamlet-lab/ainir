from pathlib import Path

from ainir.phase23_verified_intent_hardening_eval import run_phase23_verified_intent_hardening_eval


def test_phase23_verified_intent_hardening_eval_passes(tmp_path: Path):
    summary = run_phase23_verified_intent_hardening_eval(tmp_path)
    assert summary["overall_status"] == "passed"
    assert summary["case_count"] >= 10
