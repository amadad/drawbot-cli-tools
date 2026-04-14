"""
Shape outline generator: stroke-only contour shapes with character.

Focused on the quality of the line itself:
- Stroke weight variation
- Line breaks and dashes
- Corner treatments
- Organic vs geometric tension
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
            raise ImportError("drawBot required. Install with: uv sync --extra drawbot")
    return _db


def generate_shape_outline(
    genome: 'FormGenome',
    center: Tuple[float, float],
    size: float,
    specs: Dict[str, Any] = None
) -> Any:
    """
    Generate a stroke-only shape with character.

    Returns a BezierPath for stroke rendering.
    """
    db = _get_db()

    from ..parameters import DEFAULT_SPECS, denormalize_params

    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)
    rng = random.Random(genome.seed)

    cx, cy = center

    # Core shape parameters
    shape_type_val = params.get('shape_type', 0.5)
    roundness = params.get('roundness', 0.7)
    aspect = params.get('aspect', 1.0)
    asymmetry = params.get('asymmetry', 0.3)
    lobe_count = int(params.get('lobe_count', 4))
    lobe_depth = params.get('lobe_depth', 0.3)
    wobble = params.get('wobble', 0.05)

    # Line character parameters
    stroke_weight = params.get('stroke_weight', 1.5)
    line_tension = params.get('tension', 0.6)

    half_w = (size / 2) * math.sqrt(aspect)
    half_h = (size / 2) / math.sqrt(aspect)

    path = db.BezierPath()

    # Determine shape type
    shape_types = ['circle', 'pill', 'rounded_rect', 'blob', 'clover', 'overlap']
    shape_idx = int(shape_type_val * (len(shape_types) - 0.01))
    shape_type = shape_types[min(shape_idx, len(shape_types) - 1)]

    if shape_type == 'circle':
        # Ellipse with potential asymmetric distortion
        path.oval(cx - half_w, cy - half_h, half_w * 2, half_h * 2)

    elif shape_type == 'pill':
        # Stadium/pill shape using oval
        path.oval(cx - half_w, cy - half_h, half_w * 2, half_h * 2)

    elif shape_type == 'rounded_rect':
        # Rectangle shape
        path.rect(cx - half_w, cy - half_h, half_w * 2, half_h * 2)

    elif shape_type == 'blob':
        # Organic blob with character
        num_points = lobe_count * 2
        points = []

        # Per-lobe variations for asymmetry
        lobe_radii = [1.0 + rng.uniform(-asymmetry * 0.35, asymmetry * 0.35) for _ in range(lobe_count)]
        lobe_depths = [lobe_depth * (1.0 + rng.uniform(-asymmetry * 0.4, asymmetry * 0.4)) for _ in range(lobe_count)]
        lobe_angles = [rng.uniform(-asymmetry * 12, asymmetry * 12) for _ in range(lobe_count)]

        for i in range(num_points):
            lobe_idx = i // 2
            base_angle = (i / num_points) * 2 * math.pi
            base_angle += math.radians(lobe_angles[lobe_idx % lobe_count])

            is_peak = (i % 2 == 0)

            if is_peak:
                radius_mod = lobe_radii[lobe_idx % lobe_count]
            else:
                current_depth = lobe_depths[lobe_idx % lobe_count]
                radius_mod = lobe_radii[lobe_idx % lobe_count] * (1.0 - current_depth * 0.55)

            # Wobble
            radius_mod *= (1.0 + rng.uniform(-wobble, wobble))

            px = cx + math.cos(base_angle) * half_w * radius_mod
            py = cy + math.sin(base_angle) * half_h * radius_mod
            points.append((px, py))

        if points:
            path.moveTo(points[0])
            for i in range(len(points)):
                p0 = points[i]
                p1 = points[(i + 1) % len(points)]
                p_prev = points[(i - 1) % len(points)]
                p_next = points[(i + 2) % len(points)]

                tangent0 = ((p1[0] - p_prev[0]) * 0.5, (p1[1] - p_prev[1]) * 0.5)
                tangent1 = ((p_next[0] - p0[0]) * 0.5, (p_next[1] - p0[1]) * 0.5)

                handle_scale = line_tension * roundness * 0.45
                cp1 = (p0[0] + tangent0[0] * handle_scale, p0[1] + tangent0[1] * handle_scale)
                cp2 = (p1[0] - tangent1[0] * handle_scale, p1[1] - tangent1[1] * handle_scale)

                path.curveTo(cp1, cp2, p1)
            path.closePath()

    elif shape_type == 'clover':
        # Clover with overlapping circles
        petal_size = size * (0.32 + asymmetry * 0.08)
        for i in range(lobe_count):
            angle = (i / lobe_count) * 2 * math.pi
            angle_off = rng.uniform(-asymmetry * 0.25, asymmetry * 0.25)
            r_mod = 1.0 + rng.uniform(-asymmetry * 0.2, asymmetry * 0.2)

            px = cx + math.cos(angle + angle_off) * size * 0.22 * r_mod
            py = cy + math.sin(angle + angle_off) * size * 0.22 * r_mod

            petal_path = db.BezierPath()
            ps = petal_size * (1.0 + rng.uniform(-asymmetry * 0.15, asymmetry * 0.15))
            petal_path.oval(px - ps/2, py - ps/2, ps, ps)
            path = path.union(petal_path)

    elif shape_type == 'overlap':
        # Venn-style overlap
        offset = size * 0.18 * (1.0 + asymmetry * 0.4)
        circle_size = size * 0.42

        left = db.BezierPath()
        left.oval(cx - offset - circle_size/2, cy - circle_size/2, circle_size, circle_size)

        right = db.BezierPath()
        r_size = circle_size * (1.0 + rng.uniform(-asymmetry * 0.15, asymmetry * 0.15))
        right.oval(cx + offset - r_size/2, cy - r_size/2, r_size, r_size)

        path = left.union(right)

    return path


def get_generator_info() -> Dict[str, Any]:
    return {
        "name": "shape_outline",
        "version": "1.0.0",
        "description": "Stroke-only contour shapes with organic character",
        "parameters": [
            "shape_type", "roundness", "aspect", "asymmetry",
            "lobe_count", "lobe_depth", "wobble", "tension", "stroke_weight"
        ]
    }
