from __future__ import annotations

import json
from pathlib import Path

import pytest

from ainir.execution_context import TrustedExecutionContext
from ainir.phase19_trust_receipt_eval import run_phase19_trust_receipt_eval
from ainir.trust_receipt_store import issue_trust_receipt, replay_trust_receipt


def test_safe_receipt_issue_and_replay(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)
    assert replay.overall_status == "passed"
    assert issued.receipt["status"] == "passed"


def test_tampered_receipt_fails_replay(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    receipt = dict(issued.receipt)
    receipt["safety_registry_hash"] = "sha256:tampered"
    tampered = tmp_path / "tampered.receipt.json"
    tampered.write_text(json.dumps(receipt), encoding="utf-8")
    replay = replay_trust_receipt(tampered, "examples/create_user_outbox_safe/draft.yaml", ctx)
    assert replay.overall_status == "failed"
    assert any(c["check"] == "safety_registry_hash" and c["status"] == "failed" for c in replay.checks)


def test_receipt_replay_fails_with_wrong_context(tmp_path: Path) -> None:
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, TrustedExecutionContext.public_demo())
    wrong = TrustedExecutionContext.from_environment("test", source="test", purpose="wrong_context")
    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", wrong)
    assert replay.overall_status == "failed"
    assert any(c["check"] == "trusted_environment" for c in replay.checks)


def test_phase19_eval_passes(tmp_path: Path) -> None:
    summary = run_phase19_trust_receipt_eval(tmp_path / "eval")
    assert summary["overall_status"] == "passed"
    assert summary["passed"] == summary["case_count"]


def test_phase19_eval_refuses_repository_root_output() -> None:
    root = Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError, match="protected output directory"):
        run_phase19_trust_receipt_eval(root)
