from __future__ import annotations

from copy import deepcopy

from ainir.core import DraftModule, load_draft
from ainir.evidence_ledger import get_evidence_ledger
from ainir.verifier import verify_draft


def _safe_raw() -> dict:
    return load_draft("examples/create_user_outbox_safe/draft.yaml").raw


def _rules(raw: dict) -> set[str]:
    return {f.rule for f in verify_draft(DraftModule(raw=raw)).findings}


def test_safe_verified_claim_uses_ledger_bound_evidence():
    report = verify_draft(load_draft("examples/create_user_outbox_safe/draft.yaml"))
    assert report.status == "passed"
    assert "TR001.verified_claim_requires_ledger_bound_evidence" not in {f.rule for f in report.findings}


def test_draft_self_attested_checked_evidence_is_rejected():
    raw = _safe_raw()
    raw["claims"][0]["evidence"][0]["checked"] = True
    raw["claims"][0]["evidence"][0]["reliability"] = 0.99
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert "TR001.verified_claim_requires_ledger_bound_evidence" in _rules(raw)


def test_ledger_evidence_cannot_be_reused_for_fake_claim_id():
    raw = _safe_raw()
    raw["claims"][0]["id"] = "claim.fake"
    raw["claims"][0]["statement"] = "A different claim tries to reuse the safe outbox evidence."
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert "TR001.verified_claim_requires_ledger_bound_evidence" in _rules(raw)


def test_ledger_evidence_cannot_be_reused_for_changed_statement():
    raw = _safe_raw()
    raw["claims"][0]["statement"] = "CreateUser uses outbox and also secretly does something else."
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert "TR001.verified_claim_requires_ledger_bound_evidence" in _rules(raw)


def test_ledger_evidence_cannot_be_reused_for_other_module():
    raw = _safe_raw()
    raw["module"] = "demo.other_module"
    report = verify_draft(DraftModule(raw=raw))
    assert report.status == "blocked"
    assert "TR001.verified_claim_requires_ledger_bound_evidence" in _rules(raw)


def test_evidence_ledger_record_exists_for_safe_outbox():
    ledger = get_evidence_ledger()
    record = ledger.records.get("evidence.demo.safe_outbox")
    assert record is not None
    assert record["supports_claims"] == ["claim.create_user_uses_outbox"]
    assert record["status"] == "checked"
