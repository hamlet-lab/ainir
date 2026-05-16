from pathlib import Path

from ainir.core import iter_example_drafts, load_draft
from ainir.verifier import verify_draft


def test_public_demo_expectations():
    root = Path(__file__).resolve().parents[1]
    results = {}
    for path in iter_example_drafts(root):
        report = verify_draft(load_draft(path))
        results[path.parent.name] = report

    assert results["create_user_outbox_safe"].status == "passed"
    for name, report in results.items():
        if name != "create_user_outbox_safe":
            assert report.status == "blocked"
            assert report.critical_count > 0
