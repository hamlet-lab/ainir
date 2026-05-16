param([string]$OutDir = "$env:TEMP\ainir_review_results")
python scripts/run_release_candidate_review.py --out-dir $OutDir
