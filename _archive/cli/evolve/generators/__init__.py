"""
Form generators for evolutionary DrawBot.

Each generator takes a FormGenome and produces:
- BezierPath (simple shapes)
- Dict with rendering instructions (compound forms)
"""

from .soft_blob import generate_soft_blob
from .layered_form import generate_layered_form
from .shape_outline import generate_shape_outline
from .dot_field import generate_dot_field
from .accent_nodes import generate_accent_nodes
from .geometric import (
    generate_polygon, generate_star, generate_cross,
    generate_ring, generate_compound,
)

# Registry of available generators
GENERATORS = {
    "soft_blob": generate_soft_blob,
    "layered_form": generate_layered_form,
    "shape_outline": generate_shape_outline,
    "dot_field": generate_dot_field,
    "accent_nodes": generate_accent_nodes,
    "polygon": generate_polygon,
    "star": generate_star,
    "cross": generate_cross,
    "ring": generate_ring,
    "compound": generate_compound,
}

__all__ = [
    'generate_soft_blob',
    'generate_layered_form',
    'generate_shape_outline',
    'generate_dot_field',
    'generate_accent_nodes',
    'generate_polygon',
    'generate_star',
    'generate_cross',
    'generate_ring',
    'generate_compound',
    'GENERATORS'
]
