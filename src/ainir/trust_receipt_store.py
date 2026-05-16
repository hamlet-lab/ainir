from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .core import load_draft
from .execution_context import TrustedExecutionContext
from .trust_gate import evaluate_trust_gate


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(data: Mapping[str, Any]) -> str:
    return _sha256_text(_canonical_json(data))


def _stable_lowering_projection(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"status": None, "findings": []}
    findings = value.get("findings", [])
    stable_findings = []
    if isinstance(findings, list):
        for f in findings:
            if isinstance(f, Mapping):
                stable_findings.append({
                    "rule": f.get("rule"),
                    "severity": f.get("severity"),
                    "target": f.get("target"),
                    "message": f.get("message"),
                })
    return {
        "status": value.get("status"),
        "context_environment": value.get("context_environment"),
        "findings": stable_findings,
    }


def stable_receipt_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Return the tamper-evident stable receipt fields used by replay.

    Timestamps and local file paths are intentionally excluded. The projection is
    not a cryptographic signature, but it makes receipt-field edits visible to
    local replay unless the entire receipt is knowingly recomputed.
    """
    trusted_context = receipt.get("trusted_context") if isinstance(receipt.get("trusted_context"), Mapping) else {}
    return {
        "receipt_id": receipt.get("receipt_id"),
        "receipt_kind": receipt.get("receipt_kind"),
        "version": receipt.get("version"),
        "status": receipt.get("status"),
        "module_id": receipt.get("module_id"),
        "workflow": receipt.get("workflow"),
        "draft_hash": receipt.get("draft_hash"),
        "safety_registry_hash": receipt.get("safety_registry_hash"),
        "verifier_report_hash": receipt.get("verifier_report_hash"),
        "trusted_context": {
            "environment": trusted_context.get("environment"),
            "source": trusted_context.get("source"),
            "purpose": trusted_context.get("purpose"),
        },
        "failed_gates": list(receipt.get("failed_gates") or []),
        "warning_gates": list(receipt.get("warning_gates") or []),
        "lowering_eligibility": _stable_lowering_projection(receipt.get("lowering_eligibility")),
        "production_runtime_ready": receipt.get("production_runtime_ready"),
        "v1_final_ready": receipt.get("v1_final_ready"),
    }


def stable_receipt_projection_hash(receipt: Mapping[str, Any]) -> str:
    return _sha256_json(stable_receipt_projection(receipt))


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError("receipt JSON root must be an object")
    return value


@dataclass(frozen=True)
class IssuedTrustReceipt:
    decision: Mapping[str, Any]
    receipt: Mapping[str, Any]
    receipt_path: str
    decision_path: str
    manifest_path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "overall_status": "issued",
            "receipt_id": self.receipt.get("receipt_id"),
            "trust_status": self.decision.get("status"),
            "module_id": self.decision.get("module_id"),
            "workflow": self.decision.get("workflow"),
            "receipt_path": self.receipt_path,
            "decision_path": self.decision_path,
            "manifest_path": self.manifest_path,
        }


@dataclass(frozen=True)
class ReceiptReplayReport:
    overall_status: str
    receipt_id: str | None
    checks: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    fresh_decision: Mapping[str, Any] = field(default_factory=dict)
    receipt: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "receipt_id": self.receipt_id,
            "checks": [dict(c) for c in self.checks],
            "fresh_decision": dict(self.fresh_decision),
            "receipt": dict(self.receipt),
        }


def issue_trust_receipt(
    draft_path: str | Path,
    out_dir: str | Path,
    context: TrustedExecutionContext | None = None,
) -> IssuedTrustReceipt:
    """Run the Trust Gate and persist its decision plus receipt.

    A receipt is not a substitute for replay. It is a signed-by-structure local
    artifact: future replay must recompute hashes and the Trust Gate decision.
    """
    context = context or TrustedExecutionContext.public_demo()
    draft = load_draft(draft_path)
    decision = evaluate_trust_gate(draft, context).as_dict()
    receipt = dict(decision["receipt"])
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt_id = str(receipt.get("receipt_id") or "receipt.unknown")
    safe_name = receipt_id.replace(":", "_").replace("/", "_")
    decision_path = out / f"{safe_name}.decision.json"
    receipt_path = out / f"{safe_name}.receipt.json"
    manifest_path = out / "trust_receipt_manifest.jsonl"
    decision_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    receipt_record = {
        "receipt_id": receipt_id,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "trust_status": decision.get("status"),
        "module_id": decision.get("module_id"),
        "workflow": decision.get("workflow"),
        "draft_hash": receipt.get("draft_hash"),
        "safety_registry_hash": receipt.get("safety_registry_hash"),
        "verifier_report_hash": receipt.get("verifier_report_hash"),
        "receipt_file_hash": _sha256_text(_canonical_json(receipt)),
        "decision_file_hash": _sha256_text(_canonical_json(decision)),
        "receipt_path": str(receipt_path),
        "decision_path": str(decision_path),
    }
    with manifest_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt_record, sort_keys=True, ensure_ascii=False) + "\n")
    return IssuedTrustReceipt(
        decision=decision,
        receipt=receipt,
        receipt_path=str(receipt_path),
        decision_path=str(decision_path),
        manifest_path=str(manifest_path),
    )


def replay_trust_receipt(
    receipt_path: str | Path,
    draft_path: str | Path | None = None,
    context: TrustedExecutionContext | None = None,
) -> ReceiptReplayReport:
    """Replay a stored receipt against the current draft and registry.

    Replay passes only when the current Trust Gate decision reproduces the
    receipt's stable hashes and decision fields. The receipt's `generated_at`
    timestamp is intentionally ignored.
    """
    receipt = _read_json(receipt_path)
    source = draft_path if draft_path is not None else receipt.get("draft_source_path")
    checks: list[dict[str, Any]] = []
    if not isinstance(source, (str, Path)) or not str(source):
        return ReceiptReplayReport(
            overall_status="failed",
            receipt_id=receipt.get("receipt_id") if isinstance(receipt.get("receipt_id"), str) else None,
            receipt=receipt,
            checks=({
                "check": "draft_source_available",
                "status": "failed",
                "expected": "draft path provided or receipt.draft_source_path present",
                "actual": source,
            },),
        )
    source_path = Path(source)
    if not source_path.exists():
        return ReceiptReplayReport(
            overall_status="failed",
            receipt_id=receipt.get("receipt_id") if isinstance(receipt.get("receipt_id"), str) else None,
            receipt=receipt,
            checks=({
                "check": "draft_source_exists",
                "status": "failed",
                "expected": str(source_path),
                "actual": "missing",
            },),
        )
    if context is None:
        env = None
        source_value = "receipt_replay"
        purpose_value = "trust_receipt_replay"
        tc = receipt.get("trusted_context")
        if isinstance(tc, dict):
            if isinstance(tc.get("environment"), str):
                env = tc.get("environment")
            if isinstance(tc.get("source"), str) and tc.get("source"):
                source_value = tc.get("source")
            if isinstance(tc.get("purpose"), str) and tc.get("purpose"):
                purpose_value = tc.get("purpose")
        context = TrustedExecutionContext.from_environment(env or "public_demo", source=source_value, purpose=purpose_value)
    draft = load_draft(source_path)
    fresh = evaluate_trust_gate(draft, context).as_dict()
    fresh_receipt = dict(fresh.get("receipt", {}))

    stored_projection_hash = receipt.get("stable_receipt_projection_hash")
    supplied_projection_hash = stable_receipt_projection_hash(receipt)
    fresh_projection_hash = stable_receipt_projection_hash(fresh_receipt)

    comparisons = [
        ("receipt_id", receipt.get("receipt_id"), fresh_receipt.get("receipt_id")),
        ("status", receipt.get("status"), fresh_receipt.get("status")),
        ("module_id", receipt.get("module_id"), fresh_receipt.get("module_id")),
        ("workflow", receipt.get("workflow"), fresh_receipt.get("workflow")),
        ("draft_hash", receipt.get("draft_hash"), fresh_receipt.get("draft_hash")),
        ("safety_registry_hash", receipt.get("safety_registry_hash"), fresh_receipt.get("safety_registry_hash")),
        ("verifier_report_hash", receipt.get("verifier_report_hash"), fresh_receipt.get("verifier_report_hash")),
        ("trusted_environment", _nested(receipt, ["trusted_context", "environment"]), _nested(fresh_receipt, ["trusted_context", "environment"])),
        ("trusted_context_source", _nested(receipt, ["trusted_context", "source"]), _nested(fresh_receipt, ["trusted_context", "source"])),
        ("trusted_context_purpose", _nested(receipt, ["trusted_context", "purpose"]), _nested(fresh_receipt, ["trusted_context", "purpose"])),
        ("failed_gates", receipt.get("failed_gates"), fresh_receipt.get("failed_gates")),
        ("warning_gates", receipt.get("warning_gates"), fresh_receipt.get("warning_gates")),
        ("lowering_eligibility", _stable_lowering_projection(receipt.get("lowering_eligibility")), _stable_lowering_projection(fresh_receipt.get("lowering_eligibility"))),
        ("production_runtime_ready", receipt.get("production_runtime_ready"), fresh_receipt.get("production_runtime_ready")),
        ("v1_final_ready", receipt.get("v1_final_ready"), fresh_receipt.get("v1_final_ready")),
        ("stable_receipt_projection_hash_self_check", stored_projection_hash, supplied_projection_hash),
        ("stable_receipt_projection_hash_replay", stored_projection_hash, fresh_projection_hash),
    ]
    for name, expected, actual in comparisons:
        checks.append({
            "check": name,
            "status": "passed" if expected == actual else "failed",
            "expected": expected,
            "actual": actual,
        })
    overall = "passed" if all(c["status"] == "passed" for c in checks) else "failed"
    return ReceiptReplayReport(
        overall_status=overall,
        receipt_id=receipt.get("receipt_id") if isinstance(receipt.get("receipt_id"), str) else None,
        checks=tuple(checks),
        fresh_decision=fresh,
        receipt=receipt,
    )


def _nested(data: Mapping[str, Any], path: list[str]) -> Any:
    value: Any = data
    for part in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value
