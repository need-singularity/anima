#!/usr/bin/env python3
"""Dream Efficiency Analyzer -- measure whether dreaming consolidates learning.

Health grades: EFFICIENT / NEUTRAL / WASTEFUL
Usage: python dream_efficiency_analyzer.py --demo [--scenario efficient|mixed|wasteful]
"""

import argparse, random, statistics
from dataclasses import dataclass, field
from typing import Dict, List, Union


@dataclass
class DreamAnalysis:
    total_cycles: int = 0
    total_patterns: int = 0
    type_counts: Dict[str, int] = field(default_factory=dict)
    type_ratios: Dict[str, float] = field(default_factory=dict)
    tension_stability_before: float = 0.0
    tension_stability_after: float = 0.0
    learning_gain: float = 0.0
    avg_gain_per_cycle: float = 0.0
    consolidation_attempted: int = 0
    consolidation_succeeded: int = 0
    consolidation_rate: float = 0.0
    compute_cost: float = 0.0
    dream_roi: float = 0.0
    coherence_before: float = 0.0
    coherence_after: float = 0.0
    coherence_delta: float = 0.0
    health: str = "NEUTRAL"
    recommendations: List[str] = field(default_factory=list)


class DreamEfficiencyAnalyzer:
    """Analyze dream efficiency from DreamEngine instance or stats dicts."""

    EFFICIENT_ROI, WASTEFUL_ROI = 0.5, 0.1
    GOOD_CONSOL, BAD_CONSOL = 0.6, 0.2
    GOOD_STABILITY_GAIN = 0.05

    def analyze(self, source: Union[object, Dict, List[Dict]]) -> DreamAnalysis:
        cycles = self._normalize(source)
        if not cycles:
            a = DreamAnalysis()
            a.recommendations.append("No dream data available yet.")
            return a
        r = DreamAnalysis()
        self._count(cycles, r)
        self._types(cycles, r)
        self._learning(cycles, r)
        self._consolidation(cycles, r)
        self._coherence(cycles, r)
        self._roi(cycles, r)
        self._health(r)
        self._recommend(r)
        return r

    def _normalize(self, src) -> List[Dict]:
        if isinstance(src, list): return src
        if isinstance(src, dict): return [src]
        if hasattr(src, 'get_status') and hasattr(src, 'total_dream_cycles'):
            st = src.get_status()
            return [{'total_cycles': src.total_dream_cycles,
                     'total_patterns': src.total_patterns_learned,
                     'tensions': st.get('dream_tension_history', []),
                     'avg_tension': st.get('avg_dream_tension', 0.0),
                     'dream_cycle_steps': src.dream_cycle_steps,
                     'consolidation_attempted': 0, 'consolidation_succeeded': 0,
                     'consolidation_failed': 0}]
        return []

    def _count(self, cycles, r):
        r.total_cycles = cycles[-1].get('total_cycles', len(cycles))
        r.total_patterns = cycles[-1].get('total_patterns',
            sum(c.get('patterns_learned', 0) for c in cycles))

    def _types(self, cycles, r):
        counts = {k: 0 for k in ('replay', 'interpolate', 'explore', 'consolidate')}
        for c in cycles:
            for k in counts: counts[k] += c.get(f'type_{k}', 0)
        if sum(counts.values()) == 0:
            s = sum(c.get('dream_cycle_steps', 10) for c in cycles)
            counts = {'replay': int(s*.5), 'interpolate': int(s*.3),
                      'explore': int(s*.2), 'consolidate': 0}
        total = sum(counts.values()) or 1
        r.type_counts = counts
        r.type_ratios = {k: v/total for k, v in counts.items()}

    def _learning(self, cycles, r):
        t = [v for c in cycles for v in c.get('tensions', [])]
        if len(t) < 4: return
        mid = len(t) // 2
        sb = statistics.stdev(t[:mid]) if mid > 1 else 0.0
        sa = statistics.stdev(t[mid:]) if len(t)-mid > 1 else 0.0
        r.tension_stability_before, r.tension_stability_after = sb, sa
        r.learning_gain = max(0.0, sb - sa)
        r.avg_gain_per_cycle = r.learning_gain / r.total_cycles if r.total_cycles else 0.0

    def _consolidation(self, cycles, r):
        a = sum(c.get('consolidation_attempted', 0) for c in cycles)
        s = sum(c.get('consolidation_succeeded', 0) for c in cycles)
        r.consolidation_attempted, r.consolidation_succeeded = a, s
        r.consolidation_rate = s / a if a > 0 else 0.0

    def _coherence(self, cycles, r):
        t = [v for c in cycles for v in c.get('tensions', [])]
        if len(t) < 6: return
        n = len(t) // 3
        def smooth(seq):
            if len(seq) < 2: return 1.0
            return 1.0 / (1.0 + statistics.mean(abs(seq[i+1]-seq[i]) for i in range(len(seq)-1)))
        r.coherence_before = smooth(t[:n])
        r.coherence_after = smooth(t[-n:])
        r.coherence_delta = r.coherence_after - r.coherence_before

    def _roi(self, cycles, r):
        r.compute_cost = sum(c.get('dream_cycle_steps', 10) for c in cycles)
        if r.compute_cost > 0:
            r.dream_roi = (r.learning_gain + r.coherence_delta * 0.5) / (r.compute_cost / 100.0)

    def _health(self, r):
        s = 0.0
        if r.dream_roi >= self.EFFICIENT_ROI: s += 2.0
        elif r.dream_roi >= self.WASTEFUL_ROI: s += 1.0
        if r.consolidation_attempted > 0:
            if r.consolidation_rate >= self.GOOD_CONSOL: s += 2.0
            elif r.consolidation_rate >= self.BAD_CONSOL: s += 1.0
        if r.learning_gain >= self.GOOD_STABILITY_GAIN: s += 1.5
        elif r.learning_gain > 0: s += 0.5
        if r.coherence_delta > 0.02: s += 1.0
        r.health = "EFFICIENT" if s >= 4.0 else "NEUTRAL" if s >= 2.0 else "WASTEFUL"

    def _recommend(self, r):
        rc = r.recommendations
        rr = r.type_ratios.get('replay', 0)
        if rr < 0.4:
            rc.append(f"Replay ratio {rr:.0%} is low (ideal 40-60%). Increase for better consolidation.")
        elif rr > 0.6:
            rc.append(f"Replay ratio {rr:.0%} is high. Increase exploration for novel patterns.")
        if r.type_ratios.get('explore', 0) < 0.1:
            rc.append("Exploration ratio is low. Increase explore weight for novelty seeking.")
        if r.consolidation_attempted > 0 and r.consolidation_rate < 0.3:
            rc.append("Low consolidation rate. Reduce consolidation_threshold or increase noise_scale.")
        if r.learning_gain < 0.01 and r.total_cycles > 5:
            rc.append("Minimal stability gain. Increase dream_cycle_steps or reduce noise_scale.")
        if r.coherence_delta < -0.02:
            rc.append("Coherence dropped. Reduce noise_scale to prevent memory corruption.")
        if r.health == "WASTEFUL" and not rc:
            rc.append("Low dream ROI. Reduce dream frequency or cycle_steps.")
        if not rc:
            rc.append("Dream parameters look healthy. No changes needed.")


def format_report(a: DreamAnalysis) -> str:
    lines = ["=" * 56, "  Dream Efficiency Analysis", "=" * 56, "",
             f"  Cycles: {a.total_cycles}   Patterns learned: {a.total_patterns}",
             "", "  -- Dream Type Distribution --"]
    for k, v in sorted(a.type_ratios.items()):
        lines.append(f"    {k:<13} {v:5.1%}  {'#'*int(v*30)}  ({a.type_counts.get(k,0)})")
    lines += ["", "  -- Learning Metrics --",
              f"    Tension stability (early):  {a.tension_stability_before:.4f}",
              f"    Tension stability (late):   {a.tension_stability_after:.4f}",
              f"    Learning gain (std reduce): {a.learning_gain:.4f}",
              f"    Gain per cycle:             {a.avg_gain_per_cycle:.4f}"]
    if a.consolidation_attempted > 0:
        lines += ["", "  -- Consolidation --",
                  f"    Attempted: {a.consolidation_attempted}  "
                  f"Succeeded: {a.consolidation_succeeded}  Rate: {a.consolidation_rate:.1%}"]
    lines += ["", "  -- Memory Coherence --",
              f"    Before: {a.coherence_before:.4f}   After: {a.coherence_after:.4f}   "
              f"Delta: {a.coherence_delta:+.4f}",
              "", "  -- Dream ROI --",
              f"    Compute cost (steps): {a.compute_cost:.0f}",
              f"    Dream ROI:            {a.dream_roi:.3f}",
              "", f"  >>> Health: {a.health} <<<", "", "  -- Recommendations --"]
    for rec in a.recommendations:
        lines.append(f"    * {rec}")
    lines += ["", "=" * 56]
    return "\n".join(lines)


def generate_synthetic_stats(num_cycles=12, scenario="mixed") -> List[Dict]:
    cycles = []
    for i in range(num_cycles):
        steps = 10
        base = 1.0 + random.gauss(0, 0.15)
        decay = 0.85 ** i if scenario != "wasteful" else 1.0
        tensions = [max(0.0, base + random.gauss(0, 0.2 * decay)) for _ in range(steps)]
        att = random.randint(3, 7) if scenario != "wasteful" else random.randint(1, 3)
        if scenario == "efficient":
            suc = int(att * random.uniform(0.6, 0.9))
        elif scenario == "wasteful":
            suc = int(att * random.uniform(0.0, 0.15))
        else:
            suc = int(att * random.uniform(0.3, 0.6))
        cycles.append({
            'patterns_learned': random.randint(5, steps),
            'avg_tension': statistics.mean(tensions), 'tensions': tensions,
            'total_cycles': i + 1, 'total_patterns': (i + 1) * 7,
            'dream_cycle_steps': steps,
            'consolidation_attempted': att, 'consolidation_succeeded': suc,
            'consolidation_failed': att - suc,
        })
    return cycles


def main():
    ap = argparse.ArgumentParser(description="Dream Efficiency Analyzer")
    ap.add_argument("--demo", action="store_true", help="Run with synthetic stats")
    ap.add_argument("--scenario", choices=["efficient", "mixed", "wasteful"], default="mixed")
    ap.add_argument("--cycles", type=int, default=12)
    args = ap.parse_args()
    if args.demo:
        print(f"Generating {args.scenario} scenario, {args.cycles} cycles\n")
        stats = generate_synthetic_stats(args.cycles, args.scenario)
        print(format_report(DreamEfficiencyAnalyzer().analyze(stats)))
    else:
        print("Usage: python dream_efficiency_analyzer.py --demo [--scenario efficient|mixed|wasteful]")


if __name__ == "__main__":
    main()
