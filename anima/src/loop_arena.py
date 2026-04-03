#!/usr/bin/env python3
"""loop_arena.py — Loop Competition Arena

Multiple ClosedLoopEvolvers with different strategies compete.
Best strategy survives based on cumulative Phi improvement.

Usage:
  from loop_arena import LoopArena

  arena = LoopArena(max_cells=16, steps=50)
  arena.add_defaults()                    # 5 default competitors
  arena.run_tournament(n_rounds=10)       # 10-round tournament
  arena.get_leaderboard()                 # final standings
  arena.export_best_strategy()            # winner's intervention history

  # Hub
  hub.act("루프 경쟁")
  hub.act("loop arena 10")

Strategies:
  correlation      — correlation-based selection (original)
  thompson         — Thompson sampling (Beta distribution)
  epsilon_greedy   — 80% exploit, 20% explore
  thompson_synergy — Thompson + synergy-aware (Tier 2)
  random           — random intervention selection (baseline)
"""

import time
import copy
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from closed_loop import (
    ClosedLoopEvolver,
    INTERVENTIONS,
    _phi_fast,
    get_synergy_score,
    _has_strong_antagonism,
)
from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import PSI_BALANCE
except ImportError:
    PSI_BALANCE = 0.5


# ══════════════════════════════════════════
# Random strategy evolver
# ══════════════════════════════════════════

class RandomEvolver(ClosedLoopEvolver):
    """ClosedLoopEvolver that picks interventions randomly (baseline)."""

    def __init__(self, **kwargs):
        kwargs['selection_strategy'] = 'correlation'  # base init, overridden below
        super().__init__(**kwargs)

    def _select_correlation(self, laws):
        """Override: random selection instead of correlation."""
        available = self._get_available_interventions()
        if not available:
            return None
        return available[np.random.randint(len(available))]

    def _select_thompson(self, laws):
        return self._select_correlation(laws)

    def _select_epsilon_greedy(self, laws):
        return self._select_correlation(laws)


# ══════════════════════════════════════════
# Thompson + Synergy evolver (Tier 2)
# ══════════════════════════════════════════

class ThompsonSynergyEvolver(ClosedLoopEvolver):
    """Thompson sampling with full synergy awareness.

    Differences from base thompson:
      - Stronger synergy weight (2x instead of 1x)
      - Actively seeks known-good combos
      - Penalizes mild antagonisms (not just strong ones)
    """

    def __init__(self, **kwargs):
        kwargs['selection_strategy'] = 'thompson'
        super().__init__(**kwargs)

    def _select_thompson(self, laws):
        """Enhanced Thompson with stronger synergy weighting."""
        available = self._get_available_interventions()
        if not available:
            return None

        best_sample = -float('inf')
        best_iv = available[0]
        for iv in available:
            if _has_strong_antagonism(self._active_interventions, iv.name):
                continue
            a = self._intervention_alpha.get(iv.name, 1.0)
            b = self._intervention_beta.get(iv.name, 1.0)
            sample = np.random.beta(a, b)
            # Stronger synergy weighting (2x)
            synergy = get_synergy_score(self._active_interventions, iv.name)
            sample *= (1.0 + 2.0 * synergy)
            # Penalize mild antagonisms too
            if synergy < -0.005:
                sample *= 0.5
            if sample > best_sample:
                best_sample = sample
                best_iv = iv

        return best_iv


# ══════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════

@dataclass
class RoundResult:
    """Single round result for one competitor."""
    name: str
    strategy: str
    phi_before: float
    phi_after: float
    phi_delta: float
    intervention: str
    time_sec: float


@dataclass
class TournamentResult:
    """Full tournament results."""
    rounds: List[List[RoundResult]] = field(default_factory=list)
    winner: str = ""
    total_time: float = 0.0


# ══════════════════════════════════════════
# LoopArena
# ══════════════════════════════════════════

class LoopArena:
    """Multiple ClosedLoopEvolvers compete. Best strategy survives."""

    def __init__(self, max_cells: int = 32, steps: int = 50,
                 repeats: int = 1, n_rounds: int = 10):
        self.max_cells = max_cells
        self.steps = steps
        self.repeats = repeats
        self.n_rounds = n_rounds
        self.evolvers: Dict[str, ClosedLoopEvolver] = {}
        self.scores: Dict[str, float] = {}
        self.history: List[List[RoundResult]] = []
        self.result: Optional[TournamentResult] = None

    def add_competitor(self, name: str, strategy: str, **kwargs):
        """Add a competitor with a specific strategy.

        Args:
            name: unique competitor name
            strategy: one of 'correlation', 'thompson', 'epsilon_greedy',
                      'thompson_synergy', 'random'
        """
        common = dict(
            max_cells=self.max_cells,
            steps=self.steps,
            repeats=self.repeats,
            **kwargs,
        )

        if strategy == 'random':
            evolver = RandomEvolver(**common)
        elif strategy == 'thompson_synergy':
            evolver = ThompsonSynergyEvolver(**common)
        else:
            evolver = ClosedLoopEvolver(selection_strategy=strategy, **common)

        self.evolvers[name] = evolver
        self.scores[name] = 0.0
        print(f"  + Added competitor: {name} (strategy={strategy})")

    def add_defaults(self):
        """Add 5 default competitors."""
        self.add_competitor('correlation', 'correlation')
        self.add_competitor('thompson', 'thompson')
        self.add_competitor('epsilon_greedy', 'epsilon_greedy')
        self.add_competitor('thompson_synergy', 'thompson_synergy')
        self.add_competitor('random', 'random')

    def run_tournament(self, n_rounds: int = None):
        """Run all competitors for n_rounds, track scores."""
        if n_rounds is None:
            n_rounds = self.n_rounds

        if not self.evolvers:
            print("  No competitors added! Use add_competitor() or add_defaults().")
            return

        t0 = time.time()
        print(f"\n{'=' * 70}")
        print(f"  LOOP ARENA TOURNAMENT")
        print(f"  {len(self.evolvers)} competitors x {n_rounds} rounds")
        print(f"  cells={self.max_cells}, steps={self.steps}, repeats={self.repeats}")
        print(f"{'=' * 70}")

        for round_n in range(n_rounds):
            print(f"\n  --- Round {round_n + 1}/{n_rounds} ---")
            round_results = []

            for name, evolver in self.evolvers.items():
                rt0 = time.time()
                report = evolver.run_cycle()
                elapsed = time.time() - rt0

                delta = report.phi_improved - report.phi_baseline
                self.scores[name] += delta

                rr = RoundResult(
                    name=name,
                    strategy=evolver.selection_strategy
                        if not isinstance(evolver, (RandomEvolver, ThompsonSynergyEvolver))
                        else ('random' if isinstance(evolver, RandomEvolver) else 'thompson_synergy'),
                    phi_before=report.phi_baseline,
                    phi_after=report.phi_improved,
                    phi_delta=delta,
                    intervention=report.intervention_applied,
                    time_sec=elapsed,
                )
                round_results.append(rr)

                sign = '+' if delta >= 0 else ''
                print(f"    {name:<22} Phi {report.phi_baseline:.4f} -> {report.phi_improved:.4f} "
                      f"({sign}{delta:.4f}) [{report.intervention_applied}] {elapsed:.1f}s")

            self.history.append(round_results)

            # Mini leaderboard
            ranked = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
            leader = ranked[0]
            print(f"  Leader: {leader[0]} (cumul={leader[1]:+.4f})")

        total_time = time.time() - t0
        winner = max(self.scores, key=self.scores.get)
        self.result = TournamentResult(
            rounds=self.history,
            winner=winner,
            total_time=total_time,
        )

        print(f"\n  Tournament complete in {total_time:.1f}s")
        print(f"  Winner: {winner}")

    def get_winner(self) -> str:
        """Return the best-performing strategy name."""
        if not self.scores:
            return ""
        return max(self.scores, key=self.scores.get)

    def get_leaderboard(self):
        """Print formatted leaderboard with scores."""
        if not self.scores:
            print("  No results yet. Run tournament first.")
            return

        print(f"\n{'=' * 70}")
        print(f"  FINAL LEADERBOARD")
        print(f"{'=' * 70}")

        ranked = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        max_abs = max(abs(s) for _, s in ranked) if ranked else 1.0

        # Table
        print(f"  {'Rank':<6} {'Name':<22} {'Strategy':<20} {'Score':>10} {'Interventions':>14}")
        print(f"  {'----':<6} {'----':<22} {'--------':<20} {'-----':>10} {'-------------':>14}")

        for i, (name, score) in enumerate(ranked):
            evolver = self.evolvers[name]
            n_iv = len(evolver._active_interventions)
            strat = evolver.selection_strategy if not isinstance(evolver, (RandomEvolver, ThompsonSynergyEvolver)) \
                else ('random' if isinstance(evolver, RandomEvolver) else 'thompson_synergy')
            medal = ['1st', '2nd', '3rd'][i] if i < 3 else f'{i+1}th'
            print(f"  {medal:<6} {name:<22} {strat:<20} {score:>+10.4f} {n_iv:>14}")

        # ASCII bar chart
        print(f"\n  Score Distribution:")
        for name, score in ranked:
            if max_abs > 1e-8:
                bar_len = int(abs(score) / max_abs * 30)
            else:
                bar_len = 0
            if score >= 0:
                bar = " " * 15 + "|" + "+" * bar_len
            else:
                bar = " " * (15 - bar_len) + "-" * bar_len + "|"
            print(f"  {name:>20} {bar} {score:+.4f}")

        # Per-round evolution
        if self.history:
            print(f"\n  Phi Evolution per Round:")
            names = list(self.evolvers.keys())
            header = f"  {'Round':<8}" + "".join(f"{n:>14}" for n in names)
            print(header)
            print(f"  {'-----':<8}" + "".join(f"{'----------':>14}" for _ in names))
            for r_idx, round_results in enumerate(self.history):
                vals = {rr.name: rr.phi_delta for rr in round_results}
                row = f"  {r_idx + 1:<8}"
                for n in names:
                    v = vals.get(n, 0.0)
                    row += f"{v:>+14.4f}"
                print(row)

        print()

    def export_best_strategy(self) -> Dict:
        """Export the winning evolver's intervention history for reuse."""
        winner = self.get_winner()
        if not winner:
            return {}

        evolver = self.evolvers[winner]
        interventions = [
            {'name': iv.name, 'description': iv.description}
            for iv in evolver._active_interventions
        ]

        result = {
            'winner': winner,
            'strategy': evolver.selection_strategy if not isinstance(evolver, (RandomEvolver, ThompsonSynergyEvolver))
                else ('random' if isinstance(evolver, RandomEvolver) else 'thompson_synergy'),
            'score': self.scores[winner],
            'interventions': interventions,
            'n_rounds': len(self.history),
            'phi_history': [],
        }

        for round_results in self.history:
            for rr in round_results:
                if rr.name == winner:
                    result['phi_history'].append({
                        'phi_before': rr.phi_before,
                        'phi_after': rr.phi_after,
                        'delta': rr.phi_delta,
                        'intervention': rr.intervention,
                    })

        print(f"\n  Best Strategy Export:")
        print(f"    Winner: {winner}")
        print(f"    Strategy: {result['strategy']}")
        print(f"    Score: {result['score']:+.4f}")
        print(f"    Interventions ({len(interventions)}):")
        for iv in interventions:
            print(f"      - {iv['name']}: {iv['description']}")

        return result


# ══════════════════════════════════════════
# Hub registration
# ══════════════════════════════════════════

def _hub_act(text: str):
    """Hub interface: run arena from natural language."""
    import re
    n = 10
    m = re.search(r'(\d+)', text)
    if m:
        n = int(m.group(1))

    arena = LoopArena(max_cells=16, steps=50, repeats=1)
    arena.add_defaults()
    arena.run_tournament(n_rounds=n)
    arena.get_leaderboard()
    return arena.export_best_strategy()


HUB_KEYWORDS = ['loop arena', 'loop competition', 'strategy competition']
HUB_KEYWORDS_KR = ['루프 경쟁', '전략 경쟁', '루프 아레나', '경쟁 대회']


# ══════════════════════════════════════════
# main()
# ══════════════════════════════════════════

def main():
    """Demo: 5 competitors x 10 rounds."""
    print("\n  Loop Arena — 5 Competitors x 10 Rounds")
    print("  " + "=" * 50)

    arena = LoopArena(max_cells=16, steps=50, repeats=1)
    arena.add_defaults()
    arena.run_tournament(n_rounds=10)
    arena.get_leaderboard()
    best = arena.export_best_strategy()

    print(f"\n  Done. Winner: {best.get('winner', 'N/A')}")
    return arena


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
