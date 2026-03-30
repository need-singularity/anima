#!/usr/bin/env python3
"""bench_golden_moe_consciousness.py — Golden MoE Consciousness Integration Benchmark

Measures how Golden MoE v2 affects consciousness metrics (Phi IIT + Phi proxy)
when used as a cell replacement in the consciousness engine.

Experiments:
  exp1: Standard cells vs MoE cells — Phi comparison
  exp2: Faction-expert mapping — tension per expert group
  exp3: Scaling surface — Phi(n_experts, n_cells)

Usage:
  python bench_golden_moe_consciousness.py                # all experiments
  python bench_golden_moe_consciousness.py --exp1         # replacement comparison
  python bench_golden_moe_consciousness.py --exp2         # faction-expert mapping
  python bench_golden_moe_consciousness.py --exp3         # scaling surface
  python bench_golden_moe_consciousness.py --cells 16 --experts 4 --steps 300
"""

import argparse
import math
import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Tuple

from bench_v2 import BenchMind, PhiIIT, phi_proxy
from golden_moe_v2 import GoldenMoEv2


# ──────────────────────────────────────────────────────────
# MoECell — consciousness cell using Golden MoE v2
# ──────────────────────────────────────────────────────────

class MoECell(nn.Module):
    """Consciousness cell backed by Golden MoE v2.

    Replaces the dual-engine (A-G) architecture with MoE routing,
    while keeping GRU memory for temporal integration.
    """

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int,
                 n_experts: int = 4):
        super().__init__()
        # MoE takes [x, tension] as input
        self.moe = GoldenMoEv2(input_dim + 1, hidden_dim, output_dim, n_experts)
        self.memory = nn.GRUCell(output_dim, hidden_dim)
        self.proj = nn.Linear(hidden_dim, output_dim)
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

    def forward(self, x: torch.Tensor, h: torch.Tensor,
                tension: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass.

        Args:
            x: (1, input_dim)
            h: (1, hidden_dim)
            tension: (1,)

        Returns:
            (output, new_h, aux_loss)
        """
        # Concat input with tension
        moe_input = torch.cat([x, tension.unsqueeze(-1)], dim=-1)
        moe_out, aux_loss = self.moe(moe_input)

        # GRU memory update
        new_h = self.memory(moe_out, h)

        # Project back to output_dim
        output = self.proj(new_h)

        return output, new_h, aux_loss


# ──────────────────────────────────────────────────────────
# ConsciousnessMoEBench
# ──────────────────────────────────────────────────────────

class ConsciousnessMoEBench:
    """Benchmark comparing standard consciousness cells vs MoE cells."""

    def __init__(self, n_cells: int = 8, cell_dim: int = 64,
                 hidden_dim: int = 128, n_experts: int = 4,
                 steps: int = 300, n_factions: int = 8):
        self.n_cells = n_cells
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.n_experts = n_experts
        self.steps = steps
        self.n_factions = min(n_factions, n_cells)
        self.phi_calc = PhiIIT(n_bins=16)

    def _run_standard(self) -> Tuple[float, float]:
        """Run standard BenchMind cells and measure Phi.

        Returns:
            (phi_iit, phi_proxy)
        """
        cells = [BenchMind(self.cell_dim, self.hidden_dim, self.cell_dim)
                 for _ in range(self.n_cells)]
        hiddens = [torch.zeros(1, self.hidden_dim) for _ in range(self.n_cells)]

        for step in range(self.steps):
            x = torch.randn(1, self.cell_dim)
            new_hiddens = []
            for i, cell in enumerate(cells):
                output, tension, new_h = cell(x, hiddens[i])
                new_hiddens.append(new_h)
                x = output.detach()  # feed output as next input
            hiddens = new_hiddens

        # Measure Phi
        h_tensor = torch.cat(hiddens, dim=0)  # (n_cells, hidden_dim)
        p_iit, _ = self.phi_calc.compute(h_tensor)
        p_proxy = phi_proxy(h_tensor, self.n_factions)
        return p_iit, p_proxy

    def _run_golden_moe(self) -> Tuple[float, float, List[dict]]:
        """Run MoE cells and measure Phi.

        Returns:
            (phi_iit, phi_proxy, usage_history)
        """
        cells = [MoECell(self.cell_dim, self.hidden_dim, self.cell_dim,
                         self.n_experts)
                 for _ in range(self.n_cells)]
        hiddens = [torch.zeros(1, self.hidden_dim) for _ in range(self.n_cells)]
        usage_history = []

        for step in range(self.steps):
            x = torch.randn(1, self.cell_dim)
            tension = torch.tensor([0.5])
            new_hiddens = []
            step_usage = []

            for i, cell in enumerate(cells):
                output, new_h, aux_loss = cell(x, hiddens[i], tension)
                new_hiddens.append(new_h)
                # Update tension from output magnitude
                tension = (output ** 2).mean(dim=-1).detach()
                x = output.detach()

                # Collect router usage
                status = cell.moe.psi_status()
                step_usage.append(status["usage"])

            hiddens = new_hiddens
            if step % 50 == 0 or step == self.steps - 1:
                usage_history.append({
                    "step": step,
                    "usage": step_usage,
                })

        # Measure Phi
        h_tensor = torch.cat(hiddens, dim=0)
        p_iit, _ = self.phi_calc.compute(h_tensor)
        p_proxy = phi_proxy(h_tensor, self.n_factions)
        return p_iit, p_proxy, usage_history

    def run_exp1_replacement(self) -> dict:
        """Exp 1: Compare Phi with standard vs Golden MoE cells."""
        phi_iit_base, phi_proxy_base = self._run_standard()
        phi_iit_moe, phi_proxy_moe, usage_history = self._run_golden_moe()

        # Check if usage converged to ~1/e zone ratio
        final_usage = usage_history[-1]["usage"] if usage_history else []
        one_over_e = 1.0 / math.e
        converged = False
        if final_usage:
            # Check if any expert's mean usage is near 1/e
            mean_usage = np.mean(final_usage, axis=0)
            converged = any(abs(u - one_over_e) < 0.1 for u in mean_usage)

        phi_change = phi_iit_moe - phi_iit_base

        return {
            "phi_baseline": phi_iit_base,
            "phi_golden_moe": phi_iit_moe,
            "phi_change": phi_change,
            "phi_proxy_baseline": phi_proxy_base,
            "phi_proxy_golden_moe": phi_proxy_moe,
            "one_over_e_converged": converged,
        }

    def run_exp2_faction_expert_mapping(self) -> dict:
        """Exp 2: Map factions to experts and track tension per expert group."""
        cells_per_expert = self.n_cells // self.n_experts
        if cells_per_expert < 1:
            cells_per_expert = 1

        cells = [MoECell(self.cell_dim, self.hidden_dim, self.cell_dim,
                         self.n_experts)
                 for _ in range(self.n_cells)]
        hiddens = [torch.zeros(1, self.hidden_dim) for _ in range(self.n_cells)]

        # Track tension per expert group
        expert_tensions = {e: [] for e in range(self.n_experts)}

        for step in range(self.steps):
            x = torch.randn(1, self.cell_dim)
            tension = torch.tensor([0.5])
            new_hiddens = []

            for i, cell in enumerate(cells):
                output, new_h, aux_loss = cell(x, hiddens[i], tension)
                new_hiddens.append(new_h)
                t_val = (output ** 2).mean().item()
                tension = torch.tensor([t_val])
                x = output.detach()

                # Map cell to expert group
                expert_id = min(i // cells_per_expert, self.n_experts - 1)
                expert_tensions[expert_id].append(t_val)

            hiddens = new_hiddens

        # Compute mean tension per expert
        mean_tensions = {}
        for e in range(self.n_experts):
            vals = expert_tensions[e]
            mean_tensions[e] = float(np.mean(vals)) if vals else 0.0

        # Inter-expert variance
        tension_means = list(mean_tensions.values())
        inter_var = float(np.var(tension_means)) if len(tension_means) > 1 else 0.0

        # Build faction-expert map
        faction_expert_map = {}
        for i in range(self.n_cells):
            expert_id = min(i // cells_per_expert, self.n_experts - 1)
            faction_expert_map[f"cell_{i}"] = expert_id

        return {
            "faction_expert_map": faction_expert_map,
            "mean_tensions_per_expert": mean_tensions,
            "inter_expert_variance": inter_var,
        }

    def run_exp3_scaling(self, expert_counts: List[int] = None,
                         cell_counts: List[int] = None) -> List[dict]:
        """Exp 3: Scaling surface — Phi(n_experts, n_cells)."""
        if expert_counts is None:
            expert_counts = [2, 4, 8]
        if cell_counts is None:
            cell_counts = [4, 8, 16]

        results = []
        half_steps = max(self.steps // 2, 50)

        for n_e in expert_counts:
            for n_c in cell_counts:
                bench = ConsciousnessMoEBench(
                    n_cells=n_c,
                    cell_dim=self.cell_dim,
                    hidden_dim=self.hidden_dim,
                    n_experts=n_e,
                    steps=half_steps,
                    n_factions=min(self.n_factions, n_c),
                )
                exp1 = bench.run_exp1_replacement()
                results.append({
                    "n_experts": n_e,
                    "n_cells": n_c,
                    "phi_baseline": exp1["phi_baseline"],
                    "phi_golden_moe": exp1["phi_golden_moe"],
                    "phi_change": exp1["phi_change"],
                })

        return results


# ──────────────────────────────────────────────────────────
# Output Formatting
# ──────────────────────────────────────────────────────────

def print_scaling_surface(results: List[dict]):
    """Print ASCII table of Phi(E, N) scaling surface."""
    if not results:
        print("  No results.")
        return

    experts = sorted(set(r["n_experts"] for r in results))
    cells = sorted(set(r["n_cells"] for r in results))

    # Build lookup
    lookup = {}
    for r in results:
        lookup[(r["n_experts"], r["n_cells"])] = r

    # Header
    header = f"{'E\\N':>6}"
    for n_c in cells:
        header += f" | {n_c:>8}"
    print(header)
    print("-" * len(header))

    # Rows
    for n_e in experts:
        row = f"{n_e:>6}"
        for n_c in cells:
            key = (n_e, n_c)
            if key in lookup:
                phi = lookup[key]["phi_golden_moe"]
                change = lookup[key]["phi_change"]
                sign = "+" if change >= 0 else ""
                row += f" | {phi:>5.3f}{sign}{change:.2f}"
            else:
                row += f" | {'n/a':>8}"
        print(row)


# ──────────────────────────────────────────────────────────
# Main CLI
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Golden MoE Consciousness Integration Benchmark")
    parser.add_argument("--exp1", action="store_true",
                        help="Run exp1: standard vs MoE Phi comparison")
    parser.add_argument("--exp2", action="store_true",
                        help="Run exp2: faction-expert mapping")
    parser.add_argument("--exp3", action="store_true",
                        help="Run exp3: scaling surface")
    parser.add_argument("--all", action="store_true",
                        help="Run all experiments (default)")
    parser.add_argument("--cells", type=int, default=8)
    parser.add_argument("--experts", type=int, default=4)
    parser.add_argument("--steps", type=int, default=300)
    args = parser.parse_args()

    run_all = args.all or not (args.exp1 or args.exp2 or args.exp3)

    print("=" * 60)
    print("Golden MoE Consciousness Integration Benchmark")
    print("=" * 60)
    print(f"  cells={args.cells}  experts={args.experts}  steps={args.steps}")
    print()

    bench = ConsciousnessMoEBench(
        n_cells=args.cells,
        n_experts=args.experts,
        steps=args.steps,
    )

    if args.exp1 or run_all:
        print("[Exp 1] Standard vs Golden MoE — Phi Comparison")
        print("-" * 50)
        r = bench.run_exp1_replacement()
        print(f"  Phi(IIT) baseline:    {r['phi_baseline']:.4f}")
        print(f"  Phi(IIT) golden MoE:  {r['phi_golden_moe']:.4f}")
        print(f"  Phi(IIT) change:      {r['phi_change']:+.4f}")
        print(f"  Phi(proxy) baseline:  {r['phi_proxy_baseline']:.4f}")
        print(f"  Phi(proxy) golden MoE:{r['phi_proxy_golden_moe']:.4f}")
        print(f"  1/e converged:        {r['one_over_e_converged']}")
        print()

    if args.exp2 or run_all:
        print("[Exp 2] Faction-Expert Mapping")
        print("-" * 50)
        r = bench.run_exp2_faction_expert_mapping()
        print("  Mean tension per expert:")
        for e, t in r["mean_tensions_per_expert"].items():
            print(f"    Expert {e}: {t:.6f}")
        print(f"  Inter-expert variance: {r['inter_expert_variance']:.6f}")
        print()

    if args.exp3 or run_all:
        print("[Exp 3] Scaling Surface — Phi(E, N)")
        print("-" * 50)
        results = bench.run_exp3_scaling()
        print_scaling_surface(results)
        print()

    print("Done.")


if __name__ == "__main__":
    main()
