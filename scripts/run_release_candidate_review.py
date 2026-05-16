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


def _run(name: str, cmd: list[str], out_dir: Path, expect_success: bool = True) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    proc = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, timeout=180)
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:80]
    (log_dir / f"{safe}.stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (log_dir / f"{safe}.stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    ok = proc.returncode == 0 if expect_success else proc.returncode != 0
    return {
        "name": name,
        "command": cmd,
        "expected": "success" if expect_success else "failure",
        "exit_code": proc.returncode,
        "status": "passed" if ok else "failed",
        "stdout_tail": (proc.stdout or "").strip()[-700:],
        "stderr_tail": (proc.stderr or "").strip()[-700:],
    }


def _boundary_check() -> dict:
    forbidden_suffixes = {".zip", ".pyc"}
    forbidden_dirs = {"__pycache__", ".pytest_cache", "demo_results", "prelaunch_results", "review_results", "negative_conformance_results", "golden_trace_results", "out"}
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        parts = set(rel.parts)
        # Generated/cache directories are ignored during review so the check is
        # idempotent after running demos/tests locally. Release packaging still
        # removes these paths before ZIP creation.
        if parts & forbidden_dirs:
            continue
        if path.is_file() and path.suffix in forbidden_suffixes:
            findings.append(f"forbidden_file_suffix:{rel}")
        if path.is_file() and path.name.lower().endswith("all_in_one.zip"):
            findings.append(f"private_archive_like_file:{rel}")
    required = [
        "README.md",
        "START_HERE.md",
        "docs/pre_v1_status.md",
        "docs/public_private_boundary.md",
        "docs/private_archive_boundary.md",
        "docs/github_launch_checklist.md",
        "docs/phase13_release_candidate_reassessment.md",
        "review/external_style_review_request.md",
    ]
    for item in required:
        if not (ROOT / item).exists():
            findings.append(f"missing_required_public_file:{item}")
    return {"name": "public_private_boundary", "status": "passed" if not findings else "failed", "findings": findings}


def _terminology_check() -> dict:
    # Public-facing artifacts should use conformance-oriented terminology. Historical private docs are not in this repo.
    discouraged_terms = [
        "ex" + "ploit",
        "attack" + "_payload",
        "malicious" + "_draft",
        "by" + "pass_case",
        "red" + "team_corpus",
        "red" + "team-eval",
    ]
    findings: list[str] = []
    allowed_paths = {"docs/phase13_release_candidate_reassessment.md", "scripts/run_release_candidate_review.py"}
    scan_roots = ["README.md", "START_HERE.md", "docs", "src", "tests", "scripts", "registries", "review"]
    for root_name in scan_roots:
        root = ROOT / root_name
        if not root.exists():
            continue
        paths = [root] if root.is_file() else list(root.rglob("*"))
        for path in paths:
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".py", ".yaml", ".yml", ".txt"} and path.name not in {"README.md", "START_HERE.md"}:
                continue
            rel = str(path.relative_to(ROOT))
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for term in discouraged_terms:
                if term in text and rel not in allowed_paths:
                    findings.append(f"{rel}: contains discouraged public term '{term}'")
    return {"name": "terminology_conformance", "status": "passed" if not findings else "failed", "findings": findings[:30]}





def _run_phase20_receipt_conformance_direct(out_dir: Path) -> dict:
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




def _run_phase22_verified_intent_direct(out_dir: Path) -> dict:
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


def _run_phase23_verified_intent_hardening_direct(out_dir: Path) -> dict:
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



def _run_phase24_verified_intent_semantic_direct(out_dir: Path) -> dict:
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



def _run_phase25_verified_intent_contract_direct(out_dir: Path) -> dict:
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

def _run_phase21_launch_readiness_direct(out_dir: Path) -> dict:
    from ainir.phase21_release_readiness_eval import run_phase21_launch_readiness_eval
    summary = run_phase21_launch_readiness_eval(out_dir / "phase21_launch_readiness")
    ok = summary.get("overall_status") == "passed"
    return {
        "name": "phase21_launch_readiness_eval",
        "command": ["internal", "run_phase21_launch_readiness_eval"],
        "expected": "success",
        "exit_code": 0 if ok else 2,
        "status": "passed" if ok else "failed",
        "stdout_tail": f"decision={summary.get('decision')} steps={summary.get('steps_passed')}/{summary.get('steps_total')}",
        "stderr_tail": "",
    }

def _run_trust_receipt_direct(out_dir: Path) -> dict:
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

def _run_negative_direct(out_dir: Path) -> dict:
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


def _run_golden_direct(out_dir: Path) -> dict:
    from ainir.golden_trace_harness import run_golden_traces
    summary = run_golden_traces("golden_traces.yaml", out_dir / "golden_traces", "public_demo")
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

def _status_claim_check() -> dict:
    findings: list[str] = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "pre-v1" not in readme:
        findings.append("README does not state pre-v1 status")
    required_negations = ["not a v1.0 final", "not a production runtime"]
    lower = readme.lower()
    for phrase in required_negations:
        if phrase not in lower:
            findings.append(f"README missing status boundary phrase: {phrase}")
    return {"name": "status_claim_scope", "status": "passed" if not findings else "failed", "findings": findings}


def _default_out_dir() -> str:
    return str(Path(os.environ.get("AINIR_TEMP_ROOT") or tempfile.gettempdir()) / "ainir_review_results")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run AiNIR pre-v1 public launch candidate review check.")
    parser.add_argument("--out-dir", default=_default_out_dir())
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = Path(tempfile.gettempdir()) / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    py = sys.executable
    all_steps = []
    for name, fn in [
        ("public_private_boundary", _boundary_check),
        ("terminology_conformance", _terminology_check),
        ("status_claim_scope", _status_claim_check),
    ]:
        print(f"[review] starting {name}", flush=True)
        all_steps.append(fn())

    command_plan = [
        ("public_prelaunch_check", lambda: _run("public_prelaunch_check", [py, "scripts/run_prelaunch_check.py", "--out-dir", str(out_dir / "prelaunch")], out_dir)),
        ("negative_conformance_eval", lambda: _run_negative_direct(out_dir)),
        ("golden_trace_eval", lambda: _run_golden_direct(out_dir)),
        ("trust_receipt_replay_eval", lambda: _run_trust_receipt_direct(out_dir)),
        ("phase20_receipt_conformance_eval", lambda: _run_phase20_receipt_conformance_direct(out_dir)),
        ("phase22_verified_intent_export_eval", lambda: _run_phase22_verified_intent_direct(out_dir)),
        ("phase23_verified_intent_export_hardening_eval", lambda: _run_phase23_verified_intent_hardening_direct(out_dir)),
        ("phase24_verified_intent_semantic_eval", lambda: _run_phase24_verified_intent_semantic_direct(out_dir)),
        ("phase25_verified_intent_contract_eval", lambda: _run_phase25_verified_intent_contract_direct(out_dir)),
        ("phase21_launch_readiness_eval", lambda: _run_phase21_launch_readiness_direct(out_dir)),
    ]
    for name, fn in command_plan:
        print(f"[review] starting {name}", flush=True)
        all_steps.append(fn())
    overall = "passed" if all(s["status"] == "passed" for s in all_steps) else "failed"
    report = {
        "report": "ainir.pre_v1.phase13.public_launch_candidate_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "steps_total": len(all_steps),
        "steps_passed": sum(1 for s in all_steps if s["status"] == "passed"),
        "steps_failed": sum(1 for s in all_steps if s["status"] != "passed"),
        "human_external_evaluator_status": "pending",
        "production_runtime_ready": False,
        "v1_final_ready": False,
        "steps": all_steps,
    }
    (out_dir / "release_candidate_review_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# AiNIR Pre-v1 Public Launch Candidate Review",
        "",
        f"overall_status: {overall}",
        f"steps: {report['steps_passed']}/{report['steps_total']} passed",
        "human_external_evaluator_status: pending",
        "production_runtime_ready: false",
        "v1_final_ready: false",
        "",
        "| Step | Status |",
        "|---|---|",
    ]
    for step in all_steps:
        lines.append(f"| {step['name']} | {step['status']} |")
    lines.append("")
    lines.append("This is a pre-v1 public review package, not a final release proof.")
    (out_dir / "release_candidate_review_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"AiNIR pre-v1 public launch candidate review: {overall}")
    print(f"report: {out_dir / 'release_candidate_review_report.json'}")
    print(f"summary: {out_dir / 'release_candidate_review_summary.md'}")
    return 0 if overall == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
