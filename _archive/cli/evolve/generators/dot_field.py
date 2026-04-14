"""
Dot field generator: standalone dot patterns with rhythm and character.

Creates fields of dots with:
- Variable density and clustering
- Size gradients
- Rhythmic spacing variations
- Bounded by invisible shapes or free-form
"""

import math
import random
from typing import Tuple, Dict, Any, List, TYPE_CHECKING

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


def generate_dot_field(
    genome: 'FormGenome',
    center: Tuple[float, float],
    size: float,
    specs: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate a field of dots with character.

    Returns a dict with dot positions and sizes for rendering.
    """
    db = _get_db()

    from ..parameters import DEFAULT_SPECS, denormalize_params

    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)
    rng = random.Random(genome.seed)

    cx, cy = center

    # Field parameters
    dot_density = params.get('dot_density', 0.5)
    dot_size = params.get('dot_size', 2.0)
    aspect = params.get('aspect', 1.0)
    asymmetry = params.get('asymmetry', 0.3)

    # Character parameters - derived from existing params
    size_variation = asymmetry * 0.6  # How much dot sizes vary
    spacing_jitter = params.get('wobble', 0.05) * 3  # Position randomness
    cluster_tendency = params.get('lobe_depth', 0.3)  # Tendency to cluster
    gradient_strength = params.get('envelope_factor', 0.6)  # Size gradient from center

    # Bound shape for dots
    shape_type_val = params.get('shape_type', 0.5)
    roundness = params.get('roundness', 0.7)
    lobe_count = int(params.get('lobe_count', 4))

    half_w = (size / 2) * math.sqrt(aspect)
    half_h = (size / 2) / math.sqrt(aspect)

    # Create bounding path
    bound_path = _create_bound_shape(db, cx, cy, half_w, half_h, shape_type_val, roundness, lobe_count, asymmetry, rng)

    # Calculate grid spacing
    base_spacing = size * (0.12 - dot_density * 0.07)
    base_spacing = max(base_spacing, size * 0.025)

    # Generate dots
    dots = []
    bounds = bound_path.bounds() if bound_path else (cx - half_w, cy - half_h, cx + half_w, cy + half_h)
    min_x, min_y, max_x, max_y = bounds

    # Grid with jitter
    x = min_x + rng.uniform(0, base_spacing * 0.5)
    row = 0
    while x < max_x:
        y = min_y + rng.uniform(0, base_spacing * 0.5)
        # Offset every other row for more organic feel
        if row % 2 == 1:
            y += base_spacing * 0.5

        while y < max_y:
            # Check if inside bounds
            if bound_path and bound_path.pointInside((x, y)):
                # Apply jitter
                jx = x + rng.uniform(-spacing_jitter * base_spacing, spacing_jitter * base_spacing)
                jy = y + rng.uniform(-spacing_jitter * base_spacing, spacing_jitter * base_spacing)

                # Calculate size based on position (gradient from center)
                dist_from_center = math.sqrt((jx - cx)**2 + (jy - cy)**2)
                max_dist = math.sqrt(half_w**2 + half_h**2)
                normalized_dist = dist_from_center / max_dist if max_dist > 0 else 0

                # Size gradient: larger near center or edges based on gradient_strength
                if gradient_strength > 0.5:
                    # Larger at center
                    size_factor = 1.0 - normalized_dist * (gradient_strength - 0.5) * 1.5
                else:
                    # Larger at edges
                    size_factor = 0.5 + normalized_dist * (0.5 - gradient_strength) * 1.5

                # Add random variation
                size_factor *= (1.0 + rng.uniform(-size_variation, size_variation))
                size_factor = max(0.3, min(1.8, size_factor))

                # Clustering: occasionally skip dots or add extras
                if rng.random() > cluster_tendency * 0.3:
                    final_size = dot_size * size_factor
                    dots.append((jx, jy, final_size))

                    # Occasional cluster
                    if rng.random() < cluster_tendency * 0.15:
                        for _ in range(rng.randint(1, 3)):
                            cx_off = rng.uniform(-base_spacing * 0.4, base_spacing * 0.4)
                            cy_off = rng.uniform(-base_spacing * 0.4, base_spacing * 0.4)
                            cluster_size = final_size * rng.uniform(0.5, 1.2)
                            dots.append((jx + cx_off, jy + cy_off, cluster_size))

            y += base_spacing
        x += base_spacing
        row += 1

    return {
        'type': 'dot_field',
        'dots': dots,
        'bound_path': bound_path,
    }


def _create_bound_shape(db, cx, cy, half_w, half_h, shape_type_val, roundness, lobe_count, asymmetry, rng):
    """Create the bounding shape path."""
    path = db.BezierPath()

    shape_types = ['circle', 'pill', 'rounded_rect', 'blob', 'clover']
    shape_idx = int(shape_type_val * (len(shape_types) - 0.01))
    shape_type = shape_types[min(shape_idx, len(shape_types) - 1)]

    if shape_type == 'circle':
        path.oval(cx - half_w, cy - half_h, half_w * 2, half_h * 2)

    elif shape_type == 'pill':
        # Use oval for pill shape (simpler approximation)
        path.oval(cx - half_w, cy - half_h, half_w * 2, half_h * 2)

    elif shape_type == 'rounded_rect':
        # Use rect for rounded rect (simpler approximation)
        path.rect(cx - half_w, cy - half_h, half_w * 2, half_h * 2)

    elif shape_type == 'blob':
        num_points = lobe_count * 2
        points = []
        lobe_depth = 0.3

        for i in range(num_points):
            base_angle = (i / num_points) * 2 * math.pi
            is_peak = (i % 2 == 0)
            radius_mod = 1.0 if is_peak else (1.0 - lobe_depth * 0.5)
            radius_mod *= (1.0 + rng.uniform(-asymmetry * 0.2, asymmetry * 0.2))

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

                handle_scale = roundness * 0.4
                cp1 = (p0[0] + tangent0[0] * handle_scale, p0[1] + tangent0[1] * handle_scale)
                cp2 = (p1[0] - tangent1[0] * handle_scale, p1[1] - tangent1[1] * handle_scale)

                path.curveTo(cp1, cp2, p1)
            path.closePath()

    elif shape_type == 'clover':
        petal_size = (half_w + half_h) * 0.7
        for i in range(lobe_count):
            angle = (i / lobe_count) * 2 * math.pi
            px = cx + math.cos(angle) * half_w * 0.4
            py = cy + math.sin(angle) * half_h * 0.4
            petal = db.BezierPath()
            petal.oval(px - petal_size/2, py - petal_size/2, petal_size, petal_size)
            path = path.union(petal)

    return path


def get_generator_info() -> Dict[str, Any]:
    return {
        "name": "dot_field",
        "version": "1.0.0",
        "description": "Standalone dot patterns with rhythm and clustering",
        "parameters": [
            "dot_density", "dot_size", "shape_type", "aspect", "asymmetry",
            "wobble", "lobe_depth", "envelope_factor", "roundness", "lobe_count"
        ]
    }
