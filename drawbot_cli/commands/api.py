from __future__ import annotations

import json

import typer

from drawbot_cli.runtime import skia


api_app = typer.Typer(help="Inspect the vendored drawbot-skia surface.")


@api_app.command("list")
def api_list(as_json: bool = typer.Option(False, "--json", help="Emit JSON")):
    """List exported symbols from drawbot_skia.drawbot."""
    try:
        symbols = skia.list_symbols()
    except skia.DrawbotSkiaUnavailableError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    if as_json:
        typer.echo(json.dumps(symbols, indent=2))
        return

    for symbol in symbols:
        typer.echo(symbol)


@api_app.command("show")
def api_show(symbol: str = typer.Argument(..., help="Exported symbol name"), as_json: bool = typer.Option(False, "--json", help="Emit JSON")):
    """Show details for one exported symbol."""
    try:
        details = skia.describe_symbol(symbol)
    except skia.DrawbotSkiaUnavailableError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    except KeyError:
        typer.secho(f"Unknown symbol: {symbol}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if as_json:
        typer.echo(json.dumps(details, indent=2))
        return

    typer.echo(f"name={details['name']}")
    typer.echo(f"kind={details['kind']}")
    typer.echo(f"module={details['module']}")
    typer.echo(f"callable={details['callable']}")
    if details["signature"]:
        typer.echo(f"signature={details['signature']}")
    if details["doc"]:
        typer.echo(f"doc={details['doc']}")


@api_app.command("gaps")
def api_gaps(as_json: bool = typer.Option(False, "--json", help="Emit JSON")):
    """Show known upstream gaps that shape this CLI."""
    gaps = skia.known_gaps()

    if as_json:
        typer.echo(json.dumps(gaps, indent=2))
        return

    for gap in gaps:
        typer.echo(f"{gap['feature']}: {gap['status']} — {gap['note']}")
