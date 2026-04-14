from __future__ import annotations

import typer

from drawbot_cli.runtime import skia


def doctor():
    """Check that the vendored drawbot-skia runtime is importable."""
    typer.echo(f"vendor_root={skia.vendor_root()}")
    typer.echo(f"vendor_src={skia.vendor_src()}")

    try:
        module = skia.get_drawbot_module()
    except skia.DrawbotSkiaUnavailableError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"module={module.__name__}")
    typer.echo(f"version={skia.get_version()}")
    typer.echo("status=ok")
