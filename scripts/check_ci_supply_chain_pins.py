#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'ci.yml'
EXPECTED_ACTIONS = {
    'actions/checkout': '34e114876b0b11c390a56381ad16ebd13914f8d5',
    'actions/setup-python': 'a26af69be951a213d495a4c3e4e4022e16d87065',
    'actions/setup-node': '49933ea5288caeca8642d1e84afbd3f7d6820020',
}


def main() -> int:
    text = WORKFLOW.read_text(encoding='utf-8')
    failures: list[str] = []
    for action, sha in EXPECTED_ACTIONS.items():
        pattern = rf"uses:\s*{re.escape(action)}@([0-9a-f]{{40}})"
        match = re.search(pattern, text)
        if not match:
            failures.append(f'{action} is not pinned to a full 40-character commit SHA')
        elif match.group(1) != sha:
            failures.append(f'{action} pinned SHA mismatch: {match.group(1)} != {sha}')
    if re.search(r"uses:\s*[^\s#]+@v\d+", text):
        failures.append('workflow still contains a mutable version-tag action reference')
    if 'requirements.lock.txt' not in text:
        failures.append('workflow does not use requirements.lock.txt')
    if 'npm ci' not in text:
        failures.append('workflow does not install Node dependencies from package-lock with npm ci')
    if 'npm install -g' in text:
        failures.append('workflow still performs global npm install')
    if failures:
        for failure in failures:
            print(f'FAILED: {failure}')
        return 2
    print('CI supply-chain pins: passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
