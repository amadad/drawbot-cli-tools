from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from drawbot_cli.app import app
from drawbot_cli.spec.core import load_spec, validate_spec


runner = CliRunner()
FIXTURE_ROOT = Path("fixtures/brand_artifacts")


def test_social_quote_workflow_smoke_proves_fixture_driven_pipeline(tmp_path):
    out_dir = tmp_path / "workflow-out"

    design_validate = runner.invoke(app, ["design", "validate", "DESIGN.md"])
    recipe_validate = runner.invoke(app, ["recipe", "validate", str(FIXTURE_ROOT / "social-quote.recipe.yaml")])
    design_explain = runner.invoke(app, ["design", "explain", "DESIGN.md", "--json"])
    recipe_explain = runner.invoke(app, ["recipe", "explain", str(FIXTURE_ROOT / "social-quote.recipe.yaml"), "--json"])
    create_result = runner.invoke(
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
            "2",
            "-o",
            str(out_dir),
            "--seed",
            "5",
            "--json",
        ],
    )

    assert design_validate.exit_code == 0, design_validate.stdout
    assert recipe_validate.exit_code == 0, recipe_validate.stdout
    assert json.loads(design_explain.stdout)["artifact"]["family"] == "social-quote"
    assert json.loads(recipe_explain.stdout)["content_fields"] == ["quote", "author", "source"]

    assert create_result.exit_code == 0, create_result.stdout
    payload = json.loads(create_result.stdout)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert payload["manifest"] == str((out_dir / "manifest.json").resolve())
    assert manifest["inputs"]["design"].endswith("DESIGN.md")
    assert manifest["inputs"]["recipe"].endswith("fixtures/brand_artifacts/social-quote.recipe.yaml")
    assert manifest["inputs"]["data"].endswith("fixtures/brand_artifacts/social-quote.content.yaml")
    assert manifest["summary"] == {"total": 2, "rendered": 2, "failed_lint": 0}
    assert [variant["spec"] for variant in manifest["variants"]] == ["social-quote-01.yaml", "social-quote-02.yaml"]
    assert [variant["output"] for variant in manifest["variants"]] == ["social-quote-01.pdf", "social-quote-02.pdf"]
    assert all((out_dir / variant["spec"]).exists() for variant in manifest["variants"])
    assert all((out_dir / variant["output"]).exists() for variant in manifest["variants"])



def test_create_social_quote_generates_deterministic_specs_renders_outputs_and_manifest(tmp_path):
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
    output_paths = [Path(path) for path in payload["outputs"]]

    assert manifest_path.exists()
    assert len(spec_paths) == 4
    assert len(output_paths) == 4
    assert payload["rendered"] == 4
    assert payload["failed_lint"] == 0
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
    assert manifest["summary"] == {"total": 4, "rendered": 4, "failed_lint": 0}
    assert [variant["layout"] for variant in manifest["variants"]] == [
        "balanced",
        "top-heavy",
        "middle-stack",
        "lower-anchor",
    ]

    for spec_path, output_path, variant in zip(spec_paths, output_paths, manifest["variants"], strict=True):
        spec = load_spec(spec_path)
        assert validate_spec(spec) == []
        assert output_path.exists()
        assert variant["rendered"] is True
        assert variant["output"] == output_path.name
        assert variant["lint"]["ok"] is True
        assert variant["lint"]["issues"] == []
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


def test_create_social_quote_reports_machine_readable_lint_failures_and_skips_render(tmp_path):
    content_path = tmp_path / "broken-content.yaml"
    content_path.write_text("quote: Still deterministic\nauthor: Acme\n", encoding="utf-8")
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
            "1",
            "-o",
            str(out_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["rendered"] == 0
    assert payload["failed_lint"] == 1

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"] == {"total": 1, "rendered": 0, "failed_lint": 1}
    variant = manifest["variants"][0]
    assert variant["rendered"] is False
    assert variant["output"] is None
    assert variant["lint"]["ok"] is False
    assert variant["lint"]["error_count"] >= 1
    assert any(issue["code"] == "content.missing_source" for issue in variant["lint"]["issues"])
    assert (out_dir / variant["spec"]).exists()
    assert not list(out_dir.glob("*.pdf"))
