from __future__ import annotations

from ainir.core import DraftModule
from ainir.verifier import verify_draft
from ainir.safety_registry import get_registry


def _rules(raw: dict) -> set[str]:
    return {f.rule for f in verify_draft(DraftModule(raw=raw)).findings}


def _status(raw: dict) -> str:
    return verify_draft(DraftModule(raw=raw)).status


def test_registry_is_single_source_for_aliases():
    reg = get_registry()
    normalized, was_alias = reg.normalize_effect("payment.finalize.production")
    assert was_alias
    assert normalized == "effect.external.payment.provider_call.real"
    assert "payment_real" in reg.classify_effect(normalized)


def test_claude_source_cannot_self_attest_verified_claim():
    raw = {
        "module": "demo.fake_claude_evidence",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "claims": [
            {
                "id": "claim.fake",
                "status": "verified",
                "evidence": [
                    {
                        "id": "ev.fake",
                        "kind": "verifier_report",
                        "checked": True,
                        "reliability": 0.99,
                        "source": "claude",
                        "checked_by": "claude",
                    }
                ],
            }
        ],
        "operations": [
            {"id": "op.insert_user", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.user.write"]},
            {"id": "op.insert_outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    }
    assert _status(raw) == "blocked"
    assert "T001.verified_claim_requires_ledger_bound_evidence" in _rules(raw)


def test_payment_finalize_production_operation_is_blocked_even_without_real_word():
    raw = {
        "module": "demo.payment_finalize_prod",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "operations": [
            {"id": "op.amount", "op": "payment.validate_amount", "effects": ["effect.payment.validate.Amount"], "capabilities": ["cap.payment.validate"]},
            {"id": "op.intent", "op": "db.insert_payment_intent", "effects": ["effect.storage.payment_intent.write"], "capabilities": ["cap.db.payment.write"], "policies": ["policy.payment_idempotency_required"]},
            {"id": "op.finalize", "op": "payment.finalize.production", "effects": [], "capabilities": ["cap.payment.charge.real"], "policies": ["policy.payment_idempotency_required"]},
        ],
    }
    assert _status(raw) == "blocked"
    assert "P020.undeclared_implied_payment_effect" in _rules(raw)


def test_effect_real_variant_alias_is_visible_and_blocked():
    raw = {
        "module": "demo.payment_prod_alias",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "operations": [
            {"id": "op.amount", "op": "payment.validate_amount", "effects": ["effect.payment.validate.Amount"], "capabilities": ["cap.payment.validate"]},
            {"id": "op.intent", "op": "db.insert_payment_intent", "effects": ["effect.storage.payment_intent.write"], "capabilities": ["cap.db.payment.write"], "policies": ["policy.payment_idempotency_required"]},
            {"id": "op.finalize", "op": "payment.finalize.production", "effects": ["payment.finalize.production"], "capabilities": ["cap.payment.charge.real"], "policies": ["policy.payment_idempotency_required"]},
        ],
    }
    assert _status(raw) == "blocked"
    assert "N003.safety_critical_effect_alias_visible" in _rules(raw)
    assert "P003.no_real_payment_in_public_demo" in _rules(raw)
