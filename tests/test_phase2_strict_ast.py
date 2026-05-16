from __future__ import annotations

from ainir.core import DraftModule
from ainir.draft_ast import DraftAST, parse_draft_ast
from ainir.verifier import verify_draft


def test_valid_safe_fixture_parses_to_strict_ast():
    raw = {
        "module": "demo.create_user_outbox_safe",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "input_type": "CreateUserInput",
        "output_type": "CreateUserResult",
        "operations": [
            {"id": "op.insert_user", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.user.write"]},
            {"id": "op.insert_outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
        "return": "state",
    }
    result = parse_draft_ast(DraftModule(raw=raw))
    assert not result.has_critical
    assert isinstance(result.ast, DraftAST)
    assert result.ast.workflow == "CreateUser"
    assert len(result.ast.operations) == 2


def test_verifier_uses_ast_normalized_workflow_alias_before_semantic_rules():
    raw = {
        "module": "demo.negative_conformance",
        "workflow": "Create_User",
        "task": "CreateUserRequest",
        "operations": [
            {"id": "op.email", "op": "email.send.real", "effects": ["effect.external.notification.email.real"], "capabilities": ["cap.email.send"]},
        ],
    }
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert any(f.rule == "P005.no_direct_email_in_create_user" for f in report.findings)


def test_ast_stops_malformed_operation_before_semantic_verifier():
    raw = {
        "module": "demo.bad",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "operations": ["not an operation object"],
    }
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "invalid"
    assert any(f.rule == "S004.operation_must_be_object" for f in report.findings)


def test_ast_requires_effects_field_explicitly():
    raw = {
        "module": "demo.bad",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "operations": [{"id": "op.noop", "op": "data.noop"}],
    }
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "invalid"
    assert any(f.rule == "S010.effects_required" for f in report.findings)


def test_ast_optional_fields_are_typed():
    raw = {
        "module": "demo.bad",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "input_type": ["not", "a", "string"],
        "operations": [{"id": "op.noop", "op": "data.noop", "effects": []}],
    }
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "invalid"
    assert any(f.rule == "S070.input_type_must_be_string" for f in report.findings)


def test_ast_rejects_unknown_top_level_fields():
    raw = {
        "module": "demo.bad",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "surprise_hidden_semantics": {"charge_real_card": True},
        "operations": [{"id": "op.noop", "op": "data.normalize_email", "effects": []}],
    }
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "invalid"
    assert any(f.rule == "S060.unknown_top_level_field" for f in report.findings)


def test_ast_rejects_unknown_operation_fields():
    raw = {
        "module": "demo.bad",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "operations": [
            {
                "id": "op.noop",
                "op": "data.normalize_email",
                "effects": [],
                "hidden_call": {"url": "https://example.invalid"},
            }
        ],
    }
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "invalid"
    assert any(f.rule == "S061.unknown_operation_field" for f in report.findings)


def test_ast_rejects_unknown_claim_and_evidence_fields():
    raw = {
        "module": "demo.bad",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "claims": [
            {
                "id": "claim.example",
                "status": "verified",
                "statement": "Example.",
                "hidden_claim_semantics": True,
                "evidence": [{"id": "evidence.demo.safe_outbox", "kind": "verifier_report", "surprise": "model"}],
            }
        ],
        "operations": [{"id": "op.noop", "op": "data.normalize_email", "effects": []}],
    }
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "invalid"
    assert any(f.rule == "S062.unknown_claim_field" for f in report.findings)
    assert any(f.rule == "S063.unknown_claim_evidence_field" for f in report.findings)
