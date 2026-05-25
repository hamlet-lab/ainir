from __future__ import annotations

import json
from pathlib import Path
import shutil

from .execution_context import TrustedExecutionContext
from .trust_receipt_store import issue_trust_receipt, replay_trust_receipt


def run_phase19_trust_receipt_eval(out_dir: str | Path = "phase19_trust_receipt_results") -> dict:
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    context = TrustedExecutionContext.public_demo()
    safe_draft = Path("examples/create_user_outbox_safe/draft.yaml")
    blocked_draft = Path("examples/order_payment_real_payment_blocked/draft.yaml")
    cases = []

    # 1. A safe receipt can be issued and replayed.
    issued_safe = issue_trust_receipt(safe_draft, out / "safe_receipts", context)
    replay_safe = replay_trust_receipt(issued_safe.receipt_path, safe_draft, context)
    cases.append({
        "case_id": "safe_receipt_replays",
        "expected": "passed",
        "actual": replay_safe.overall_status,
        "passed": replay_safe.overall_status == "passed",
    })

    # 2. A refused receipt can also be replayed as the same refused decision.
    issued_blocked = issue_trust_receipt(blocked_draft, out / "blocked_receipts", context)
    replay_blocked = replay_trust_receipt(issued_blocked.receipt_path, blocked_draft, context)
    cases.append({
        "case_id": "refused_receipt_replays_as_refused",
        "expected": "passed",
        "actual": replay_blocked.overall_status,
        "passed": replay_blocked.overall_status == "passed",
    })

    # 3. Tampering with the receipt status fails replay.
    tampered_receipt = out / "tampered_status.receipt.json"
    receipt_obj = dict(issued_safe.receipt)
    receipt_obj["status"] = "refused"
    tampered_receipt.write_text(json.dumps(receipt_obj, indent=2, ensure_ascii=False), encoding="utf-8")
    replay_tampered = replay_trust_receipt(tampered_receipt, safe_draft, context)
    cases.append({
        "case_id": "tampered_receipt_status_fails",
        "expected": "failed",
        "actual": replay_tampered.overall_status,
        "passed": replay_tampered.overall_status == "failed",
    })

    # 4. Replaying a safe receipt against a modified draft fails hash checks.
    modified_dir = out / "modified_draft"
    modified_dir.mkdir(parents=True, exist_ok=True)
    modified_draft = modified_dir / "draft.yaml"
    text = safe_draft.read_text(encoding="utf-8")
    text = text.replace("demo.create_user_outbox_safe", "demo.create_user_outbox_modified")
    modified_draft.write_text(text, encoding="utf-8")
    replay_modified = replay_trust_receipt(issued_safe.receipt_path, modified_draft, context)
    cases.append({
        "case_id": "receipt_bound_to_original_draft_hash",
        "expected": "failed",
        "actual": replay_modified.overall_status,
        "passed": replay_modified.overall_status == "failed",
    })

    # 5. Replaying under a different trusted environment fails context binding.
    test_context = TrustedExecutionContext.from_environment("test", source="phase19_eval", purpose="receipt_replay_wrong_context")
    replay_wrong_context = replay_trust_receipt(issued_safe.receipt_path, safe_draft, test_context)
    cases.append({
        "case_id": "receipt_bound_to_trusted_context",
        "expected": "failed",
        "actual": replay_wrong_context.overall_status,
        "passed": replay_wrong_context.overall_status == "failed",
    })

    # 6. Tampering with stable explanatory fields fails replay.
    tampered_gates = out / "tampered_failed_gates.receipt.json"
    receipt_obj = dict(issued_safe.receipt)
    receipt_obj["failed_gates"] = ["fake_gate"]
    tampered_gates.write_text(json.dumps(receipt_obj, indent=2, ensure_ascii=False), encoding="utf-8")
    replay_tampered_gates = replay_trust_receipt(tampered_gates, safe_draft, context)
    cases.append({
        "case_id": "tampered_failed_gates_fails",
        "expected": "failed",
        "actual": replay_tampered_gates.overall_status,
        "passed": replay_tampered_gates.overall_status == "failed",
    })

    # 7. Tampering with trusted context source/purpose fails when replayed against
    # the original trusted context.
    tampered_context = out / "tampered_context.receipt.json"
    receipt_obj = dict(issued_safe.receipt)
    receipt_obj["trusted_context"] = dict(receipt_obj.get("trusted_context") or {})
    receipt_obj["trusted_context"]["source"] = "tampered_source"
    tampered_context.write_text(json.dumps(receipt_obj, indent=2, ensure_ascii=False), encoding="utf-8")
    replay_tampered_context = replay_trust_receipt(tampered_context, safe_draft, context)
    cases.append({
        "case_id": "tampered_trusted_context_source_fails",
        "expected": "failed",
        "actual": replay_tampered_context.overall_status,
        "passed": replay_tampered_context.overall_status == "failed",
    })

    summary = {
        "phase": "pre_v1_phase19_trust_receipt_persistence_and_replay",
        "overall_status": "passed" if all(c["passed"] for c in cases) else "failed",
        "case_count": len(cases),
        "passed": sum(1 for c in cases if c["passed"]),
        "failed": sum(1 for c in cases if not c["passed"]),
        "cases": cases,
    }
    (out / "phase19_trust_receipt_eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
