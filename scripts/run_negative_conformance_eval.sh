#!/usr/bin/env bash
set -euo pipefail
AINIR_TMP="${AINIR_TEMP_ROOT:-${TMPDIR:-/tmp}}"
PYTHONPATH=src python -m ainir negative-conformance-eval --out-dir "${1:-$AINIR_TMP/ainir_negative_conformance}"
