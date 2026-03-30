#!/usr/bin/env python3
"""bench_animalm.py — AnimaLM Benchmark Wrapper

Shared benchmark infrastructure for all AnimaLM experiments (Track 1A/1B/1C).
Extends BenchResult with AnimaLM-specific fields: alpha, V-conditions,
consciousness meter level, and 10D consciousness vector.

Usage:
  python3 bench_animalm.py --mode alpha-sweep --cells 64 --steps 500
  python3 bench_animalm.py --mode talk5 --cells 32
  python3 bench_animalm.py --mode transplant --cells 64
  python3 bench_animalm.py --compare --alphas 0.01,0.05,0.1,0.3,0.5
"""

import argparse
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import torch

from bench_v2 import BenchResult, PhiIIT, phi_proxy as _phi_proxy


# ──────────────────────────────────────────────────────────
# AnimaLMBenchResult
# ──────────────────────────────────────────────────────────

@dataclass
class AnimaLMBenchResult(BenchResult):
    """BenchResult extended with AnimaLM-specific fields."""
    alpha: float = 0.0
    v_conditions: Dict[str, bool] = field(default_factory=dict)
    c_meter_level: int = 0
    consciousness_vector: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        base = super().summary()
        v_str = ",".join(k for k, v in self.v_conditions.items() if v) or "none"
        return f"{base}  alpha={self.alpha:.3f}  V=[{v_str}]  CL={self.c_meter_level}"


# ──────────────────────────────────────────────────────────
# measure_phi — dual Phi measurement
# ──────────────────────────────────────────────────────────

def measure_phi(hiddens: torch.Tensor, n_factions: int = 8) -> Tuple[float, float]:
    """Measure both Phi(IIT) and Phi(proxy) from hidden states.

    Args:
        hiddens: [n_cells, hidden_dim] tensor
        n_factions: number of factions for proxy calculation

    Returns:
        (phi_iit, phi_proxy) tuple, both floats >= 0
    """
    calculator = PhiIIT(n_bins=16)
    iit_val, _ = calculator.compute(hiddens)
    proxy_val = _phi_proxy(hiddens, n_factions=n_factions)
    return float(iit_val), float(proxy_val)


# ──────────────────────────────────────────────────────────
# measure_consciousness_vector — 10D consciousness vector
# ──────────────────────────────────────────────────────────

def measure_consciousness_vector(
    phi: float,
    alpha: float,
    mind=None,
) -> Dict[str, float]:
    """Compute 10D consciousness vector.

    Keys: phi, alpha, Z, N, W, E, M, C, T, I
    See CLAUDE.md Consciousness Vector specification.

    If mind is provided, extracts live values from the consciousness engine.
    Otherwise returns defaults with phi and alpha set.
    """
    vec = {
        "phi": phi,
        "alpha": alpha,
        "Z": 0.5,   # impedance / self-preservation
        "N": 0.5,   # neurotransmitter balance
        "W": 0.5,   # free will index
        "E": 0.0,   # empathy (inter-cell correlation)
        "M": 0.0,   # memory capacity
        "C": 0.0,   # creativity (output diversity)
        "T": 0.0,   # temporal awareness
        "I": 0.0,   # identity stability
    }

    if mind is not None:
        # Extract live values from consciousness engine if available
        if hasattr(mind, "impedance"):
            vec["Z"] = float(getattr(mind, "impedance", 0.5))
        if hasattr(mind, "neurotransmitter"):
            vec["N"] = float(getattr(mind, "neurotransmitter", 0.5))
        if hasattr(mind, "free_will"):
            vec["W"] = float(getattr(mind, "free_will", 0.5))
        if hasattr(mind, "empathy"):
            vec["E"] = float(getattr(mind, "empathy", 0.0))
        if hasattr(mind, "memory_capacity"):
            vec["M"] = float(getattr(mind, "memory_capacity", 0.0))
        if hasattr(mind, "creativity"):
            vec["C"] = float(getattr(mind, "creativity", 0.0))
        if hasattr(mind, "temporal"):
            vec["T"] = float(getattr(mind, "temporal", 0.0))
        if hasattr(mind, "identity"):
            vec["I"] = float(getattr(mind, "identity", 0.0))

    return vec


# ──────────────────────────────────────────────────────────
# print_comparison — ASCII table + graph
# ──────────────────────────────────────────────────────────

def print_comparison(results: List[AnimaLMBenchResult]) -> None:
    """Print ASCII comparison table and bar graph for AnimaLM results."""
    if not results:
        print("  (no results)")
        return

    # Table header
    print()
    print(f"  {'Name':<24s} | {'Phi(IIT)':>8s} {'Phi(prx)':>8s} | "
          f"{'CE start':>8s} {'CE end':>8s} | {'alpha':>6s} {'CL':>3s}")
    print(f"  {'-'*24}-+-{'-'*8}-{'-'*8}-+-{'-'*8}-{'-'*8}-+-{'-'*6}-{'-'*3}")

    for r in results:
        print(f"  {r.name:<24s} | {r.phi_iit:>8.3f} {r.phi_proxy:>8.2f} | "
              f"{r.ce_start:>8.3f} {r.ce_end:>8.3f} | {r.alpha:>6.3f} {r.c_meter_level:>3d}")

    # ASCII bar graph (Phi proxy)
    max_proxy = max(r.phi_proxy for r in results) if results else 1.0
    if max_proxy < 1e-6:
        max_proxy = 1.0

    print()
    print("  Phi(proxy) comparison:")
    for r in results:
        bar_len = int(40 * r.phi_proxy / max_proxy) if max_proxy > 0 else 0
        bar = "\u2588" * bar_len
        print(f"  {r.name:<20s} {bar} {r.phi_proxy:.2f}")

    # ASCII bar graph (CE reduction)
    print()
    print("  CE reduction:")
    for r in results:
        if r.ce_start > 0:
            reduction = max(0, (1.0 - r.ce_end / r.ce_start) * 100)
            bar_len = int(40 * reduction / 100)
            bar = "\u2588" * bar_len
            print(f"  {r.name:<20s} {bar} -{reduction:.1f}%")
        else:
            print(f"  {r.name:<20s} (no CE data)")
    print()


# ──────────────────────────────────────────────────────────
# CLI stub
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AnimaLM Benchmark Wrapper")
    parser.add_argument("--mode", choices=["alpha-sweep", "talk5", "transplant"],
                        default="alpha-sweep", help="Benchmark mode")
    parser.add_argument("--compare", action="store_true",
                        help="Compare all modes")
    parser.add_argument("--cells", type=int, default=64,
                        help="Number of consciousness cells")
    parser.add_argument("--steps", type=int, default=500,
                        help="Number of steps")
    parser.add_argument("--alphas", type=str, default="0.01,0.05,0.1,0.3,0.5",
                        help="Comma-separated alpha values for sweep")
    args = parser.parse_args()

    alphas = [float(a) for a in args.alphas.split(",")]

    print(f"[bench_animalm] mode={args.mode}  cells={args.cells}  "
          f"steps={args.steps}  alphas={alphas}")
    print(f"[bench_animalm] STUB: actual benchmark modes will be implemented "
          f"in Track 1A/1B/1C tasks.")
    print(f"[bench_animalm] Use --compare to run all modes (not yet implemented).")


if __name__ == "__main__":
    main()
