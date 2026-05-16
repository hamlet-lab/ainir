import yaml
from pathlib import Path

from ainir.core import DraftModule, load_draft
from ainir.execution_context import TrustedExecutionContext
from ainir.lowering import lower_to_typescript
from ainir.verifier import verify_draft


def _safe_create_user_no_claim():
    raw = yaml.safe_load(Path('examples/create_user_outbox_safe/draft.yaml').read_text())
    raw.pop('claims', None)
    return raw


def _report(raw):
    return verify_draft(DraftModule(raw), TrustedExecutionContext.from_environment('public_demo')).as_dict()


def test_exact_capability_rejects_db_delete_capability_on_read_operation():
    raw = _safe_create_user_no_claim()
    for op in raw['operations']:
        if op['id'] == 'op.check_duplicate':
            op['capabilities'] = ['cap.db.delete.everything']
    report = _report(raw)
    assert report['status'] == 'blocked'
    assert any(f['rule'] == 'O012.operation_declares_unallowed_capability' for f in report['findings'])


def test_exact_capability_rejects_payment_capability_on_pure_operation():
    raw = _safe_create_user_no_claim()
    for op in raw['operations']:
        if op['id'] == 'op.normalize_email':
            op['capabilities'] = ['cap.payment.charge.real']
    report = _report(raw)
    assert report['status'] == 'blocked'
    assert any(f['rule'] == 'O012.operation_declares_unallowed_capability' for f in report['findings'])


def test_exact_capability_allows_registered_alternative_read_capability():
    raw = _safe_create_user_no_claim()
    for op in raw['operations']:
        if op['id'] == 'op.check_duplicate':
            op['capabilities'] = ['cap.db.read']
    report = _report(raw)
    assert report['status'] == 'passed', report


def test_lowered_code_dispatches_by_canonical_envelope_not_local_id(tmp_path):
    raw = _safe_create_user_no_claim()
    draft = DraftModule(raw)
    ctx = TrustedExecutionContext.from_environment('public_demo')
    report = verify_draft(draft, ctx)
    assert report.status == 'passed', report.as_dict()
    target = lower_to_typescript(draft, report, tmp_path, ctx)
    text = target.read_text()
    assert 'callOperation(envelope_' in text
    assert 'ctx.call("op.' not in text
    assert 'canonicalOp' in text
