"""
Geometric shape generators: clean, precise forms inspired by SVG geometric primitives.

Produces regular polygons, stars, crosses, nested/concentric forms, and
geometric compounds — all parameterized for evolution.

Parameters used (all normalized 0..1):
    shape_type      → polygon sides (0=triangle..1=decagon) or special form
    rotation        → base rotation
    roundness       → corner rounding (0=sharp, 1=fully rounded)
    aspect          → width/height ratio
    lobe_count      → used as: nesting layers / star points / compound count
    lobe_depth      → used as: star inner radius / cross thickness / ring width
    dot_density     → fill vs stroke (0=stroke only, 1=filled)
    stroke_weight   → line thickness for stroke mode
    asymmetry       → compound offset / rotation variation per layer
    wobble          → per-layer scale variation
    tension         → nesting scale ratio between layers
"""

import math
import random
from typing import Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..genome import FormGenome

_db = None


def _get_db():
    global _db
    if _db is None:
        try:
            import drawBot as db_module
            _db = db_module
        except ImportError:
            raise ImportError("drawBot required: uv sync --extra drawbot")
    return _db


def _polygon_points(cx, cy, radius_x, radius_y, sides, rotation_deg):
    """Generate points for a regular polygon."""
    pts = []
    rot = math.radians(rotation_deg)
    for i in range(sides):
        angle = (2 * math.pi * i / sides) - math.pi / 2 + rot
        pts.append((
            cx + math.cos(angle) * radius_x,
            cy + math.sin(angle) * radius_y,
        ))
    return pts


def _star_points(cx, cy, outer_rx, outer_ry, inner_ratio, points, rotation_deg):
    """Generate alternating outer/inner points for a star."""
    pts = []
    rot = math.radians(rotation_deg)
    for i in range(points * 2):
        angle = (2 * math.pi * i / (points * 2)) - math.pi / 2 + rot
        if i % 2 == 0:
            rx, ry = outer_rx, outer_ry
        else:
            rx, ry = outer_rx * inner_ratio, outer_ry * inner_ratio
        pts.append((cx + math.cos(angle) * rx, cy + math.sin(angle) * ry))
    return pts


def _cross_points(cx, cy, rx, ry, thickness, rotation_deg):
    """Generate a cross/plus shape."""
    t = thickness
    rot = math.radians(rotation_deg)
    # Cross as 12 points
    raw = [
        (-t, ry), (t, ry), (t, t),
        (rx, t), (rx, -t), (t, -t),
        (t, -ry), (-t, -ry), (-t, -t),
        (-rx, -t), (-rx, t), (-t, t),
    ]
    pts = []
    cos_r, sin_r = math.cos(rot), math.sin(rot)
    for x, y in raw:
        pts.append((cx + x * cos_r - y * sin_r, cy + x * sin_r + y * cos_r))
    return pts


def _build_path(db, points, roundness=0.0):
    """Build a BezierPath from points, with optional corner rounding."""
    path = db.BezierPath()
    n = len(points)

    if roundness < 0.05:
        # Sharp corners
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
        path.closePath()
    else:
        # Rounded corners: cut corners and add curves
        r = roundness * 0.4  # max 40% of edge used for rounding
        for i in range(n):
            p_prev = points[(i - 1) % n]
            p_curr = points[i]
            p_next = points[(i + 1) % n]

            # Points along edges toward current vertex
            dx1 = p_curr[0] - p_prev[0]
            dy1 = p_curr[1] - p_prev[1]
            dx2 = p_next[0] - p_curr[0]
            dy2 = p_next[1] - p_curr[1]

            # Start of curve (coming from previous)
            sx = p_curr[0] - dx1 * r
            sy = p_curr[1] - dy1 * r
            # End of curve (going to next)
            ex = p_curr[0] + dx2 * r
            ey = p_curr[1] + dy2 * r

            if i == 0:
                path.moveTo((sx, sy))
            else:
                path.lineTo((sx, sy))

            # Quadratic-ish curve through the corner
            path.curveTo(p_curr, p_curr, (ex, ey))

        path.closePath()
    return path


def generate_polygon(genome, center, size, specs=None):
    """Regular polygon with nesting and rounding."""
    db = _get_db()
    from ..parameters import DEFAULT_SPECS, denormalize_params
    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)
    rng = random.Random(genome.seed)

    cx, cy = center
    shape_val = genome.params.get('shape_type', 0.5)
    sides = int(3 + shape_val * 7)  # 3 to 10
    sides = max(3, min(10, sides))

    rotation = params.get('rotation', 0)
    roundness = genome.params.get('roundness', 0)
    aspect = params.get('aspect', 1.0)
    layers = max(1, int(genome.params.get('lobe_count', 0.3) * 5) + 1)  # 1-6
    scale_ratio = 0.5 + genome.params.get('tension', 0.5) * 0.4  # 0.5-0.9
    is_filled = genome.params.get('dot_density', 0.5) > 0.5
    rot_variation = genome.params.get('asymmetry', 0) * 30  # degrees per layer

    rx = (size / 2) * math.sqrt(aspect)
    ry = (size / 2) / math.sqrt(aspect)

    result_layers = []
    for layer_i in range(layers):
        scale = scale_ratio ** layer_i
        layer_rot = rotation + rot_variation * layer_i
        pts = _polygon_points(cx, cy, rx * scale, ry * scale, sides, layer_rot)
        path = _build_path(db, pts, roundness)
        result_layers.append({
            'name': 'fill' if is_filled else 'outline',
            'path': path,
            'stroke_weight': params.get('stroke_weight', 1.5),
        })

    return {'type': 'layered', 'layers': result_layers}


def generate_star(genome, center, size, specs=None):
    """Star/burst forms with variable points and inner radius."""
    db = _get_db()
    from ..parameters import DEFAULT_SPECS, denormalize_params
    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)
    rng = random.Random(genome.seed)

    cx, cy = center
    point_count = max(3, int(3 + genome.params.get('lobe_count', 0.5) * 9))  # 3-12
    inner_ratio = 0.15 + genome.params.get('lobe_depth', 0.5) * 0.65  # 0.15-0.8
    rotation = params.get('rotation', 0)
    roundness = genome.params.get('roundness', 0)
    aspect = params.get('aspect', 1.0)
    is_filled = genome.params.get('dot_density', 0.5) > 0.5

    rx = (size / 2) * math.sqrt(aspect)
    ry = (size / 2) / math.sqrt(aspect)

    pts = _star_points(cx, cy, rx, ry, inner_ratio, point_count, rotation)
    path = _build_path(db, pts, roundness)

    return {'type': 'layered', 'layers': [{
        'name': 'fill' if is_filled else 'outline',
        'path': path,
        'stroke_weight': params.get('stroke_weight', 1.5),
    }]}


def generate_cross(genome, center, size, specs=None):
    """Cross/plus forms with variable thickness."""
    db = _get_db()
    from ..parameters import DEFAULT_SPECS, denormalize_params
    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)
    rng = random.Random(genome.seed)

    cx, cy = center
    rotation = params.get('rotation', 0)
    roundness = genome.params.get('roundness', 0)
    aspect = params.get('aspect', 1.0)
    thickness = 0.1 + genome.params.get('lobe_depth', 0.3) * 0.35  # fraction of size
    is_filled = genome.params.get('dot_density', 0.5) > 0.5

    rx = (size / 2) * math.sqrt(aspect)
    ry = (size / 2) / math.sqrt(aspect)
    t = size * thickness / 2

    pts = _cross_points(cx, cy, rx, ry, t, rotation)
    path = _build_path(db, pts, roundness)

    return {'type': 'layered', 'layers': [{
        'name': 'fill' if is_filled else 'outline',
        'path': path,
        'stroke_weight': params.get('stroke_weight', 1.5),
    }]}


def generate_ring(genome, center, size, specs=None):
    """Concentric rings / donut forms."""
    db = _get_db()
    from ..parameters import DEFAULT_SPECS, denormalize_params
    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)

    cx, cy = center
    aspect = params.get('aspect', 1.0)
    ring_count = max(1, int(1 + genome.params.get('lobe_count', 0.5) * 5))
    ring_width = 0.4 + genome.params.get('lobe_depth', 0.5) * 0.5  # ratio
    rotation = params.get('rotation', 0)

    rx = (size / 2) * math.sqrt(aspect)
    ry = (size / 2) / math.sqrt(aspect)

    layers = []
    for i in range(ring_count):
        scale = 1.0 - (i / max(ring_count, 1)) * 0.85
        outer_rx, outer_ry = rx * scale, ry * scale
        inner_rx = outer_rx * ring_width
        inner_ry = outer_ry * ring_width

        path = db.BezierPath()
        # Outer circle
        path.oval(cx - outer_rx, cy - outer_ry, outer_rx * 2, outer_ry * 2)
        # Inner circle (cut out) — reverse winding
        path.oval(cx - inner_rx, cy - inner_ry, inner_rx * 2, inner_ry * 2)

        layers.append({
            'name': 'fill' if i % 2 == 0 else 'outline',
            'path': path,
            'stroke_weight': params.get('stroke_weight', 1.5),
        })

    return {'type': 'layered', 'layers': layers}


def generate_compound(genome, center, size, specs=None):
    """Overlapping geometric shapes — multiple forms composed together."""
    db = _get_db()
    from ..parameters import DEFAULT_SPECS, denormalize_params
    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)
    rng = random.Random(genome.seed)

    cx, cy = center
    count = max(2, int(2 + genome.params.get('lobe_count', 0.5) * 4))  # 2-6 shapes
    shape_val = genome.params.get('shape_type', 0.5)
    sides = int(3 + shape_val * 7)
    rotation = params.get('rotation', 0)
    roundness = genome.params.get('roundness', 0)
    aspect = params.get('aspect', 1.0)
    offset_strength = genome.params.get('asymmetry', 0.3) * size * 0.3
    is_filled = genome.params.get('dot_density', 0.5) > 0.5

    rx = (size / 2) * math.sqrt(aspect) * 0.6
    ry = (size / 2) / math.sqrt(aspect) * 0.6

    layers = []
    for i in range(count):
        angle = (2 * math.pi * i / count) + math.radians(rotation)
        ox = cx + math.cos(angle) * offset_strength
        oy = cy + math.sin(angle) * offset_strength
        rot = rotation + (360 / count) * i * genome.params.get('asymmetry', 0)
        scale_var = 1.0 + rng.uniform(-genome.params.get('wobble', 0), genome.params.get('wobble', 0))

        pts = _polygon_points(ox, oy, rx * scale_var, ry * scale_var, sides, rot)
        path = _build_path(db, pts, roundness)

        layers.append({
            'name': 'fill' if is_filled else 'outline',
            'path': path,
            'stroke_weight': params.get('stroke_weight', 1.5),
        })

    return {'type': 'layered', 'layers': layers}
