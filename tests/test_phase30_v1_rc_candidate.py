from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v1_rc_docs_exist_and_status_is_bounded():
    required = [
        "docs/v1_rc_candidate.md",
        "docs/v1_rc_scope.md",
        "docs/v1_api_surface.md",
        "docs/v1_acceptance_criteria.md",
        "docs/v1_known_limitations.md",
        "release/v1_0_rc_candidate_manifest.yaml",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "v1.0 RC candidate" in readme
    assert "not a v1.0 final" in readme
    assert "not a production runtime" in readme


def test_phase30_quick_integrity_mode_skips_heavy_phase26(tmp_path):
    from ainir.phase30_v1_rc_candidate import run_phase30_v1_rc_candidate_check

    report = run_phase30_v1_rc_candidate_check(tmp_path / "phase30_quick", mode="quick-integrity")
    assert report["overall_status"] == "passed"
    assert report["mode"] == "quick-integrity"
    assert report["decision"] == "quick_integrity_passed_full_release_check_not_run"
    steps = {step["name"]: step for step in report["steps"]}
    assert steps["phase26_private_trial"]["status"] == "not_run"
