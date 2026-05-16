from __future__ import annotations

from pathlib import Path

from ainir.phase21_release_readiness_eval import run_phase21_launch_readiness_eval


def test_phase21_launch_readiness_passes(tmp_path: Path) -> None:
    report = run_phase21_launch_readiness_eval(tmp_path / "phase21")
    assert report["overall_status"] == "passed"
    assert report["private_github_trial_ready"] is True
    assert report["public_release_ready"] is False
    assert report["production_runtime_ready"] is False
    assert report["v1_final_ready"] is False
