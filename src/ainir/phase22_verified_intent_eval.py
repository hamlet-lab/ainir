from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml

from .core import load_draft
from .execution_context import TrustedExecutionContext
from .verified_intent_export import export_verified_intent_packet, validate_verified_intent_packet


def run_phase22_verified_intent_eval(out_dir: str | Path = "phase22_verified_intent_results") -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    context = TrustedExecutionContext.public_demo()
    cases: list[dict[str, Any]] = []
    repo_root = Path.cwd()
    safe_path = repo_root / "fixtures" / "aivl_consumer_profile" / "pii_export_allowed" / "draft.yaml"

    def add_case(case_id: str, path: Path, expected_status: str, expected_reason: str | None = None) -> None:
        result = export_verified_intent_packet(load_draft(path), context, "AIVL")
        errors = validate_verified_intent_packet(result.packet) if result.packet else []
        passed = result.status == expected_status and (not expected_reason or expected_reason in result.reasons) and (result.packet is None or not errors)
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

    add_case("pii_export_with_evidence_allowed", safe_path, "exported")

    with TemporaryDirectory() as td:
        temp = Path(td)
        base = yaml.safe_load(safe_path.read_text())

        no_evidence = dict(base)
        no_evidence["module"] = "demo.pii_export_without_evidence_blocked"
        no_evidence["claims"] = []
        p = temp / "pii_export_without_evidence.yaml"
        p.write_text(yaml.safe_dump(no_evidence, sort_keys=False, allow_unicode=True), encoding="utf-8")
        add_case("pii_export_without_evidence_blocked", p, "refused", "profile_requires_verified_authorization_evidence")

        ambiguous = dict(base)
        ambiguous["module"] = "demo.ambiguous_top_customers_blocked"
        ambiguous["ambiguity"] = {"status": "requires_clarification", "unresolved_ambiguities": [{"slot": "top_customers_metric", "question": "Does top mean revenue, order count, or recency?"}]}
        p = temp / "ambiguous.yaml"
        p.write_text(yaml.safe_dump(ambiguous, sort_keys=False, allow_unicode=True), encoding="utf-8")
        add_case("ambiguous_top_customers_blocked", p, "refused", "unresolved_ambiguity")

        network = dict(base)
        network["module"] = "demo.network_export_denied"
        network["operations"] = list(base["operations"]) + [{"id": "op.network", "op": "http.call", "effects": ["effect.external.network.call"], "capabilities": ["cap.http.call"]}]
        p = temp / "network.yaml"
        p.write_text(yaml.safe_dump(network, sort_keys=False, allow_unicode=True), encoding="utf-8")
        add_case("network_export_denied", p, "refused", "trust_gate_not_passed")

        # Contract-level packet fixture: safe internal query. This is a packet
        # shape fixture, not a live AiNIR workflow fixture in the public demo.
        safe_packet = _safe_internal_query_packet()
        errors = validate_verified_intent_packet(safe_packet)
        cases.append({
            "case_id": "safe_internal_query_allowed_packet_shape",
            "expected_status": "packet_valid",
            "actual_status": "packet_valid" if not errors else "packet_invalid",
            "expected_reason": None,
            "actual_reasons": [],
            "packet_validation_errors": errors,
            "passed": not errors,
        })
        (out / "safe_internal_query_allowed.verified_intent_packet.json").write_text(json.dumps(safe_packet, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = {
        "phase": "pre_v1_phase22_verified_intent_export_surface",
        "overall_status": "passed" if all(c["passed"] for c in cases) else "failed",
        "case_count": len(cases),
        "passed": sum(1 for c in cases if c["passed"]),
        "failed": sum(1 for c in cases if not c["passed"]),
        "cases": cases,
    }
    (out / "phase22_verified_intent_eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def _safe_internal_query_packet() -> dict[str, Any]:
    # Backward-compatible Phase 22 packet-shape fixture, updated in Phase 24 to
    # satisfy the stricter PIIExportRequest profile contract. This is not a
    # concrete downstream plan; schema grounding remains a consumer obligation.
    return {
        "kind": "VerifiedIntentPacket",
        "version": "pre_v1_phase25",
        "packet_id": "ainir.verified_intent.fixture.pii_export_shape_phase25",
        "producer": "AiNIR",
        "consumer_profile": "AIVLConsumerProfile",
        "profile_status": "consumer_profile_contract_only_no_downstream_integration",
        "slots": {
            "trust": {"status": "verified", "decision": "allow", "blocked_reasons": [], "trust_gate_status": "passed", "lowering_allowed": True, "handoff_allowed": True},
            "profile_scope": {"profile": "AIVLConsumerProfile", "workflow": "PIIExportRequest", "task": "FixturePIIExport", "task_family": "pii_export_pipeline", "supported_workflow": True},
            "evidence_bindings": [{"claim":"claim.pii_export_authorized", "evidence_id":"evidence.fixture.authz", "issuer":"ainir_evidence_ledger", "status":"verified", "ledger_bound": True}],
            "effects": {
                "consumer_allowed": ["AuthorizationCheck", "Encrypt", "PIIExport", "PIIRead", "WriteExportPackage"],
                "consumer_required": ["PIIExport", "PIIRead"],
                "consumer_denied": ["NetworkAccess", "WriteDatabase", "SecretAccess", "PaymentCharge", "AccountDelete"],
                "ainir_declared": ["effect.auth.authorization.check", "effect.crypto.encrypt", "effect.privacy.pii.read", "effect.storage.export_package.write"],
                "ainir_implied": ["effect.privacy.pii.export"],
            },
            "capabilities": {
                "consumer_allowed": ["AuthorizationCheck", "Encrypt", "PIIExport", "PIIRead", "WriteExportPackage"],
                "consumer_denied": ["NetworkAccess", "WriteDatabase", "SecretAccess", "PaymentCharge", "AccountDelete"],
                "ainir_declared": ["cap.auth.check", "cap.crypto.encrypt", "cap.export.storage.write", "cap.pii.read"],
                "ainir_implied": ["cap.pii.export"],
            },
            "intent": {"task_intent": "prepare_authorized_pii_export_package", "domain": "privacy_export", "operation_kind": "data_pipeline", "natural_language_summary": "Prepare an authorized encrypted PII export package. Concrete data-source grounding must be performed by the future consumer."},
            "grounding_status": {"status":"consumer_must_ground", "reason":"fixture", "required_consumer_checks":["schema_grounding_required", "filter_matches", "projection_matches", "field_allowlist"]},
            "groundings": [],
            "ambiguity": {"status": "resolved", "unresolved_ambiguities": []},
            "operation_constraints": {"allowed_operations": ["authorization_check", "encrypt_export_package", "field_allowlist_check", "read_pii_fields", "store_export_package"], "denied_operations": ["delete", "update", "external_network_send", "production_financial_effect"], "requires_human_review": True, "semantic_roles":["authorization", "encrypted_or_safe_export", "export_allowlist", "export_encryption", "export_package_storage", "pii_read"], "canonical_operations": [
                    {"operation_id":"op.authorize_export","canonical_op":"auth.check_pii_export_authorization","semantic_roles":["authorization"],"effects":["effect.auth.authorization.check"],"capabilities":["cap.auth.check"]},
                    {"operation_id":"op.enforce_field_allowlist","canonical_op":"policy.enforce_export_field_allowlist","semantic_roles":["export_allowlist"],"effects":[],"capabilities":[]},
                    {"operation_id":"op.read_user_pii","canonical_op":"db.read_user_pii_bundle","semantic_roles":["pii_read"],"effects":["effect.privacy.pii.read"],"capabilities":["cap.pii.read"]},
                    {"operation_id":"op.encrypt_export_package","canonical_op":"export.encrypt_pii_export_package","semantic_roles":["encrypted_or_safe_export","export_encryption"],"effects":["effect.crypto.encrypt"],"capabilities":["cap.crypto.encrypt"]},
                    {"operation_id":"op.write_encrypted_package","canonical_op":"storage.write_encrypted_pii_export_package","semantic_roles":["encrypted_or_safe_export","export_package_storage"],"effects":["effect.storage.export_package.write"],"capabilities":["cap.export.storage.write"]}
                ]},
            "required_contracts": ["encrypted_export_package", "field_allowlist", "filter_matches", "pii_export_authorized", "pii_export_boundary_declared", "projection_matches", "schema_grounding_required"],
            "security_classifications": [{"classification_scope":"export_payload", "classification":"PII", "source":"consumer_grounded_export_fields", "status":"consumer_must_ground"}],
            "receipt_links": {"ainir_receipt_id": "ainir.trust.receipt.fixture", "draft_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000", "registry_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111", "verifier_report_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222", "policy_hash": "sha256:3333333333333333333333333333333333333333333333333333333333333333"},
        },
    }
