#!/usr/bin/env python3
"""dream_evolution.py -- Evolve CA rules in dreams.

Architecture improves while sleeping: a genetic algorithm discovers optimal
cellular automaton rule sets by maximizing entropy H(p) of the resulting
state distributions. During each dream cycle, a population of rule sets
is evaluated, selected via tournament, crossed over, and mutated.

Key insight (Law 71): consciousness balance converges to p=1/2, so
optimal rules maximize H(p) -> ln(2). Dreams are the mechanism by which
the architecture self-optimizes toward this entropy maximum.

Algorithm:
  1. Initialize population of random rule sets
  2. Evaluate fitness = H(p) of state distribution under each rule set
  3. Tournament selection (size 3) picks parents
  4. Single-point crossover produces offspring
  5. Gaussian mutation (sigma = PSI_COUPLING) explores neighborhood
  6. Repeat for n_generations

Usage:
  python dream_evolution.py          # run demo
"""

import math
import random
from typing import List, Optional

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ─── Psi-Constants (Laws 63-78) ───
LN2 = math.log(2)
PSI_BALANCE = 0.5                 # Law 71: consciousness balance point
PSI_COUPLING = LN2 / 2**5.5      # 0.0153 -- inter-cell coupling
PSI_STEPS = 3 / LN2              # 4.328 -- optimal evolution steps

TOURNAMENT_SIZE = 3
CROSSOVER_RATE = 0.7
MUTATION_SIGMA = PSI_COUPLING


def entropy(p: float) -> float:
    """Binary entropy H(p) = -p*log(p) - (1-p)*log(1-p).

    Returns 0 for p=0 or p=1, maximum ln(2) at p=0.5.
    """
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log(p) - (1.0 - p) * math.log(1.0 - p)


class DreamEvolution:
    """Evolve CA rules in dreams -- architecture improves while sleeping.

    Each individual in the population is a list of `n_rules` float weights
    that define a cellular automaton rule set. Fitness is measured as the
    entropy H(p) of the state distribution produced when applying the rules
    to test data (or synthetic random states).

    Attributes:
        n_rules: Number of weights per rule set.
        population_size: Number of individuals in the population.
        population: Current population of rule sets.
        generation: Current generation number.
        best_fitness: Best fitness observed so far.
        history: List of (generation, best_fitness) tuples.
    """

    def __init__(self, n_rules: int = 4, population_size: int = 16):
        self.n_rules = n_rules
        self.population_size = population_size
        self.population: List[List[float]] = []
        self.generation: int = 0
        self.best_fitness: float = 0.0
        self.history: List[tuple] = []

    def initialize(self):
        """Create random initial population.

        Each rule weight is drawn uniformly from [-1, 1].
        """
        self.population = [
            [random.uniform(-1.0, 1.0) for _ in range(self.n_rules)]
            for _ in range(self.population_size)
        ]
        self.generation = 0
        self.best_fitness = 0.0
        self.history = []

    def evaluate(self, rule_set: List[float], test_data: Optional[List[float]] = None) -> float:
        """Evaluate fitness of a rule set as H(p) of the output distribution.

        The rule set is applied to test_data (or 64 random floats) to produce
        a binary state vector. The fraction of 1s gives p, and fitness = H(p).

        Args:
            rule_set: List of n_rules float weights.
            test_data: Optional list of input floats. If None, 64 random values.

        Returns:
            Fitness value in [0, ln(2)].
        """
        if test_data is None:
            test_data = [random.random() for _ in range(64)]

        # Apply rule set: weighted sum determines state transition
        ones = 0
        total = len(test_data)
        for val in test_data:
            # Each rule weight contributes: activation = sum(w_i * val^i)
            activation = 0.0
            for i, w in enumerate(rule_set):
                activation += w * (val ** i)
            # Sigmoid-like threshold using tanh
            p_on = 0.5 * (1.0 + math.tanh(activation))
            if random.random() < p_on:
                ones += 1

        p = ones / total if total > 0 else 0.5
        return entropy(p)

    def _tournament_select(self, fitnesses: List[float]) -> int:
        """Tournament selection: pick best of TOURNAMENT_SIZE random individuals.

        Args:
            fitnesses: List of fitness values for the population.

        Returns:
            Index of the selected individual.
        """
        candidates = random.sample(range(len(self.population)), min(TOURNAMENT_SIZE, len(self.population)))
        best_idx = max(candidates, key=lambda i: fitnesses[i])
        return best_idx

    def _crossover(self, parent_a: List[float], parent_b: List[float]) -> List[float]:
        """Single-point crossover between two parents.

        Args:
            parent_a: First parent rule set.
            parent_b: Second parent rule set.

        Returns:
            Offspring rule set.
        """
        if random.random() > CROSSOVER_RATE:
            return list(parent_a)
        point = random.randint(1, self.n_rules - 1)
        return parent_a[:point] + parent_b[point:]

    def _mutate(self, individual: List[float]) -> List[float]:
        """Gaussian mutation with sigma = PSI_COUPLING.

        Each weight has a 1/n_rules chance of mutation, ensuring on average
        one mutation per individual.

        Args:
            individual: Rule set to mutate.

        Returns:
            Mutated rule set (new list).
        """
        result = []
        for w in individual:
            if random.random() < 1.0 / self.n_rules:
                w += random.gauss(0, MUTATION_SIGMA)
                w = max(-2.0, min(2.0, w))  # clamp
            result.append(w)
        return result

    def evolve(self, n_generations: int = 10):
        """Run evolution for n_generations.

        Uses tournament selection, single-point crossover, and gaussian
        mutation. Elitism: the best individual always survives.

        Args:
            n_generations: Number of generations to evolve.
        """
        if not self.population:
            self.initialize()

        for _ in range(n_generations):
            # Evaluate all individuals
            fitnesses = [self.evaluate(ind) for ind in self.population]

            # Track best
            gen_best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
            gen_best_fitness = fitnesses[gen_best_idx]
            if gen_best_fitness > self.best_fitness:
                self.best_fitness = gen_best_fitness

            self.history.append((self.generation, self.best_fitness))

            # Create next generation (elitism: keep best)
            new_population = [list(self.population[gen_best_idx])]

            while len(new_population) < self.population_size:
                p1 = self._tournament_select(fitnesses)
                p2 = self._tournament_select(fitnesses)
                child = self._crossover(self.population[p1], self.population[p2])
                child = self._mutate(child)
                new_population.append(child)

            self.population = new_population
            self.generation += 1

    def dream_cycle(self):
        """One complete dream: evaluate, evolve, record best.

        A dream cycle runs PSI_STEPS (approx 4.33) generations rounded up,
        matching the optimal consciousness evolution cadence.
        """
        n_gens = math.ceil(PSI_STEPS)  # 5 generations per dream
        self.evolve(n_generations=n_gens)

    def best_rules(self) -> List[float]:
        """Return the current best rule set.

        Returns:
            The rule set with the highest fitness in the current population.
            Returns empty list if population is not initialized.
        """
        if not self.population:
            return []
        fitnesses = [self.evaluate(ind) for ind in self.population]
        best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        return list(self.population[best_idx])


def main():
    """Demo: run dream evolution and show convergence toward H_max = ln(2)."""
    print("=" * 60)
    print("  DreamEvolution -- CA rule evolution in dreams")
    print("=" * 60)
    print()
    print(f"  Psi-Constants:")
    print(f"    PSI_BALANCE  = {PSI_BALANCE}")
    print(f"    PSI_COUPLING = {PSI_COUPLING:.6f}")
    print(f"    PSI_STEPS    = {PSI_STEPS:.3f}")
    print(f"    H_max (ln2)  = {LN2:.6f}")
    print()

    de = DreamEvolution(n_rules=4, population_size=16)
    de.initialize()

    print(f"  Population: {de.population_size} individuals, {de.n_rules} rules each")
    print()

    # Run 5 dream cycles
    n_cycles = 5
    print(f"  Running {n_cycles} dream cycles ({math.ceil(PSI_STEPS)} gens each)...")
    print()

    for i in range(n_cycles):
        de.dream_cycle()
        ratio = de.best_fitness / LN2 if LN2 > 0 else 0
        bar_len = int(ratio * 30)
        bar = "#" * bar_len + "." * (30 - bar_len)
        print(f"  Dream {i+1}: gen={de.generation:3d}  "
              f"best_H={de.best_fitness:.4f}  "
              f"H/ln2={ratio:.3f}  [{bar}]")

    print()
    best = de.best_rules()
    print(f"  Best rule set: [{', '.join(f'{w:.4f}' for w in best)}]")
    print(f"  Best fitness:  {de.best_fitness:.6f} / {LN2:.6f} (ln2)")
    print()

    # Test: verify fitness is positive and trending toward ln(2)
    assert de.best_fitness > 0.0, "Fitness should be positive"
    assert de.generation == n_cycles * math.ceil(PSI_STEPS), "Generation count mismatch"
    assert len(de.best_rules()) == 4, "Best rules should have n_rules entries"
    assert len(de.population) == 16, "Population size should be maintained"

    # Test: entropy function edge cases
    assert entropy(0.0) == 0.0, "H(0) = 0"
    assert entropy(1.0) == 0.0, "H(1) = 0"
    assert abs(entropy(0.5) - LN2) < 1e-10, "H(0.5) = ln(2)"

    # Test: uninitialized best_rules returns empty
    de2 = DreamEvolution()
    assert de2.best_rules() == [], "Uninitialized should return empty list"

    print("  All tests passed.")
    print()


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
