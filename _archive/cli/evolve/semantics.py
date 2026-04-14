"""
Semantic layer for evolutionary forms.

Concepts map to composition, density, and a monochrome form language.
The goal is not to "color-code" the idea, but to make each concept read
through silhouette, edge treatment, and internal structure.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


@dataclass
class Concept:
    """A semantic concept with visual mappings."""

    name: str
    description: str

    # Legacy color ranges remain for prompt semantics, but the renderer stays monochrome.
    hue_range: Tuple[float, float]  # e.g., (200, 240) for blues
    saturation_range: Tuple[float, float]  # e.g., (0.3, 0.7)
    lightness_range: Tuple[float, float]  # e.g., (0.4, 0.6)

    # Composition
    gravity: str = "center"  # center, bottom, top, scatter
    scale_range: Tuple[float, float] = (0.6, 0.8)  # how much of canvas to fill
    density: str = "medium"  # sparse, medium, dense

    # Form bias — which generators suit this concept
    preferred_generators: List[str] = field(default_factory=list)

    # Parameter biases — nudge specific params
    param_biases: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # Textual cue rendered on the form
    glyph: Optional[str] = None  # optional single character/symbol


# The concept vocabulary
CONCEPTS: Dict[str, Concept] = {
    "shelter": Concept(
        name="shelter",
        description="Protection, enclosure, safety",
        hue_range=(200, 260),  # cool blues
        saturation_range=(0.2, 0.5),
        lightness_range=(0.35, 0.55),
        gravity="bottom",
        scale_range=(0.7, 0.9),
        density="medium",
        preferred_generators=["soft_blob", "layered_form", "polygon", "ring"],
        param_biases={
            "envelope_factor": (0.65, 0.9),
            "roundness": (0.6, 0.9),
            "lobe_depth": (0.2, 0.5),
        },
    ),
    "growth": Concept(
        name="growth",
        description="Expansion, emergence, upward energy",
        hue_range=(80, 150),
        saturation_range=(0.4, 0.7),
        lightness_range=(0.4, 0.6),
        gravity="bottom",
        scale_range=(0.5, 0.75),
        density="medium",
        preferred_generators=["soft_blob", "layered_form", "star", "polygon"],
        param_biases={
            "aspect": (0.2, 0.45),
            "asymmetry": (0.3, 0.6),
            "lobe_count": (0.4, 0.8),
        },
    ),
    "tension": Concept(
        name="tension",
        description="Conflict, pressure, opposing forces",
        hue_range=(0, 30),
        saturation_range=(0.5, 0.8),
        lightness_range=(0.4, 0.55),
        gravity="center",
        scale_range=(0.6, 0.85),
        density="dense",
        preferred_generators=["star", "cross", "compound", "shape_outline"],
        param_biases={
            "roundness": (0.0, 0.3),
            "tension": (0.7, 0.9),
            "lobe_depth": (0.5, 0.8),
            "asymmetry": (0.5, 0.9),
        },
    ),
    "connection": Concept(
        name="connection",
        description="Linking, bridging, togetherness",
        hue_range=(270, 320),
        saturation_range=(0.3, 0.6),
        lightness_range=(0.45, 0.65),
        gravity="center",
        scale_range=(0.6, 0.8),
        density="medium",
        preferred_generators=["compound", "ring", "layered_form", "shape_outline"],
        param_biases={
            "dot_density": (0.5, 0.8),
            "accent_count": (0.6, 1.0),
        },
    ),
    "stillness": Concept(
        name="stillness",
        description="Calm, pause, contemplation",
        hue_range=(180, 220),
        saturation_range=(0.1, 0.35),
        lightness_range=(0.5, 0.7),
        gravity="center",
        scale_range=(0.4, 0.6),
        density="sparse",
        preferred_generators=["polygon", "ring", "soft_blob"],
        param_biases={
            "roundness": (0.7, 1.0),
            "wobble": (0.0, 0.05),
            "lobe_depth": (0.0, 0.2),
            "asymmetry": (0.0, 0.2),
        },
    ),
    "chaos": Concept(
        name="chaos",
        description="Disorder, energy, disruption",
        hue_range=(30, 60),
        saturation_range=(0.6, 0.9),
        lightness_range=(0.45, 0.6),
        gravity="scatter",
        scale_range=(0.7, 0.95),
        density="dense",
        preferred_generators=["compound", "layered_form", "star", "shape_outline"],
        param_biases={
            "wobble": (0.1, 0.2),
            "asymmetry": (0.6, 1.0),
            "rotation": (0.0, 1.0),
            "lobe_depth": (0.4, 0.8),
        },
    ),
    "intimacy": Concept(
        name="intimacy",
        description="Closeness, warmth, tenderness",
        hue_range=(340, 370),
        saturation_range=(0.3, 0.55),
        lightness_range=(0.55, 0.7),
        gravity="center",
        scale_range=(0.5, 0.7),
        density="medium",
        preferred_generators=["soft_blob", "ring", "polygon"],
        param_biases={
            "roundness": (0.6, 0.9),
            "envelope_factor": (0.5, 0.8),
            "tension": (0.3, 0.55),
        },
    ),
    "emergence": Concept(
        name="emergence",
        description="Coming into being, threshold, becoming",
        hue_range=(40, 70),
        saturation_range=(0.3, 0.6),
        lightness_range=(0.5, 0.65),
        gravity="bottom",
        scale_range=(0.55, 0.75),
        density="sparse",
        preferred_generators=["layered_form", "star", "polygon", "shape_outline"],
        param_biases={
            "lobe_count": (0.2, 0.5),
            "envelope_factor": (0.4, 0.65),
            "aspect": (0.3, 0.5),
        },
    ),
    "erosion": Concept(
        name="erosion",
        description="Wearing away, time, entropy",
        hue_range=(20, 50),
        saturation_range=(0.15, 0.35),
        lightness_range=(0.4, 0.55),
        gravity="center",
        scale_range=(0.6, 0.8),
        density="sparse",
        preferred_generators=["shape_outline", "layered_form", "cross"],
        param_biases={
            "wobble": (0.08, 0.18),
            "roundness": (0.3, 0.6),
            "lobe_depth": (0.2, 0.5),
        },
    ),
    "rhythm": Concept(
        name="rhythm",
        description="Repetition, pulse, pattern",
        hue_range=(250, 290),
        saturation_range=(0.4, 0.65),
        lightness_range=(0.4, 0.6),
        gravity="center",
        scale_range=(0.6, 0.85),
        density="dense",
        preferred_generators=["layered_form", "polygon", "ring", "star", "compound"],
        param_biases={
            "dot_density": (0.6, 0.9),
            "lobe_count": (0.5, 1.0),
            "asymmetry": (0.0, 0.3),
        },
    ),
}

FORM_LANGUAGE = {
    "shelter": {
        "ink_mode": "banded",
        "line_weight": 1.1,
        "white_band": 7.0,
        "dot_scale": 0.8,
        "accent_scale": 0.7,
    },
    "growth": {
        "ink_mode": "solid",
        "line_weight": 1.0,
        "white_band": 0.0,
        "dot_scale": 0.6,
        "accent_scale": 0.9,
    },
    "tension": {
        "ink_mode": "echo",
        "line_weight": 1.6,
        "white_band": 3.0,
        "dot_scale": 0.9,
        "accent_scale": 1.2,
    },
    "connection": {
        "ink_mode": "outline",
        "line_weight": 1.2,
        "white_band": 0.0,
        "dot_scale": 1.15,
        "accent_scale": 1.4,
    },
    "stillness": {
        "ink_mode": "outline",
        "line_weight": 0.8,
        "white_band": 0.0,
        "dot_scale": 0.55,
        "accent_scale": 0.25,
    },
    "chaos": {
        "ink_mode": "echo",
        "line_weight": 1.4,
        "white_band": 2.0,
        "dot_scale": 1.5,
        "accent_scale": 1.6,
    },
    "intimacy": {
        "ink_mode": "banded",
        "line_weight": 0.95,
        "white_band": 8.0,
        "dot_scale": 0.55,
        "accent_scale": 0.45,
    },
    "emergence": {
        "ink_mode": "solid",
        "line_weight": 1.0,
        "white_band": 0.0,
        "dot_scale": 0.5,
        "accent_scale": 0.75,
    },
    "erosion": {
        "ink_mode": "outline",
        "line_weight": 0.85,
        "white_band": 0.0,
        "dot_scale": 0.7,
        "accent_scale": 0.4,
    },
    "rhythm": {
        "ink_mode": "banded",
        "line_weight": 1.25,
        "white_band": 5.0,
        "dot_scale": 1.25,
        "accent_scale": 0.95,
    },
}


def concept_to_style(concept: Concept, seed: int = 0) -> Dict:
    """
    Generate a style dict from a concept.

    Returns a style dict compatible with render_genome(), plus extra
    semantic fields for the renderer.
    """
    style = FORM_LANGUAGE.get(concept.name, FORM_LANGUAGE["shelter"])

    return {
        "fill_color": [0.0, 0.0, 0.0],
        "stroke_color": [0.0, 0.0, 0.0],
        "stroke_width": 1.5,
        "background": [1.0, 1.0, 1.0],
        "shadow_color": [0.92, 0.92, 0.92],
        # Semantic extras
        "_concept": concept.name,
        "_gravity": concept.gravity,
        "_scale": sum(concept.scale_range) / 2,
        "_density": concept.density,
        "_ink_mode": style["ink_mode"],
        "_line_weight": style["line_weight"],
        "_white_band": style["white_band"],
        "_dot_scale": style["dot_scale"],
        "_accent_scale": style["accent_scale"],
        "_shadow_strength": 0.0,
    }


def pick_generator_for_concept(concept: Concept, rng: random.Random) -> str:
    """Pick a generator that suits this concept."""
    if concept.preferred_generators:
        return rng.choice(concept.preferred_generators)
    from .generators import GENERATORS

    return rng.choice(list(GENERATORS.keys()))


def apply_concept_constraints(
    concept: Concept,
    existing_constraints: Optional[Dict[str, Tuple[float, float]]] = None,
) -> Dict[str, Tuple[float, float]]:
    """Merge concept param biases into constraints."""
    constraints = dict(existing_constraints or {})
    for param, (lo, hi) in concept.param_biases.items():
        if param in constraints:
            old_lo, old_hi = constraints[param]
            constraints[param] = (max(lo, old_lo), min(hi, old_hi))
        else:
            constraints[param] = (lo, hi)
    return constraints


def get_concept(name: str) -> Optional[Concept]:
    """Look up a concept by name."""
    return CONCEPTS.get(name.lower())


def list_concepts() -> List[str]:
    """Return all concept names."""
    return list(CONCEPTS.keys())


def random_concept(rng: Optional[random.Random] = None) -> Concept:
    """Pick a random concept."""
    rng = rng or random.Random()
    return rng.choice(list(CONCEPTS.values()))
