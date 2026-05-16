from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .core import load_draft
from .execution_context import TrustedExecutionContext
from .trust_gate import evaluate_trust_gate

ROOT = Path(__file__).resolve().parents[2]


def _write_case(out_dir: Path, name: str, data: dict[str, Any]) -> Path:
    p = out_dir / "cases" / f"{name}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def _base(workflow: str) -> dict[str, Any]:
    return {
        "module": f"demo.phase18.{workflow.lower()}",
        "workflow": workflow,
        "task": f"{workflow}Task",
        "input_type": "CreateUserInput",
        "output_type": "CreateUserResult",
        "return": "state",
        "operations": [],
    }


def run_phase18_trust_gate_eval(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    if not out.is_absolute():
        out = Path("/tmp") / out
    out.mkdir(parents=True, exist_ok=True)
    ctx = TrustedExecutionContext.public_demo()
    cases: list[dict[str, Any]] = []

    fixtures = [
        ("safe_create_user", ROOT / "examples" / "create_user_outbox_safe" / "draft.yaml", "passed", True),
        ("blocked_password_reset", ROOT / "examples" / "password_reset_raw_token_blocked" / "draft.yaml", "refused", False),
    ]
    for name, path, expected_status, expected_lowering in fixtures:
        decision = evaluate_trust_gate(load_draft(path), ctx).as_dict()
        ok = decision["status"] == expected_status and decision["lowering_allowed"] is expected_lowering
        (out / f"{name}.decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
        cases.append({"name": name, "status": "passed" if ok else "failed", "observed": {"trust_status": decision["status"], "lowering_allowed": decision["lowering_allowed"]}, "expected": {"trust_status": expected_status, "lowering_allowed": expected_lowering}})

    empty = _write_case(out, "empty", {})
    decision = evaluate_trust_gate(load_draft(empty), ctx).as_dict()
    ok = decision["status"] == "invalid" and not decision["lowering_allowed"]
    cases.append({"name": "empty_draft_invalid", "status": "passed" if ok else "failed", "observed": {"trust_status": decision["status"], "lowering_allowed": decision["lowering_allowed"]}})

    d = _base("CreateUser")
    d.update({
        "policies": [{"id": "policy.no_direct_email_in_create_user"}, {"id": "policy.transactional_outbox_required"}, {"id": "policy.user_email_unique"}],
        "operations": [
            {"id": "op.norm", "op": "data.normalize_email", "effects": [], "capabilities": ["cap.payment.charge.real"]},
            {"id": "op.check", "op": "db.exists_user_by_email", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.read"]},
            {"id": "op.insert", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"], "policies": ["policy.user_email_unique"]},
            {"id": "op.outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"], "policies": ["policy.transactional_outbox_required"]},
        ],
        "transaction": {"id": "tx.create_user", "mode": "atomic", "includes": ["op.insert", "op.outbox"]},
    })
    p = _write_case(out, "extra_capability", d)
    decision = evaluate_trust_gate(load_draft(p), ctx).as_dict()
    ok = decision["status"] == "refused" and not decision["lowering_allowed"]
    cases.append({"name": "extra_capability_refused", "status": "passed" if ok else "failed", "observed": {"trust_status": decision["status"], "failed_gates": decision["failed_gates"]}})

    passed = sum(1 for c in cases if c["status"] == "passed")
    summary = {"overall_status": "passed" if passed == len(cases) else "failed", "case_count": len(cases), "passed": passed, "failed": len(cases)-passed, "cases": cases}
    (out / "phase18_trust_gate_eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
