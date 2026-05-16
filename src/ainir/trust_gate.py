
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Mapping

import yaml

from .core import DraftModule, Finding, VerificationReport
from .execution_context import TrustedExecutionContext
from .lowering_gate import assess_lowering_eligibility
from .verifier import verify_draft
from .safety_registry import get_registry


_GATE_PREFIXES: dict[str, str] = {
    "S": "strict_draft_ast",
    "N": "safety_registry_resolution",
    "W": "workflow_registry",
    "X": "trusted_execution_context",
    "TR": "evidence_ledger_binding",
    "T": "trust_gate",
    "O": "operation_spec_binding",
    "P": "policy_core",
    "C": "capability_contract",
    "WF": "workflow_semantic_profile",
    "M": "workflow_semantic_profile",
    "TX": "transaction_binding",
    "H": "hole_resolution",
    "L": "lowering_eligibility",
}

_REQUIRED_GATES = [
    "strict_draft_ast",
    "safety_registry_resolution",
    "workflow_registry",
    "trusted_execution_context",
    "evidence_ledger_binding",
    "operation_spec_binding",
    "capability_contract",
    "workflow_semantic_profile",
    "transaction_binding",
    "policy_core",
    "lowering_eligibility",
]


@dataclass(frozen=True)
class TrustGateDecision:
    """Unified AiNIR trust-gate surface.

    This object is an AiNIR-internal decision surface. It is not an adapter for
    any downstream compiler/runtime. Optional export surfaces may consume this
    decision later, but they do not define AiNIR's core trust gate.
    """

    status: str
    module_id: str
    workflow: str
    executable: bool
    lowering_allowed: bool
    handoff_allowed: bool
    trusted_environment: str
    satisfied_gates: tuple[str, ...] = field(default_factory=tuple)
    failed_gates: tuple[str, ...] = field(default_factory=tuple)
    warning_gates: tuple[str, ...] = field(default_factory=tuple)
    required_next_actions: tuple[str, ...] = field(default_factory=tuple)
    verifier_report: Mapping[str, Any] = field(default_factory=dict)
    lowering_eligibility: Mapping[str, Any] = field(default_factory=dict)
    findings: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    receipt: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": "AiNIRTrustGateDecision",
            "version": "pre_v1_phase18",
            "status": self.status,
            "module_id": self.module_id,
            "workflow": self.workflow,
            "executable": self.executable,
            "lowering_allowed": self.lowering_allowed,
            "handoff_allowed": self.handoff_allowed,
            "trusted_environment": self.trusted_environment,
            "satisfied_gates": list(self.satisfied_gates),
            "failed_gates": list(self.failed_gates),
            "warning_gates": list(self.warning_gates),
            "required_next_actions": list(self.required_next_actions),
            "verifier_report": dict(self.verifier_report),
            "lowering_eligibility": dict(self.lowering_eligibility),
            "findings": [dict(f) for f in self.findings],
            "receipt": dict(self.receipt),
        }


def evaluate_trust_gate(draft: DraftModule, context: TrustedExecutionContext | None = None) -> TrustGateDecision:
    context = context or TrustedExecutionContext.public_demo()
    verifier_report = verify_draft(draft, context)
    lowering = assess_lowering_eligibility(draft, verifier_report, context)
    verifier_dict = verifier_report.as_dict()
    lowering_dict = lowering.as_dict()

    all_findings: list[dict[str, Any]] = list(verifier_dict.get("findings", [])) + list(lowering_dict.get("findings", []))
    failed = sorted({_gate_for_rule(str(f.get("rule", ""))) for f in all_findings if f.get("severity") == "critical"})
    failed = [g for g in failed if g]
    warnings = sorted({_gate_for_rule(str(f.get("rule", ""))) for f in all_findings if f.get("severity") == "warning"})
    warnings = [g for g in warnings if g and g not in failed]

    if verifier_report.status == "invalid":
        status = "invalid"
    elif verifier_report.status != "passed" or not lowering.allowed:
        status = "refused"
    else:
        status = "passed"

    lowering_allowed = status == "passed" and lowering.allowed
    executable = lowering_allowed
    handoff_allowed = status == "passed"
    satisfied = tuple(g for g in _REQUIRED_GATES if g not in set(failed))
    next_actions = tuple(_next_actions(all_findings, status))
    receipt = _build_receipt(draft, context, verifier_report, lowering_dict, status, failed, warnings)

    return TrustGateDecision(
        status=status,
        module_id=verifier_report.module_id,
        workflow=verifier_report.workflow,
        executable=executable,
        lowering_allowed=lowering_allowed,
        handoff_allowed=handoff_allowed,
        trusted_environment=context.environment,
        satisfied_gates=tuple(satisfied),
        failed_gates=tuple(failed),
        warning_gates=tuple(warnings),
        required_next_actions=next_actions,
        verifier_report=verifier_dict,
        lowering_eligibility=lowering_dict,
        findings=tuple(all_findings),
        receipt=receipt,
    )


def _gate_for_rule(rule: str) -> str:
    # Rule identifiers start with an uppercase prefix such as S060, TR001,
    # TX001, or L008. Extract the alphabetic prefix explicitly instead of
    # relying on prefix-length sorting, so adding future prefixes cannot
    # silently change gate classification.
    match = re.match(r"^[A-Z]+", rule or "")
    if not match:
        return "unknown_gate"
    return _GATE_PREFIXES.get(match.group(0), "unknown_gate")


def _next_actions(findings: list[Mapping[str, Any]], status: str) -> list[str]:
    if status == "passed":
        return []
    actions: list[str] = []
    rules = {str(f.get("rule", "")) for f in findings}
    if any("evidence" in r.lower() or r.startswith("TR") for r in rules):
        actions.append("provide_ledger_bound_evidence")
    if any(r.startswith("S") for r in rules):
        actions.append("repair_draft_structure")
    if any(r.startswith("O") for r in rules):
        actions.append("bind_operations_to_registered_specs")
    if any(r.startswith("C") for r in rules):
        actions.append("reduce_capabilities_to_exact_operation_contract")
    if any(r.startswith("TX") for r in rules):
        actions.append("repair_transaction_contract")
    if any(r.startswith("L") for r in rules):
        actions.append("rerun_verification_before_lowering")
    if not actions:
        actions.append("review_trust_gate_findings")
    return sorted(set(actions))


def _build_receipt(
    draft: DraftModule,
    context: TrustedExecutionContext,
    report: VerificationReport,
    lowering: Mapping[str, Any],
    status: str,
    failed_gates: list[str],
    warning_gates: list[str],
) -> dict[str, Any]:
    source_path = draft.raw.get("__source_path__")
    draft_payload = {k: v for k, v in draft.raw.items() if not str(k).startswith("__")}
    draft_text = yaml.safe_dump(draft_payload, sort_keys=True, allow_unicode=True)
    draft_hash = "sha256:" + sha256(draft_text.encode("utf-8")).hexdigest()
    registry = get_registry()
    registry_text = json.dumps(registry.data, sort_keys=True, ensure_ascii=False)
    registry_hash = "sha256:" + sha256(registry_text.encode("utf-8")).hexdigest()
    report_text = json.dumps(report.as_dict(), sort_keys=True, ensure_ascii=False)
    report_hash = "sha256:" + sha256(report_text.encode("utf-8")).hexdigest()
    receipt_seed = "|".join([draft_hash, registry_hash, report_hash, context.environment, status])
    receipt_id = "ainir.trust.receipt." + sha256(receipt_seed.encode("utf-8")).hexdigest()[:20]
    receipt = {
        "receipt_id": receipt_id,
        "receipt_kind": "AiNIRTrustReceipt",
        "version": "pre_v1_phase18",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "module_id": report.module_id,
        "workflow": report.workflow,
        "draft_hash": draft_hash,
        "draft_source_path": str(source_path) if isinstance(source_path, str) else None,
        "safety_registry_hash": registry_hash,
        "verifier_report_hash": report_hash,
        "trusted_context": {
            "environment": context.environment,
            "source": context.source,
            "purpose": context.purpose,
        },
        "failed_gates": failed_gates,
        "warning_gates": warning_gates,
        "lowering_eligibility": dict(lowering),
        "production_runtime_ready": False,
        "v1_final_ready": False,
        "external_consumer_handoff": {
            "status": "future_extension_point",
            "note": "AiNIR may expose verified intent artifacts later; no external consumer is part of the current pre-v1 public demo.",
        },
    }
    # Imported lazily to avoid a module import cycle at import time.
    from .trust_receipt_store import stable_receipt_projection_hash

    receipt["stable_receipt_projection_hash"] = stable_receipt_projection_hash(receipt)
    return receipt
