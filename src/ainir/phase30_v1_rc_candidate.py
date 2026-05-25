from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .temp_paths import ainir_temp_str
from .phase26_private_trial import _is_local_temp_rel, _is_within, _safe_trial_temp_parent, run_phase26_private_trial
from .phase25_verified_intent_contract_eval import run_phase25_verified_intent_contract_eval

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCS = [
    "docs/v1_rc_candidate.md",
    "docs/v1_rc_scope.md",
    "docs/v1_api_surface.md",
    "docs/v1_acceptance_criteria.md",
    "docs/v1_known_limitations.md",
    "release/v1_0_rc_candidate_manifest.yaml",
]

REQUIRED_README_PHRASES = [
    "Model output is a claim, not a fact.",
    "v1.0 RC candidate",
    "not a v1.0 final",
    "not a production runtime",
]


def _step(name: str, status: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "status": status, **extra}


def _static_docs_check() -> dict[str, Any]:
    missing = [rel for rel in REQUIRED_DOCS if not (ROOT / rel).exists()]
    return _step("v1_rc_docs_present", "passed" if not missing else "failed", missing=missing)


def _status_language_check() -> dict[str, Any]:
    text = (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore")
    missing = [phrase for phrase in REQUIRED_README_PHRASES if phrase not in text]
    forbidden = []
    lower = text.lower()
    for phrase in ["production-ready", "v1.0 final release", "v1 final release"]:
        idx = lower.find(phrase)
        if idx != -1:
            context = lower[max(0, idx - 80):idx]
            if "not" not in context:
                forbidden.append(phrase)
    return _step("v1_rc_status_language", "passed" if not missing and not forbidden else "failed", missing=missing, forbidden=forbidden)


def _manifest_check() -> dict[str, Any]:
    path = ROOT / "release/v1_0_rc_candidate_manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    required = [
        "not_v1_final: true",
        "production_runtime_ready: false",
        "TrustGateDecision",
        "VerifiedIntentPacket",
        "rc_candidate_patch7",
    ]
    status_ok = "status: rc_candidate" in text or "status: rc_candidate_patch7" in text
    missing = [s for s in required if s not in text]
    if not status_ok:
        missing.append("status: rc_candidate or status: rc_candidate_patch7")
    return _step("v1_rc_manifest", "passed" if not missing else "failed", missing=missing)



def _registry_snapshot_validity_check() -> dict[str, Any]:
    from .registry_provenance import registry_snapshot, registry_snapshot_failures
    snap = registry_snapshot()
    failures = registry_snapshot_failures(snap)
    return _step(
        "registry_snapshot_valid_and_copy_consistent",
        "passed" if not failures else "failed",
        failures=failures,
        registry_snapshot_hash=snap.get("combined_sha256"),
    )


def _run_eval_function(name: str, fn, out_path: str) -> dict[str, Any]:
    print(f"[phase30] starting {name}", flush=True)
    try:
        result = fn(out_path)
    except Exception as exc:  # pragma: no cover - defensive readiness wrapper
        return _step(name, "failed", error=repr(exc))
    status = result.get("overall_status") or result.get("status") or "unknown"
    return _step(name, "passed" if status == "passed" else "failed", output_dir=out_path, summary_status=status)

def _run_command(name: str, cmd: list[str], timeout: int = 240) -> dict[str, Any]:
    print(f"[phase30] starting {name}", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    return _step(
        name,
        "passed" if proc.returncode == 0 else "failed",
        exit_code=proc.returncode,
        command=cmd,
        stdout_tail=(proc.stdout or "").strip()[-1200:],
        stderr_tail=(proc.stderr or "").strip()[-1200:],
    )



def _sanitize_phase30_out_dir(out_dir: Path) -> Path:
    try:
        resolved = out_dir.expanduser().resolve()
    except OSError:
        return out_dir
    if _is_within(resolved, ROOT) and _is_local_temp_rel(resolved.relative_to(ROOT)):
        target = (_safe_trial_temp_parent() / resolved.name).resolve()
        target.mkdir(parents=True, exist_ok=True)
        return target
    return out_dir

def run_phase30_v1_rc_candidate_check(out_dir: str | Path, mode: str = "full") -> dict[str, Any]:
    out_dir = _sanitize_phase30_out_dir(Path(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode not in {"quick-integrity", "full"}:
        raise ValueError("mode must be 'quick-integrity' or 'full'")

    steps: list[dict[str, Any]] = [
        _static_docs_check(),
        _status_language_check(),
        _manifest_check(),
        _registry_snapshot_validity_check(),
        _run_eval_function("phase25_verified_intent_contract", run_phase25_verified_intent_contract_eval, ainir_temp_str("ainir_phase30_phase25_verified_intent_contract")),
    ]
    if mode == "full":
        steps.append(_run_eval_function("phase26_private_trial", run_phase26_private_trial, ainir_temp_str("ainir_phase30_phase26_private_trial")))
    else:
        steps.append(_step("phase26_private_trial", "not_run", reason="quick-integrity mode skips the heavier private-trial simulation"))
    passed = sum(1 for s in steps if s["status"] == "passed")
    failed = [s for s in steps if s["status"] not in {"passed", "not_run"}]
    report = {
        "phase": "pre_v1_phase30_v1_0_rc_candidate",
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(out_dir),
        "overall_status": "passed" if not failed else "failed",
        "decision": ("v1_0_rc_candidate_ready_for_private_github_trial" if mode == "full" and not failed else "quick_integrity_passed_full_release_check_not_run" if mode == "quick-integrity" and not failed else "needs_fix_before_rc_candidate"),
        "steps_total": len(steps),
        "steps_passed": passed,
        "steps_failed": len(failed),
        "production_runtime_ready": False,
        "v1_final_ready": False,
        "human_external_review": "pending",
        "steps": steps,
    }
    (out_dir / "phase30_v1_rc_candidate_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# AiNIR Phase 30 v1.0 RC Candidate Check",
        "",
        f"overall_status: {report['overall_status']}",
        f"mode: {report['mode']}",
        f"decision: {report['decision']}",
        "",
        "This check confirms RC candidate scope, status language, manifest presence, Phase 26 private-trial simulation, and Phase 25 VerifiedIntentPacket contract strictness.",
        "",
        "AiNIR remains not v1.0 final and not a production runtime.",
    ]
    for s in steps:
        lines.append(f"- {s['name']}: {s['status']}")
    (out_dir / "phase30_v1_rc_candidate_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report
