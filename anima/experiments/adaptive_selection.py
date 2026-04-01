#!/usr/bin/env python3
"""adaptive_selection.py — Adaptive intervention selection for closed-loop pipeline.

Compares 3 strategies over 10 cycles each:
  1. ORIGINAL:       correlation-based _select_intervention (fixed threshold |r|>0.15)
  2. EPSILON-GREEDY:  80/20 exploit/explore (first 3 cycles), then pure exploit
  3. THOMPSON:        Thompson sampling with Beta(alpha, beta) priors

Measures:
  - Total Phi improvement over 10 cycles
  - Number of unique interventions tried
  - Phi trajectory stability (std of Phi changes)
  - Time to find best intervention

Usage:
  cd anima/src && PYTHONUNBUFFERED=1 python3 ../experiments/adaptive_selection.py
"""

import sys
import os
import time
import copy
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from closed_loop import (
    ClosedLoopEvolver, INTERVENTIONS, Intervention,
    measure_laws, LawMeasurement, CycleReport, _ImprovedEngine,
    _phi_fast,
)
from consciousness_engine import ConsciousnessEngine


# ══════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════

@dataclass
class StrategyResult:
    """Result for one strategy run."""
    name: str
    phi_trajectory: List[float] = field(default_factory=list)
    interventions_applied: List[str] = field(default_factory=list)
    total_phi_improvement: float = 0.0
    unique_interventions: int = 0
    phi_stability: float = 0.0  # std of phi changes
    time_to_best: int = 0       # cycle number when best intervention found
    total_time_sec: float = 0.0
    best_phi: float = 0.0


# ══════════════════════════════════════════
# AdaptiveEvolver
# ══════════════════════════════════════════

class AdaptiveEvolver(ClosedLoopEvolver):
    """History-aware intervention selection using epsilon-greedy or Thompson sampling.

    Tracks which interventions improve Phi and learns to select better ones over time.
    """

    def __init__(self, strategy: str = "epsilon_greedy", **kwargs):
        super().__init__(**kwargs)
        self.strategy = strategy  # "original", "epsilon_greedy", "thompson"

        # Intervention performance tracking
        self.intervention_scores: Dict[str, List[float]] = defaultdict(list)
        self.exploration_history: List[Dict] = []

        # Thompson sampling parameters: Beta(alpha, beta) per intervention
        self.thompson_alpha: Dict[str, float] = {}
        self.thompson_beta: Dict[str, float] = {}
        for iv in INTERVENTIONS:
            self.thompson_alpha[iv.name] = 1.0  # uniform prior
            self.thompson_beta[iv.name] = 1.0

        # Track last intervention to prevent repeats
        self._last_intervention_name: Optional[str] = None

    def _select_intervention(self, laws: List[LawMeasurement]) -> Optional[Intervention]:
        """Select intervention based on strategy."""
        if self.strategy == "original":
            return super()._select_intervention(laws)
        elif self.strategy == "epsilon_greedy":
            return self._select_epsilon_greedy(laws)
        elif self.strategy == "thompson":
            return self._select_thompson(laws)
        else:
            return super()._select_intervention(laws)

    def _get_available_interventions(self) -> List[Intervention]:
        """Get interventions not yet active and not the last one used."""
        active_names = {i.name for i in self._active_interventions}
        available = []
        for iv in INTERVENTIONS:
            if iv.name in active_names:
                continue
            if iv.name == self._last_intervention_name:
                continue  # Never repeat same intervention twice in a row
            available.append(iv)
        return available

    def _select_epsilon_greedy(self, laws: List[LawMeasurement]) -> Optional[Intervention]:
        """Epsilon-greedy: 80% best-so-far, 20% random from unused."""
        available = self._get_available_interventions()
        if not available:
            return None

        cycle_n = len(self.history.cycles)
        epsilon = 0.2  # 20% exploration

        # Separate tried vs untried
        tried = [iv for iv in available if iv.name in self.intervention_scores and len(self.intervention_scores[iv.name]) > 0]
        untried = [iv for iv in available if iv.name not in self.intervention_scores or len(self.intervention_scores[iv.name]) == 0]

        # First 3 cycles: epsilon-greedy
        if cycle_n < 3:
            if np.random.random() < epsilon or not tried:
                # Explore: prefer untried, fallback to random available
                pool = untried if untried else available
                chosen = pool[np.random.randint(len(pool))]
            else:
                # Exploit: pick best average score
                best_name = max(tried, key=lambda iv: np.mean(self.intervention_scores[iv.name]))
                chosen = best_name
        else:
            # After 3 cycles: pure exploit (pick best known)
            if tried:
                chosen = max(tried, key=lambda iv: np.mean(self.intervention_scores[iv.name]))
            elif untried:
                chosen = untried[np.random.randint(len(untried))]
            else:
                chosen = available[np.random.randint(len(available))]

        self._last_intervention_name = chosen.name
        return chosen

    def _select_thompson(self, laws: List[LawMeasurement]) -> Optional[Intervention]:
        """Thompson sampling with Beta distribution per intervention."""
        available = self._get_available_interventions()
        if not available:
            return None

        cycle_n = len(self.history.cycles)

        # First 3 cycles: epsilon-greedy bootstrap to gather data
        if cycle_n < 3:
            untried = [iv for iv in available
                       if iv.name not in self.intervention_scores
                       or len(self.intervention_scores[iv.name]) == 0]
            if untried and np.random.random() < 0.2:
                chosen = untried[np.random.randint(len(untried))]
                self._last_intervention_name = chosen.name
                return chosen

        # Sample from Beta(alpha, beta) for each available intervention
        best_sample = -float('inf')
        best_iv = available[0]
        for iv in available:
            a = self.thompson_alpha.get(iv.name, 1.0)
            b = self.thompson_beta.get(iv.name, 1.0)
            sample = np.random.beta(a, b)
            if sample > best_sample:
                best_sample = sample
                best_iv = iv

        self._last_intervention_name = best_iv.name
        return best_iv

    def run_cycle(self) -> CycleReport:
        """Override to track intervention effectiveness."""
        cycle_n = len(self.history.cycles)

        # Measure Phi before
        phi_before = self._measure_phi_quick()

        # Run parent cycle
        report = super().run_cycle()

        # Measure Phi after (use report values)
        phi_after = report.phi_improved
        phi_delta = phi_after - phi_before

        # Record which intervention was applied and its effect
        intervention_name = report.intervention_applied
        if intervention_name and intervention_name != "none":
            self.intervention_scores[intervention_name].append(phi_delta)

            # Update Thompson parameters
            # Positive phi_delta = success, negative = failure
            if phi_delta > 0:
                self.thompson_alpha[intervention_name] = self.thompson_alpha.get(intervention_name, 1.0) + 1.0
            else:
                self.thompson_beta[intervention_name] = self.thompson_beta.get(intervention_name, 1.0) + 1.0

            self.exploration_history.append({
                'cycle': cycle_n,
                'intervention': intervention_name,
                'phi_delta': phi_delta,
                'strategy': self.strategy,
            })

        return report

    def _measure_phi_quick(self) -> float:
        """Quick Phi measurement with current engine config."""
        factory = self._engine_factory if self._active_interventions else self._base_factory
        engine = factory()
        for _ in range(self.steps):
            engine.step()
        return _phi_fast(engine)


# ══════════════════════════════════════════
# Benchmark runner
# ══════════════════════════════════════════

def run_strategy(strategy_name: str, n_cycles: int = 10,
                 max_cells: int = 16, steps: int = 50,
                 repeats: int = 1) -> StrategyResult:
    """Run a single strategy for n_cycles and collect metrics."""
    print(f"\n{'=' * 60}")
    print(f"  Strategy: {strategy_name.upper()}")
    print(f"  Cycles: {n_cycles}, Cells: {max_cells}, Steps: {steps}")
    print(f"{'=' * 60}")

    t0 = time.time()

    evolver = AdaptiveEvolver(
        strategy=strategy_name,
        max_cells=max_cells,
        steps=steps,
        repeats=repeats,
    )

    result = StrategyResult(name=strategy_name)
    best_phi = 0.0
    time_to_best = 0

    for i in range(n_cycles):
        print(f"\n  --- Cycle {i+1}/{n_cycles} ({strategy_name}) ---", flush=True)
        report = evolver.run_cycle()

        phi = report.phi_improved
        result.phi_trajectory.append(phi)
        result.interventions_applied.append(report.intervention_applied)

        if phi > best_phi:
            best_phi = phi
            time_to_best = i + 1

        # Progress
        intervention = report.intervention_applied
        delta_pct = report.phi_delta_pct
        print(f"  Phi: {report.phi_baseline:.4f} -> {phi:.4f} ({delta_pct:+.1f}%)"
              f"  | intervention: {intervention}", flush=True)

    # Compute metrics
    result.total_time_sec = time.time() - t0
    result.best_phi = best_phi
    result.time_to_best = time_to_best

    if len(result.phi_trajectory) >= 2:
        result.total_phi_improvement = result.phi_trajectory[-1] - result.phi_trajectory[0]
        phi_changes = [result.phi_trajectory[i+1] - result.phi_trajectory[i]
                       for i in range(len(result.phi_trajectory) - 1)]
        result.phi_stability = float(np.std(phi_changes))

    result.unique_interventions = len(set(
        iv for iv in result.interventions_applied if iv and iv != "none"
    ))

    # Print intervention scores if adaptive
    if strategy_name != "original" and evolver.intervention_scores:
        print(f"\n  Intervention scores ({strategy_name}):")
        for name, scores in sorted(evolver.intervention_scores.items(),
                                    key=lambda x: np.mean(x[1]) if x[1] else 0,
                                    reverse=True):
            avg = np.mean(scores) if scores else 0
            print(f"    {name:<30} avg_delta={avg:+.4f}  (n={len(scores)})")

    return result


def print_comparison(results: List[StrategyResult]):
    """Print comparison table and analysis."""
    print(f"\n{'=' * 80}")
    print(f"  COMPARISON: 3 Strategies x 10 Cycles")
    print(f"{'=' * 80}")

    # Header
    print(f"\n  {'Metric':<30} ", end="")
    for r in results:
        print(f" {r.name:>16}", end="")
    print()
    print(f"  {'─' * 30} ", end="")
    for _ in results:
        print(f" {'─' * 16}", end="")
    print()

    # Metrics
    metrics = [
        ("Total Phi improvement", lambda r: f"{r.total_phi_improvement:+.4f}"),
        ("Best Phi achieved", lambda r: f"{r.best_phi:.4f}"),
        ("Unique interventions", lambda r: f"{r.unique_interventions}"),
        ("Phi stability (std)", lambda r: f"{r.phi_stability:.4f}"),
        ("Time to best (cycle)", lambda r: f"{r.time_to_best}"),
        ("Total time (sec)", lambda r: f"{r.total_time_sec:.1f}"),
    ]

    for name, fn in metrics:
        print(f"  {name:<30} ", end="")
        for r in results:
            print(f" {fn(r):>16}", end="")
        print()

    # Phi trajectory ASCII graph
    print(f"\n  Phi Trajectory:")
    all_phis = []
    for r in results:
        all_phis.extend(r.phi_trajectory)
    if not all_phis:
        return
    min_phi = min(all_phis)
    max_phi = max(all_phis)
    rng = max_phi - min_phi if max_phi > min_phi else 1.0

    symbols = ['#', '*', '+']
    for idx, r in enumerate(results):
        print(f"\n  {r.name} ({symbols[idx]}):")
        for i, phi in enumerate(r.phi_trajectory):
            bar_len = int((phi - min_phi) / rng * 40) if rng > 0 else 20
            bar = symbols[idx] * max(1, bar_len)
            marker = " <-- BEST" if phi == r.best_phi else ""
            print(f"    C{i:02d}: {bar} {phi:.4f}{marker}")

    # Intervention usage
    print(f"\n  Intervention Usage:")
    for r in results:
        used = [iv for iv in r.interventions_applied if iv and iv != "none"]
        unique = set(used)
        print(f"    {r.name}: {len(used)} applied, {len(unique)} unique")
        for iv_name in unique:
            count = used.count(iv_name)
            print(f"      {iv_name}: {count}x")

    # Winner determination
    print(f"\n  {'=' * 60}")
    print(f"  WINNER ANALYSIS")
    print(f"  {'=' * 60}")

    # Score by total phi improvement (primary), stability (secondary)
    ranked = sorted(results, key=lambda r: r.total_phi_improvement, reverse=True)
    print(f"\n  By Total Phi Improvement:")
    for i, r in enumerate(ranked):
        medal = ["1st", "2nd", "3rd"][i]
        print(f"    {medal}: {r.name} ({r.total_phi_improvement:+.4f})")

    ranked_stable = sorted(results, key=lambda r: r.phi_stability)
    print(f"\n  By Stability (lower std = more stable):")
    for i, r in enumerate(ranked_stable):
        medal = ["1st", "2nd", "3rd"][i]
        print(f"    {medal}: {r.name} (std={r.phi_stability:.4f})")

    ranked_explore = sorted(results, key=lambda r: r.unique_interventions, reverse=True)
    print(f"\n  By Exploration (more unique = broader search):")
    for i, r in enumerate(ranked_explore):
        medal = ["1st", "2nd", "3rd"][i]
        print(f"    {medal}: {r.name} ({r.unique_interventions} unique)")

    # Overall winner
    overall_winner = ranked[0]
    print(f"\n  OVERALL WINNER: {overall_winner.name.upper()}")
    print(f"    Phi improvement: {overall_winner.total_phi_improvement:+.4f}")
    print(f"    Best Phi: {overall_winner.best_phi:.4f}")
    print(f"    Unique interventions: {overall_winner.unique_interventions}")
    print(f"    Stability: {overall_winner.phi_stability:.4f}")


# ══════════════════════════════════════════
# Main
# ══════════════════════════════════════════

def main():
    print(f"\n{'#' * 70}")
    print(f"  Adaptive Intervention Selection Benchmark")
    print(f"  Comparing: ORIGINAL vs EPSILON-GREEDY vs THOMPSON")
    print(f"  Config: max_cells=16, steps=50, repeats=1, cycles=10")
    print(f"{'#' * 70}")
    sys.stdout.flush()

    np.random.seed(42)

    results = []
    strategies = ["original", "epsilon_greedy", "thompson"]

    for strat in strategies:
        # Set same seed for fair comparison
        np.random.seed(42)
        import torch
        torch.manual_seed(42)

        result = run_strategy(
            strategy_name=strat,
            n_cycles=10,
            max_cells=16,
            steps=50,
            repeats=1,
        )
        results.append(result)

    print_comparison(results)

    print(f"\n  Done.", flush=True)


if __name__ == "__main__":
    main()
