"""Compatibility facade over the single-source safety registry.

Older public-demo modules imported helpers from safety_model.py. In the pre-v1
hardening track, the actual source of truth is safety_registry.py plus
registries/safety_registry.yaml. Keep this facade thin to avoid split-brain
policy/alias lists.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .safety_registry import get_registry, strict_safe_id


def normalize_workflow_name(workflow: str) -> tuple[str, bool]:
    return get_registry().normalize_workflow(workflow)


def normalize_effect_name(effect: str) -> str:
    return get_registry().normalize_effect(effect)[0]


def safe_id(value: Any) -> bool:
    return strict_safe_id(value)


def evidence_is_checked_external(ev: Mapping[str, Any], module_id: str = "", workflow: str = "") -> bool:
    return get_registry().evidence_decision(ev, module_id, workflow).checked


def is_raw_token_effect(effect: str) -> bool:
    return "raw_token" in get_registry().classify_effect(effect)


def is_raw_pii_effect(effect: str) -> bool:
    return "raw_pii" in get_registry().classify_effect(effect)


def is_real_payment_effect(effect: str) -> bool:
    families = get_registry().classify_effect(effect)
    return "payment_real" in families


def is_payment_charge_effect(effect: str) -> bool:
    return "payment_charge" in get_registry().classify_effect(effect)


def is_sandbox_or_mock_payment_effect(effect: str) -> bool:
    families = get_registry().classify_effect(effect)
    return "payment_charge" in families and "payment_real" not in families


def is_real_email_effect(effect: str) -> bool:
    return "notification_real" in get_registry().classify_effect(effect)


def is_hard_delete_effect(effect: str) -> bool:
    return "destructive_delete" in get_registry().classify_effect(effect)


def looks_real_effect(effect: str) -> bool:
    return bool(get_registry().classify_effect(effect) & {"payment_real", "notification_real"})


def is_unallowlisted_external_effect(effect: str) -> bool:
    return "external_unallowlisted" in get_registry().classify_effect(effect)


def is_safety_critical_external_op(op: str) -> bool:
    return "external_network" in get_registry().classify_operation(op)


def is_destructive_op(op: str) -> bool:
    return "destructive_delete" in get_registry().classify_operation(op)


def operation_implies_payment(op: str) -> bool:
    return "payment" in get_registry().classify_operation(op)


def operation_implies_raw_token(op: str) -> bool:
    return "raw_token" in get_registry().classify_operation(op)


def operation_implies_raw_pii(op: str) -> bool:
    return "raw_pii" in get_registry().classify_operation(op)


# Registry-backed constants for legacy imports.
REGISTRY = get_registry()
CANONICAL_WORKFLOWS = REGISTRY.canonical_workflows
WORKFLOW_ALIASES = REGISTRY.workflow_aliases
EFFECT_ALIASES = REGISTRY.effect_aliases
ALLOWLISTED_EXTERNAL_EFFECTS = REGISTRY.allowed_external_effects
IDEMPOTENCY_POLICY_HINTS = set(REGISTRY.data.get("role_markers", {}).get("idempotency", {}).get("policy_any", []))
TS_RESERVED_WORDS = REGISTRY.ts_reserved_words
