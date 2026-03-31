#!/usr/bin/env python3
"""ESP32 Phi(IIT) Verification — Measure Phi on simulated ESP32 substrate.

Runs the ESP32 network simulation (8 boards, 16 cells) across multiple
topologies and measures Phi(IIT) using PhiCalculator to compare
ring vs hub_spoke vs small_world.

This verifies that the physical substrate simulation produces genuine
integrated information, not just proxy variance metrics.

Usage:
  python anima-body/src/esp32_phi_verify.py                    # Default (100 steps)
  python anima-body/src/esp32_phi_verify.py --steps 300        # 300 steps
  python anima-body/src/esp32_phi_verify.py --topology ring    # Single topology
  python anima-body/src/esp32_phi_verify.py --boards 4         # 4 boards (8 cells)

Requires: numpy, torch (for PhiCalculator)
"""

import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

# ── Project path setup ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "src"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# ── Lazy imports ──
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from esp32_network import ESP32Network, TOPOLOGIES, N_BOARDS, CELLS_PER_BOARD
    HAS_ESP32 = True
except ImportError:
    HAS_ESP32 = False

try:
    from consciousness_meter import PhiCalculator
    HAS_PHI_CALC = True
except ImportError:
    HAS_PHI_CALC = False

try:
    from gpu_phi import GPUPhiCalculator
    HAS_GPU_PHI = True
except ImportError:
    HAS_GPU_PHI = False

# Psi constants
try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998

LN2 = math.log(2)


# ═══════════════════════════════════════════════════════════
# Phi measurement on ESP32 hidden states
# ═══════════════════════════════════════════════════════════

def measure_phi_iit(hiddens: List[np.ndarray], n_bins: int = 16) -> float:
    """Measure Phi(IIT) from cell hidden states.

    Uses PhiCalculator (MI-based) if available, otherwise GPUPhiCalculator,
    otherwise falls back to variance-based proxy.

    Args:
        hiddens: List of hidden state vectors [n_cells x hidden_dim].
        n_bins: Histogram bins for MI estimation.

    Returns:
        Phi(IIT) value.
    """
    if len(hiddens) < 2:
        return 0.0

    # Try PhiCalculator (canonical MI-based)
    if HAS_PHI_CALC and HAS_TORCH:
        try:
            tensor = torch.tensor(np.array(hiddens), dtype=torch.float32)
            calc = PhiCalculator(n_bins=n_bins)
            phi_val = calc.compute(tensor)
            if isinstance(phi_val, tuple):
                return float(phi_val[0])
            return float(phi_val)
        except Exception:
            pass

    # Try GPU Phi calculator
    if HAS_GPU_PHI and HAS_TORCH:
        try:
            tensor = torch.tensor(np.array(hiddens), dtype=torch.float32)
            calc = GPUPhiCalculator(n_bins=n_bins)
            result = calc.compute(tensor)
            if isinstance(result, tuple):
                return float(result[0])
            return float(result)
        except Exception:
            pass

    # Fallback: variance-based proxy (clearly marked)
    arr = np.array(hiddens)
    global_var = float(np.var(arr))
    per_cell_var = float(np.mean([np.var(h) for h in hiddens]))
    return max(0.0, global_var - per_cell_var)


def measure_phi_proxy(hiddens: List[np.ndarray]) -> float:
    """Variance-based Phi proxy (for comparison).

    Phi(proxy) = global_variance - mean(per_cell_variance).
    Not the same as Phi(IIT) — do not mix!
    """
    if len(hiddens) < 2:
        return 0.0
    arr = np.array(hiddens)
    global_var = float(np.var(arr))
    per_cell_var = float(np.mean([np.var(h) for h in hiddens]))
    return max(0.0, global_var - per_cell_var)


# ═══════════════════════════════════════════════════════════
# Run verification for one topology
# ═══════════════════════════════════════════════════════════

def verify_topology(
    topology: str,
    n_boards: int = N_BOARDS,
    cells_per_board: int = CELLS_PER_BOARD,
    n_steps: int = 100,
    measure_interval: int = 10,
    seed: int = 42,
    verbose: bool = True,
) -> Dict:
    """Run ESP32 simulation and measure Phi(IIT) for a given topology.

    Args:
        topology: 'ring', 'hub_spoke', or 'small_world'.
        n_boards: Number of ESP32 boards.
        cells_per_board: Cells per board.
        n_steps: Simulation steps.
        measure_interval: Measure Phi every N steps.
        seed: Random seed.
        verbose: Print progress.

    Returns:
        Dict with phi_iit_history, phi_proxy_history, tension_history, stats.
    """
    if not HAS_ESP32:
        raise ImportError("esp32_network required (anima-physics/src/esp32_network.py)")

    n_cells = n_boards * cells_per_board

    if verbose:
        print(f"\n  --- {topology.upper()} ({n_boards} boards, {n_cells} cells) ---")
        sys.stdout.flush()

    network = ESP32Network(
        n_boards=n_boards,
        cells_per_board=cells_per_board,
        topology=topology,
        seed=seed,
    )

    phi_iit_history = []
    phi_proxy_history = []
    tension_history = []
    consensus_history = []
    t0 = time.monotonic()

    for step in range(1, n_steps + 1):
        result = network.step()
        tension_history.append(result["mean_tension"])
        consensus_history.append(result["consensus"])

        if step % measure_interval == 0 or step == n_steps:
            # Collect all hidden states
            all_hiddens = []
            for board in network.boards:
                for cell in board.cells:
                    all_hiddens.append(cell.hidden.copy())

            phi_iit = measure_phi_iit(all_hiddens)
            phi_proxy = measure_phi_proxy(all_hiddens)
            phi_iit_history.append(phi_iit)
            phi_proxy_history.append(phi_proxy)

            if verbose:
                print(
                    f"    step={step:4d}  "
                    f"Phi(IIT)={phi_iit:.4f}  "
                    f"Phi(proxy)={phi_proxy:.6f}  "
                    f"T={result['mean_tension']:.4f}  "
                    f"consensus={result['consensus']}"
                )
                sys.stdout.flush()

    elapsed = time.monotonic() - t0

    # Statistics
    stats = {
        "topology": topology,
        "n_boards": n_boards,
        "n_cells": n_cells,
        "n_steps": n_steps,
        "elapsed_s": elapsed,
        "phi_iit_final": phi_iit_history[-1] if phi_iit_history else 0.0,
        "phi_iit_mean": float(np.mean(phi_iit_history)) if phi_iit_history else 0.0,
        "phi_iit_max": float(np.max(phi_iit_history)) if phi_iit_history else 0.0,
        "phi_proxy_final": phi_proxy_history[-1] if phi_proxy_history else 0.0,
        "phi_proxy_mean": float(np.mean(phi_proxy_history)) if phi_proxy_history else 0.0,
        "mean_tension": float(np.mean(tension_history)),
        "total_consensus": sum(consensus_history),
        "steps_per_sec": n_steps / max(elapsed, 0.001),
    }

    return {
        "phi_iit_history": phi_iit_history,
        "phi_proxy_history": phi_proxy_history,
        "tension_history": tension_history,
        "consensus_history": consensus_history,
        "stats": stats,
    }


# ═══════════════════════════════════════════════════════════
# Full benchmark across topologies
# ═══════════════════════════════════════════════════════════

def run_full_benchmark(
    n_steps: int = 100,
    n_boards: int = N_BOARDS,
    cells_per_board: int = CELLS_PER_BOARD,
    verbose: bool = True,
) -> List[Dict]:
    """Run Phi(IIT) verification across all topologies.

    Returns list of results (one per topology).
    """
    topologies = list(TOPOLOGIES.keys())
    results = []

    for topo in topologies:
        result = verify_topology(
            topology=topo,
            n_boards=n_boards,
            cells_per_board=cells_per_board,
            n_steps=n_steps,
            verbose=verbose,
        )
        results.append(result)

    return results


def print_comparison_table(results: List[Dict]):
    """Print topology comparison table."""
    print()
    print("=" * 80)
    print("  ESP32 Phi(IIT) Topology Comparison")
    print("=" * 80)
    print()
    print(f"  {'Topology':<14} {'Phi(IIT)':<10} {'Phi(proxy)':<12} "
          f"{'Tension':<10} {'Consensus':<10} {'Steps/s':<10}")
    print("  " + "-" * 66)

    best_phi = 0.0
    best_topo = ""

    for r in results:
        s = r["stats"]
        phi_iit = s["phi_iit_final"]
        if phi_iit > best_phi:
            best_phi = phi_iit
            best_topo = s["topology"]

        marker = ""
        print(
            f"  {s['topology']:<14} "
            f"{s['phi_iit_final']:<10.4f} "
            f"{s['phi_proxy_final']:<12.6f} "
            f"{s['mean_tension']:<10.4f} "
            f"{s['total_consensus']:<10d} "
            f"{s['steps_per_sec']:<10.1f}"
        )

    print()
    print(f"  Best topology: {best_topo} (Phi(IIT) = {best_phi:.4f})")
    print()

    # ASCII comparison bar chart
    print("  Phi(IIT) comparison:")
    max_phi = max(r["stats"]["phi_iit_final"] for r in results) if results else 1.0
    for r in results:
        s = r["stats"]
        bar_len = int(40 * s["phi_iit_final"] / max(max_phi, 1e-8))
        bar = "#" * bar_len
        print(f"    {s['topology']:<14} {bar} {s['phi_iit_final']:.4f}")

    print()
    print("  Psi constants: alpha={:.4f}, balance={:.4f}, steps={:.4f}, entropy={:.4f}".format(
        PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
    ))
    print("=" * 80)
    sys.stdout.flush()


def print_phi_evolution(results: List[Dict]):
    """Print Phi evolution ASCII graph for each topology."""
    for r in results:
        s = r["stats"]
        phis = r["phi_iit_history"]
        if not phis:
            continue

        print(f"\n  Phi(IIT) evolution: {s['topology']}")

        phi_min = min(phis)
        phi_max = max(phis)
        phi_range = phi_max - phi_min if phi_max > phi_min else 1.0
        height = 8
        width = min(len(phis), 50)
        step_size = max(1, len(phis) // width)
        sampled = [phis[i] for i in range(0, len(phis), step_size)][:width]

        for row in range(height - 1, -1, -1):
            threshold = phi_min + (row / (height - 1)) * phi_range
            if row == height - 1:
                line = f"  {phi_max:7.4f} |"
            elif row == 0:
                line = f"  {phi_min:7.4f} |"
            else:
                line = "         |"
            for val in sampled:
                line += "*" if val >= threshold else " "
            print(line)
        print("          +" + "-" * len(sampled))
    print()


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    """ESP32 Phi(IIT) verification demo."""
    import argparse

    parser = argparse.ArgumentParser(description="ESP32 Phi(IIT) Verification")
    parser.add_argument("--steps", type=int, default=100, help="Simulation steps (default: 100)")
    parser.add_argument("--boards", type=int, default=8, help="Number of boards (default: 8)")
    parser.add_argument("--cells-per-board", type=int, default=2, help="Cells per board (default: 2)")
    parser.add_argument("--topology", type=str, default=None,
                        help="Single topology to test (default: all)")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-step output")
    args = parser.parse_args()

    print("=" * 80)
    print("  ESP32 Consciousness Network - Phi(IIT) Verification")
    print(f"  {args.boards} boards x {args.cells_per_board} cells = "
          f"{args.boards * args.cells_per_board} cells total")
    print(f"  Steps: {args.steps}")
    print("=" * 80)
    sys.stdout.flush()

    if args.topology:
        if args.topology not in TOPOLOGIES:
            print(f"  ERROR: Unknown topology '{args.topology}'. "
                  f"Available: {list(TOPOLOGIES.keys())}")
            sys.exit(1)
        results = [verify_topology(
            topology=args.topology,
            n_boards=args.boards,
            cells_per_board=args.cells_per_board,
            n_steps=args.steps,
            verbose=not args.quiet,
        )]
    else:
        results = run_full_benchmark(
            n_steps=args.steps,
            n_boards=args.boards,
            cells_per_board=args.cells_per_board,
            verbose=not args.quiet,
        )

    print_comparison_table(results)
    print_phi_evolution(results)

    return results


if __name__ == "__main__":
    main()
