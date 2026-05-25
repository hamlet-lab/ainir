from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .core import load_draft
from .execution_context import TrustedExecutionContext
from .verified_intent_export import export_verified_intent_packet, validate_verified_intent_packet
from .temp_paths import ainir_temp_str


def run_phase25_verified_intent_contract_eval(out_dir: str | Path = ainir_temp_str("ainir_phase25_verified_intent_contract")) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    context = TrustedExecutionContext.public_demo()
    safe_path = Path.cwd() / "fixtures" / "aivl_consumer_profile" / "pii_export_allowed" / "draft.yaml"
    safe_result = export_verified_intent_packet(load_draft(safe_path), context, "AIVL")
    cases: list[dict[str, Any]] = []

    def record_valid_export(case_id: str, ok: bool, errors: list[str], packet: dict[str, Any] | None) -> None:
        cases.append({
            "case_id": case_id,
            "expected_status": "exported_valid_packet",
            "actual_status": "exported_valid_packet" if ok else "failed",
            "packet_validation_errors": errors,
            "passed": ok,
        })
        if packet is not None:
            (out / f"{case_id}.packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")

    def invalid_packet_case(case_id: str, mutator, expected_substring: str) -> None:
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

    valid = safe_result.status == "exported" and safe_result.packet is not None
    errors = validate_verified_intent_packet(safe_result.packet) if safe_result.packet else list(safe_result.reasons)
    record_valid_export("pii_export_with_strict_contract_valid", valid and not errors, errors, safe_result.packet)

    invalid_packet_case("top_level_extra_field_invalid", lambda p: p.__setitem__("extra", True), "packet contains unsupported fields")
    invalid_packet_case("trust_extra_field_invalid", lambda p: p["slots"]["trust"].__setitem__("extra", True), "trust contains unsupported fields")
    invalid_packet_case("effects_extra_field_invalid", lambda p: p["slots"]["effects"].__setitem__("extra", []), "effects contains unsupported fields")
    invalid_packet_case("receipt_extra_field_invalid", lambda p: p["slots"]["receipt_links"].__setitem__("extra", "x"), "receipt_links contains unsupported fields")
    invalid_packet_case("evidence_source_field_invalid", lambda p: p["slots"]["evidence_bindings"][0].__setitem__("source", "claude"), "evidence_bindings[0] contains unsupported fields")
    invalid_packet_case("empty_denied_operations_invalid", lambda p: p["slots"]["operation_constraints"].__setitem__("denied_operations", []), "denied_operations must be non-empty")
    invalid_packet_case("requires_human_review_false_invalid", lambda p: p["slots"]["operation_constraints"].__setitem__("requires_human_review", False), "requires_human_review must be true")
    invalid_packet_case("empty_canonical_operations_invalid", lambda p: p["slots"]["operation_constraints"].__setitem__("canonical_operations", []), "canonical_operations must be a non-empty list")
    invalid_packet_case("superadmin_effect_invalid", lambda p: p["slots"]["effects"]["consumer_allowed"].append("SuperAdminEffect"), "effects.consumer_allowed contains unsupported values")
    invalid_packet_case("superadmin_capability_invalid", lambda p: p["slots"]["capabilities"]["consumer_allowed"].append("SuperAdminCap"), "capabilities.consumer_allowed contains unsupported values")
    invalid_packet_case("superadmin_required_effect_invalid", lambda p: p["slots"]["effects"]["consumer_required"].append("SuperAdminEffect"), "effects.consumer_required contains unsupported values")
    invalid_packet_case("unsupported_semantic_role_invalid", lambda p: p["slots"]["operation_constraints"]["semantic_roles"].append("exfiltrate_role"), "operation_constraints.semantic_roles contains unsupported values")
    invalid_packet_case("missing_pii_export_boundary_invalid", lambda p: p["slots"]["required_contracts"].remove("pii_export_boundary_declared"), "missing required contracts")
    invalid_packet_case("unsupported_contract_invalid", lambda p: p["slots"]["required_contracts"].append("delete_allowed"), "unsupported contracts")
    invalid_packet_case("missing_profile_status_invalid", lambda p: p.pop("profile_status"), "profile_status")
    invalid_packet_case("profile_status_extra_value_invalid", lambda p: p.__setitem__("profile_status", "other"), "profile_status")

    summary = {
        "phase": "pre_v1_phase25_verified_intent_packet_contract_strictness_and_registry_consistency",
        "overall_status": "passed" if all(c["passed"] for c in cases) else "failed",
        "case_count": len(cases),
        "passed": sum(1 for c in cases if c["passed"]),
        "failed": sum(1 for c in cases if not c["passed"]),
        "cases": cases,
    }
    (out / "phase25_verified_intent_contract_eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run AiNIR pre-v1 Phase 25 VerifiedIntentPacket strict contract evaluation.")
    parser.add_argument("--out-dir", default=ainir_temp_str("ainir_phase25_verified_intent_contract"))
    args = parser.parse_args()
    report = run_phase25_verified_intent_contract_eval(args.out_dir)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report.get("overall_status") == "passed" else 2)
