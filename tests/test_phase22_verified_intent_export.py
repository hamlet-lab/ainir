from pathlib import Path

from ainir.core import load_draft
from ainir.execution_context import TrustedExecutionContext
from ainir.verified_intent_export import export_verified_intent_packet, validate_verified_intent_packet
from ainir.phase22_verified_intent_eval import run_phase22_verified_intent_eval


def test_pii_export_verified_intent_packet_exports():
    draft = load_draft("fixtures/aivl_consumer_profile/pii_export_allowed/draft.yaml")
    result = export_verified_intent_packet(draft, TrustedExecutionContext.public_demo(), "AIVL")
    assert result.status == "exported"
    assert result.packet is not None
    assert validate_verified_intent_packet(result.packet) == []
    slots = result.packet["slots"]
    assert slots["trust"]["status"] == "verified"
    assert "pii_export_authorized" in slots["required_contracts"]
    assert "PIIExport" in slots["effects"]["consumer_allowed"]
    assert "PIIExport" in slots["capabilities"]["consumer_allowed"]
    assert slots["groundings"] == []
    assert slots["grounding_status"]["status"] == "consumer_must_ground"
    assert any(c.get("classification") == "PII" and c.get("classification_scope") == "export_payload" for c in slots["security_classifications"])
    assert slots["receipt_links"]["ainir_receipt_id"].startswith("ainir.trust.receipt.")


def test_phase22_eval_passes(tmp_path: Path):
    summary = run_phase22_verified_intent_eval(tmp_path)
    assert summary["overall_status"] == "passed"
    assert summary["case_count"] == 5
