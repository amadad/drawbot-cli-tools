from __future__ import annotations

import json

from typer.testing import CliRunner

from drawbot_cli.app import app
from drawbot_cli.recipes.core import load_recipe, validate_recipe


runner = CliRunner()


def test_recipe_validate_and_explain_fixture():
    result = runner.invoke(app, ["recipe", "validate", "fixtures/brand_artifacts/social-quote.recipe.yaml"])
    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "ok"

    explain = runner.invoke(app, ["recipe", "explain", "fixtures/brand_artifacts/social-quote.recipe.yaml", "--json"])
    assert explain.exit_code == 0, explain.stdout
    payload = json.loads(explain.stdout)
    assert payload["artifact"] == "social-quote"
    assert payload["page"] == {"aspect_ratio": "4:5", "height": 1350, "width": 1080}
    assert payload["content_fields"] == ["quote", "author", "source"]
    assert payload["placements"] == ["accent_bar", "author", "panel", "quote", "source"]
    assert payload["variants"] == {"accent_edge": "bottom", "format": "social-quote-portrait"}


def test_recipe_validate_reports_missing_content_field(tmp_path):
    content_path = tmp_path / "content.yaml"
    content_path.write_text('quote: "Hello"\nauthor: "Acme"\n', encoding="utf-8")
    recipe_path = tmp_path / "recipe.yaml"
    recipe_path.write_text(
        f"""
contract_version: 1
brand: acme
artifact: social-quote
content: {content_path}
variants:
  format: social-quote-portrait
  accent_edge: bottom
page:
  width: 1080
  height: 1350
safe_zone:
  x: 96
  y: 96
  width: 888
  height: 1158
placements:
  quote:
    x: 96
    y: 650
    width: 888
    height: 360
    anchor: bottom-left
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["recipe", "validate", str(recipe_path), "--json"])
    assert result.exit_code == 1, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "content missing required field: source" in payload["errors"]


def test_recipe_validate_reports_embedded_copy_mismatch(tmp_path):
    content_path = tmp_path / "content.yaml"
    content_path.write_text(
        'quote: "Good design is visible structure made quietly inevitable."\n'
        'author: "Acme Studio"\n'
        'source: "Design Principles Notes, 2026"\n',
        encoding="utf-8",
    )
    recipe_path = tmp_path / "recipe.yaml"
    recipe_path.write_text(
        f"""
contract_version: 1
brand: acme
artifact: social-quote
content: {content_path}
variants:
  format: social-quote-portrait
  accent_edge: bottom
page:
  width: 1080
  height: 1350
safe_zone:
  x: 96
  y: 96
  width: 888
  height: 1158
placements:
  quote:
    x: 96
    y: 650
    width: 888
    height: 360
    anchor: bottom-left
  author:
    x: 96
    y: 500
    width: 888
    height: 40
    anchor: bottom-left
  source:
    x: 96
    y: 450
    width: 888
    height: 36
    anchor: bottom-left
elements:
  - type: text
    text: "Good design is visible structure made quietly inevitable."
  - type: text
    text: "— Acme Studio"
  - type: text
    text: "Design Principles Notes, 2026"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["recipe", "validate", str(recipe_path), "--json"])
    assert result.exit_code == 1, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "embedded author must match content fixture" in payload["errors"]


def test_recipe_validate_reports_invalid_geometry_and_options(tmp_path):
    content_path = tmp_path / "content.yaml"
    content_path.write_text('quote: "Hello"\nauthor: "Acme"\nsource: "Notes"\n', encoding="utf-8")
    recipe_path = tmp_path / "recipe.yaml"
    recipe_path.write_text(
        f"""
contract_version: 1
brand: acme
artifact: social-quote
content: {content_path}
variants:
  format: social-quote-landscape
  accent_edge: left
page:
  width: 1200
  height: 1200
safe_zone:
  x: 96
  y: 96
  width: 1200
  height: 1158
placements:
  quote:
    x: 50
    y: 650
    width: 1200
    height: 360
    anchor: center
""".strip()
        + "\n",
        encoding="utf-8",
    )

    recipe = load_recipe(recipe_path)
    errors = validate_recipe(recipe, recipe_path=recipe_path)
    assert "page must be 1080x1350 for social-quote" in errors
    assert "safe_zone must fit inside the page" in errors
    assert "placements.quote.anchor must be bottom-left or top-left" in errors
    assert "placements.quote must fit inside safe_zone" in errors
    assert "variants.format must be one of: social-quote-portrait" in errors
    assert "variants.accent_edge must be one of: bottom" in errors
