#!/usr/bin/env bash
set -euo pipefail
AINIR_TMP="${AINIR_TEMP_ROOT:-${TMPDIR:-/tmp}}"
python scripts/run_prelaunch_check.py --out-dir "${1:-$AINIR_TMP/ainir_prelaunch_results}"
