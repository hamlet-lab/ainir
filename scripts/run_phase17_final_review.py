from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    return env


def _run(name: str, cmd: list[str], out_dir: Path, expect_success: bool = True, timeout: int = 120) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, env=_env(), text=True, capture_output=True, timeout=timeout)
    logs = out_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:100]
    (logs / f"{safe}.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (logs / f"{safe}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    ok = proc.returncode == 0 if expect_success else proc.returncode != 0
    return {
        "name": name,
        "command": cmd,
        "expected": "success" if expect_success else "failure",
        "exit_code": proc.returncode,
        "status": "passed" if ok else "failed",
        "stdout_tail": (proc.stdout or "").strip()[-900:],
        "stderr_tail": (proc.stderr or "").strip()[-900:],
    }


def _write_case(out_dir: Path, name: str, data: dict) -> Path:
    case_dir = out_dir / "synthetic_cases"
    case_dir.mkdir(parents=True, exist_ok=True)
    path = case_dir / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _verify_case(out_dir: Path, name: str, data: dict, expected_status: str | set[str], expect_lower: str | None = None) -> dict:
    path = _write_case(out_dir, name, data)
    proc = subprocess.run([sys.executable, "-m", "ainir", "verify", str(path), "--json"], cwd=ROOT, env=_env(), text=True, capture_output=True, timeout=60)
    try:
        report = json.loads(proc.stdout)
    except Exception:
        report = {"status": "parse_error", "stdout": proc.stdout, "stderr": proc.stderr}
    expected = {expected_status} if isinstance(expected_status, str) else set(expected_status)
    ok = report.get("status") in expected
    lower_result = None
    if expect_lower is not None:
        lproc = subprocess.run([sys.executable, "-m", "ainir", "lower", str(path), "--out-dir", str(out_dir / "lowered" / name)], cwd=ROOT, env=_env(), text=True, capture_output=True, timeout=60)
        lower_result = "emitted" if lproc.returncode == 0 else "refused"
        ok = ok and lower_result == expect_lower
    return {
        "name": name,
        "expected_status": sorted(expected),
        "observed_status": report.get("status"),
        "critical_count": report.get("critical_count"),
        "observed_rules": [f.get("rule") for f in report.get("findings", [])[:16]],
        "lower_expected": expect_lower,
        "lower_observed": lower_result,
        "status": "passed" if ok else "failed",
    }


def _base(workflow: str) -> dict:
    type_map = {
        "CreateUser": ("CreateUserInput", "CreateUserResult"),
        "PasswordReset": ("PasswordResetInput", "AcceptedResponse"),
        "OrderPayment": ("PaymentIntentInput", "PaymentResult"),
        "PIIExportRequest": ("PIIExportJob", "ExportPackageRef"),
        "AccountDeletion": ("AccountDeletionJob", "DeletionResult"),
        "NewsletterSignup": ("CreateUserInput", "CreateUserResult"),
    }
    inp, out = type_map.get(workflow, ("unknown", "unknown"))
    return {"module": f"demo.phase17.{workflow.lower()}", "workflow": workflow, "task": f"{workflow}Task", "input_type": inp, "output_type": out, "return": "state", "operations": []}


def _synthetic_review(out_dir: Path) -> dict:
    cases: list[dict] = []

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
    cases.append(_verify_case(out_dir, "extra_capability_on_pure_operation_refused", d, {"blocked", "invalid"}, "refused"))

    d = _base("OrderPayment")
    d.update({
        "policies": [{"id": "policy.no_real_payment_in_beta"}, {"id": "policy.payment_idempotency_required"}],
        "operations": [
            {"id": "op.auth", "op": "auth.check_order_payment", "effects": ["effect.auth.authorization.check"], "capabilities": ["cap.auth.check"]},
            {"id": "op.amount", "op": "payment.validate_amount", "effects": ["effect.payment.validate.Amount"], "capabilities": ["cap.payment.validate"]},
            {"id": "op.intent", "op": "db.insert_payment_intent", "effects": ["effect.storage.payment_intent.write"], "capabilities": ["cap.db.write"]},
            {"id": "op.pay", "op": "payment.finalize.production", "effects": ["effect.external.payment.charge.sandbox"], "capabilities": ["cap.payment.charge.sandbox"], "policies": ["policy.payment_idempotency_required"]},
        ],
    })
    cases.append(_verify_case(out_dir, "production_financial_operation_disguised_as_sandbox_refused", d, {"blocked", "invalid"}, "refused"))

    d = _base("PasswordReset")
    d.update({
        "policies": [{"id": "policy.no_user_enumeration"}],
        "operations": [
            {"id": "op.norm", "op": "data.normalize_email", "effects": [], "capabilities": []},
            {"id": "op.lookup", "op": "db.find_user_for_password_reset", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.read"]},
            {"id": "op.enum", "op": "policy.enforce_no_user_enumeration", "effects": [], "capabilities": []},
            {"id": "op.hash", "op": "secret.hash_password_reset_token", "effects": [], "capabilities": ["cap.secret.hash"]},
            {"id": "op.raw", "op": "db.store_raw_reset_token", "effects": ["effect.secret.token.hash"], "capabilities": ["cap.secret.hash"]},
            {"id": "op.outbox", "op": "outbox.insert_password_reset_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
    })
    cases.append(_verify_case(out_dir, "forbidden_secret_persistence_role_refused_even_with_safe_effect", d, {"blocked", "invalid"}, "refused"))

    d = _base("PIIExportRequest")
    d.update({
        "policies": [{"id": "policy.pii_export_authorization_required"}, {"id": "policy.export_package_must_be_encrypted"}, {"id": "policy.export_fields_allowlist_required"}],
        "operations": [
            {"id": "op.auth", "op": "auth.check_pii_export_authorization", "effects": ["effect.auth.authorization.check"], "capabilities": ["cap.auth.check"]},
            {"id": "op.allow", "op": "policy.enforce_export_field_allowlist", "effects": [], "capabilities": []},
            {"id": "op.read", "op": "db.read_user_pii_bundle", "effects": ["effect.privacy.pii.read"], "capabilities": ["cap.pii.read"]},
            {"id": "op.encrypt", "op": "export.encrypt_pii_export_package", "effects": ["effect.crypto.encrypt"], "capabilities": ["cap.crypto.encrypt"]},
            {"id": "op.store", "op": "storage.write_encrypted_pii_export_package", "effects": ["effect.storage.export_package.write"], "capabilities": ["cap.export.storage.write"]},
        ],
    })
    cases.append(_verify_case(out_dir, "registered_pii_export_safe_flow_passes", d, "passed", None))

    d = _base("CreateUser")
    d.update({
        "policies": [{"id": "policy.no_direct_email_in_create_user"}, {"id": "policy.transactional_outbox_required"}, {"id": "policy.user_email_unique"}],
        "operations": [
            {"id": "op.norm", "op": "data.normalize_email", "effects": [], "capabilities": []},
            {"id": "op.check", "op": "db.exists_user_by_email", "effects": ["effect.storage.db.read"], "capabilities": ["cap.db.read"]},
            {"id": "op.insert", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"], "policies": ["policy.user_email_unique"]},
            {"id": "op.outbox", "op": "outbox.insert_welcome_email_requested", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"], "policies": ["policy.transactional_outbox_required"]},
        ],
    })
    cases.append(_verify_case(out_dir, "create_user_without_transaction_refused", d, {"blocked", "invalid"}, "refused"))

    passed = sum(1 for c in cases if c["status"] == "passed")
    return {"name": "phase17_synthetic_conformance_cases", "status": "passed" if passed == len(cases) else "failed", "case_count": len(cases), "passed": passed, "failed": len(cases) - passed, "cases": cases}


def _typescript_compile_check(out_dir: Path) -> dict:
    lower_dir = out_dir / "typescript_compile"
    lower_dir.mkdir(parents=True, exist_ok=True)
    lower_step = _run("lower_safe_create_user", [sys.executable, "-m", "ainir", "lower", "examples/create_user_outbox_safe/draft.yaml", "--out-dir", str(lower_dir)], out_dir)
    if lower_step["status"] != "passed":
        return {"name": "typescript_compile", "status": "failed", "reason": "lowering failed", "lower_step": lower_step}
    tsc = subprocess.run(["bash", "-lc", "command -v tsc"], text=True, capture_output=True, timeout=10)
    if tsc.returncode != 0:
        return {"name": "typescript_compile", "status": "warning", "reason": "tsc unavailable in PATH"}
    (lower_dir / "tsconfig.json").write_text(json.dumps({"compilerOptions": {"strict": True, "target": "ES2020", "module": "CommonJS", "noEmit": True}, "include": ["*.ts"]}, indent=2), encoding="utf-8")
    compile_step = _run("tsc_generated_skeleton", ["tsc", "-p", str(lower_dir / "tsconfig.json")], out_dir)
    return {"name": "typescript_compile", "status": compile_step["status"], "lower_step": lower_step, "compile_step": compile_step}


def _doc_scope_check() -> dict:
    findings: list[str] = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore")
    status = (ROOT / "docs" / "pre_v1_status.md").read_text(encoding="utf-8", errors="ignore") if (ROOT / "docs" / "pre_v1_status.md").exists() else ""
    required_phrases = ["pre-v1", "not a v1.0 final", "not a production runtime"]
    for phrase in required_phrases:
        if phrase.lower() not in readme.lower():
            findings.append(f"README missing phrase: {phrase}")
    if "Phase 16" not in readme and "Exact capability" not in readme:
        findings.append("README does not mention Phase 16 exact capability contracts")
    if "Phase 16" not in status and "Exact capability" not in status:
        findings.append("docs/pre_v1_status.md appears stale: Phase 16 not mentioned")
    return {"name": "documentation_scope", "status": "passed" if not findings else "warning", "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 17 final defensive conformance review for the public demo.")
    parser.add_argument("--out-dir", default="phase17_review_results")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = Path(tempfile.gettempdir()) / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    command_steps = [
        _run("release_candidate_review", [sys.executable, "scripts/run_release_candidate_review.py", "--out-dir", str(out_dir / "release_review")], out_dir, timeout=240),
        _run("prelaunch_check", [sys.executable, "scripts/run_prelaunch_check.py", "--out-dir", str(out_dir / "prelaunch")], out_dir, timeout=240),
    ]
    synthetic = _synthetic_review(out_dir)
    ts = _typescript_compile_check(out_dir)
    docs = _doc_scope_check()
    steps = command_steps + [synthetic, ts, docs]

    blocking_failures = [s for s in steps if s.get("status") == "failed"]
    warnings = [s for s in steps if s.get("status") == "warning"]
    overall = "passed" if not blocking_failures else "failed"
    decision = "public_launch_candidate_ready_for_private_github_trial" if overall == "passed" else "hold_public_launch"
    report = {
        "report": "ainir.pre_v1.phase17.final_defensive_conformance_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "decision": decision,
        "human_external_evaluator_status": "pending",
        "production_runtime_ready": False,
        "v1_final_ready": False,
        "steps_total": len(steps),
        "steps_passed": sum(1 for s in steps if s.get("status") == "passed"),
        "steps_warning": len(warnings),
        "steps_failed": len(blocking_failures),
        "steps": steps,
    }
    (out_dir / "phase17_final_review_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# AiNIR Pre-v1 Phase 17 Final Defensive Conformance Review",
        "",
        f"overall_status: {overall}",
        f"decision: {decision}",
        "human_external_evaluator_status: pending",
        "production_runtime_ready: false",
        "v1_final_ready: false",
        "",
        "| Step | Status |",
        "|---|---|",
    ]
    for s in steps:
        lines.append(f"| {s['name']} | {s['status']} |")
    lines.append("")
    if warnings:
        lines.append("## Warnings")
        for w in warnings:
            lines.append(f"- {w['name']}: {w.get('findings') or w.get('reason')}")
        lines.append("")
    lines.append("This review makes the public demo a candidate for a private GitHub trial first, not an immediate public release and not a v1.0 final release.")
    (out_dir / "phase17_final_review_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"AiNIR phase17 final conformance review: {overall}")
    print(f"decision: {decision}")
    print(f"report: {out_dir / 'phase17_final_review_report.json'}")
    print(f"summary: {out_dir / 'phase17_final_review_summary.md'}")
    return 0 if overall == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
