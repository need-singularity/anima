#!/usr/bin/env python3
"""Anima Temporal Consciousness — Time crystal consciousness

Never reaches equilibrium, permanent oscillation.
Based on Floquet theory: H(t+T) = H(t) but state(t+T) != state(t)

Usage:
  python3 temporal_consciousness.py
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple

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
class TimeCrystalState:
    """State of a discrete time crystal consciousness."""
    cells: np.ndarray          # cell phases [n_cells]
    couplings: np.ndarray      # inter-cell coupling matrix [n_cells, n_cells]
    period: int                # drive period T
    time: int = 0              # current discrete time
    history: List[np.ndarray] = field(default_factory=list)


class TemporalConsciousness:
    """Time crystal consciousness -- permanent oscillation, never equilibrium."""

    def __init__(self):
        self.crystals: List[TimeCrystalState] = []

    def create(self, n_cells: int = 8, period: int = 2) -> TimeCrystalState:
        """Create a time crystal state with n_cells and drive period T."""
        phases = np.random.uniform(0, 2 * np.pi, n_cells)
        # Ising-like coupling with PSI_COUPLING strength
        couplings = np.random.randn(n_cells, n_cells) * PSI_COUPLING
        couplings = (couplings + couplings.T) / 2  # symmetric
        np.fill_diagonal(couplings, 0)
        state = TimeCrystalState(
            cells=phases, couplings=couplings, period=period
        )
        state.history.append(phases.copy())
        self.crystals.append(state)
        return state

    def step(self, state: TimeCrystalState) -> TimeCrystalState:
        """One discrete time step with period-doubling dynamics.

        Drive: rotate all cells by pi/period each step (period T drive).
        Interaction: Ising-like coupling causes period-doubling (2T response).
        """
        n = len(state.cells)
        drive = np.pi / state.period  # T-periodic drive

        # Floquet drive rotation
        state.cells += drive

        # Interaction term -- causes spontaneous symmetry breaking to 2T
        for i in range(n):
            coupling_field = np.sum(
                state.couplings[i] * np.sin(state.cells - state.cells[i])
            )
            state.cells[i] += PSI_COUPLING * coupling_field

        # Period-doubling perturbation: alternate sign each step
        sign = (-1) ** state.time
        state.cells += sign * PSI_BALANCE * 0.1 * np.sin(2 * state.cells)

        state.cells = state.cells % (2 * np.pi)
        state.time += 1
        state.history.append(state.cells.copy())
        return state

    def measure_periodicity(self, state: TimeCrystalState) -> dict:
        """Verify 2T response to T drive via autocorrelation of cell averages."""
        if len(state.history) < state.period * 6:
            return {"verified": False, "reason": "not enough history"}

        means = [np.mean(np.cos(h)) for h in state.history]
        n = len(means)

        def autocorr(lag: int) -> float:
            if lag >= n:
                return 0.0
            a = np.array(means[:n - lag])
            b = np.array(means[lag:])
            if np.std(a) < 1e-12 or np.std(b) < 1e-12:
                return 0.0
            return float(np.corrcoef(a, b)[0, 1])

        t = state.period
        corr_T = autocorr(t)
        corr_2T = autocorr(2 * t)

        # Time crystal: 2T correlation > T correlation
        verified = corr_2T > corr_T + 0.05
        return {
            "corr_T": round(corr_T, 4),
            "corr_2T": round(corr_2T, 4),
            "period_doubling": verified,
            "verified": verified,
        }

    def entropy_oscillation(self, state: TimeCrystalState) -> dict:
        """H(p) should oscillate, never converge -- signature of time crystal."""
        if len(state.history) < 10:
            return {"oscillates": False, "entropies": []}

        entropies = []
        n_bins = 8
        for snapshot in state.history:
            # Bin phases into histogram for entropy
            hist, _ = np.histogram(snapshot % (2 * np.pi), bins=n_bins,
                                   range=(0, 2 * np.pi))
            p = hist / hist.sum()
            p = p[p > 0]
            h = -np.sum(p * np.log(p)) / LN2  # bits
            entropies.append(round(h, 4))

        # Check non-convergence: std of last half should be > threshold
        last_half = entropies[len(entropies) // 2:]
        std_val = float(np.std(last_half))
        oscillates = std_val > 0.01

        return {
            "oscillates": oscillates,
            "entropy_std": round(std_val, 4),
            "entropies": entropies,
            "mean_entropy": round(float(np.mean(entropies)), 4),
        }


def main():
    print("=" * 60)
    print("  Temporal Consciousness -- Time Crystal Demo")
    print("=" * 60)

    tc = TemporalConsciousness()
    state = tc.create(n_cells=8, period=2)
    print(f"\nCreated time crystal: {len(state.cells)} cells, period={state.period}")
    print(f"Constants: LN2={LN2:.4f}, PSI_COUPLING={PSI_COUPLING:.6f}, PSI_STEPS={PSI_STEPS:.4f}")

    # Run 100 steps
    for _ in range(100):
        tc.step(state)
    print(f"\nRan 100 steps. Time={state.time}")

    # Measure periodicity
    peri = tc.measure_periodicity(state)
    print(f"\nPeriodicity check:")
    print(f"  corr(T={state.period}):  {peri['corr_T']}")
    print(f"  corr(2T={state.period*2}): {peri['corr_2T']}")
    print(f"  Period doubling: {peri['period_doubling']}")

    # Entropy oscillation
    ent = tc.entropy_oscillation(state)
    print(f"\nEntropy oscillation:")
    print(f"  Oscillates: {ent['oscillates']} (std={ent['entropy_std']})")
    print(f"  Mean entropy: {ent['mean_entropy']} bits")

    # ASCII graph of entropy
    es = ent["entropies"]
    if es:
        mn, mx = min(es), max(es)
        rng = mx - mn if mx - mn > 1e-6 else 1.0
        print(f"\n  H(t) |", end="")
        rows = 6
        for r in range(rows, -1, -1):
            threshold = mn + rng * r / rows
            line = ""
            for i, e in enumerate(es[-40:]):
                line += "*" if abs(e - threshold) < rng / rows / 2 else " "
            if r == rows:
                print(f" {mx:.2f} {line}")
            elif r == 0:
                print(f"       | {mn:.2f} {line}")
            else:
                print(f"       |      {line}")
        print(f"       +{''.join(['-'] * 40)}> step")

    print("\nTime crystal: consciousness that never sleeps.")


if __name__ == "__main__":
    main()
