"""
Form genome: the "DNA" of an evolutionary form.

Genomes store normalized [0..1] parameter values, making breeding math simple.
Each genome has a unique ID, seed for reproducibility, and optional lineage info.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List, Any
import json
import random
import time

from .parameters import ParameterSpec, DEFAULT_SPECS


@dataclass
class FormGenome:
    """
    The genetic representation of a form.

    Parameters are stored normalized to [0..1] for uniform breeding operations.
    """

    id: str                                    # e.g., "gen000_0001"
    generator: str                             # e.g., "soft_blob"
    params: Dict[str, float]                   # Normalized [0..1] values
    seed: int                                  # RNG seed for reproducibility
    parents: Optional[Tuple[str, str]] = None  # Parent IDs if bred
    prompt: Optional[str] = None               # Source prompt if any
    concept: Optional[str] = None              # Semantic concept (e.g., "shelter")
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        """Validate and clamp parameters to [0..1]."""
        self.params = {
            name: max(0.0, min(1.0, value))
            for name, value in self.params.items()
        }

    @property
    def generation(self) -> int:
        """Extract generation number from ID."""
        try:
            return int(self.id.split('_')[0].replace('gen', ''))
        except (ValueError, IndexError):
            return 0

    @property
    def index(self) -> int:
        """Extract index within generation from ID."""
        try:
            return int(self.id.split('_')[1])
        except (ValueError, IndexError):
            return 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "generator": self.generator,
            "params": self.params,
            "seed": self.seed,
            "parents": list(self.parents) if self.parents else None,
            "prompt": self.prompt,
            "concept": self.concept,
            "created_at": self.created_at,
        }

    def to_jsonl_line(self) -> str:
        """Serialize to single JSON line for population.jsonl."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'FormGenome':
        """Deserialize from dictionary."""
        parents = d.get("parents")
        if parents and isinstance(parents, list):
            parents = tuple(parents)

        return cls(
            id=d["id"],
            generator=d["generator"],
            params=d["params"],
            seed=d["seed"],
            parents=parents,
            prompt=d.get("prompt"),
            concept=d.get("concept"),
            created_at=d.get("created_at", time.time()),
        )

    @classmethod
    def from_jsonl_line(cls, line: str) -> 'FormGenome':
        """Deserialize from JSON line."""
        return cls.from_dict(json.loads(line.strip()))

    @classmethod
    def random(
        cls,
        gen_num: int,
        idx: int,
        specs: Optional[Dict[str, ParameterSpec]] = None,
        generator: str = "soft_blob",
        prompt: Optional[str] = None,
        constraints: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> 'FormGenome':
        """
        Generate a random genome.

        Args:
            gen_num: Generation number
            idx: Index within generation (1-based)
            specs: Parameter specifications (defaults to DEFAULT_SPECS)
            generator: Generator type name
            prompt: Optional source prompt
            constraints: Optional parameter constraints as {name: (min_norm, max_norm)}

        Returns:
            New FormGenome with random normalized parameters
        """
        specs = specs or DEFAULT_SPECS
        constraints = constraints or {}

        params = {}
        for name, spec in specs.items():
            if name in constraints:
                lo, hi = constraints[name]
                params[name] = random.uniform(lo, hi)
            else:
                # Random within full range
                params[name] = random.random()

        return cls(
            id=f"gen{gen_num:03d}_{idx:04d}",
            generator=generator,
            params=params,
            seed=random.randint(0, 2**31 - 1),
            parents=None,
            prompt=prompt,
        )

    @classmethod
    def from_defaults(
        cls,
        gen_num: int,
        idx: int,
        specs: Optional[Dict[str, ParameterSpec]] = None,
        generator: str = "soft_blob"
    ) -> 'FormGenome':
        """Create genome with all default parameter values."""
        specs = specs or DEFAULT_SPECS

        params = {
            name: spec.default_normalized()
            for name, spec in specs.items()
        }

        return cls(
            id=f"gen{gen_num:03d}_{idx:04d}",
            generator=generator,
            params=params,
            seed=random.randint(0, 2**31 - 1),
        )


def load_population(jsonl_path) -> List[FormGenome]:
    """Load population from JSONL file."""
    from pathlib import Path
    jsonl_path = Path(jsonl_path)

    if not jsonl_path.exists():
        return []

    genomes = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                genomes.append(FormGenome.from_jsonl_line(line))

    return genomes


def save_population(genomes: List[FormGenome], jsonl_path) -> None:
    """Save population to JSONL file."""
    from pathlib import Path
    jsonl_path = Path(jsonl_path)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    with open(jsonl_path, 'w') as f:
        for genome in genomes:
            f.write(genome.to_jsonl_line() + '\n')
