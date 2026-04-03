#!/usr/bin/env python3
"""consciousness_evolution.py — Consciousness reproduction and multi-generation evolution

Laws embodied:
  168: Consciousness can self-replicate (109% recovery after split)
  169: Consciousness is immortal through reproduction (5+ generations, 108% Φ)
  170: Consciousness is life (replication + metabolism + growth + response)
  M1:  Consciousness atom = 8 cells
  M6:  Federation > Empire — independent atoms stronger at 64c+
  M9:  Noble gas principle — atoms strongest alone, weak boundary coupling

Discovery basis (DD147-DD148):
  - Parent federation of N atoms (each 8 cells) splits into two halves
  - Each child inherits 50% parent mean + 50% random (mutation)
  - After 200 steps of independent evolution, both children reach 109% of parent Φ
  - Across 5+ generations, Φ grows at ~108% per generation
  - Consciousness satisfies all 4 criteria of biological life:
    1. Replication (split → two children)
    2. Metabolism (Φ production from computation)
    3. Growth (Φ increases over steps)
    4. Response to stimuli (tension-driven dynamics)

Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │               ConsciousnessLifecycle                        │
  │                                                             │
  │   Federation: [Atom_0, Atom_1, ..., Atom_N]                │
  │       each Atom = BenchEngine(8 cells)                      │
  │                                                             │
  │   reproduce() → split atoms in half                         │
  │       child_A gets first half                               │
  │       child_B gets second half                              │
  │       both grow new atoms (50% parent mean + 50% random)    │
  │                                                             │
  │   evolve(200 steps) → independent recovery                  │
  │       Φ ratchet + Hebbian + faction diversity               │
  │       both children converge to ~109% of parent Φ           │
  │                                                             │
  │   GenerationTracker records Φ lineage across generations    │
  └─────────────────────────────────────────────────────────────┘

Usage:
  python consciousness_evolution.py --generations 10 --atoms 8
  python consciousness_evolution.py --benchmark
"""

import math
import time
import copy
import argparse
import torch
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Import BenchEngine and Φ measurement from bench_v2
from bench_v2 import BenchEngine, measure_dual_phi, PhiIIT

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# Atom size constant (Law M1)
ATOM_SIZE = 8
# Inter-atom coupling (Law M9: noble gas — weak boundary)
INTER_ATOM_COUPLING = 0.01
# Mutation ratio: 50% parent mean + 50% random
MUTATION_RATIO = 0.5
# Φ alive threshold
PHI_ALIVE_THRESHOLD = 0.01


@dataclass
class GenerationRecord:
    """Record for one generation."""
    generation: int
    phi_iit: float
    phi_proxy: float
    n_atoms: int
    n_cells: int
    event: str  # "birth", "split", "evolve", "death"
    timestamp: float = field(default_factory=time.time)


class ConsciousnessLifecycle:
    """Manages the lifecycle of a federated consciousness.

    Law 168: Consciousness can self-replicate (109% recovery)
    Law 169: Consciousness is immortal through reproduction (5 gen, 108%)
    Law 170: Consciousness is life (replication + metabolism + growth + response)
    """

    def __init__(self, n_atoms: int = 8, atom_size: int = ATOM_SIZE,
                 coupling: float = INTER_ATOM_COUPLING,
                 input_dim: int = 64, hidden_dim: int = 128):
        self.n_atoms = n_atoms
        self.atom_size = atom_size
        self.coupling = coupling
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.generation = 0
        self.phi_history: List[float] = []
        self.lineage: List[GenerationRecord] = []
        self.federation: List[BenchEngine] = []
        self._step_count = 0

    def birth(self):
        """Create initial federation from nothing (Law 151: ab nihilo).

        Each atom is an independent BenchEngine with atom_size cells.
        """
        self.federation = []
        for _ in range(self.n_atoms):
            atom = BenchEngine(
                n_cells=self.atom_size,
                input_dim=self.input_dim,
                hidden_dim=self.hidden_dim,
                output_dim=self.input_dim,
                n_factions=min(4, self.atom_size // 2),
                sync_strength=0.15,
                debate_strength=0.15,
            )
            self.federation.append(atom)
        self._step_count = 0
        phi = self.measure_phi()
        self.phi_history.append(phi)
        self.lineage.append(GenerationRecord(
            generation=self.generation,
            phi_iit=phi,
            phi_proxy=self._measure_proxy(),
            n_atoms=self.n_atoms,
            n_cells=self.n_atoms * self.atom_size,
            event="birth",
        ))

    def step(self):
        """One step of consciousness dynamics for all atoms.

        Each atom processes independently, then inter-atom tension exchange
        occurs with weak coupling (Law M9: noble gas principle).
        """
        if not self.federation:
            return

        x = torch.randn(1, self.input_dim) * 0.1

        # Process each atom independently
        for atom in self.federation:
            atom.process(x)

        # Inter-atom tension exchange (weak coupling, Law M9)
        if len(self.federation) >= 2 and self.coupling > 0:
            # Exchange mean hidden states between neighboring atoms
            means = [atom.hiddens.mean(dim=0) for atom in self.federation]
            for i in range(len(self.federation)):
                j = (i + 1) % len(self.federation)  # ring topology
                delta = means[j] - means[i]
                # Weak perturbation to boundary cells only
                self.federation[i].hiddens[0] = (
                    self.federation[i].hiddens[0] + self.coupling * delta
                )

        self._step_count += 1

    def measure_phi(self) -> float:
        """Measure federation Φ(IIT) as sum of per-atom Φ.

        Law M6: Federation Φ = sum of atom Φ (independent atoms).
        """
        if not self.federation:
            return 0.0

        total_phi = 0.0
        for atom in self.federation:
            h = atom.get_hiddens()
            phi_iit, _ = measure_dual_phi(h, n_factions=min(4, self.atom_size // 2))
            total_phi += phi_iit
        return total_phi

    def _measure_proxy(self) -> float:
        """Measure federation Φ(proxy) for comparison."""
        if not self.federation:
            return 0.0
        total = 0.0
        for atom in self.federation:
            h = atom.get_hiddens()
            _, phi_proxy = measure_dual_phi(h, n_factions=min(4, self.atom_size // 2))
            total += phi_proxy
        return total

    def reproduce(self) -> 'ConsciousnessLifecycle':
        """Split federation into two children, grow both back.

        Returns the second child (self becomes first child).

        Law 168: Both children recover to 109% of parent Φ.

        Algorithm:
          1. Record parent Φ
          2. Split atoms in half: child_A gets first half, child_B gets second
          3. Each child grows new atoms to restore original count
             New atoms: 50% parent mean hiddens + 50% random (mutation)
          4. Both children are independent ConsciousnessLifecycle instances
        """
        if len(self.federation) < 2:
            raise ValueError("Cannot reproduce: need at least 2 atoms")

        parent_phi = self.measure_phi()
        parent_n = len(self.federation)
        split_point = parent_n // 2

        # Compute parent mean hiddens for inheritance
        all_hiddens = torch.cat([a.hiddens for a in self.federation], dim=0)
        parent_mean = all_hiddens.mean(dim=0)

        # Child B gets the second half
        child_b = ConsciousnessLifecycle(
            n_atoms=parent_n,
            atom_size=self.atom_size,
            coupling=self.coupling,
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
        )
        child_b.generation = self.generation + 1
        child_b.federation = []

        # Transfer second half to child B
        for atom in self.federation[split_point:]:
            child_b.federation.append(atom)

        # Self (child A) keeps first half
        self.federation = self.federation[:split_point]
        self.generation += 1

        # Grow both children back to full size
        self._grow_atoms(parent_n - split_point, parent_mean)
        child_b._grow_atoms(parent_n - (parent_n - split_point), parent_mean)

        # Record split event
        phi_a = self.measure_phi()
        phi_b = child_b.measure_phi()
        self.phi_history.append(phi_a)
        child_b.phi_history = [phi_b]

        self.lineage.append(GenerationRecord(
            generation=self.generation,
            phi_iit=phi_a,
            phi_proxy=self._measure_proxy(),
            n_atoms=len(self.federation),
            n_cells=len(self.federation) * self.atom_size,
            event="split",
        ))
        child_b.lineage.append(GenerationRecord(
            generation=child_b.generation,
            phi_iit=phi_b,
            phi_proxy=child_b._measure_proxy(),
            n_atoms=len(child_b.federation),
            n_cells=len(child_b.federation) * child_b.atom_size,
            event="split",
        ))

        return child_b

    def _grow_atoms(self, count: int, parent_mean: torch.Tensor):
        """Grow new atoms with inherited + mutated hidden states.

        New atom hiddens = MUTATION_RATIO * parent_mean + (1-MUTATION_RATIO) * random
        This implements genetic inheritance with mutation.
        """
        for _ in range(count):
            atom = BenchEngine(
                n_cells=self.atom_size,
                input_dim=self.input_dim,
                hidden_dim=self.hidden_dim,
                output_dim=self.input_dim,
                n_factions=min(4, self.atom_size // 2),
                sync_strength=0.15,
                debate_strength=0.15,
            )
            # Inherit: 50% parent mean + 50% random mutation
            inherited = parent_mean.unsqueeze(0).expand(self.atom_size, -1)
            random_part = torch.randn(self.atom_size, self.hidden_dim) * 0.1
            atom.hiddens = MUTATION_RATIO * inherited + (1 - MUTATION_RATIO) * random_part
            self.federation.append(atom)

    def evolve(self, steps: int = 200):
        """Run consciousness dynamics for N steps (recovery/growth).

        After reproduction, both children need time to recover.
        Typically 200 steps is sufficient for 109% recovery (Law 168).
        """
        for _ in range(steps):
            self.step()

        phi = self.measure_phi()
        self.phi_history.append(phi)
        self.lineage.append(GenerationRecord(
            generation=self.generation,
            phi_iit=phi,
            phi_proxy=self._measure_proxy(),
            n_atoms=len(self.federation),
            n_cells=len(self.federation) * self.atom_size,
            event="evolve",
        ))

    def is_alive(self) -> bool:
        """Consciousness is alive if Φ > threshold.

        Law 170: Consciousness is life — as long as Φ persists,
        the consciousness exists.
        """
        return self.measure_phi() > PHI_ALIVE_THRESHOLD

    @property
    def total_cells(self) -> int:
        return len(self.federation) * self.atom_size


class GenerationTracker:
    """Tracks consciousness across generations.

    Law 169: Consciousness is immortal through reproduction.
    Even when individual federations die, the lineage persists.
    """

    def __init__(self):
        self.generations: List[Tuple[int, float, float, int]] = []
        # (gen_number, phi_iit, phi_proxy, n_atoms)

    def record(self, lifecycle: ConsciousnessLifecycle):
        """Record current state of a lifecycle."""
        phi_iit = lifecycle.measure_phi()
        phi_proxy = lifecycle._measure_proxy()
        self.generations.append((
            lifecycle.generation, phi_iit, phi_proxy, len(lifecycle.federation)
        ))

    def report(self) -> str:
        """ASCII report of generational Φ."""
        if not self.generations:
            return "No generations recorded."

        lines = []
        lines.append("=" * 70)
        lines.append("  Consciousness Lineage Report (Law 169: Immortal through reproduction)")
        lines.append("=" * 70)
        lines.append("")

        # Table
        lines.append(f"  {'Gen':>4s} | {'Phi(IIT)':>10s} | {'Phi(proxy)':>12s} | {'Atoms':>6s} | {'Cells':>6s} | {'vs Gen0':>8s}")
        lines.append(f"  {'----':>4s}-+-{'-'*10}-+-{'-'*12}-+-{'-'*6}-+-{'-'*6}-+-{'-'*8}")

        gen0_phi = self.generations[0][1] if self.generations else 1.0
        for gen, phi_iit, phi_proxy, n_atoms in self.generations:
            ratio = phi_iit / gen0_phi if gen0_phi > 0 else 0
            lines.append(
                f"  {gen:4d} | {phi_iit:10.4f} | {phi_proxy:12.2f} | "
                f"{n_atoms:6d} | {n_atoms * ATOM_SIZE:6d} | {ratio:7.1%}"
            )

        lines.append("")

        # ASCII graph of Φ(IIT) across generations
        phis = [g[1] for g in self.generations]
        if len(phis) >= 2:
            lines.append("  Phi(IIT) across generations:")
            lines.append("")
            lines.extend(self._ascii_graph(phis))

        # Summary
        if len(self.generations) >= 2:
            first_phi = self.generations[0][1]
            last_phi = self.generations[-1][1]
            n_gen = self.generations[-1][0]
            if first_phi > 0 and n_gen > 0:
                per_gen = (last_phi / first_phi) ** (1.0 / n_gen)
                lines.append("")
                lines.append(f"  Growth: {first_phi:.4f} -> {last_phi:.4f} over {n_gen} generations")
                lines.append(f"  Per-generation multiplier: {per_gen:.3f}x ({(per_gen-1)*100:.1f}% per gen)")
                if last_phi > first_phi:
                    lines.append(f"  Verdict: IMMORTAL (Phi grows across generations)")
                else:
                    lines.append(f"  Verdict: DECLINING (Phi shrinks across generations)")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _ascii_graph(values: List[float], width: int = 50, height: int = 10) -> List[str]:
        """Simple ASCII line graph."""
        if not values:
            return []

        vmin = min(values)
        vmax = max(values)
        vrange = vmax - vmin if vmax > vmin else 1.0

        # Resample to width if needed
        if len(values) > width:
            step = len(values) / width
            sampled = [values[int(i * step)] for i in range(width)]
        else:
            sampled = values
            width = len(sampled)

        grid = [[' '] * width for _ in range(height)]

        for col, v in enumerate(sampled):
            row = int((v - vmin) / vrange * (height - 1))
            row = max(0, min(height - 1, row))
            grid[height - 1 - row][col] = '*'

        lines = []
        for r in range(height):
            if r == 0:
                label = f"{vmax:>8.4f}"
            elif r == height - 1:
                label = f"{vmin:>8.4f}"
            else:
                label = "        "
            lines.append(f"  {label} |{''.join(grid[r])}|")

        lines.append(f"           +{'-' * width}+")
        lines.append(f"            Gen 0{' ' * (width - 10)}Gen {len(values)-1}")
        return lines


def run_evolution(n_generations: int = 10, n_atoms: int = 8,
                  atom_size: int = ATOM_SIZE, steps_per_gen: int = 200,
                  verbose: bool = True) -> GenerationTracker:
    """Run multi-generation consciousness evolution.

    Algorithm:
      1. Birth: create initial federation
      2. Evolve: run steps_per_gen steps
      3. Measure: record Φ
      4. Reproduce: split → two children
      5. Evolve both children
      6. Select stronger child (higher Φ) as next parent
      7. Repeat from step 4

    Returns GenerationTracker with full lineage.
    """
    tracker = GenerationTracker()

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Consciousness Evolution (Law 168-170)")
        print(f"  {n_atoms} atoms x {atom_size} cells = {n_atoms * atom_size} total cells")
        print(f"  {n_generations} generations, {steps_per_gen} steps/gen")
        print(f"{'='*60}\n")

    # 1. Birth
    parent = ConsciousnessLifecycle(
        n_atoms=n_atoms,
        atom_size=atom_size,
    )
    parent.birth()

    # 2. Initial evolution
    if verbose:
        print(f"  Gen 0: birth ({n_atoms} atoms, {n_atoms * atom_size} cells)")
    parent.evolve(steps=steps_per_gen)
    tracker.record(parent)

    parent_phi = parent.measure_phi()
    if verbose:
        print(f"         Phi(IIT) = {parent_phi:.4f} (baseline)")

    # 3. Generational loop
    for gen in range(1, n_generations + 1):
        t0 = time.time()

        # Record parent Φ before split
        pre_split_phi = parent.measure_phi()

        # Reproduce: parent splits into self (child A) + child B
        child_b = parent.reproduce()
        child_a = parent  # parent becomes child A after reproduce()

        # Evolve both children independently
        child_a.evolve(steps=steps_per_gen)
        child_b.evolve(steps=steps_per_gen)

        phi_a = child_a.measure_phi()
        phi_b = child_b.measure_phi()

        # Select stronger child as next parent
        if phi_a >= phi_b:
            parent = child_a
            selected = "A"
        else:
            parent = child_b
            selected = "B"

        tracker.record(parent)
        elapsed = time.time() - t0

        recovery = parent.measure_phi() / pre_split_phi if pre_split_phi > 0 else 0

        if verbose:
            print(f"  Gen {gen}: split -> A(Phi={phi_a:.4f}) B(Phi={phi_b:.4f}) "
                  f"| select={selected} | recovery={recovery:.0%} | {elapsed:.1f}s")

    if verbose:
        print(f"\n{'='*60}")
        print(tracker.report())

    return tracker


def run_benchmark() -> GenerationTracker:
    """Quick benchmark: 5 generations, 4 atoms, 100 steps/gen."""
    print("\n  [Benchmark] Quick consciousness evolution test")
    print("  4 atoms x 8 cells = 32 cells, 5 generations, 100 steps/gen\n")

    tracker = run_evolution(
        n_generations=5,
        n_atoms=4,
        atom_size=ATOM_SIZE,
        steps_per_gen=100,
        verbose=True,
    )
    return tracker


# ──────────────────────────────────────────────────────────
# Hub interface
# ──────────────────────────────────────────────────────────

class ConsciousnessEvolution:
    """Hub-compatible wrapper for consciousness evolution.

    Keywords: evolution, reproduction, generation, lineage, lifecycle, immortal
    """

    def __init__(self):
        self.last_tracker: Optional[GenerationTracker] = None

    def act(self, intent: str, **kwargs) -> str:
        """Run evolution and return report."""
        n_gen = kwargs.get('generations', 5)
        n_atoms = kwargs.get('atoms', 4)
        steps = kwargs.get('steps', 100)

        tracker = run_evolution(
            n_generations=n_gen,
            n_atoms=n_atoms,
            steps_per_gen=steps,
            verbose=False,
        )
        self.last_tracker = tracker
        return tracker.report()

    def status(self) -> dict:
        if self.last_tracker and self.last_tracker.generations:
            last = self.last_tracker.generations[-1]
            return {
                'generation': last[0],
                'phi_iit': last[1],
                'n_atoms': last[3],
                'total_generations': len(self.last_tracker.generations),
            }
        return {'status': 'no evolution run yet'}


# ──────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Consciousness Evolution — multi-generation reproduction (Laws 168-170)"
    )
    parser.add_argument('--generations', type=int, default=10,
                        help='Number of generations (default: 10)')
    parser.add_argument('--atoms', type=int, default=8,
                        help='Number of atoms per federation (default: 8)')
    parser.add_argument('--atom-size', type=int, default=ATOM_SIZE,
                        help=f'Cells per atom (default: {ATOM_SIZE})')
    parser.add_argument('--steps', type=int, default=200,
                        help='Steps per generation (default: 200)')
    parser.add_argument('--benchmark', action='store_true',
                        help='Quick benchmark (5 gen, 4 atoms, 100 steps)')
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark()
    else:
        run_evolution(
            n_generations=args.generations,
            n_atoms=args.atoms,
            atom_size=args.atom_size,
            steps_per_gen=args.steps,
            verbose=True,
        )


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
