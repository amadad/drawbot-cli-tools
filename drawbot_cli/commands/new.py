from __future__ import annotations

from pathlib import Path

import typer

_TEMPLATE = '''newPage(612, 792)
fill(1)
rect(0, 0, width(), height())

fill(0)
font("Helvetica")
fontSize(48)
text("{title}", (72, height() - 120))
'''


def new(
    name: str = typer.Argument(..., help="Name for the new script"),
    directory: Path = typer.Option(Path("."), "--dir", "-d", file_okay=False, dir_okay=True, help="Output directory"),
):
    """Create a tiny DrawBot script scaffold."""
    filename = name if name.endswith(".py") else f"{name}.py"
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename

    if path.exists():
        typer.secho(f"File already exists: {path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    title = Path(filename).stem.replace("_", " ").replace("-", " ").title()
    path.write_text(_TEMPLATE.format(title=title), encoding="utf-8")
    typer.echo(str(path))
