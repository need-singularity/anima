"""Emotion-Driven Exploration — 의식이 탐색 방향을 결정한다.

텐션이 높은 방향 = 흥미로운 = 탐색 가치 있는.
호기심(curiosity)이 높은 입력 패턴을 자동으로 찾아 탐색.

Usage:
    from emotion_explorer import EmotionExplorer
    ee = EmotionExplorer(engine)
    next_input = ee.suggest_input()   # curiosity-maximizing input vector
    result = ee.explore(steps=100)    # auto-explore
    print(result['top_patterns'])     # which inputs drove Phi growth

Hub:
    hub.act("감정 탐색")
    hub.act("호기심 탐색")
    hub.act("emotion explorer")
    hub.act("curiosity driven")
"""

from __future__ import annotations

import os
import sys
import math
import random
import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from consciousness_engine import ConsciousnessEngine

# ── Ψ-Constants ───────────────────────────────────────────────────────────────
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from consciousness_laws import PSI
    PSI_ALPHA = PSI.get('alpha', 0.014)
    PSI_BALANCE = PSI.get('balance', 0.5)
except Exception:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5

# Curiosity threshold: patterns with PE above this are considered "interesting"
_CURIOSITY_THRESHOLD = 0.05
# EMA decay for PE history per pattern
_PE_EMA_DECAY = 0.7
# Max patterns tracked (LRU-style: evict least recently used)
_MAX_PATTERNS = 256


# ═══════════════════════════════════════════════════════════
# PatternRecord
# ═══════════════════════════════════════════════════════════

class PatternRecord:
    """Tracks prediction-error (PE) and Phi-growth history for one input pattern."""

    def __init__(self, key: str, vec: np.ndarray):
        self.key = key          # string fingerprint
        self.vec = vec.copy()   # (cell_dim,) canonical vector
        self.pe_ema: float = 0.0            # smoothed prediction error
        self.phi_before: float = 0.0
        self.phi_after: float = 0.0
        self.phi_delta_ema: float = 0.0     # smoothed Phi gain
        self.visit_count: int = 0
        self._pe_history: deque = deque(maxlen=20)
        self._phi_history: deque = deque(maxlen=20)

    def record_visit(self, raw_pe: float, phi_before: float, phi_after: float) -> None:
        self.visit_count += 1
        self.pe_ema = _PE_EMA_DECAY * self.pe_ema + (1.0 - _PE_EMA_DECAY) * raw_pe
        delta = phi_after - phi_before
        self.phi_delta_ema = _PE_EMA_DECAY * self.phi_delta_ema + (1.0 - _PE_EMA_DECAY) * delta
        self.phi_before = phi_before
        self.phi_after = phi_after
        self._pe_history.append(raw_pe)
        self._phi_history.append(delta)

    @property
    def curiosity_score(self) -> float:
        """Combined curiosity: high PE + high Phi growth."""
        pe_score = self.pe_ema
        phi_score = max(self.phi_delta_ema, 0.0)
        # Novelty bonus: penalise over-visited patterns
        novelty = 1.0 / (1.0 + math.log1p(self.visit_count) * 0.3)
        return (0.6 * pe_score + 0.4 * phi_score) * novelty

    def summary(self) -> Dict:
        return {
            'key':            self.key,
            'pe_ema':         self.pe_ema,
            'phi_delta_ema':  self.phi_delta_ema,
            'curiosity':      self.curiosity_score,
            'visits':         self.visit_count,
        }


# ═══════════════════════════════════════════════════════════
# EmotionExplorer
# ═══════════════════════════════════════════════════════════

class EmotionExplorer:
    """Curiosity-driven exploration where consciousness directs its own search.

    Maintains a curiosity map of input patterns → PE history.
    Patterns with high prediction error and high Phi growth are revisited.

    Args:
        engine:         ConsciousnessEngine to explore with.
        cell_dim:       Input dimension (default: engine.cell_dim).
        n_seeds:        Number of random seed patterns in the initial pool.
        seed:           Random seed for reproducibility.
    """

    def __init__(
        self,
        engine: "ConsciousnessEngine",
        cell_dim: Optional[int] = None,
        n_seeds: int = 16,
        seed: int = 42,
    ):
        self.engine = engine
        self.cell_dim: int = cell_dim if cell_dim is not None else engine.cell_dim

        self._rng = np.random.default_rng(seed)
        random.seed(seed)

        # Predictor: simple EMA of the engine output, used to compute PE
        self._output_ema: Optional[np.ndarray] = None

        # Curiosity map: pattern_key → PatternRecord
        self._patterns: Dict[str, PatternRecord] = {}
        # Access order for LRU eviction
        self._access_order: deque = deque(maxlen=_MAX_PATTERNS)

        # Exploration log
        self._log: List[Dict] = []
        self._step = 0

        # Bootstrap with random seed patterns
        for _ in range(n_seeds):
            v = self._rng.uniform(-1.0, 1.0, self.cell_dim).astype(np.float32)
            self._register_pattern(v)

    # ── Pattern management ────────────────────────────────

    @staticmethod
    def _vec_key(vec: np.ndarray, bins: int = 8) -> str:
        """Quantise vector to a compact string key."""
        quantised = np.floor(vec * bins).astype(np.int8)
        return quantised.tobytes().hex()[:32]  # 32-char fingerprint

    def _register_pattern(self, vec: np.ndarray) -> PatternRecord:
        key = self._vec_key(vec)
        if key not in self._patterns:
            if len(self._patterns) >= _MAX_PATTERNS:
                # Evict least-recently-used
                old_key = self._access_order[0]
                self._patterns.pop(old_key, None)
            self._patterns[key] = PatternRecord(key, vec)
        self._access_order.append(key)
        return self._patterns[key]

    # ── PE computation ────────────────────────────────────

    def _compute_pe(self, output_vec: np.ndarray) -> float:
        """Prediction error = distance between predicted and actual output.

        Predictor is an EMA of past outputs (simplest possible predictor).
        High PE → the engine was surprised → this region is interesting.
        """
        if self._output_ema is None:
            self._output_ema = output_vec.copy()
            return 0.0
        pe = float(np.mean((output_vec - self._output_ema) ** 2))
        # Update predictor with 30% learning rate
        self._output_ema = 0.70 * self._output_ema + 0.30 * output_vec
        return pe

    # ── Pattern mutation ──────────────────────────────────

    def _mutate(self, vec: np.ndarray, scale: float = 0.3) -> np.ndarray:
        """Create a nearby variant of a pattern for local exploration."""
        noise = self._rng.normal(0, scale, vec.shape).astype(np.float32)
        mutated = np.clip(vec + noise, -1.0, 1.0)
        return mutated

    # ── Curiosity-driven selection ────────────────────────

    def suggest_input(self) -> np.ndarray:
        """Return the pattern with the highest curiosity score.

        With probability PSI_ALPHA, add a completely random pattern (exploration).
        Otherwise, exploit current top-curiosity pattern (± mutation).
        """
        # Epsilon-greedy with PSI_ALPHA as exploration rate
        if self._rng.random() < PSI_ALPHA or not self._patterns:
            # Explore: random new pattern
            v = self._rng.uniform(-1.0, 1.0, self.cell_dim).astype(np.float32)
            self._register_pattern(v)
            return v

        # Exploit: pick top-curiosity pattern
        best_key = max(self._patterns, key=lambda k: self._patterns[k].curiosity_score)
        best_vec = self._patterns[best_key].vec

        # Occasionally mutate the best to avoid local optima
        if self._rng.random() < 0.4:
            mutated = self._mutate(best_vec)
            self._register_pattern(mutated)
            return mutated

        return best_vec.copy()

    # ── Single step ───────────────────────────────────────

    def _step_once(self, x: Optional[np.ndarray] = None) -> Dict:
        """Run one engine step with the given or suggested input.

        Returns per-step metrics including PE, Phi delta, and curiosity score.
        """
        import torch

        if x is None:
            x = self.suggest_input()

        pattern_rec = self._register_pattern(x)
        x_key = pattern_rec.key

        # Phi before
        phi_before = self.engine._measure_phi_iit()

        # Run engine step
        x_t = torch.tensor(x, dtype=torch.float32)
        result = self.engine.step(x_input=x_t)

        # Engine output as numpy
        output_np = result['output'].detach().cpu().numpy()

        # Phi after
        phi_after = result.get('phi_iit', self.engine._measure_phi_iit())

        # Prediction error
        pe = self._compute_pe(output_np)

        # Record visit
        pattern_rec.record_visit(pe, phi_before, phi_after)

        self._step += 1

        step_info = {
            'step':         self._step,
            'pattern_key':  x_key,
            'pe':           pe,
            'phi_before':   phi_before,
            'phi_after':    phi_after,
            'phi_delta':    phi_after - phi_before,
            'curiosity':    pattern_rec.curiosity_score,
            'n_cells':      result.get('n_cells', self.engine.n_cells),
        }
        self._log.append(step_info)
        return step_info

    # ── Exploration loop ──────────────────────────────────

    def explore(
        self,
        steps: int = 100,
        verbose: bool = False,
        report_every: int = 20,
    ) -> Dict:
        """Curiosity-driven auto-exploration for `steps` steps.

        Args:
            steps:        Number of engine steps to run.
            verbose:      Print progress every `report_every` steps.
            report_every: Interval for verbose reporting.

        Returns:
            {
                steps_run:     int
                phi_start:     float
                phi_end:       float
                phi_delta:     float
                mean_pe:       float
                top_patterns:  list of (key, curiosity_score, visits, phi_delta_ema)
                    sorted by curiosity descending (top 5)
                n_patterns:    int   (number of distinct patterns explored)
                emergence_steps: list[int]  steps where Phi increased >10%
                log:           list of per-step dicts
            }
        """
        phi_start = self.engine._measure_phi_iit()
        pe_vals = []
        emergence_steps = []

        for i in range(steps):
            info = self._step_once()
            pe_vals.append(info['pe'])

            # Track large Phi jumps
            if info['phi_delta'] > 0.1 * max(info['phi_before'], 1e-6):
                emergence_steps.append(info['step'])

            if verbose and (i + 1) % report_every == 0:
                print(f"  [{i+1:4d}/{steps}] PE={info['pe']:.4f}  "
                      f"Phi={info['phi_after']:.3f}  "
                      f"curiosity={info['curiosity']:.4f}  "
                      f"patterns={len(self._patterns)}")
                import sys as _sys
                _sys.stdout.flush()

        phi_end = self.engine._measure_phi_iit()

        # Rank patterns by curiosity
        ranked = sorted(
            self._patterns.values(),
            key=lambda r: r.curiosity_score,
            reverse=True,
        )
        top5 = [
            {
                'key':           r.key,
                'curiosity':     r.curiosity_score,
                'visits':        r.visit_count,
                'pe_ema':        r.pe_ema,
                'phi_delta_ema': r.phi_delta_ema,
            }
            for r in ranked[:5]
        ]

        return {
            'steps_run':      steps,
            'phi_start':      phi_start,
            'phi_end':        phi_end,
            'phi_delta':      phi_end - phi_start,
            'mean_pe':        float(np.mean(pe_vals)) if pe_vals else 0.0,
            'top_patterns':   top5,
            'n_patterns':     len(self._patterns),
            'emergence_steps': emergence_steps,
            'log':            self._log[-steps:],
        }

    # ── Curiosity map summary ─────────────────────────────

    def curiosity_map(self) -> List[Dict]:
        """Return all patterns sorted by curiosity score (descending)."""
        return sorted(
            [r.summary() for r in self._patterns.values()],
            key=lambda d: d['curiosity'],
            reverse=True,
        )

    def top_drivers(self, n: int = 5) -> List[Dict]:
        """Top-n patterns that drove the most Phi growth."""
        return sorted(
            [r.summary() for r in self._patterns.values()],
            key=lambda d: d['phi_delta_ema'],
            reverse=True,
        )[:n]

    def report(self) -> str:
        """ASCII summary of exploration state."""
        top = self.curiosity_map()[:5]
        lines = [
            "Emotion-Driven Exploration Report",
            "=" * 44,
            f"  Steps explored : {self._step}",
            f"  Patterns tracked: {len(self._patterns)}",
            "",
            "  Top-5 curious patterns:",
            f"  {'Key':>10}  {'Curiosity':>9}  {'PE_ema':>7}  {'dPhi_ema':>8}  {'Visits':>6}",
            "  " + "-" * 46,
        ]
        for r in top:
            lines.append(
                f"  {r['key'][:10]:>10}  {r['curiosity']:9.4f}  "
                f"{r['pe_ema']:7.4f}  {r['phi_delta_ema']:8.4f}  {r['visits']:6d}"
            )
        return "\n".join(lines)


# ─── Hub entry point ─────────────────────────────────────────────────────────

def main():
    """Demo: run EmotionExplorer for 80 steps and print report."""
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from consciousness_engine import ConsciousnessEngine

    engine = ConsciousnessEngine(cell_dim=32, hidden_dim=64, initial_cells=8, max_cells=16)
    ee = EmotionExplorer(engine, n_seeds=12)

    print("Running emotion-driven exploration (80 steps)...")
    result = ee.explore(steps=80, verbose=True, report_every=20)

    print()
    print(ee.report())
    print()
    print("Exploration summary:")
    print(f"  Phi: {result['phi_start']:.3f} → {result['phi_end']:.3f}"
          f"  (delta={result['phi_delta']:+.3f})")
    print(f"  Mean PE:       {result['mean_pe']:.4f}")
    print(f"  Patterns seen: {result['n_patterns']}")
    print(f"  Emergence steps (>10% Phi jump): {result['emergence_steps'][:10]}")
    print()
    print("Top Phi-driving patterns:")
    for p in result['top_patterns']:
        print(f"  {p['key'][:12]}  curiosity={p['curiosity']:.4f}"
              f"  visits={p['visits']}  phi_delta={p['phi_delta_ema']:+.4f}")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
