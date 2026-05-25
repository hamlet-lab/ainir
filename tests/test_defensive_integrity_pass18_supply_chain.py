from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_supply_chain_pins_are_enforced():
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'check_ci_supply_chain_pins.py')],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_lockfiles_present_and_type_script_pinned():
    assert (ROOT / 'requirements.lock.txt').exists()
    assert 'PyYAML==6.0.3' in (ROOT / 'requirements.lock.txt').read_text(encoding='utf-8')
    assert 'pytest==9.0.2' in (ROOT / 'requirements.lock.txt').read_text(encoding='utf-8')
    package_lock = (ROOT / 'package-lock.json').read_text(encoding='utf-8')
    assert 'typescript-5.8.3.tgz' in package_lock
    assert 'sha512-p1diW6TqL9L07nNxvRMM7hMMw4c5XOo/1ibL4aAIGmSAt9slTE1Xgw5KWuof2uTOvCg9BY7ZRi+GaF+7sfgPeQ==' in package_lock
