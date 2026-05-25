from pathlib import Path

import pytest

from ainir.core import DraftModule, load_draft
from ainir.lowering import lower_to_typescript
from ainir.verifier import verify_draft
from ainir.cli import main


def test_empty_draft_is_invalid_and_not_lowered(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("{}\n", encoding="utf-8")
    draft = load_draft(path)
    report = verify_draft(draft)
    assert report.status == "invalid"
    assert report.critical_count > 0
    with pytest.raises(RuntimeError):
        lower_to_typescript(draft, report, tmp_path / "out")


def test_missing_examples_dir_fails_demo(tmp_path):
    empty_dir = tmp_path / "no_examples"
    empty_dir.mkdir()
    out_dir = tmp_path / "demo_out"
    code = main(["demo", "--examples-dir", str(empty_dir), "--out-dir", str(out_dir)])
    assert code == 2
    summary = (out_dir / "summary.yaml").read_text(encoding="utf-8")
    assert "overall_status: failed" in summary
    assert "No example draft files were found" in summary


def test_lowerer_rejects_unallowlisted_type(tmp_path):
    draft = load_draft("examples/create_user_outbox_safe/draft.yaml")
    draft.raw["input_type"] = "EvilType"
    report = verify_draft(draft)
    assert report.status == "passed"
    with pytest.raises(RuntimeError) as exc:
        lower_to_typescript(draft, report, tmp_path / "out")
    assert "L009.lowering_forbids_unallowed_input_type" in str(exc.value)


def test_lowerer_sanitizes_filename_and_function(tmp_path):
    from ainir.lowering import _safe_slug, _safe_function_name

    assert _safe_slug("demo.safe-name", fallback="module") == "demo.safe-name"
    assert _safe_function_name("CreateUserRequest") == "createUserRequest"


def test_verified_claim_with_llm_output_source_fails():
    raw = {
        "module": "demo.fake_llm_source",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "input_type": "CreateUserInput",
        "output_type": "CreateUserResult",
        "claims": [
            {
                "id": "claim.fake",
                "status": "verified",
                "evidence": [
                    {"id": "ev.fake", "kind": "verifier_report", "checked": True, "reliability": 0.99, "source": "llm_output"}
                ],
            }
        ],
        "operations": [
            {"id": "op.insert_user", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.user.write"]},
            {"id": "op.insert_outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    }
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert any(f.rule == "TR001.verified_claim_requires_ledger_bound_evidence" for f in report.findings)
