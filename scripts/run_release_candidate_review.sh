#!/usr/bin/env bash
set -euo pipefail
AINIR_TMP="${AINIR_TEMP_ROOT:-${TMPDIR:-/tmp}}"
python scripts/run_release_candidate_review.py --out-dir "${1:-$AINIR_TMP/ainir_review_results}"
