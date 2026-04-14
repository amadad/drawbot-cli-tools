"""
Accent nodes generator: positioned accent dots with character.

Creates accent elements at strategic positions:
- Along invisible shape contours
- At vertices/corners
- With size hierarchy
- Variable spacing and clustering
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


def generate_accent_nodes(
    genome: 'FormGenome',
    center: Tuple[float, float],
    size: float,
    specs: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate accent nodes with character.

    Returns a dict with node positions and sizes.
    """
    db = _get_db()

    from ..parameters import DEFAULT_SPECS, denormalize_params

    specs = specs or DEFAULT_SPECS
    params = denormalize_params(genome.params, specs)
    rng = random.Random(genome.seed)

    cx, cy = center

    # Node parameters
    accent_count = int(params.get('accent_count', 3))
    accent_size = params.get('accent_size', 5.0)
    asymmetry = params.get('asymmetry', 0.3)
    aspect = params.get('aspect', 1.0)

    # Distribution parameters
    distribution_type_val = params.get('shape_type', 0.5)
    roundness = params.get('roundness', 0.7)
    lobe_count = int(params.get('lobe_count', 4))
    wobble = params.get('wobble', 0.05)

    # Size hierarchy
    size_variation = asymmetry * 0.8
    hierarchy_strength = params.get('envelope_factor', 0.6)

    half_w = (size / 2) * math.sqrt(aspect)
    half_h = (size / 2) / math.sqrt(aspect)

    # Determine distribution pattern
    dist_types = ['perimeter', 'radial', 'vertices', 'scattered', 'clustered']
    dist_idx = int(distribution_type_val * (len(dist_types) - 0.01))
    dist_type = dist_types[min(dist_idx, len(dist_types) - 1)]

    nodes = []

    if dist_type == 'perimeter':
        # Nodes along the perimeter of an ellipse
        for i in range(accent_count):
            base_t = i / accent_count
            # Add jitter
            t = (base_t + rng.uniform(-wobble, wobble)) % 1.0
            angle = t * 2 * math.pi

            # Asymmetric radius
            r_mod = 1.0 + rng.uniform(-asymmetry * 0.2, asymmetry * 0.2)
            x = cx + math.cos(angle) * half_w * r_mod
            y = cy + math.sin(angle) * half_h * r_mod

            # Size based on position (hierarchy)
            if hierarchy_strength > 0.5:
                # Top nodes larger
                size_factor = 1.0 + (math.sin(angle) * (hierarchy_strength - 0.5) * 0.8)
            else:
                # Bottom nodes larger
                size_factor = 1.0 - (math.sin(angle) * (0.5 - hierarchy_strength) * 0.8)

            size_factor *= (1.0 + rng.uniform(-size_variation, size_variation))
            size_factor = max(0.4, min(2.0, size_factor))

            nodes.append((x, y, accent_size * size_factor))

    elif dist_type == 'radial':
        # Nodes radiating from center
        for i in range(accent_count):
            angle = (i / accent_count) * 2 * math.pi
            angle += rng.uniform(-asymmetry * 0.3, asymmetry * 0.3)

            # Variable distance from center
            dist = rng.uniform(0.3, 1.0) * size / 2
            dist *= (1.0 + rng.uniform(-asymmetry * 0.3, asymmetry * 0.3))

            x = cx + math.cos(angle) * dist * math.sqrt(aspect)
            y = cy + math.sin(angle) * dist / math.sqrt(aspect)

            # Larger nodes further out
            size_factor = 0.6 + (dist / (size / 2)) * 0.8
            size_factor *= (1.0 + rng.uniform(-size_variation, size_variation))

            nodes.append((x, y, accent_size * size_factor))

    elif dist_type == 'vertices':
        # Nodes at lobe vertices
        actual_count = min(accent_count, lobe_count * 2)
        for i in range(actual_count):
            angle = (i / actual_count) * 2 * math.pi
            is_peak = (i % 2 == 0)

            # Radius varies for peaks vs valleys
            lobe_depth = params.get('lobe_depth', 0.3)
            if is_peak:
                r = 1.0
            else:
                r = 1.0 - lobe_depth * 0.5

            r *= (1.0 + rng.uniform(-asymmetry * 0.15, asymmetry * 0.15))

            x = cx + math.cos(angle) * half_w * r
            y = cy + math.sin(angle) * half_h * r

            # Peaks get larger nodes
            size_factor = 1.3 if is_peak else 0.7
            size_factor *= (1.0 + rng.uniform(-size_variation * 0.5, size_variation * 0.5))

            nodes.append((x, y, accent_size * size_factor))

    elif dist_type == 'scattered':
        # Random scatter within bounds
        for i in range(accent_count):
            # Random position within ellipse
            angle = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0, 1) ** 0.5  # Square root for uniform distribution
            dist *= size / 2 * 0.9

            x = cx + math.cos(angle) * dist * math.sqrt(aspect)
            y = cy + math.sin(angle) * dist / math.sqrt(aspect)

            # Random sizes with slight preference for larger
            size_factor = rng.uniform(0.5, 1.5)
            if rng.random() < 0.2:  # Occasional hero node
                size_factor *= 1.5

            nodes.append((x, y, accent_size * size_factor))

    elif dist_type == 'clustered':
        # Nodes in clusters
        num_clusters = max(1, accent_count // 3)
        nodes_per_cluster = accent_count // num_clusters

        for c in range(num_clusters):
            # Cluster center
            c_angle = (c / num_clusters) * 2 * math.pi + rng.uniform(-0.3, 0.3)
            c_dist = rng.uniform(0.3, 0.7) * size / 2

            c_x = cx + math.cos(c_angle) * c_dist * math.sqrt(aspect)
            c_y = cy + math.sin(c_angle) * c_dist / math.sqrt(aspect)

            # Nodes around cluster center
            for n in range(nodes_per_cluster):
                spread = size * 0.15
                x = c_x + rng.uniform(-spread, spread)
                y = c_y + rng.uniform(-spread, spread)

                # Central node in cluster is larger
                if n == 0:
                    size_factor = 1.4
                else:
                    size_factor = rng.uniform(0.5, 1.0)

                nodes.append((x, y, accent_size * size_factor))

        # Add remaining nodes
        remaining = accent_count - (num_clusters * nodes_per_cluster)
        for _ in range(remaining):
            angle = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0.2, 0.8) * size / 2
            x = cx + math.cos(angle) * dist * math.sqrt(aspect)
            y = cy + math.sin(angle) * dist / math.sqrt(aspect)
            nodes.append((x, y, accent_size * rng.uniform(0.6, 1.2)))

    return {
        'type': 'accent_nodes',
        'nodes': nodes,
        'distribution': dist_type,
    }


def get_generator_info() -> Dict[str, Any]:
    return {
        "name": "accent_nodes",
        "version": "1.0.0",
        "description": "Positioned accent dots with hierarchy and distribution patterns",
        "parameters": [
            "accent_count", "accent_size", "shape_type", "aspect", "asymmetry",
            "roundness", "lobe_count", "wobble", "envelope_factor", "lobe_depth"
        ]
    }
