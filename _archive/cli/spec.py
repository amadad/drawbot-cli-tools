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
from PIL import Image
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
# Backend-neutral drawing helpers
# -----------------------------------------------------------------------------


def build_rounded_rect_path(
    db: Any, x: float, y: float, width: float, height: float, radius: float
):
    """Build a rounded rectangle path without relying on backend helpers."""
    radius = max(0.0, min(radius, width / 2, height / 2))
    path = db.BezierPath()

    if radius == 0:
        path.rect(x, y, width, height)
        return path

    kappa = 0.5522847498
    ctrl = radius * kappa
    right = x + width
    top = y + height

    path.moveTo((x + radius, y))
    path.lineTo((right - radius, y))
    path.curveTo(
        (right - radius + ctrl, y),
        (right, y + radius - ctrl),
        (right, y + radius),
    )
    path.lineTo((right, top - radius))
    path.curveTo(
        (right, top - radius + ctrl),
        (right - radius + ctrl, top),
        (right - radius, top),
    )
    path.lineTo((x + radius, top))
    path.curveTo(
        (x + radius - ctrl, top),
        (x, top - radius + ctrl),
        (x, top - radius),
    )
    path.lineTo((x, y + radius))
    path.curveTo(
        (x, y + radius - ctrl),
        (x + radius - ctrl, y),
        (x + radius, y),
    )
    path.closePath()
    return path


def get_image_size(image_path: Path) -> Tuple[float, float]:
    """Return image dimensions using Pillow so rendering is backend-independent."""
    with Image.open(image_path) as image:
        return image.size


def compute_image_placement(
    frame: Tuple[float, float, float, float],
    intrinsic_size: Tuple[float, float],
    fit: str,
) -> Tuple[float, float, float, float]:
    """Compute final image placement in page coordinates."""
    x, y, width, height = frame
    image_width, image_height = intrinsic_size

    if fit == "stretch":
        return x, y, width / image_width, height / image_height

    if fit == "fill":
        scale = max(width / image_width, height / image_height)
    else:
        scale = min(width / image_width, height / image_height)

    draw_width = image_width * scale
    draw_height = image_height * scale
    draw_x = x + (width - draw_width) / 2
    draw_y = y + (height - draw_height) / 2
    return draw_x, draw_y, scale, scale


def draw_image_in_frame(
    db: Any,
    image_path: Path,
    frame: Tuple[float, float, float, float],
    fit: str,
    opacity: float = 1.0,
) -> None:
    """Draw an image via translate/scale so backends do not need DrawBot-only helpers."""
    x, y, width, height = frame
    intrinsic_size = get_image_size(image_path)
    draw_x, draw_y, scale_x, scale_y = compute_image_placement(
        frame, intrinsic_size, fit
    )

    with db.savedState():
        if opacity < 1.0:
            db.opacity(opacity)

        if fit == "fill":
            clip_path = db.BezierPath()
            clip_path.rect(x, y, width, height)
            db.clipPath(clip_path)

        db.translate(draw_x, draw_y)
        db.scale(scale_x, scale_y)
        db.image(str(image_path), (0, 0))


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
                db.drawPath(build_rounded_rect_path(db, x, y, w, h, elem.corner_radius))
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
                draw_image_in_frame(
                    db,
                    img_path,
                    (x, y, w, h),
                    elem.fit,
                    opacity=elem.opacity,
                )

    # Determine output path
    if output_path:
        final_path = output_path
    elif spec.output:
        final_path = get_output_path(spec.output)
    else:
        final_path = get_output_path(spec_path.stem + ".pdf")

    db.saveImage(str(final_path))

    return final_path
