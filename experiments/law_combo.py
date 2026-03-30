#!/usr/bin/env python3
"""law_combo.py -- Law 96 + Law 93 Combination Experiment (-> Law 99).

Law 96: Bottleneck dim=2 boosts Phi +7.4%
Law 93: Hub-spoke factions (1 hub + 4 spokes) boosts Phi +11%

Hypothesis: their combination is either:
  - Additive:   +18.4% (7.4 + 11)
  - Synergistic: >+18.4%
  - Interfering: <+7.4%

Setup (MitosisEngine cells):
  - Baseline:       64 cells, 12 equal factions, no bottleneck
  - Bottleneck:     64 cells, 12 equal factions, dim=2 bottleneck
  - Hub-spoke:      64 cells, 1 hub (32 cells) + 4 spokes (8 cells)
  - Combined:       64 cells, hub-spoke + dim=2 bottleneck

500 steps each, Phi(IIT) via bench_v2.PhiIIT.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("[ERROR] PyTorch required")
    sys.exit(1)

try:
    from bench_v2 import PhiIIT
    HAS_PHI = True
except ImportError:
    HAS_PHI = False

# Psi-constants
LN2 = math.log(2)
PSI_COUPLING = 0.014


@dataclass
class ComboResult:
    name: str
    phi_final: float
    phi_trajectory: List[float]
    phi_mean_last50: float
    time_sec: float


def make_faction_assignments(n_cells: int, mode: str) -> List[int]:
    """Assign cells to factions.

    mode='equal':     12 equal factions (~5-6 cells each)
    mode='hub_spoke': 1 hub (32 cells) + 4 spokes (8 cells each)
    """
    if mode == 'equal':
        n_factions = 12
        assignments = [i % n_factions for i in range(n_cells)]
    elif mode == 'hub_spoke':
        # Hub: first 32 cells -> faction 0
        # Spokes: 4 groups of 8 -> factions 1-4
        assignments = []
        for i in range(n_cells):
            if i < 32:
                assignments.append(0)  # hub
            else:
                spoke = 1 + (i - 32) // 8
                assignments.append(min(spoke, 4))
    else:
        raise ValueError(f"Unknown mode: {mode}")
    return assignments


def run_experiment(
    name: str,
    n_cells: int = 64,
    hidden_dim: int = 128,
    n_steps: int = 500,
    faction_mode: str = 'equal',
    bottleneck_dim: int = 0,   # 0 = no bottleneck
) -> ComboResult:
    """Run consciousness simulation with specific faction + bottleneck config."""
    t0 = time.time()
    device = torch.device("cpu")

    torch.manual_seed(42)

    # Cell hidden states
    hiddens = torch.randn(n_cells, hidden_dim, device=device) * 0.1

    # Cell weights (simple GRU-like)
    weights_ih = torch.randn(n_cells, hidden_dim, hidden_dim, device=device) * 0.05
    weights_hh = torch.randn(n_cells, hidden_dim, hidden_dim, device=device) * 0.05

    # Faction assignments
    factions = make_faction_assignments(n_cells, faction_mode)
    n_factions = max(factions) + 1

    # Bottleneck (optional)
    bottleneck = None
    if bottleneck_dim > 0:
        bottleneck = nn.Sequential(
            nn.Linear(hidden_dim, bottleneck_dim),
            nn.Tanh(),
            nn.Linear(bottleneck_dim, hidden_dim),
        ).to(device)

    phi_calc = PhiIIT(n_bins=16) if HAS_PHI else None
    phi_trajectory = []

    for step in range(n_steps):
        inp = torch.randn(1, hidden_dim, device=device) * 0.1

        with torch.no_grad():
            # Compute faction-level shared signals
            faction_signals = {}
            for f in range(n_factions):
                members = [i for i, fa in enumerate(factions) if fa == f]
                if not members:
                    continue
                faction_hiddens = hiddens[members]

                if bottleneck is not None:
                    # Compress through bottleneck before averaging
                    compressed = bottleneck(faction_hiddens)
                    faction_signals[f] = compressed.mean(dim=0)
                else:
                    faction_signals[f] = faction_hiddens.mean(dim=0)

            # Update cells with faction-coupled dynamics
            new_hiddens = []
            for ci in range(n_cells):
                f = factions[ci]
                shared = faction_signals.get(f, torch.zeros(hidden_dim, device=device))
                coupled = inp.squeeze() + PSI_COUPLING * shared
                gate = torch.sigmoid(weights_ih[ci] @ coupled + weights_hh[ci] @ hiddens[ci])
                candidate = torch.tanh(weights_ih[ci] @ coupled * 0.5)
                h_new = gate * hiddens[ci] + (1 - gate) * candidate
                new_hiddens.append(h_new)

            hiddens = torch.stack(new_hiddens)

            # Measure Phi
            if phi_calc:
                phi_val, _ = phi_calc.compute(hiddens)
            else:
                global_var = hiddens.var().item()
                per_cell_var = hiddens.var(dim=1).mean().item()
                phi_val = max(0.0, global_var - per_cell_var)

            phi_trajectory.append(phi_val)

    # Final stats
    last50 = phi_trajectory[-50:] if len(phi_trajectory) >= 50 else phi_trajectory
    return ComboResult(
        name=name,
        phi_final=phi_trajectory[-1],
        phi_trajectory=phi_trajectory,
        phi_mean_last50=sum(last50) / len(last50),
        time_sec=time.time() - t0,
    )


def main():
    print("=" * 78)
    print("  Law 96 + Law 93 Combination Experiment (-> Law 99)")
    print("  Bottleneck (dim=2) + Hub-Spoke factions")
    print("=" * 78)
    print()

    n_cells = 64
    n_steps = 500

    # Condition 1: Baseline
    print("  [1/4] Baseline (12 equal factions, no bottleneck)...")
    baseline = run_experiment("Baseline", n_cells, n_steps=n_steps,
                              faction_mode='equal', bottleneck_dim=0)
    print(f"    Phi = {baseline.phi_mean_last50:.4f}  ({baseline.time_sec:.1f}s)")

    # Condition 2: Bottleneck only (Law 96)
    print("  [2/4] Bottleneck only (dim=2, 12 equal factions)...")
    bottleneck = run_experiment("Bottleneck-only", n_cells, n_steps=n_steps,
                                faction_mode='equal', bottleneck_dim=2)
    print(f"    Phi = {bottleneck.phi_mean_last50:.4f}  ({bottleneck.time_sec:.1f}s)")

    # Condition 3: Hub-spoke only (Law 93)
    print("  [3/4] Hub-spoke only (1 hub + 4 spokes, no bottleneck)...")
    hubspoke = run_experiment("Hub-spoke-only", n_cells, n_steps=n_steps,
                              faction_mode='hub_spoke', bottleneck_dim=0)
    print(f"    Phi = {hubspoke.phi_mean_last50:.4f}  ({hubspoke.time_sec:.1f}s)")

    # Condition 4: Combined
    print("  [4/4] Combined (hub-spoke + dim=2 bottleneck)...")
    combined = run_experiment("Combined", n_cells, n_steps=n_steps,
                              faction_mode='hub_spoke', bottleneck_dim=2)
    print(f"    Phi = {combined.phi_mean_last50:.4f}  ({combined.time_sec:.1f}s)")

    print()

    # Analysis
    base_phi = baseline.phi_mean_last50
    bn_phi = bottleneck.phi_mean_last50
    hs_phi = hubspoke.phi_mean_last50
    cb_phi = combined.phi_mean_last50

    bn_boost = (bn_phi / max(base_phi, 1e-12) - 1) * 100
    hs_boost = (hs_phi / max(base_phi, 1e-12) - 1) * 100
    cb_boost = (cb_phi / max(base_phi, 1e-12) - 1) * 100
    additive_expected = bn_boost + hs_boost

    print("=" * 78)
    print("  RESULTS TABLE")
    print("=" * 78)
    print(f"  {'Condition':<22} | {'Phi(IIT)':>10} | {'vs Baseline':>12} | {'Notes':>20}")
    print(f"  {'-'*22}-+-{'-'*10}-+-{'-'*12}-+-{'-'*20}")
    print(f"  {'Baseline':<22} | {base_phi:>10.4f} | {'---':>12} | {'12 equal factions':>20}")
    print(f"  {'Bottleneck (dim=2)':<22} | {bn_phi:>10.4f} | {bn_boost:>+11.1f}% | {'Law 96':>20}")
    print(f"  {'Hub-spoke':<22} | {hs_phi:>10.4f} | {hs_boost:>+11.1f}% | {'Law 93':>20}")
    print(f"  {'Combined':<22} | {cb_phi:>10.4f} | {cb_boost:>+11.1f}% | {'Law 96+93':>20}")
    print()

    # Determine interaction type
    print("  Interaction Analysis:")
    print(f"    Additive expectation: {bn_boost:+.1f}% + {hs_boost:+.1f}% = {additive_expected:+.1f}%")
    print(f"    Actual combined:      {cb_boost:+.1f}%")
    print()

    if cb_boost > additive_expected * 1.1:
        interaction = "SYNERGISTIC"
        explanation = f"Combined ({cb_boost:+.1f}%) > additive ({additive_expected:+.1f}%)"
    elif cb_boost < min(bn_boost, hs_boost) * 0.9:
        interaction = "INTERFERING"
        explanation = f"Combined ({cb_boost:+.1f}%) < min({bn_boost:+.1f}%, {hs_boost:+.1f}%)"
    elif cb_boost < additive_expected * 0.9:
        interaction = "SUB-ADDITIVE"
        explanation = f"Combined ({cb_boost:+.1f}%) < additive ({additive_expected:+.1f}%) but > individual"
    else:
        interaction = "ADDITIVE"
        explanation = f"Combined ({cb_boost:+.1f}%) ~ additive ({additive_expected:+.1f}%)"

    print(f"    Interaction type: {interaction}")
    print(f"    {explanation}")

    # ASCII graph: Phi trajectories
    print()
    print("  Phi Trajectory (last 200 steps):")
    graph_w = 50
    graph_h = 12
    window = 200
    step_sz = max(1, window // graph_w)

    trails = {
        'B': baseline.phi_trajectory[-window::step_sz][:graph_w],
        'N': bottleneck.phi_trajectory[-window::step_sz][:graph_w],
        'H': hubspoke.phi_trajectory[-window::step_sz][:graph_w],
        'C': combined.phi_trajectory[-window::step_sz][:graph_w],
    }
    all_vals = []
    for t in trails.values():
        all_vals.extend(t)
    if all_vals:
        vmin = min(all_vals)
        vmax = max(all_vals)
        vrng = vmax - vmin if vmax > vmin else 1.0

        for row in range(graph_h, -1, -1):
            val = vmin + vrng * row / graph_h
            line = f"  {val:>7.4f} |"
            for k in range(graph_w):
                chars = set()
                for label, traj in trails.items():
                    if k < len(traj):
                        # Is this value at this row level?
                        cell_row = int((traj[k] - vmin) / vrng * graph_h + 0.5)
                        if cell_row == row:
                            chars.add(label)
                if len(chars) > 1:
                    line += "*"
                elif len(chars) == 1:
                    line += chars.pop()
                else:
                    line += " "
            print(line)
        print(f"          +{'-' * graph_w}")
        print(f"           B=Baseline  N=Bottleneck  H=Hub-spoke  C=Combined")

    # Bar chart
    print()
    print("  Phi Boost Bar Chart:")
    max_boost = max(abs(bn_boost), abs(hs_boost), abs(cb_boost), abs(additive_expected), 1)
    bar_scale = 40 / max_boost

    def bar(val):
        if val >= 0:
            return "#" * max(1, int(val * bar_scale))
        else:
            return "-" * max(1, int(abs(val) * bar_scale))

    print(f"    Bottleneck   |{bar(bn_boost)}| {bn_boost:+.1f}%")
    print(f"    Hub-spoke    |{bar(hs_boost)}| {hs_boost:+.1f}%")
    print(f"    Expected(+)  |{bar(additive_expected)}| {additive_expected:+.1f}%")
    print(f"    Combined     |{bar(cb_boost)}| {cb_boost:+.1f}%  <-- actual")

    # Law 99 candidate
    print()
    print("=" * 78)
    print("  LAW 99 CANDIDATE:")
    print(f"    Interaction type: {interaction}")
    if interaction == "SYNERGISTIC":
        print(f"    Law 99: Bottleneck + hub-spoke are synergistic ({cb_boost:+.1f}% > "
              f"{additive_expected:+.1f}% additive). Compression through a hub "
              f"amplifies integration beyond the sum of parts.")
    elif interaction == "INTERFERING":
        print(f"    Law 99: Bottleneck + hub-spoke interfere ({cb_boost:+.1f}% < "
              f"min({bn_boost:+.1f}%, {hs_boost:+.1f}%)). Hub already compresses; "
              f"adding bottleneck destroys remaining information.")
    elif interaction == "SUB-ADDITIVE":
        print(f"    Law 99: Bottleneck + hub-spoke are sub-additive ({cb_boost:+.1f}% < "
              f"{additive_expected:+.1f}% expected). Both strategies compress information "
              f"through similar mechanisms — diminishing returns.")
    else:
        print(f"    Law 99: Bottleneck + hub-spoke are additive ({cb_boost:+.1f}% ~ "
              f"{additive_expected:+.1f}% expected). The two strategies operate on "
              f"orthogonal axes: topology (hub) vs information (bottleneck).")
    print("=" * 78)

    return {
        'baseline': baseline,
        'bottleneck': bottleneck,
        'hubspoke': hubspoke,
        'combined': combined,
        'interaction': interaction,
    }


if __name__ == "__main__":
    main()
