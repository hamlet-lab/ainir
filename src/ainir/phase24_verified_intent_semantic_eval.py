from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .core import load_draft
from .execution_context import TrustedExecutionContext
from .verified_intent_export import export_verified_intent_packet, validate_verified_intent_packet


def run_phase24_verified_intent_semantic_eval(out_dir: str | Path = "phase24_verified_intent_semantic_results") -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    context = TrustedExecutionContext.public_demo()
    safe_path = Path.cwd() / "fixtures" / "aivl_consumer_profile" / "pii_export_allowed" / "draft.yaml"
    safe_result = export_verified_intent_packet(load_draft(safe_path), context, "AIVL")
    cases: list[dict[str, Any]] = []

    def add_export_case(case_id: str, expected_status: str, actual_status: str, errors: list[str] | None = None, packet: dict[str, Any] | None = None, extra_ok: bool = True) -> None:
        errors = errors or []
        passed = actual_status == expected_status and not errors and extra_ok
        cases.append({
            "case_id": case_id,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "packet_validation_errors": errors,
            "passed": passed,
        })
        if packet is not None:
            (out / f"{case_id}.verified_intent_packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_invalid_packet_case(case_id: str, mutator, expected_substring: str) -> None:
        assert safe_result.packet is not None
        packet = copy.deepcopy(safe_result.packet)
        mutator(packet)
        errors = validate_verified_intent_packet(packet)
        passed = bool(errors) and any(expected_substring in err for err in errors)
        cases.append({
            "case_id": case_id,
            "expected_status": "packet_invalid",
            "actual_status": "packet_invalid" if errors else "packet_valid",
            "expected_error_substring": expected_substring,
            "packet_validation_errors": errors,
            "passed": passed,
        })
        (out / f"{case_id}.packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")

    if safe_result.status == "exported" and safe_result.packet:
        errors = validate_verified_intent_packet(safe_result.packet)
        slots = safe_result.packet["slots"]
        extra_ok = (
            slots["groundings"] == []
            and slots["grounding_status"]["status"] == "consumer_must_ground"
            and "schema_grounding_required" in slots["grounding_status"]["required_consumer_checks"]
            and "PIIExport" in slots["effects"]["consumer_allowed"]
            and "PIIExport" in slots["effects"]["consumer_required"]
            and "PIIExport" in slots["capabilities"]["consumer_allowed"]
            and any(c.get("classification") == "PII" and c.get("classification_scope") == "export_payload" for c in slots["security_classifications"])
        )
        add_export_case("pii_export_exported_without_concrete_groundings", "exported", safe_result.status, errors, safe_result.packet, extra_ok)
    else:
        add_export_case("pii_export_exported_without_concrete_groundings", "exported", safe_result.status, list(safe_result.reasons), safe_result.packet)

    add_invalid_packet_case("empty_evidence_bindings_invalid", lambda p: p["slots"].__setitem__("evidence_bindings", []), "evidence")
    add_invalid_packet_case("empty_required_contracts_invalid", lambda p: p["slots"].__setitem__("required_contracts", []), "missing required contracts")
    add_invalid_packet_case("missing_pii_export_effect_invalid", lambda p: p["slots"]["effects"]["consumer_allowed"].remove("PIIExport"), "PIIExportRequest missing required consumer_allowed effects")
    add_invalid_packet_case("missing_pii_export_required_effect_invalid", lambda p: p["slots"]["effects"].__setitem__("consumer_required", ["PIIRead"]), "requires effects.consumer_required")
    add_invalid_packet_case("missing_pii_export_capability_invalid", lambda p: p["slots"]["capabilities"]["consumer_allowed"].remove("PIIExport"), "missing required consumer_allowed capabilities")
    add_invalid_packet_case("malicious_intent_invalid", lambda p: p["slots"].__setitem__("intent", {"task_intent":"delete_all", "operation_kind":"destructive_workflow"}), "intent.task_intent")
    add_invalid_packet_case("delete_allowed_operation_invalid", lambda p: p["slots"]["operation_constraints"].__setitem__("allowed_operations", p["slots"]["operation_constraints"]["allowed_operations"] + ["delete"]), "unsupported operations")
    add_invalid_packet_case("semantic_role_in_allowed_operations_invalid", lambda p: p["slots"]["operation_constraints"].__setitem__("allowed_operations", p["slots"]["operation_constraints"]["allowed_operations"] + ["encrypted_or_safe_export"]), "unsupported operations")
    add_invalid_packet_case("unsupported_task_family_invalid", lambda p: p["slots"]["profile_scope"].__setitem__("task_family", "generic_pipeline"), "task_family")
    add_invalid_packet_case("concrete_grounding_invalid", lambda p: p["slots"].__setitem__("groundings", [{"phrase":"active customers","source":"customers","field_path":["active"],"confidence":0.99}]), "groundings must be empty")
    add_invalid_packet_case("missing_security_classification_invalid", lambda p: p["slots"].__setitem__("security_classifications", []), "security classification")
    add_invalid_packet_case("missing_schema_grounding_required_invalid", lambda p: p["slots"]["grounding_status"].__setitem__("required_consumer_checks", ["projection_matches"]), "schema_grounding_required")

    summary = {
        "phase": "pre_v1_phase24_verified_intent_packet_semantic_grounding_and_validator_hardening",
        "overall_status": "passed" if all(c["passed"] for c in cases) else "failed",
        "case_count": len(cases),
        "passed": sum(1 for c in cases if c["passed"]),
        "failed": sum(1 for c in cases if not c["passed"]),
        "cases": cases,
    }
    (out / "phase24_verified_intent_semantic_eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
