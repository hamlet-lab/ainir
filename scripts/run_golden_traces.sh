#!/usr/bin/env bash
set -euo pipefail
AINIR_TMP="${AINIR_TEMP_ROOT:-${TMPDIR:-/tmp}}"
PYTHONPATH=src python -m ainir golden-trace-eval --out-dir "${1:-$AINIR_TMP/ainir_golden_traces}"
