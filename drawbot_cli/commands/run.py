from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from drawbot_cli.runtime import skia


def run(
    script: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to a Python drawing script"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", dir_okay=False, help="Optional output file path"),
):
    """Run a script through the vendored drawbot-skia runtime."""
    try:
        runner_main = skia.get_runner_main()
    except skia.DrawbotSkiaUnavailableError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc

    script = script.resolve()
    args = [str(script)]

    if output is not None:
        output = output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        args.append(str(output))

    runner_main(args)

    if output is not None:
        typer.echo(str(output))
