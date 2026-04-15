from pathlib import Path

from drawbot_cli.spec.core import render_spec


FIXTURE_ROOT = Path("fixtures/brand_artifacts")


def test_render_spec_creates_missing_output_directory(tmp_path):
    rendered = render_spec(
        FIXTURE_ROOT / "social-quote.recipe.yaml",
        tmp_path / "nested" / "social-quote.pdf",
    )

    assert rendered == (tmp_path / "nested" / "social-quote.pdf").resolve()
    assert rendered.exists()
