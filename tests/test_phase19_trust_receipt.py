from __future__ import annotations

import json
import pytest
from pathlib import Path

from ainir.execution_context import TrustedExecutionContext
from ainir.phase19_trust_receipt_eval import run_phase19_trust_receipt_eval
from ainir.trust_receipt_store import issue_trust_receipt, replay_trust_receipt


def test_safe_receipt_issue_and_replay(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)
    assert replay.overall_status == "passed"
    assert issued.receipt["status"] == "passed"


def test_tampered_receipt_fails_replay(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    receipt = dict(issued.receipt)
    receipt["safety_registry_hash"] = "sha256:tampered"
    tampered = tmp_path / "tampered.receipt.json"
    tampered.write_text(json.dumps(receipt), encoding="utf-8")
    replay = replay_trust_receipt(tampered, "examples/create_user_outbox_safe/draft.yaml", ctx)
    assert replay.overall_status == "failed"
    assert any(c["check"] == "safety_registry_hash" and c["status"] == "failed" for c in replay.checks)


def test_receipt_replay_fails_with_wrong_context(tmp_path: Path) -> None:
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, TrustedExecutionContext.public_demo())
    wrong = TrustedExecutionContext.from_environment("test", source="test", purpose="wrong_context")
    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", wrong)
    assert replay.overall_status == "failed"
    assert any(c["check"] == "trusted_environment" for c in replay.checks)


def test_phase19_eval_passes(tmp_path: Path) -> None:
    summary = run_phase19_trust_receipt_eval(tmp_path / "eval")
    assert summary["overall_status"] == "passed"
    assert summary["passed"] == summary["case_count"]


def test_receipt_replay_rejects_malformed_manifest_jsonl_line(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    manifest = Path(issued.manifest_path)
    manifest.write_text(manifest.read_text(encoding="utf-8") + "{bad json}\n", encoding="utf-8")

    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)

    assert replay.overall_status == "failed"
    failed = [c for c in replay.checks if c["check"] == "bundle_manifest_jsonl_valid"]
    assert failed and failed[0]["status"] == "failed"
    assert any(err.get("reason") == "json_decode_error" for err in failed[0]["actual"])


def test_receipt_replay_rejects_duplicate_key_manifest_jsonl_line(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    manifest = Path(issued.manifest_path)
    manifest.write_text(manifest.read_text(encoding="utf-8") + '{"receipt_id":"shadow","receipt_id":"shadow2"}\n', encoding="utf-8")

    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)

    assert replay.overall_status == "failed"
    failed = [c for c in replay.checks if c["check"] == "bundle_manifest_jsonl_valid"]
    assert failed and failed[0]["status"] == "failed"
    assert any(err.get("reason") == "json_duplicate_key" for err in failed[0]["actual"])



def test_receipt_replay_rejects_conflicting_same_receipt_id_manifest_record(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    manifest = Path(issued.manifest_path)
    records = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    conflict = dict(records[-1])
    conflict["receipt_raw_file_sha256"] = "sha256:" + "0" * 64
    conflict["receipt_canonical_sha256"] = "sha256:" + "1" * 64
    conflict["manifest_record_status"] = "active"
    manifest.write_text(manifest.read_text(encoding="utf-8") + json.dumps(conflict, sort_keys=True) + "\n", encoding="utf-8")

    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)

    assert replay.overall_status == "failed"
    failed = [c for c in replay.checks if c["check"] == "bundle_manifest_receipt_id_unique_or_consistent"]
    assert failed and failed[0]["status"] == "failed"


def test_receipt_replay_rejects_incomplete_active_same_receipt_manifest_record(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    manifest = Path(issued.manifest_path)
    incomplete = {"receipt_id": issued.receipt["receipt_id"], "manifest_record_status": "active"}
    manifest.write_text(manifest.read_text(encoding="utf-8") + json.dumps(incomplete, sort_keys=True) + "\n", encoding="utf-8")

    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)

    assert replay.overall_status == "failed"
    failed = [c for c in replay.checks if c["check"] == "bundle_manifest_active_record_required_fields_present"]
    assert failed and failed[0]["status"] == "failed"


def test_receipt_replay_requires_active_matching_manifest_record(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    manifest = Path(issued.manifest_path)
    records = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    for rec in records:
        if rec.get("receipt_id") == issued.receipt["receipt_id"]:
            rec["manifest_record_status"] = "superseded"
    manifest.write_text("\n".join(json.dumps(rec, sort_keys=True) for rec in records) + "\n", encoding="utf-8")

    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)

    assert replay.overall_status == "failed"
    failed = [c for c in replay.checks if c["check"] == "bundle_manifest_active_matching_record_present"]
    assert failed and failed[0]["status"] == "failed"
    missing = [c for c in replay.checks if c["check"] == "bundle_manifest_matching_record_present"]
    assert missing and missing[0]["status"] == "failed"


def test_receipt_replay_rejects_unknown_manifest_record_status(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    manifest = Path(issued.manifest_path)
    records = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    records[-1]["manifest_record_status"] = "revoked"
    manifest.write_text("\n".join(json.dumps(rec, sort_keys=True) for rec in records) + "\n", encoding="utf-8")

    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)

    assert replay.overall_status == "failed"
    failed = [c for c in replay.checks if c["check"] == "bundle_manifest_record_status_valid"]
    assert failed and failed[0]["status"] == "failed"


def test_receipt_replay_rejects_unrelated_incomplete_active_manifest_record(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    manifest = Path(issued.manifest_path)
    unrelated = {"receipt_id": "ainir.trust.receipt.unrelated", "manifest_record_status": "active"}
    manifest.write_text(manifest.read_text(encoding="utf-8") + json.dumps(unrelated, sort_keys=True) + "\n", encoding="utf-8")

    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)

    assert replay.overall_status == "failed"
    failed = [c for c in replay.checks if c["check"] == "bundle_manifest_all_active_records_required_fields_present"]
    assert failed and failed[0]["status"] == "failed"


def test_receipt_replay_rejects_unrelated_unknown_manifest_record_status(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    issued = issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
    manifest = Path(issued.manifest_path)
    unrelated = {
        "receipt_id": "ainir.trust.receipt.unrelated",
        "manifest_record_status": "revoked",
        "receipt_raw_file_sha256": "sha256:" + "0" * 64,
        "receipt_canonical_sha256": "sha256:" + "1" * 64,
        "stable_receipt_projection_hash": "sha256:" + "2" * 64,
        "registry_snapshot_hash": "sha256:" + "3" * 64,
    }
    manifest.write_text(manifest.read_text(encoding="utf-8") + json.dumps(unrelated, sort_keys=True) + "\n", encoding="utf-8")

    replay = replay_trust_receipt(issued.receipt_path, "examples/create_user_outbox_safe/draft.yaml", ctx)

    assert replay.overall_status == "failed"
    failed = [c for c in replay.checks if c["check"] == "bundle_manifest_all_record_statuses_valid"]
    assert failed and failed[0]["status"] == "failed"


def test_receipt_issue_refuses_to_append_to_defective_manifest(tmp_path: Path) -> None:
    ctx = TrustedExecutionContext.public_demo()
    manifest = tmp_path / "trust_receipt_manifest.jsonl"
    manifest.write_text("{bad json}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to append to defective trust receipt manifest"):
        issue_trust_receipt("examples/create_user_outbox_safe/draft.yaml", tmp_path, ctx)
