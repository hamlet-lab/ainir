from pathlib import Path

from ainir.core import DraftModule
from ainir.execution_context import TrustedExecutionContext
from ainir.lowering import lower_to_typescript
from ainir.lowering_gate import assess_lowering_eligibility
from ainir.verifier import verify_draft


def _safe_create_user():
    return DraftModule({
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
        "transaction": {"id": "tx.create_user", "mode": "atomic", "includes": ["op.insert", "op.outbox"]},
        "operations": [
            {"id": "op.normalize", "op": "data.normalize_email", "effects": []},
            {"id": "op.lookup", "op": "db.exists_user_by_email", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.read"]},
            {"id": "op.insert", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"], "policies": ["policy.user_email_unique"]},
            {"id": "op.outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    })


def _unsafe_payment():
    return DraftModule({
        "module": "demo.order_payment_real_payment_blocked",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "input_type": "PaymentIntentInput",
        "output_type": "PaymentResult",
        "return": "state",
        "operations": [
            {"id": "op.intent", "op": "payment.intent.create", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"]},
            {"id": "op.pay", "op": "payment.charge.real", "effects": ["effect.external.payment.charge.real"], "capabilities": ["cap.payment.charge.real"], "policies": ["policy.payment_idempotency_required"]},
        ],
    })


def test_lowering_gate_allows_fresh_passed_report():
    ctx = TrustedExecutionContext.from_environment("public_demo")
    draft = _safe_create_user()
    report = verify_draft(draft, ctx)
    gate = assess_lowering_eligibility(draft, report, ctx)
    assert report.status == "passed"
    assert gate.allowed


def test_lowering_gate_rejects_stale_report_reused_for_unsafe_draft(tmp_path: Path):
    ctx = TrustedExecutionContext.from_environment("public_demo")
    safe_report = verify_draft(_safe_create_user(), ctx)
    unsafe = _unsafe_payment()
    gate = assess_lowering_eligibility(unsafe, safe_report, ctx)
    assert not gate.allowed
    assert {f.rule for f in gate.findings} >= {"L004.lowering_fresh_verification_failed", "L005.lowering_report_identity_mismatch"}
    try:
        lower_to_typescript(unsafe, safe_report, tmp_path, ctx)
    except RuntimeError as exc:
        assert "Refusing to lower" in str(exc)
    else:
        raise AssertionError("stale passed report must not authorize unsafe draft lowering")


def test_lowering_emits_host_enforcement_contract(tmp_path: Path):
    ctx = TrustedExecutionContext.from_environment("staging")
    draft = _safe_create_user()
    report = verify_draft(draft, ctx)
    target = lower_to_typescript(draft, report, tmp_path, ctx)
    text = target.read_text(encoding="utf-8")
    assert "enforceModule" in text
    assert "enforceOperation" in text
    assert "riskFamilies" in text
    assert '"trustedEnvironment": "staging"' in text
    assert '"verificationStatus": "passed"' in text


def test_lowering_gate_rejects_unresolved_holes_even_when_not_executable():
    ctx = TrustedExecutionContext.from_environment("public_demo")
    draft = _safe_create_user()
    draft.raw["executable"] = False
    draft.raw["holes"] = [{"id": "hole.normalize_impl", "resolved": False}]
    report = verify_draft(draft, ctx)
    assert report.status == "passed"
    gate = assess_lowering_eligibility(draft, report, ctx)
    assert not gate.allowed
    assert any(f.rule == "L007.lowering_forbids_unresolved_holes" for f in gate.findings)


def test_lowering_gate_rejects_unresolved_ambiguity_even_when_not_executable():
    ctx = TrustedExecutionContext.from_environment("public_demo")
    draft = _safe_create_user()
    draft.raw["executable"] = False
    draft.raw["ambiguity"] = {"status": "requires_clarification", "unresolved_ambiguities": [{"slot": "x", "question": "Clarify x?"}]}
    report = verify_draft(draft, ctx)
    assert report.status == "passed"
    gate = assess_lowering_eligibility(draft, report, ctx)
    assert not gate.allowed
    assert any(f.rule == "L008.lowering_forbids_unresolved_ambiguity" for f in gate.findings)


def test_strict_ast_rejects_unknown_unresolved_ambiguity_field():
    ctx = TrustedExecutionContext.from_environment("public_demo")
    draft = _safe_create_user()
    draft.raw["ambiguity"] = {"status": "requires_clarification", "unresolved_ambiguities": [{"slot": "x", "hidden_hint": "do not expose"}]}
    report = verify_draft(draft, ctx)
    assert report.status in {"invalid", "blocked"}
    assert "S076.unknown_unresolved_ambiguity_field" in {f.rule for f in report.findings}
