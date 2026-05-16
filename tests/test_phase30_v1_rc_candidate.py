from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v1_rc_docs_exist_and_status_is_bounded():
    required = [
        "docs/v1_rc_candidate.md",
        "docs/v1_rc_scope.md",
        "docs/v1_api_surface.md",
        "docs/v1_acceptance_criteria.md",
        "docs/v1_known_limitations.md",
        "release/v1_0_rc_candidate_manifest.yaml",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "v1.0 RC candidate" in readme
    assert "not a v1.0 final" in readme
    assert "not a production runtime" in readme
