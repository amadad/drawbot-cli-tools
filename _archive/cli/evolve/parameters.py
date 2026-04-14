"""
Parameter specification for evolutionary form generation.

Parameters are stored normalized to [0..1] internally for clean breeding math,
but can be converted to/from actual ranges for rendering.
"""

from dataclasses import dataclass
from typing import Dict, Any, Union
from pathlib import Path
import json


@dataclass
class ParameterSpec:
    """Specification for a single form parameter with normalized mapping."""

    name: str
    min_val: float
    max_val: float
    default: float
    kind: str = "float"  # "float" or "int"
    description: str = ""

    def normalize(self, value: Union[int, float]) -> float:
        """Map actual value to [0..1] range."""
        if self.max_val == self.min_val:
            return 0.5
        return (value - self.min_val) / (self.max_val - self.min_val)

    def denormalize(self, norm: float) -> Union[int, float]:
        """Map [0..1] back to actual range."""
        value = self.min_val + norm * (self.max_val - self.min_val)
        if self.kind == "int":
            return int(round(value))
        return value

    def clamp_normalized(self, norm: float) -> float:
        """Clamp normalized value to [0..1]."""
        return max(0.0, min(1.0, norm))

    def default_normalized(self) -> float:
        """Get default value in normalized form."""
        return self.normalize(self.default)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON storage."""
        return {
            "name": self.name,
            "min": self.min_val,
            "max": self.max_val,
            "default": self.default,
            "kind": self.kind,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, name: str, d: Dict[str, Any]) -> 'ParameterSpec':
        """Create from dict (e.g., from brand_dna.json)."""
        return cls(
            name=name,
            min_val=d.get("min", 0.0),
            max_val=d.get("max", 1.0),
            default=d.get("default", 0.5),
            kind=d.get("kind", "float"),
            description=d.get("description", ""),
        )


# Default parameter specifications for soft_blob generator
DEFAULT_SPECS: Dict[str, ParameterSpec] = {
    "lobe_count": ParameterSpec(
        name="lobe_count",
        min_val=2,
        max_val=6,
        default=4,
        kind="int",
        description="Number of radial lobes/petals"
    ),
    "lobe_depth": ParameterSpec(
        name="lobe_depth",
        min_val=0.0,
        max_val=1.0,
        default=0.3,
        kind="float",
        description="Indent depth between lobes (0=circle, 1=deep scallops)"
    ),
    "envelope_factor": ParameterSpec(
        name="envelope_factor",
        min_val=0.3,
        max_val=0.9,
        default=0.6,
        kind="float",
        description="Protective/embracing quality (asymmetric bulge)"
    ),
    "roundness": ParameterSpec(
        name="roundness",
        min_val=0.0,
        max_val=1.0,
        default=0.7,
        kind="float",
        description="Curve smoothness (0=angular, 1=smooth)"
    ),
    "wobble": ParameterSpec(
        name="wobble",
        min_val=0.0,
        max_val=0.2,
        default=0.05,
        kind="float",
        description="Organic irregularity/hand-drawn feel"
    ),
    "tension": ParameterSpec(
        name="tension",
        min_val=0.3,
        max_val=0.9,
        default=0.6,
        kind="float",
        description="Bezier handle length (tight vs flowing curves)"
    ),
    "aspect": ParameterSpec(
        name="aspect",
        min_val=0.6,
        max_val=1.4,
        default=1.0,
        kind="float",
        description="Width/height ratio"
    ),
    "rotation": ParameterSpec(
        name="rotation",
        min_val=0,
        max_val=360,
        default=0,
        kind="float",
        description="Base orientation in degrees"
    ),
    "asymmetry": ParameterSpec(
        name="asymmetry",
        min_val=0.0,
        max_val=1.0,
        default=0.3,
        kind="float",
        description="Break radial symmetry (0=symmetric, 1=highly asymmetric)"
    ),
}


def load_specs_from_config(config_path: Path) -> Dict[str, ParameterSpec]:
    """Load parameter specs from brand_dna.json config file."""
    if not config_path.exists():
        return DEFAULT_SPECS.copy()

    with open(config_path, 'r') as f:
        config = json.load(f)

    specs = {}
    param_configs = config.get("parameter_specs", {})

    for name, param_dict in param_configs.items():
        specs[name] = ParameterSpec.from_dict(name, param_dict)

    # Fill in any missing specs with defaults
    for name, spec in DEFAULT_SPECS.items():
        if name not in specs:
            specs[name] = spec

    return specs


def denormalize_params(
    normalized: Dict[str, float],
    specs: Dict[str, ParameterSpec]
) -> Dict[str, Union[int, float]]:
    """Convert all normalized params to actual values."""
    return {
        name: specs[name].denormalize(value)
        for name, value in normalized.items()
        if name in specs
    }


def normalize_params(
    actual: Dict[str, Union[int, float]],
    specs: Dict[str, ParameterSpec]
) -> Dict[str, float]:
    """Convert all actual params to normalized [0..1] values."""
    return {
        name: specs[name].normalize(value)
        for name, value in actual.items()
        if name in specs
    }
