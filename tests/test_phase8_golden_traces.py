from pathlib import Path

from ainir.golden_trace_harness import run_golden_traces


def test_golden_traces_replay(tmp_path):
    report = run_golden_traces("golden_traces.yaml", tmp_path / "golden", "public_demo")
    assert report["overall_status"] == "passed"
    assert report["trace_count"] >= 8
    assert report["failed"] == 0
    safe = next(r for r in report["results"] if r["trace_id"] == "GT-PUB-01-safe-create-user-outbox")
    assert safe["lowering_status"] == "lowered"
    assert safe["output_hash"].startswith("sha256:")
