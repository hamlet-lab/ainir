from __future__ import annotations

import json
from pathlib import Path

import yaml

from ainir.core import load_draft
from ainir.execution_context import TrustedExecutionContext
from ainir.trust_gate import evaluate_trust_gate
from ainir.trust_receipt_store import issue_trust_receipt, replay_trust_receipt
from ainir.verifier import verify_draft

ROOT = Path(__file__).resolve().parents[1]
SAFE = ROOT / "examples/create_user_outbox_safe/draft.yaml"


def test_no_claims_no_evidence_cannot_pass_trust_gate_or_lowering(tmp_path: Path) -> None:
    raw = yaml.safe_load(SAFE.read_text(encoding="utf-8"))
    raw.pop("claims", None)
    draft_path = tmp_path / "no_claims.yaml"
    draft_path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")

    decision = evaluate_trust_gate(load_draft(draft_path), TrustedExecutionContext.public_demo()).as_dict()
    assert decision["status"] == "refused"
    assert decision["handoff_allowed"] is False
    assert decision["lowering_allowed"] is False
    assert "evidence_ledger_binding" in decision["failed_gates"]
    assert "evidence_ledger_binding" not in decision["satisfied_gates"]
    assert decision["receipt"]["evidence_summary"]["gate_status"] == "failed"
    assert decision["receipt"]["evidence_summary"]["claim_count"] == 0


def test_duplicate_yaml_keys_are_rejected_before_trust_gate(tmp_path: Path) -> None:
    text = SAFE.read_text(encoding="utf-8")
    text = text.replace("workflow: CreateUser\n", "workflow: AccountDeletion\nworkflow: CreateUser\n", 1)
    draft_path = tmp_path / "duplicate_workflow.yaml"
    draft_path.write_text(text, encoding="utf-8")

    draft = load_draft(draft_path)
    decision = evaluate_trust_gate(draft, TrustedExecutionContext.public_demo()).as_dict()
    assert decision["status"] == "invalid"
    assert decision["lowering_allowed"] is False
    rules = {f["rule"] for f in decision["findings"]}
    assert "S070.yaml_duplicate_key" in rules
    assert decision["receipt"]["raw_source_sha256"].startswith("sha256:")


def test_receipt_binds_raw_source_hash_not_only_canonical_hash(tmp_path: Path) -> None:
    issued = issue_trust_receipt(SAFE, tmp_path, TrustedExecutionContext.public_demo())
    receipt = dict(issued.receipt)
    assert receipt["raw_source_sha256"].startswith("sha256:")
    assert receipt["canonical_draft_sha256"] == receipt["draft_hash"]

    tampered = tmp_path / "tampered_raw_hash.receipt.json"
    receipt["raw_source_sha256"] = "sha256:" + "0" * 64
    tampered.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    replay = replay_trust_receipt(tampered, SAFE, TrustedExecutionContext.public_demo())
    assert replay.overall_status == "failed"
    assert any(c["check"] == "raw_source_sha256" and c["status"] == "failed" for c in replay.checks)


def test_complex_yaml_key_is_invalid_without_traceback(tmp_path: Path) -> None:
    path = tmp_path / "complex_key.yaml"
    path.write_text(
        """
? [module]
: demo.create_user_outbox_safe
workflow: CreateUser
operation: create_user_with_outbox
intent:
  summary: create user
operations: []
""",
        encoding="utf-8",
    )
    report = verify_draft(load_draft(path), TrustedExecutionContext.public_demo())
    assert report.status == "invalid"
    assert any(f.rule == "S071.yaml_complex_mapping_key_forbidden" for f in report.findings)


def test_non_utf8_yaml_is_invalid_without_traceback(tmp_path: Path) -> None:
    path = tmp_path / "bad_utf8.yaml"
    path.write_bytes(b"\xff\xfe\x00bad")
    report = verify_draft(load_draft(path), TrustedExecutionContext.public_demo())
    assert report.status == "invalid"
    assert any(f.rule == "S072.yaml_utf8_decode_error" for f in report.findings)


def test_receipt_id_includes_context_source_and_purpose(tmp_path: Path) -> None:
    ctx_a = TrustedExecutionContext.from_environment("public_demo", source="cli", purpose="trust_gate")
    ctx_b = TrustedExecutionContext.from_environment("public_demo", source="host", purpose="verified_intent_export")
    r_a = evaluate_trust_gate(load_draft(SAFE), ctx_a).as_dict()["receipt"]
    r_b = evaluate_trust_gate(load_draft(SAFE), ctx_b).as_dict()["receipt"]
    assert r_a["receipt_id"] != r_b["receipt_id"]
    assert r_a["trusted_context"]["source"] != r_b["trusted_context"]["source"]


def test_production_context_is_refused_for_public_demo() -> None:
    ctx = TrustedExecutionContext.from_environment("production", source="cli", purpose="trust_gate")
    decision = evaluate_trust_gate(load_draft(SAFE), ctx).as_dict()
    assert decision["status"] == "refused"
    assert decision["handoff_allowed"] is False
    assert decision["lowering_allowed"] is False
    assert any(f["rule"] == "T010.production_context_not_supported" for f in decision["findings"])
