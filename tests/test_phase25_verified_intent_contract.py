from pathlib import Path

from ainir.phase25_verified_intent_contract_eval import run_phase25_verified_intent_contract_eval


def test_phase25_verified_intent_contract_eval_passes(tmp_path: Path) -> None:
    summary = run_phase25_verified_intent_contract_eval(tmp_path / "phase25")
    assert summary["overall_status"] == "passed"
    assert summary["case_count"] >= 16
