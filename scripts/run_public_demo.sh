#!/usr/bin/env bash
set -euo pipefail
AINIR_TMP="${AINIR_TEMP_ROOT:-${TMPDIR:-/tmp}}"
PYTHONPATH=src python -m ainir demo --out-dir "${1:-$AINIR_TMP/ainir_demo_results}"
