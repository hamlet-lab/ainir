from __future__ import annotations

from pathlib import Path

import yaml

from ainir.core import load_draft
from ainir.execution_context import TrustedExecutionContext
from ainir.trust_gate import evaluate_trust_gate
from ainir.verifier import verify_draft

ROOT = Path(__file__).resolve().parents[1]
SAFE = ROOT / "examples" / "create_user_outbox_safe" / "draft.yaml"


def test_complex_yaml_mapping_key_is_reported_not_traceback(tmp_path: Path) -> None:
    path = tmp_path / "complex_key.yaml"
    path.write_text("? [module]\n: demo.shadow\nworkflow: CreateUser\ntask: CreateUserRequest\noperations: []\n", encoding="utf-8")
    report = verify_draft(load_draft(path), TrustedExecutionContext.public_demo())
    assert report.status == "invalid"
    assert any(f.rule == "S071.yaml_complex_mapping_key_forbidden" for f in report.findings)


def test_non_utf8_yaml_is_reported_not_traceback(tmp_path: Path) -> None:
    path = tmp_path / "bad_encoding.yaml"
    path.write_bytes(b"\xff\xfe\x00bad")
    report = verify_draft(load_draft(path), TrustedExecutionContext.public_demo())
    assert report.status == "invalid"
    assert any(f.rule == "S072.yaml_utf8_decode_error" for f in report.findings)


def test_receipt_id_binds_context_source_and_purpose() -> None:
    draft = load_draft(SAFE)
    a = evaluate_trust_gate(draft, TrustedExecutionContext.from_environment("public_demo", source="cli", purpose="trust_gate")).as_dict()["receipt"]
    b = evaluate_trust_gate(draft, TrustedExecutionContext.from_environment("public_demo", source="host", purpose="verified_intent_export")).as_dict()["receipt"]
    assert a["canonical_draft_sha256"] == b["canonical_draft_sha256"]
    assert a["raw_source_sha256"] == b["raw_source_sha256"]
    assert a["receipt_id"] != b["receipt_id"]


def test_public_production_context_does_not_handoff_or_lower() -> None:
    draft = load_draft(SAFE)
    decision = evaluate_trust_gate(draft, TrustedExecutionContext.from_environment("production", source="cli", purpose="trust_gate")).as_dict()
    assert decision["status"] == "refused"
    assert decision["handoff_allowed"] is False
    assert decision["lowering_allowed"] is False
    assert "trusted_execution_context" in decision["failed_gates"]
    assert any(f["rule"] == "X010.production_context_not_supported" for f in decision["findings"])
