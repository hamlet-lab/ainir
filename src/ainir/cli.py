from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .temp_paths import ainir_temp_str

from .core import dump_yaml, iter_example_drafts, load_draft
from .execution_context import TrustedExecutionContext, allowed_environments
from .lowering import lower_to_typescript
from .verifier import verify_draft
from .trust_gate import evaluate_trust_gate
from .trust_receipt_store import issue_trust_receipt, replay_trust_receipt
from .negative_conformance_harness import run_negative_conformance_corpus

from .golden_trace_harness import run_golden_traces


def _sha256_bytes(data: bytes) -> str:
    from hashlib import sha256
    return "sha256:" + sha256(data).hexdigest()


def _write_trust_gate_bundle(out: Path, decision: dict[str, Any]) -> None:
    """Persist trust-gate decision/receipt with a manifest so replay can audit siblings."""
    out.mkdir(parents=True, exist_ok=True)
    decision_path = out / "trust_gate_decision.json"
    receipt_path = out / "trust_receipt.json"
    manifest_path = out / "trust_receipt_manifest.jsonl"
    decision_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
    receipt = dict(decision.get("receipt", {})) if isinstance(decision.get("receipt"), dict) else {}
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    from .trust_receipt_store import _sha256_json  # local helper; public API intentionally unchanged
    record = {
        "receipt_id": receipt.get("receipt_id"),
        "manifest_record_status": "active",
        "artifact_family": "trust_gate_out_dir_bundle",
        "trust_status": decision.get("status"),
        "stable_receipt_projection_hash": receipt.get("stable_receipt_projection_hash"),
        "registry_snapshot_hash": receipt.get("registry_snapshot_hash"),
        "module_id": decision.get("module_id"),
        "workflow": decision.get("workflow"),
        "receipt_raw_file_sha256": _sha256_bytes(receipt_path.read_bytes()),
        "receipt_canonical_sha256": _sha256_json(receipt),
        "decision_raw_file_sha256": _sha256_bytes(decision_path.read_bytes()),
        "decision_canonical_sha256": _sha256_json(decision),
        "receipt_path": str(receipt_path),
        "decision_path": str(decision_path),
    }
    manifest_path.write_text(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_verified_intent_bundle(out: Path, result: dict[str, Any]) -> None:
    """Persist a VerifiedIntentPacket with the exact TrustReceipt it references."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "verified_intent_export_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    packet = result.get("packet")
    receipt = result.get("receipt")
    decision = result.get("decision")
    if isinstance(packet, dict):
        (out / "verified_intent_packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
    if isinstance(receipt, dict):
        (out / "verified_intent_trust_receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    if isinstance(decision, dict):
        (out / "verified_intent_trust_gate_decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8")
    if isinstance(receipt, dict) and isinstance(decision, dict):
        from .trust_receipt_store import _sha256_json
        receipt_path = out / "verified_intent_trust_receipt.json"
        decision_path = out / "verified_intent_trust_gate_decision.json"
        packet_path = out / "verified_intent_packet.json"
        record = {
            "artifact_family": "verified_intent_export_bundle",
            "manifest_record_status": "active",
            "receipt_id": receipt.get("receipt_id"),
            "trust_status": decision.get("status"),
            "stable_receipt_projection_hash": receipt.get("stable_receipt_projection_hash"),
            "registry_snapshot_hash": receipt.get("registry_snapshot_hash"),
            "module_id": decision.get("module_id"),
            "workflow": decision.get("workflow"),
            "receipt_raw_file_sha256": _sha256_bytes(receipt_path.read_bytes()),
            "receipt_canonical_sha256": _sha256_json(receipt),
            "decision_raw_file_sha256": _sha256_bytes(decision_path.read_bytes()),
            "decision_canonical_sha256": _sha256_json(decision),
            "packet_raw_file_sha256": _sha256_bytes(packet_path.read_bytes()) if packet_path.exists() else None,
            "packet_canonical_sha256": __import__("ainir.verified_intent_export", fromlist=["_canonical_verified_intent_packet_hash"])._canonical_verified_intent_packet_hash(packet) if isinstance(packet, dict) else None,
            "receipt_path": str(receipt_path),
            "decision_path": str(decision_path),
            "packet_path": str(packet_path) if packet_path.exists() else None,
        }
        (out / "trust_receipt_manifest.jsonl").write_text(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ainir", description="AiNIR public demo CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_verify = sub.add_parser("verify", help="verify a draft YAML file")
    p_verify.add_argument("draft")
    p_verify.add_argument("--json", action="store_true")
    p_verify.add_argument("--env", choices=list(allowed_environments()), default="public_demo", help="trusted runtime environment; draft.environment is ignored")

    p_trust = sub.add_parser("trust-gate", help="run the unified AiNIR Trust Gate decision surface")
    p_trust.add_argument("draft")
    p_trust.add_argument("--json", action="store_true")
    p_trust.add_argument("--out-dir", default=None, help="optional output directory for decision.json and trust_receipt.json")
    p_trust.add_argument("--env", choices=list(allowed_environments()), default="public_demo", help="trusted runtime environment; draft.environment is ignored")

    p_lower = sub.add_parser("lower", help="verify then lower a safe draft into TypeScript skeleton")
    p_lower.add_argument("draft")
    p_lower.add_argument("--out-dir", default="out")
    p_lower.add_argument("--env", choices=list(allowed_environments()), default="public_demo", help="trusted runtime environment; draft.environment is ignored")

    p_demo = sub.add_parser("demo", help="run all public demo examples")
    p_demo.add_argument("--examples-dir", default="examples")
    p_demo.add_argument("--out-dir", default=ainir_temp_str("ainir_demo_results"))
    p_demo.add_argument("--env", choices=list(allowed_environments()), default="public_demo", help="trusted runtime environment; draft.environment is ignored")


    p_gold = sub.add_parser("golden-trace-eval", help="run fixed Pre-v1 conformance golden traces")
    p_gold.add_argument("--traces", default="golden_traces.yaml")
    p_gold.add_argument("--out-dir", default=ainir_temp_str("ainir_golden_traces"))
    p_gold.add_argument("--env", choices=list(allowed_environments()), default="public_demo", help="trusted runtime environment; draft.environment is ignored")
    p_neg = sub.add_parser("negative-conformance-eval", help="run defensive negative conformance fixtures")
    p_neg.add_argument("--corpus", default="negative_conformance_corpus.yaml")
    p_neg.add_argument("--out-dir", default=ainir_temp_str("ainir_negative_conformance"))
    p_neg.add_argument("--env", choices=list(allowed_environments()), default="public_demo", help="trusted runtime environment; draft.environment is ignored")

    p_receipt_issue = sub.add_parser("trust-receipt-issue", help="run Trust Gate and persist decision/receipt artifacts")
    p_receipt_issue.add_argument("draft")
    p_receipt_issue.add_argument("--out-dir", default="trust_receipts")
    p_receipt_issue.add_argument("--json", action="store_true")
    p_receipt_issue.add_argument("--env", choices=list(allowed_environments()), default="public_demo", help="trusted runtime environment; draft.environment is ignored")

    p_receipt_replay = sub.add_parser("trust-receipt-replay", help="replay a persisted TrustReceipt against the current draft and registry")
    p_receipt_replay.add_argument("receipt")
    p_receipt_replay.add_argument("--draft", default=None, help="draft path override; defaults to receipt.draft_source_path")
    p_receipt_replay.add_argument("--out-dir", default=None)
    p_receipt_replay.add_argument("--json", action="store_true")
    p_receipt_replay.add_argument("--env", choices=list(allowed_environments()), default=None, help="override trusted environment; defaults to receipt.trusted_context.environment")

    p_phase18 = sub.add_parser("phase18-trust-gate-eval", help="run Phase 18 Trust Gate conformance checks")
    p_phase18.add_argument("--out-dir", default=ainir_temp_str("ainir_phase18_trust_gate"))

    p_phase19 = sub.add_parser("phase19-trust-receipt-eval", help="run Phase 19 TrustReceipt persistence/replay checks")
    p_phase19.add_argument("--out-dir", default=ainir_temp_str("ainir_phase19_trust_receipt"))

    p_phase20 = sub.add_parser("phase20-receipt-conformance-eval", help="run Phase 20 TrustReceipt conformance integration checks")
    p_phase20.add_argument("--out-dir", default=ainir_temp_str("ainir_phase20_receipt_conformance"))

    p_export = sub.add_parser("verified-intent-export", help="export optional VerifiedIntentPacket after Trust Gate pass")
    p_export.add_argument("draft")
    p_export.add_argument("--profile", default="AIVL", help="external consumer profile name; currently supports AIVLConsumerProfile")
    p_export.add_argument("--out-dir", default=ainir_temp_str("ainir_verified_intent_results"))
    p_export.add_argument("--json", action="store_true")
    p_export.add_argument("--env", choices=list(allowed_environments()), default="public_demo", help="trusted runtime environment; draft.environment is ignored")

    p_phase22 = sub.add_parser("phase22-verified-intent-eval", help="run Phase 22 VerifiedIntentPacket export/profile conformance checks")
    p_phase22.add_argument("--out-dir", default=ainir_temp_str("ainir_phase22_verified_intent"))

    p_phase23 = sub.add_parser("phase23-verified-intent-hardening-eval", help="run Phase 23 VerifiedIntentPacket export contract hardening checks")
    p_phase23.add_argument("--out-dir", default=ainir_temp_str("ainir_phase23_verified_intent_hardening"))

    p_phase24 = sub.add_parser("phase24-verified-intent-semantic-eval", help="run Phase 24 VerifiedIntentPacket semantic grounding and validator checks")
    p_phase24.add_argument("--out-dir", default=ainir_temp_str("ainir_phase24_verified_intent_semantic"))

    p_phase25 = sub.add_parser("phase25-verified-intent-contract-eval", help="run Phase 25 VerifiedIntentPacket strict contract and registry consistency checks")
    p_phase25.add_argument("--out-dir", default=ainir_temp_str("ainir_phase25_verified_intent_contract"))

    p_phase21 = sub.add_parser("phase21-launch-readiness-eval", help="run Phase 21 launch-readiness gate with TrustReceipt replay")
    p_phase21.add_argument("--out-dir", default=ainir_temp_str("ainir_phase21_launch_readiness"))

    p_phase26 = sub.add_parser("phase26-private-trial-eval", help="run Phase 26 local GitHub private-trial simulation")
    p_phase26.add_argument("--out-dir", default=ainir_temp_str("ainir_phase26_private_trial"))

    p_phase30 = sub.add_parser("phase30-v1-rc-candidate-check", help="run Phase 30 v1.0 RC candidate scope/package check")
    p_phase30.add_argument("--out-dir", default=ainir_temp_str("ainir_phase30_v1_rc_candidate"))
    p_phase30.add_argument("--mode", choices=["quick-integrity", "full"], default="full", help="quick-integrity skips the heavier Phase 26 private-trial simulation")

    args = parser.parse_args(argv)

    if args.cmd == "verify":
        context = TrustedExecutionContext.from_environment(args.env, source="cli", purpose="verification")
        draft = load_draft(args.draft)
        report = verify_draft(draft, context)
        if args.json:
            print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
        else:
            _print_report(report.as_dict())
        return 0 if report.status == "passed" else 2

    if args.cmd == "trust-gate":
        context = TrustedExecutionContext.from_environment(args.env, source="cli", purpose="trust_gate")
        draft = load_draft(args.draft)
        decision = evaluate_trust_gate(draft, context).as_dict()
        if args.out_dir:
            _write_trust_gate_bundle(Path(args.out_dir), decision)
        if args.json:
            print(json.dumps(decision, indent=2, ensure_ascii=False))
        else:
            print(f"trust_gate_status: {decision['status']}")
            print(f"module: {decision['module_id']}")
            print(f"workflow: {decision['workflow']}")
            print(f"lowering_allowed: {decision['lowering_allowed']}")
            print(f"receipt_id: {decision['receipt'].get('receipt_id')}")
            for finding in decision.get("findings", []):
                if finding.get("severity") == "critical":
                    print(f"[critical] {finding.get('rule')} :: {finding.get('target')}")
        return 0 if decision["status"] == "passed" else 2

    if args.cmd == "trust-receipt-issue":
        context = TrustedExecutionContext.from_environment(args.env, source="cli", purpose="trust_receipt_issue")
        issued = issue_trust_receipt(args.draft, args.out_dir, context).as_dict()
        if args.json:
            print(json.dumps(issued, indent=2, ensure_ascii=False))
        else:
            print(f"trust_receipt_issued: {issued['receipt_id']}")
            print(f"trust_status: {issued['trust_status']}")
            print(f"receipt: {issued['receipt_path']}")
            print(f"decision: {issued['decision_path']}")
        return 0

    if args.cmd == "trust-receipt-replay":
        context = None
        if args.env:
            context = TrustedExecutionContext.from_environment(args.env, source="cli", purpose="trust_receipt_replay")
        report = replay_trust_receipt(args.receipt, args.draft, context).as_dict()
        if args.out_dir:
            out = Path(args.out_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / "trust_receipt_replay_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"trust_receipt_replay: {report['overall_status']}")
            print(f"receipt_id: {report.get('receipt_id')}")
            for check in report.get("checks", []):
                if check.get("status") != "passed":
                    print(f"[failed] {check.get('check')} expected={check.get('expected')} actual={check.get('actual')}")
        return 0 if report["overall_status"] == "passed" else 2

    if args.cmd == "lower":
        context = TrustedExecutionContext.from_environment(args.env, source="cli", purpose="lowering")
        draft = load_draft(args.draft)
        decision = evaluate_trust_gate(draft, context)
        if not decision.lowering_allowed:
            print(f"lowering refused by trust gate: status={decision.status}")
            if decision.failed_gates:
                print("failed_gates: " + ", ".join(decision.failed_gates))
            for finding in decision.findings:
                if finding.get("severity") == "critical":
                    print(f"[critical] {finding.get('rule')} :: {finding.get('target')}")
            return 2
        report = verify_draft(draft, context)
        try:
            target = lower_to_typescript(draft, report, args.out_dir, context)
        except RuntimeError as exc:
            print(f"lowering refused: {exc}")
            return 2
        print(f"lowered: {target}")
        return 0

    if args.cmd == "demo":
        context = TrustedExecutionContext.from_environment(args.env, source="cli", purpose="demo")
        return _run_demo(Path(args.examples_dir), Path(args.out_dir), context)


    if args.cmd == "golden-trace-eval":
        summary = run_golden_traces(args.traces, args.out_dir, args.env)
        print(f"AiNIR golden traces: {summary['overall_status']}")
        print(f"traces: {summary['trace_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2
    if args.cmd == "negative-conformance-eval":
        summary = run_negative_conformance_corpus(args.corpus, args.out_dir, args.env)
        print(f"AiNIR negative conformance: {summary['overall_status']}")
        print(f"cases: {summary['case_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    if args.cmd == "phase19-trust-receipt-eval":
        from .phase19_trust_receipt_eval import run_phase19_trust_receipt_eval
        summary = run_phase19_trust_receipt_eval(args.out_dir)
        print(f"AiNIR Phase 19 trust receipt eval: {summary['overall_status']}")
        print(f"cases: {summary['case_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    if args.cmd == "phase20-receipt-conformance-eval":
        from .phase20_receipt_conformance_eval import run_phase20_receipt_conformance_eval
        summary = run_phase20_receipt_conformance_eval(args.out_dir)
        print(f"AiNIR Phase 20 receipt conformance eval: {summary['overall_status']}")
        print(f"cases: {summary['case_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    if args.cmd == "phase18-trust-gate-eval":
        from .phase18_trust_gate_eval import run_phase18_trust_gate_eval
        summary = run_phase18_trust_gate_eval(args.out_dir)
        print(f"AiNIR Phase 18 trust gate eval: {summary['overall_status']}")
        print(f"cases: {summary['case_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    if args.cmd == "phase21-launch-readiness-eval":
        from .phase21_release_readiness_eval import run_phase21_launch_readiness_eval
        summary = run_phase21_launch_readiness_eval(args.out_dir)
        print(f"AiNIR Phase 21 launch readiness: {summary['overall_status']}")
        print(f"decision: {summary['decision']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2


    if args.cmd == "verified-intent-export":
        from .verified_intent_export import export_verified_intent_packet
        context = TrustedExecutionContext.from_environment(args.env, source="cli", purpose="verified_intent_export")
        draft = load_draft(args.draft)
        result = export_verified_intent_packet(draft, context, args.profile).as_dict()
        out = Path(args.out_dir)
        _write_verified_intent_bundle(out, result)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"verified_intent_export: {result['status']}")
            print(f"reports: {args.out_dir}")
            for reason in result.get("reasons", []):
                print(f"reason: {reason}")
        return 0 if result["status"] == "exported" else 2

    if args.cmd == "phase22-verified-intent-eval":
        from .phase22_verified_intent_eval import run_phase22_verified_intent_eval
        summary = run_phase22_verified_intent_eval(args.out_dir)
        print(f"AiNIR Phase 22 verified intent export eval: {summary['overall_status']}")
        print(f"cases: {summary['case_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    if args.cmd == "phase23-verified-intent-hardening-eval":
        from .phase23_verified_intent_hardening_eval import run_phase23_verified_intent_hardening_eval
        summary = run_phase23_verified_intent_hardening_eval(args.out_dir)
        print(f"AiNIR Phase 23 verified intent export hardening eval: {summary['overall_status']}")
        print(f"cases: {summary['case_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    if args.cmd == "phase24-verified-intent-semantic-eval":
        from .phase24_verified_intent_semantic_eval import run_phase24_verified_intent_semantic_eval
        summary = run_phase24_verified_intent_semantic_eval(args.out_dir)
        print(f"AiNIR Phase 24 verified intent semantic eval: {summary['overall_status']}")
        print(f"cases: {summary['case_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    if args.cmd == "phase25-verified-intent-contract-eval":
        from .phase25_verified_intent_contract_eval import run_phase25_verified_intent_contract_eval
        summary = run_phase25_verified_intent_contract_eval(args.out_dir)
        print(f"AiNIR Phase 25 verified intent contract eval: {summary['overall_status']}")
        print(f"cases: {summary['case_count']} passed={summary['passed']} failed={summary['failed']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2


    if args.cmd == "phase26-private-trial-eval":
        from .phase26_private_trial import run_phase26_private_trial
        summary = run_phase26_private_trial(args.out_dir)
        print(f"AiNIR Phase 26 private-trial simulation: {summary['overall_status']}")
        print(f"decision: {summary['decision']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    if args.cmd == "phase30-v1-rc-candidate-check":
        from .phase30_v1_rc_candidate import run_phase30_v1_rc_candidate_check
        summary = run_phase30_v1_rc_candidate_check(args.out_dir, mode=args.mode)
        print(f"AiNIR Phase 30 v1.0 RC candidate check: {summary['overall_status']}")
        print(f"decision: {summary['decision']}")
        print(f"reports: {args.out_dir}")
        return 0 if summary["overall_status"] == "passed" else 2

    return 1


def _run_demo(examples_dir: Path, out_dir: Path, context: TrustedExecutionContext) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    draft_paths = list(iter_example_drafts(examples_dir))
    if not draft_paths:
        summary = {
            "overall_status": "failed",
            "reason": "No example draft files were found.",
            "examples_dir": str(examples_dir),
            "examples": [],
        }
        dump_yaml(summary, out_dir / "summary.yaml")
        print("AiNIR public demo: failed")
        print(f"reason: no example draft files found in {examples_dir}")
        print(f"reports: {out_dir}")
        return 2
    manifest = _load_demo_manifest(examples_dir)
    for path in draft_paths:
        draft = load_draft(path)
        report = verify_draft(draft, context)
        decision = evaluate_trust_gate(draft, context)
        example_name = path.parent.name
        expected_status = (manifest.get(example_name) or {}).get("expected_status") if manifest else None
        result = {"example": example_name, "expected_status": expected_status, **report.as_dict()}
        result["trust_gate"] = {
            "status": decision.status,
            "lowering_allowed": decision.lowering_allowed,
            "handoff_allowed": decision.handoff_allowed,
            "failed_gates": list(decision.failed_gates),
        }
        results.append(result)
        dump_yaml(report.as_dict(), out_dir / f"{example_name}.report.yaml")
        if report.status == "passed":
            if not decision.lowering_allowed:
                results[-1]["lowering_error"] = "trust_gate_lowering_not_allowed"
                results[-1]["status"] = "failed"
                results[-1]["critical_count"] = int(results[-1].get("critical_count", 0)) + 1
                results[-1]["findings"].append({
                    "rule": "T011.trust_gate_lowering_not_allowed",
                    "severity": "critical",
                    "target": "trust_gate.lowering_allowed",
                    "message": "Demo lowering is refused unless TrustGateDecision.lowering_allowed is true.",
                })
            else:
                try:
                    lower_to_typescript(draft, report, out_dir / "lowered", context)
                except RuntimeError as exc:
                    results[-1]["lowering_error"] = str(exc)
                    results[-1]["status"] = "failed"
                    results[-1]["critical_count"] = int(results[-1].get("critical_count", 0)) + 1
                    results[-1]["findings"].append({
                        "rule": "L001.lowering_refused",
                        "severity": "critical",
                        "target": "lowerer",
                        "message": str(exc),
                    })

    summary = {
        "overall_status": "passed" if all(_expected_ok(r) for r in results) else "failed",
        "trusted_context": {"environment": context.environment, "source": context.source, "purpose": context.purpose},
        "expected_status_source": "examples/demo_manifest.json" if manifest else "legacy_name_fallback",
        "examples": results,
    }
    dump_yaml(summary, out_dir / "summary.yaml")
    print(f"AiNIR public demo: {summary['overall_status']}")
    for r in results:
        print(f"- {r['example']}: {r['status']} ({r['critical_count']} critical)")
    print(f"reports: {out_dir}")
    return 0 if summary["overall_status"] == "passed" else 2


def _load_demo_manifest(examples_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = examples_dir / "demo_manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    examples = data.get("examples", {}) if isinstance(data, dict) else {}
    return examples if isinstance(examples, dict) else {}


def _expected_ok(result: dict[str, Any]) -> bool:
    expected = result.get("expected_status")
    if expected == "passed":
        return result["status"] == "passed"
    if expected == "blocked":
        return result["status"] == "blocked" and result["critical_count"] > 0
    # Legacy fallback for older extracted demos without a manifest.
    example = result["example"]
    if example.endswith("_safe"):
        return result["status"] == "passed"
    return result["status"] == "blocked" and result["critical_count"] > 0


def _print_report(report: dict[str, Any]) -> None:
    print(f"status: {report['status']}")
    print(f"module: {report['module_id']}")
    print(f"workflow: {report['workflow']}")
    for finding in report["findings"]:
        print(f"[{finding['severity']}] {finding['rule']} :: {finding['target']}")
        print(f"  {finding['message']}")
        if finding.get("suggestion"):
            print(f"  suggestion: {finding['suggestion']}")


if __name__ == "__main__":
    raise SystemExit(main())
