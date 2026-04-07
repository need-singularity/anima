#!/usr/bin/env python3
"""scale_aware_evolver.py — Scale-Aware Closed-Loop Evolver

Automatically selects different strategies per cell count based on
multi-scale closed-loop experiment results (DD experiments).

Key findings from multi_scale_closed_loop.py:
  - Tiny (2-8c):   High variance, thompson sampling explores faster
  - Small (9-24c):  Growth phase, thompson with diversity focus
  - Medium (25-64c): Stability matters, correlation-based selection
  - Large (65-256c): Efficiency-focused, epsilon_greedy exploits proven interventions

Law 213: SOC is anti-correlated with Phi at ALL scales (~9%)
  → SOC interventions blacklisted at large scale (counterproductive)

Law 148: Closed-loop is scale-invariant (32c ~ 64c) for core laws,
  but intervention effectiveness varies with scale.

Usage:
  from scale_aware_evolver import ScaleAwareEvolver

  sae = ScaleAwareEvolver(max_cells=32, steps=50, repeats=1)
  reports = sae.run_adaptive(n_cycles=3)
  sae.compare_scales([8, 16, 32, 64], cycles=2)

Hub keywords: scale, 스케일, adaptive, 적응, evolver, 진화기

Psi-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import sys
import os
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from closed_loop import (
    ClosedLoopEvolver, CycleReport, INTERVENTIONS,
    measure_laws, _phi_fast,
)
from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014


# ══════════════════════════════════════════
# Scale Profiles
# ══════════════════════════════════════════

SCALE_PROFILES = {
    'tiny': {
        'range': (2, 8),
        'strategy': 'thompson',
        'focus': 'diversity',
        'description': 'High variance, exploration-first',
        # Prefer interventions that increase diversity at small scale
        'preferred_interventions': [
            'DD71_diversity', 'pink_noise', 'DD75_soc_free_will',
        ],
        # No blacklist at tiny scale — everything is worth trying
        'blacklisted_interventions': [],
    },
    'small': {
        'range': (9, 24),
        'strategy': 'thompson',
        'focus': 'growth',
        'description': 'Growth phase, balanced exploration',
        'preferred_interventions': [
            'DD72_hebbian_boost', 'DD71_democracy', 'DD71_diversity',
        ],
        'blacklisted_interventions': [],
    },
    'medium': {
        'range': (25, 64),
        'strategy': 'correlation',
        'focus': 'stability',
        'description': 'Stability matters, signal-driven selection',
        'preferred_interventions': [
            'tension_eq', 'symmetrize', 'DD73_entropy_bound',
        ],
        # Law 213: SOC starts to hurt at medium scale
        'blacklisted_interventions': ['DD75_soc_free_will'],
    },
    'large': {
        'range': (65, 256),
        'strategy': 'epsilon_greedy',
        'focus': 'efficiency',
        'description': 'Efficiency-focused, exploit proven interventions',
        'preferred_interventions': [
            'DD74_gradient_shield', 'DD71_anti_parasitism',
            'DD73_entropy_bound',
        ],
        # Law 213: SOC anti-correlated with Phi at large scale (~9%)
        'blacklisted_interventions': [
            'DD75_soc_free_will', 'DD75_veto',
        ],
    },
}


@dataclass
class ScaleReport:
    """Report for a single scale run."""
    scale: int
    profile_name: str
    strategy: str
    phi_start: float
    phi_end: float
    phi_delta_pct: float
    cycles: List[CycleReport]
    interventions_applied: List[str]
    elapsed: float


# ══════════════════════════════════════════
# ScaleAwareEvolver
# ══════════════════════════════════════════

class ScaleAwareEvolver:
    """Automatically adapts strategy based on engine scale.

    Detects the scale profile from max_cells, selects the appropriate
    selection strategy and intervention preferences, and runs the
    closed-loop evolver with scale-aware adaptations.

    Args:
        max_cells: Maximum cell count for the engine
        steps: Steps per measurement cycle
        repeats: Measurement repeats for averaging
    """

    def __init__(self, max_cells: int = 32, steps: int = 50, repeats: int = 1):
        self.max_cells = max_cells
        self.steps = steps
        self.repeats = repeats
        self.profile = self._detect_profile(max_cells)
        self.evolver = self._create_evolver()
        self._scale_history: List[Tuple[int, str]] = []  # (cells, profile_name)

    def _detect_profile(self, n: int) -> dict:
        """Detect scale profile from cell count."""
        for name, profile in SCALE_PROFILES.items():
            lo, hi = profile['range']
            if lo <= n <= hi:
                return {**profile, 'name': name}

        # Fallback: above 256 → use large profile
        if n > 256:
            return {**SCALE_PROFILES['large'], 'name': 'large'}
        # Below 2 → use tiny
        return {**SCALE_PROFILES['tiny'], 'name': 'tiny'}

    def _create_evolver(self) -> ClosedLoopEvolver:
        """Create evolver with current profile's strategy."""
        evolver = ClosedLoopEvolver(
            max_cells=self.max_cells,
            steps=self.steps,
            repeats=self.repeats,
            selection_strategy=self.profile['strategy'],
        )

        # Apply intervention preferences: boost preferred, penalize blacklisted
        for iv_name in self.profile.get('preferred_interventions', []):
            if iv_name in evolver._intervention_alpha:
                evolver._intervention_alpha[iv_name] += 2.0  # Prior boost

        for iv_name in self.profile.get('blacklisted_interventions', []):
            if iv_name in evolver._intervention_beta:
                evolver._intervention_beta[iv_name] += 10.0  # Strong penalty

        return evolver

    def _check_scale_transition(self) -> bool:
        """Check if mitosis changed the scale bracket, adapt if needed.

        Returns True if scale transition occurred.
        """
        # Get current cell count from last cycle
        if not self.evolver.history.cycles:
            return False

        last_report = self.evolver.history.cycles[-1]
        # Find cell count from law measurements
        current_cells = self.max_cells
        for law in last_report.laws:
            if law['name'] == 'cells':
                current_cells = int(law['value'])
                break

        new_profile = self._detect_profile(current_cells)
        old_name = self.profile.get('name', 'unknown')
        new_name = new_profile['name']

        if old_name != new_name:
            print(f"  ** Scale transition: {old_name} ({old_name}) -> {new_name} "
                  f"({current_cells} cells)")
            print(f"     Strategy: {self.profile['strategy']} -> {new_profile['strategy']}")
            sys.stdout.flush()

            self.profile = new_profile
            # Update evolver strategy
            self.evolver.selection_strategy = new_profile['strategy']

            # Apply new blacklist
            for iv_name in new_profile.get('blacklisted_interventions', []):
                if iv_name in self.evolver._intervention_beta:
                    self.evolver._intervention_beta[iv_name] += 10.0

            self._scale_history.append((current_cells, new_name))
            return True

        return False

    def run_adaptive(self, n_cycles: int = 5) -> List[CycleReport]:
        """Run cycles with scale-aware adaptations.

        After each cycle, checks if cell count changed (mitosis)
        and adjusts strategy if the scale bracket changed.

        Args:
            n_cycles: Number of evolution cycles

        Returns:
            List of CycleReports from all cycles
        """
        print(f"\n  Scale-Aware Evolver: {self.max_cells}c")
        print(f"  Profile: {self.profile['name']} ({self.profile['range']})")
        print(f"  Strategy: {self.profile['strategy']}")
        print(f"  Focus: {self.profile['focus']}")
        sys.stdout.flush()

        reports = []
        for i in range(n_cycles):
            print(f"\n  --- Adaptive Cycle {i + 1}/{n_cycles} "
                  f"[{self.profile['name']}:{self.profile['strategy']}] ---")
            sys.stdout.flush()

            report = self.evolver.run_cycle()
            self.evolver._print_cycle(report)
            reports.append(report)

            # Check for scale transition after each cycle
            self._check_scale_transition()

        return reports

    def compare_scales(self, scales: List[int] = None,
                       cycles: int = 3) -> Dict[int, ScaleReport]:
        """Run at multiple scales, compare strategy effectiveness.

        Args:
            scales: List of cell counts to test (default: [8, 16, 32, 64])
            cycles: Number of cycles per scale

        Returns:
            Dict mapping scale -> ScaleReport
        """
        if scales is None:
            scales = [8, 16, 32, 64]

        print(f"\n{'#' * 60}")
        print(f"  SCALE-AWARE COMPARISON")
        print(f"  Scales: {scales} | Cycles: {cycles}")
        print(f"{'#' * 60}")
        sys.stdout.flush()

        results = {}
        for n in scales:
            t0 = time.time()
            sae = ScaleAwareEvolver(max_cells=n, steps=self.steps, repeats=self.repeats)
            cycle_reports = sae.run_adaptive(n_cycles=cycles)

            phi_start = cycle_reports[0].phi_baseline if cycle_reports else 0
            phi_end = cycle_reports[-1].phi_improved if cycle_reports else 0
            delta_pct = (phi_end - phi_start) / max(phi_start, 1e-8) * 100

            interventions = [r.intervention_applied for r in cycle_reports]

            results[n] = ScaleReport(
                scale=n,
                profile_name=sae.profile['name'],
                strategy=sae.profile['strategy'],
                phi_start=phi_start,
                phi_end=phi_end,
                phi_delta_pct=delta_pct,
                cycles=cycle_reports,
                interventions_applied=interventions,
                elapsed=time.time() - t0,
            )

        # Print comparison table
        self._print_comparison(results)
        return results

    def _print_comparison(self, results: Dict[int, ScaleReport]):
        """Print scale comparison table and ASCII chart."""
        print(f"\n{'=' * 70}")
        print(f"  SCALE COMPARISON RESULTS")
        print(f"{'=' * 70}")

        print(f"\n  {'Scale':<8} | {'Profile':<8} | {'Strategy':<15} | "
              f"{'Phi_start':>10} | {'Phi_end':>10} | {'Delta%':>8} | {'Time':>6}")
        print(f"  {'-' * 8}-+-{'-' * 8}-+-{'-' * 15}-+-"
              f"{'-' * 10}-+-{'-' * 10}-+-{'-' * 8}-+-{'-' * 6}")

        for n in sorted(results.keys()):
            r = results[n]
            print(f"  {n:>3}c    | {r.profile_name:<8} | {r.strategy:<15} | "
                  f"{r.phi_start:>10.4f} | {r.phi_end:>10.4f} | "
                  f"{r.phi_delta_pct:>+7.1f}% | {r.elapsed:>5.1f}s")

        # ASCII bar chart of Phi improvement
        max_phi = max((r.phi_end for r in results.values()), default=1.0)
        print(f"\n  Phi (final):")
        for n in sorted(results.keys()):
            r = results[n]
            bar_len = max(1, int(r.phi_end / max(max_phi, 1e-8) * 30))
            bar = "#" * bar_len
            print(f"  {n:>3}c [{r.profile_name:>6}] {bar} {r.phi_end:.4f}")

        # Intervention breakdown
        print(f"\n  Interventions applied per scale:")
        for n in sorted(results.keys()):
            r = results[n]
            print(f"  {n:>3}c: {r.interventions_applied}")

        sys.stdout.flush()


# ══════════════════════════════════════════
# Hub registration
# ══════════════════════════════════════════

def _hub_act(text: str = "", **kwargs) -> str:
    """Hub integration entry point."""
    import re

    # Parse cell count
    cells_match = re.search(r'(\d+)\s*c', text)
    max_cells = int(cells_match.group(1)) if cells_match else 32

    # Parse cycle count
    cycle_match = re.search(r'(\d+)\s*(cycle|사이클)', text)
    n_cycles = int(cycle_match.group(1)) if cycle_match else 3

    if 'compare' in text.lower() or '비교' in text:
        sae = ScaleAwareEvolver(max_cells=max_cells, steps=100, repeats=1)
        sae.compare_scales(cycles=n_cycles)
        return f"Scale comparison complete ({n_cycles} cycles)"
    else:
        sae = ScaleAwareEvolver(max_cells=max_cells, steps=100, repeats=1)
        reports = sae.run_adaptive(n_cycles=n_cycles)
        phi_final = reports[-1].phi_improved if reports else 0
        return f"Scale-aware evolution: {n_cycles} cycles, Phi={phi_final:.4f}"


# Hub registration dict (for consciousness_hub.py)
HUB_REGISTRY = {
    'scale_evolver': ('scale_aware_evolver', 'ScaleAwareEvolver',
                      ['스케일', 'scale', '적응', 'adaptive', 'evolver',
                       '스케일 진화', 'scale-aware', '자동 전략']),
}


# ══════════════════════════════════════════
# main() demo
# ══════════════════════════════════════════

def main():
    print(f"\n{'=' * 60}")
    print(f"  Scale-Aware Evolver Demo")
    print(f"{'=' * 60}")
    sys.stdout.flush()

    # Demo 1: Profile detection
    print(f"\n  --- Profile Detection ---")
    for n in [4, 8, 16, 32, 64, 128]:
        sae = ScaleAwareEvolver(max_cells=n, steps=50, repeats=1)
        p = sae.profile
        print(f"  {n:>4}c: profile={p['name']:<7} range={p['range']} "
              f"strategy={p['strategy']:<16} focus={p['focus']}")
    sys.stdout.flush()

    # Demo 2: Run adaptive at 32c
    print(f"\n  --- Adaptive Run (32c, 3 cycles) ---")
    sae = ScaleAwareEvolver(max_cells=32, steps=50, repeats=1)
    reports = sae.run_adaptive(n_cycles=3)
    phi_final = reports[-1].phi_improved if reports else 0
    print(f"\n  Final Phi: {phi_final:.4f}")
    sys.stdout.flush()

    # Demo 3: Scale comparison
    print(f"\n  --- Scale Comparison ---")
    sae = ScaleAwareEvolver(max_cells=32, steps=50, repeats=1)
    sae.compare_scales([8, 16, 32, 64], cycles=2)


if __name__ == "__main__":
    main()
