"""Registry-bound evidence ledger for AiNIR public demo.

Pre-v1 Phase 3: model/provider drafts are not allowed to self-attest evidence
with fields such as ``checked: true`` or ``source: claude``. A verified claim is
accepted only when its evidence id resolves to a bundled ledger record whose
scope, producer, reliability, artifact, and optional claim statement hash match.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

import yaml

from .safety_registry import get_registry
from .core import DraftModule

_SELF_ATTEST_FIELDS = {
    "checked",
    "status",
    "reliability",
    "source",
    "source_ref",
    "producer",
    "producer_kind",
    "generated_by",
    "checked_by",
    "report_ref",
    "artifact_ref",
    "supports",
    "supports_claims",
    "claim_statement_sha256",
}


@dataclass(frozen=True)
class LedgerDecision:
    checked: bool
    reason: str
    evidence_id: str | None = None


class EvidenceLedger:
    def __init__(self, data: Mapping[str, Any], root: Path | None = None):
        self.data = dict(data or {})
        self.root = root
        self.records = {}
        for rec in self.data.get("records", []) or []:
            if isinstance(rec, Mapping) and isinstance(rec.get("id"), str):
                self.records[str(rec["id"])] = dict(rec)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "EvidenceLedger":
        if path is not None:
            p = Path(path)
            with p.open("r", encoding="utf-8") as f:
                return cls(yaml.safe_load(f) or {}, p.parent.parent if p.parent.name == "registries" else p.parent)

        # Prefer the repository-root ledger so artifact hashes can be checked
        # against files in examples/. Packaged resources are a fallback for
        # installed/demo mode, where artifact verification may be unavailable.
        here = Path(__file__).resolve()
        for candidate in (
            here.parents[2] / "registries" / "evidence_ledger.yaml",
            Path.cwd() / "registries" / "evidence_ledger.yaml",
        ):
            if candidate.exists():
                with candidate.open("r", encoding="utf-8") as f:
                    return cls(yaml.safe_load(f) or {}, candidate.parent.parent)

        try:
            content = resources.files("ainir.registries").joinpath("evidence_ledger.yaml").read_text(encoding="utf-8")
            return cls(yaml.safe_load(content) or {}, None)
        except Exception:
            pass

        return cls({"records": []}, None)

    def decide(self, ev: Mapping[str, Any], claim: Mapping[str, Any], module_id: str, workflow: str, draft: DraftModule | None = None) -> LedgerDecision:
        eid = ev.get("id")
        if not isinstance(eid, str) or not eid.strip():
            return LedgerDecision(False, "evidence id is missing")

        forbidden = sorted(k for k in ev.keys() if k in _SELF_ATTEST_FIELDS)
        # id/kind is a reference. The rest of evidence facts must come from the ledger.
        forbidden = [k for k in forbidden if k not in {"id", "kind"}]
        if forbidden:
            return LedgerDecision(False, "draft evidence contains self-attested fields: " + ", ".join(forbidden), eid)

        rec = self.records.get(eid)
        if rec is None:
            return LedgerDecision(False, "evidence id is not present in the evidence ledger", eid)

        kind = ev.get("kind")
        if kind is not None and kind != rec.get("kind"):
            return LedgerDecision(False, "evidence kind does not match ledger record", eid)

        registry = get_registry()
        if rec.get("kind") not in set(registry.trusted_evidence.get("allowed_kinds", [])):
            return LedgerDecision(False, "ledger evidence kind is not allowed", eid)
        if rec.get("status") != "checked":
            return LedgerDecision(False, "ledger evidence is not checked", eid)
        producer_kind = rec.get("producer_kind")
        if producer_kind not in set(registry.trusted_evidence.get("trusted_producers", [])):
            return LedgerDecision(False, "ledger evidence producer is not trusted", eid)
        try:
            reliability = float(rec.get("reliability", 0))
        except Exception:
            reliability = 0.0
        if reliability < float(rec.get("min_reliability", 0.8)):
            return LedgerDecision(False, "ledger evidence reliability is below threshold", eid)

        if rec.get("supports_module") and rec.get("supports_module") != module_id:
            return LedgerDecision(False, "ledger evidence does not support this module", eid)
        if rec.get("supports_workflow") and rec.get("supports_workflow") != workflow:
            return LedgerDecision(False, "ledger evidence does not support this workflow", eid)

        claim_id = claim.get("id")
        supported_claims = rec.get("supports_claims") or []
        if supported_claims and claim_id not in supported_claims:
            return LedgerDecision(False, "ledger evidence does not support this claim id", eid)

        expected_statement_hash = rec.get("claim_statement_sha256")
        if expected_statement_hash:
            statement = str(claim.get("statement", ""))
            observed = sha256(statement.encode("utf-8")).hexdigest()
            if observed != expected_statement_hash:
                return LedgerDecision(False, "claim statement hash does not match the ledger-bound statement", eid)

        artifact_ref = rec.get("artifact_ref")
        artifact_sha = rec.get("artifact_sha256")
        if artifact_ref and artifact_sha:
            if self.root is not None:
                artifact = (self.root / str(artifact_ref)).resolve()
                try:
                    root = self.root.resolve()
                    artifact.relative_to(root)
                except Exception:
                    return LedgerDecision(False, "ledger artifact_ref escapes repository root", eid)
                if not artifact.exists():
                    return LedgerDecision(False, "ledger artifact_ref does not exist", eid)
                observed_sha = sha256(artifact.read_bytes()).hexdigest()
                if observed_sha != artifact_sha:
                    return LedgerDecision(False, "ledger artifact hash mismatch", eid)
            if draft is None or not isinstance(draft.raw.get("__source_path__"), str):
                return LedgerDecision(False, "current draft source path is unavailable for artifact binding", eid)
            current_path = Path(str(draft.raw["__source_path__"]))
            if not current_path.exists():
                return LedgerDecision(False, "current draft source path does not exist", eid)
            current_sha = sha256(current_path.read_bytes()).hexdigest()
            if current_sha != artifact_sha:
                return LedgerDecision(False, "ledger evidence is not bound to the current draft artifact", eid)

        return LedgerDecision(True, "evidence is ledger-bound and checked for the current draft", eid)


@lru_cache(maxsize=1)
def get_evidence_ledger() -> EvidenceLedger:
    return EvidenceLedger.load()


def claim_statement_sha256(statement: str) -> str:
    return sha256(str(statement).encode("utf-8")).hexdigest()
