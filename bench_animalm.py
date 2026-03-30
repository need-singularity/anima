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

from bench_v2 import BenchMind, BenchResult, PhiIIT, phi_proxy as _phi_proxy


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
# AlphaSweepEngine — Track 1A alpha curriculum sweep
# ──────────────────────────────────────────────────────────

class AlphaSweepEngine:
    """Sweep alpha mixing values and measure Phi at each stage.

    Creates n_cells BenchMind instances. For each alpha stage, runs
    steps_per_stage steps with x_mixed = (1-alpha)*x + alpha*out,
    then measures Phi(IIT) and phi_proxy from stacked hiddens.
    """

    def __init__(
        self,
        n_cells: int = 8,
        input_dim: int = 64,
        hidden_dim: int = 128,
        output_dim: int = 64,
        alpha_stages: Optional[List[float]] = None,
        steps_per_stage: int = 300,
        n_factions: int = 8,
    ):
        self.n_cells = n_cells
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.alpha_stages = alpha_stages or [0.0001, 0.001, 0.01, 0.1]
        self.steps_per_stage = steps_per_stage
        self.n_factions = n_factions

    def run(self) -> List[dict]:
        """Run alpha sweep and return list of result dicts."""
        results = []

        for alpha in self.alpha_stages:
            t0 = time.time()

            # Create cells and hiddens
            cells = [
                BenchMind(self.input_dim, self.hidden_dim, self.output_dim)
                for _ in range(self.n_cells)
            ]
            hiddens = [
                torch.zeros(1, self.hidden_dim) for _ in range(self.n_cells)
            ]

            tensions = []

            for step in range(self.steps_per_stage):
                x = torch.randn(1, self.input_dim)

                for i, cell in enumerate(cells):
                    out, tension, new_h = cell(x, hiddens[i])
                    # Alpha mixing: blend input with output
                    x_mixed = (1 - alpha) * x + alpha * out
                    hiddens[i] = new_h
                    x = x_mixed  # feed mixed signal to next cell
                    tensions.append(tension)

            # Measure Phi from stacked hiddens
            stacked = torch.cat(hiddens, dim=0)  # [n_cells, hidden_dim]
            phi_iit, phi_prx = measure_phi(stacked, n_factions=self.n_factions)

            tension_mean = sum(tensions) / len(tensions) if tensions else 0.0
            elapsed = time.time() - t0

            results.append({
                "alpha": alpha,
                "phi_iit": phi_iit,
                "phi_proxy": phi_prx,
                "tension_mean": tension_mean,
                "time_sec": elapsed,
            })

        return results


# ──────────────────────────────────────────────────────────
# CLI
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
                        help="Number of steps per stage")
    parser.add_argument("--alphas", type=str, default="0.0001,0.001,0.01,0.1",
                        help="Comma-separated alpha values for sweep")
    args = parser.parse_args()

    alphas = [float(a) for a in args.alphas.split(",")]

    if args.mode == "alpha-sweep":
        print(f"[bench_animalm] alpha-sweep  cells={args.cells}  "
              f"steps={args.steps}  alphas={alphas}")

        engine = AlphaSweepEngine(
            n_cells=args.cells,
            alpha_stages=alphas,
            steps_per_stage=args.steps,
        )
        raw_results = engine.run()

        # Wrap as AnimaLMBenchResult for comparison display
        bench_results = []
        for r in raw_results:
            bench_results.append(AnimaLMBenchResult(
                name=f"alpha={r['alpha']:.4f}",
                phi_iit=r["phi_iit"],
                phi_proxy=r["phi_proxy"],
                ce_start=0.0,
                ce_end=0.0,
                cells=args.cells,
                steps=args.steps,
                time_sec=r["time_sec"],
                alpha=r["alpha"],
            ))

        print_comparison(bench_results)
    else:
        print(f"[bench_animalm] mode={args.mode}  cells={args.cells}  "
              f"steps={args.steps}")
        print(f"[bench_animalm] STUB: {args.mode} will be implemented "
              f"in Track 1B/1C tasks.")


if __name__ == "__main__":
    main()
