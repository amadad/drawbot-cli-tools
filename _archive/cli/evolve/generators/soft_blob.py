"""
Soft blob generator: organic bezier-based radial forms.

Creates forms that suggest "care and safety" through:
- Smooth, flowing curves
- Protective envelope asymmetry
- Organic wobble variations
"""

import math
import random
from typing import Tuple, Dict, Any, TYPE_CHECKING

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


def generate_soft_blob(
    genome: 'FormGenome',
    center: Tuple[float, float],
    size: float,
    specs: Dict[str, Any] = None
) -> Any:
    """
    Generate a soft blob form as a BezierPath.

    Args:
        genome: FormGenome with normalized [0..1] parameters
        center: (x, y) center point of the form
        size: Reference size (approximate diameter)
        specs: Optional ParameterSpec dict for denormalization

    Returns:
        drawBot.BezierPath object ready to draw
    """
    db = _get_db()

    # Import here to avoid circular dependency
    from ..parameters import DEFAULT_SPECS, denormalize_params

    specs = specs or DEFAULT_SPECS

    # Denormalize parameters to actual values
    params = denormalize_params(genome.params, specs)

    # Set up seeded RNG for reproducibility
    rng = random.Random(genome.seed)

    # Extract parameters with defaults
    lobe_count = int(params.get('lobe_count', 4))
    lobe_depth = params.get('lobe_depth', 0.3)
    envelope_factor = params.get('envelope_factor', 0.6)
    roundness = params.get('roundness', 0.7)
    wobble = params.get('wobble', 0.05)
    tension = params.get('tension', 0.6)
    aspect = params.get('aspect', 1.0)
    rotation = params.get('rotation', 0)
    asymmetry = params.get('asymmetry', 0.3)

    # Pre-generate per-lobe asymmetric variations (seeded for reproducibility)
    lobe_radii = [1.0 + rng.uniform(-asymmetry * 0.4, asymmetry * 0.4) for _ in range(lobe_count)]
    lobe_depths = [lobe_depth * (1.0 + rng.uniform(-asymmetry * 0.5, asymmetry * 0.5)) for _ in range(lobe_count)]
    lobe_angles = [rng.uniform(-asymmetry * 15, asymmetry * 15) for _ in range(lobe_count)]  # Angular offset in degrees

    # Calculate base dimensions
    cx, cy = center
    half_width = (size / 2) * math.sqrt(aspect)
    half_height = (size / 2) / math.sqrt(aspect)

    # Rotation in radians
    rot_rad = math.radians(rotation)

    # Generate points around the form
    # We create 2 * lobe_count points: alternating peaks and valleys
    num_points = lobe_count * 2
    points = []

    for i in range(num_points):
        # Which lobe does this point belong to?
        lobe_idx = i // 2

        # Base angle for this point, with per-lobe angular offset
        base_angle = (i / num_points) * 2 * math.pi
        base_angle += math.radians(lobe_angles[lobe_idx % lobe_count])

        # Determine if this is a peak (even) or valley (odd)
        is_peak = (i % 2 == 0)

        # Base radius modifier with per-lobe variation
        if is_peak:
            radius_mod = lobe_radii[lobe_idx % lobe_count]
        else:
            # Valley depth varies with per-lobe depth
            current_lobe_depth = lobe_depths[lobe_idx % lobe_count]
            radius_mod = lobe_radii[lobe_idx % lobe_count] * (1.0 - current_lobe_depth * 0.6)

        # Apply envelope factor: creates asymmetric "protective" bulge
        # Envelope emphasizes the top portion of the form
        envelope_mod = 1.0
        angle_from_top = abs(math.sin(base_angle))  # 0 at top/bottom, 1 at sides
        if math.cos(base_angle) > 0:  # Upper half
            envelope_mod = 1.0 + (envelope_factor - 0.5) * 0.3 * (1 - angle_from_top)

        # Apply wobble: organic perturbation
        wobble_mod = 1.0 + rng.uniform(-wobble, wobble)

        # Combined radius
        radius = radius_mod * envelope_mod * wobble_mod

        # Calculate point position (before rotation)
        px = math.cos(base_angle) * half_width * radius
        py = math.sin(base_angle) * half_height * radius

        # Apply rotation
        rx = px * math.cos(rot_rad) - py * math.sin(rot_rad)
        ry = px * math.sin(rot_rad) + py * math.cos(rot_rad)

        points.append((cx + rx, cy + ry))

    # Build the path with smooth bezier curves
    path = db.BezierPath()

    if len(points) < 3:
        return path

    # Start at first point
    path.moveTo(points[0])

    # Connect points with bezier curves
    for i in range(len(points)):
        p0 = points[i]
        p1 = points[(i + 1) % len(points)]
        p_prev = points[(i - 1) % len(points)]
        p_next = points[(i + 2) % len(points)]

        # Calculate tangent direction at p0 and p1
        # Using Catmull-Rom style tangent calculation
        tangent0 = (
            (p1[0] - p_prev[0]) * 0.5,
            (p1[1] - p_prev[1]) * 0.5
        )
        tangent1 = (
            (p_next[0] - p0[0]) * 0.5,
            (p_next[1] - p0[1]) * 0.5
        )

        # Distance between points
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        dist = math.sqrt(dx * dx + dy * dy)

        # Handle length based on tension and roundness
        # Higher roundness = longer handles = smoother curves
        handle_scale = tension * roundness * 0.5

        # Control points
        cp1 = (
            p0[0] + tangent0[0] * handle_scale,
            p0[1] + tangent0[1] * handle_scale
        )
        cp2 = (
            p1[0] - tangent1[0] * handle_scale,
            p1[1] - tangent1[1] * handle_scale
        )

        path.curveTo(cp1, cp2, p1)

    path.closePath()
    return path


def get_generator_info() -> Dict[str, Any]:
    """Return metadata about this generator."""
    return {
        "name": "soft_blob",
        "version": "1.0.0",
        "description": "Organic bezier-based radial forms suggesting care and safety",
        "parameters": [
            "lobe_count", "lobe_depth", "envelope_factor", "roundness",
            "wobble", "tension", "aspect", "rotation"
        ]
    }
