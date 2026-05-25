from pathlib import Path
import json

from ainir.core import load_draft
from ainir.execution_context import TrustedExecutionContext
from ainir.verified_intent_export import export_verified_intent_packet, verify_verified_intent_packet_handoff_from_files, _canonical_verified_intent_packet_hash
from ainir.trust_receipt_store import replay_trust_receipt, stable_receipt_projection_hash, _sha256_json, _sha256_bytes


def _write_bundle(out: Path) -> Path:
    draft = load_draft("fixtures/aivl_consumer_profile/pii_export_allowed/draft.yaml")
    result = export_verified_intent_packet(draft, TrustedExecutionContext.from_environment("public_demo", source="cli", purpose="verified_intent_export"), "AIVL")
    assert result.status == "exported"
    out.mkdir(parents=True, exist_ok=True)
    packet_path = out / "verified_intent_packet.json"
    receipt_path = out / "verified_intent_trust_receipt.json"
    decision_path = out / "verified_intent_trust_gate_decision.json"
    manifest_path = out / "trust_receipt_manifest.jsonl"
    packet_path.write_text(json.dumps(result.packet, indent=2), encoding="utf-8")
    receipt_path.write_text(json.dumps(result.receipt, indent=2), encoding="utf-8")
    decision_path.write_text(json.dumps(result.decision, indent=2), encoding="utf-8")
    record = {
        "artifact_family": "verified_intent_export_bundle",
        "receipt_id": result.receipt["receipt_id"],
        "stable_receipt_projection_hash": result.receipt["stable_receipt_projection_hash"],
        "registry_snapshot_hash": result.receipt["registry_snapshot_hash"],
        "receipt_raw_file_sha256": _sha256_bytes(receipt_path.read_bytes()),
        "receipt_canonical_sha256": _sha256_json(result.receipt),
        "decision_raw_file_sha256": _sha256_bytes(decision_path.read_bytes()),
        "decision_canonical_sha256": _sha256_json(result.decision),
        "packet_raw_file_sha256": _sha256_bytes(packet_path.read_bytes()),
        "packet_canonical_sha256": _canonical_verified_intent_packet_hash(result.packet),
    }
    manifest_path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return receipt_path


def test_verified_intent_bundle_replay_checks_packet_payload(tmp_path: Path):
    receipt_path = _write_bundle(tmp_path)
    clean = replay_trust_receipt(receipt_path, "fixtures/aivl_consumer_profile/pii_export_allowed/draft.yaml")
    assert clean.overall_status == "passed"
    assert verify_verified_intent_packet_handoff_from_files(tmp_path / "verified_intent_packet.json", receipt_path, "fixtures/aivl_consumer_profile/pii_export_allowed/draft.yaml") == []

    packet_path = tmp_path / "verified_intent_packet.json"
    receipt_path = tmp_path / "verified_intent_trust_receipt.json"
    decision_path = tmp_path / "verified_intent_trust_gate_decision.json"
    manifest_path = tmp_path / "trust_receipt_manifest.jsonl"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["slots"]["intent"]["natural_language_summary"] = "Tampered semantic summary."
    packet_hash = _canonical_verified_intent_packet_hash(packet)
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["verified_intent_packet_canonical_sha256"] = packet_hash
    receipt["stable_receipt_projection_hash"] = stable_receipt_projection_hash(receipt)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["receipt"] = receipt
    decision_path.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    record.update({
        "stable_receipt_projection_hash": receipt["stable_receipt_projection_hash"],
        "receipt_raw_file_sha256": _sha256_bytes(receipt_path.read_bytes()),
        "receipt_canonical_sha256": _sha256_json(receipt),
        "decision_raw_file_sha256": _sha256_bytes(decision_path.read_bytes()),
        "decision_canonical_sha256": _sha256_json(decision),
        "packet_raw_file_sha256": _sha256_bytes(packet_path.read_bytes()),
        "packet_canonical_sha256": packet_hash,
    })
    manifest_path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    tampered = replay_trust_receipt(receipt_path, "fixtures/aivl_consumer_profile/pii_export_allowed/draft.yaml")
    assert tampered.overall_status == "failed"
    failed = {c["check"] for c in tampered.checks if c["status"] == "failed"}
    assert "sibling_verified_intent_packet_hash_matches_fresh_replay" in failed


def test_verified_intent_bundle_replay_requires_packet_sidecars_even_without_decision(tmp_path: Path):
    receipt_path = _write_bundle(tmp_path)
    (tmp_path / "verified_intent_trust_gate_decision.json").unlink()
    (tmp_path / "trust_receipt_manifest.jsonl").unlink()
    report = replay_trust_receipt(receipt_path, "fixtures/aivl_consumer_profile/pii_export_allowed/draft.yaml")
    assert report.overall_status == "failed"
    failed = {c["check"] for c in report.checks if c["status"] == "failed"}
    assert "sibling_decision_present_for_bound_packet" in failed
    assert "bundle_manifest_present" in failed
    assert "sibling_verified_intent_packet_json_valid" not in failed
