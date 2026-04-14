"""
Evolutionary breeding and mutation functions.

Handles crossover between parent genomes and random mutation to create
new generations of forms.
"""

import random
from typing import List, Dict, Tuple, Optional

from .genome import FormGenome
from .parameters import ParameterSpec, DEFAULT_SPECS


def breed(
    parent_a: FormGenome,
    parent_b: FormGenome,
    gen_num: int,
    idx: int,
    crossover_method: str = "uniform"
) -> FormGenome:
    """
    Create offspring by combining two parent genomes.

    Args:
        parent_a: First parent genome
        parent_b: Second parent genome
        gen_num: Generation number for the child
        idx: Index within the new generation (1-based)
        crossover_method: "uniform" (random per param) or "single_point"

    Returns:
        New FormGenome with mixed parameters from both parents
    """
    child_params = {}

    if crossover_method == "uniform":
        # Uniform crossover: randomly pick each parameter from one parent
        for name in parent_a.params.keys():
            if random.random() < 0.5:
                child_params[name] = parent_a.params.get(name, 0.5)
            else:
                child_params[name] = parent_b.params.get(name, 0.5)
    else:
        # Single-point crossover
        param_names = list(parent_a.params.keys())
        crossover_point = random.randint(1, len(param_names) - 1)

        for i, name in enumerate(param_names):
            if i < crossover_point:
                child_params[name] = parent_a.params.get(name, 0.5)
            else:
                child_params[name] = parent_b.params.get(name, 0.5)

    # Randomly inherit generator from either parent
    child_generator = random.choice([parent_a.generator, parent_b.generator])

    return FormGenome(
        id=f"gen{gen_num:03d}_{idx:04d}",
        generator=child_generator,
        params=child_params,
        seed=random.randint(0, 2**31 - 1),
        parents=(parent_a.id, parent_b.id),
        prompt=parent_a.prompt or parent_b.prompt,
    )


def mutate(
    genome: FormGenome,
    rate: float = 0.2,
    strength: float = 0.15
) -> FormGenome:
    """
    Apply random mutations to a genome's parameters.

    Args:
        genome: The genome to mutate
        rate: Probability of mutating each parameter (0-1)
        strength: Maximum mutation magnitude as fraction of [0..1] range

    Returns:
        New FormGenome with mutated parameters (original unchanged)
    """
    mutated_params = {}

    for name, value in genome.params.items():
        if random.random() < rate:
            # Apply mutation
            delta = random.uniform(-strength, strength)
            new_value = value + delta
            # Clamp to [0, 1]
            mutated_params[name] = max(0.0, min(1.0, new_value))
        else:
            mutated_params[name] = value

    return FormGenome(
        id=genome.id,
        generator=genome.generator,
        params=mutated_params,
        seed=genome.seed,  # Keep same seed for reproducibility
        parents=genome.parents,
        prompt=genome.prompt,
        created_at=genome.created_at,
    )


def generate_population(
    size: int,
    gen_num: int,
    parents: Optional[List[FormGenome]] = None,
    specs: Optional[Dict[str, ParameterSpec]] = None,
    prompt_constraints: Optional[Dict[str, Tuple[float, float]]] = None,
    mutation_rate: float = 0.2,
    mutation_strength: float = 0.15,
    generator: str = "soft_blob"
) -> List[FormGenome]:
    """
    Generate a population of genomes.

    If parents are provided, breeds from them. Otherwise creates random genomes.

    Args:
        size: Number of genomes to generate
        gen_num: Generation number
        parents: Optional list of parent genomes to breed from
        specs: Parameter specifications
        prompt_constraints: Optional constraints as {param: (min_norm, max_norm)}
        mutation_rate: Probability of mutating each param
        mutation_strength: Maximum mutation magnitude
        generator: Generator type for new genomes

    Returns:
        List of FormGenome objects
    """
    specs = specs or DEFAULT_SPECS
    population = []

    if parents and len(parents) > 0:
        # Breeding mode: create children from parents
        for i in range(size):
            # Select two parents (with replacement)
            parent_a = random.choice(parents)
            parent_b = random.choice(parents)

            # Breed
            child = breed(parent_a, parent_b, gen_num, i + 1)

            # Mutate
            child = mutate(child, mutation_rate, mutation_strength)

            population.append(child)
    else:
        # Random initialization mode
        for i in range(size):
            genome = FormGenome.random(
                gen_num=gen_num,
                idx=i + 1,
                specs=specs,
                generator=generator,
                constraints=prompt_constraints,
            )
            population.append(genome)

    return population


def select_winners(
    population: List[FormGenome],
    winner_indices: List[int]
) -> List[FormGenome]:
    """
    Select winner genomes from population by index.

    Args:
        population: Full population list
        winner_indices: 1-based indices of winners

    Returns:
        List of selected FormGenome objects
    """
    winners = []
    for idx in winner_indices:
        if 1 <= idx <= len(population):
            winners.append(population[idx - 1])
    return winners


def calculate_diversity(population: List[FormGenome]) -> float:
    """
    Calculate genetic diversity of a population.

    Returns average pairwise distance in parameter space.

    Args:
        population: List of genomes

    Returns:
        Diversity score (0 = identical, higher = more diverse)
    """
    if len(population) < 2:
        return 0.0

    total_distance = 0.0
    comparisons = 0

    for i, genome_a in enumerate(population):
        for genome_b in population[i + 1:]:
            # Calculate Euclidean distance in normalized param space
            dist_sq = 0.0
            for name in genome_a.params.keys():
                diff = genome_a.params.get(name, 0.5) - genome_b.params.get(name, 0.5)
                dist_sq += diff * diff
            total_distance += dist_sq ** 0.5
            comparisons += 1

    return total_distance / comparisons if comparisons > 0 else 0.0
