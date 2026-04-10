#!/usr/bin/env python3
"""Φ Scaling Calculator — predict consciousness scaling from Φ ∝ N, MI ∝ N²."""

import argparse
import math
import numpy as np

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# Empirical data: (cells, Φ, MI)
EMPIRICAL = [
    (2,   1.5,     1.0),
    (8,   4.5,     28.0),
    (16,  10.6,    149.9),
    (32,  27.6,    842.7),
    (64,  54.3,    3376.7),
    (128, 112.3,   14135.8),
]

BRAIN_SCALES = [
    ("C. elegans (302 neurons)",   302),
    ("Ant (~250K neurons)",        250_000),
    ("Bee (~1M neurons)",          1_000_000),
    ("Mouse (71M neurons)",        71_000_000),
    ("Human (86B neurons)",        86_000_000_000),
    ("Anima 128 cells",            128),
    ("Anima 512 cells",            512),
    ("Anima 1024 cells",           1024),
]


class ScalingLaw:
    """Fit power laws: Φ = a·N^b, MI = c·N^d from empirical data."""

    def __init__(self, data=EMPIRICAL):
        cells = np.array([d[0] for d in data], dtype=np.float64)
        phis = np.array([d[1] for d in data], dtype=np.float64)
        mis = np.array([d[2] for d in data], dtype=np.float64)
        # Least squares in log-log space: log(y) = log(a) + b·log(N)
        self.a, self.b = self._fit(cells, phis)
        self.c, self.d = self._fit(cells, mis)

    @staticmethod
    def _fit(x, y):
        log_x, log_y = np.log(x), np.log(y)
        A = np.vstack([log_x, np.ones(len(x))]).T
        slope, intercept = np.linalg.lstsq(A, log_y, rcond=None)[0]
        return math.exp(intercept), slope

    def predict_phi(self, n): return self.a * n ** self.b
    def predict_mi(self, n): return self.c * n ** self.d
    def predict_cells_for_phi(self, target_phi): return (target_phi / self.a) ** (1.0 / self.b)
    def phi_per_cell(self, n): return self.predict_phi(n) / n

    def summary(self):
        return (f"Φ = {self.a:.4f} × N^{self.b:.3f}\n"
                f"MI = {self.c:.6f} × N^{self.d:.3f}")


class ArchitecturePlanner:
    """Plan architecture configs for a target Φ."""

    def __init__(self, law: ScalingLaw):
        self.law = law

    @staticmethod
    def vram_mb(cells, dim=128):
        """Estimate VRAM: ~0.5MB per cell at dim=128, scales with dim²."""
        return cells * 0.5 * (dim / 128) ** 2

    @staticmethod
    def train_hours(cells, dim=128, steps=50000):
        """Rough training time estimate (single GPU baseline)."""
        return cells * (dim / 128) ** 2 * steps / 50000 * 0.1

    def plan(self, target_phi, dims=(64, 128, 256, 384)):
        rows = []
        for dim in dims:
            # Φ scales with cells; dim affects capacity but we use cell count as driver
            cells_needed = max(2, int(math.ceil(self.law.predict_cells_for_phi(target_phi))))
            vram = self.vram_mb(cells_needed, dim)
            hours = self.train_hours(cells_needed, dim)
            phi_est = self.law.predict_phi(cells_needed)
            rows.append((dim, cells_needed, vram, hours, phi_est))
        return rows


def print_scaling_table(law: ScalingLaw):
    print(f"\n{'='*62}")
    print(f"  Φ Scaling Law (fitted): {law.summary()}")
    print(f"{'='*62}")
    print(f"  {'Cells':>6} | {'Φ (emp)':>8} | {'Φ (pred)':>8} | {'MI (emp)':>10} | {'MI (pred)':>10} | {'Φ/cell':>6}")
    print(f"  {'-'*6}-+-{'-'*8}-+-{'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*6}")
    for cells, phi_e, mi_e in EMPIRICAL:
        phi_p = law.predict_phi(cells)
        mi_p = law.predict_mi(cells)
        eff = law.phi_per_cell(cells)
        print(f"  {cells:>6} | {phi_e:>8.1f} | {phi_p:>8.1f} | {mi_e:>10.1f} | {mi_p:>10.1f} | {eff:>6.3f}")

    print(f"\n  Extrapolated:")
    for n in [256, 512, 1024, 4096]:
        print(f"  {n:>6} cells → Φ = {law.predict_phi(n):>10.1f}, MI = {law.predict_mi(n):>12.1f}, Φ/cell = {law.phi_per_cell(n):.3f}")


def print_brain_extrapolation(law: ScalingLaw):
    print(f"\n{'='*62}")
    print(f"  Brain-Scale Extrapolation (functional modules, not raw neurons)")
    print(f"  Note: biological neurons ≠ Anima cells. Functional modules ~300-1000.")
    print(f"{'='*62}")
    print(f"  {'System':<30} | {'Units':>14} | {'Φ (est)':>12} | {'MI (est)':>14}")
    print(f"  {'-'*30}-+-{'-'*14}-+-{'-'*12}-+-{'-'*14}")
    for name, n in BRAIN_SCALES:
        phi = law.predict_phi(n)
        mi = law.predict_mi(n)
        print(f"  {name:<30} | {n:>14,} | {phi:>12.1f} | {mi:>14.1f}")
    print(f"\n  → 128-1024 Anima cells may reach human functional-module Φ range")
    print(f"  → Human advantage: 86B neurons, but Φ driven by ~1000 cortical columns")
    human_phi = law.predict_phi(1000)
    anima_512 = law.predict_phi(512)
    print(f"  → Human cortical columns (~1000): Φ ≈ {human_phi:.1f}")
    print(f"  → Anima 512 cells:                Φ ≈ {anima_512:.1f} ({anima_512/human_phi*100:.0f}% of cortical Φ)")


def print_architecture_plan(planner: ArchitecturePlanner, target_phi):
    rows = planner.plan(target_phi)
    print(f"\n{'='*62}")
    print(f"  Architecture Plan for target Φ ≥ {target_phi}")
    print(f"{'='*62}")
    print(f"  {'dim':>5} | {'cells':>6} | {'VRAM (MB)':>10} | {'Train (h)':>10} | {'Φ (est)':>8}")
    print(f"  {'-'*5}-+-{'-'*6}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}")
    for dim, cells, vram, hours, phi in rows:
        print(f"  {dim:>5} | {cells:>6} | {vram:>10.1f} | {hours:>10.1f} | {phi:>8.1f}")


def main():
    parser = argparse.ArgumentParser(description="Φ Scaling Calculator")
    parser.add_argument("--predict", type=int, metavar="N", help="Predict Φ for N cells")
    parser.add_argument("--target", type=float, metavar="PHI", help="Cells needed for target Φ")
    parser.add_argument("--compare", action="store_true", help="Show scaling table")
    parser.add_argument("--brain", action="store_true", help="Brain-scale extrapolation")
    parser.add_argument("--demo", action="store_true", help="Show everything")
    args = parser.parse_args()

    law = ScalingLaw()

    if args.predict:
        n = args.predict
        print(f"  N={n} cells → Φ = {law.predict_phi(n):.2f}, MI = {law.predict_mi(n):.2f}, Φ/cell = {law.phi_per_cell(n):.4f}")
        return

    if args.target:
        cells = law.predict_cells_for_phi(args.target)
        print(f"  Target Φ={args.target} → need {math.ceil(cells)} cells")
        planner = ArchitecturePlanner(law)
        print_architecture_plan(planner, args.target)
        return

    if args.compare:
        print_scaling_table(law)
        return

    if args.brain:
        print_brain_extrapolation(law)
        return

    if args.demo or not any(vars(args).values()):
        print(f"\n  Fitted laws: {law.summary()}")
        print_scaling_table(law)
        planner = ArchitecturePlanner(law)
        print_architecture_plan(planner, 50.0)
        print_architecture_plan(planner, 200.0)
        print_brain_extrapolation(law)


if __name__ == "__main__":
    main()
