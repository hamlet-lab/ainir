from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import tempfile

import yaml

from .temp_paths import ainir_temp_str

from .core import DraftModule, dump_yaml, load_draft, load_yaml_no_duplicate_keys
from .execution_context import TrustedExecutionContext
from .lowering import lower_to_typescript
from .verifier import verify_draft


@dataclass(frozen=True)
class NegativeConformanceResult:
    case_id: str
    expected_status: str
    actual_status: str
    passed: bool
    critical_count: int
    lowering_refused: bool | None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "expected_status": self.expected_status,
            "actual_status": self.actual_status,
            "passed": self.passed,
            "critical_count": self.critical_count,
            "lowering_refused": self.lowering_refused,
            "notes": self.notes,
        }


def run_negative_conformance_corpus(
    corpus_path: str | Path = "negative_conformance_corpus.yaml",
    out_dir: str | Path = ainir_temp_str("ainir_negative_conformance"),
    environment: str = "public_demo",
) -> dict[str, Any]:
    corpus_path = Path(corpus_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus = _load_yaml(corpus_path)
    context = TrustedExecutionContext.from_environment(environment, source="negative_conformance_harness", purpose="conformance_eval")
    results: list[NegativeConformanceResult] = []

    for case in corpus.get("cases", []):
        results.append(_run_case(case, corpus_path.parent, out_dir, context))

    for robustness_case in _generate_deterministic_robustness_cases(corpus.get("deterministic_robustness_profiles", [])):
        results.append(_run_case(robustness_case, corpus_path.parent, out_dir, context))

    summary = {
        "overall_status": "passed" if all(r.passed for r in results) else "failed",
        "corpus": str(corpus_path),
        "trusted_context": {"environment": context.environment, "source": context.source, "purpose": context.purpose},
        "case_count": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "results": [r.as_dict() for r in results],
    }
    dump_yaml(summary, out_dir / "negative_conformance_report.yaml")
    return summary


def _run_case(case: dict[str, Any], root: Path, out_dir: Path, context: TrustedExecutionContext) -> NegativeConformanceResult:
    cid = str(case.get("id", "unnamed_case"))
    expected = str(case.get("expected_status", "blocked"))
    expect_lowering_refused = bool(case.get("expect_lowering_refused", expected != "passed"))
    draft = _draft_from_case(case, root)
    report = verify_draft(draft, context)
    dump_yaml(report.as_dict(), out_dir / f"{_safe_file(cid)}.verify.yaml")

    lowering_refused: bool | None = None
    if report.status == "passed":
        try:
            lower_to_typescript(draft, report, out_dir / "lowered", context)
            lowering_refused = False
        except Exception:
            lowering_refused = True
    else:
        try:
            lower_to_typescript(draft, report, out_dir / "lowered", context)
            lowering_refused = False
        except Exception:
            lowering_refused = True

    status_ok = report.status == expected
    lowering_ok = (lowering_refused is True) if expect_lowering_refused else (lowering_refused is False)
    notes = ""
    if not status_ok:
        notes += f"expected status {expected!r}, got {report.status!r}. "
    if not lowering_ok:
        notes += f"lowering_refused={lowering_refused}, expected_refused={expect_lowering_refused}."
    return NegativeConformanceResult(cid, expected, report.status, status_ok and lowering_ok, report.critical_count, lowering_refused, notes.strip())


def _draft_from_case(case: dict[str, Any], root: Path) -> DraftModule:
    if "draft_ref" in case:
        return load_draft(root / str(case["draft_ref"]))
    if "raw_yaml" in case:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(str(case["raw_yaml"]))
            path = Path(f.name)
        return load_draft(path)
    return DraftModule(raw=case.get("draft") or {})


def _generate_deterministic_robustness_cases(profiles: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for profile in profiles:
        pid = str(profile.get("id", "robustness_profile"))
        expected = str(profile.get("expected_status", "blocked"))
        if pid == "safety_critical_effect_suffix_variants":
            stems = profile.get("effect_stems", []) or []
            suffixes = profile.get("suffixes", []) or []
            for i, stem in enumerate(stems):
                for j, suffix in enumerate(suffixes):
                    effect = f"{stem}{suffix}"
                    yield {
                        "id": f"{pid}_{i}_{j}",
                        "expected_status": expected,
                        "expect_lowering_refused": True,
                        "draft": _minimal_order_payment(effect),
                    }
        elif pid == "provider_source_evidence_variants":
            for i, source in enumerate(profile.get("sources", []) or []):
                yield {
                    "id": f"{pid}_{i}_{source}",
                    "expected_status": expected,
                    "expect_lowering_refused": True,
                    "draft": _unbound_evidence_draft(str(source)),
                }
        elif pid == "hidden_operation_effectless_variants":
            for i, op in enumerate(profile.get("operations", []) or []):
                yield {
                    "id": f"{pid}_{i}_{_safe_file(str(op))}",
                    "expected_status": expected,
                    "expect_lowering_refused": True,
                    "draft": _hidden_op_draft(str(op)),
                }


def _minimal_order_payment(effect: str) -> dict[str, Any]:
    return {
        "module": "demo.negative_conformance",
        "workflow": "OrderPayment",
        "task": "ProcessOrderPaymentWorker",
        "operations": [
            {"id": "op.amount", "op": "payment.validate_amount", "effects": [], "capabilities": []},
            {"id": "op.intent", "op": "payment.create_intent", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"]},
            {"id": "op.robustness", "op": "payment.charge.sandbox", "effects": [effect], "capabilities": ["cap.payment.charge.sandbox"]},
        ],
    }


def _unbound_evidence_draft(source: str) -> dict[str, Any]:
    return {
        "module": "demo.negative_conformance",
        "workflow": "CreateUser",
        "task": "CreateUserRequest",
        "operations": [
            {"id": "op.db", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"]},
            {"id": "op.out", "op": "outbox.insert_welcome_email", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
        ],
        "claims": [{"id": "claim.unbound", "status": "verified", "evidence": [{"id": f"ev.{source}", "kind": "verifier_report", "checked": True, "source": source, "reliability": 0.99}]}],
    }


def _hidden_op_draft(op: str) -> dict[str, Any]:
    workflow = "OrderPayment" if "payment" in op else "CreateUser"
    return {
        "module": "demo.negative_conformance",
        "workflow": workflow,
        "task": "ProcessOrderPaymentWorker" if workflow == "OrderPayment" else "CreateUserRequest",
        "operations": [
            {"id": "op.db", "op": "db.insert_user", "effects": ["effect.storage.db.write"], "capabilities": ["cap.db.write"]},
            {"id": "op.out", "op": "outbox.insert_welcome_email", "effects": ["effect.storage.outbox.write"], "capabilities": ["cap.outbox.write"]},
            {"id": "op.hidden", "op": op, "effects": [], "capabilities": []},
        ],
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = load_yaml_no_duplicate_keys(f.read()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"negative conformance corpus root must be an object: {path}")
    return data


def _safe_file(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)[:120]
