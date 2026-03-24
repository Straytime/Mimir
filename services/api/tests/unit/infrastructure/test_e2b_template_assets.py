from pathlib import Path


def test_e2b_template_assets_include_cjk_font_and_fc_cache_step() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    font_path = repo_root / "assets" / "fonts" / "NotoSansCJKsc-Regular.otf"
    dockerfile_path = repo_root / "e2b_template" / "e2b.Dockerfile"

    assert font_path.exists()
    assert dockerfile_path.exists()

    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    assert "NotoSansCJKsc-Regular.otf" in dockerfile
    assert "fc-cache" in dockerfile
    assert "fontconfig" in dockerfile
