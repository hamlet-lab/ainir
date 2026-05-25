import json
import subprocess
import sys
from pathlib import Path

from ainir.core import load_draft
from ainir.execution_context import TrustedExecutionContext
from ainir.trust_gate import evaluate_trust_gate
from ainir.verifier import verify_draft


def test_complex_yaml_mapping_key_is_invalid_not_traceback(tmp_path: Path) -> None:
    path = tmp_path / "complex_key.yaml"
    path.write_text(
        "? [module]\n: demo.shadow\nworkflow: CreateUser\ntask: CreateUserRequest\noperations: []\n",
        encoding="utf-8",
    )
    report = verify_draft(load_draft(path))
    assert report.status == "invalid"
    assert any(f.rule == "S071.yaml_complex_mapping_key_forbidden" for f in report.findings)


def test_non_utf8_source_is_invalid_not_traceback(tmp_path: Path) -> None:
    path = tmp_path / "bad_utf8.yaml"
    path.write_bytes(b"\xff\xfe\x00bad")
    report = verify_draft(load_draft(path))
    assert report.status == "invalid"
    assert any(f.rule == "S072.yaml_utf8_decode_error" for f in report.findings)


def test_receipt_id_includes_trusted_context_source_and_purpose() -> None:
    draft_path = Path("examples/create_user_outbox_safe/draft.yaml")
    draft = load_draft(draft_path)
    first = evaluate_trust_gate(
        draft,
        TrustedExecutionContext.from_environment("public_demo", source="cli", purpose="trust_gate"),
    )
    second = evaluate_trust_gate(
        draft,
        TrustedExecutionContext.from_environment("public_demo", source="host", purpose="verified_intent_export"),
    )
    assert first.receipt["receipt_id"] != second.receipt["receipt_id"]


def test_public_demo_refuses_production_context_handoff() -> None:
    draft_path = Path("examples/create_user_outbox_safe/draft.yaml")
    decision = evaluate_trust_gate(
        load_draft(draft_path),
        TrustedExecutionContext.from_environment("production", source="cli", purpose="trust_gate"),
    )
    assert decision.status == "refused"
    assert decision.lowering_allowed is False
    assert decision.handoff_allowed is False
    assert "trusted_execution_context" in decision.failed_gates



def test_lowering_refuses_public_demo_production_context(tmp_path: Path) -> None:
    from ainir.core import load_draft
    from ainir.execution_context import TrustedExecutionContext
    from ainir.lowering import lower_to_typescript
    from ainir.verifier import verify_draft

    draft = load_draft("examples/create_user_outbox_safe/draft.yaml")
    ctx = TrustedExecutionContext.from_environment("production", source="cli", purpose="lowering")
    report = verify_draft(draft, ctx)
    assert report.status == "passed"
    try:
        lower_to_typescript(draft, report, tmp_path / "lowered", ctx)
    except RuntimeError as exc:
        assert "L013.public_demo_production_context_not_lowerable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("public demo lowerer must refuse production context")


def test_demo_does_not_lower_when_trust_gate_refuses_production(tmp_path: Path) -> None:
    from ainir.cli import main

    out_dir = tmp_path / "demo_prod"
    code = main(["demo", "--env", "production", "--out-dir", str(out_dir)])
    assert code == 2
    lowered_dir = out_dir / "lowered"
    assert not lowered_dir.exists() or not list(lowered_dir.glob("*.lowered.ts"))


def test_receipt_replay_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    from ainir.execution_context import TrustedExecutionContext
    from ainir.trust_receipt_store import issue_trust_receipt, replay_trust_receipt

    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, TrustedExecutionContext.public_demo())
    original = json.loads(Path(issued.receipt_path).read_text(encoding="utf-8"))
    shadowed = '{"receipt_id":"shadowed", "status":"passed_shadow", ' + Path(issued.receipt_path).read_text(encoding="utf-8").strip()[1:]
    dup = tmp_path / "duplicate_key.receipt.json"
    dup.write_text(shadowed, encoding="utf-8")
    replay = replay_trust_receipt(dup, "examples/create_user_outbox_safe/draft.yaml", TrustedExecutionContext.public_demo())
    assert replay.overall_status == "failed"
    assert any(c["check"] == "receipt_json_valid" and c["actual"] == "json_duplicate_key" for c in replay.checks)


def test_receipt_replay_handles_malformed_json_without_traceback(tmp_path: Path) -> None:
    from ainir.execution_context import TrustedExecutionContext
    from ainir.trust_receipt_store import replay_trust_receipt

    malformed = tmp_path / "bad.receipt.json"
    malformed.write_text("{bad json", encoding="utf-8")
    replay = replay_trust_receipt(malformed, "examples/create_user_outbox_safe/draft.yaml", TrustedExecutionContext.public_demo())
    assert replay.overall_status == "failed"
    assert any(c["check"] == "receipt_json_valid" and c["actual"] == "json_decode_error" for c in replay.checks)


def test_receipt_replay_rejects_json_array_root_without_traceback(tmp_path: Path) -> None:
    from ainir.execution_context import TrustedExecutionContext
    from ainir.trust_receipt_store import replay_trust_receipt

    array_root = tmp_path / "array.receipt.json"
    array_root.write_text("[]", encoding="utf-8")
    replay = replay_trust_receipt(array_root, "examples/create_user_outbox_safe/draft.yaml", TrustedExecutionContext.public_demo())
    assert replay.overall_status == "failed"
    assert any(c["check"] == "receipt_json_valid" and c["actual"] == "json_root_not_object" for c in replay.checks)
