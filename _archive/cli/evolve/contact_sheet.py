"""
Contact sheet generator for evolutionary selection.

Creates multi-page PDF with numbered form candidates in a grid layout,
allowing humans to review and select winners by ID.
"""

import math
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from .genome import FormGenome
from .parameters import DEFAULT_SPECS, ParameterSpec
from .generators import GENERATORS
from .render import (
    _accent_scale,
    _dot_scale,
    _draw_path_mark,
    _layer_style,
    resolve_render_plan,
)


# Lazy DrawBot import
_db = None


def _get_db():
    """Lazy-load drawBot on first use."""
    global _db
    if _db is None:
        try:
            import drawBot as db_module

            _db = db_module
        except ImportError:
            raise ImportError(
                "drawBot is required for contact sheet generation.\n"
                "Install with: uv sync --extra drawbot"
            )
    return _db


def _render_dot_field_contact(db, form_data: Dict[str, Any], style: Dict[str, Any]):
    """Render a dot field in contact sheet."""
    fill_color = style.get("fill_color", [0.0, 0.0, 0.0])
    dots = form_data.get("dots", [])
    dot_scale = _dot_scale(style)

    db.fill(*fill_color)
    db.stroke(None)

    for x, y, radius in dots:
        radius *= dot_scale
        db.oval(x - radius / 2, y - radius / 2, radius, radius)


def _render_accent_nodes_contact(db, form_data: Dict[str, Any], style: Dict[str, Any]):
    """Render accent nodes in contact sheet."""
    fill_color = style.get("fill_color", [0.0, 0.0, 0.0])
    nodes = form_data.get("nodes", [])
    dot_scale = _accent_scale(style)

    db.fill(*fill_color)
    db.stroke(None)

    for x, y, radius in nodes:
        radius *= dot_scale
        db.oval(x - radius / 2, y - radius / 2, radius, radius)


def _render_layered_form_contact(db, form_data: Dict[str, Any], style: Dict[str, Any]):
    """Render a layered compound form in contact sheet context."""
    shadow_color = style.get("shadow_color", [0.85, 0.85, 0.88])
    shadow_strength = style.get("_shadow_strength", 0.0)

    for layer in form_data.get("layers", []):
        layer_name = layer.get("name", "")
        layer_style = _layer_style(style, layer)

        if layer_name == "shadow":
            path = layer.get("path")
            if path and shadow_strength > 0:
                fill_color = layer.get("fill_color", shadow_color)
                db.fill(*fill_color)
                db.stroke(None)
                db.drawPath(path)

        elif layer_name == "outline":
            path = layer.get("path")
            if path:
                _draw_path_mark(
                    db,
                    path,
                    layer_style,
                    filled=False,
                    base_width=layer.get(
                        "stroke_weight", style.get("stroke_width", 1.5)
                    ),
                )

        elif layer_name == "carve":
            path = layer.get("path")
            if path:
                carve_style = dict(layer_style)
                carve_style["fill_color"] = carve_style.get(
                    "background", style.get("background", [1.0, 1.0, 1.0])
                )
                carve_style["stroke_color"] = carve_style["fill_color"]
                carve_style["_ink_mode"] = "solid"
                _draw_path_mark(
                    db,
                    path,
                    carve_style,
                    filled=True,
                    base_width=layer.get(
                        "stroke_weight", style.get("stroke_width", 1.5)
                    ),
                )

        elif layer_name == "dots":
            dots = layer.get("dots", [])
            db.fill(*layer_style.get("fill_color", [0.0, 0.0, 0.0]))
            db.stroke(None)
            for x, y, radius in dots:
                radius *= _dot_scale(layer_style)
                db.oval(x - radius / 2, y - radius / 2, radius, radius)

        elif layer_name == "accents":
            dots = layer.get("dots", [])
            db.fill(*layer_style.get("fill_color", [0.0, 0.0, 0.0]))
            db.stroke(None)
            for x, y, radius in dots:
                radius *= _accent_scale(layer_style)
                db.oval(x - radius / 2, y - radius / 2, radius, radius)

        elif layer_name == "fill":
            path = layer.get("path")
            if path:
                _draw_path_mark(
                    db,
                    path,
                    layer_style,
                    filled=True,
                    base_width=layer.get(
                        "stroke_weight", style.get("stroke_width", 1.5)
                    ),
                )


def generate_contact_sheet(
    genomes: List[FormGenome],
    output_path: Path,
    cols: int = 4,
    rows: int = 4,
    page_size: Tuple[float, float] = (612, 792),  # Letter
    margin: float = 40,
    style: Optional[Dict[str, Any]] = None,
    specs: Optional[Dict[str, ParameterSpec]] = None,
    title: Optional[str] = None,
) -> Path:
    """
    Generate a multi-page PDF contact sheet with numbered candidates.

    Args:
        genomes: List of FormGenome to display
        output_path: Where to save the PDF
        cols: Number of columns per page
        rows: Number of rows per page
        page_size: (width, height) in points
        margin: Page margin in points
        style: Style dict for rendering forms
        specs: Parameter specifications
        title: Optional title for header

    Returns:
        Path to the saved PDF
    """
    db = _get_db()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Default style
    style = style or {
        "fill_color": [0.0, 0.0, 0.0],
        "stroke_color": [0.0, 0.0, 0.0],
        "stroke_width": 1.0,
        "background": [1.0, 1.0, 1.0],
        "_ink_mode": "banded",
        "_line_weight": 1.0,
        "_white_band": 6.0,
        "_dot_scale": 1.0,
        "_accent_scale": 0.9,
        "_shadow_strength": 0.0,
    }

    specs = specs or DEFAULT_SPECS

    page_width, page_height = page_size
    per_page = cols * rows
    pages_needed = math.ceil(len(genomes) / per_page) if genomes else 1

    # Calculate cell dimensions
    content_width = page_width - 2 * margin
    content_height = page_height - 2 * margin - 40  # Reserve space for header
    gutter = 10

    cell_width = (content_width - (cols - 1) * gutter) / cols
    cell_height = (content_height - (rows - 1) * gutter) / rows

    db.newDrawing()

    for page_idx in range(pages_needed):
        db.newPage(page_width, page_height)

        # Page background
        db.fill(1, 1, 1)
        db.rect(0, 0, page_width, page_height)

        # Header
        header_y = page_height - margin
        db.fill(0.2)
        db.font("Helvetica-Bold", 14)

        if title:
            header_text = f"{title} - Page {page_idx + 1}/{pages_needed}"
        else:
            gen_num = genomes[0].generation if genomes else 0
            header_text = f"Generation {gen_num} - Page {page_idx + 1}/{pages_needed}"

        db.text(header_text, (margin, header_y - 5))

        # Draw grid of forms
        content_top = header_y - 30

        for cell_idx in range(per_page):
            form_idx = page_idx * per_page + cell_idx
            if form_idx >= len(genomes):
                break

            genome = genomes[form_idx]

            # Calculate cell position
            col = cell_idx % cols
            row = cell_idx // cols

            cell_x = margin + col * (cell_width + gutter)
            cell_y = content_top - (row + 1) * (cell_height + gutter) + gutter

            # Draw cell background
            bg = style.get("background", [0.97, 0.97, 0.97])
            db.fill(*bg)
            db.stroke(0.85)
            db.strokeWidth(0.5)
            db.rect(cell_x, cell_y, cell_width, cell_height)

            # Draw form
            generator_func = GENERATORS.get(genome.generator)
            if generator_func:
                render_height = max(cell_height - 18, 40)
                plan = resolve_render_plan(genome, (cell_width, render_height), style)
                center = (
                    cell_x + plan["center"][0],
                    cell_y + 18 + plan["center"][1],
                )
                size = min(plan["size"], min(cell_width, render_height) * 0.95)

                result = generator_func(genome, center, size, specs)

                # Check result type and render accordingly
                if isinstance(result, dict):
                    result_type = result.get("type", "")
                    if result_type == "layered":
                        _render_layered_form_contact(db, result, style)
                    elif result_type == "dot_field":
                        _render_dot_field_contact(db, result, style)
                    elif result_type == "accent_nodes":
                        _render_accent_nodes_contact(db, result, style)
                else:
                    path = result
                    _draw_path_mark(
                        db,
                        path,
                        style,
                        filled=genome.generator != "shape_outline",
                        base_width=style.get("stroke_width", 1.5),
                    )

            # Draw ID label
            db.fill(0.3)
            db.stroke(None)
            db.font("Helvetica-Bold", 11)
            label = f"{genome.index:04d}"
            db.text(label, (cell_x + 5, cell_y + 5))

            # Draw small index number in corner for quick reference
            db.font("Helvetica", 9)
            db.fill(0.5)
            quick_label = str(form_idx + 1)
            db.text(quick_label, (cell_x + cell_width - 15, cell_y + cell_height - 15))

    db.saveImage(str(output_path))
    db.endDrawing()

    return output_path


def generate_selection_summary(
    genomes: List[FormGenome],
    winner_indices: List[int],
    output_path: Path,
    style: Optional[Dict[str, Any]] = None,
    specs: Optional[Dict[str, ParameterSpec]] = None,
) -> Path:
    """
    Generate a summary PDF showing only the selected winners.

    Args:
        genomes: Full population list
        winner_indices: 1-based indices of selected winners
        output_path: Where to save the PDF
        style: Style dict
        specs: Parameter specifications

    Returns:
        Path to saved PDF
    """
    # Convert 1-based indices to genomes
    winners = []
    for idx in winner_indices:
        if 1 <= idx <= len(genomes):
            winners.append(genomes[idx - 1])

    # Generate a smaller contact sheet with just winners
    cols = min(4, len(winners))
    rows = math.ceil(len(winners) / cols) if winners else 1

    return generate_contact_sheet(
        winners,
        output_path,
        cols=cols,
        rows=rows,
        style=style,
        specs=specs,
        title="Selected Winners",
    )
