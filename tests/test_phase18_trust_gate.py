from pathlib import Path

from ainir.core import load_draft
from ainir.execution_context import TrustedExecutionContext
from ainir.phase18_trust_gate_eval import run_phase18_trust_gate_eval
from ainir.trust_gate import evaluate_trust_gate

ROOT = Path(__file__).resolve().parents[1]


def test_trust_gate_safe_create_user_passes():
    decision = evaluate_trust_gate(load_draft(ROOT / "examples/create_user_outbox_safe/draft.yaml"), TrustedExecutionContext.public_demo()).as_dict()
    assert decision["kind"] == "AiNIRTrustGateDecision"
    assert decision["status"] == "passed"
    assert decision["lowering_allowed"] is True
    assert decision["executable"] is True
    assert decision["receipt"]["receipt_kind"] == "AiNIRTrustReceipt"
    assert decision["receipt"]["v1_final_ready"] is False


def test_trust_gate_blocked_draft_refuses_lowering():
    decision = evaluate_trust_gate(load_draft(ROOT / "examples/order_payment_real_payment_blocked/draft.yaml"), TrustedExecutionContext.public_demo()).as_dict()
    assert decision["status"] == "refused"
    assert decision["lowering_allowed"] is False
    assert decision["failed_gates"]


def test_trust_gate_empty_draft_invalid(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("{}\n", encoding="utf-8")
    decision = evaluate_trust_gate(load_draft(p), TrustedExecutionContext.public_demo()).as_dict()
    assert decision["status"] == "invalid"
    assert decision["lowering_allowed"] is False


def test_phase18_eval(tmp_path):
    summary = run_phase18_trust_gate_eval(tmp_path / "phase18")
    assert summary["overall_status"] == "passed"
