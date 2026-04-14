"""
Layered form generator: compound forms with shadow, outline, dot grid, and accent dots.

Creates forms inspired by modern UI/brand design with:
- Soft shadow layer (offset background)
- Stroke outline (no fill)
- Internal dot grid pattern
- Accent dots at key vertices
"""

import math
import random
from typing import Tuple, Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..genome import FormGenome

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
                "drawBot is required for form generation but is not installed.\n"
                "Install with: uv sync --extra drawbot"
            )
    return _db


def _rounded_rect_path(
    db, x: float, y: float, width: float, height: float, radius: float
):
    """Build a rounded rectangle path without relying on DrawBot convenience APIs."""
    radius = max(0.0, min(radius, width / 2, height / 2))
    if radius == 0:
        path = db.BezierPath()
        path.rect(x, y, width, height)
        return path

    kappa = 0.5522847498
    ctrl = radius * kappa
    right = x + width
    top = y + height

    path = db.BezierPath()
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


def _generate_base_shape(
    shape_type: str,
    center: Tuple[float, float],
    size: float,
    params: Dict[str, Any],
    rng: random.Random,
) -> Any:
    """Generate the base shape path based on shape_type."""
    db = _get_db()

    cx, cy = center
    roundness = params.get("roundness", 0.5)
    aspect = params.get("aspect", 1.0)
    asymmetry = params.get("asymmetry", 0.2)
    lobe_count = int(params.get("lobe_count", 4))

    half_width = (size / 2) * math.sqrt(aspect)
    half_height = (size / 2) / math.sqrt(aspect)

    path = db.BezierPath()

    if shape_type == "pill":
        # Horizontal pill / stadium shape
        corner_radius = min(half_width, half_height) * roundness
        rect_x = cx - half_width
        rect_y = cy - half_height
        path = _rounded_rect_path(
            db, rect_x, rect_y, half_width * 2, half_height * 2, corner_radius
        )

    elif shape_type == "rounded_rect":
        # Rounded rectangle with variable corners
        corner_radius = min(half_width, half_height) * 0.3 * roundness
        rect_x = cx - half_width
        rect_y = cy - half_height
        path = _rounded_rect_path(
            db, rect_x, rect_y, half_width * 2, half_height * 2, corner_radius
        )

    elif shape_type == "circle":
        # Simple circle/ellipse
        path.oval(cx - half_width, cy - half_height, half_width * 2, half_height * 2)

    elif shape_type == "clover":
        # Clover/flower shape with overlapping circles
        petal_size = size * 0.35
        for i in range(lobe_count):
            angle = (i / lobe_count) * 2 * math.pi
            # Add asymmetric offset
            angle_offset = rng.uniform(-asymmetry * 0.3, asymmetry * 0.3)
            radius_mod = 1.0 + rng.uniform(-asymmetry * 0.2, asymmetry * 0.2)

            px = cx + math.cos(angle + angle_offset) * size * 0.25 * radius_mod
            py = cy + math.sin(angle + angle_offset) * size * 0.25 * radius_mod
            petal_path = db.BezierPath()
            petal_path.oval(
                px - petal_size / 2,
                py - petal_size / 2,
                petal_size,
                petal_size * (1.0 + rng.uniform(-asymmetry * 0.15, asymmetry * 0.15)),
            )
            path = path.union(petal_path)

    elif shape_type == "blob":
        # Organic blob (similar to soft_blob but simplified)
        num_points = lobe_count * 2
        points = []
        lobe_depth = params.get("lobe_depth", 0.3)

        # Generate per-lobe variations
        lobe_radii = [
            1.0 + rng.uniform(-asymmetry * 0.3, asymmetry * 0.3)
            for _ in range(lobe_count)
        ]

        for i in range(num_points):
            lobe_idx = i // 2
            base_angle = (i / num_points) * 2 * math.pi
            is_peak = i % 2 == 0

            if is_peak:
                radius_mod = lobe_radii[lobe_idx % lobe_count]
            else:
                radius_mod = lobe_radii[lobe_idx % lobe_count] * (
                    1.0 - lobe_depth * 0.5
                )

            # Add wobble
            wobble = params.get("wobble", 0.05)
            radius_mod *= 1.0 + rng.uniform(-wobble, wobble)

            px = cx + math.cos(base_angle) * half_width * radius_mod
            py = cy + math.sin(base_angle) * half_height * radius_mod
            points.append((px, py))

        # Build smooth path
        if points:
            path.moveTo(points[0])
            for i in range(len(points)):
                p0 = points[i]
                p1 = points[(i + 1) % len(points)]
                p_prev = points[(i - 1) % len(points)]
                p_next = points[(i + 2) % len(points)]

                tangent0 = ((p1[0] - p_prev[0]) * 0.5, (p1[1] - p_prev[1]) * 0.5)
                tangent1 = ((p_next[0] - p0[0]) * 0.5, (p_next[1] - p0[1]) * 0.5)

                handle_scale = roundness * 0.4
                cp1 = (
                    p0[0] + tangent0[0] * handle_scale,
                    p0[1] + tangent0[1] * handle_scale,
                )
                cp2 = (
                    p1[0] - tangent1[0] * handle_scale,
                    p1[1] - tangent1[1] * handle_scale,
                )

                path.curveTo(cp1, cp2, p1)
            path.closePath()

    elif shape_type == "overlap":
        # Two overlapping circles (Venn diagram style)
        offset = size * 0.2 * (1.0 + asymmetry * 0.5)
        circle_size = size * 0.45

        left_path = db.BezierPath()
        left_path.oval(
            cx - offset - circle_size / 2,
            cy - circle_size / 2,
            circle_size,
            circle_size,
        )

        right_path = db.BezierPath()
        right_path.oval(
            cx + offset - circle_size / 2,
            cy - circle_size / 2,
            circle_size,
            circle_size,
        )

        path = left_path.union(right_path)

    else:
        # Default to circle
        path.oval(cx - half_width, cy - half_height, half_width * 2, half_height * 2)

    return path


def _get_path_bounds(path) -> Tuple[float, float, float, float]:
    """Get bounding box of a path."""
    bounds = path.bounds()
    if bounds:
        return bounds
    return (0, 0, 100, 100)


def _generate_dot_grid(
    path,
    center: Tuple[float, float],
    size: float,
    dot_density: float,
    dot_size: float,
    rng: random.Random,
) -> List[Tuple[float, float, float]]:
    """Generate dots that fall within the path bounds."""
    dots = []

    bounds = _get_path_bounds(path)
    min_x, min_y, max_x, max_y = bounds

    # Calculate grid spacing based on density (higher = more dots)
    spacing = size * (0.15 - dot_density * 0.1)
    spacing = max(spacing, size * 0.03)  # Minimum spacing

    # Offset grid slightly for visual interest
    offset_x = rng.uniform(0, spacing * 0.5)
    offset_y = rng.uniform(0, spacing * 0.5)

    x = min_x + offset_x
    while x < max_x:
        y = min_y + offset_y
        while y < max_y:
            # Check if point is inside path
            if path.pointInside((x, y)):
                dots.append((x, y, dot_size))
            y += spacing
        x += spacing

    return dots


def _get_accent_points(
    path, center: Tuple[float, float], size: float, num_accents: int, rng: random.Random
) -> List[Tuple[float, float]]:
    """Get points along the path outline for accent dots."""
    points = []

    # Sample points along the path
    for i in range(num_accents):
        t = i / num_accents
        # Add slight randomization
        t = (t + rng.uniform(-0.05, 0.05)) % 1.0

        try:
            point = path.pointOnContour(0, t)
            if point:
                points.append(point)
        except (AttributeError, IndexError, TypeError):
            # Fallback: use path bounds corners
            bounds = _get_path_bounds(path)
            if bounds:
                min_x, min_y, max_x, max_y = bounds
                corners = [
                    (min_x, min_y),
                    (max_x, min_y),
                    (max_x, max_y),
                    (min_x, max_y),
                ]
                if i < len(corners):
                    points.append(corners[i])

    return points


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value."""
    return max(low, min(high, value))


def _axis_vectors(rotation: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return the primary axis and its perpendicular for a rotated form."""
    angle = math.radians(rotation - 90)
    axis = (math.cos(angle), math.sin(angle))
    normal = (-axis[1], axis[0])
    return axis, normal


def _offset_point(
    point: Tuple[float, float], direction: Tuple[float, float], distance: float
) -> Tuple[float, float]:
    """Offset a point along a unit vector."""
    return (
        point[0] + direction[0] * distance,
        point[1] + direction[1] * distance,
    )


def _sample_dots(
    dots: List[Tuple[float, float, float]], max_count: int, rng: random.Random
) -> List[Tuple[float, float, float]]:
    """Keep dot fields supportive instead of visually taking over the form."""
    if len(dots) <= max_count:
        return dots
    picked = rng.sample(dots, max_count)
    picked.sort(key=lambda dot: (dot[1], dot[0]))
    return picked


def _build_structural_layers(
    shape_type: str,
    center: Tuple[float, float],
    size: float,
    params: Dict[str, Any],
    stroke_weight: float,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """Build secondary masses and carved apertures that give the form a language."""
    rotation = params.get("rotation", 0.0)
    asymmetry = params.get("asymmetry", 0.3)
    envelope = params.get("envelope_factor", 0.6)
    roundness = params.get("roundness", 0.5)
    lobe_depth = params.get("lobe_depth", 0.3)
    wobble = params.get("wobble", 0.05)
    dot_density = params.get("dot_density", 0.5)
    aspect = params.get("aspect", 1.0)

    axis, normal = _axis_vectors(rotation)
    layers: List[Dict[str, Any]] = []

    inner_center = _offset_point(center, axis, size * (-0.03 + asymmetry * 0.06))
    inner_params = dict(params)
    inner_params["wobble"] = wobble * 0.45
    inner_params["lobe_depth"] = max(0.05, lobe_depth * 0.7)
    inner_path = _generate_base_shape(
        shape_type,
        inner_center,
        size * _clamp(0.72 - dot_density * 0.08, 0.56, 0.76),
        inner_params,
        random.Random(rng.randint(0, 2**31 - 1)),
    )
    layers.append(
        {
            "name": "outline",
            "path": inner_path,
            "stroke_weight": stroke_weight * 0.7,
            "_line_weight": 0.8,
        }
    )

    aperture_shape = {
        "circle": "circle",
        "pill": "pill",
        "rounded_rect": "pill",
        "blob": "rounded_rect",
        "clover": "circle",
        "overlap": "pill",
    }.get(shape_type, "pill")
    aperture_center = _offset_point(center, axis, size * (0.09 + (envelope - 0.5) * 0.22))
    aperture_center = _offset_point(
        aperture_center, normal, size * (asymmetry - 0.5) * 0.18
    )
    aperture_params = dict(params)
    aperture_params["roundness"] = max(roundness, 0.72)
    aperture_params["aspect"] = _clamp(aspect * (0.82 + envelope * 0.14), 0.72, 1.28)
    aperture_params["wobble"] = wobble * 0.25
    aperture_params["lobe_depth"] = max(0.04, lobe_depth * 0.4)
    aperture_path = _generate_base_shape(
        aperture_shape,
        aperture_center,
        size * _clamp(0.24 + envelope * 0.22 - lobe_depth * 0.06, 0.18, 0.42),
        aperture_params,
        random.Random(rng.randint(0, 2**31 - 1)),
    )
    layers.append({"name": "carve", "path": aperture_path})

    slit_count = 1 if asymmetry < 0.4 else 2
    slit_width = size * (0.04 + roundness * 0.02)
    slit_height = size * (0.18 + lobe_depth * 0.12)
    slit_spread = size * 0.085
    for slit_idx in range(slit_count):
        across = 0.0
        if slit_count == 2:
            across = -slit_spread if slit_idx == 0 else slit_spread
        slit_center = _offset_point(aperture_center, normal, across)
        slit_center = _offset_point(slit_center, axis, -size * 0.12)
        layers.append(
            {
                "name": "carve",
                "path": _rounded_rect_path(
                    _get_db(),
                    slit_center[0] - slit_width / 2,
                    slit_center[1] - slit_height / 2,
                    slit_width,
                    slit_height,
                    slit_width / 2,
                ),
            }
        )

    satellite_count = 1 + int(asymmetry > 0.45) + int(dot_density > 0.72)
    satellite_shape = {
        "circle": "pill",
        "pill": "rounded_rect",
        "rounded_rect": "pill",
        "blob": "circle",
        "clover": "pill",
        "overlap": "rounded_rect",
    }.get(shape_type, "pill")
    for satellite_idx in range(satellite_count):
        along = -size * (0.16 + satellite_idx * 0.08)
        spread_index = satellite_idx - (satellite_count - 1) / 2
        across = size * 0.13 * spread_index
        satellite_center = _offset_point(center, axis, along)
        satellite_center = _offset_point(satellite_center, normal, across)
        satellite_params = dict(params)
        satellite_params["roundness"] = max(roundness, 0.65)
        satellite_params["aspect"] = _clamp(aspect * 0.88, 0.72, 1.2)
        satellite_params["wobble"] = wobble * 0.35
        satellite_params["lobe_depth"] = max(0.03, lobe_depth * 0.55)
        layers.append(
            {
                "name": "fill",
                "path": _generate_base_shape(
                    satellite_shape,
                    satellite_center,
                    size * _clamp(0.16 - satellite_idx * 0.025 + dot_density * 0.05, 0.1, 0.22),
                    satellite_params,
                    random.Random(rng.randint(0, 2**31 - 1)),
                ),
                "stroke_weight": stroke_weight * 0.8,
                "_line_weight": 0.85,
            }
        )

    return layers


def generate_layered_form(
    genome: "FormGenome",
    center: Tuple[float, float],
    size: float,
    specs: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Generate a layered compound form.

    Returns a dict with rendering instructions rather than a single path,
    allowing the renderer to draw multiple layers.

    Args:
        genome: FormGenome with normalized [0..1] parameters
        center: (x, y) center point
        size: Reference size
        specs: Optional ParameterSpec dict

    Returns:
        Dict with 'type': 'layered' and layer definitions
    """
    db = _get_db()

    from ..parameters import DEFAULT_SPECS, denormalize_params

    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)
    rng = random.Random(genome.seed)

    # Extract parameters
    shape_type_val = params.get("shape_type", 0.5)
    shape_types = ["circle", "pill", "rounded_rect", "blob", "clover", "overlap"]
    shape_idx = int(shape_type_val * (len(shape_types) - 0.01))
    shape_type = shape_types[min(shape_idx, len(shape_types) - 1)]

    dot_density = params.get("dot_density", 0.5)
    dot_size = params.get("dot_size", 2.0)
    accent_size = params.get("accent_size", 4.0)
    accent_count = int(params.get("accent_count", 3))
    shadow_offset_x = params.get("shadow_offset_x", 4.0)
    shadow_offset_y = params.get("shadow_offset_y", -4.0)
    stroke_weight = params.get("stroke_weight", 1.5)

    # Generate base shape
    base_path = _generate_base_shape(shape_type, center, size, params, rng)

    # Generate shadow path (same shape, offset)
    shadow_center = (center[0] + shadow_offset_x, center[1] + shadow_offset_y)
    shadow_path = _generate_base_shape(
        shape_type, shadow_center, size * 1.05, params, rng
    )

    # Generate dot grid
    dots = _generate_dot_grid(base_path, center, size, dot_density, dot_size, rng)
    dots = _sample_dots(
        dots,
        max(8, int(10 + dot_density * 16)),
        rng,
    )

    # Generate accent points
    accent_points = _get_accent_points(base_path, center, size, accent_count, rng)
    accent_points = accent_points[: max(2, min(accent_count, 5))]

    structural_layers = _build_structural_layers(
        shape_type,
        center,
        size,
        params,
        stroke_weight,
        rng,
    )

    return {
        "type": "layered",
        "layers": [
            {
                "name": "shadow",
                "path": shadow_path,
                "fill": True,
                "stroke": False,
                "fill_color": [0.85, 0.85, 0.88],  # Light gray
            },
            {
                "name": "fill",
                "path": base_path,
                "stroke_weight": stroke_weight,
            },
            *structural_layers,
            *(
                [
                    {
                        "name": "dots",
                        "dots": dots,  # List of (x, y, radius)
                    }
                ]
                if dots
                else []
            ),
            *(
                [
                    {
                        "name": "accents",
                        "dots": [(x, y, accent_size) for x, y in accent_points],
                    }
                ]
                if accent_points
                else []
            ),
            {
                "name": "outline",
                "path": base_path,
                "fill": False,
                "stroke": True,
                "stroke_weight": stroke_weight,
            },
        ],
        "shape_type": shape_type,
    }


def get_generator_info() -> Dict[str, Any]:
    """Return metadata about this generator."""
    return {
        "name": "layered_form",
        "version": "1.0.0",
        "description": "Compound forms with shadow, outline, dot grid, and accent dots",
        "parameters": [
            "shape_type",
            "roundness",
            "aspect",
            "lobe_count",
            "lobe_depth",
            "asymmetry",
            "wobble",
            "dot_density",
            "dot_size",
            "accent_size",
            "accent_count",
            "shadow_offset_x",
            "shadow_offset_y",
            "stroke_weight",
        ],
    }
