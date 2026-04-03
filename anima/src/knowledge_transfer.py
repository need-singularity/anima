#!/usr/bin/env python3
"""knowledge_transfer.py — Cross-loop knowledge transfer

Multiple ClosedLoopEvolvers share what they learn via a KnowledgePool.
Thompson sampling priors, intervention rankings, and scale-specific
knowledge flow between loops so later evolvers get a head start.

Usage:
  from knowledge_transfer import KnowledgePool
  from closed_loop import ClosedLoopEvolver

  pool = KnowledgePool()

  e1 = ClosedLoopEvolver(max_cells=16, steps=50, repeats=1, selection_strategy='thompson')
  e1.run_cycles(3)
  pool.contribute(e1, scale=16)

  e2 = ClosedLoopEvolver(max_cells=32, steps=50, repeats=1, selection_strategy='thompson')
  pool.advise(e2, scale=32)
  e2.run_cycles(3)
  pool.contribute(e2, scale=32)

  pool.get_consensus_ranking()

  # Hub
  hub.act("knowledge transfer")
  hub.act("지식 전이")

Psi-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import json
import os
import time
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014


def _scale_bracket(scale: int) -> str:
    """Bucket scale into brackets for knowledge grouping."""
    if scale <= 16:
        return 'small'
    elif scale <= 64:
        return 'medium'
    elif scale <= 256:
        return 'large'
    else:
        return 'xlarge'


class KnowledgePool:
    """Shared knowledge pool for multiple ClosedLoopEvolvers.

    Aggregates Thompson alpha/beta, phi deltas, and law change patterns
    across evolvers so later runs benefit from earlier discoveries.
    """

    def __init__(self):
        # name -> {alpha_sum, beta_sum, total_phi_delta, n_trials}
        self.intervention_scores: Dict[str, Dict] = {}
        # intervention_name -> {law_name -> [change_pct values]}
        self.law_change_patterns: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        # scale_bracket -> {intervention_name -> {phi_delta_sum, count}}
        self.scale_knowledge: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(lambda: {'phi_delta_sum': 0.0, 'count': 0}))
        # metadata
        self._contributors: List[Dict] = []

    def contribute(self, evolver, scale: int):
        """Extract knowledge from a completed evolver.

        Pulls Thompson alpha/beta, intervention history with phi deltas,
        and law change patterns into the shared pool.

        Args:
            evolver: A ClosedLoopEvolver that has completed run_cycles().
            scale: The cell count (max_cells) used by this evolver.
        """
        bracket = _scale_bracket(scale)

        # 1. Pull Thompson alpha/beta scores
        for name, alpha in evolver._intervention_alpha.items():
            beta = evolver._intervention_beta.get(name, 1.0)
            if name not in self.intervention_scores:
                self.intervention_scores[name] = {
                    'alpha_sum': 0.0,
                    'beta_sum': 0.0,
                    'total_phi_delta': 0.0,
                    'n_trials': 0,
                }
            entry = self.intervention_scores[name]
            # Only add the learned part (subtract the prior of 1.0)
            entry['alpha_sum'] += max(0.0, alpha - 1.0)
            entry['beta_sum'] += max(0.0, beta - 1.0)

        # 2. Pull intervention history + phi deltas from cycle reports
        for report in evolver.history.cycles:
            iv_name = report.intervention_applied
            if iv_name and iv_name != 'none':
                phi_delta = report.phi_improved - report.phi_baseline
                if iv_name in self.intervention_scores:
                    self.intervention_scores[iv_name]['total_phi_delta'] += phi_delta
                    self.intervention_scores[iv_name]['n_trials'] += 1

                # Scale-specific knowledge
                sk = self.scale_knowledge[bracket][iv_name]
                sk['phi_delta_sum'] += phi_delta
                sk['count'] += 1

                # Law change patterns
                for lc in report.laws_changed:
                    self.law_change_patterns[iv_name][lc['name']].append(lc['change_pct'])

        # Record contributor
        self._contributors.append({
            'scale': scale,
            'bracket': bracket,
            'cycles': len(evolver.history.cycles),
            'timestamp': time.time(),
        })

        n_scored = sum(1 for s in self.intervention_scores.values() if s['n_trials'] > 0)
        print(f"  [KnowledgePool] Contributed from scale={scale} ({bracket}), "
              f"{len(evolver.history.cycles)} cycles, {n_scored} interventions scored")

    def advise(self, evolver, scale: int):
        """Inject pool knowledge into a new evolver as Thompson priors.

        Sets the evolver's Thompson alpha/beta from pool averages, giving
        it a head start. Scale-similar knowledge is weighted more heavily.

        Args:
            evolver: A fresh ClosedLoopEvolver before run_cycles().
            scale: The cell count this evolver will use.
        """
        if not self.intervention_scores:
            print("  [KnowledgePool] No knowledge yet, nothing to advise")
            return

        bracket = _scale_bracket(scale)
        advised_count = 0

        for name, scores in self.intervention_scores.items():
            if scores['n_trials'] == 0:
                continue

            # Base prior from global pool
            alpha_prior = 1.0 + scores['alpha_sum'] * PSI_BALANCE
            beta_prior = 1.0 + scores['beta_sum'] * PSI_BALANCE

            # Scale-specific bonus: if we have data from the same bracket, weight it more
            if bracket in self.scale_knowledge and name in self.scale_knowledge[bracket]:
                sk = self.scale_knowledge[bracket][name]
                if sk['count'] > 0:
                    avg_delta = sk['phi_delta_sum'] / sk['count']
                    if avg_delta > 0:
                        alpha_prior += sk['count'] * 0.5
                    else:
                        beta_prior += sk['count'] * 0.5

            evolver._intervention_alpha[name] = alpha_prior
            evolver._intervention_beta[name] = beta_prior
            advised_count += 1

        print(f"  [KnowledgePool] Advised evolver at scale={scale} ({bracket}), "
              f"{advised_count} interventions primed")

    def get_consensus_ranking(self) -> List[Tuple[str, float, int]]:
        """Rank interventions by aggregated success across all contributors.

        Returns:
            List of (name, avg_phi_delta, n_trials) sorted by avg_phi_delta descending.
        """
        ranking = []
        for name, scores in self.intervention_scores.items():
            if scores['n_trials'] > 0:
                avg_delta = scores['total_phi_delta'] / scores['n_trials']
                ranking.append((name, avg_delta, scores['n_trials']))

        ranking.sort(key=lambda x: x[1], reverse=True)

        # Print
        print(f"\n  {'=' * 65}")
        print(f"  Consensus Ranking ({len(ranking)} interventions, "
              f"{len(self._contributors)} contributors)")
        print(f"  {'=' * 65}")
        print(f"  {'#':<4} {'Intervention':<30} {'Avg dPhi':>10} {'Trials':>8}")
        print(f"  {'─' * 4} {'─' * 30} {'─' * 10} {'─' * 8}")
        for i, (name, avg_d, trials) in enumerate(ranking):
            marker = ' *' if avg_d > 0 else ''
            print(f"  {i + 1:<4} {name:<30} {avg_d:>+10.4f} {trials:>8}{marker}")

        # ASCII bar chart
        if ranking:
            max_abs = max(abs(r[1]) for r in ranking) or 1.0
            print(f"\n  {'─' * 65}")
            for name, avg_d, _ in ranking[:10]:
                bar_len = int(abs(avg_d) / max_abs * 20)
                if avg_d > 0:
                    bar = ' ' * 20 + '|' + '+' * bar_len
                else:
                    bar = ' ' * (20 - bar_len) + '-' * bar_len + '|'
                short = name[:18]
                print(f"  {short:>20} {bar} {avg_d:+.4f}")
            print()

        return ranking

    def get_scale_report(self) -> Dict[str, List[Tuple[str, float]]]:
        """Report per-scale-bracket intervention rankings.

        Returns:
            Dict mapping bracket -> [(intervention_name, avg_phi_delta), ...]
        """
        report = {}
        for bracket, interventions in self.scale_knowledge.items():
            entries = []
            for name, data in interventions.items():
                if data['count'] > 0:
                    entries.append((name, data['phi_delta_sum'] / data['count']))
            entries.sort(key=lambda x: x[1], reverse=True)
            report[bracket] = entries
        return report

    def save(self, path: str = 'data/knowledge_pool.json'):
        """Persist pool to JSON."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        data = {
            'intervention_scores': self.intervention_scores,
            'law_change_patterns': {
                iv: {law: vals for law, vals in laws.items()}
                for iv, laws in self.law_change_patterns.items()
            },
            'scale_knowledge': {
                bracket: {name: info for name, info in interventions.items()}
                for bracket, interventions in self.scale_knowledge.items()
            },
            'contributors': self._contributors,
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"  [KnowledgePool] Saved to {path}")

    def load(self, path: str = 'data/knowledge_pool.json'):
        """Load pool from JSON."""
        with open(path, 'r') as f:
            data = json.load(f)

        self.intervention_scores = data.get('intervention_scores', {})

        # Restore law_change_patterns with defaultdict behavior
        raw_lcp = data.get('law_change_patterns', {})
        self.law_change_patterns = defaultdict(lambda: defaultdict(list))
        for iv, laws in raw_lcp.items():
            for law, vals in laws.items():
                self.law_change_patterns[iv][law] = vals

        # Restore scale_knowledge with defaultdict behavior
        raw_sk = data.get('scale_knowledge', {})
        self.scale_knowledge = defaultdict(lambda: defaultdict(lambda: {'phi_delta_sum': 0.0, 'count': 0}))
        for bracket, interventions in raw_sk.items():
            for name, info in interventions.items():
                self.scale_knowledge[bracket][name] = info

        self._contributors = data.get('contributors', [])
        print(f"  [KnowledgePool] Loaded from {path} "
              f"({len(self.intervention_scores)} interventions, "
              f"{len(self._contributors)} contributors)")


# ══════════════════════════════════════════
# Hub registration
# ══════════════════════════════════════════

def register_to_hub():
    """Register KnowledgePool to ConsciousnessHub."""
    try:
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub(lazy_load=True)
        hub._registry['knowledge_transfer'] = (
            'knowledge_transfer', 'KnowledgePool',
            ['지식 전이', 'knowledge transfer', 'cross-loop', '크로스 루프',
             'pool', '공유', 'share', 'advise', 'contribute']
        )
        return hub
    except ImportError:
        return None


# ══════════════════════════════════════════
# main() demo
# ══════════════════════════════════════════

def main():
    from closed_loop import ClosedLoopEvolver

    print(f"\n{'=' * 70}")
    print(f"  Cross-Loop Knowledge Transfer Demo")
    print(f"{'=' * 70}")

    pool = KnowledgePool()

    # Evolver 1: small scale
    print(f"\n  --- Evolver 1 (16 cells) ---")
    e1 = ClosedLoopEvolver(max_cells=16, steps=50, repeats=1, selection_strategy='thompson')
    e1.run_cycles(3)
    pool.contribute(e1, scale=16)
    print(f"  Pool has {len(pool.intervention_scores)} interventions scored")

    # Evolver 2: medium scale, advised by pool
    print(f"\n  --- Evolver 2 (32 cells, advised) ---")
    e2 = ClosedLoopEvolver(max_cells=32, steps=50, repeats=1, selection_strategy='thompson')
    pool.advise(e2, scale=32)
    e2.run_cycles(3)
    pool.contribute(e2, scale=32)

    # Consensus ranking
    pool.get_consensus_ranking()

    # Scale report
    report = pool.get_scale_report()
    for bracket, entries in report.items():
        print(f"  Scale [{bracket}]: top = {entries[0][0] if entries else 'n/a'}")

    # Save/load roundtrip
    pool.save('/tmp/knowledge_pool_demo.json')
    pool2 = KnowledgePool()
    pool2.load('/tmp/knowledge_pool_demo.json')
    print(f"  Roundtrip OK: {len(pool2.intervention_scores)} interventions loaded")

    print(f"\n{'=' * 70}")
    print(f"  Knowledge transfer complete")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
