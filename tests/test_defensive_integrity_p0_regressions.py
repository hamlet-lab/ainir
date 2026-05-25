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
from ainir.core import VerificationReport

ROOT = Path(__file__).resolve().parents[1]
SAFE = ROOT / "examples" / "create_user_outbox_safe" / "draft.yaml"


def _safe_without_claims(tmp_path: Path) -> Path:
    data = yaml.safe_load(SAFE.read_text(encoding="utf-8"))
    data.pop("claims", None)
    path = tmp_path / "no_claims.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_no_claims_no_evidence_cannot_handoff_or_lower(tmp_path: Path) -> None:
    path = _safe_without_claims(tmp_path)
    draft = load_draft(path)

    # Shape/policy verification can pass; Trust Gate handoff/lowering must not
    # treat absent claims/evidence as a satisfied evidence gate.
    report = verify_draft(draft, TrustedExecutionContext.public_demo())
    assert report.status == "passed"

    decision = evaluate_trust_gate(draft, TrustedExecutionContext.public_demo()).as_dict()
    assert decision["status"] == "refused"
    assert decision["handoff_allowed"] is False
    assert decision["lowering_allowed"] is False
    assert "evidence_ledger_binding" in decision["failed_gates"]
    assert "evidence_ledger_binding" not in decision["satisfied_gates"]
    assert decision["gate_results"]["evidence_ledger_binding"]["status"] == "failed"
    assert any(f["rule"].startswith("TR000") for f in decision["findings"])

    forged_passed_report = VerificationReport(module_id=draft.module_id, workflow=draft.workflow, status="passed", findings=[])
    try:
        lower_to_typescript(draft, forged_passed_report, tmp_path / "lowered", TrustedExecutionContext.public_demo())
    except RuntimeError as exc:
        assert "TR000.ledger_bound_claim_required" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("lowering unexpectedly succeeded without claim/evidence warrant")


def test_duplicate_yaml_keys_are_rejected_before_semantic_verification(tmp_path: Path) -> None:
    path = tmp_path / "duplicate_workflow.yaml"
    path.write_text(
        """
module: demo.duplicate_key
workflow: AccountDeletion
workflow: CreateUser
task: CreateUserRequest
operations:
  - id: op.noop
    op: data.noop
    effects: []
""",
        encoding="utf-8",
    )
    report = verify_draft(load_draft(path), TrustedExecutionContext.public_demo())
    assert report.status == "invalid"
    assert any(f.rule == "S070.yaml_duplicate_key" for f in report.findings)


def test_receipt_records_raw_source_hash_and_replay_detects_tampering(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt(SAFE, tmp_path, ctx)
    receipt = dict(issued.receipt)
    assert receipt["canonical_draft_sha256"] == receipt["draft_hash"]
    assert isinstance(receipt["raw_source_sha256"], str)
    assert receipt["raw_source_sha256"].startswith("sha256:")

    tampered = copy.deepcopy(receipt)
    tampered["raw_source_sha256"] = "sha256:" + "0" * 64
    path = tmp_path / "tampered_raw_hash.receipt.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    replay = replay_trust_receipt(path, SAFE, ctx)
    assert replay.overall_status == "failed"
    assert any(c["check"] == "raw_source_sha256" and c["status"] == "failed" for c in replay.checks)
    assert any(c["check"] == "stable_receipt_projection_hash_self_check" and c["status"] == "failed" for c in replay.checks)


def test_raw_source_hash_distinguishes_same_canonical_yaml(tmp_path: Path) -> None:
    base = yaml.safe_load(SAFE.read_text(encoding="utf-8"))
    base.pop("claims", None)
    one = tmp_path / "one.yaml"
    two = tmp_path / "two.yaml"
    canonical_text = yaml.safe_dump(base, sort_keys=False)
    one.write_text(canonical_text, encoding="utf-8")
    two.write_text("# different raw source; same parsed draft\n" + canonical_text, encoding="utf-8")

    r1 = evaluate_trust_gate(load_draft(one), TrustedExecutionContext.public_demo()).as_dict()["receipt"]
    r2 = evaluate_trust_gate(load_draft(two), TrustedExecutionContext.public_demo()).as_dict()["receipt"]
    assert r1["canonical_draft_sha256"] == r2["canonical_draft_sha256"]
    assert r1["raw_source_sha256"] != r2["raw_source_sha256"]
    assert r1["receipt_id"] != r2["receipt_id"]


def test_hypothesized_claim_with_ledger_evidence_cannot_handoff_or_lower(tmp_path):
    from copy import deepcopy
    from ainir.core import load_draft
    from ainir.execution_context import TrustedExecutionContext
    from ainir.trust_gate import evaluate_trust_gate
    from ainir.lowering import lower_to_typescript
    from ainir.verifier import verify_draft

    root = Path(__file__).resolve().parents[1]
    original = load_draft(root / "examples" / "create_user_outbox_safe" / "draft.yaml")
    data = deepcopy(original.raw)
    for claim in data.get("claims", []):
        claim["status"] = "hypothesized"
    path = tmp_path / "hypothesized_claim.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    draft = load_draft(path)
    context = TrustedExecutionContext.public_demo()

    report = verify_draft(draft, context)
    assert report.status == "passed"

    decision = evaluate_trust_gate(draft, context).as_dict()
    assert decision["status"] == "refused"
    assert decision["handoff_allowed"] is False
    assert "evidence_ledger_binding" in decision["failed_gates"]
    assert any(f["rule"] == "TR000.verified_ledger_bound_claim_required" for f in decision["findings"])

    try:
        lower_to_typescript(draft, report, tmp_path / "lowered", context)
    except RuntimeError as exc:
        assert "TR000.verified_ledger_bound_claim_required" in str(exc)
    else:
        raise AssertionError("hypothesized claim with evidence must not lower")
