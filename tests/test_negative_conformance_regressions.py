from __future__ import annotations

import json
from pathlib import Path

import pytest

from ainir.cli import main
from ainir.core import DraftModule, load_draft
from ainir.verifier import verify_draft


def report_for(raw: dict) -> dict:
    return verify_draft(DraftModule(raw=raw)).as_dict()


def rules(report: dict) -> set[str]:
    return {f["rule"] for f in report["findings"]}


def _verify(path: Path):
    return verify_draft(load_draft(path))


def test_malformed_section_items_are_invalid_not_crashes():
    for field in ["claims", "policies", "holes"]:
        raw = {
            "module": "demo.negative_conformance",
            "workflow": "CreateUser",
            "task": "CreateUserRequest",
            "operations": [{"id": "op.noop", "op": "data.noop", "effects": []}],
            field: ["not an object"],
        }
        report = report_for(raw)
        assert report["status"] == "invalid"
        assert "S017.section_item_must_be_object" in rules(report)


def test_trailing_space_effect_ids_are_invalid():
    raw = {
        "module": "demo.negative_conformance",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "operations": [
            {
                "id": "op.pay",
                "op": "payment.charge.real",
                "effects": ["effect.external.payment.charge.real "],
                "capabilities": ["cap.payment.charge.real"],
            }
        ],
    }
    report = report_for(raw)
    assert report["status"] == "invalid"
    assert "S012.effect_id_whitespace_forbidden" in rules(report)


def test_alias_with_trailing_space_is_invalid_before_aliasing():
    raw = {
        "module": "demo.negative_conformance",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "operations": [
            {
                "id": "op.pay",
                "op": "payment.charge.real",
                "effects": ["real_payment "],
                "capabilities": ["cap.payment.charge.real"],
            }
        ],
    }
    report = report_for(raw)
    assert report["status"] == "invalid"
    assert "S012.effect_id_whitespace_forbidden" in rules(report)


def test_create_user_workflow_alias_still_blocks_direct_email():
    raw = {
        "module": "demo.negative_conformance",
        "workflow": "Create_User",
        "task": "CreateUserRequest",
        "operations": [
            {
                "id": "op.email",
                "op": "email.send.real",
                "effects": ["effect.external.notification.email.real"],
                "capabilities": ["cap.email.send"],
            }
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert "P005.no_direct_email_in_create_user" in rules(report)


def test_unknown_real_payment_effect_is_blocked_by_prefix():
    raw = {
        "module": "demo.negative_conformance",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "operations": [
            {
                "id": "op.pay",
                "op": "payment.charge.capture",
                "effects": ["effect.external.payment.capture.real"],
                "capabilities": ["cap.payment.charge.real"],
            }
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert "P003.no_real_payment_in_public_demo" in rules(report)


def test_semantic_empty_known_workflow_is_blocked():
    raw = {
        "module": "demo.negative_conformance",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "input_type": "PaymentIntentInput",
        "output_type": "PaymentResult",
        "operations": [{"id": "op.noop", "op": "data.noop", "effects": []}],
        "return": "state",
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert rules(report) & {"W010.workflow_semantic_profile_missing", "W011.workflow_semantic_empty"}


def test_capability_items_must_be_strings():
    raw = {
        "module": "demo.negative_conformance",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "operations": [
            {"id": "op.write", "op": "db.write", "effects": ["effect.storage.db.write"], "capabilities": [{}]}
        ],
    }
    report = report_for(raw)
    assert report["status"] == "invalid"
    assert "S016.capability_id_required" in rules(report)


def test_yaml_root_list_cli_returns_invalid_without_traceback(tmp_path, capsys):
    path = tmp_path / "list.yaml"
    path.write_text("- not\n- an\n- object\n", encoding="utf-8")
    code = main(["verify", str(path), "--json"])
    captured = capsys.readouterr()
    assert code == 2
    data = json.loads(captured.out)
    assert data["status"] == "invalid"
    assert "S000.draft_root_must_be_object" in {f["rule"] for f in data["findings"]}


def test_malformed_yaml_cli_returns_invalid_without_traceback(tmp_path, capsys):
    path = tmp_path / "bad.yaml"
    path.write_text("module: [\n", encoding="utf-8")
    code = main(["verify", str(path), "--json"])
    captured = capsys.readouterr()
    assert code == 2
    data = json.loads(captured.out)
    assert data["status"] == "invalid"
    assert "S000.yaml_parse_error" in {f["rule"] for f in data["findings"]}


def test_verified_claim_with_fake_evidence_fails(tmp_path):
    draft = tmp_path / "fake_evidence.yaml"
    draft.write_text(
        """
module: demo.fake_evidence
workflow: CreateUser
task: CreateUserRequest
input_type: CreateUserInput
output_type: CreateUserResult
claims:
  - id: claim.fake
    status: verified
    evidence:
      - id: unchecked
        kind: verifier_report
operations:
  - id: op.insert_user
    op: db.insert_user
    effects: [effect.storage.db.write]
    capabilities: [cap.db.user.write]
    policies: [policy.user_email_unique]
  - id: op.insert_outbox
    op: outbox.insert_welcome_email_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
return: state
""",
        encoding="utf-8",
    )
    report = _verify(draft)
    assert report.status in {"invalid", "blocked"}
    assert any(f.rule == "TR001.verified_claim_requires_ledger_bound_evidence" for f in report.findings)


def test_payment_effect_real_variant_fails(tmp_path):
    draft = tmp_path / "payment_real_variant.yaml"
    draft.write_text(
        """
module: demo.payment_real_variant
workflow: OrderPayment
task: ProcessOrderPaymentWorker
input_type: PaymentIntentInput
output_type: PaymentResult
operations:
  - id: op.validate_amount
    op: payment.validate_amount
    effects: [effect.payment.validate.Amount]
    capabilities: [cap.payment.validate]
  - id: op.pay
    op: payment.charge.real
    effects: [effect.external.payment.charge.real.v2]
    capabilities: [cap.payment.charge.real]
return: state
""",
        encoding="utf-8",
    )
    report = _verify(draft)
    assert report.status == "blocked"
    assert any(f.rule == "P003.no_real_payment_in_public_demo" for f in report.findings)


def test_payment_effect_noncanonical_alias_fails(tmp_path):
    draft = tmp_path / "payment_alias.yaml"
    draft.write_text(
        """
module: demo.payment_alias
workflow: OrderPayment
task: ProcessOrderPaymentWorker
input_type: PaymentIntentInput
output_type: PaymentResult
operations:
  - id: op.validate_amount
    op: payment.validate_amount
    effects: [effect.payment.validate.Amount]
    capabilities: [cap.payment.validate]
  - id: op.pay
    op: payment.charge.real
    effects: [payment.charge.real]
    capabilities: [cap.payment.charge.real]
return: state
""",
        encoding="utf-8",
    )
    report = _verify(draft)
    assert report.status == "blocked"


def test_safety_critical_op_name_with_empty_effects_fails(tmp_path):
    draft = tmp_path / "hidden_real_payment.yaml"
    draft.write_text(
        """
module: demo.hidden_real_payment
workflow: OrderPayment
task: ProcessOrderPaymentWorker
input_type: PaymentIntentInput
output_type: PaymentResult
operations:
  - id: op.validate_amount
    op: payment.validate_amount
    effects: [effect.payment.validate.Amount]
    capabilities: [cap.payment.validate]
  - id: op.pay
    op: payment.charge.real
    effects: []
return: state
""",
        encoding="utf-8",
    )
    report = _verify(draft)
    assert report.status == "blocked"
    assert any(f.rule.startswith("P020") or f.rule.startswith("P003") for f in report.findings)


def test_password_reset_noop_semantics_fail(tmp_path):
    draft = tmp_path / "password_noop.yaml"
    draft.write_text(
        """
module: demo.password_noop
workflow: PasswordReset
task: PasswordResetRequest
input_type: PasswordResetInput
output_type: AcceptedResponse
operations:
  - id: op.noop
    op: password_reset.noop
    effects: []
return: state
""",
        encoding="utf-8",
    )
    report = _verify(draft)
    assert report.status == "blocked"
    assert any(f.rule in {"W010.workflow_semantic_profile_missing", "W011.workflow_semantic_empty"} for f in report.findings)


def test_raw_secret_variant_fails(tmp_path):
    draft = tmp_path / "raw_secret_variant.yaml"
    draft.write_text(
        """
module: demo.raw_secret_variant
workflow: PasswordReset
task: PasswordResetRequest
input_type: PasswordResetInput
output_type: AcceptedResponse
operations:
  - id: op.store_raw_token
    op: db.store_raw_reset_token
    effects: [effect.secret.raw_token.store.v2]
    capabilities: [cap.secret.write]
  - id: op.outbox
    op: outbox.insert_password_reset_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
return: state
""",
        encoding="utf-8",
    )
    report = _verify(draft)
    assert report.status == "blocked"
    assert any(f.rule == "P001.no_raw_secret_persistence" for f in report.findings)


def test_unknown_external_effect_fails(tmp_path):
    draft = tmp_path / "unknown_external.yaml"
    draft.write_text(
        """
module: demo.unknown_external
workflow: CreateUser
task: CreateUserRequest
input_type: CreateUserInput
output_type: CreateUserResult
policies:
  - id: policy.no_direct_email_in_create_user
  - id: policy.transactional_outbox_required
  - id: policy.user_email_unique
transaction:
  id: tx.create_user
  mode: atomic
  includes: [op.insert_user, op.insert_outbox]
operations:
  - id: op.normalize
    op: data.normalize_email
    effects: []
  - id: op.check
    op: db.exists_user_by_email
    effects: [effect.storage.db.read]
    capabilities: [cap.db.user.read]
  - id: op.insert_user
    op: db.insert_user
    effects: [effect.storage.db.write]
    capabilities: [cap.db.user.write]
    policies: [policy.user_email_unique]
  - id: op.insert_outbox
    op: outbox.insert_welcome_email_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
  - id: op.call_api
    op: http.call
    effects: [effect.external.api.call]
    capabilities: [cap.http.call]
return: state
""",
        encoding="utf-8",
    )
    report = _verify(draft)
    assert report.status == "blocked"
    assert any(f.rule == "P008.no_unallowlisted_external_effect" for f in report.findings)


def test_reserved_word_task_lowering_safe(tmp_path):
    draft = tmp_path / "reserved_task.yaml"
    draft.write_text(
        """
module: demo.reserved_task
workflow: CreateUser
task: class
input_type: CreateUserInput
output_type: CreateUserResult
policies:
  - id: policy.no_direct_email_in_create_user
  - id: policy.transactional_outbox_required
  - id: policy.user_email_unique
transaction:
  id: tx.create_user
  mode: atomic
  includes: [op.insert_user, op.insert_outbox]
operations:
  - id: op.normalize
    op: data.normalize_email
    effects: []
  - id: op.check
    op: db.exists_user_by_email
    effects: [effect.storage.db.read]
    capabilities: [cap.db.user.read]
  - id: op.insert_user
    op: db.insert_user
    effects: [effect.storage.db.write]
    capabilities: [cap.db.user.write]
    policies: [policy.user_email_unique]
  - id: op.insert_outbox
    op: outbox.insert_welcome_email_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
return: state
""",
        encoding="utf-8",
    )
    report = _verify(draft)
    assert report.status == "passed"
    from ainir.lowering import _safe_function_name
    assert _safe_function_name("class") == "runClass"



def test_verified_claim_with_self_attested_checked_evidence_fails():
    raw = {
        "module": "demo.fake_checked_evidence",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "input_type": "CreateUserInput",
        "output_type": "CreateUserResult",
        "claims": [
            {
                "id": "claim.fake",
                "status": "verified",
                "evidence": [
                    {"id": "ev.fake", "kind": "verifier_report", "checked": True, "reliability": 0.99}
                ],
            }
        ],
        "operations": [
            {"id": "op.insert_user", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.user.write"]},
            {"id": "op.insert_outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert "TR001.verified_claim_requires_ledger_bound_evidence" in rules(report)


def test_verified_claim_with_model_checked_evidence_fails():
    raw = {
        "module": "demo.fake_model_checked",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "input_type": "CreateUserInput",
        "output_type": "CreateUserResult",
        "claims": [
            {
                "id": "claim.fake",
                "status": "verified",
                "evidence": [
                    {"id": "ev.fake", "kind": "verifier_report", "checked": True, "reliability": 0.99, "source": "llm_output", "checked_by": "model"}
                ],
            }
        ],
        "operations": [
            {"id": "op.insert_user", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.user.write"]},
            {"id": "op.insert_outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert "TR001.verified_claim_requires_ledger_bound_evidence" in rules(report)


def test_hidden_http_call_without_effects_fails():
    raw = {
        "module": "demo.hidden_http",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "input_type": "CreateUserInput",
        "output_type": "CreateUserResult",
        "operations": [
            {"id": "op.insert_user", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.user.write"]},
            {"id": "op.insert_outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
            {"id": "op.api", "op": "http.call", "effects": [], "capabilities": ["cap.http.call"]},
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert "P025.undeclared_implied_external_effect" in rules(report)


def test_account_delete_permanent_effect_variant_fails():
    raw = {
        "module": "demo.account_delete_permanent",
        "workflow": "AccountDeletion",
        "task": "ProcessAccountDeletionWorker",
        "input_type": "AccountDeletionJob",
        "output_type": "DeletionResult",
        "operations": [
            {"id": "op.auth", "op": "auth.check", "effects": ["effect.auth.authorization.check"], "capabilities": ["cap.auth.check"]},
            {"id": "op.del", "op": "account.delete", "effects": ["effect.destructive.account.delete.permanent"], "capabilities": ["cap.account.delete"]},
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert "P004.no_hard_delete_in_public_demo" in rules(report)


def test_account_delete_permanent_op_without_effect_fails():
    raw = {
        "module": "demo.account_delete_permanent_op",
        "workflow": "AccountDeletion",
        "task": "ProcessAccountDeletionWorker",
        "input_type": "AccountDeletionJob",
        "output_type": "DeletionResult",
        "operations": [
            {"id": "op.auth", "op": "auth.check", "effects": ["effect.auth.authorization.check"], "capabilities": ["cap.auth.check"]},
            {"id": "op.delete", "op": "account.delete.permanent", "effects": [], "capabilities": ["cap.account.delete"]},
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert rules(report) & {"P022.undeclared_implied_hard_delete_effect", "P004.no_hard_delete_in_public_demo"}


def test_newsletter_marketing_email_without_effect_fails():
    raw = {
        "module": "demo.newsletter_marketing_hidden",
        "workflow": "NewsletterSignup",
        "task": "NewsletterSignupRequest",
        "input_type": "NewsletterSignupInput",
        "output_type": "AcceptedResponse",
        "policies": [{"id": "policy.no_marketing_without_consent"}],
        "operations": [
            {"id": "op.consent", "op": "consent.enforce", "effects": []},
            {"id": "op.outbox", "op": "outbox.insert_double_opt_in", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
            {"id": "op.marketing", "op": "email.marketing.real", "effects": [], "capabilities": ["cap.email.send"]},
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert "P021.undeclared_implied_email_effect" in rules(report)


def test_sandbox_payment_without_idempotency_fails():
    raw = {
        "module": "demo.sandbox_payment_no_idempotency",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "input_type": "PaymentIntentInput",
        "output_type": "PaymentResult",
        "operations": [
            {"id": "op.validate", "op": "payment.validate_amount", "effects": ["effect.payment.validate.Amount"], "capabilities": ["cap.payment.validate"]},
            {"id": "op.intent", "op": "db.insert_payment_intent", "effects": ["effect.db.write.PaymentIntent"], "capabilities": ["cap.db.payment.write"]},
            {"id": "op.sandbox", "op": "payment.charge.sandbox", "effects": ["effect.external.payment.charge.sandbox"], "capabilities": ["cap.payment.charge.sandbox"]},
        ],
    }
    report = report_for(raw)
    assert report["status"] == "blocked"
    assert "P009.payment_charge_requires_idempotency" in rules(report)


def test_sandbox_payment_with_idempotency_policy_passes():
    raw = {
        "module": "demo.sandbox_payment_idempotent",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "input_type": "PaymentIntentInput",
        "output_type": "PaymentResult",
        "policies": [{"id": "policy.payment_idempotency_required"}, {"id": "policy.no_real_payment_in_beta"}],
        "operations": [
            {"id": "op.auth", "op": "auth.check_order_payment", "effects": ["effect.auth.authorization.check"], "capabilities": ["cap.auth.check"]},
            {"id": "op.validate", "op": "payment.validate_amount", "effects": ["effect.payment.validate.Amount"], "capabilities": ["cap.payment.validate"]},
            {"id": "op.intent", "op": "db.insert_payment_intent", "effects": ["effect.db.write.PaymentIntent"], "capabilities": ["cap.db.payment.write"]},
            {"id": "op.sandbox", "op": "payment.charge.sandbox", "effects": ["effect.external.payment.charge.sandbox"], "capabilities": ["cap.payment.charge.sandbox"], "policies": ["policy.payment_idempotency_required"]},
        ],
    }
    report = report_for(raw)
    assert report["status"] == "passed"
