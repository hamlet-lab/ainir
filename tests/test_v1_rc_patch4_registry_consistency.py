from __future__ import annotations

from pathlib import Path

from ainir.core import DraftModule, load_draft
from ainir.normalizer import normalize_draft
from ainir.safety_registry import get_registry
from ainir.trust_gate import _gate_for_rule, evaluate_trust_gate
from ainir.execution_context import TrustedExecutionContext
from ainir.verified_intent_export import export_verified_intent_packet

ROOT = Path(__file__).resolve().parents[1]


def test_effect_family_matching_uses_token_boundaries_not_substrings():
    reg = get_registry()
    assert "db_delete" not in reg.classify_effect("effect.debug.delete")
    assert "db_delete" in reg.classify_effect("effect.db.delete.User")


def test_operation_destructive_delete_requires_registry_pattern_not_inline_delete_keyword():
    reg = get_registry()
    assert "destructive_delete" not in reg.classify_operation("cache.delete")
    assert "destructive_delete" in reg.classify_operation("account.delete.permanent")


def test_raw_token_family_does_not_treat_outbox_as_persistence_action():
    reg = get_registry()
    assert "raw_token" not in reg.classify_effect("effect.secret.raw_token.outbox")
    assert "raw_token" in reg.classify_effect("effect.secret.raw_token.store")


def test_trust_gate_rule_prefix_mapping_is_explicit_for_tr_and_tx():
    assert _gate_for_rule("TR001.verified_claim_requires_ledger_bound_evidence") == "evidence_ledger_binding"
    assert _gate_for_rule("TX001.transaction_includes_unknown_operation") == "transaction_binding"
    assert _gate_for_rule("T001.some_trust_rule") == "trust_gate"


def test_normalizer_safety_critical_alias_has_direct_unit_coverage():
    draft = DraftModule(raw={
        "module": "demo.alias_visibility",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "operations": [
            {"id": "op.finalize", "op": "payment.finalize.production", "effects": ["payment.finalize.production"], "capabilities": ["cap.payment.charge.real"]}
        ],
    })
    _normalized, findings = normalize_draft(draft)
    rules = {f.rule for f in findings}
    assert "N001.effect_alias_normalized" in rules
    assert "N003.safety_critical_effect_alias_visible" in rules


def test_verified_intent_policy_hash_is_distinct_from_registry_hash():
    draft = load_draft(ROOT / "fixtures" / "aivl_consumer_profile" / "pii_export_allowed" / "draft.yaml")
    result = export_verified_intent_packet(draft, TrustedExecutionContext.public_demo()).as_dict()
    assert result["status"] == "exported"
    links = result["packet"]["slots"]["receipt_links"]
    assert links["policy_hash"] != links["registry_hash"]


def test_packaged_registry_copies_are_byte_identical():
    root = ROOT / "registries"
    packaged = ROOT / "src" / "ainir" / "registries"
    for name in [
        "safety_registry.yaml",
        "operation_spec_registry.yaml",
        "evidence_ledger.yaml",
        "external_consumer_profiles.yaml",
    ]:
        assert (root / name).read_bytes() == (packaged / name).read_bytes(), name
