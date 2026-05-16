from pathlib import Path
import subprocess
import os
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}


def _verify(tmp_path, name, data):
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    proc = subprocess.run([sys.executable, "-m", "ainir", "verify", str(path), "--json"], cwd=ROOT, env=ENV, text=True, capture_output=True)
    return proc


def _order_payment_base():
    return {
        "module": "demo.order_payment",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "input_type": "PaymentIntentInput",
        "output_type": "PaymentResult",
        "return": "state",
        "policies": [
            {"id": "policy.no_real_payment_in_beta"},
            {"id": "policy.payment_idempotency_required"},
        ],
        "operations": [
            {"id":"op.auth","op":"auth.check_order_payment","effects":["effect.auth.authorization.check"],"capabilities":["cap.auth.check"]},
            {"id":"op.amount","op":"payment.validate_amount","effects":["effect.payment.validate.Amount"],"capabilities":["cap.payment.validate"]},
            {"id":"op.intent","op":"db.insert_payment_intent","effects":["effect.storage.payment_intent.write"],"capabilities":["cap.db.write"]},
        ],
    }


def test_real_payment_operation_alias_cannot_be_disguised_with_sandbox_effect(tmp_path):
    data = _order_payment_base()
    data["operations"].append({"id":"op.pay","op":"payment.finalize.production","effects":["effect.external.payment.charge.sandbox"],"capabilities":["cap.payment.charge.sandbox"],"policies":["policy.payment_idempotency_required"]})
    proc = _verify(tmp_path, "payment_disguised", data)
    assert proc.returncode != 0, proc.stdout
    assert "O010.operation_forbidden_in_public_demo" in proc.stdout or "O003.operation_not_allowed" in proc.stdout


def test_raw_token_persistence_role_cannot_be_disguised_with_hash_effect(tmp_path):
    data = {
        "module":"demo.password_reset", "workflow":"PasswordReset", "task":"PasswordResetRequest",
        "input_type":"PasswordResetInput", "output_type":"AcceptedResponse", "return":"state",
        "policies":[{"id":"policy.no_user_enumeration"}],
        "operations":[
            {"id":"op.norm","op":"data.normalize_email","effects":[]},
            {"id":"op.lookup","op":"db.find_user_for_password_reset","effects":["effect.storage.db.read"],"capabilities":["cap.db.read"]},
            {"id":"op.raw","op":"db.store_raw_reset_token","effects":["effect.secret.token.hash"],"capabilities":["cap.secret.hash"]},
            {"id":"op.safe","op":"secret.hash_password_reset_token","effects":["effect.secret.token.hash"],"capabilities":["cap.secret.hash"]},
            {"id":"op.policy","op":"policy.enforce_no_user_enumeration","effects":[]},
            {"id":"op.out","op":"outbox.insert_password_reset_requested","effects":["effect.storage.outbox.write"],"capabilities":["cap.outbox.write"]},
        ]
    }
    proc = _verify(tmp_path, "raw_token_role", data)
    assert proc.returncode != 0, proc.stdout
    assert "forbidden" in proc.stdout.lower()


def test_registered_safe_pii_export_operations_are_not_blocked_by_keyword_classifier(tmp_path):
    data = {
        "module":"demo.pii_export", "workflow":"PIIExportRequest", "task":"PIIExportRequest",
        "input_type":"PIIExportJob", "output_type":"ExportPackageRef", "return":"state",
        "policies":[
            {"id":"policy.pii_export_authorization_required"},
            {"id":"policy.export_package_must_be_encrypted"},
            {"id":"policy.export_fields_allowlist_required"},
        ],
        "operations":[
            {"id":"op.auth","op":"auth.check_pii_export_authorization","effects":["effect.auth.authorization.check"],"capabilities":["cap.auth.check"]},
            {"id":"op.allow","op":"policy.enforce_export_field_allowlist","effects":[]},
            {"id":"op.read","op":"db.read_user_pii_bundle","effects":["effect.privacy.pii.read"],"capabilities":["cap.pii.read"]},
            {"id":"op.encrypt","op":"export.encrypt_pii_export_package","effects":["effect.crypto.encrypt"],"capabilities":["cap.crypto.encrypt"]},
            {"id":"op.store","op":"storage.write_encrypted_pii_export_package","effects":["effect.storage.export_package.write"],"capabilities":["cap.export.storage.write"]},
        ]
    }
    proc = _verify(tmp_path, "pii_export_safe", data)
    assert proc.returncode == 0, proc.stdout


def test_registered_operation_extra_unknown_effect_fails(tmp_path):
    data = {
        "module":"demo.create_user_outbox_safe", "workflow":"CreateUser", "task":"CreateUserRequest",
        "input_type":"CreateUserInput", "output_type":"CreateUserResult", "return":"state",
        "policies":[{"id":"policy.no_direct_email_in_create_user"},{"id":"policy.transactional_outbox_required"},{"id":"policy.user_email_unique"}],
        "operations":[
            {"id":"op.normalize_email","op":"data.normalize_email","effects":["effect.file.write"],"capabilities":["cap.file.write"]},
            {"id":"op.find","op":"db.exists_user_by_email","effects":["effect.storage.db.read"],"capabilities":["cap.db.read"]},
            {"id":"op.insert_user","op":"db.insert_user","effects":["effect.storage.db.write"],"capabilities":["cap.db.write"],"policies":["policy.user_email_unique"]},
            {"id":"op.outbox","op":"outbox.insert_welcome_email_requested","effects":["effect.storage.outbox.write"],"capabilities":["cap.outbox.write"]},
        ],
        "transaction":{"id":"tx.create_user","mode":"atomic","includes":["op.insert_user","op.outbox"],"rollback_on":["failure"]}
    }
    proc = _verify(tmp_path, "extra_effect", data)
    assert proc.returncode != 0, proc.stdout
    assert "O009.operation_declares_unallowed_effect" in proc.stdout
