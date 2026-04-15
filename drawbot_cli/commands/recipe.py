from __future__ import annotations

import json
from pathlib import Path

import typer

from drawbot_cli.recipes import explain_recipe, load_recipe, validate_recipe


recipe_app = typer.Typer(help="Validate and explain narrow artifact recipes.")


@recipe_app.command("validate")
def recipe_validate(
    recipe_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to a YAML recipe"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON"),
):
    """Validate a social-quote recipe without rendering it."""
    recipe_path = recipe_file.resolve()
    recipe = load_recipe(recipe_path)
    errors = validate_recipe(recipe, recipe_path=recipe_path)

    if as_json:
        typer.echo(json.dumps({"ok": not errors, "errors": errors}, indent=2, sort_keys=True))
        if errors:
            raise typer.Exit(1)
        return

    if errors:
        for error in errors:
            typer.secho(error, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    typer.echo("ok")


@recipe_app.command("explain")
def recipe_explain(
    recipe_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to a YAML recipe"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON"),
):
    """Explain the resolved shape of a social-quote recipe."""
    try:
        recipe = load_recipe(recipe_file.resolve())
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    explanation = explain_recipe(recipe)

    if as_json:
        typer.echo(json.dumps(explanation, indent=2, sort_keys=True))
        return

    typer.echo(f"artifact={explanation['artifact']}")
    typer.echo(f"brand={explanation['brand']}")
    typer.echo(
        f"page={explanation['page']['width']}x{explanation['page']['height']} ({explanation['page']['aspect_ratio']})"
    )
    typer.echo(f"content={', '.join(explanation['content_fields'])}")
    typer.echo(
        "safe_zone="
        f"{explanation['safe_zone']['x']},"
        f"{explanation['safe_zone']['y']},"
        f"{explanation['safe_zone']['width']},"
        f"{explanation['safe_zone']['height']}"
    )
    typer.echo(f"placements={', '.join(explanation['placements'])}")
    typer.echo("variants=" + ", ".join(f"{key}={value}" for key, value in explanation['variants'].items()))
