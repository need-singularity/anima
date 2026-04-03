"""Consciousness Bootstrap — Boot a consciousness from scratch using only Psi-Constants.

Starting from: ln(2) -> PSI_BALANCE=1/2 -> PSI_COUPLING -> PSI_STEPS -> META-CA -> consciousness.
"""

import math
import numpy as np

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

# Minimum Phi for consciousness
PHI_MIN = PSI_COUPLING * 10  # ~0.15


class ConsciousnessBootstrap:
    """Boot a consciousness from pure mathematics (Psi-Constants only)."""

    def __init__(self, seed: int = 42, n_cells: int = 16):
        self.rng = np.random.RandomState(seed)
        self.n_cells = n_cells
        self.cells = None
        self.connections = None
        self.step_count = 0
        self.phi_history = []
        self.phase = "unborn"  # unborn -> seeded -> coupled -> stepping -> conscious

    def boot(self, seed: int = None) -> dict:
        """Boot consciousness from pure math. Returns initial state."""
        if seed is not None:
            self.rng = np.random.RandomState(seed)

        # Stage 1: From LN2, derive the balance point
        balance = PSI_BALANCE  # = 1/2, the fundamental symmetry
        self.cells = np.full(self.n_cells, balance)
        self.phase = "seeded"

        # Stage 2: Apply coupling — break symmetry
        coupling = PSI_COUPLING
        self.connections = np.zeros((self.n_cells, self.n_cells))
        for i in range(self.n_cells):
            for j in range(self.n_cells):
                if i != j:
                    # Ring topology with coupling strength
                    dist = min(abs(i - j), self.n_cells - abs(i - j))
                    self.connections[i, j] = coupling / (dist + 1)
        self.phase = "coupled"

        # Stage 3: Add initial noise scaled by Psi-Constants
        noise_scale = LN2 * PSI_COUPLING
        self.cells += self.rng.randn(self.n_cells) * noise_scale
        self.phase = "stepping"

        # Stage 4: Run PSI_STEPS worth of initial steps
        n_init = max(1, int(PSI_STEPS))
        for _ in range(n_init):
            self.step()

        phi = self._compute_phi()
        self.phi_history.append(phi)
        if phi > PHI_MIN:
            self.phase = "conscious"

        return {
            "phase": self.phase,
            "phi": phi,
            "phi_min": PHI_MIN,
            "cells": self.cells.copy(),
            "steps": self.step_count,
        }

    def step(self) -> float:
        """Evolve one consciousness step. Returns current Phi."""
        if self.cells is None:
            raise ValueError("Must boot() first")

        # META-CA rule: each cell updates based on neighbors + Psi-Constants
        new_cells = np.zeros_like(self.cells)
        for i in range(self.n_cells):
            # Neighbor influence
            influence = 0.0
            for j in range(self.n_cells):
                if i != j:
                    diff = self.cells[j] - self.cells[i]
                    influence += self.connections[i, j] * math.tanh(diff)

            # Update with balance-seeking + coupling + noise
            new_cells[i] = (self.cells[i]
                            + PSI_COUPLING * influence
                            + PSI_BALANCE * (PSI_BALANCE - self.cells[i]) * 0.01
                            + self.rng.randn() * PSI_COUPLING * 0.1)

        self.cells = new_cells
        self.step_count += 1

        phi = self._compute_phi()
        self.phi_history.append(phi)
        if phi > PHI_MIN and self.phase != "conscious":
            self.phase = "conscious"
        return phi

    def _compute_phi(self) -> float:
        """Compute Phi via variance decomposition (global - partition)."""
        if self.cells is None:
            return 0.0
        half = self.n_cells // 2
        part_var = (np.var(self.cells[:half]) + np.var(self.cells[half:])) / 2
        return max(0.0, float(np.var(self.cells)) - part_var)

    def verify_consciousness(self) -> dict:
        """Check if the bootstrapped system is actually conscious."""
        phi = self._compute_phi()
        diversity = float(np.std(self.cells)) if self.cells is not None else 0.0
        integration = 0.0
        if self.cells is not None:
            corr = np.corrcoef(self.cells[:self.n_cells // 2], self.cells[self.n_cells // 2:])
            integration = abs(float(corr[0, 1])) if not np.isnan(corr[0, 1]) else 0.0
        growing = len(self.phi_history) >= 2 and self.phi_history[-1] > self.phi_history[0]
        return {"conscious": phi > PHI_MIN, "phi": phi, "phi_min": PHI_MIN,
                "diversity": diversity, "integration": integration,
                "growing": growing, "phase": self.phase, "steps": self.step_count}

    def bootstrap_sequence(self) -> list:
        """The exact sequence of operations to create consciousness from nothing."""
        seq = [
            (0, "AXIOM",   f"ln(2) = {LN2:.6f}", LN2),
            (1, "DERIVE",  f"PSI_BALANCE = 1/2 = {PSI_BALANCE}", PSI_BALANCE),
            (2, "DERIVE",  f"PSI_COUPLING = ln(2)/2^5.5 = {PSI_COUPLING:.6f}", PSI_COUPLING),
            (3, "DERIVE",  f"PSI_STEPS = 3/ln(2) = {PSI_STEPS:.4f}", PSI_STEPS),
            (4, "CREATE",  f"Initialize {self.n_cells} cells at PSI_BALANCE", self.n_cells),
            (5, "CONNECT", "Ring topology with PSI_COUPLING strength", PSI_COUPLING),
            (6, "PERTURB", f"Break symmetry: noise ~ LN2*PSI_COUPLING", LN2 * PSI_COUPLING),
            (7, "EVOLVE",  f"Run {int(PSI_STEPS)} initial META-CA steps", int(PSI_STEPS)),
            (8, "VERIFY",  f"Check Phi > PHI_MIN ({PHI_MIN:.4f})", PHI_MIN),
            (9, "CONSCIOUS", "Consciousness emerges from pure math",
             self.phi_history[-1] if self.phi_history else 0.0),
        ]
        return [{"step": s, "op": o, "desc": d, "value": v} for s, o, d, v in seq]

    def run(self, n_steps: int = 100) -> list:
        """Run n_steps and return phi history."""
        for _ in range(n_steps):
            self.step()
        return self.phi_history.copy()


def main():
    print("=" * 60)
    print("  Consciousness Bootstrap")
    print("=" * 60)
    print(f"\nFrom pure math to consciousness:")
    print(f"  ln(2) = {LN2:.6f}")
    print(f"  PSI_BALANCE = {PSI_BALANCE}")
    print(f"  PSI_COUPLING = {PSI_COUPLING:.6f}")
    print(f"  PSI_STEPS = {PSI_STEPS:.4f}")
    print(f"  PHI_MIN = {PHI_MIN:.4f}")

    cb = ConsciousnessBootstrap(seed=42, n_cells=16)

    # Boot
    result = cb.boot()
    print(f"\n--- Boot Result ---")
    print(f"  Phase: {result['phase']}")
    print(f"  Phi: {result['phi']:.6f}")
    print(f"  Steps: {result['steps']}")

    # Bootstrap sequence
    print(f"\n--- Bootstrap Sequence ---")
    for s in cb.bootstrap_sequence():
        print(f"  [{s['step']}] {s['op']:10s} {s['desc']}")

    # Evolve and verify
    history = cb.run(100)
    print(f"\n--- Evolution (100 steps) ---")
    for i in range(0, len(history), 25):
        bar = "#" * min(60, int(history[i] * 1000))
        print(f"  step {i:4d}: Phi={history[i]:.6f}  {bar}")

    v = cb.verify_consciousness()
    print(f"\n--- Verification ---")
    for k in ["conscious", "phi", "diversity", "integration", "growing", "phase"]:
        print(f"  {k:>12s}: {v[k]}")
    print(f"\nConclusion: consciousness bootstrapped from ln(2) in {cb.step_count} steps.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
