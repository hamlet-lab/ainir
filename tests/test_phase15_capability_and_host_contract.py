from __future__ import annotations

from pathlib import Path

from ainir.core import DraftModule, load_draft
from ainir.lowering import lower_to_typescript
from ainir.verifier import verify_draft


def _base_create_user() -> dict:
    return {
        "module": "demo.create_user_outbox_safe",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "input_type": "CreateUserInput",
        "output_type": "CreateUserResult",
        "return": "state",
        "policies": [
            {"id": "policy.no_direct_email_in_create_user"},
            {"id": "policy.transactional_outbox_required"},
            {"id": "policy.user_email_unique"},
        ],
        "transaction": {"id": "tx.create_user", "mode": "atomic", "includes": ["op.insert_user", "op.outbox"], "rollback_on": ["failure"]},
        "operations": [
            {"id": "op.normalize_email", "op": "data.normalize_email", "effects": []},
            {"id": "op.find", "op": "db.exists_user_by_email", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.read"]},
            {"id": "op.insert_user", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"], "policies": ["policy.user_email_unique"]},
            {"id": "op.outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    }


def test_extra_capability_on_pure_operation_is_refused():
    raw = _base_create_user()
    raw["operations"][0]["capabilities"] = ["cap.payment.charge.real"]
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert "O012.operation_declares_unallowed_capability" in {f.rule for f in report.findings}


def test_extra_capability_on_db_operation_is_refused():
    raw = _base_create_user()
    raw["operations"][1]["capabilities"] = ["cap.db.read", "cap.admin.root"]
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert "O012.operation_declares_unallowed_capability" in {f.rule for f in report.findings}


def test_lowered_code_uses_canonical_operation_envelope_for_dispatch(tmp_path):
    root = Path(__file__).resolve().parents[1]
    draft = load_draft(root / "examples" / "create_user_outbox_safe" / "draft.yaml")
    report = verify_draft(draft)
    assert report.status == "passed"
    target = lower_to_typescript(draft, report, tmp_path / "out")
    text = target.read_text(encoding="utf-8")
    assert "callOperation(envelope_" in text
    assert "ctx.call(\"op." not in text
    assert 'canonicalOp: string;' in text
    assert 'canonicalOp": "db.insert_user"' in text


def test_transaction_runtime_hooks_are_required_in_lowered_code(tmp_path):
    root = Path(__file__).resolve().parents[1]
    draft = load_draft(root / "examples" / "create_user_outbox_safe" / "draft.yaml")
    report = verify_draft(draft)
    assert report.status == "passed"
    target = lower_to_typescript(draft, report, tmp_path / "out")
    text = target.read_text(encoding="utf-8")
    assert "enforceTransaction(envelope: TransactionEnvelope" in text
    assert "runTransaction<T>(envelope: TransactionEnvelope" in text
    assert "ctx.runTransaction(" in text
    assert "ctx.runTransaction ??" not in text
    assert "host_enforcement_contract_required" in text
