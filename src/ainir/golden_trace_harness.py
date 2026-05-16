from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import tempfile

import yaml

from .core import DraftModule, dump_yaml, load_draft
from .execution_context import TrustedExecutionContext
from .lowering import lower_to_typescript
from .trust_receipt_store import issue_trust_receipt, replay_trust_receipt
from .verifier import verify_draft


@dataclass(frozen=True)
class GoldenTraceResult:
    trace_id: str
    description: str
    expected_status: str
    actual_status: str
    passed: bool
    critical_count: int
    lowering_status: str
    trust_receipt_status: str
    output_hash: str | None = None
    receipt_id: str | None = None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "description": self.description,
            "expected_status": self.expected_status,
            "actual_status": self.actual_status,
            "passed": self.passed,
            "critical_count": self.critical_count,
            "lowering_status": self.lowering_status,
            "trust_receipt_status": self.trust_receipt_status,
            "output_hash": self.output_hash,
            "receipt_id": self.receipt_id,
            "notes": self.notes,
        }


def run_golden_traces(
    traces_path: str | Path = "golden_traces.yaml",
    out_dir: str | Path = "golden_trace_results",
    environment: str = "public_demo",
) -> dict[str, Any]:
    """Replay fixed end-to-end golden traces.

    Phase 20 extends the public conformance replay with TrustReceipt replay.
    Each trace now exercises:

      draft -> strict AST -> normalize -> verify -> lower/refuse -> receipt issue -> receipt replay

    Golden traces intentionally include both verifier-ready and refused drafts.
    A refused draft passes a trace only when it is refused, cannot be lowered,
    and its TrustReceipt replays to the same refused decision.
    """
    traces_path = Path(traces_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    root = traces_path.parent
    doc = _load_yaml(traces_path)
    context = TrustedExecutionContext.from_environment(environment, source="golden_trace_harness", purpose="conformance_replay")
    results: list[GoldenTraceResult] = []

    for trace in doc.get("traces", []):
        results.append(_run_trace(trace, root, out_dir, context))

    summary = {
        "phase": "pre_v1_phase20_trust_receipt_conformance",
        "overall_status": "passed" if all(r.passed for r in results) else "failed",
        "trace_pack": str(traces_path),
        "trusted_context": {
            "environment": context.environment,
            "source": context.source,
            "purpose": context.purpose,
        },
        "trace_count": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "receipt_replay_passed": sum(1 for r in results if r.trust_receipt_status == "replayed"),
        "receipt_replay_failed": sum(1 for r in results if r.trust_receipt_status not in {"replayed", "not_required"}),
        "results": [r.as_dict() for r in results],
    }
    dump_yaml(summary, out_dir / "golden_trace_report.yaml")
    return summary


def _run_trace(trace: dict[str, Any], root: Path, out_dir: Path, context: TrustedExecutionContext) -> GoldenTraceResult:
    trace_id = str(trace.get("id", "unnamed_trace"))
    description = str(trace.get("description", ""))
    expected_status = str(trace.get("expected_status", "blocked"))
    expect_lowering = bool(trace.get("expect_lowering", expected_status == "passed"))
    expect_enforcement_hooks = bool(trace.get("expect_enforcement_hooks", expect_lowering))
    expect_receipt_replay = bool(trace.get("expect_trust_receipt_replay", True))
    min_critical = int(trace.get("min_critical_count", 0))
    required_rules = [str(r) for r in trace.get("require_finding_rules", [])]

    trace_out = out_dir / _safe_file(trace_id)
    trace_out.mkdir(parents=True, exist_ok=True)

    draft, draft_source_path = _draft_from_trace(trace, root, trace_out)
    verify_report = verify_draft(draft, context)
    dump_yaml(verify_report.as_dict(), trace_out / "verify_report.yaml")

    notes: list[str] = []
    passed = True
    if verify_report.status != expected_status:
        passed = False
        notes.append(f"expected status {expected_status!r}, got {verify_report.status!r}")
    if verify_report.critical_count < min_critical:
        passed = False
        notes.append(f"expected at least {min_critical} critical finding(s), got {verify_report.critical_count}")
    rules = [f.rule for f in verify_report.findings]
    for required in required_rules:
        if not any(rule == required or rule.startswith(required) for rule in rules):
            passed = False
            notes.append(f"missing expected finding rule prefix {required!r}")

    lowering_status = "not_attempted"
    output_hash: str | None = None
    try:
        lowered = lower_to_typescript(draft, verify_report, trace_out / "lowered", context)
        text = lowered.read_text(encoding="utf-8")
        output_hash = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        if expect_lowering:
            lowering_status = "lowered"
            if expect_enforcement_hooks:
                for token in ["ctx.enforceModule", "ctx.enforceOperation", "verificationStatus"]:
                    if token not in text:
                        passed = False
                        notes.append(f"lowered output missing enforcement token {token!r}")
        else:
            lowering_status = "unexpectedly_lowered"
            passed = False
            notes.append("lowering succeeded for a trace that expected lowering refusal")
    except Exception as exc:  # noqa: BLE001 - harness records refusal reason
        if expect_lowering:
            lowering_status = "unexpectedly_refused"
            passed = False
            notes.append(f"lowering was expected but refused: {exc}")
        else:
            lowering_status = "refused"
            (trace_out / "lowering_refusal.txt").write_text(str(exc), encoding="utf-8")

    receipt_status = "not_required"
    receipt_id: str | None = None
    if expect_receipt_replay:
        try:
            issued = issue_trust_receipt(draft_source_path, trace_out / "trust_receipts", context)
            receipt_id = str(issued.receipt.get("receipt_id") or "") or None
            replay = replay_trust_receipt(issued.receipt_path, draft_source_path, context)
            dump_yaml(replay.as_dict(), trace_out / "trust_receipt_replay_report.yaml")
            if replay.overall_status == "passed":
                receipt_status = "replayed"
            else:
                receipt_status = "replay_failed"
                passed = False
                notes.append("TrustReceipt replay failed")
        except Exception as exc:  # noqa: BLE001 - conformance harness records failure
            receipt_status = "issue_or_replay_error"
            passed = False
            notes.append(f"TrustReceipt issue/replay error: {exc}")

    return GoldenTraceResult(
        trace_id=trace_id,
        description=description,
        expected_status=expected_status,
        actual_status=verify_report.status,
        passed=passed,
        critical_count=verify_report.critical_count,
        lowering_status=lowering_status,
        trust_receipt_status=receipt_status,
        output_hash=output_hash,
        receipt_id=receipt_id,
        notes="; ".join(notes),
    )


def _draft_from_trace(trace: dict[str, Any], root: Path, trace_out: Path) -> tuple[DraftModule, Path]:
    if "draft_ref" in trace:
        source = root / str(trace["draft_ref"])
        return load_draft(source), source
    generated_source = trace_out / "input_draft.yaml"
    if "raw_yaml" in trace:
        generated_source.write_text(str(trace["raw_yaml"]), encoding="utf-8")
        return load_draft(generated_source), generated_source
    if "draft" in trace:
        raw = trace.get("draft")
        if not isinstance(raw, dict):
            raw = {}
        generated_source.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return load_draft(generated_source), generated_source
    generated_source.write_text("{}\n", encoding="utf-8")
    return load_draft(generated_source), generated_source


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"golden trace pack root must be an object: {path}")
    return data


def _safe_file(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)[:120] or "trace"
