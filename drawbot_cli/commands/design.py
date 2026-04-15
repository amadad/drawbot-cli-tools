from __future__ import annotations

import json
from pathlib import Path

import typer

from drawbot_cli.design import explain_design, load_design, normalize_design, validate_design


design_app = typer.Typer(help="Load and inspect a DESIGN.md contract.")


@design_app.command("validate")
def design_validate(
    design_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to DESIGN.md"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON"),
):
    """Validate a DESIGN.md contract."""
    try:
        document = load_design(design_file.resolve())
        errors = validate_design(document)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    if errors:
        if as_json:
            typer.echo(json.dumps({"errors": errors, "ok": False}, indent=2, sort_keys=True))
        else:
            for error in errors:
                typer.secho(error, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps({"design": normalize_design(document), "ok": True}, indent=2, sort_keys=True))
    else:
        typer.echo("ok")


@design_app.command("explain")
def design_explain(
    design_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to DESIGN.md"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON"),
):
    """Explain the effective design tokens and prose summary."""
    try:
        explanation = explain_design(load_design(design_file.resolve()))
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    if as_json:
        typer.echo(json.dumps(explanation, indent=2, sort_keys=True))
        return

    typer.echo(f"brand={explanation['brand']['id']}")
    typer.echo(f"artifact={explanation['artifact']['family']}")
    typer.echo("palette=" + ", ".join(f"{key}={value}" for key, value in explanation["palette"].items()))
    typer.echo(
        "type="
        + ", ".join(
            f"{key}={value}"
            for key, value in (
                ("quote_font", explanation["type"]["quote_font"]),
                ("quote_size", explanation["type"]["quote_size"]),
                ("attribution_font", explanation["type"]["attribution_font"]),
                ("attribution_size", explanation["type"]["attribution_size"]),
                ("source_font", explanation["type"]["source_font"]),
                ("source_size", explanation["type"]["source_size"]),
            )
        )
    )
    typer.echo(
        "composition="
        + ", ".join(
            (
                f"canvas={explanation['composition']['canvas']['width']}x{explanation['composition']['canvas']['height']}",
                f"outer_padding={explanation['composition']['spacing']['outer_padding']}",
                f"quote_gap={explanation['composition']['spacing']['quote_gap']}",
            )
        )
    )
    for key, value in explanation["prose_summary"].items():
        typer.echo(f"{key}={value}")
