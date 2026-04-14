"""
DrawBot CLI - Main entry point.

Commands:
    render      Render a DrawBot script to PDF/PNG/SVG
    new         Scaffold a new poster from template
    preview     Quick render and open
    watch       Watch script and re-render on changes
    from-spec   Render from YAML specification
    templates   List and show available templates
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

from drawbot_backend import DRAWBOT_BACKEND_ENV_VAR, SUPPORTED_BACKENDS, resolve_backend

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

app = typer.Typer(
    name="drawbot",
    help="DrawBot design system CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()

# Project paths
REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_DIR = REPO_ROOT / "lib"
OUTPUT_DIR = REPO_ROOT / "output"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def ensure_output_dir():
    """Ensure output directory exists."""
    OUTPUT_DIR.mkdir(exist_ok=True)


def run_drawbot_script(
    script_path: Path,
    output_path: Optional[Path] = None,
    backend: Optional[str] = None,
) -> bool:
    """
    Execute a DrawBot script.

    Returns True on success, False on failure.
    """
    if not script_path.exists():
        console.print(f"[red]Error:[/red] Script not found: {script_path}")
        return False

    env = {
        **os.environ,
        "PYTHONPATH": str(LIB_DIR),
    }

    if output_path:
        env["DRAWBOT_OUTPUT"] = str(output_path)

    if backend:
        env[DRAWBOT_BACKEND_ENV_VAR] = backend

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            console.print(f"[red]Error running script:[/red]")
            if result.stderr:
                console.print(result.stderr)
            return False

        if result.stdout:
            console.print(result.stdout)

        return True

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return False


@app.command()
def render(
    script: Path = typer.Argument(..., help="Path to DrawBot script"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path"),
    output_format: str = typer.Option("pdf", "--format", "-f", help="Output format: pdf, png, svg"),
    open_file: bool = typer.Option(False, "--open", help="Open file after rendering"),
    backend: Optional[str] = typer.Option(None, "--backend", help=f"Backend: {', '.join(SUPPORTED_BACKENDS)}"),
):
    """
    Render a DrawBot script to PDF/PNG/SVG.

    Example:
        drawbot render examples/minimal_poster_example.py
        drawbot render my_poster.py --output poster.pdf --open
    """
    ensure_output_dir()

    script = script.resolve()

    backend_info = resolve_backend(selected=backend)
    console.print(f"[blue]Rendering:[/blue] {script.name} [dim]({backend_info.name} via {backend_info.source})[/dim]")

    success = run_drawbot_script(script, output, backend=backend_info.name)

    if success:
        # Try to find the output file
        if output:
            out_file = output
        else:
            # Look for most recent file in output/
            outputs = sorted(OUTPUT_DIR.glob(f"*.{output_format}"), key=lambda p: p.stat().st_mtime, reverse=True)
            out_file = outputs[0] if outputs else None

        if out_file and out_file.exists():
            console.print(f"[green]Saved:[/green] {out_file}")

            if open_file:
                _open_file(out_file)
        else:
            console.print("[green]Done[/green]")
    else:
        raise typer.Exit(1)


@app.command()
def preview(
    script: Path = typer.Argument(..., help="Path to DrawBot script"),
    backend: Optional[str] = typer.Option(None, "--backend", help=f"Backend: {', '.join(SUPPORTED_BACKENDS)}"),
):
    """
    Quick render and open - for rapid iteration.

    Example:
        drawbot preview my_poster.py
    """
    ensure_output_dir()

    script = script.resolve()

    backend_info = resolve_backend(selected=backend)
    console.print(f"[blue]Preview:[/blue] {script.name} [dim]({backend_info.name} via {backend_info.source})[/dim]")

    success = run_drawbot_script(script, backend=backend_info.name)

    if success:
        # Find most recent PDF
        outputs = sorted(OUTPUT_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if outputs:
            _open_file(outputs[0])
        else:
            # Try PNG
            outputs = sorted(OUTPUT_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
            if outputs:
                _open_file(outputs[0])
    else:
        raise typer.Exit(1)


@app.command()
def watch(
    script: Path = typer.Argument(..., help="Path to DrawBot script"),
    open_first: bool = typer.Option(True, "--open/--no-open", help="Open file on first render"),
    backend: Optional[str] = typer.Option(None, "--backend", help=f"Backend: {', '.join(SUPPORTED_BACKENDS)}"),
):
    """
    Watch script and re-render on changes.

    Example:
        drawbot watch my_poster.py
        drawbot watch my_poster.py --no-open
    """
    try:
        from watchfiles import watch as watchfiles_watch
    except ImportError:
        console.print("[red]Error:[/red] watchfiles not installed. Run: uv pip install watchfiles")
        raise typer.Exit(1)

    ensure_output_dir()
    script = script.resolve()

    if not script.exists():
        console.print(f"[red]Error:[/red] Script not found: {script}")
        raise typer.Exit(1)

    backend_info = resolve_backend(selected=backend)
    console.print(f"[blue]Watching:[/blue] {script.name} [dim]({backend_info.name} via {backend_info.source})[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    # Initial render
    success = run_drawbot_script(script, backend=backend_info.name)

    if success and open_first:
        outputs = sorted(OUTPUT_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if outputs:
            _open_file(outputs[0])

    # Watch for changes
    try:
        for changes in watchfiles_watch(script.parent, watch_filter=lambda _, p: p == str(script)):
            console.print(f"\n[yellow]Changed:[/yellow] {script.name}")
            success = run_drawbot_script(script, backend=backend_info.name)
            if success:
                console.print("[green]Rendered[/green]")
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching[/dim]")


@app.command()
def new(
    name: str = typer.Argument(..., help="Name for the new poster script"),
    page_format: str = typer.Option("letter", "--format", "-f", help="Page format: letter, a4, tabloid"),
    template: str = typer.Option("minimal", "--template", "-t", help="Template: minimal, grid, text"),
    output_dir: Optional[Path] = typer.Option(None, "--dir", "-d", help="Output directory"),
):
    """
    Scaffold a new poster script from template.

    Example:
        drawbot new my_poster
        drawbot new concert_flyer --format a4 --template grid
    """
    if output_dir is None:
        output_dir = Path.cwd()

    output_dir = output_dir.resolve()

    # Ensure .py extension
    if not name.endswith(".py"):
        filename = f"{name}.py"
    else:
        filename = name
        name = name[:-3]

    output_path = output_dir / filename

    if output_path.exists():
        console.print(f"[red]Error:[/red] File already exists: {output_path}")
        raise typer.Exit(1)

    # Get template content
    template_content = _get_template(template, name, page_format)

    output_path.write_text(template_content)

    console.print(f"[green]Created:[/green] {output_path}")
    console.print(f"\n[dim]Run with:[/dim] drawbot render {filename}")


# Templates subcommand group
templates_app = typer.Typer(help="Manage poster templates")
app.add_typer(templates_app, name="templates")

# Import and add evolve subcommand
from .evolve import app as evolve_app
app.add_typer(evolve_app, name="evolve")


@templates_app.command("list")
def templates_list():
    """List available templates."""
    from rich.table import Table

    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    table.add_row("minimal", "Clean starter with title, subtitle, body text")
    table.add_row("grid", "Grid-heavy layout demonstrating 12-column system")
    table.add_row("text", "Text-focused layout with multiple text blocks")

    console.print(table)


@templates_app.command("show")
def templates_show(
    name: str = typer.Argument(..., help="Template name to preview"),
):
    """Show template code."""
    content = _get_template(name, "example", "letter")

    syntax = Syntax(content, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"Template: {name}"))


def _get_template(template: str, name: str, format: str) -> str:
    """Get template content with substitutions."""
    templates = {
        "minimal": '''"""
{name} - Generated with DrawBot CLI
"""

import sys
from pathlib import Path

# Design system imports
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import drawBot as db
from drawbot_design_system import (
    POSTER_SCALE,
    setup_poster_page,
    draw_wrapped_text,
    get_output_path,
    get_color_palette,
)
from drawbot_grid import Grid

# Page setup
WIDTH, HEIGHT, MARGIN = setup_poster_page("{format}")

# Grid setup (12 columns, 8 rows)
grid = Grid.from_margins(
    (-MARGIN, -MARGIN, -MARGIN, -MARGIN),
    column_subdivisions=12,
    row_subdivisions=8,
)

# Colors
palette = get_color_palette("dark")
scale = POSTER_SCALE

# Background
db.fill(*palette["background"])
db.rect(0, 0, WIDTH, HEIGHT)

# Header bar
db.fill(*palette["primary"])
x, y = grid[(0, 6)]
w, h = grid * (12, 2)
db.rect(x, y, w, h)

# Title
db.fill(*palette["text"])
db.font("Helvetica Bold")
db.fontSize(scale.title)
tx, ty = grid[(1, 6)]
db.text("TITLE HERE", (tx, ty + h/2))

# Body text
body = "Your body text goes here. Replace this with your actual content."
bx, by = grid[(1, 1)]
bw, bh = grid * (10, 4)
draw_wrapped_text(body, bx, by + bh, bw, bh, "Helvetica", scale.body)

# Save
db.saveImage(str(get_output_path("{name}.pdf")))
print(f"Saved: {name}.pdf")
''',
        "grid": '''"""
{name} - Grid-focused layout
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import drawBot as db
from drawbot_design_system import (
    POSTER_SCALE,
    setup_poster_page,
    get_output_path,
)
from drawbot_grid import Grid

WIDTH, HEIGHT, MARGIN = setup_poster_page("{format}")

grid = Grid.from_margins(
    (-MARGIN, -MARGIN, -MARGIN, -MARGIN),
    column_subdivisions=12,
    row_subdivisions=8,
)

scale = POSTER_SCALE

# Background
db.fill(0.95)
db.rect(0, 0, WIDTH, HEIGHT)

# Draw grid for reference (remove in production)
db.stroke(0.8)
db.strokeWidth(0.5)
db.fill(None)
grid.draw()

# Header spanning full width
db.fill(0.1)
db.stroke(None)
x, y = grid[(0, 7)]
w, h = grid * (12, 1)
db.rect(x, y, w, h)

# Left column (4 cols)
db.fill(0.3)
x, y = grid[(0, 0)]
w, h = grid * (4, 6)
db.rect(x, y, w, h)

# Right content area (8 cols)
db.fill(0.6)
x, y = grid[(4, 0)]
w, h = grid * (8, 6)
db.rect(x, y, w, h)

# Title
db.fill(1)
db.font("Helvetica Bold")
db.fontSize(scale.h1)
tx, ty = grid[(1, 7)]
_, th = grid * (1, 1)
db.text("GRID LAYOUT", (tx, ty + th/3))

db.saveImage(str(get_output_path("{name}.pdf")))
print(f"Saved: {name}.pdf")
''',
        "text": '''"""
{name} - Text-focused layout
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import drawBot as db
from drawbot_design_system import (
    POSTER_SCALE,
    setup_poster_page,
    draw_wrapped_text,
    get_output_path,
)
from drawbot_grid import Grid

WIDTH, HEIGHT, MARGIN = setup_poster_page("{format}")

grid = Grid.from_margins(
    (-MARGIN, -MARGIN, -MARGIN, -MARGIN),
    column_subdivisions=12,
    row_subdivisions=12,
)

scale = POSTER_SCALE

# Background
db.fill(1)
db.rect(0, 0, WIDTH, HEIGHT)

# Title
db.fill(0)
db.font("Helvetica Bold")
db.fontSize(scale.title)
tx, ty = grid[(0, 10)]
db.text("HEADLINE", (tx, ty))

# Subtitle
db.font("Helvetica")
db.fontSize(scale.h2)
sx, sy = grid[(0, 9)]
db.text("A compelling subtitle goes here", (sx, sy))

# Body paragraphs
body1 = """First paragraph of body text. This template is designed
for text-heavy layouts like articles, reports, or informational posters."""

body2 = """Second paragraph continues here. The grid system ensures
consistent spacing and alignment across all elements."""

db.fill(0.2)
bx, by = grid[(0, 4)]
bw, bh = grid * (12, 4)
draw_wrapped_text(body1, bx, by + bh, bw, bh, "Helvetica", scale.body)

bx2, by2 = grid[(0, 0)]
draw_wrapped_text(body2, bx2, by2 + bh, bw, bh, "Helvetica", scale.body)

db.saveImage(str(get_output_path("{name}.pdf")))
print(f"Saved: {name}.pdf")
''',
    }

    if template not in templates:
        template = "minimal"

    return templates[template].format(name=name, format=format)


def _open_file(path: Path):
    """Open file with system default application."""
    system = platform.system()

    try:
        if system == "Darwin":
            subprocess.run(["open", str(path)], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(path)], check=True)
        elif system == "Windows":
            os.startfile(path)  # Native Windows API, no shell needed
    except Exception as e:
        console.print(f"[yellow]Could not open file:[/yellow] {e}")


@app.command("from-spec")
def from_spec(
    spec_file: Path = typer.Argument(..., help="YAML spec file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path"),
    open_file: bool = typer.Option(False, "--open", help="Open after rendering"),
    backend: Optional[str] = typer.Option(None, "--backend", help=f"Backend: {', '.join(SUPPORTED_BACKENDS)}"),
):
    """
    Render from YAML specification file.

    Example:
        drawbot from-spec poster.yaml
        drawbot from-spec poster.yaml --output my_poster.pdf --open
    """
    try:
        from .spec import render_from_spec
    except ImportError:
        console.print("[red]Error:[/red] YAML spec support not available. Install pyyaml and pydantic.")
        raise typer.Exit(1)

    spec_file = spec_file.resolve()

    if not spec_file.exists():
        console.print(f"[red]Error:[/red] Spec file not found: {spec_file}")
        raise typer.Exit(1)

    backend_info = resolve_backend(selected=backend)
    console.print(f"[blue]Rendering spec:[/blue] {spec_file.name} [dim]({backend_info.name} via {backend_info.source})[/dim]")

    try:
        out_path = render_from_spec(spec_file, output, backend=backend_info.name)
        console.print(f"[green]Saved:[/green] {out_path}")

        if open_file:
            _open_file(out_path)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
