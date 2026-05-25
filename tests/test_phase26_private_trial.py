
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ainir.phase26_private_trial import _is_within, _safe_trial_temp_parent, _scan_ci, _scan_doc_commands, _scan_packaging_cleanliness, _scan_status_claims, ROOT


def test_phase26_static_packaging_cleanliness():
    root = Path(__file__).resolve().parents[1]
    result = _scan_packaging_cleanliness(root)
    assert result["status"] == "passed", result


def test_phase26_static_status_claims():
    root = Path(__file__).resolve().parents[1]
    result = _scan_status_claims(root)
    assert result["status"] == "passed", result


def test_phase26_doc_commands_use_tmp_outputs():
    root = Path(__file__).resolve().parents[1]
    result = _scan_doc_commands(root)
    assert result["status"] == "passed", result


def test_phase26_ci_uses_private_trial_gate():
    root = Path(__file__).resolve().parents[1]
    result = _scan_ci(root)
    assert result["status"] == "passed", result


def test_phase26_copy_temp_parent_is_outside_repo(monkeypatch, tmp_path):
    repo_local_temp = ROOT / '.codex_tmp'
    repo_local_temp.mkdir(exist_ok=True)
    monkeypatch.setattr(tempfile, 'gettempdir', lambda: str(repo_local_temp))
    parent = _safe_trial_temp_parent()
    assert not _is_within(parent, ROOT)


def test_phase26_local_temp_patterns_are_ignored(tmp_path):
    root = Path(__file__).resolve().parents[1]
    local_temp = root / '.codex_tmp'
    local_temp.mkdir(exist_ok=True)
    try:
        result = _scan_packaging_cleanliness(root)
        assert result['status'] == 'passed', result
    finally:
        try:
            local_temp.rmdir()
        except OSError:
            pass
