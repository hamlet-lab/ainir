$repoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $repoRoot "src"
python -m ainir demo --out-dir "$env:TEMP\ainir_demo_results"
