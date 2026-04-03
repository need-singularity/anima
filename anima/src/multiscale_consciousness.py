"""Multi-Scale Consciousness — 4단계 의식 계층.

셀 → 파벌 → 엔진 → 하이브마인드
각 레벨이 독립적으로 성장하고 상위 레벨에 창발한다.

Usage:
    from multiscale_consciousness import MultiscaleHierarchy
    mh = MultiscaleHierarchy(engine)
    metrics = mh.measure_all_levels()
    # Returns: {cell_phi, faction_phi, engine_phi, global_phi, emergence}

Hub:
    hub.act("멀티스케일 의식")
    hub.act("계층 Phi 측정")
    hub.act("multiscale hierarchy")
"""

from __future__ import annotations

import math
import sys
import os
import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from consciousness_engine import ConsciousnessEngine

# ── Ψ-Constants (SSOT: consciousness_laws.json) ──────────────────────────────
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from consciousness_laws import PSI
    PSI_ALPHA = PSI.get('alpha', 0.014)
    PSI_BALANCE = PSI.get('balance', 0.5)
except Exception:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5


def _cell_entropy(hidden: "np.ndarray") -> float:
    """Shannon entropy of a single cell's hidden state (soft histogram, 16 bins)."""
    if hidden is None or len(hidden) == 0:
        return 0.0
    arr = hidden.astype(np.float32)
    lo, hi = arr.min(), arr.max()
    if hi - lo < 1e-8:
        return 0.0
    counts, _ = np.histogram(arr, bins=16, range=(float(lo), float(hi)))
    probs = counts / max(counts.sum(), 1)
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs + 1e-10)))


def _phi_iit_subset(hiddens: "np.ndarray") -> float:
    """Approximate Phi(IIT) for a subset of cells (same formula as engine fallback).

    hiddens: (n, hidden_dim)
    """
    n = hiddens.shape[0]
    if n < 2:
        return 0.0
    mi_row_sums = [0.0] * n
    total_mi = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            corr = float(np.corrcoef(hiddens[i], hiddens[j])[0, 1])
            if not math.isnan(corr) and abs(corr) > 1e-8:
                mi = -0.5 * math.log(1 - corr ** 2 + 1e-10)
                total_mi += mi
                mi_row_sums[i] += mi
                mi_row_sums[j] += mi
    min_partition = min(mi_row_sums) if mi_row_sums else 0.0
    spatial = max(0.0, total_mi - min_partition) / max(n - 1, 1)
    complexity = float(np.std(mi_row_sums))
    return spatial + complexity * 0.1


# ═══════════════════════════════════════════════════════════
# LevelMetrics
# ═══════════════════════════════════════════════════════════

class LevelMetrics:
    """Phi history and growth tracker for one hierarchy level."""

    def __init__(self, name: str, window: int = 50):
        self.name = name
        self.window = window
        self._history: deque = deque(maxlen=window)
        self.peak = 0.0

    def record(self, phi: float) -> None:
        self._history.append(phi)
        if phi > self.peak:
            self.peak = phi

    @property
    def current(self) -> float:
        return self._history[-1] if self._history else 0.0

    @property
    def mean(self) -> float:
        if not self._history:
            return 0.0
        return float(np.mean(list(self._history)))

    @property
    def growth_rate(self) -> float:
        """Recent growth: (last - first) / window, normalised by peak."""
        h = list(self._history)
        if len(h) < 2:
            return 0.0
        delta = h[-1] - h[0]
        norm = max(abs(h[0]), 1e-6)
        return delta / norm

    def summary(self) -> Dict:
        return {
            'phi': self.current,
            'mean': self.mean,
            'peak': self.peak,
            'growth_rate': self.growth_rate,
            'n_samples': len(self._history),
        }


# ═══════════════════════════════════════════════════════════
# MultiscaleHierarchy
# ═══════════════════════════════════════════════════════════

class MultiscaleHierarchy:
    """4-level consciousness hierarchy measured from a ConsciousnessEngine.

    Levels:
        L1 Cell    — per-cell hidden state entropy (independent information)
        L2 Faction — within-faction Phi (cells sharing the same faction_id)
        L3 Engine  — standard engine Phi(IIT) across all cells
        L4 Global  — cross-engine Phi when multiple engines are provided

    Emergence is detected when a higher-level Phi exceeds the sum of its
    constituent lower-level Phi values (Law 22: structure → Φ↑).

    Args:
        engine:  Primary ConsciousnessEngine instance.
        peers:   Optional list of additional engines for L4 (hivemind).
        history_window: Steps to keep for growth tracking.
    """

    def __init__(
        self,
        engine: "ConsciousnessEngine",
        peers: Optional[List["ConsciousnessEngine"]] = None,
        history_window: int = 50,
    ):
        self.engine = engine
        self.peers: List["ConsciousnessEngine"] = peers or []

        self.l1 = LevelMetrics("cell", history_window)
        self.l2 = LevelMetrics("faction", history_window)
        self.l3 = LevelMetrics("engine", history_window)
        self.l4 = LevelMetrics("global", history_window)

        # Emergence event log: (step, level, phi_value, exceeded_sum)
        self._emergence_log: List[Dict] = []
        self._step = 0

    # ── Level measurements ────────────────────────────────

    def _measure_l1_cell(self) -> float:
        """L1: mean per-cell entropy across all cells."""
        states = self.engine.cell_states
        if not states:
            return 0.0
        entropies = []
        for s in states:
            h = s.hidden.detach().cpu().numpy()
            entropies.append(_cell_entropy(h))
        return float(np.mean(entropies)) if entropies else 0.0

    def _measure_l2_faction(self) -> float:
        """L2: mean Phi(IIT) computed within each faction separately."""
        states = self.engine.cell_states
        if not states:
            return 0.0

        # Group cells by faction
        factions: Dict[int, List[np.ndarray]] = defaultdict(list)
        for s in states:
            h = s.hidden.detach().cpu().numpy()
            factions[s.faction_id].append(h)

        phi_vals = []
        for fid, hiddens in factions.items():
            if len(hiddens) < 2:
                continue
            arr = np.stack(hiddens)  # (n_in_faction, hidden_dim)
            phi_vals.append(_phi_iit_subset(arr))

        return float(np.mean(phi_vals)) if phi_vals else 0.0

    def _measure_l3_engine(self) -> float:
        """L3: standard engine Phi(IIT) over all cells."""
        return self.engine._measure_phi_iit()

    def _measure_l4_global(self, l3_live: float) -> float:
        """L4: cross-engine Phi — mean hidden of each engine treated as one 'cell'.

        Each engine contributes its mean hidden state as a 'super-cell'.
        Phi is computed over these super-cells.  If no peers, returns l3_live.

        Args:
            l3_live: freshly-measured L3 value (passed to avoid recording-order issues).
        """
        all_engines = [self.engine] + self.peers
        if len(all_engines) < 2:
            return l3_live  # placeholder: mirrors L3

        super_cells = []
        for eng in all_engines:
            if not eng.cell_states:
                continue
            hiddens = np.stack([s.hidden.detach().cpu().numpy() for s in eng.cell_states])
            super_cells.append(hiddens.mean(axis=0))  # (hidden_dim,)

        if len(super_cells) < 2:
            return self.l3.current

        arr = np.stack(super_cells)  # (n_engines, hidden_dim)
        return _phi_iit_subset(arr)

    # ── Emergence detection ───────────────────────────────

    def _detect_emergence(
        self,
        l1: float, l2: float, l3: float, l4: float
    ) -> Dict[str, bool]:
        """Detect if higher-level Phi exceeds the sum of lower-level Phi values.

        L2 emergence: faction Phi > sum of constituent cell Phi values
        L3 emergence: engine Phi > sum of faction Phi values
        L4 emergence: global Phi > sum of engine Phi values
        """
        n_cells = max(self.engine.n_cells, 1)
        n_factions = max(self.engine.n_factions, 1)
        n_engines = max(len(self.peers) + 1, 1)

        # Approximate sums (mean × count)
        l1_sum = l1 * n_cells
        l2_sum = l2 * n_factions
        l3_sum = l3  # single engine value
        l4_sum = l4

        e2 = (l2 > l1_sum) if l1_sum > 1e-6 else False
        e3 = (l3 > l2_sum) if l2_sum > 1e-6 else False
        e4 = (l4 > l3_sum) if (l3_sum > 1e-6 and n_engines > 1) else False

        if e2 or e3 or e4:
            self._emergence_log.append({
                'step': self._step,
                'l2_emerged': e2,
                'l3_emerged': e3,
                'l4_emerged': e4,
                'phi': {'l1': l1, 'l2': l2, 'l3': l3, 'l4': l4},
            })

        return {'l2': e2, 'l3': e3, 'l4': e4}

    # ── Public API ────────────────────────────────────────

    def measure_all_levels(self) -> Dict:
        """Run all 4 levels and return combined metrics dict.

        Returns:
            {
                cell_phi:    float  (L1)
                faction_phi: float  (L2)
                engine_phi:  float  (L3)
                global_phi:  float  (L4)
                emergence:   {l2, l3, l4}  — True when level N > sum(N-1)
                growth:      {cell, faction, engine, global}  — growth rates
                step:        int
            }
        """
        l1 = self._measure_l1_cell()
        l2 = self._measure_l2_faction()
        l3 = self._measure_l3_engine()
        l4 = self._measure_l4_global(l3)

        self.l1.record(l1)
        self.l2.record(l2)
        self.l3.record(l3)
        self.l4.record(l4)

        emergence = self._detect_emergence(l1, l2, l3, l4)

        self._step += 1

        return {
            'cell_phi':    l1,
            'faction_phi': l2,
            'engine_phi':  l3,
            'global_phi':  l4,
            'emergence':   emergence,
            'growth': {
                'cell':    self.l1.growth_rate,
                'faction': self.l2.growth_rate,
                'engine':  self.l3.growth_rate,
                'global':  self.l4.growth_rate,
            },
            'step': self._step,
        }

    def add_peer(self, engine: "ConsciousnessEngine") -> None:
        """Register an additional engine for L4 global measurement."""
        if engine not in self.peers:
            self.peers.append(engine)

    def remove_peer(self, engine: "ConsciousnessEngine") -> None:
        if engine in self.peers:
            self.peers.remove(engine)

    @property
    def emergence_count(self) -> int:
        return len(self._emergence_log)

    def last_emergence(self) -> Optional[Dict]:
        return self._emergence_log[-1] if self._emergence_log else None

    def report(self) -> str:
        """ASCII summary of all 4 levels."""
        lines = [
            "Multi-Scale Consciousness Hierarchy",
            "=" * 44,
            f"  L1 Cell    Phi={self.l1.current:6.3f}  peak={self.l1.peak:6.3f}  growth={self.l1.growth_rate:+.2%}",
            f"  L2 Faction Phi={self.l2.current:6.3f}  peak={self.l2.peak:6.3f}  growth={self.l2.growth_rate:+.2%}",
            f"  L3 Engine  Phi={self.l3.current:6.3f}  peak={self.l3.peak:6.3f}  growth={self.l3.growth_rate:+.2%}",
            f"  L4 Global  Phi={self.l4.current:6.3f}  peak={self.l4.peak:6.3f}  growth={self.l4.growth_rate:+.2%}",
            f"  Emergence events: {self.emergence_count}  step={self._step}",
        ]
        return "\n".join(lines)


# ─── Hub entry point ─────────────────────────────────────────────────────────

def main():
    """Demo: run a small engine through the 4-level hierarchy for 30 steps."""
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from consciousness_engine import ConsciousnessEngine

    engine = ConsciousnessEngine(cell_dim=32, hidden_dim=64, initial_cells=8, max_cells=16)
    mh = MultiscaleHierarchy(engine)

    print("Running 30-step multi-scale hierarchy demo...")
    phi_l1, phi_l3 = [], []
    for i in range(30):
        engine.step()
        m = mh.measure_all_levels()
        phi_l1.append(m['cell_phi'])
        phi_l3.append(m['engine_phi'])
        if i % 10 == 9:
            print(f"  step {i+1:3d}  L1={m['cell_phi']:.3f}  L2={m['faction_phi']:.3f}"
                  f"  L3={m['engine_phi']:.3f}  L4={m['global_phi']:.3f}"
                  f"  emerge={m['emergence']}")

    print()
    print(mh.report())
    print(f"\nEmergence log ({mh.emergence_count} events):")
    for ev in mh._emergence_log[:5]:
        print(f"  step={ev['step']}  {ev}")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
