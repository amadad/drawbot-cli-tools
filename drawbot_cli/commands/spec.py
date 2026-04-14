from __future__ import annotations

import json
from pathlib import Path

import typer

from drawbot_cli.runtime import skia
from drawbot_cli.spec.core import explain_spec, load_spec, render_spec, validate_spec


spec_app = typer.Typer(help="Render and inspect simple YAML drawing specs.")


@spec_app.command("render")
def spec_render(
    spec_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to a YAML spec"),
    output: Path | None = typer.Option(None, "--output", "-o", dir_okay=False, help="Optional output file"),
):
    """Render a YAML spec with the vendored drawbot-skia runtime."""
    try:
        rendered = render_spec(spec_file.resolve(), output.resolve() if output else None)
    except skia.DrawbotSkiaUnavailableError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    typer.echo(str(rendered))


@spec_app.command("validate")
def spec_validate(spec_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to a YAML spec")):
    """Validate a YAML spec without rendering it."""
    spec = load_spec(spec_file.resolve())
    errors = validate_spec(spec)
    if errors:
        for error in errors:
            typer.secho(error, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    typer.echo("ok")


@spec_app.command("explain")
def spec_explain(
    spec_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to a YAML spec"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON"),
):
    """Explain the resolved shape of a YAML spec."""
    explanation = explain_spec(load_spec(spec_file.resolve()))
    if as_json:
        typer.echo(json.dumps(explanation, indent=2))
        return

    typer.echo(f"page={explanation['page']['width']}x{explanation['page']['height']}")
    typer.echo(f"elements={explanation['element_count']}")
    typer.echo(f"types={', '.join(explanation['element_types'])}")
    typer.echo(f"output={explanation['output']}")
