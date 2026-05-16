from pathlib import Path

from ainir.phase24_verified_intent_semantic_eval import run_phase24_verified_intent_semantic_eval


def test_phase24_verified_intent_semantic_eval_passes(tmp_path: Path):
    summary = run_phase24_verified_intent_semantic_eval(tmp_path)
    assert summary["overall_status"] == "passed"
    assert summary["case_count"] >= 12
