from ainir.negative_conformance_harness import run_negative_conformance_corpus


def test_negative_conformance_corpus_and_deterministic_robustness_harness(tmp_path):
    summary = run_negative_conformance_corpus("negative_conformance_corpus.yaml", tmp_path / "negative_conformance")
    assert summary["overall_status"] == "passed"
    assert summary["case_count"] >= 40
    assert summary["failed"] == 0
