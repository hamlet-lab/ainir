from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def run_cmd(name: str, cmd: list[str], out_dir: Path, expect_success: bool = True, env_extra: dict[str, str] | None = None) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, timeout=90)
    step_dir = out_dir / "logs"
    step_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:80]
    (step_dir / f"{safe}.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (step_dir / f"{safe}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    passed = (proc.returncode == 0) if expect_success else (proc.returncode != 0)
    return {
        "name": name,
        "command": cmd,
        "expected": "success" if expect_success else "failure",
        "exit_code": proc.returncode,
        "status": "passed" if passed else "failed",
        "stdout_tail": (proc.stdout or "").strip()[-800:],
        "stderr_tail": (proc.stderr or "").strip()[-800:],
    }




def run_cli_direct(name: str, argv: list[str], out_dir: Path, expect_success: bool = True) -> dict:
    from contextlib import redirect_stdout, redirect_stderr
    from io import StringIO
    from ainir.cli import main as ainir_main

    stdout = StringIO()
    stderr = StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = ainir_main(argv)
    except Exception as exc:
        code = 99
        stderr.write(repr(exc))
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:80]
    (log_dir / f"{safe}.stdout.txt").write_text(stdout.getvalue(), encoding="utf-8")
    (log_dir / f"{safe}.stderr.txt").write_text(stderr.getvalue(), encoding="utf-8")
    passed = (code == 0) if expect_success else (code != 0)
    return {
        "name": name,
        "command": ["internal", "ainir"] + argv,
        "expected": "success" if expect_success else "failure",
        "exit_code": code,
        "status": "passed" if passed else "failed",
        "stdout_tail": stdout.getvalue().strip()[-800:],
        "stderr_tail": stderr.getvalue().strip()[-800:],
    }

def run_negative_conformance_direct(out_dir: Path) -> dict:
    from ainir.negative_conformance_harness import run_negative_conformance_corpus
    summary = run_negative_conformance_corpus("negative_conformance_corpus.yaml", out_dir / "negative_conformance", "public_demo")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "negative_conformance_eval",
        "command": ["internal", "run_negative_conformance_corpus"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"cases={summary.get('case_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }


def run_golden_trace_direct(out_dir: Path) -> dict:
    from ainir.golden_trace_harness import run_golden_traces
    summary = run_golden_traces("golden_traces.yaml", out_dir / "golden", "public_demo")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "golden_trace_eval",
        "command": ["internal", "run_golden_traces"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"traces={summary.get('trace_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }




def run_trust_receipt_direct(out_dir: Path) -> dict:
    from ainir.phase19_trust_receipt_eval import run_phase19_trust_receipt_eval
    summary = run_phase19_trust_receipt_eval(out_dir / "trust_receipts")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "trust_receipt_replay_eval",
        "command": ["internal", "run_phase19_trust_receipt_eval"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"cases={summary.get('case_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }


def run_phase20_receipt_conformance_direct(out_dir: Path) -> dict:
    from ainir.phase20_receipt_conformance_eval import run_phase20_receipt_conformance_eval
    summary = run_phase20_receipt_conformance_eval(out_dir / "phase20_receipt_conformance")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "phase20_receipt_conformance_eval",
        "command": ["internal", "run_phase20_receipt_conformance_eval"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"cases={summary.get('case_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }



def run_phase22_verified_intent_direct(out_dir: Path) -> dict:
    from ainir.phase22_verified_intent_eval import run_phase22_verified_intent_eval
    summary = run_phase22_verified_intent_eval(out_dir / "phase22_verified_intent")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "phase22_verified_intent_export_eval",
        "command": ["internal", "run_phase22_verified_intent_eval"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"cases={summary.get('case_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }


def run_phase23_verified_intent_hardening_direct(out_dir: Path) -> dict:
    from ainir.phase23_verified_intent_hardening_eval import run_phase23_verified_intent_hardening_eval
    summary = run_phase23_verified_intent_hardening_eval(out_dir / "phase23_verified_intent_hardening")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "phase23_verified_intent_export_hardening_eval",
        "command": ["internal", "run_phase23_verified_intent_hardening_eval"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"cases={summary.get('case_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }



def run_phase24_verified_intent_semantic_direct(out_dir: Path) -> dict:
    from ainir.phase24_verified_intent_semantic_eval import run_phase24_verified_intent_semantic_eval
    summary = run_phase24_verified_intent_semantic_eval(out_dir / "phase24_verified_intent_semantic")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "phase24_verified_intent_semantic_eval",
        "command": ["internal", "run_phase24_verified_intent_semantic_eval"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"cases={summary.get('case_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }



def run_phase25_verified_intent_contract_direct(out_dir: Path) -> dict:
    from ainir.phase25_verified_intent_contract_eval import run_phase25_verified_intent_contract_eval
    summary = run_phase25_verified_intent_contract_eval(out_dir / "phase25_verified_intent_contract")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "phase25_verified_intent_contract_eval",
        "command": ["internal", "run_phase25_verified_intent_contract_eval"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"cases={summary.get('case_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }

def run_trust_gate_direct(out_dir: Path) -> dict:
    from ainir.phase18_trust_gate_eval import run_phase18_trust_gate_eval
    summary = run_phase18_trust_gate_eval(out_dir / "trust_gate")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "trust_gate_eval",
        "command": ["internal", "run_phase18_trust_gate_eval"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"cases={summary.get('case_count')} passed={summary.get('passed')} failed={summary.get('failed')}",
        "stderr_tail": "",
    }

def _default_out_dir() -> str:
    return str(Path(os.environ.get("AINIR_TEMP_ROOT") or tempfile.gettempdir()) / "ainir_prelaunch_results")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run AiNIR public pre-launch checks.")
    parser.add_argument("--out-dir", default=_default_out_dir())
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = Path(tempfile.gettempdir()) / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    steps: list[dict] = []
    py = sys.executable

    # Keep failure-mode checks before heavier corpus runners. Some environments
    # keep subprocess pipes open after corpus runs; this order makes the launch
    # check deterministic and easier to diagnose.
    empty = out_dir / "empty.yaml"
    empty.write_text("{}\n", encoding="utf-8")
    steps.append(run_cli_direct("empty_draft_must_fail", ["verify", str(empty), "--json"], out_dir, expect_success=False))

    missing = out_dir / "missing_examples"
    missing.mkdir(exist_ok=True)
    steps.append(run_cli_direct("missing_examples_must_fail", ["demo", "--examples-dir", str(missing), "--out-dir", str(out_dir / "missing_examples_report")], out_dir, expect_success=False))

    steps.append(run_cmd("pytest", [py, "-m", "pytest", "-q"], out_dir))
    steps.append(run_cli_direct("public_demo", ["demo", "--out-dir", str(out_dir / "demo")], out_dir))
    steps.append(run_cli_direct("safe_lowering", ["lower", "examples/create_user_outbox_safe/draft.yaml", "--out-dir", str(out_dir / "lowered")], out_dir))
    steps.append(run_cli_direct("trust_gate_safe_create_user", ["trust-gate", "examples/create_user_outbox_safe/draft.yaml", "--json", "--out-dir", str(out_dir / "trust_gate_safe")], out_dir))
    steps.append(run_trust_gate_direct(out_dir))
    steps.append(run_trust_receipt_direct(out_dir))
    steps.append(run_phase20_receipt_conformance_direct(out_dir))
    steps.append(run_phase22_verified_intent_direct(out_dir))
    steps.append(run_phase23_verified_intent_hardening_direct(out_dir))
    steps.append(run_phase24_verified_intent_semantic_direct(out_dir))
    steps.append(run_phase25_verified_intent_contract_direct(out_dir))
    steps.append(run_negative_conformance_direct(out_dir))
    steps.append(run_golden_trace_direct(out_dir))

    overall = "passed" if all(s["status"] == "passed" for s in steps) else "failed"
    report = {
        "report": "ainir.public.prelaunch_check",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "repo_root": str(ROOT),
        "steps_total": len(steps),
        "steps_passed": sum(1 for s in steps if s["status"] == "passed"),
        "steps_failed": sum(1 for s in steps if s["status"] != "passed"),
        "steps": steps,
    }
    (out_dir / "prelaunch_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_lines = [
        "# AiNIR Public Pre-launch Check",
        "",
        f"overall_status: {overall}",
        f"steps: {report['steps_passed']}/{report['steps_total']} passed",
        "",
        "| Step | Expected | Exit | Status |",
        "|---|---:|---:|---|",
    ]
    for s in steps:
        summary_lines.append(f"| {s['name']} | {s['expected']} | {s['exit_code']} | {s['status']} |")
    summary_lines.append("")
    summary_lines.append("This check is a launch sanity gate, not a production security proof.")
    (out_dir / "prelaunch_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    print(f"AiNIR prelaunch check: {overall}")
    print(f"report: {out_dir / 'prelaunch_report.json'}")
    print(f"summary: {out_dir / 'prelaunch_summary.md'}")
    return 0 if overall == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
