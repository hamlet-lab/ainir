from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml

from .core import load_draft, load_yaml_no_duplicate_keys
from .execution_context import TrustedExecutionContext
from .verified_intent_export import export_verified_intent_packet, validate_verified_intent_packet


def run_phase23_verified_intent_hardening_eval(out_dir: str | Path = "phase23_verified_intent_hardening_results") -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    context = TrustedExecutionContext.public_demo()
    repo_root = Path.cwd()
    safe_path = repo_root / "fixtures" / "aivl_consumer_profile" / "pii_export_allowed" / "draft.yaml"
    base = load_yaml_no_duplicate_keys(safe_path.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []

    def add_result(case_id: str, result, expected_status: str, expected_reason: str | None = None, extra_check=None) -> None:
        errors = validate_verified_intent_packet(result.packet) if result.packet else []
        passed = result.status == expected_status and (not expected_reason or expected_reason in result.reasons)
        if result.packet and errors:
            passed = False
        if extra_check is not None:
            try:
                passed = passed and bool(extra_check(result.packet))
            except Exception:
                passed = False
        cases.append({
            "case_id": case_id,
            "expected_status": expected_status,
            "actual_status": result.status,
            "expected_reason": expected_reason,
            "actual_reasons": list(result.reasons),
            "packet_validation_errors": errors,
            "passed": passed,
        })
        if result.packet:
            (out / f"{case_id}.verified_intent_packet.json").write_text(json.dumps(result.packet, indent=2, ensure_ascii=False), encoding="utf-8")

    def write_temp(temp: Path, name: str, doc: dict[str, Any]) -> Path:
        p = temp / f"{name}.yaml"
        p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return p

    def require_pii_export_packet(packet: dict[str, Any] | None) -> bool:
        if not packet:
            return False
        slots = packet["slots"]
        return (
            slots["profile_scope"]["workflow"] == "PIIExportRequest"
            and "PIIExport" in slots["effects"]["consumer_allowed"]
            and "PIIExport" in slots["capabilities"]["consumer_allowed"]
            and not (set(slots["effects"]["consumer_allowed"]) & set(slots["effects"]["consumer_denied"]))
            and not (set(slots["capabilities"]["consumer_allowed"]) & set(slots["capabilities"]["consumer_denied"]))
            and slots["ambiguity"]["status"] == "resolved"
            and slots["ambiguity"]["unresolved_ambiguities"] == []
        )

    safe_result = export_verified_intent_packet(load_draft(safe_path), context, "AIVL")
    add_result("pii_export_with_evidence_allowed", safe_result, "exported", extra_check=require_pii_export_packet)

    with TemporaryDirectory() as td:
        temp = Path(td)

        no_evidence = copy.deepcopy(base)
        no_evidence["module"] = "demo.pii_export_without_evidence_blocked"
        no_evidence["claims"] = []
        add_result("pii_export_without_evidence_blocked", export_verified_intent_packet(load_draft(write_temp(temp, "no_evidence", no_evidence)), context, "AIVL"), "refused", "trust_gate_not_passed")

        ambiguous = copy.deepcopy(base)
        ambiguous["ambiguity"] = {"status": "requires_clarification", "unresolved_ambiguities": [{"slot": "top_customers_metric", "question": "Does top mean revenue, order count, or recency?"}]}
        add_result("ambiguous_top_customers_blocked", export_verified_intent_packet(load_draft(write_temp(temp, "ambiguous", ambiguous)), context, "AIVL"), "refused", "unresolved_ambiguity")

        contradictory_ambiguity = copy.deepcopy(base)
        contradictory_ambiguity["ambiguity"] = {"status": "resolved", "unresolved_ambiguities": [{"slot": "x"}]}
        add_result("resolved_with_unresolved_ambiguity_blocked", export_verified_intent_packet(load_draft(write_temp(temp, "bad_ambiguity", contradictory_ambiguity)), context, "AIVL"), "refused", "unresolved_ambiguity")

        network = copy.deepcopy(base)
        network["module"] = "demo.network_export_denied"
        network["operations"] = list(base["operations"]) + [{"id": "op.network", "op": "http.call", "effects": ["effect.external.network.call"], "capabilities": ["cap.http.call"]}]
        add_result("network_export_denied", export_verified_intent_packet(load_draft(write_temp(temp, "network", network)), context, "AIVL"), "refused", "trust_gate_not_passed")

        raw_intent = copy.deepcopy(base)
        raw_intent["intent"] = {"task_intent": "delete_all_customers", "operation_kind": "destructive_workflow", "natural_language_summary": "Delete all customer records."}
        add_result("raw_intent_override_refused", export_verified_intent_packet(load_draft(write_temp(temp, "raw_intent", raw_intent)), context, "AIVL"), "refused", "raw_intent_slot_not_exportable")

        raw_grounding = copy.deepcopy(base)
        raw_grounding["groundings"] = [{"phrase": "emails", "source": "admin_secrets", "field_path": ["root_key"], "classification": "Secret", "confidence": 1.0}]
        add_result("raw_grounding_override_refused", export_verified_intent_packet(load_draft(write_temp(temp, "raw_grounding", raw_grounding)), context, "AIVL"), "refused", "raw_groundings_slot_not_exportable")

        raw_classification = copy.deepcopy(base)
        raw_classification["field_classifications"] = [{"source": "customers", "field_path": ["email"], "classification": "PublicText"}]
        add_result("raw_classification_override_refused", export_verified_intent_packet(load_draft(write_temp(temp, "raw_classification", raw_classification)), context, "AIVL"), "refused", "raw_field_classifications_slot_not_exportable")

        create_user = load_yaml_no_duplicate_keys((repo_root / "examples" / "create_user_outbox_safe" / "draft.yaml").read_text(encoding="utf-8"))
        add_result("unsupported_workflow_create_user_refused", export_verified_intent_packet(load_draft(write_temp(temp, "create_user", create_user)), context, "AIVL"), "refused", "consumer_profile_does_not_support_workflow")

        bad_packet = copy.deepcopy(safe_result.packet)
        assert bad_packet is not None
        bad_packet["slots"]["effects"]["consumer_denied"].append("PIIExport")
        packet_errors = validate_verified_intent_packet(bad_packet)
        cases.append({
            "case_id": "contradictory_allowed_denied_packet_invalid",
            "expected_status": "packet_invalid",
            "actual_status": "packet_invalid" if packet_errors else "packet_valid",
            "expected_reason": "effects consumer_allowed/consumer_denied",
            "actual_reasons": packet_errors,
            "packet_validation_errors": packet_errors,
            "passed": bool(packet_errors),
        })

        bad_hash_packet = copy.deepcopy(safe_result.packet)
        assert bad_hash_packet is not None
        bad_hash_packet["slots"]["receipt_links"]["registry_hash"] = "sha256:nothex"
        packet_errors = validate_verified_intent_packet(bad_hash_packet)
        cases.append({
            "case_id": "malformed_sha256_packet_invalid",
            "expected_status": "packet_invalid",
            "actual_status": "packet_invalid" if packet_errors else "packet_valid",
            "expected_reason": "sha256",
            "actual_reasons": packet_errors,
            "packet_validation_errors": packet_errors,
            "passed": bool(packet_errors),
        })

    summary = {
        "phase": "pre_v1_phase23_verified_intent_export_contract_hardening",
        "overall_status": "passed" if all(c["passed"] for c in cases) else "failed",
        "case_count": len(cases),
        "passed": sum(1 for c in cases if c["passed"]),
        "failed": sum(1 for c in cases if not c["passed"]),
        "cases": cases,
    }
    (out / "phase23_verified_intent_hardening_eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
