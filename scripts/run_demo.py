from ainir.cli import main
from ainir.temp_paths import ainir_temp_str

raise SystemExit(main(["demo", "--out-dir", ainir_temp_str("ainir_demo_results")]))
