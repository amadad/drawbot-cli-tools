from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from drawbot_cli.app import app
from drawbot_cli.spec.core import load_spec, validate_spec


runner = CliRunner()
FIXTURE_ROOT = Path("fixtures/brand_artifacts")


def test_create_social_quote_generates_deterministic_specs_and_manifest(tmp_path):
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "create",
            "social-quote",
            "--design",
            "DESIGN.md",
            "--recipe",
            str(FIXTURE_ROOT / "social-quote.recipe.yaml"),
            "--data",
            str(FIXTURE_ROOT / "social-quote.content.yaml"),
            "-n",
            "4",
            "-o",
            str(out_dir),
            "--seed",
            "7",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    manifest_path = Path(payload["manifest"])
    spec_paths = [Path(path) for path in payload["specs"]]

    assert manifest_path.exists()
    assert len(spec_paths) == 4
    assert [path.name for path in spec_paths] == [
        "social-quote-01.yaml",
        "social-quote-02.yaml",
        "social-quote-03.yaml",
        "social-quote-04.yaml",
    ]

    first_pass = [path.read_text(encoding="utf-8") for path in spec_paths]

    rerun = runner.invoke(
        app,
        [
            "create",
            "social-quote",
            "--design",
            "DESIGN.md",
            "--recipe",
            str(FIXTURE_ROOT / "social-quote.recipe.yaml"),
            "--data",
            str(FIXTURE_ROOT / "social-quote.content.yaml"),
            "-n",
            "4",
            "-o",
            str(out_dir),
            "--seed",
            "7",
        ],
    )
    assert rerun.exit_code == 0, rerun.stdout
    second_pass = [path.read_text(encoding="utf-8") for path in spec_paths]
    assert first_pass == second_pass

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifact"] == "social-quote"
    assert manifest["count"] == 4
    assert [variant["layout"] for variant in manifest["variants"]] == [
        "balanced",
        "top-heavy",
        "middle-stack",
        "lower-anchor",
    ]

    for spec_path in spec_paths:
        spec = load_spec(spec_path)
        assert validate_spec(spec) == []
        assert spec["page"] == {"width": 1080, "height": 1350, "background": "#0F172A"}
        assert spec["elements"][0]["fill"] == "#111827"
        assert spec["elements"][1]["fill"] == "#F59E0B"
        assert spec["elements"][2]["text"] == "Good design is visible structure made quietly inevitable."


def test_create_social_quote_accepts_json_content_input(tmp_path):
    content_path = tmp_path / "quote.json"
    content_path.write_text(
        json.dumps({"quote": "Design is editing.", "author": "Acme", "source": "Workshop"}),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "create",
            "social-quote",
            "--design",
            "DESIGN.md",
            "--recipe",
            str(FIXTURE_ROOT / "social-quote.recipe.yaml"),
            "--data",
            str(content_path),
            "-n",
            "3",
            "-o",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    spec_paths = sorted(out_dir.glob("social-quote-*.yaml"))
    assert len(spec_paths) == 3
    texts = [yaml.safe_load(path.read_text(encoding="utf-8"))["elements"][2]["text"] for path in spec_paths]
    assert texts == ["Design is editing."] * 3
