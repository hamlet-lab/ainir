from __future__ import annotations

from pathlib import Path

from ainir.core import DraftModule, load_draft
from ainir.lowering import lower_to_typescript
from ainir.verifier import verify_draft


def rules(raw: dict) -> set[str]:
    return {f.rule for f in verify_draft(DraftModule(raw=raw)).findings}


def status(raw: dict) -> str:
    return verify_draft(DraftModule(raw=raw)).status


def base_create_user_ops():
    return [
        {"id": "op.normalize", "op": "data.normalize_email", "effects": []},
        {"id": "op.check", "op": "db.exists_user_by_email", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.user.read"]},
        {"id": "op.insert_user", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.user.write"], "policies": ["policy.user_email_unique"]},
        {"id": "op.outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
    ]


def base_create_user():
    return {
        "module": "demo.create_user_tx_case",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "input_type": "CreateUserInput",
        "output_type": "CreateUserResult",
        "policies": [
            {"id": "policy.no_direct_email_in_create_user"},
            {"id": "policy.transactional_outbox_required"},
            {"id": "policy.user_email_unique"},
        ],
        "transaction": {"id": "tx.create_user", "mode": "atomic", "includes": ["op.insert_user", "op.outbox"]},
        "operations": base_create_user_ops(),
        "return": "state",
    }


def test_create_user_requires_transaction_binding():
    raw = base_create_user()
    raw.pop("transaction")
    assert status(raw) == "blocked"
    assert "TX001.transaction_required" in rules(raw)


def test_transaction_requires_atomic_mode():
    raw = base_create_user()
    raw["transaction"].pop("mode")
    assert status(raw) == "blocked"
    assert "TX005.transaction_mode_required" in rules(raw)


def test_transaction_includes_must_resolve_and_be_contiguous():
    raw = base_create_user()
    raw["operations"] = [
        raw["operations"][0],
        raw["operations"][2],
        {"id": "op.other", "op": "data.normalize_email", "effects": []},
        raw["operations"][3],
        raw["operations"][1],
    ]
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert {f.rule for f in report.findings} & {"TX013.transaction_includes_must_be_contiguous", "TX015.transaction_role_order_violation"}


def test_transaction_role_order_is_enforced():
    raw = base_create_user()
    raw["operations"] = [
        raw["operations"][0],
        raw["operations"][1],
        raw["operations"][3],
        raw["operations"][2],
    ]
    raw["transaction"]["includes"] = ["op.outbox", "op.insert_user"]
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert "TX015.transaction_role_order_violation" in {f.rule for f in report.findings}


def test_lowering_emits_transaction_enforcement_hook(tmp_path):
    root = Path(__file__).resolve().parents[1]
    draft = load_draft(root / "examples" / "create_user_outbox_safe" / "draft.yaml")
    report = verify_draft(draft)
    assert report.status == "passed"
    target = lower_to_typescript(draft, report, tmp_path / "out")
    text = target.read_text(encoding="utf-8")
    assert "TransactionEnvelope" in text
    assert "enforceTransaction" in text
    assert "runTransaction" in text
    assert '"transactionId": "tx.create_user"' in text


def test_unknown_transaction_field_is_refused_by_strict_ast():
    raw = base_create_user()
    raw["transaction"]["hidden_call"] = {"url": "https://example.invalid"}
    report = verify_draft(DraftModule(raw=raw))
    assert report.status in {"invalid", "blocked"}
    assert "S067.unknown_transaction_field" in {f.rule for f in report.findings}


def test_unknown_transactions_item_field_is_refused_by_strict_ast():
    raw = base_create_user()
    raw.pop("transaction")
    raw["transactions"] = [{"id": "tx.create_user", "mode": "atomic", "includes": ["op.insert_user", "op.outbox"], "hidden_call": {"url": "https://example.invalid"}}]
    report = verify_draft(DraftModule(raw=raw))
    assert report.status in {"invalid", "blocked"}
    assert "S068.unknown_transactions_field" in {f.rule for f in report.findings}
