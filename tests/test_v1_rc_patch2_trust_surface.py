from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from ainir.core import load_draft
from ainir.execution_context import TrustedExecutionContext
from ainir.lowering import lower_to_typescript
from ainir.trust_gate import evaluate_trust_gate
from ainir.trust_receipt_store import issue_trust_receipt, replay_trust_receipt
from ainir.verifier import verify_draft

ROOT = Path(__file__).resolve().parents[1]
SAFE = ROOT / "examples/create_user_outbox_safe/draft.yaml"


def _safe_data() -> dict:
    data = yaml.safe_load(SAFE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _hypothesized_safe(tmp_path: Path, name: str = "draft.yaml") -> Path:
    data = _safe_data()
    for claim in data.get("claims", []):
        claim["status"] = "hypothesized"
        claim.pop("evidence", None)
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_trust_gate_lowering_surface_matches_return_allowlist(tmp_path: Path) -> None:
    path = _hypothesized_safe(tmp_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["return"] = "process.exit(1)"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    draft = load_draft(path)
    decision = evaluate_trust_gate(draft, TrustedExecutionContext.public_demo()).as_dict()
    assert decision["status"] == "refused"
    assert decision["lowering_allowed"] is False
    assert "lowering_eligibility" in decision
    rules = {f["rule"] for f in decision["lowering_eligibility"]["findings"]}
    assert "L011.lowering_forbids_unallowed_return_expr" in rules


def test_trust_gate_lowering_surface_matches_type_allowlist(tmp_path: Path) -> None:
    path = _hypothesized_safe(tmp_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["input_type"] = "EvilType"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    decision = evaluate_trust_gate(load_draft(path), TrustedExecutionContext.public_demo()).as_dict()
    assert decision["status"] == "refused"
    rules = {f["rule"] for f in decision["lowering_eligibility"]["findings"]}
    assert "L009.lowering_forbids_unallowed_input_type" in rules


def test_evidence_checked_status_is_not_public_demo_claim_status(tmp_path: Path) -> None:
    data = _safe_data()
    data["claims"][0]["status"] = "evidence_checked"
    data["claims"][0].pop("evidence", None)
    path = tmp_path / "evidence_checked.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    report = verify_draft(load_draft(path), TrustedExecutionContext.public_demo())
    assert report.status == "invalid"
    assert any(f.rule == "S040.claim_status_invalid" for f in report.findings)


def test_executable_false_draft_does_not_lower(tmp_path: Path) -> None:
    path = _hypothesized_safe(tmp_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["executable"] = False
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    draft = load_draft(path)
    report = verify_draft(draft, TrustedExecutionContext.public_demo())
    assert report.status == "passed"
    decision = evaluate_trust_gate(draft, TrustedExecutionContext.public_demo()).as_dict()
    assert decision["lowering_allowed"] is False
    assert any(f["rule"] == "L012.lowering_forbids_executable_false" for f in decision["lowering_eligibility"]["findings"])
    try:
        lower_to_typescript(draft, report, tmp_path / "lowered", TrustedExecutionContext.public_demo())
    except RuntimeError as exc:
        assert "L012.lowering_forbids_executable_false" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("lowering unexpectedly succeeded")


def test_trust_receipt_replay_detects_explanatory_field_tampering(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt(SAFE, tmp_path, ctx)
    receipt = copy.deepcopy(dict(issued.receipt))
    receipt["failed_gates"] = ["fake_gate"]
    tampered = tmp_path / "tampered_failed_gates.receipt.json"
    tampered.write_text(json.dumps(receipt), encoding="utf-8")
    replay = replay_trust_receipt(tampered, SAFE, ctx)
    assert replay.overall_status == "failed"
    assert any(c["check"] == "failed_gates" and c["status"] == "failed" for c in replay.checks)
    assert any(c["check"] == "stable_receipt_projection_hash_self_check" and c["status"] == "failed" for c in replay.checks)


def test_trust_receipt_replay_detects_trusted_context_tampering(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt(SAFE, tmp_path, ctx)
    receipt = copy.deepcopy(dict(issued.receipt))
    receipt["trusted_context"]["source"] = "evil_source"
    tampered = tmp_path / "tampered_context.receipt.json"
    tampered.write_text(json.dumps(receipt), encoding="utf-8")
    replay = replay_trust_receipt(tampered, SAFE, ctx)
    assert replay.overall_status == "failed"
    assert any(c["check"] == "trusted_context_source" and c["status"] == "failed" for c in replay.checks)
