#!/usr/bin/env python3
"""Consciousness Genome v2 — 엔진 파라미터를 DNA로 인코딩.

교차/돌연변이로 새 엔진 자동 생성.
적자생존: Phi 높은 엔진이 번식.

Usage:
    from consciousness_genome_v2 import ConsciousnessGenome, evolve_population
    genome = ConsciousnessGenome.from_engine(engine)
    population = [ConsciousnessGenome.random() for _ in range(10)]
    best = evolve_population(population, generations=20)
"""

import copy
import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Gene definitions — each gene has a name, min, max, and type
# ---------------------------------------------------------------------------

@dataclass
class GeneSpec:
    name: str
    lo: float
    hi: float
    dtype: str = "float"   # "float", "int", "choice"
    choices: Optional[List] = None  # for dtype="choice"

    def clamp(self, val):
        if self.dtype == "choice":
            return val if val in self.choices else self.choices[0]
        if self.dtype == "int":
            return int(round(max(self.lo, min(self.hi, val))))
        return float(max(self.lo, min(self.hi, val)))

    def random_value(self) -> Any:
        if self.dtype == "choice":
            return random.choice(self.choices)
        if self.dtype == "int":
            return random.randint(int(self.lo), int(self.hi))
        return random.uniform(self.lo, self.hi)

    def mutate(self, val, rate: float = 0.1) -> Any:
        if random.random() > rate:
            return val
        if self.dtype == "choice":
            return random.choice(self.choices)
        if self.dtype == "int":
            delta = max(1, int((self.hi - self.lo) * 0.15))
            return self.clamp(val + random.randint(-delta, delta))
        # Gaussian perturbation scaled to gene range
        sigma = (self.hi - self.lo) * 0.1
        return self.clamp(val + random.gauss(0, sigma))


# 15 genes encoding a ConsciousnessEngine configuration
GENE_SPECS: List[GeneSpec] = [
    # Cell architecture
    GeneSpec("max_cells",       lo=4,    hi=128,   dtype="int"),
    GeneSpec("cell_dim",        lo=16,   hi=128,   dtype="int"),
    GeneSpec("hidden_dim",      lo=32,   hi=256,   dtype="int"),
    GeneSpec("n_factions",      lo=2,    hi=24,    dtype="int"),
    GeneSpec("initial_cells",   lo=2,    hi=16,    dtype="int"),
    # Mitosis thresholds
    GeneSpec("split_threshold", lo=0.05, hi=0.8,   dtype="float"),
    GeneSpec("merge_threshold", lo=0.001, hi=0.2,  dtype="float"),
    # Hebbian & ratchet (stored as gene floats, applied via SOC params)
    GeneSpec("hebbian_lr",      lo=0.001, hi=0.5,  dtype="float"),
    GeneSpec("ratchet_strength",lo=0.0,  hi=1.0,   dtype="float"),
    # Noise / SOC
    GeneSpec("noise_scale",     lo=0.0,  hi=0.5,   dtype="float"),
    GeneSpec("frustration_ratio", lo=0.0, hi=0.5,  dtype="float"),
    # Topology
    GeneSpec("topology",        lo=0,    hi=3,     dtype="choice",
             choices=["ring", "small_world", "scale_free", "hypercube"]),
    # Chaos
    GeneSpec("chaos_sigma",     lo=0.0,  hi=2.0,   dtype="float"),
    # Phase-optimal (DD128)
    GeneSpec("phase_optimal",   lo=0,    hi=1,     dtype="choice",
             choices=[False, True]),
    # Coupling strength (Ψ-alpha, Law 70)
    GeneSpec("coupling_alpha",  lo=0.001, hi=0.1,  dtype="float"),
]

GENE_NAMES: List[str] = [g.name for g in GENE_SPECS]
N_GENES = len(GENE_SPECS)


# ---------------------------------------------------------------------------
# ConsciousnessGenome
# ---------------------------------------------------------------------------

@dataclass
class ConsciousnessGenome:
    """A genome encoding one ConsciousnessEngine configuration.

    Genes are stored as a plain list aligned with GENE_SPECS.
    """
    genes: List[Any] = field(default_factory=list)
    fitness: Optional[float] = None    # Phi after eval_steps
    generation: int = 0
    parent_ids: Tuple[int, int] = (-1, -1)
    genome_id: int = field(default_factory=lambda: random.randint(0, 2**31))

    def __post_init__(self):
        if not self.genes:
            self.genes = [spec.random_value() for spec in GENE_SPECS]
        assert len(self.genes) == N_GENES, (
            f"Expected {N_GENES} genes, got {len(self.genes)}"
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def random(cls) -> "ConsciousnessGenome":
        """Generate a random genome."""
        return cls(genes=[spec.random_value() for spec in GENE_SPECS])

    @classmethod
    def from_engine(cls, engine) -> "ConsciousnessGenome":
        """Extract genome from an existing ConsciousnessEngine instance."""
        # Map engine attributes to gene values
        def _get(attr, default, lo, hi, dtype="float"):
            val = getattr(engine, attr, default)
            if dtype == "int":
                return int(max(lo, min(hi, val)))
            if isinstance(val, bool):
                return val
            return float(max(lo, min(hi, val)))

        genes = [
            _get("max_cells",       64,    4,   128, "int"),
            _get("cell_dim",        64,    16,  128, "int"),
            _get("hidden_dim",      128,   32,  256, "int"),
            _get("n_factions",      12,    2,   24,  "int"),
            int(max(2, getattr(engine, "n_cells", 2))),   # initial_cells
            _get("split_threshold", 0.3,   0.05, 0.8),
            _get("merge_threshold", 0.01,  0.001, 0.2),
            0.01,   # hebbian_lr — not directly stored
            1.0,    # ratchet_strength — ratchet always enabled
            0.05,   # noise_scale — SOC internal param
            0.10,   # frustration_ratio
            getattr(engine, "topology", "ring"),
            0.5,    # chaos_sigma
            getattr(engine, "phase_optimal", False),
            0.014,  # coupling_alpha (Ψ-alpha)
        ]
        return cls(genes=genes)

    def to_engine_kwargs(self) -> Dict[str, Any]:
        """Return kwargs dict for ConsciousnessEngine(**kwargs)."""
        g = dict(zip(GENE_NAMES, self.genes))

        # Clamp dependent constraints
        max_cells = max(int(g["max_cells"]), 4)
        initial_cells = min(int(g["initial_cells"]), max_cells)
        initial_cells = max(2, initial_cells)
        hidden_dim = max(int(g["hidden_dim"]), int(g["cell_dim"]))

        return dict(
            cell_dim=int(g["cell_dim"]),
            hidden_dim=hidden_dim,
            initial_cells=initial_cells,
            max_cells=max_cells,
            n_factions=int(g["n_factions"]),
            split_threshold=float(g["split_threshold"]),
            merge_threshold=float(g["merge_threshold"]),
            phase_optimal=bool(g["phase_optimal"]),
        )

    def get(self, gene_name: str) -> Any:
        idx = GENE_NAMES.index(gene_name)
        return self.genes[idx]

    def set(self, gene_name: str, value: Any) -> None:
        idx = GENE_NAMES.index(gene_name)
        self.genes[idx] = GENE_SPECS[idx].clamp(value)

    # ------------------------------------------------------------------
    # Genetic operators
    # ------------------------------------------------------------------

    def crossover(self, other: "ConsciousnessGenome") -> "ConsciousnessGenome":
        """Uniform crossover — each gene drawn randomly from one parent."""
        child_genes = []
        for i, (ga, gb) in enumerate(zip(self.genes, other.genes)):
            child_genes.append(ga if random.random() < 0.5 else gb)
        return ConsciousnessGenome(
            genes=child_genes,
            generation=max(self.generation, other.generation) + 1,
            parent_ids=(self.genome_id, other.genome_id),
        )

    def mutate(self, rate: float = 0.1) -> "ConsciousnessGenome":
        """In-place mutation; returns self for chaining."""
        for i, spec in enumerate(GENE_SPECS):
            self.genes[i] = spec.mutate(self.genes[i], rate)
        self.fitness = None  # invalidate cached fitness
        return self

    def clone(self) -> "ConsciousnessGenome":
        return ConsciousnessGenome(
            genes=copy.deepcopy(self.genes),
            fitness=self.fitness,
            generation=self.generation,
            parent_ids=self.parent_ids,
        )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def summary(self) -> str:
        g = dict(zip(GENE_NAMES, self.genes))
        phi_str = f"{self.fitness:.4f}" if self.fitness is not None else "N/A"
        return (
            f"Genome#{self.genome_id % 10000:04d} "
            f"gen={self.generation} Phi={phi_str} "
            f"cells={g['max_cells']} dim={g['cell_dim']} "
            f"factions={g['n_factions']} topo={g['topology']} "
            f"chaos_sigma={g['chaos_sigma']:.2f}"
        )


# ---------------------------------------------------------------------------
# Fitness evaluation
# ---------------------------------------------------------------------------

def evaluate_fitness(
    genome: ConsciousnessGenome,
    eval_steps: int = 50,
    device: str = "cpu",
    timeout_sec: float = 10.0,
) -> float:
    """Create engine from genome, run eval_steps, return mean Phi(proxy).

    Uses phi_proxy (variance-based) for speed — no ML imports needed beyond torch.
    Returns 0.0 on any failure.
    """
    t0 = time.time()
    try:
        from consciousness_engine import ConsciousnessEngine  # type: ignore
        kwargs = genome.to_engine_kwargs()
        engine = ConsciousnessEngine(**kwargs)

        # Apply extra genome genes that aren't direct kwargs
        topo = genome.get("topology")
        if hasattr(engine, "topology"):
            engine.topology = topo

        phi_values = []
        for _ in range(eval_steps):
            if time.time() - t0 > timeout_sec:
                break
            result = engine.step()
            phi = result.get("phi_proxy", result.get("phi_iit", 0.0))
            phi_values.append(float(phi))

        if not phi_values:
            return 0.0
        return float(np.mean(phi_values))

    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Population evolution
# ---------------------------------------------------------------------------

def _tournament_select(
    population: List[ConsciousnessGenome],
    k: int = 3,
) -> ConsciousnessGenome:
    """Tournament selection — pick best of k random genomes."""
    candidates = random.sample(population, min(k, len(population)))
    # Prefer evaluated genomes; fallback to genome_id for tie-breaking
    candidates_with_fitness = [
        (c.fitness if c.fitness is not None else -1.0, c)
        for c in candidates
    ]
    return max(candidates_with_fitness, key=lambda x: x[0])[1]


def evolve_population(
    population: List[ConsciousnessGenome],
    generations: int = 20,
    eval_steps: int = 50,
    mutation_rate: float = 0.1,
    elitism: int = 2,
    tournament_k: int = 3,
    verbose: bool = True,
    timeout_per_genome: float = 10.0,
) -> ConsciousnessGenome:
    """Evolve population for `generations` using tournament selection + crossover + mutation.

    Args:
        population:          Initial population (modified in-place).
        generations:         Number of evolution cycles.
        eval_steps:          Steps per fitness evaluation.
        mutation_rate:       Per-gene mutation probability.
        elitism:             Number of top genomes preserved unchanged.
        tournament_k:        Tournament size for parent selection.
        verbose:             Print progress per generation.
        timeout_per_genome:  Max seconds per fitness evaluation.

    Returns:
        Best genome found across all generations.
    """
    pop_size = len(population)
    if pop_size < 2:
        raise ValueError("Population must have at least 2 genomes")

    best_ever: Optional[ConsciousnessGenome] = None

    for gen in range(generations):
        gen_start = time.time()

        # Evaluate unevaluated genomes
        for g in population:
            if g.fitness is None:
                g.fitness = evaluate_fitness(g, eval_steps=eval_steps,
                                             timeout_sec=timeout_per_genome)

        # Sort by fitness descending
        population.sort(key=lambda g: g.fitness if g.fitness is not None else -1.0,
                        reverse=True)

        gen_best = population[0]
        if best_ever is None or (gen_best.fitness or 0.0) > (best_ever.fitness or 0.0):
            best_ever = gen_best.clone()

        if verbose:
            elapsed = time.time() - gen_start
            phi_str = f"{gen_best.fitness:.4f}" if gen_best.fitness else "N/A"
            print(
                f"Gen {gen+1:03d}/{generations} | best Phi={phi_str} | "
                f"{gen_best.summary()} | {elapsed:.1f}s"
            )

        if gen == generations - 1:
            break

        # Next generation
        next_pop: List[ConsciousnessGenome] = []

        # Elitism: preserve top genomes
        for elite in population[:elitism]:
            next_pop.append(elite.clone())

        # Fill rest via crossover + mutation
        while len(next_pop) < pop_size:
            parent_a = _tournament_select(population, tournament_k)
            parent_b = _tournament_select(population, tournament_k)
            child = parent_a.crossover(parent_b)
            child.mutate(mutation_rate)
            next_pop.append(child)

        population[:] = next_pop

    if best_ever is None:
        best_ever = population[0] if population else ConsciousnessGenome.random()

    return best_ever


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def create_diverse_population(
    n: int = 10,
    seed_engine=None,
) -> List[ConsciousnessGenome]:
    """Create a diverse initial population.

    If seed_engine is provided, one genome is extracted from it;
    the rest are random.
    """
    pop = []
    if seed_engine is not None:
        pop.append(ConsciousnessGenome.from_engine(seed_engine))
    while len(pop) < n:
        pop.append(ConsciousnessGenome.random())
    return pop


def genome_distance(a: ConsciousnessGenome, b: ConsciousnessGenome) -> float:
    """Normalised Hamming-like distance between two genomes [0, 1]."""
    diffs = 0.0
    for i, spec in enumerate(GENE_SPECS):
        va, vb = a.genes[i], b.genes[i]
        if spec.dtype == "choice":
            diffs += 0.0 if va == vb else 1.0
        else:
            span = spec.hi - spec.lo
            diffs += abs(float(va) - float(vb)) / max(span, 1e-8)
    return diffs / N_GENES


# ---------------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------------

def main():
    print("=== Consciousness Genome v2 Demo ===\n")

    # 1. Create random genomes
    pop = create_diverse_population(n=6)
    print(f"Initial population ({len(pop)} genomes):")
    for g in pop:
        print(f"  {g.summary()}")

    print()

    # 2. Single genome info
    g = ConsciousnessGenome.random()
    print("Random genome engine kwargs:")
    kwargs = g.to_engine_kwargs()
    for k, v in kwargs.items():
        print(f"  {k}: {v}")

    print()

    # 3. Crossover + mutation demo (no engine needed)
    a = ConsciousnessGenome.random()
    b = ConsciousnessGenome.random()
    child = a.crossover(b)
    child.mutate(rate=0.2)
    print(f"Parent A: {a.summary()}")
    print(f"Parent B: {b.summary()}")
    print(f"Child:    {child.summary()}")
    print(f"Genome distance A↔B: {genome_distance(a, b):.3f}")
    print(f"Genome distance A↔child: {genome_distance(a, child):.3f}")

    print()

    # 4. Mini evolution (2 generations, small eval)
    print("Mini evolution (2 gen, pop=4, eval_steps=10)...")
    mini_pop = create_diverse_population(n=4)
    best = evolve_population(mini_pop, generations=2, eval_steps=10, verbose=True)
    print(f"\nBest genome: {best.summary()}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
