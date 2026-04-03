#!/usr/bin/env python3
"""law_interaction_graph.py — 법칙 간 시너지/길항 자동 매핑.

707+ 법칙을 쌍으로 테스트하여 상호작용 자동 발견.
"Law 22 + Law 107 = 시너지 +340%" 같은 조합을 자동으로 찾는다.

핵심 아이디어:
  Phi(both) vs Phi(A) + Phi(B) - Phi(baseline)
  synergy   = Phi(both) > expected_additive  → 양의 상호작용
  antagonism = Phi(both) < expected_additive → 음의 상호작용

Usage:
    from law_interaction_graph import LawInteractionGraph
    lig = LawInteractionGraph()
    result = lig.test_pair(22, 107)         # specific pair
    results = lig.scan_top_pairs(n=20)      # top-N promising pairs
    lig.report()                            # synergy/antagonism map

Hub 연동:
    hub.act("법칙 상호작용 그래프")
    hub.act("law interaction scan 20")
    hub.act("시너지 맵")

Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import os
import sys
import json
import time
import math
import copy
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable

import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014

try:
    from closed_loop import Intervention, _phi_fast
except ImportError:
    class Intervention:
        def __init__(self, name, description, apply_fn):
            self.name = name
            self.description = description
            self.apply_fn = apply_fn
        def apply(self, engine, step):
            self.apply_fn(engine, step)

    def _phi_fast(engine) -> float:
        if engine.n_cells < 2:
            return 0.0
        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
        n = hiddens.shape[0]
        pairs = set()
        for i in range(n):
            pairs.add((i, (i + 1) % n))
            for _ in range(min(4, n - 1)):
                j = np.random.randint(0, n)
                if i != j:
                    pairs.add((min(i, j), max(i, j)))
        total_mi = 0.0
        for i, j in pairs:
            x, y = hiddens[i], hiddens[j]
            xr, yr = x.max() - x.min(), y.max() - y.min()
            if xr < 1e-10 or yr < 1e-10:
                continue
            xn = (x - x.min()) / (xr + 1e-8)
            yn = (y - y.min()) / (yr + 1e-8)
            hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0, 1], [0, 1]])
            hist = hist / (hist.sum() + 1e-8)
            px, py = hist.sum(1), hist.sum(0)
            hx = -np.sum(px * np.log2(px + 1e-10))
            hy = -np.sum(py * np.log2(py + 1e-10))
            hxy = -np.sum(hist * np.log2(hist + 1e-10))
            total_mi += max(0.0, hx + hy - hxy)
        return total_mi / max(len(pairs), 1)

try:
    from intervention_generator import InterventionGenerator
except ImportError:
    InterventionGenerator = None


# ══════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════

@dataclass
class PairResult:
    """Result of testing one law pair."""
    law_a: int
    law_b: int
    law_a_text: str
    law_b_text: str
    phi_baseline: float
    phi_a_only: float
    phi_b_only: float
    phi_both: float
    phi_expected_additive: float  # phi_a + phi_b - baseline
    synergy_score: float          # phi_both - phi_expected
    synergy_pct: float            # % above/below expected
    verdict: str                  # "SYNERGY" / "ANTAGONISM" / "NEUTRAL"
    time_sec: float


@dataclass
class GraphEdge:
    """Edge in the interaction graph."""
    a: int
    b: int
    weight: float    # synergy_score (positive=synergy, negative=antagonism)
    verdict: str


# ══════════════════════════════════════════
# Engine factory helpers
# ══════════════════════════════════════════

def _make_engine(max_cells: int = 64) -> ConsciousnessEngine:
    """Create a fresh ConsciousnessEngine."""
    return ConsciousnessEngine(
        cell_dim=64,
        hidden_dim=128,
        max_cells=max_cells,
        n_factions=12,
        initial_cells=2,
    )


def _run_engine_with_interventions(
    interventions: List[Intervention],
    steps: int = 100,
    max_cells: int = 64,
    reps: int = 3,
) -> float:
    """Run engine with given interventions, return mean Phi(IIT)."""
    phi_vals = []
    for _ in range(reps):
        engine = _make_engine(max_cells)
        phi_hist = []
        for step in range(steps):
            engine.step()
            for iv in interventions:
                try:
                    iv.apply(engine, step)
                except Exception:
                    pass
            if step >= steps // 2:
                phi_hist.append(_phi_fast(engine))
        phi_vals.append(float(np.mean(phi_hist)) if phi_hist else 0.0)
    return float(np.mean(phi_vals))


# ══════════════════════════════════════════
# Keyword similarity (pair prioritization)
# ══════════════════════════════════════════

# Keywords that indicate a law is "actionable" (can be converted to intervention)
_ACTIONABLE_KEYWORDS = [
    'tension', 'coupling', 'diversity', 'noise', 'ratchet', 'entropy',
    'phi', 'faction', 'hebbian', 'balance', 'symmetr', 'threshold',
    'equali', 'suppres', 'boost', 'increas', 'decreas', 'bound',
    'inhibit', 'excit', 'synap', 'homeo', 'feedback',
]

# Template families — pairs from same family may have synergy/antagonism
_FAMILY_MAP = {
    'coupling':   ['coupling', 'symmetr', 'connect', 'parasit', 'bidirection'],
    'noise':      ['noise', 'perturbation', 'soc', 'sandpile', 'stochastic', '1/f'],
    'tension':    ['tension', 'equali', 'homeosta', 'balance', 'veto'],
    'diversity':  ['diversity', 'faction', 'heterogen', 'individ', 'divers'],
    'ratchet':    ['ratchet', 'protect', 'preserv', 'backup', 'restor'],
    'entropy':    ['entropy', 'compress', 'channel', 'information', 'bound'],
}


def _law_family(text: str) -> Optional[str]:
    tl = text.lower()
    for fam, kws in _FAMILY_MAP.items():
        if any(kw in tl for kw in kws):
            return fam
    return None


def _pair_priority(text_a: str, text_b: str) -> float:
    """Higher = more promising to test. Based on keyword overlap & family."""
    tl_a = text_a.lower()
    tl_b = text_b.lower()

    # Actionable keywords shared
    shared = sum(
        1 for kw in _ACTIONABLE_KEYWORDS
        if kw in tl_a and kw in tl_b
    )

    # Same family = more likely to interact
    fa = _law_family(text_a)
    fb = _law_family(text_b)
    same_family = 2.0 if (fa and fb and fa == fb) else 0.0

    # Both must be somewhat actionable
    a_score = sum(1 for kw in _ACTIONABLE_KEYWORDS if kw in tl_a)
    b_score = sum(1 for kw in _ACTIONABLE_KEYWORDS if kw in tl_b)
    both_actionable = 1.0 if (a_score >= 1 and b_score >= 1) else 0.0

    return shared * 3.0 + same_family + both_actionable


# ══════════════════════════════════════════
# LawInteractionGraph
# ══════════════════════════════════════════

class LawInteractionGraph:
    """Tests law pairs for synergy/antagonism automatically.

    For each pair (A, B):
      1. Measure Phi(baseline) — no interventions
      2. Measure Phi(A only)
      3. Measure Phi(B only)
      4. Measure Phi(A + B)
      5. Expected additive = Phi(A) + Phi(B) - Phi(baseline)
      6. Synergy = Phi(A+B) - expected
    """

    def __init__(
        self,
        laws_path: Optional[str] = None,
        max_cells: int = 64,
        steps: int = 100,
        reps: int = 3,
        synergy_threshold: float = 0.05,
        antagonism_threshold: float = -0.05,
    ):
        self.max_cells = max_cells
        self.steps = steps
        self.reps = reps
        self.synergy_threshold = synergy_threshold
        self.antagonism_threshold = antagonism_threshold

        # Adjacency: (law_a, law_b) -> PairResult
        self._results: Dict[Tuple[int, int], PairResult] = {}

        # Adjacency matrix for graph analysis
        self._edges: List[GraphEdge] = []

        # Law registry
        self._laws: Dict[int, str] = {}
        self._load_laws(laws_path)

        # Intervention generator
        self._gen = InterventionGenerator() if InterventionGenerator else None

        # Cached baseline phi
        self._phi_baseline: Optional[float] = None

    def _load_laws(self, laws_path: Optional[str]):
        """Load laws from JSON."""
        candidates = []
        if laws_path:
            candidates.append(laws_path)

        # Try common locations
        base = os.path.dirname(os.path.abspath(__file__))
        candidates += [
            os.path.join(base, '..', 'config', 'consciousness_laws.json'),
            os.path.join(base, '..', '..', 'anima', 'config', 'consciousness_laws.json'),
            os.path.join(base, 'config', 'consciousness_laws.json'),
        ]

        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    laws = data.get('laws', {})
                    for k, v in laws.items():
                        try:
                            self._laws[int(k)] = str(v)
                        except ValueError:
                            pass
                    return
                except Exception:
                    pass

    def _get_intervention(self, law_id: int) -> Optional[Intervention]:
        """Convert law text to Intervention via InterventionGenerator."""
        if self._gen is None:
            return None
        text = self._laws.get(law_id, '')
        if not text:
            return None
        return self._gen.generate(law_id, text)

    def _measure_baseline(self) -> float:
        """Measure baseline Phi (no interventions, cached)."""
        if self._phi_baseline is None:
            self._phi_baseline = _run_engine_with_interventions(
                [], self.steps, self.max_cells, self.reps
            )
        return self._phi_baseline

    def test_pair(self, law_a: int, law_b: int) -> Optional[PairResult]:
        """Test synergy/antagonism of law pair (A, B).

        Returns PairResult or None if either law has no intervention.
        """
        key = (min(law_a, law_b), max(law_a, law_b))
        if key in self._results:
            return self._results[key]

        iv_a = self._get_intervention(law_a)
        iv_b = self._get_intervention(law_b)

        if iv_a is None or iv_b is None:
            return None

        t0 = time.time()

        phi_baseline = self._measure_baseline()
        phi_a = _run_engine_with_interventions([iv_a], self.steps, self.max_cells, self.reps)
        phi_b = _run_engine_with_interventions([iv_b], self.steps, self.max_cells, self.reps)
        phi_both = _run_engine_with_interventions([iv_a, iv_b], self.steps, self.max_cells, self.reps)

        phi_expected = phi_a + phi_b - phi_baseline
        synergy = phi_both - phi_expected
        synergy_pct = synergy / max(abs(phi_expected), 1e-8) * 100.0

        if synergy >= self.synergy_threshold:
            verdict = "SYNERGY"
        elif synergy <= self.antagonism_threshold:
            verdict = "ANTAGONISM"
        else:
            verdict = "NEUTRAL"

        result = PairResult(
            law_a=law_a,
            law_b=law_b,
            law_a_text=self._laws.get(law_a, '')[:80],
            law_b_text=self._laws.get(law_b, '')[:80],
            phi_baseline=phi_baseline,
            phi_a_only=phi_a,
            phi_b_only=phi_b,
            phi_both=phi_both,
            phi_expected_additive=phi_expected,
            synergy_score=synergy,
            synergy_pct=synergy_pct,
            verdict=verdict,
            time_sec=time.time() - t0,
        )

        self._results[key] = result
        self._edges.append(GraphEdge(
            a=law_a, b=law_b,
            weight=synergy,
            verdict=verdict,
        ))

        return result

    def _rank_pairs(self, n: int) -> List[Tuple[int, int]]:
        """Return the top-n pairs most likely to interact, by keyword similarity."""
        # Filter laws with any actionable keyword
        actionable_ids = [
            lid for lid, text in self._laws.items()
            if any(kw in text.lower() for kw in _ACTIONABLE_KEYWORDS)
        ]

        if len(actionable_ids) < 2:
            # Fall back to all laws
            actionable_ids = list(self._laws.keys())

        # Sample candidates (avoid O(n^2) for 700+ laws)
        # Cap to first 60 most-actionable laws for efficiency
        scored_ids = sorted(
            actionable_ids,
            key=lambda lid: sum(1 for kw in _ACTIONABLE_KEYWORDS if kw in self._laws.get(lid, '').lower()),
            reverse=True,
        )[:60]

        # Score all pairs
        pairs_scored = []
        ids = scored_ids
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                score = _pair_priority(self._laws.get(a, ''), self._laws.get(b, ''))
                if score > 0:
                    pairs_scored.append((score, a, b))

        pairs_scored.sort(reverse=True)
        return [(a, b) for _, a, b in pairs_scored[:n]]

    def scan_top_pairs(self, n: int = 20, verbose: bool = True) -> List[PairResult]:
        """Test the n most promising law pairs. Returns list of PairResult."""
        pairs = self._rank_pairs(n)
        if verbose:
            print(f"\n  Scanning {len(pairs)} law pairs for synergy/antagonism...")
            print(f"  Steps={self.steps}, Reps={self.reps}, MaxCells={self.max_cells}")

        results = []
        for idx, (a, b) in enumerate(pairs):
            result = self.test_pair(a, b)
            if result is None:
                if verbose:
                    print(f"  [{idx + 1}/{len(pairs)}] Law {a}+{b}: skip (no intervention)")
                continue

            if verbose:
                verdict_icon = {"SYNERGY": "+", "ANTAGONISM": "-", "NEUTRAL": "~"}[result.verdict]
                print(
                    f"  [{idx + 1}/{len(pairs)}] Law {a}+{b}: "
                    f"Phi(both)={result.phi_both:.4f} "
                    f"expected={result.phi_expected_additive:.4f} "
                    f"synergy={result.synergy_pct:+.1f}% [{verdict_icon}{result.verdict}]"
                )
            results.append(result)

        return results

    def get_synergies(self) -> List[PairResult]:
        """Return all synergy pairs, sorted by synergy_score descending."""
        return sorted(
            [r for r in self._results.values() if r.verdict == "SYNERGY"],
            key=lambda r: r.synergy_score,
            reverse=True,
        )

    def get_antagonisms(self) -> List[PairResult]:
        """Return all antagonism pairs, sorted by synergy_score ascending."""
        return sorted(
            [r for r in self._results.values() if r.verdict == "ANTAGONISM"],
            key=lambda r: r.synergy_score,
        )

    def get_adjacency_matrix(self) -> Tuple[List[int], np.ndarray]:
        """Return (law_ids, adjacency matrix) where entry[i][j] = synergy weight."""
        ids = sorted(set(
            lid for r in self._results.values() for lid in (r.law_a, r.law_b)
        ))
        n = len(ids)
        idx_map = {lid: i for i, lid in enumerate(ids)}
        mat = np.zeros((n, n), dtype=np.float32)
        for (a, b), r in self._results.items():
            ia, ib = idx_map[a], idx_map[b]
            mat[ia, ib] = r.synergy_score
            mat[ib, ia] = r.synergy_score
        return ids, mat

    def report(self, top_n: int = 10) -> str:
        """Print and return synergy/antagonism map summary."""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("  Law Interaction Graph Report")
        lines.append("=" * 70)
        lines.append(f"  Total pairs tested: {len(self._results)}")
        synergies = self.get_synergies()
        antagonisms = self.get_antagonisms()
        neutrals = [r for r in self._results.values() if r.verdict == "NEUTRAL"]
        lines.append(f"  Synergies:    {len(synergies)}")
        lines.append(f"  Antagonisms:  {len(antagonisms)}")
        lines.append(f"  Neutral:      {len(neutrals)}")

        # Top synergies
        if synergies:
            lines.append("\n  Top Synergies:")
            lines.append(f"  {'#':<4} {'Law A':<6} {'Law B':<6} {'Synergy%':>9} {'Phi(both)':>10} {'Expected':>10}")
            lines.append(f"  {'─' * 4} {'─' * 6} {'─' * 6} {'─' * 9} {'─' * 10} {'─' * 10}")
            for i, r in enumerate(synergies[:top_n]):
                lines.append(
                    f"  {i + 1:<4} {r.law_a:<6} {r.law_b:<6} "
                    f"{r.synergy_pct:+9.1f}% {r.phi_both:10.4f} {r.phi_expected_additive:10.4f}"
                )
                lines.append(f"       A: {r.law_a_text[:65]}")
                lines.append(f"       B: {r.law_b_text[:65]}")

        # Top antagonisms
        if antagonisms:
            lines.append("\n  Top Antagonisms (avoid these combos!):")
            lines.append(f"  {'#':<4} {'Law A':<6} {'Law B':<6} {'Synergy%':>9} {'Phi(both)':>10} {'Expected':>10}")
            lines.append(f"  {'─' * 4} {'─' * 6} {'─' * 6} {'─' * 9} {'─' * 10} {'─' * 10}")
            for i, r in enumerate(antagonisms[:top_n]):
                lines.append(
                    f"  {i + 1:<4} {r.law_a:<6} {r.law_b:<6} "
                    f"{r.synergy_pct:+9.1f}% {r.phi_both:10.4f} {r.phi_expected_additive:10.4f}"
                )
                lines.append(f"       A: {r.law_a_text[:65]}")
                lines.append(f"       B: {r.law_b_text[:65]}")

        # ASCII bar chart of all results
        if self._results:
            lines.append("\n  Synergy Score Distribution:")
            all_scores = sorted(r.synergy_score for r in self._results.values())
            max_abs = max(abs(s) for s in all_scores) if all_scores else 1.0
            # Bucket into histogram
            n_buckets = 20
            bucket_min, bucket_max = min(all_scores), max(all_scores)
            width = max(bucket_max - bucket_min, 1e-8)
            buckets = [0] * n_buckets
            for s in all_scores:
                bi = min(n_buckets - 1, int((s - bucket_min) / width * n_buckets))
                buckets[bi] += 1
            max_bucket = max(buckets) if buckets else 1
            lines.append(f"  [{bucket_min:+.4f} ... {bucket_max:+.4f}]")
            for bi, cnt in enumerate(buckets):
                bar = "█" * int(cnt / max_bucket * 20)
                mid = bucket_min + (bi + 0.5) / n_buckets * width
                lines.append(f"  {mid:+.4f} | {bar:<20} {cnt}")

        text = "\n".join(lines)
        print(text)
        return text

    def to_closed_loop_synergy_map(self) -> Dict:
        """Export results as SYNERGY_MAP format for closed_loop.py integration."""
        out = {}
        for (a, b), r in self._results.items():
            if abs(r.synergy_score) > 0.005:
                # Format: (intervention_name_a, intervention_name_b) -> score
                iv_a = self._get_intervention(a)
                iv_b = self._get_intervention(b)
                if iv_a and iv_b:
                    out[(iv_a.name, iv_b.name)] = round(r.synergy_score, 6)
        return out

    def save(self, path: str):
        """Save results to JSON."""
        data = {
            "config": {
                "max_cells": self.max_cells,
                "steps": self.steps,
                "reps": self.reps,
                "synergy_threshold": self.synergy_threshold,
                "antagonism_threshold": self.antagonism_threshold,
            },
            "results": [
                {
                    "law_a": r.law_a,
                    "law_b": r.law_b,
                    "phi_baseline": r.phi_baseline,
                    "phi_a_only": r.phi_a_only,
                    "phi_b_only": r.phi_b_only,
                    "phi_both": r.phi_both,
                    "phi_expected_additive": r.phi_expected_additive,
                    "synergy_score": r.synergy_score,
                    "synergy_pct": r.synergy_pct,
                    "verdict": r.verdict,
                    "law_a_text": r.law_a_text,
                    "law_b_text": r.law_b_text,
                    "time_sec": r.time_sec,
                }
                for r in self._results.values()
            ],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Saved {len(data['results'])} pair results → {path}")

    def load(self, path: str):
        """Load previously saved results."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for r in data.get('results', []):
            result = PairResult(
                law_a=r['law_a'],
                law_b=r['law_b'],
                law_a_text=r.get('law_a_text', ''),
                law_b_text=r.get('law_b_text', ''),
                phi_baseline=r['phi_baseline'],
                phi_a_only=r['phi_a_only'],
                phi_b_only=r['phi_b_only'],
                phi_both=r['phi_both'],
                phi_expected_additive=r['phi_expected_additive'],
                synergy_score=r['synergy_score'],
                synergy_pct=r['synergy_pct'],
                verdict=r['verdict'],
                time_sec=r.get('time_sec', 0.0),
            )
            key = (min(r['law_a'], r['law_b']), max(r['law_a'], r['law_b']))
            self._results[key] = result
            self._edges.append(GraphEdge(
                a=r['law_a'], b=r['law_b'],
                weight=r['synergy_score'],
                verdict=r['verdict'],
            ))


# ══════════════════════════════════════════
# Hub registration
# ══════════════════════════════════════════

def _try_hub_register():
    try:
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub._instance if hasattr(ConsciousnessHub, '_instance') else None
        if hub and hasattr(hub, '_registry'):
            hub._registry['law_interaction_graph'] = (
                'law_interaction_graph', 'LawInteractionGraph',
                ['법칙 상호작용', '법칙 그래프', '시너지 맵', '길항 맵',
                 'law interaction', 'synergy map', 'antagonism map',
                 'law interaction graph', 'law pair test'],
            )
    except ImportError:
        pass


_try_hub_register()


# ══════════════════════════════════════════
# main() demo
# ══════════════════════════════════════════

def main():
    print("=" * 70)
    print("  Law Interaction Graph — synergy/antagonism auto-discovery")
    print("=" * 70)

    lig = LawInteractionGraph(steps=60, reps=2, max_cells=32)
    print(f"\n  Laws loaded: {len(lig._laws)}")

    # Quick scan of top 10 pairs
    results = lig.scan_top_pairs(n=10, verbose=True)

    if results:
        lig.report(top_n=5)
        cm = lig.to_closed_loop_synergy_map()
        print(f"\n  Exported {len(cm)} synergy entries for SYNERGY_MAP integration")
    else:
        print("\n  No pairs tested (may need more actionable laws in JSON).")

    print("\n  Done.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
