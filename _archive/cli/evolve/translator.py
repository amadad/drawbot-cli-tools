"""
Natural language to parameter constraint translation.

Rule-based system that maps descriptive keywords to parameter ranges.
This provides a deterministic, reproducible starting point for form generation.
"""

import re
from typing import Dict, Tuple, List


# Keyword to parameter constraint mapping
# Values are (min_normalized, max_normalized) ranges
KEYWORD_MAP: Dict[str, Dict[str, Tuple[float, float]]] = {
    # Softness/hardness
    "soft": {"roundness": (0.7, 1.0), "tension": (0.5, 0.8), "wobble": (0.02, 0.1)},
    "gentle": {"roundness": (0.6, 0.9), "tension": (0.4, 0.7), "lobe_depth": (0.1, 0.4)},
    "hard": {"roundness": (0.0, 0.3), "tension": (0.6, 0.9)},
    "angular": {"roundness": (0.0, 0.2), "tension": (0.7, 0.9)},
    "sharp": {"roundness": (0.0, 0.15), "lobe_depth": (0.5, 0.8)},

    # Symmetry/asymmetry
    "symmetric": {"asymmetry": (0.0, 0.15)},
    "balanced": {"asymmetry": (0.0, 0.2)},
    "asymmetric": {"asymmetry": (0.6, 1.0)},
    "irregular": {"asymmetry": (0.5, 0.9), "wobble": (0.08, 0.18)},
    "uneven": {"asymmetry": (0.4, 0.8)},
    "lopsided": {"asymmetry": (0.7, 1.0)},

    # Protection/safety
    "protective": {"envelope_factor": (0.65, 0.9), "lobe_depth": (0.2, 0.5)},
    "safe": {"envelope_factor": (0.6, 0.85), "roundness": (0.5, 0.8)},
    "embracing": {"envelope_factor": (0.7, 0.9), "aspect": (0.4, 0.7)},
    "nurturing": {"envelope_factor": (0.6, 0.85), "roundness": (0.6, 0.9)},
    "sheltering": {"envelope_factor": (0.7, 0.9), "lobe_count": (0.3, 0.6)},

    # Organic/natural
    "organic": {"wobble": (0.1, 0.2), "roundness": (0.4, 0.7), "tension": (0.3, 0.6)},
    "natural": {"wobble": (0.08, 0.15), "roundness": (0.5, 0.8)},
    "flowing": {"tension": (0.3, 0.5), "roundness": (0.6, 0.9)},
    "fluid": {"tension": (0.25, 0.45), "roundness": (0.7, 0.95)},

    # Strength/boldness
    "bold": {"lobe_depth": (0.4, 0.7), "envelope_factor": (0.5, 0.75)},
    "strong": {"lobe_depth": (0.35, 0.6), "aspect": (0.5, 0.65)},
    "powerful": {"lobe_depth": (0.5, 0.8), "lobe_count": (0.6, 1.0)},

    # Delicacy/subtlety
    "delicate": {"wobble": (0.0, 0.05), "lobe_depth": (0.1, 0.3), "roundness": (0.7, 0.95)},
    "subtle": {"lobe_depth": (0.05, 0.25), "wobble": (0.0, 0.08)},
    "light": {"lobe_depth": (0.1, 0.3), "envelope_factor": (0.35, 0.55)},

    # Complexity
    "complex": {"lobe_count": (0.7, 1.0), "lobe_depth": (0.3, 0.6)},
    "simple": {"lobe_count": (0.0, 0.3), "lobe_depth": (0.1, 0.35)},
    "intricate": {"lobe_count": (0.8, 1.0), "wobble": (0.05, 0.12)},

    # Shape descriptors
    "round": {"roundness": (0.8, 1.0), "lobe_depth": (0.0, 0.2)},
    "curved": {"roundness": (0.6, 0.9), "tension": (0.4, 0.7)},
    "wavy": {"lobe_depth": (0.3, 0.5), "tension": (0.35, 0.55)},
    "scalloped": {"lobe_depth": (0.4, 0.7), "roundness": (0.5, 0.8)},

    # Size/proportion
    "tall": {"aspect": (0.25, 0.45)},
    "wide": {"aspect": (0.7, 1.0)},
    "compact": {"aspect": (0.45, 0.55)},

    # Lobe count keywords
    "petals": {"lobe_count": (0.4, 0.8)},
    "lobes": {"lobe_count": (0.4, 0.8)},
    "flower": {"lobe_count": (0.6, 1.0), "roundness": (0.5, 0.8)},
    "clover": {"lobe_count": (0.2, 0.4), "lobe_depth": (0.3, 0.5), "shape_type": (0.75, 0.85)},

    # Shape type keywords (for layered_form)
    "pill": {"shape_type": (0.15, 0.25)},
    "capsule": {"shape_type": (0.15, 0.25)},
    "rectangle": {"shape_type": (0.35, 0.45)},
    "rect": {"shape_type": (0.35, 0.45)},
    "blobby": {"shape_type": (0.55, 0.65)},
    "venn": {"shape_type": (0.9, 1.0)},
    "overlap": {"shape_type": (0.9, 1.0)},

    # Dot grid keywords
    "dense": {"dot_density": (0.7, 1.0)},
    "sparse": {"dot_density": (0.0, 0.3)},
    "dotted": {"dot_density": (0.4, 0.7)},
    "gridded": {"dot_density": (0.5, 0.8)},

    # Shadow keywords
    "shadowed": {"shadow_offset_x": (3.0, 6.0), "shadow_offset_y": (-6.0, -3.0)},
    "floating": {"shadow_offset_x": (4.0, 8.0), "shadow_offset_y": (-8.0, -4.0)},
    "flat": {"shadow_offset_x": (0.0, 1.0), "shadow_offset_y": (-1.0, 0.0)},

    # Stroke weight keywords
    "thin": {"stroke_weight": (0.5, 1.0)},
    "thick": {"stroke_weight": (2.0, 3.0)},
    "medium": {"stroke_weight": (1.2, 1.8)},
}

# Number words mapping
NUMBER_WORDS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
}


def translate_prompt(prompt: str) -> Dict[str, Tuple[float, float]]:
    """
    Translate a natural language prompt to parameter constraints.

    Args:
        prompt: Natural language description like "soft protective 4 lobes"

    Returns:
        Dictionary of {param_name: (min_norm, max_norm)} constraints
    """
    prompt_lower = prompt.lower()
    constraints: Dict[str, Tuple[float, float]] = {}

    # Find matching keywords
    for keyword, param_constraints in KEYWORD_MAP.items():
        # Match whole words only
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, prompt_lower):
            for param, (lo, hi) in param_constraints.items():
                if param in constraints:
                    # Intersect with existing constraint
                    existing_lo, existing_hi = constraints[param]
                    constraints[param] = (
                        max(lo, existing_lo),
                        min(hi, existing_hi)
                    )
                else:
                    constraints[param] = (lo, hi)

    # Look for explicit lobe count numbers
    for word, count in NUMBER_WORDS.items():
        pattern = r'\b' + re.escape(word) + r'\b.*\b(lobe|petal|fold)'
        if re.search(pattern, prompt_lower):
            # Convert count to normalized value (2-6 range)
            norm_val = (count - 2) / 4  # 2->0, 6->1
            constraints["lobe_count"] = (
                max(0, norm_val - 0.1),
                min(1, norm_val + 0.1)
            )
            break

    return constraints


def get_available_keywords() -> List[str]:
    """Return list of all recognized keywords."""
    return sorted(KEYWORD_MAP.keys())


def get_keyword_categories() -> Dict[str, List[str]]:
    """Return keywords organized by semantic category."""
    return {
        "softness": ["soft", "gentle", "hard", "angular", "sharp"],
        "symmetry": ["symmetric", "balanced", "asymmetric", "irregular", "uneven", "lopsided"],
        "protection": ["protective", "safe", "embracing", "nurturing", "sheltering"],
        "organic": ["organic", "natural", "flowing", "fluid"],
        "strength": ["bold", "strong", "powerful"],
        "delicacy": ["delicate", "subtle", "light"],
        "complexity": ["complex", "simple", "intricate"],
        "shape": ["round", "curved", "wavy", "scalloped"],
        "proportion": ["tall", "wide", "compact"],
        "structure": ["petals", "lobes", "flower", "clover"],
    }


def explain_constraints(constraints: Dict[str, Tuple[float, float]]) -> str:
    """
    Generate human-readable explanation of constraints.

    Args:
        constraints: Parameter constraints from translate_prompt()

    Returns:
        Multi-line string explaining each constraint
    """
    if not constraints:
        return "No constraints applied - full parameter range available."

    lines = ["Parameter constraints:"]
    for param, (lo, hi) in sorted(constraints.items()):
        lines.append(f"  {param}: {lo:.2f} - {hi:.2f}")

    return "\n".join(lines)
