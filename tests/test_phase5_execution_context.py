from pathlib import Path

import yaml

from ainir.core import DraftModule
from ainir.execution_context import TrustedExecutionContext
from ainir.verifier import verify_draft
from ainir.lowering import lower_to_typescript


def _draft(**overrides):
    base = {
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
    }
    base.update(overrides)
    return DraftModule(base)


def _rules(report):
    return {f.rule for f in report.findings}


def test_draft_environment_is_untrusted_metadata_not_policy_source():
    draft = _draft(environment="production")
    report = verify_draft(draft, TrustedExecutionContext.from_environment("test"))
    assert report.status == "passed"
    assert "X001.draft_environment_is_untrusted_metadata" in _rules(report)


def test_real_external_effect_blocked_by_trusted_test_context_even_if_draft_claims_production():
    draft = _draft(
        environment="production",
        operations=[
            {"id": "op.normalize", "op": "data.normalize_email", "effects": []},
            {"id": "op.lookup", "op": "db.exists_user_by_email", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.read"]},
            {"id": "op.insert", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"], "policies": ["policy.user_email_unique"]},
            {"id": "op.outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
            {"id": "op.email", "op": "email.send.real", "effects": ["effect.external.notification.email.real"], "capabilities": ["cap.email.send"]},
        ],
    )
    report = verify_draft(draft, TrustedExecutionContext.from_environment("test"))
    assert report.status == "blocked"
    assert "P006.no_real_external_effect_in_test_context" in _rules(report)
    assert "X001.draft_environment_is_untrusted_metadata" in _rules(report)


def test_context_rejects_unknown_environment():
    try:
        TrustedExecutionContext.from_environment("prod-but-trust-me")
    except ValueError as exc:
        assert "Unsupported trusted environment" in str(exc)
    else:
        raise AssertionError("unknown trusted environment should be rejected")


def test_lowering_refuses_blocked_context_sensitive_draft(tmp_path: Path):
    draft = _draft(
        environment="production",
        operations=[
            {"id": "op.normalize", "op": "data.normalize_email", "effects": []},
            {"id": "op.lookup", "op": "db.exists_user_by_email", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.read"]},
            {"id": "op.insert", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"], "policies": ["policy.user_email_unique"]},
            {"id": "op.outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
            {"id": "op.email", "op": "email.send.real", "effects": ["effect.external.notification.email.real"], "capabilities": ["cap.email.send"]},
        ],
    )
    report = verify_draft(draft, TrustedExecutionContext.from_environment("test"))
    assert report.status == "blocked"
    try:
        lower_to_typescript(draft, report, tmp_path)
    except RuntimeError as exc:
        assert "Refusing to lower" in str(exc)
    else:
        raise AssertionError("blocked draft should not lower")
