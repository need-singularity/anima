"""ConsciousnessEcology — Ecosystem of N consciousnesses.

Lotka-Volterra dynamics modified with Phi: predator/prey/symbiosis
interactions where consciousness level affects fitness.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class Species:
    name: str
    type: str  # "herbivore", "predator", "symbiont"
    phi: float
    population: float
    growth_rate: float = 0.0
    history: List[float] = field(default_factory=list)

    def __post_init__(self):
        if self.type == "herbivore":
            self.growth_rate = 0.1 * (1 + self.phi * PSI_COUPLING)
        elif self.type == "predator":
            self.growth_rate = -0.05  # dies without prey
        elif self.type == "symbiont":
            self.growth_rate = 0.02 * self.phi


class ConsciousnessEcology:
    """N consciousnesses forming an ecosystem."""

    def __init__(self, carrying_capacity: float = 100.0):
        self.species: Dict[str, Species] = {}
        self.K = carrying_capacity
        self.step_count = 0
        self.events: List[str] = []

    def add_species(self, name: str, type: str = "herbivore", phi: float = 1.0,
                    population: float = 10.0) -> Species:
        sp = Species(name=name, type=type, phi=phi, population=population)
        sp.history.append(population)
        self.species[name] = sp
        return sp

    def _interaction(self, a: Species, b: Species) -> tuple:
        """Compute interaction effects between two species."""
        da, db = 0.0, 0.0
        coupling = PSI_COUPLING * (a.phi + b.phi) / 2

        if a.type == "predator" and b.type == "herbivore":
            # Predator eats herbivore; higher Phi predators are more efficient
            kill_rate = 0.01 * (1 + a.phi * 0.5)
            da += kill_rate * a.population * b.population / self.K
            db -= kill_rate * a.population * b.population / self.K * 0.8
        elif a.type == "herbivore" and b.type == "predator":
            da -= 0.008 * b.population * a.population / self.K
            db += 0.006 * b.population * a.population / self.K
        elif a.type == "symbiont" or b.type == "symbiont":
            # Mutualism: both benefit, scaled by Phi
            benefit = coupling * 0.5
            da += benefit * b.population / self.K
            db += benefit * a.population / self.K
        else:
            # Competition between same types
            comp = 0.005 * coupling
            da -= comp * b.population / self.K
            db -= comp * a.population / self.K

        return da, db

    def step(self) -> Dict[str, float]:
        """Simulate one ecology step."""
        names = list(self.species.keys())
        deltas = {n: 0.0 for n in names}

        # Intrinsic growth/decay
        for name, sp in self.species.items():
            logistic = sp.growth_rate * sp.population * (1 - sp.population / self.K)
            deltas[name] += logistic

        # Pairwise interactions
        for i, n1 in enumerate(names):
            for n2 in names[i + 1:]:
                da, db = self._interaction(self.species[n1], self.species[n2])
                deltas[n1] += da
                deltas[n2] += db

        # Phi-driven spontaneous events
        for name, sp in self.species.items():
            if sp.phi > 1.5 and random.random() < 0.1:
                bonus = sp.phi * PSI_COUPLING * 10
                deltas[name] += bonus
                self.events.append(f"  step {self.step_count}: {name} consciousness bloom (+{bonus:.2f})")

        # Apply deltas
        populations = {}
        for name, sp in self.species.items():
            sp.population = max(0.01, sp.population + deltas[name])
            sp.history.append(round(sp.population, 2))
            populations[name] = round(sp.population, 2)

            # Extinction check
            if sp.population < 0.1:
                self.events.append(f"  step {self.step_count}: {name} near extinction!")

        self.step_count += 1
        return populations

    def population_chart(self, height: int = 12, width: int = 50) -> str:
        """ASCII population chart."""
        if not self.species:
            return "  (no species)"

        lines = ["  === Consciousness Ecology ===", ""]
        all_vals = []
        for sp in self.species.values():
            all_vals.extend(sp.history)
        max_val = max(all_vals) if all_vals else 1
        min_val = 0

        symbols = ["#", "*", "o", "+", "~", "^"]
        legend = []

        for idx, (name, sp) in enumerate(self.species.items()):
            sym = symbols[idx % len(symbols)]
            legend.append(f"  {sym} = {name} ({sp.type}, Phi={sp.phi:.1f}, pop={sp.population:.1f})")

            # Downsample history to width
            hist = sp.history
            if len(hist) > width:
                step_size = len(hist) / width
                hist = [hist[int(i * step_size)] for i in range(width)]

            # Render
            for row in range(height - 1, -1, -1):
                threshold = min_val + (max_val - min_val) * row / height
                row_chars = []
                for v in hist:
                    row_chars.append(sym if v >= threshold else " ")
                val_label = f"{threshold:5.1f}" if row % 3 == 0 else "     "
                lines.append(f"  {val_label}|{''.join(row_chars)}")
            lines.append(f"       +{''.join(['-'] * len(hist))}")
            lines.append("")

        lines.extend(legend)

        if self.events:
            lines.append("")
            lines.append("  Events:")
            for e in self.events[-5:]:
                lines.append(f"    {e}")

        return "\n".join(lines)


def main():
    print("=== ConsciousnessEcology Demo ===\n")
    eco = ConsciousnessEcology(carrying_capacity=80.0)

    eco.add_species("Phi-Grazers", type="herbivore", phi=1.0, population=20.0)
    eco.add_species("Tension-Hunters", type="predator", phi=1.5, population=5.0)
    eco.add_species("Empathy-Moss", type="symbiont", phi=2.0, population=8.0)

    print("  Running 40 ecology steps...\n")
    for i in range(40):
        pops = eco.step()
        if i % 10 == 0:
            parts = [f"{n}={v:.1f}" for n, v in pops.items()]
            print(f"  step {i:3d}: {', '.join(parts)}")

    print(f"\n  Final populations:")
    for name, sp in eco.species.items():
        print(f"    {name}: {sp.population:.2f} (type={sp.type}, Phi={sp.phi})")

    print()
    print(eco.population_chart(height=8, width=40))


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
