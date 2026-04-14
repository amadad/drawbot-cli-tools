"""
Render genomes to visual output files.

Each genome is rendered to an SVG/PDF file along with a metadata JSON file
that captures all parameters, seed, lineage, and generation info.
"""

import json
import random
import time
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List

from .genome import FormGenome
from .parameters import DEFAULT_SPECS, ParameterSpec
from .generators import GENERATORS


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
                "drawBot is required for rendering but is not installed.\n"
                "Install with: uv sync --extra drawbot"
            )
    return _db


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value."""
    return max(low, min(high, value))


def density_multiplier(style: Optional[Dict[str, Any]] = None) -> float:
    """Map semantic density names to a visual multiplier."""
    density = (style or {}).get("_density", "medium")
    return {
        "sparse": 0.85,
        "medium": 1.0,
        "dense": 1.2,
    }.get(density, 1.0)


def resolve_render_plan(
    genome: FormGenome,
    canvas_size: Tuple[float, float],
    style: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve semantic placement and sizing for a render."""
    style = style or {}
    width, height = canvas_size
    gravity = style.get("_gravity", "center")
    scale = _clamp(float(style.get("_scale", 0.8)), 0.35, 0.95)

    center_x = width / 2
    center_y = height / 2

    if gravity == "bottom":
        center_y = height * 0.38
    elif gravity == "top":
        center_y = height * 0.62
    elif gravity == "scatter":
        rng = random.Random(genome.seed)
        center_x = width * rng.uniform(0.32, 0.68)
        center_y = height * rng.uniform(0.32, 0.68)

    return {
        "center": (center_x, center_y),
        "size": min(width, height) * scale,
        "density_scale": density_multiplier(style),
    }


def _gray(value: float) -> List[float]:
    """Expand a grayscale value to RGB."""
    return [value, value, value]


def _line_weight(style: Dict[str, Any], base_width: float) -> float:
    """Resolve the effective line weight for a mark."""
    return max(
        0.8, base_width * style.get("_line_weight", 1.0) * density_multiplier(style)
    )


def _dot_scale(style: Dict[str, Any]) -> float:
    """Resolve dot scale from density and semantic style."""
    return density_multiplier(style) * style.get("_dot_scale", 1.0)


def _accent_scale(style: Dict[str, Any]) -> float:
    """Resolve accent scale from density and semantic style."""
    return density_multiplier(style) * style.get("_accent_scale", 1.0)


def _layer_style(style: Dict[str, Any], layer: Dict[str, Any]) -> Dict[str, Any]:
    """Merge per-layer overrides onto the generation style."""
    merged = dict(style)
    for key in (
        "fill_color",
        "stroke_color",
        "background",
        "stroke_width",
        "_ink_mode",
        "_line_weight",
        "_white_band",
        "_dot_scale",
        "_accent_scale",
        "_shadow_strength",
    ):
        if key in layer:
            merged[key] = layer[key]
    return merged


def _draw_path_mark(
    db,
    path,
    style: Dict[str, Any],
    *,
    filled: bool,
    base_width: float,
):
    """Draw a path using the active monochrome form language."""
    fill = style.get("fill_color", [0.0, 0.0, 0.0])
    stroke = style.get("stroke_color", [0.0, 0.0, 0.0])
    bg = style.get("background", [1.0, 1.0, 1.0])
    mode = style.get("_ink_mode", "banded")
    main_width = _line_weight(style, base_width)
    band_width = max(0.0, style.get("_white_band", 0.0))

    if mode == "solid" and filled:
        db.fill(*fill)
        db.stroke(None)
        db.drawPath(path)
        return

    if mode == "outline" or not filled:
        db.fill(None)
        db.stroke(*stroke)
        db.strokeWidth(main_width)
        db.drawPath(path)
        return

    if mode == "echo":
        db.fill(None)
        db.stroke(*_gray(0.7))
        db.strokeWidth(main_width * 3.0)
        db.drawPath(path)
        db.stroke(*bg)
        db.strokeWidth(main_width * 1.8)
        db.drawPath(path)
        db.stroke(*stroke)
        db.strokeWidth(main_width * 0.85)
        db.drawPath(path)
        return

    db.fill(*fill)
    db.stroke(None)
    db.drawPath(path)
    if band_width > 0:
        db.fill(None)
        db.stroke(*bg)
        db.strokeWidth(main_width + band_width)
        db.drawPath(path)
    db.stroke(*stroke)
    db.strokeWidth(main_width)
    db.drawPath(path)


def _render_dot_field(db, form_data: Dict[str, Any], style: Dict[str, Any]):
    """Render a dot field."""
    fill_color = style.get("fill_color", [0.0, 0.0, 0.0])
    dots = form_data.get("dots", [])
    dot_scale = _dot_scale(style)

    db.fill(*fill_color)
    db.stroke(None)

    for x, y, radius in dots:
        radius *= dot_scale
        db.oval(x - radius / 2, y - radius / 2, radius, radius)


def _render_accent_nodes(db, form_data: Dict[str, Any], style: Dict[str, Any]):
    """Render accent nodes."""
    fill_color = style.get("fill_color", [0.0, 0.0, 0.0])
    nodes = form_data.get("nodes", [])
    dot_scale = _accent_scale(style)

    db.fill(*fill_color)
    db.stroke(None)

    for x, y, radius in nodes:
        radius *= dot_scale
        db.oval(x - radius / 2, y - radius / 2, radius, radius)


def _render_layered_form(db, form_data: Dict[str, Any], style: Dict[str, Any]):
    """Render a layered compound form with multiple layers."""
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

        elif layer_name == "outline" and layer.get("path"):
            path = layer["path"]
            _draw_path_mark(
                db,
                path,
                style,
                filled=False,
                base_width=layer.get("stroke_weight", style.get("stroke_width", 1.5)),
            )


def render_genome(
    genome: FormGenome,
    output_dir: Path,
    canvas_size: Tuple[float, float] = (200, 200),
    format: str = "svg",
    style: Optional[Dict[str, Any]] = None,
    specs: Optional[Dict[str, ParameterSpec]] = None,
) -> Tuple[Path, Path]:
    """
    Render a genome to an image file and metadata JSON.

    Args:
        genome: The FormGenome to render
        output_dir: Directory to save output files
        canvas_size: (width, height) of canvas in points
        format: Output format ("svg", "pdf", "png")
        style: Optional style dict with fill_color, stroke_color, stroke_width
        specs: Parameter specifications for denormalization

    Returns:
        Tuple of (image_path, metadata_path)
    """
    db = _get_db()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Default style
    style = style or {
        "fill_color": [0.0, 0.0, 0.0],
        "stroke_color": [0.0, 0.0, 0.0],
        "stroke_width": 1.5,
        "background": [1.0, 1.0, 1.0],
        "_ink_mode": "banded",
        "_line_weight": 1.0,
        "_white_band": 6.0,
        "_dot_scale": 1.0,
        "_accent_scale": 0.9,
        "_shadow_strength": 0.0,
    }

    specs = specs or DEFAULT_SPECS

    # Get the generator function
    generator_func = GENERATORS.get(genome.generator)
    if not generator_func:
        raise ValueError(f"Unknown generator: {genome.generator}")

    # Set up canvas
    width, height = canvas_size
    db.newDrawing()
    db.newPage(width, height)

    # Background
    bg = style.get("background", [1.0, 1.0, 1.0])
    db.fill(*bg)
    db.rect(0, 0, width, height)

    # Generate and draw the form
    plan = resolve_render_plan(genome, canvas_size, style)
    center = plan["center"]
    size = plan["size"]

    result = generator_func(genome, center, size, specs)

    # Check result type and render accordingly
    if isinstance(result, dict):
        result_type = result.get("type", "")
        if result_type == "layered":
            _render_layered_form(db, result, style)
        elif result_type == "dot_field":
            _render_dot_field(db, result, style)
        elif result_type == "accent_nodes":
            _render_accent_nodes(db, result, style)
        else:
            # Unknown dict type, try to render as simple form
            pass
    else:
        # Simple path rendering (BezierPath)
        path = result
        _draw_path_mark(
            db,
            path,
            style,
            filled=genome.generator != "shape_outline",
            base_width=style.get("stroke_width", 1.5),
        )

    # Determine output paths
    file_base = f"{genome.index:04d}"
    image_path = output_dir / f"{file_base}.{format}"
    meta_path = output_dir / f"{file_base}_meta.json"

    # Save image
    db.saveImage(str(image_path))
    db.endDrawing()

    # Save metadata
    metadata = {
        "genome": genome.to_dict(),
        "render_info": {
            "canvas_size": list(canvas_size),
            "format": format,
            "style": style,
            "rendered_at": time.time(),
        },
        "generator_info": {
            "name": genome.generator,
            "version": "1.0.0",
        },
    }

    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return image_path, meta_path


def render_population(
    genomes: List[FormGenome],
    output_dir: Path,
    canvas_size: Tuple[float, float] = (200, 200),
    format: str = "svg",
    style: Optional[Dict[str, Any]] = None,
    specs: Optional[Dict[str, ParameterSpec]] = None,
) -> List[Tuple[Path, Path]]:
    """
    Render all genomes in a population.

    Args:
        genomes: List of FormGenome to render
        output_dir: Directory to save output files
        canvas_size: (width, height) of canvas
        format: Output format
        style: Style dict
        specs: Parameter specifications

    Returns:
        List of (image_path, metadata_path) tuples
    """
    results = []

    for genome in genomes:
        image_path, meta_path = render_genome(
            genome, output_dir, canvas_size, format, style, specs
        )
        results.append((image_path, meta_path))

    return results
