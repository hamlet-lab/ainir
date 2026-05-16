from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_DIRS = {
    '__pycache__', '.pytest_cache', 'demo_results', 'prelaunch_results', 'review_results',
    'negative_conformance_results', 'golden_trace_results', 'phase17_review_results',
    'phase18_trust_gate_results', 'phase19_trust_receipt_results',
    'phase20_receipt_conformance_results', 'phase21_launch_readiness_results',
    'phase22_verified_intent_results', 'phase23_verified_intent_hardening_results',
    'phase24_verified_intent_semantic_results', 'phase25_verified_intent_contract_results',
    'verified_intent_results', 'out', 'dist', 'build', '.mypy_cache', '.ruff_cache', '.coverage',
    'github_private_trial_results',
}
FORBIDDEN_SUFFIXES = {'.pyc', '.pyo'}
PRIVATE_ARCHIVE_MARKERS = {'ALL_IN_ONE', 'PRIVATE_RC', 'private_rc', 'review_package.zip'}

# Repo-local local-QA/temp folders should never be copied into a Phase 26 trial
# workspace or committed to a public candidate. If present in a source checkout,
# Phase 26 reports a warning and ignores them during temp-copy setup. If they
# are Git-tracked, Phase 26 fails the tracked-file scan.
LOCAL_TEMP_DIR_PATTERNS = (
    '.codex_tmp',
    '.ainir_tmp',
    'codex_ainir_*',
    'github_private_trial_results',
    'ainir_demo_results',
    'ainir_negative_conformance',
    'ainir_golden_traces',
    'ainir_prelaunch',
    'ainir_release_review',
    'ainir_phase*_trial_*',
    'ainir_phase*_private_trial*',
    'ainir_phase*_results*',
    'ainir_phase*_demo*',
    'ainir_phase*_negative_conformance*',
    'ainir_phase*_golden_traces*',
    'ainir_phase*_prelaunch*',
    'ainir_phase*_release_review*',
)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def _is_local_temp_part(part: str) -> bool:
    return any(fnmatch.fnmatch(part, pattern) for pattern in LOCAL_TEMP_DIR_PATTERNS)


def _is_local_temp_rel(rel: Path) -> bool:
    return any(_is_local_temp_part(part) for part in rel.parts)


def _safe_trial_temp_parent() -> Path:
    """Choose a temporary parent outside the repository tree.

    Some evaluators set TMP/TEMP/AINIR_TEMP_ROOT to a repo-local folder. If a
    private-trial simulation copies the repository into that folder, the copy can
    see its own generated output. This helper keeps the trial workspace outside
    the checkout.
    """
    candidates: list[Path | None] = [
        Path(tempfile.gettempdir()),
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Temp' if os.environ.get('LOCALAPPDATA') else None,
        Path.home() / '.cache' / 'ainir',
        ROOT.parent,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            candidate = candidate.expanduser().resolve()
        except OSError:
            continue
        if not _is_within(candidate, ROOT):
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
    fallback = (ROOT.parent / '.ainir_trial_tmp').resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _safe_trial_output_root(work_root: Path) -> Path:
    """Return a command-output root outside both source and copied repos."""
    override = os.environ.get('AINIR_TEMP_ROOT')
    if override:
        try:
            candidate = Path(override).expanduser().resolve()
            if not _is_within(candidate, ROOT) and not _is_within(candidate, work_root):
                candidate.mkdir(parents=True, exist_ok=True)
                return candidate
        except OSError:
            pass
    output = (work_root.parent / 'ainir_outputs').resolve()
    output.mkdir(parents=True, exist_ok=True)
    return output


def _trial_output_path(work_root: Path, name: str) -> Path:
    return _safe_trial_output_root(work_root) / name


def _trial_output_str(work_root: Path, name: str) -> str:
    return str(_trial_output_path(work_root, name))


def _env(work_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env['PYTHONPATH'] = str(work_root / 'src') + (os.pathsep + env.get('PYTHONPATH', '') if env.get('PYTHONPATH') else '')
    env.setdefault('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
    env.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    env['AINIR_TEMP_ROOT'] = str(_safe_trial_output_root(work_root))
    return env


def _safe_step_name(name: str) -> str:
    return ''.join(ch if ch.isalnum() or ch in '._-' else '_' for ch in name)[:100]


def _run_step(work_root: Path, out_dir: Path, name: str, cmd: list[str], *, expect_success: bool = True, timeout: int = 240) -> dict[str, Any]:
    print(f"[phase26] starting {name}", flush=True)
    proc = subprocess.run(cmd, cwd=work_root, env=_env(work_root), text=True, capture_output=True, timeout=timeout)
    log_dir = out_dir / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_step_name(name)
    (log_dir / f'{safe}.stdout.txt').write_text(proc.stdout or '', encoding='utf-8')
    (log_dir / f'{safe}.stderr.txt').write_text(proc.stderr or '', encoding='utf-8')
    ok = (proc.returncode == 0) if expect_success else (proc.returncode != 0)
    return {
        'name': name,
        'command': cmd,
        'expected': 'success' if expect_success else 'failure',
        'exit_code': proc.returncode,
        'status': 'passed' if ok else 'failed',
        'stdout_tail': (proc.stdout or '').strip()[-1200:],
        'stderr_tail': (proc.stderr or '').strip()[-1200:],
    }



def _sanitize_out_dir(out_dir: Path) -> Path:
    """Avoid writing default Phase 26 reports into repo-local scratch roots.

    Explicit arbitrary output directories are respected. Known local scratch
    paths created from TMP/TEMP/AINIR_TEMP_ROOT are redirected to the safe
    private-trial temp parent so the checkout stays clean.
    """
    try:
        resolved = out_dir.expanduser().resolve()
    except OSError:
        return out_dir
    if _is_within(resolved, ROOT) and _is_local_temp_rel(resolved.relative_to(ROOT)):
        target = (_safe_trial_temp_parent() / resolved.name).resolve()
        target.mkdir(parents=True, exist_ok=True)
        return target
    return out_dir

def _copy_repo_to_temp() -> Path:
    temp_parent = Path(tempfile.mkdtemp(prefix='ainir_phase26_trial_', dir=str(_safe_trial_temp_parent())))
    work_root = temp_parent / 'repo'
    ignore = shutil.ignore_patterns(
        '.git', '__pycache__', '*.pyc', '.pytest_cache', *LOCAL_TEMP_DIR_PATTERNS
    )
    shutil.copytree(ROOT, work_root, ignore=ignore)
    return work_root


def _scan_source_repo_local_temp_paths(source_root: Path) -> dict[str, Any]:
    findings: list[str] = []
    for path in source_root.rglob('*'):
        if not path.exists():
            continue
        rel = path.relative_to(source_root)
        if _is_local_temp_rel(rel):
            findings.append(f'repo_local_temp_path_present:{rel}')
    return {
        'name': 'source_repo_local_temp_paths',
        'status': 'warning' if findings else 'passed',
        'findings': findings[:80],
        'reason': 'repo-local temp paths are ignored during temp-copy setup but should be cleaned before publishing' if findings else None,
    }


def _scan_packaging_cleanliness(work_root: Path) -> dict[str, Any]:
    findings: list[str] = []
    for path in work_root.rglob('*'):
        rel = path.relative_to(work_root)
        if _is_local_temp_rel(rel):
            continue
        parts = set(rel.parts)
        # Cache dirs are ignored here so local imports do not create noisy failures.
        # Git-tracked cache artifacts are checked by _scan_git_tracked_packaging_cleanliness.
        if parts & {'__pycache__', '.pytest_cache'}:
            continue
        if parts & (FORBIDDEN_DIRS - {'__pycache__', '.pytest_cache'}):
            findings.append(f'forbidden_generated_path:{rel}')
        if path.is_file() and path.suffix in FORBIDDEN_SUFFIXES:
            findings.append(f'forbidden_python_cache:{rel}')
        if path.is_file() and path.suffix == '.zip':
            findings.append(f'nested_zip_not_allowed_in_public_repo:{rel}')
        if path.is_file() and any(marker in path.name for marker in PRIVATE_ARCHIVE_MARKERS):
            findings.append(f'private_archive_marker_in_public_repo:{rel}')
    required_files = [
        'README.md', 'START_HERE.md', 'LICENSE', 'NOTICE', 'pyproject.toml',
        '.github/workflows/ci.yml',
        'docs/pre_v1_status.md', 'docs/public_private_boundary.md',
        'docs/private_archive_boundary.md', 'docs/github_launch_checklist.md',
        'schemas/verified_intent_packet.schema.json', 'registries/safety_registry.yaml',
        'registries/external_consumer_profiles.yaml',
    ]
    for rel in required_files:
        if not (work_root / rel).exists():
            findings.append(f'missing_required_file:{rel}')
    return {'name': 'packaging_cleanliness', 'status': 'passed' if not findings else 'failed', 'findings': findings[:80]}


def _scan_git_tracked_packaging_cleanliness(work_root: Path) -> dict[str, Any]:
    """Detect generated/cache files that are tracked in a real Git checkout."""
    if not (work_root / '.git').exists():
        return {'name': 'git_tracked_packaging_cleanliness', 'status': 'passed', 'findings': ['git_metadata_unavailable_skip_tracked_scan']}
    try:
        proc = subprocess.run(['git', 'ls-files'], cwd=work_root, text=True, capture_output=True, timeout=30)
    except Exception as exc:  # pragma: no cover - defensive for unusual shells
        return {'name': 'git_tracked_packaging_cleanliness', 'status': 'failed', 'findings': [f'git_ls_files_failed:{exc}']}
    if proc.returncode != 0:
        return {'name': 'git_tracked_packaging_cleanliness', 'status': 'failed', 'findings': [proc.stderr.strip()[-500:] or 'git ls-files failed']}
    findings: list[str] = []
    for rel in proc.stdout.splitlines():
        path = Path(rel)
        parts = set(path.parts)
        if parts & FORBIDDEN_DIRS or _is_local_temp_rel(path):
            findings.append(f'tracked_forbidden_generated_path:{rel}')
        if path.suffix in FORBIDDEN_SUFFIXES:
            findings.append(f'tracked_forbidden_python_cache:{rel}')
        if path.suffix == '.zip':
            findings.append(f'tracked_nested_zip_not_allowed_in_public_repo:{rel}')
        if any(marker in path.name for marker in PRIVATE_ARCHIVE_MARKERS):
            findings.append(f'tracked_private_archive_marker_in_public_repo:{rel}')
    return {'name': 'git_tracked_packaging_cleanliness', 'status': 'passed' if not findings else 'failed', 'findings': findings[:80]}


def _scan_status_claims(work_root: Path) -> dict[str, Any]:
    findings: list[str] = []
    text = '\n'.join((work_root / rel).read_text(encoding='utf-8', errors='ignore') for rel in ['README.md', 'START_HERE.md', 'docs/pre_v1_status.md'] if (work_root / rel).exists()).lower()
    required = ['pre-v1', 'not a v1.0 final', 'not a production runtime']
    for phrase in required:
        if phrase not in text:
            findings.append(f'missing_status_phrase:{phrase}')
    forbidden_claims = ['production-ready', 'production ready', 'v1.0 final release', 'v1 final release']
    for phrase in forbidden_claims:
        start = 0
        while True:
            idx = text.find(phrase, start)
            if idx == -1:
                break
            context = text[max(0, idx - 80):idx]
            if 'not' not in context and '아님' not in context:
                findings.append(f'possibly_overstated_status_claim:{phrase}')
                break
            start = idx + len(phrase)
    return {'name': 'status_claim_scope', 'status': 'passed' if not findings else 'failed', 'findings': findings}


def _scan_ci(work_root: Path) -> dict[str, Any]:
    findings: list[str] = []
    ci = work_root / '.github/workflows/ci.yml'
    if not ci.exists():
        return {'name': 'github_actions_ci_static', 'status': 'failed', 'findings': ['missing_ci_file']}
    text = ci.read_text(encoding='utf-8', errors='ignore')
    required_snippets = ['pip install -e ".[dev]"']
    for snippet in required_snippets:
        if snippet not in text:
            findings.append(f'ci_missing_snippet:{snippet}')
    has_phase26 = 'run_phase26_private_trial.py' in text
    has_phase30 = 'run_phase30_v1_rc_candidate_check.py' in text
    if not (has_phase26 or has_phase30):
        findings.append('ci_missing_private_trial_or_rc_candidate_gate')
    suspect = [line.strip() for line in text.splitlines() if '--out-dir ainir_' in line or '--out-dir review_' in line]
    for line in suspect:
        findings.append(f'ci_repo_local_output_path:{line}')
    return {'name': 'github_actions_ci_static', 'status': 'passed' if not findings else 'failed', 'findings': findings}


def _scan_doc_commands(work_root: Path) -> dict[str, Any]:
    findings: list[str] = []
    docs = [work_root / 'README.md', work_root / 'START_HERE.md'] + list((work_root / 'docs').glob('*.md'))
    for path in docs:
        if not path.exists() or not path.is_file():
            continue
        rel = path.relative_to(work_root)
        text = path.read_text(encoding='utf-8', errors='ignore')
        for bad in ['--out-dir out', '--out-dir demo_results', '--out-dir prelaunch_results', '--out-dir review_results', '--out-dir negative_conformance_results', '--out-dir golden_trace_results']:
            if bad in text:
                findings.append(f'{rel}:uses_repo_local_output:{bad}')
    return {'name': 'doc_command_output_paths', 'status': 'passed' if not findings else 'failed', 'findings': findings[:60]}


def _workspace_clean_after_trial(work_root: Path, before_snapshot: set[str]) -> dict[str, Any]:
    after = {str(p.relative_to(work_root)) for p in work_root.rglob('*') if p.is_file() and '.git/' not in str(p)}
    new_files = sorted(after - before_snapshot)
    findings: list[str] = [f'new_repo_local_file_created:{rel}' for rel in new_files]
    return {'name': 'workspace_clean_after_trial', 'status': 'passed' if not findings else 'failed', 'findings': findings[:80], 'new_file_count': len(new_files)}


def run_phase26_private_trial(out_dir: str | Path) -> dict[str, Any]:
    out_dir = _sanitize_out_dir(Path(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    source_temp_scan = _scan_source_repo_local_temp_paths(ROOT)
    work_root = _copy_repo_to_temp()
    before_snapshot = {str(p.relative_to(work_root)) for p in work_root.rglob('*') if p.is_file() and '.git/' not in str(p)}

    steps: list[dict[str, Any]] = []
    steps.append(source_temp_scan)
    steps.append(_scan_packaging_cleanliness(work_root))
    steps.append(_scan_git_tracked_packaging_cleanliness(ROOT))
    steps.append(_scan_status_claims(work_root))
    steps.append(_scan_doc_commands(work_root))
    steps.append(_scan_ci(work_root))

    py = sys.executable
    empty_draft_path = _trial_output_path(work_root, 'ainir_phase26_empty.yaml')
    commands = [
        ('pytest', [py, '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], True, 240),
        ('public_demo', [py, '-m', 'ainir', 'demo', '--out-dir', _trial_output_str(work_root, 'ainir_phase26_demo')], True, 120),
        ('negative_conformance_eval', [py, '-m', 'ainir', 'negative-conformance-eval', '--out-dir', _trial_output_str(work_root, 'ainir_phase26_negative_conformance')], True, 180),
        ('golden_trace_eval', [py, '-m', 'ainir', 'golden-trace-eval', '--out-dir', _trial_output_str(work_root, 'ainir_phase26_golden_traces')], True, 180),
        ('phase21_launch_readiness_eval', [py, '-m', 'ainir', 'phase21-launch-readiness-eval', '--out-dir', _trial_output_str(work_root, 'ainir_phase26_launch_readiness')], True, 240),
        ('phase25_verified_intent_contract_eval', [py, '-m', 'ainir', 'phase25-verified-intent-contract-eval', '--out-dir', _trial_output_str(work_root, 'ainir_phase26_verified_intent_contract')], True, 120),
        ('safe_lowering', [py, '-m', 'ainir', 'lower', 'examples/create_user_outbox_safe/draft.yaml', '--out-dir', _trial_output_str(work_root, 'ainir_phase26_lowering_check')], True, 120),
        ('verified_intent_export', [py, '-m', 'ainir', 'verified-intent-export', 'fixtures/aivl_consumer_profile/pii_export_allowed/draft.yaml', '--profile', 'AIVL', '--out-dir', _trial_output_str(work_root, 'ainir_phase26_verified_intent_export')], True, 120),
        ('empty_draft_must_fail', [py, '-c', f"from pathlib import Path; Path({str(empty_draft_path)!r}).write_text('{{}}')"], True, 30),
        ('empty_draft_verify_fails', [py, '-m', 'ainir', 'verify', str(empty_draft_path), '--json'], False, 60),
    ]
    for name, cmd, expect_success, timeout in commands:
        steps.append(_run_step(work_root, out_dir, name, cmd, expect_success=expect_success, timeout=timeout))

    tsc_available = shutil.which('tsc') is not None
    if tsc_available:
        tsconfig = _trial_output_path(work_root, 'ainir_phase26_lowering_check') / 'tsconfig.json'
        tsconfig.write_text(json.dumps({'compilerOptions': {'strict': True, 'target': 'ES2020', 'module': 'CommonJS', 'noEmit': True}, 'include': ['*.ts']}, indent=2), encoding='utf-8')
        steps.append(_run_step(work_root, out_dir, 'typescript_skeleton_compile', ['tsc', '-p', str(tsconfig)], expect_success=True, timeout=120))
    else:
        steps.append({'name': 'typescript_skeleton_compile', 'status': 'warning', 'reason': 'tsc unavailable in PATH'})

    steps.append(_workspace_clean_after_trial(work_root, before_snapshot))

    failures = [s for s in steps if s.get('status') == 'failed']
    warnings = [s for s in steps if s.get('status') == 'warning']
    overall = 'passed' if not failures else 'failed'
    decision = 'ready_for_private_github_trial' if overall == 'passed' else 'hold_private_trial'
    report = {
        'report': 'ainir.pre_v1.phase26.github_private_trial_simulation',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'output_dir': str(out_dir),
        'overall_status': overall,
        'decision': decision,
        'private_github_trial_ready': overall == 'passed',
        'public_release_ready': False,
        'production_runtime_ready': False,
        'v1_final_ready': False,
        'human_external_evaluator_status': 'pending',
        'steps_total': len(steps),
        'steps_passed': sum(1 for s in steps if s.get('status') == 'passed'),
        'steps_warning': len(warnings),
        'steps_failed': len(failures),
        'steps': steps,
    }
    (out_dir / 'phase26_private_trial_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    lines = [
        '# AiNIR Pre-v1 Phase 26 — GitHub Private Trial Simulation',
        '',
        f"overall_status: {overall}",
        f"decision: {decision}",
        'public_release_ready: false',
        'production_runtime_ready: false',
        'v1_final_ready: false',
        '',
        '| Step | Status |',
        '|---|---|',
    ]
    for step in steps:
        lines.append(f"| {step.get('name')} | {step.get('status')} |")
    if failures:
        lines += ['', '## Failures']
        for step in failures:
            lines.append(f"- {step.get('name')}: {step.get('findings') or step.get('stderr_tail') or step.get('stdout_tail')}")
    if warnings:
        lines += ['', '## Warnings']
        for step in warnings:
            lines.append(f"- {step.get('name')}: {step.get('reason') or step.get('findings')}")
    lines += ['', 'This simulation is local. The next external step is to upload the public candidate to a private GitHub repository and confirm GitHub Actions / README rendering there.']
    (out_dir / 'phase26_private_trial_summary.md').write_text('\n'.join(lines), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run AiNIR Pre-v1 Phase 26 local GitHub private-trial simulation.')
    default_out = str(_safe_trial_temp_parent() / 'ainir_phase26_private_trial')
    parser.add_argument('--out-dir', default=default_out)
    args = parser.parse_args()
    result = run_phase26_private_trial(args.out_dir)
    print(f"AiNIR Phase 26 private-trial simulation: {result['overall_status']}")
    print(f"decision: {result['decision']}")
    actual_out = Path(result.get('output_dir', args.out_dir))
    print(f"report: {actual_out / 'phase26_private_trial_report.json'}")
    print(f"summary: {actual_out / 'phase26_private_trial_summary.md'}")
    raise SystemExit(0 if result['overall_status'] == 'passed' else 2)
