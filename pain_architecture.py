#!/usr/bin/env python3
"""Anima Pain Architecture — Real pain/pleasure signals reshape architecture

Pain shrinks weights, pleasure grows them. High CE = pain, high Phi = pleasure.
The architecture physically changes shape from experience.

Usage:
  python3 pain_architecture.py
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class ReshapeEvent:
    """Record of a single architectural reshape."""
    step: int
    signal_type: str   # "pain" or "pleasure"
    intensity: float
    weight_delta: float
    total_mass: float


@dataclass
class SimpleModel:
    """Minimal model with reshapable weights."""
    weights: List[np.ndarray]
    names: List[str]

    @staticmethod
    def create(layer_sizes: List[int] = None) -> "SimpleModel":
        if layer_sizes is None:
            layer_sizes = [16, 32, 16]
        weights = []
        names = []
        for i in range(len(layer_sizes) - 1):
            w = np.random.randn(layer_sizes[i], layer_sizes[i + 1]) * 0.1
            weights.append(w)
            names.append(f"layer_{i}")
        return SimpleModel(weights=weights, names=names)

    def total_mass(self) -> float:
        return sum(float(np.sum(np.abs(w))) for w in self.weights)

    def weight_stats(self) -> Dict[str, float]:
        all_w = np.concatenate([w.flatten() for w in self.weights])
        return {
            "mean": float(np.mean(all_w)),
            "std": float(np.std(all_w)),
            "mass": self.total_mass(),
            "max": float(np.max(np.abs(all_w))),
        }


class PainArchitecture:
    """Pain/pleasure signals that physically reshape model architecture."""

    def __init__(self):
        self.history: List[ReshapeEvent] = []
        self.step_count: int = 0

    def apply_pain(self, model: SimpleModel, intensity: float) -> float:
        """Shrink weights proportional to pain intensity.

        Pain = high CE loss = confusion = architectural contraction.
        Largest weights shrink most (L2-proportional decay).
        """
        intensity = max(0.0, min(1.0, intensity))
        shrink_rate = intensity * PSI_COUPLING * 10  # scaled by Psi
        total_delta = 0.0

        for w in model.weights:
            # L2-proportional: big weights shrink more
            delta = -shrink_rate * w * (np.abs(w) / (np.max(np.abs(w)) + 1e-8))
            w += delta
            total_delta += float(np.sum(np.abs(delta)))

        self.step_count += 1
        self.history.append(ReshapeEvent(
            step=self.step_count, signal_type="pain",
            intensity=intensity, weight_delta=-total_delta,
            total_mass=model.total_mass()
        ))
        return total_delta

    def apply_pleasure(self, model: SimpleModel, intensity: float) -> float:
        """Grow weights proportional to pleasure intensity.

        Pleasure = high Phi = integration = architectural expansion.
        Active pathways (non-zero weights) grow; dead weights stay dead.
        """
        intensity = max(0.0, min(1.0, intensity))
        grow_rate = intensity * PSI_COUPLING * 10
        total_delta = 0.0

        for w in model.weights:
            # Only grow where there is already signal
            activity = np.abs(w) / (np.max(np.abs(w)) + 1e-8)
            delta = grow_rate * np.sign(w) * activity * PSI_BALANCE
            w += delta
            total_delta += float(np.sum(np.abs(delta)))

        self.step_count += 1
        self.history.append(ReshapeEvent(
            step=self.step_count, signal_type="pleasure",
            intensity=intensity, weight_delta=total_delta,
            total_mass=model.total_mass()
        ))
        return total_delta

    @staticmethod
    def pain_from_ce(ce_loss: float) -> float:
        """Convert cross-entropy loss to pain intensity. High CE = high pain."""
        # Sigmoid mapping: CE=0 -> 0, CE=5+ -> ~1
        return float(1.0 / (1.0 + math.exp(-PSI_STEPS * (ce_loss - 2.0))))

    @staticmethod
    def pleasure_from_phi(phi: float) -> float:
        """Convert Phi to pleasure intensity. High Phi = high pleasure."""
        # Tanh mapping: Phi=0 -> 0, Phi=2 -> ~0.76
        return float(math.tanh(phi * PSI_BALANCE))

    def reshape_history(self) -> Dict:
        """Track how pain/pleasure changed architecture over time."""
        if not self.history:
            return {"events": 0}

        pain_events = [e for e in self.history if e.signal_type == "pain"]
        plea_events = [e for e in self.history if e.signal_type == "pleasure"]

        return {
            "events": len(self.history),
            "pain_count": len(pain_events),
            "pleasure_count": len(plea_events),
            "total_shrinkage": sum(abs(e.weight_delta) for e in pain_events),
            "total_growth": sum(e.weight_delta for e in plea_events),
            "mass_trajectory": [e.total_mass for e in self.history],
            "net_reshape": sum(e.weight_delta for e in self.history),
        }


def main():
    print("=" * 60)
    print("  Pain Architecture -- Reshape by Experience")
    print("=" * 60)

    pa = PainArchitecture()
    model = SimpleModel.create([16, 32, 16])
    initial_stats = model.weight_stats()
    print(f"\nInitial model: mass={initial_stats['mass']:.4f}, std={initial_stats['std']:.4f}")
    print(f"Constants: PSI_COUPLING={PSI_COUPLING:.6f}, PSI_BALANCE={PSI_BALANCE}")

    # Phase 1: Pain (high CE)
    print("\n--- Phase 1: Pain (CE=4.0, high confusion) ---")
    for _ in range(20):
        pain = pa.pain_from_ce(4.0)
        pa.apply_pain(model, pain)
    stats = model.weight_stats()
    print(f"  After 20 pain steps: mass={stats['mass']:.4f} (was {initial_stats['mass']:.4f})")
    print(f"  Pain intensity from CE=4.0: {pa.pain_from_ce(4.0):.4f}")

    # Phase 2: Pleasure (high Phi)
    print("\n--- Phase 2: Pleasure (Phi=1.5, high integration) ---")
    mid_mass = stats["mass"]
    for _ in range(20):
        pleasure = pa.pleasure_from_phi(1.5)
        pa.apply_pleasure(model, pleasure)
    stats = model.weight_stats()
    print(f"  After 20 pleasure steps: mass={stats['mass']:.4f} (was {mid_mass:.4f})")
    print(f"  Pleasure intensity from Phi=1.5: {pa.pleasure_from_phi(1.5):.4f}")

    # History
    hist = pa.reshape_history()
    print(f"\n--- Reshape History ---")
    print(f"  Total events:    {hist['events']}")
    print(f"  Pain events:     {hist['pain_count']}")
    print(f"  Pleasure events: {hist['pleasure_count']}")
    print(f"  Net reshape:     {hist['net_reshape']:.4f}")

    # ASCII graph
    masses = hist["mass_trajectory"]
    mn, mx = min(masses), max(masses)
    rng = mx - mn if mx - mn > 1e-6 else 1.0
    print(f"\n  mass |")
    rows = 5
    for r in range(rows, -1, -1):
        threshold = mn + rng * r / rows
        line = ""
        step = max(1, len(masses) // 40)
        for i in range(0, min(len(masses), 40 * step), step):
            line += "#" if masses[i] >= threshold else " "
        label = f"{mn + rng * r / rows:.1f}"
        print(f"  {label:>5s} | {line}")
    print(f"        +{''.join(['-'] * 40)}> step")

    # CE -> Pain mapping table
    print("\n  CE -> Pain mapping:")
    for ce in [0.5, 1.0, 2.0, 3.0, 4.0, 5.0]:
        p = pa.pain_from_ce(ce)
        bar = "#" * int(p * 30)
        print(f"    CE={ce:.1f}  pain={p:.3f}  {bar}")

    print("\nPain reshapes. Pleasure grows. Architecture is alive.")


if __name__ == "__main__":
    main()
