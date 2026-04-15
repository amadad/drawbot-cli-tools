from __future__ import annotations

import json
from pathlib import Path

import typer

from drawbot_cli.create import create_social_quote_specs
from drawbot_cli.design import load_design


create_app = typer.Typer(help="Generate internal specs from design, recipe, and content inputs.")


@create_app.command("social-quote")
def create_social_quote(
    design_file: Path = typer.Option(..., "--design", exists=True, dir_okay=False, help="Path to DESIGN.md"),
    recipe_file: Path = typer.Option(..., "--recipe", exists=True, dir_okay=False, help="Path to recipe YAML"),
    data_file: Path = typer.Option(..., "--data", exists=True, dir_okay=False, help="Path to content YAML/JSON"),
    count: int = typer.Option(4, "-n", min=1, max=4, help="Number of variants to generate"),
    output_dir: Path = typer.Option(..., "-o", "--output", file_okay=False, help="Directory for generated specs"),
    seed: int = typer.Option(1, "--seed", help="Deterministic seed for variant planning"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON summary"),
):
    """Create deterministic social-quote internal specs."""
    try:
        result = create_social_quote_specs(
            design_document=load_design(design_file.resolve()),
            recipe_path=recipe_file.resolve(),
            data_path=data_file.resolve(),
            output_dir=output_dir.resolve(),
            count=count,
            seed=seed,
        )
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    payload = {
        "ok": True,
        "manifest": str(result.manifest_path),
        "specs": [str(path) for path in result.spec_paths],
        "outputs": [str(path) for path in result.output_paths],
        "rendered": len(result.output_paths),
        "failed_lint": sum(1 for variant in result.variants if not variant.lint["ok"]),
    }
    if as_json:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    typer.echo(f"manifest={result.manifest_path}")
    for spec_path in result.spec_paths:
        typer.echo(f"spec={spec_path}")
    for output_path in result.output_paths:
        typer.echo(f"output={output_path}")
