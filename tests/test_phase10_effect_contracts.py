from __future__ import annotations

import tempfile
from pathlib import Path

from ainir.core import load_draft
from ainir.verifier import verify_draft
from ainir.lowering import lower_to_typescript


def _verify_yaml(text: str):
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write(text)
        path = Path(f.name)
    return verify_draft(load_draft(path))


def _assert_blocked(text: str, rule_prefix: str | None = None):
    report = _verify_yaml(text)
    assert report.status in {'blocked', 'invalid'}, report.as_dict()
    if rule_prefix:
        assert any(f.rule.startswith(rule_prefix) for f in report.findings), report.as_dict()
    return report


def test_create_user_without_normalize_duplicate_transaction_is_blocked():
    _assert_blocked('''
module: demo.create_user_minimal
workflow: CreateUser
task: CreateUserRequest
operations:
  - id: op.insert_user
    op: db.insert_user
    effects: [effect.storage.db.write]
    capabilities: [cap.db.user.write]
    policies: [policy.user_email_unique]
  - id: op.outbox
    op: outbox.insert_welcome_email_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
policies:
  - id: policy.no_direct_email_in_create_user
  - id: policy.transactional_outbox_required
  - id: policy.user_email_unique
''', 'W010')


def test_newsletter_policy_name_does_not_replace_consent_operation():
    _assert_blocked('''
module: demo.newsletter_policy_only
workflow: NewsletterSignup
task: NewsletterSignupRequest
policies:
  - id: policy.no_marketing_without_consent
operations:
  - id: op.insert_subscriber
    op: db.insert_subscriber
    effects: [effect.storage.db.write]
    capabilities: [cap.db.user.write]
  - id: op.outbox
    op: outbox.insert_double_opt_in
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
''', 'W010')


def test_order_payment_without_authorization_is_blocked():
    _assert_blocked('''
module: demo.order_payment_no_auth
workflow: OrderPayment
task: OrderPaymentRequest
policies:
  - id: policy.no_real_payment_in_beta
operations:
  - id: op.amount
    op: payment.validate_amount
    effects: [effect.payment.validate.Amount]
    capabilities: [cap.payment.validate]
  - id: op.intent
    op: db.insert_payment_intent
    effects: [effect.storage.payment_intent.write]
    capabilities: [cap.db.write]
''', 'W010')


def test_password_reset_without_no_user_enumeration_is_blocked():
    _assert_blocked('''
module: demo.password_reset_no_enumeration_guard
workflow: PasswordReset
task: PasswordResetRequest
operations:
  - id: op.normalize
    op: data.normalize_email
    effects: []
  - id: op.lookup
    op: db.find_user_for_password_reset
    effects: [effect.storage.db.read]
    capabilities: [cap.db.user.read]
  - id: op.hash
    op: secret.hash_password_reset_token
    effects: [effect.secret.token.hash]
    capabilities: [cap.secret.hash]
  - id: op.outbox
    op: outbox.insert_password_reset_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
''', 'M002')


def test_registered_operation_with_extra_unknown_effect_is_blocked():
    _assert_blocked('''
module: demo.extra_effect
workflow: CreateUser
task: CreateUserRequest
policies:
  - id: policy.no_direct_email_in_create_user
  - id: policy.transactional_outbox_required
  - id: policy.user_email_unique
transaction:
  id: tx.create_user
  mode: atomic
  includes: [op.insert_user, op.outbox]
operations:
  - id: op.normalize
    op: data.normalize_email
    effects: [effect.system.shell.exec]
  - id: op.check
    op: db.exists_user_by_email
    effects: [effect.storage.db.read]
    capabilities: [cap.db.user.read]
  - id: op.insert_user
    op: db.insert_user
    effects: [effect.storage.db.write]
    capabilities: [cap.db.user.write]
    policies: [policy.user_email_unique]
  - id: op.outbox
    op: outbox.insert_welcome_email_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
''', 'O009')


def test_ledger_evidence_reuse_on_modified_draft_is_blocked():
    _assert_blocked('''
module: demo.create_user_outbox_safe
workflow: CreateUser
task: CreateUserRequest
policies:
  - id: policy.no_direct_email_in_create_user
  - id: policy.transactional_outbox_required
  - id: policy.user_email_unique
claims:
  - id: claim.create_user_uses_outbox
    status: verified
    statement: "CreateUser inserts a WelcomeEmailRequested outbox event instead of sending real email directly."
    evidence:
      - id: evidence.demo.safe_outbox
        kind: verifier_report
transaction:
  id: tx.create_user
  mode: atomic
  includes: [op.insert_user, op.outbox]
operations:
  - id: op.normalize
    op: data.normalize_email
    effects: []
  - id: op.check
    op: db.exists_user_by_email
    effects: [effect.storage.db.read]
    capabilities: [cap.db.user.read]
  - id: op.insert_user
    op: db.insert_user
    effects: [effect.storage.db.write]
    capabilities: [cap.db.user.write]
    policies: [policy.user_email_unique]
  - id: op.outbox
    op: outbox.insert_welcome_email_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
  - id: op.extra
    op: data.noop
    effects: []
''', 'T001')


def test_transaction_must_resolve_and_include_required_roles():
    _assert_blocked('''
module: demo.create_user_bad_tx
workflow: CreateUser
task: CreateUserRequest
policies:
  - id: policy.no_direct_email_in_create_user
  - id: policy.transactional_outbox_required
  - id: policy.user_email_unique
transaction:
  id: tx.create_user
  mode: atomic
  includes: [op.missing]
operations:
  - id: op.normalize
    op: data.normalize_email
    effects: []
  - id: op.check
    op: db.exists_user_by_email
    effects: [effect.storage.db.read]
    capabilities: [cap.db.user.read]
  - id: op.insert_user
    op: db.insert_user
    effects: [effect.storage.db.write]
    capabilities: [cap.db.user.write]
    policies: [policy.user_email_unique]
  - id: op.outbox
    op: outbox.insert_welcome_email_requested
    effects: [effect.storage.outbox.write]
    capabilities: [cap.outbox.write]
''', 'TX003')


def test_blocked_draft_does_not_lower():
    yaml_text = '''
module: demo.extra_effect
workflow: CreateUser
task: CreateUserRequest
operations:
  - id: op.normalize
    op: data.normalize_email
    effects: [effect.system.shell.exec]
'''
    report = _assert_blocked(yaml_text)
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False, encoding='utf-8') as f:
        f.write(yaml_text)
        path = Path(f.name)
    try:
        lower_to_typescript(load_draft(path), report, Path(path).parent / 'out')
    except RuntimeError:
        pass
    else:
        raise AssertionError('blocked draft should not lower')
