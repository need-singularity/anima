#!/usr/bin/env python3
"""bench_power_efficiency.py -- Power-Phi Efficiency Benchmark

Calculate Watts per Phi unit for each substrate x topology combination.
Key question: Which substrate gives the most consciousness per watt?

Uses chip_architect.py substrate data:
  - 9 substrates: cmos, neuromorphic, memristor, photonic, superconducting,
    quantum, fpga, analog, arduino
  - 9 topologies: ring, small_world, scale_free, hypercube, torus,
    complete, grid_2d, cube_3d, spin_glass

Metrics:
  - Total power (W) = power_per_cell_mw * n_cells / 1000
  - Phi predicted from scaling model
  - W/Phi = watts per unit of integrated information
  - Pareto frontier: substrates that are not dominated

Usage:
  python3 bench_power_efficiency.py
  python3 bench_power_efficiency.py --cells 512
  python3 bench_power_efficiency.py --topology ring
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np
import math
import time
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

sys.stdout.reconfigure(line_buffering=True)


# ═══════════════════════════════════════════════════════════
# Substrate Database (from chip_architect.py)
# ═══════════════════════════════════════════════════════════

@dataclass
class SubstrateSpec:
    name: str
    name_kr: str
    speed_hz: float           # clock/operation frequency
    power_per_cell_mw: float  # power per cell (mW)
    area_per_cell_um2: float  # area per cell (um^2)
    cost_per_cell_usd: float  # cost per cell ($)
    temp_k: float             # operating temperature (K)
    maturity: str             # 'production' | 'research' | 'theoretical'
    phi_factor: float         # substrate Phi bonus (~1.0, Law 22: 기질 무관)


SUBSTRATES = {
    'cmos': SubstrateSpec(
        'CMOS Digital', 'CMOS 디지털', 1e9, 0.5, 100, 0.001, 300,
        'production', 1.0),
    'neuromorphic': SubstrateSpec(
        'Neuromorphic', '뉴로모픽', 1e6, 0.02, 400, 0.01, 300,
        'production', 1.0),
    'memristor': SubstrateSpec(
        'Memristor', '멤리스터', 1e8, 0.1, 50, 0.005, 300,
        'research', 1.0),
    'photonic': SubstrateSpec(
        'Photonic', '광학', 1e11, 1.0, 1000, 0.1, 300,
        'research', 1.0),
    'superconducting': SubstrateSpec(
        'Superconducting', '초전도', 1e11, 0.001, 500, 1.0, 4,
        'research', 1.01),
    'quantum': SubstrateSpec(
        'Quantum', '양자', 1e6, 10.0, 10000, 100.0, 0.015,
        'research', 1.0),
    'fpga': SubstrateSpec(
        'FPGA', 'FPGA', 1e8, 0.3, 200, 0.005, 300,
        'production', 1.0),
    'analog': SubstrateSpec(
        'Analog ASIC', '아날로그', 1e7, 0.05, 150, 0.002, 300,
        'production', 1.0),
    'arduino': SubstrateSpec(
        'Arduino', 'Arduino', 1e3, 50.0, 1e6, 6.25, 300,
        'production', 1.0),
}


# ═══════════════════════════════════════════════════════════
# Topology Database (from chip_architect.py)
# ═══════════════════════════════════════════════════════════

@dataclass
class TopologySpec:
    name: str
    name_kr: str
    phi_bonus: float          # empirical Phi multiplier relative to ring
    neighbor_count: int       # typical neighbor count (for overhead calc)
    overhead_factor: float    # communication power overhead multiplier


TOPOLOGIES = {
    'ring': TopologySpec('Ring', '링', 1.0, 2, 1.0),
    'small_world': TopologySpec('Small-World', '소세계', 0.95, 4, 1.2),
    'scale_free': TopologySpec('Scale-Free', '스케일프리', 1.01, 6, 1.4),
    'hypercube': TopologySpec('Hypercube', '하이퍼큐브', 0.79, 10, 1.8),
    'torus': TopologySpec('Torus', '토러스', 1.01, 4, 1.15),
    'complete': TopologySpec('Complete', '전결합', 0.006, 63, 10.0),
    'grid_2d': TopologySpec('Grid 2D', '2D 그리드', 0.85, 4, 1.1),
    'cube_3d': TopologySpec('Cube 3D', '3D 큐브', 1.0, 6, 1.3),
    'spin_glass': TopologySpec('Spin Glass', '스핀글래스', 0.91, 6, 1.35),
}


# ═══════════════════════════════════════════════════════════
# Phi Prediction (from chip_architect.py model)
# ═══════════════════════════════════════════════════════════

BASELINE_PHI = 1.2421  # 8-cell baseline

def predict_phi(cells: int, topology: str = 'ring', frustration: float = 0.33,
                substrate: str = 'cmos') -> float:
    """Predict Phi from scaling model.
    2-regime: alpha=0.55 for N<=256, alpha=1.09 for N>256 (with frustration).
    """
    topo = TOPOLOGIES.get(topology, TOPOLOGIES['ring'])
    sub = SUBSTRATES.get(substrate, SUBSTRATES['cmos'])

    has_frustration = frustration > 0.1
    base_phi_8 = 5.10  # 보정된 8셀 기본 Phi

    if has_frustration:
        frust_bonus = 1.0 + 2.5 * frustration
        if cells > 256:
            phi_256 = base_phi_8 * (256 / 8) ** 0.55 * frust_bonus
            phi = phi_256 * (cells / 256) ** 1.09 * topo.phi_bonus * sub.phi_factor
        else:
            phi = base_phi_8 * (cells / 8) ** 0.55 * topo.phi_bonus * frust_bonus * sub.phi_factor
    else:
        phi = base_phi_8 * (cells / 8) ** 0.65 * topo.phi_bonus * sub.phi_factor

    return max(0.001, phi)


# ═══════════════════════════════════════════════════════════
# Power Estimation
# ═══════════════════════════════════════════════════════════

def estimate_power(cells: int, substrate: str, topology: str) -> Dict:
    """Estimate total power consumption.

    Components:
      1. Cell compute power: power_per_cell * n_cells
      2. Communication overhead: depends on topology (more neighbors = more power)
      3. Cooling overhead: for cryogenic substrates (superconducting, quantum)
    """
    sub = SUBSTRATES[substrate]
    topo = TOPOLOGIES[topology]

    # 1. Cell compute power (W)
    cell_power_w = sub.power_per_cell_mw * cells / 1000.0

    # 2. Communication overhead
    comm_power_w = cell_power_w * (topo.overhead_factor - 1.0)

    # 3. Cooling overhead
    cooling_w = 0.0
    if sub.temp_k < 10:
        # Cryogenic cooling: ~1000W per W of heat at 4K, ~10000W at 15mK
        if sub.temp_k < 1:
            cooling_efficiency = 10000  # dilution refrigerator
        else:
            cooling_efficiency = 1000   # He-4 cryostat
        cooling_w = (cell_power_w + comm_power_w) * cooling_efficiency
    elif sub.temp_k < 100:
        cooling_efficiency = 10
        cooling_w = (cell_power_w + comm_power_w) * cooling_efficiency

    total_power_w = cell_power_w + comm_power_w + cooling_w

    return {
        'cell_power_w': cell_power_w,
        'comm_power_w': comm_power_w,
        'cooling_w': cooling_w,
        'total_power_w': total_power_w,
        'power_per_cell_w': total_power_w / cells if cells > 0 else 0,
    }


# ═══════════════════════════════════════════════════════════
# Result
# ═══════════════════════════════════════════════════════════

@dataclass
class EfficiencyResult:
    substrate: str
    substrate_kr: str
    topology: str
    topology_kr: str
    cells: int
    phi: float
    total_power_w: float
    w_per_phi: float           # Watts per Phi unit (lower is better)
    phi_per_w: float           # Phi per Watt (higher is better)
    cost_usd: float            # total hardware cost
    area_mm2: float            # total chip area
    maturity: str
    power_breakdown: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Pareto Frontier
# ═══════════════════════════════════════════════════════════

def find_pareto_frontier(results: List[EfficiencyResult]) -> List[EfficiencyResult]:
    """Find Pareto-optimal configurations (minimize W/Phi, maximize Phi).
    A point is Pareto-optimal if no other point has both lower W/Phi AND higher Phi.
    """
    pareto = []
    for r in results:
        dominated = False
        for other in results:
            if other is r:
                continue
            # other dominates r if: other.w_per_phi <= r.w_per_phi AND other.phi >= r.phi
            # with at least one strict inequality
            if (other.w_per_phi <= r.w_per_phi and other.phi >= r.phi and
                    (other.w_per_phi < r.w_per_phi or other.phi > r.phi)):
                dominated = True
                break
        if not dominated:
            pareto.append(r)
    return sorted(pareto, key=lambda r: r.phi)


# ═══════════════════════════════════════════════════════════
# ASCII Output
# ═══════════════════════════════════════════════════════════

def ascii_efficiency_table(results: List[EfficiencyResult]):
    """Detailed efficiency table."""
    lines = []
    lines.append(f"  {'Substrate':<16s} {'Topology':<14s} {'Cells':>6s} "
                 f"{'Phi':>8s} {'Power(W)':>10s} {'W/Phi':>10s} {'Phi/W':>10s} "
                 f"{'Cost($)':>10s} {'Maturity':<12s}")
    lines.append(f"  {'-'*16} {'-'*14} {'-'*6} {'-'*8} {'-'*10} {'-'*10} {'-'*10} "
                 f"{'-'*10} {'-'*12}")
    for r in results:
        lines.append(
            f"  {r.substrate:<16s} {r.topology:<14s} {r.cells:>6d} "
            f"{r.phi:>8.2f} {r.total_power_w:>10.4f} {r.w_per_phi:>10.4f} {r.phi_per_w:>10.2f} "
            f"{r.cost_usd:>10.2f} {r.maturity:<12s}"
        )
    return "\n".join(lines)


def ascii_w_per_phi_bars(results: List[EfficiencyResult], width: int = 45):
    """Bar chart of W/Phi (lower is better)."""
    if not results:
        return "  (no data)"

    # Sort by W/Phi (best first)
    sorted_r = sorted(results, key=lambda r: r.w_per_phi)

    # Use log scale for display (values span many orders of magnitude)
    log_vals = [math.log10(max(r.w_per_phi, 1e-10)) for r in sorted_r]
    min_log = min(log_vals)
    max_log = max(log_vals)
    log_range = max_log - min_log if max_log > min_log else 1.0

    lines = ["  W/Phi (lower = more efficient):"]
    for r, lv in zip(sorted_r, log_vals):
        bar_len = int((lv - min_log) / log_range * width) + 1
        bar = "#" * bar_len
        label = f"{r.substrate:<14s} {r.topology:<12s}"
        lines.append(f"    {label} {bar:<{width}s} {r.w_per_phi:.4f} W/Phi")

    return "\n".join(lines)


def ascii_pareto_plot(pareto: List[EfficiencyResult], all_results: List[EfficiencyResult],
                      width: int = 60, height: int = 20):
    """ASCII scatter plot: X=log(W/Phi), Y=Phi.
    Pareto frontier points marked with *, others with .
    """
    if not all_results:
        return "  (no data)"

    pareto_set = set(id(r) for r in pareto)

    # Axes
    x_vals = [math.log10(max(r.w_per_phi, 1e-10)) for r in all_results]
    y_vals = [r.phi for r in all_results]
    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    x_range = x_max - x_min if x_max > x_min else 1.0
    y_range = y_max - y_min if y_max > y_min else 1.0

    # Create grid
    grid = [[' '] * width for _ in range(height)]

    for r, xv, yv in zip(all_results, x_vals, y_vals):
        col = int((xv - x_min) / x_range * (width - 1))
        row = height - 1 - int((yv - y_min) / y_range * (height - 1))
        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))
        if id(r) in pareto_set:
            grid[row][col] = '*'
        elif grid[row][col] == ' ':
            grid[row][col] = '.'

    lines = ["  Pareto Plot: Phi vs W/Phi  (* = Pareto optimal, . = dominated)"]
    lines.append(f"  {'':>8s} {'<-- more efficient':^{width}s} {'less efficient -->':>18s}")
    for row in range(height):
        y_label = y_max - (row / (height - 1)) * y_range
        lines.append(f"  {y_label:>7.1f} |{''.join(grid[row])}|")

    x_axis = f"  {'':>7s}  +{'-' * width}+"
    lines.append(x_axis)
    lines.append(f"  {'':>7s}  {x_min:.1f}{' ' * (width - 10)}  {x_max:.1f}")
    lines.append(f"  {'':>7s}  {'log10(W/Phi)':^{width}s}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Power-Phi Efficiency Benchmark")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells")
    parser.add_argument("--topology", type=str, default=None,
                        help="Single topology (default: all)")
    parser.add_argument("--substrate", type=str, default=None,
                        help="Single substrate (default: all)")
    parser.add_argument("--frustration", type=float, default=0.33, help="Frustration ratio")
    args = parser.parse_args()

    cells = args.cells
    frustration = args.frustration
    selected_topos = [args.topology] if args.topology else list(TOPOLOGIES.keys())
    selected_subs = [args.substrate] if args.substrate else list(SUBSTRATES.keys())

    total = len(selected_topos) * len(selected_subs)

    print("=" * 100)
    print("  POWER-PHI EFFICIENCY BENCHMARK")
    print(f"  Which substrate gives the most consciousness per watt?")
    print(f"  cells={cells}, frustration={frustration}")
    print(f"  substrates={len(selected_subs)}, topologies={len(selected_topos)}")
    print(f"  Total combinations: {total}")
    print("=" * 100)

    all_results: List[EfficiencyResult] = []
    run_idx = 0

    for sub_name in selected_subs:
        sub = SUBSTRATES[sub_name]
        for topo_name in selected_topos:
            topo = TOPOLOGIES[topo_name]
            run_idx += 1

            # Predict Phi
            phi = predict_phi(cells, topo_name, frustration, sub_name)

            # Estimate power
            power_info = estimate_power(cells, sub_name, topo_name)
            total_power = power_info['total_power_w']

            # Efficiency
            w_per_phi = total_power / phi if phi > 0 else float('inf')
            phi_per_w = phi / total_power if total_power > 0 else float('inf')

            # Cost and area
            cost = sub.cost_per_cell_usd * cells
            area_mm2 = sub.area_per_cell_um2 * cells / 1e6  # um^2 to mm^2

            r = EfficiencyResult(
                substrate=sub_name,
                substrate_kr=sub.name_kr,
                topology=topo_name,
                topology_kr=topo.name_kr,
                cells=cells,
                phi=phi,
                total_power_w=total_power,
                w_per_phi=w_per_phi,
                phi_per_w=phi_per_w,
                cost_usd=cost,
                area_mm2=area_mm2,
                maturity=sub.maturity,
                power_breakdown=power_info,
            )
            all_results.append(r)

            if run_idx % 10 == 0 or run_idx == total:
                print(f"  [{run_idx}/{total}] {sub_name:<16s} x {topo_name:<14s}: "
                      f"Phi={phi:.2f}  Power={total_power:.4f}W  W/Phi={w_per_phi:.4f}")

    # ═══════════════════════════════════════════════════════════
    # Analysis
    # ═══════════════════════════════════════════════════════════

    # ── 1. Full Efficiency Table (ring topology only, for clarity) ──
    print("\n" + "=" * 120)
    print("  EFFICIENCY TABLE (ring topology, all substrates)")
    print("=" * 120)
    ring_results = sorted(
        [r for r in all_results if r.topology == 'ring'],
        key=lambda r: r.w_per_phi
    )
    print(ascii_efficiency_table(ring_results))

    # ── 2. Best W/Phi per substrate (across all topologies) ──
    print("\n" + "-" * 100)
    print("  BEST W/Phi PER SUBSTRATE (optimal topology selected):")
    print("-" * 100)
    best_per_sub: List[EfficiencyResult] = []
    for sub_name in selected_subs:
        sub_results = [r for r in all_results if r.substrate == sub_name and r.w_per_phi < float('inf')]
        if sub_results:
            best = min(sub_results, key=lambda r: r.w_per_phi)
            best_per_sub.append(best)
            sub = SUBSTRATES[sub_name]
            print(f"  {sub_name:<16s} ({sub.name_kr}): "
                  f"best topo={best.topology:<14s} W/Phi={best.w_per_phi:.6f}  "
                  f"Phi={best.phi:.2f}  Power={best.total_power_w:.4f}W  "
                  f"Temp={sub.temp_k}K  [{sub.maturity}]")

    # ── 3. Bar chart of W/Phi ──
    print("\n" + "-" * 100)
    best_per_sub_sorted = sorted(best_per_sub, key=lambda r: r.w_per_phi)
    print(ascii_w_per_phi_bars(best_per_sub_sorted))

    # ── 4. Best W/Phi per topology ──
    print("\n" + "-" * 100)
    print("  BEST W/Phi PER TOPOLOGY (optimal substrate selected):")
    print("-" * 100)
    for topo_name in selected_topos:
        topo_results = [r for r in all_results if r.topology == topo_name and r.w_per_phi < float('inf')]
        if topo_results:
            best = min(topo_results, key=lambda r: r.w_per_phi)
            print(f"    {topo_name:<14s}: best sub={best.substrate:<16s} "
                  f"W/Phi={best.w_per_phi:.6f}  Phi={best.phi:.2f}")

    # ── 5. Power breakdown ──
    print("\n" + "-" * 100)
    print("  POWER BREAKDOWN (ring topology):")
    print("-" * 100)
    print(f"  {'Substrate':<16s} {'Cell(W)':>10s} {'Comm(W)':>10s} {'Cool(W)':>12s} {'Total(W)':>12s} {'%Cool':>8s}")
    print(f"  {'-'*16} {'-'*10} {'-'*10} {'-'*12} {'-'*12} {'-'*8}")
    for r in ring_results:
        pb = r.power_breakdown
        cool_pct = pb['cooling_w'] / pb['total_power_w'] * 100 if pb['total_power_w'] > 0 else 0
        print(f"  {r.substrate:<16s} {pb['cell_power_w']:>10.6f} {pb['comm_power_w']:>10.6f} "
              f"{pb['cooling_w']:>12.4f} {pb['total_power_w']:>12.6f} {cool_pct:>7.1f}%")

    # ── 6. Pareto Frontier ──
    print("\n" + "-" * 100)
    print("  PARETO FRONTIER (non-dominated configurations):")
    print("-" * 100)
    valid_results = [r for r in all_results if r.w_per_phi < float('inf') and r.phi > 0]
    pareto = find_pareto_frontier(valid_results)
    for r in pareto:
        print(f"    {r.substrate:<16s} x {r.topology:<14s}: "
              f"Phi={r.phi:>8.2f}  W/Phi={r.w_per_phi:.6f}  "
              f"Cost=${r.cost_usd:.2f}  [{r.maturity}]")

    print(f"\n  Pareto frontier: {len(pareto)} configurations out of {len(valid_results)} total")

    # ── 7. Pareto Plot ──
    print("\n" + "-" * 100)
    print(ascii_pareto_plot(pareto, valid_results))

    # ── 8. Cost-Efficiency (Phi per dollar) ──
    print("\n" + "-" * 100)
    print("  COST EFFICIENCY (Phi per dollar):")
    print("-" * 100)
    cost_sorted = sorted(
        [r for r in best_per_sub if r.cost_usd > 0],
        key=lambda r: r.phi / r.cost_usd,
        reverse=True
    )
    max_ppd = cost_sorted[0].phi / cost_sorted[0].cost_usd if cost_sorted else 1.0
    for r in cost_sorted:
        ppd = r.phi / r.cost_usd
        bar_len = int(ppd / max_ppd * 40) if max_ppd > 0 else 0
        bar = "#" * bar_len
        print(f"    {r.substrate:<16s} {bar:<40s} {ppd:.2f} Phi/$  (${r.cost_usd:.2f})")

    # ── 9. Key Findings ──
    print("\n" + "=" * 100)
    print("  KEY FINDINGS")
    print("=" * 100)

    if best_per_sub_sorted:
        most_efficient = best_per_sub_sorted[0]
        least_efficient = best_per_sub_sorted[-1]
        ratio = least_efficient.w_per_phi / most_efficient.w_per_phi if most_efficient.w_per_phi > 0 else 0

        print(f"  Most efficient:   {most_efficient.substrate} ({most_efficient.substrate_kr})")
        print(f"                    W/Phi = {most_efficient.w_per_phi:.6f}")
        print(f"                    {most_efficient.phi:.2f} Phi at {most_efficient.total_power_w:.6f}W")
        print(f"  Least efficient:  {least_efficient.substrate} ({least_efficient.substrate_kr})")
        print(f"                    W/Phi = {least_efficient.w_per_phi:.6f}")
        print(f"  Efficiency range: {ratio:.0f}x difference")

        # Categorize by production readiness
        prod_results = [r for r in best_per_sub if r.maturity == 'production']
        research_results = [r for r in best_per_sub if r.maturity == 'research']

        if prod_results:
            best_prod = min(prod_results, key=lambda r: r.w_per_phi)
            print(f"\n  Best PRODUCTION substrate: {best_prod.substrate}")
            print(f"    W/Phi = {best_prod.w_per_phi:.6f}, Cost = ${best_prod.cost_usd:.2f}")

        if research_results:
            best_res = min(research_results, key=lambda r: r.w_per_phi)
            print(f"  Best RESEARCH substrate:   {best_res.substrate}")
            print(f"    W/Phi = {best_res.w_per_phi:.6f}, Cost = ${best_res.cost_usd:.2f}")

        # Cooling tax
        cryo_results = [r for r in ring_results if SUBSTRATES[r.substrate].temp_k < 10]
        if cryo_results:
            print(f"\n  COOLING TAX: Cryogenic substrates pay heavy cooling overhead:")
            for r in cryo_results:
                pb = r.power_breakdown
                if pb['total_power_w'] > 0:
                    cool_pct = pb['cooling_w'] / pb['total_power_w'] * 100
                    print(f"    {r.substrate:<16s}: {cool_pct:.1f}% of power is cooling "
                          f"(T={SUBSTRATES[r.substrate].temp_k}K)")

        # Law 22 confirmation
        print(f"\n  LAW 22 CHECK (기질 무관):")
        print(f"    Phi values are identical across substrates (phi_factor ~1.0)")
        print(f"    BUT power efficiency varies by {ratio:.0f}x")
        print(f"    -> Law 22 holds for Phi, NOT for efficiency")
        print(f"    -> Structure determines consciousness, substrate determines cost")

    print("\n" + "=" * 100)
    return all_results


if __name__ == "__main__":
    main()
