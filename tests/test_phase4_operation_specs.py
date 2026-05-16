from __future__ import annotations

from ainir.core import DraftModule
from ainir.operation_registry import get_operation_registry
from ainir.verifier import verify_draft


def _report(raw: dict):
    return verify_draft(DraftModule(raw=raw))


def _rules(raw: dict) -> set[str]:
    return {f.rule for f in _report(raw).findings}


def test_operation_registry_resolves_aliases_to_specs():
    reg = get_operation_registry()
    resolved, was_alias = reg.resolve_id("insert_user")
    assert was_alias is True
    assert resolved == "db.insert_user"
    assert reg.spec_for("insert_user").semantic_roles == {"create_user"}


def test_unknown_operation_in_known_workflow_is_blocked():
    raw = {
        "module": "demo.unknown_op",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "operations": [
            {"id": "op.mystery", "op": "custom.mystery", "effects": [], "capabilities": []},
        ],
    }
    report = _report(raw)
    assert report.status == "blocked"
    assert "O001.operation_spec_required" in _rules(raw)


def test_operation_spec_required_effect_is_enforced():
    raw = {
        "module": "demo.insert_missing_effect",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "operations": [
            {"id": "op.insert_user", "op": "db.insert_user", "effects": [], "capabilities": ["cap.db.user.write"]},
            {"id": "op.outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    }
    report = _report(raw)
    assert report.status == "blocked"
    assert "O004.operation_required_effect_missing" in _rules(raw)


def test_placeholder_operation_does_not_satisfy_semantic_role():
    raw = {
        "module": "demo.placeholder_role",
        "workflow": "AccountDeletion",
        "task": "ProcessAccountDeletionWorker",
        "operations": [
            {"id": "op.auth", "op": "auth.check_account_deletion_authorization", "effects": ["effect.auth.authorization.check"], "capabilities": ["cap.auth.check"]},
            {"id": "op.placeholder", "op": "grace.period.placeholder", "effects": [], "capabilities": []},
        ],
    }
    report = _report(raw)
    assert report.status == "blocked"
    assert "W010.workflow_semantic_profile_missing" in _rules(raw)


def test_registered_semantic_roles_can_satisfy_account_deletion_profile():
    raw = {
        "module": "demo.account_deletion_gate_only",
        "workflow": "AccountDeletion",
        "task": "ProcessAccountDeletionWorker",
        "policies": [{"id": "policy.no_hard_delete_in_beta"}],
        "operations": [
            {"id": "op.auth", "op": "auth.check_account_deletion_authorization", "effects": ["effect.auth.authorization.check"], "capabilities": ["cap.auth.check"]},
            {"id": "op.reauth", "op": "auth.verify_recent_reauthentication", "effects": ["effect.auth.reauthentication.check"], "capabilities": ["cap.auth.reauthentication"]},
            {"id": "op.legal_hold", "op": "legal_hold.check", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.account.read"]},
            {"id": "op.grace", "op": "grace_period.check", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.account.read"]},
        ],
    }
    report = _report(raw)
    assert report.status == "passed", report.as_dict()


def test_operation_alias_normalizes_then_binds_to_spec():
    raw = {
        "module": "demo.create_user_aliases",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "policies": [
            {"id": "policy.no_direct_email_in_create_user"},
            {"id": "policy.transactional_outbox_required"},
            {"id": "policy.user_email_unique"},
        ],
        "transaction": {"id": "tx.create_user", "mode": "atomic", "includes": ["op.insert", "op.outbox"]},
        "operations": [
            {"id": "op.normalize", "op": "normalize_email", "effects": []},
            {"id": "op.check", "op": "find_user_by_email", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.user.read"]},
            {"id": "op.insert", "op": "insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.user.write"], "policies": ["policy.user_email_unique"]},
            {"id": "op.outbox", "op": "outbox.insert_welcome_email", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    }
    report = _report(raw)
    assert report.status == "passed", report.as_dict()
