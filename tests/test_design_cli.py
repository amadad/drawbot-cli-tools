from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from drawbot_cli.app import app
from drawbot_cli.design import explain_design, load_design, normalize_design, validate_design


runner = CliRunner()


def test_design_validate_and_explain_json():
    validate = runner.invoke(app, ["design", "validate", "DESIGN.md", "--json"])
    explain = runner.invoke(app, ["design", "explain", "DESIGN.md", "--json"])

    assert validate.exit_code == 0, validate.stdout
    validate_payload = json.loads(validate.stdout)
    assert validate_payload["ok"] is True
    assert validate_payload["design"]["brand"] == {"id": "acme", "name": "Acme"}
    assert validate_payload["design"]["composition"]["canvas"] == {"width": 1080, "height": 1350}

    explanation = json.loads(explain.stdout)
    assert explanation["palette"]["accent"] == "#F59E0B"
    assert explanation["type"]["quote_font"] == "Helvetica-Bold"
    assert explanation["type"]["source_font"] == "Helvetica"
    assert explanation["type"]["source_size"] == 28
    assert explanation["composition"]["spacing"]["quote_gap"] == 36
    assert explanation["prose_summary"]["guidance"].startswith("The contract exists")


def test_design_validate_reports_missing_required_tokens(tmp_path):
    design_path = tmp_path / "DESIGN.md"
    design_path.write_text(
        "# Broken\n\n## Scope\n\n```yaml\ncontract_version: 1\nbrand:\n  id: acme\n  name: Acme\nartifact:\n  family: social-quote\n  command_path: drawbot spec render demo.yaml -o out.pdf\ninputs:\n  recipe: recipe.yaml\n  content_example: content.yaml\n  review_rubric: review.yaml\ncanvas:\n  width: 1080\n  height: 1350\ntokens:\n  colors:\n    background: '#000000'\n  typography:\n    quote_font: Helvetica-Bold\n    quote_size: 72\n    attribution_font: Helvetica\n    attribution_size: 32\n  spacing:\n    outer_padding: 96\nrules: []\n```\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["design", "validate", str(design_path)])

    assert result.exit_code == 1
    assert "missing tokens.colors.panel" in result.stderr
    assert "missing tokens.colors.accent" in result.stderr
    assert "missing tokens.spacing.quote_gap" in result.stderr


def test_design_explain_plain_text_includes_full_typography_contract():
    result = runner.invoke(app, ["design", "explain", "DESIGN.md"])

    assert result.exit_code == 0, result.stdout
    assert "source_font=Helvetica" in result.stdout
    assert "source_size=28" in result.stdout


def test_design_loader_normalizes_stable_model():
    document = load_design(Path("DESIGN.md").resolve())

    errors = validate_design(document)
    normalized = normalize_design(document)
    explanation = explain_design(document)

    assert errors == []
    assert normalized["rules"][0] == "recipe must target artifact.family == social-quote"
    assert normalized["prose"]["scope"].startswith("- Brand: `acme`")
    assert explanation["artifact"]["command_path"] == "drawbot spec render fixtures/brand_artifacts/social-quote.recipe.yaml -o out/social-quote.pdf"
