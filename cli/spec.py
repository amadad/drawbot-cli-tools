"""
YAML Spec Parser and Renderer for DrawBot.

Allows declarative poster definitions:

    page:
      format: letter
      margins: 72

    typography:
      scale: poster

    grid:
      columns: 12
      rows: 8

    elements:
      - type: rect
        grid: [0, 6, 12, 2]
        fill: "#1a1a1a"

      - type: text
        content: "${title}"
        grid: [1, 6, 10, 1]
        style: title
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, Field

# Add lib to path for design system imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "lib"))


# -----------------------------------------------------------------------------
# Schema Models
# -----------------------------------------------------------------------------


class PageSpec(BaseModel):
    """Page configuration."""

    format: Literal["letter", "a4", "tabloid"] = "letter"
    margins: int = 72
    orientation: Literal["portrait", "landscape"] = "portrait"


class TypographySpec(BaseModel):
    """Typography configuration."""

    scale: Literal["poster", "magazine", "book", "report"] = "poster"
    title_font: str = "Helvetica Bold"
    body_font: str = "Helvetica"


class GridSpec(BaseModel):
    """Grid configuration."""

    columns: int = 12
    rows: int = 8


class RectElement(BaseModel):
    """Rectangle element."""

    type: Literal["rect"] = "rect"
    grid: Tuple[int, int, int, int]  # col, row, col_span, row_span
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: float = 1.0
    corner_radius: float = 0


class TextElement(BaseModel):
    """Text element."""

    type: Literal["text"] = "text"
    content: str
    grid: Tuple[int, int, int, int]  # col, row, col_span, row_span
    style: Literal["title", "h1", "h2", "h3", "body", "caption"] = "body"
    font: Optional[str] = None
    size: Optional[float] = None
    color: str = "#000000"
    align: Literal["left", "center", "right"] = "left"
    wrap: bool = True


class ImageElement(BaseModel):
    """Image element."""

    type: Literal["image"] = "image"
    path: str
    grid: Tuple[int, int, int, int]
    fit: Literal["fill", "fit", "stretch"] = "fit"
    opacity: float = 1.0


class LineElement(BaseModel):
    """Line element."""

    type: Literal["line"] = "line"
    start: Tuple[int, int]  # grid col, row
    end: Tuple[int, int]  # grid col, row
    stroke: str = "#000000"
    stroke_width: float = 1.0


class OvalElement(BaseModel):
    """Oval/circle element."""

    type: Literal["oval"] = "oval"
    grid: Tuple[int, int, int, int]
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: float = 1.0


Element = Union[RectElement, TextElement, ImageElement, LineElement, OvalElement]


class PosterSpec(BaseModel):
    """Complete poster specification."""

    page: PageSpec = Field(default_factory=PageSpec)
    typography: TypographySpec = Field(default_factory=TypographySpec)
    grid: GridSpec = Field(default_factory=GridSpec)
    variables: Dict[str, Any] = Field(default_factory=dict)
    elements: List[Dict[str, Any]] = Field(default_factory=list)
    output: Optional[str] = None


# -----------------------------------------------------------------------------
# Color Utilities
# -----------------------------------------------------------------------------


def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")
    try:
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
    except ValueError as e:
        raise ValueError(f"Invalid hex color: #{hex_color}") from e
    return (r, g, b)


def parse_color(color: Optional[str]) -> Optional[Tuple[float, ...]]:
    """Parse color string to tuple."""
    if color is None:
        return None
    if isinstance(color, str):
        if color.startswith("#"):
            return hex_to_rgb(color)
        # Named colors
        named = {
            "black": (0, 0, 0),
            "white": (1, 1, 1),
            "red": (1, 0, 0),
            "green": (0, 1, 0),
            "blue": (0, 0, 1),
        }
        return named.get(color.lower(), (0, 0, 0))
    return color


# -----------------------------------------------------------------------------
# Variable Interpolation
# -----------------------------------------------------------------------------


def interpolate_variables(text: str, variables: Dict[str, Any]) -> str:
    """Replace ${var} patterns with variable values."""

    def replacer(match):
        key = match.group(1)
        # Support nested keys like ${colors.primary}
        parts = key.split(".")
        value = variables
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, match.group(0))
            else:
                return match.group(0)
        return str(value)

    return re.sub(r"\$\{([^}]+)\}", replacer, text)


# -----------------------------------------------------------------------------
# Spec Loader
# -----------------------------------------------------------------------------


def load_spec(spec_path: Path, overrides: Optional[Dict[str, Any]] = None) -> PosterSpec:
    """Load and validate a YAML spec file."""
    try:
        with open(spec_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {spec_path.name}: {e}") from e

    if data is None:
        data = {}

    # Apply overrides to variables
    if overrides:
        if "variables" not in data:
            data["variables"] = {}
        data["variables"].update(overrides)

    return PosterSpec(**data)


# -----------------------------------------------------------------------------
# Renderer
# -----------------------------------------------------------------------------


def render_from_spec(
    spec_path: Path,
    output_path: Optional[Path] = None,
    overrides: Optional[Dict[str, Any]] = None,
    backend: Optional[str] = None,
) -> Path:
    """
    Render a poster from YAML specification.

    Args:
        spec_path: Path to YAML spec file
        output_path: Optional output path override
        overrides: Optional variable overrides (--set key=value)

    Returns:
        Path to rendered file
    """
    from drawbot_backend import get_backend

    db = get_backend(selected=backend)

    from drawbot_design_system import (
        BOOK_SCALE,
        MAGAZINE_SCALE,
        POSTER_SCALE,
        REPORT_SCALE,
        draw_wrapped_text,
        get_output_path,
        setup_poster_page,
    )
    from drawbot_grid import Grid

    spec = load_spec(spec_path, overrides)

    # Get typography scale
    scales = {
        "poster": POSTER_SCALE,
        "magazine": MAGAZINE_SCALE,
        "book": BOOK_SCALE,
        "report": REPORT_SCALE,
    }
    scale = scales.get(spec.typography.scale, POSTER_SCALE)

    # Style to font size mapping
    style_sizes = {
        "title": scale.title,
        "h1": scale.h1,
        "h2": scale.h2,
        "h3": scale.h3,
        "body": scale.body,
        "caption": scale.caption,
    }

    # Setup page
    WIDTH, HEIGHT, MARGIN = setup_poster_page(spec.page.format)

    # Override margin if specified
    if spec.page.margins != 72:
        MARGIN = spec.page.margins

    # Setup grid
    grid = Grid.from_margins(
        (-MARGIN, -MARGIN, -MARGIN, -MARGIN),
        column_subdivisions=spec.grid.columns,
        row_subdivisions=spec.grid.rows,
    )

    # Render elements
    for elem_data in spec.elements:
        elem_type = elem_data.get("type")

        if elem_type == "rect":
            elem = RectElement(**elem_data)
            col, row, col_span, row_span = elem.grid
            x, y = grid[(col, row)]
            w, h = grid * (col_span, row_span)

            if elem.fill:
                db.fill(*parse_color(elem.fill))
            else:
                db.fill(None)

            if elem.stroke:
                db.stroke(*parse_color(elem.stroke))
                db.strokeWidth(elem.stroke_width)
            else:
                db.stroke(None)

            if elem.corner_radius > 0:
                db.roundedRect(x, y, w, h, elem.corner_radius)
            else:
                db.rect(x, y, w, h)

        elif elem_type == "oval":
            elem = OvalElement(**elem_data)
            col, row, col_span, row_span = elem.grid
            x, y = grid[(col, row)]
            w, h = grid * (col_span, row_span)

            if elem.fill:
                db.fill(*parse_color(elem.fill))
            else:
                db.fill(None)

            if elem.stroke:
                db.stroke(*parse_color(elem.stroke))
                db.strokeWidth(elem.stroke_width)
            else:
                db.stroke(None)

            db.oval(x, y, w, h)

        elif elem_type == "text":
            elem = TextElement(**elem_data)
            col, row, col_span, row_span = elem.grid
            x, y = grid[(col, row)]
            w, h = grid * (col_span, row_span)

            # Interpolate variables in content
            content = interpolate_variables(elem.content, spec.variables)

            # Set color
            db.fill(*parse_color(elem.color))
            db.stroke(None)

            # Set font
            font = elem.font or (
                spec.typography.title_font
                if elem.style in ("title", "h1", "h2", "h3")
                else spec.typography.body_font
            )
            size = elem.size or style_sizes.get(elem.style, scale.body)

            db.font(font)
            db.fontSize(size)

            if elem.wrap:
                draw_wrapped_text(content, x, y + h, w, h, font, size)
            else:
                # Simple text placement
                if elem.align == "center":
                    text_w, _ = db.textSize(content)
                    x = x + (w - text_w) / 2
                elif elem.align == "right":
                    text_w, _ = db.textSize(content)
                    x = x + w - text_w

                db.text(content, (x, y + h - size))

        elif elem_type == "line":
            elem = LineElement(**elem_data)
            x1, y1 = grid[(elem.start[0], elem.start[1])]
            x2, y2 = grid[(elem.end[0], elem.end[1])]

            db.stroke(*parse_color(elem.stroke))
            db.strokeWidth(elem.stroke_width)
            db.fill(None)
            db.line((x1, y1), (x2, y2))

        elif elem_type == "image":
            elem = ImageElement(**elem_data)
            col, row, col_span, row_span = elem.grid
            x, y = grid[(col, row)]
            w, h = grid * (col_span, row_span)

            img_path = Path(elem.path)
            if not img_path.is_absolute():
                img_path = spec_path.parent / img_path

            if img_path.exists():
                with db.savedState():
                    if elem.opacity < 1.0:
                        db.opacity(elem.opacity)

                    # Get image size for fitting
                    img_w, img_h = db.imageSize(str(img_path))

                    if elem.fit == "fill":
                        # Scale to fill, may crop
                        img_scale = max(w / img_w, h / img_h)
                    elif elem.fit == "fit":
                        # Scale to fit, may have margins
                        img_scale = min(w / img_w, h / img_h)
                    else:  # stretch
                        img_scale = 1

                    if elem.fit != "stretch":
                        new_w = img_w * img_scale
                        new_h = img_h * img_scale
                        offset_x = (w - new_w) / 2
                        offset_y = (h - new_h) / 2
                        db.image(str(img_path), (x + offset_x, y + offset_y), scale=img_scale)
                    else:
                        # Stretch: scale to fit box dimensions
                        scale_x = w / img_w
                        scale_y = h / img_h
                        db.save()
                        db.translate(x, y)
                        db.scale(scale_x, scale_y)
                        db.image(str(img_path), (0, 0))
                        db.restore()

    # Determine output path
    if output_path:
        final_path = output_path
    elif spec.output:
        final_path = get_output_path(spec.output)
    else:
        final_path = get_output_path(spec_path.stem + ".pdf")

    db.saveImage(str(final_path))

    return final_path
