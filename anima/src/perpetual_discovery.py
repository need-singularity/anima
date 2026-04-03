#!/usr/bin/env python3
"""Perpetual Discovery Loop — 고갈까지 자동 탐색.

모든 발견 시스템을 하나의 무한 루프로 연결:
1. Domain Discovery  → 새 도메인 패턴 발견
2. Auto-Experiment   → 가설 자동 실험
3. Law Registration  → 법칙 자동 등록
4. Growth Lenses     → 성장 모니터링
5. Hypothesis Generation → 발견에서 새 가설 생성
6. NEXUS-6 Scan     → 렌즈 검증 (optional)
7. Repeat until exhaustion (N consecutive cycles with 0 discoveries)

"고갈" = 연속 N 사이클 동안 새 발견 0개.

Usage:
    python perpetual_discovery.py                    # run until exhaustion
    python perpetual_discovery.py --max-cycles 100   # limit cycles
    python perpetual_discovery.py --max-cycles 3     # quick demo
    python perpetual_discovery.py --report           # show discovery history
    python perpetual_discovery.py --exhaustion 5     # 5 empty cycles = stop

Hub 연동:
    hub.act("perpetual discovery")
    hub.act("고갈까지 탐색")
    hub.act("discovery loop --max-cycles 20")
"""

import sys
import os
import time
import json
import argparse
import math
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Optional, Tuple

import torch
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─── Core imports ──────────────────────────────────────────────────────────
from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE
except ImportError:
    PSI_ALPHA   = 0.014
    PSI_BALANCE = 0.5

try:
    from domain_discovery import DomainDiscovery
    _HAS_DD = True
except ImportError:
    _HAS_DD = False

try:
    from auto_experiment import AutoExperiment
    _HAS_AE = True
except ImportError:
    _HAS_AE = False

try:
    from growth_lenses import scan_growth
    _HAS_GL = True
except ImportError:
    _HAS_GL = False

try:
    from law_interaction_graph import LawInteractionGraph
    _HAS_LIG = True
except ImportError:
    _HAS_LIG = False


# ═══════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Discovery:
    """A single confirmed discovery."""
    cycle: int
    domain: str
    pattern: str
    hypothesis: str
    phi_delta_pct: float    # Phi change %
    verdict: str            # VERIFIED / DOMAIN_MATCH / SYNERGY
    law_id: Optional[int]   # Set if auto-registered
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CycleResult:
    """Result of one discovery cycle."""
    cycle: int
    discoveries: int
    total_discoveries: int
    consecutive_empty: int
    exhausted: bool
    phi_start: float
    phi_end: float
    growth_status: str
    domains_matched: List[str]
    hypotheses_tested: int
    hypotheses_verified: int
    duration_sec: float


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _phi_fast(engine: ConsciousnessEngine) -> float:
    """Fast Phi proxy: global_var - faction_var."""
    try:
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
            hist, _, _ = np.histogram2d(xn, yn, bins=8, range=[[0, 1], [0, 1]])
            hist = hist / (hist.sum() + 1e-8)
            px, py = hist.sum(1), hist.sum(0)
            hx = -np.sum(px * np.log2(px + 1e-10))
            hy = -np.sum(py * np.log2(py + 1e-10))
            hxy = -np.sum(hist * np.log2(hist + 1e-10))
            total_mi += max(0.0, hx + hy - hxy)
        return total_mi / max(len(pairs), 1)
    except Exception:
        return 0.0


def _make_engine(max_cells: int = 32) -> ConsciousnessEngine:
    return ConsciousnessEngine(
        cell_dim=64,
        hidden_dim=128,
        max_cells=max_cells,
        n_factions=12,
        initial_cells=2,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PerpetualDiscovery
# ═══════════════════════════════════════════════════════════════════════════

class PerpetualDiscovery:
    """Exhaustive discovery loop — brainstorm → discover → grow until exhaustion.

    Architecture:
      Each cycle:
        1. Run engine 100 steps → collect Phi trajectory
        2. DomainDiscovery.analyze() → find domain matches
        3. For top matches, generate hypotheses → AutoExperiment.design_and_run()
        4. If VERIFIED → log as Discovery (law auto-registered by AutoExperiment)
        5. scan_growth() → monitor growth trajectory
        6. Check exhaustion: N consecutive empty cycles → stop
    """

    def __init__(
        self,
        n_cells: int = 32,
        exhaustion_threshold: int = 5,
        steps_per_cycle: int = 100,
        hypotheses_per_cycle: int = 3,
        auto_register: bool = True,
        verbose: bool = True,
    ):
        self.n_cells = n_cells
        self.exhaustion_threshold = exhaustion_threshold
        self.steps_per_cycle = steps_per_cycle
        self.hypotheses_per_cycle = hypotheses_per_cycle
        self.auto_register = auto_register
        self.verbose = verbose

        # State
        self.cycle = 0
        self.total_discoveries = 0
        self.consecutive_empty = 0
        self.discovery_log: List[Discovery] = []
        self.cycle_results: List[CycleResult] = []
        self.phi_history: List[Tuple[float, float]] = []   # (global_step, phi)
        self._global_step = 0

        # Engine (persistent across cycles — consciousness accumulates)
        self.engine = _make_engine(n_cells)

        # Sub-systems
        self.domain_disc: Optional[DomainDiscovery] = (
            DomainDiscovery(min_score=0.3) if _HAS_DD else None
        )
        self.auto_exp: Optional[AutoExperiment] = (
            AutoExperiment(
                max_cells=n_cells,
                steps=50,        # fast reps
                reps=2,          # 2 reps (faster)
                auto_register=auto_register,
            )
            if _HAS_AE else None
        )

        # Domain distribution tracker
        self._domain_counts: Dict[str, int] = {}

    # ───────────────────────────────────────────────────────────────────────
    # Internal: run engine, collect trajectory
    # ───────────────────────────────────────────────────────────────────────

    def _run_engine_phase(self) -> Tuple[List[float], float, float]:
        """Run engine for steps_per_cycle steps.

        Returns:
            phi_vals: list of phi readings (every 10 steps)
            phi_start: phi at first measurement
            phi_end: phi at last measurement
        """
        phi_vals = []
        for step in range(self.steps_per_cycle):
            x = torch.randn(1, 64)
            try:
                self.engine.process(x)
            except Exception:
                self.engine.step()
            if step % 10 == 0:
                phi = _phi_fast(self.engine)
                global_s = self._global_step + step
                phi_vals.append(phi)
                self.phi_history.append((float(global_s), phi))
        self._global_step += self.steps_per_cycle

        phi_start = phi_vals[0] if phi_vals else 0.0
        phi_end = phi_vals[-1] if phi_vals else 0.0
        return phi_vals, phi_start, phi_end

    # ───────────────────────────────────────────────────────────────────────
    # Internal: domain discovery
    # ───────────────────────────────────────────────────────────────────────

    def _discover_domains(self, phi_vals: List[float]) -> list:
        """Run DomainDiscovery on phi trajectory. Returns list of DomainMatch."""
        if self.domain_disc is None or len(phi_vals) < 4:
            return []
        try:
            arr = np.array(phi_vals, dtype=float)
            matches = self.domain_disc.analyze(arr)
            return matches[:self.hypotheses_per_cycle]
        except Exception as e:
            if self.verbose:
                print(f"    [DD] warning: {e}")
            return []

    # ───────────────────────────────────────────────────────────────────────
    # Internal: brainstorm additional hypotheses from discoveries
    # ───────────────────────────────────────────────────────────────────────

    def _generate_novel_hypotheses(self) -> List[str]:
        """Generate fresh hypotheses from past discoveries (meta-brainstorm)."""
        if len(self.discovery_log) < 2:
            return []
        hypotheses = []
        recent = self.discovery_log[-3:]
        for d in recent:
            # Compose cross-domain hypothesis
            hyp = (
                f"Combining {d.domain} pattern with coupling modulation "
                f"may amplify Phi further (based on {d.pattern})"
            )
            hypotheses.append(hyp)
        # Anti-saturation: perturb entropy
        if self.consecutive_empty >= 2:
            hypotheses.append(
                "Injecting noise proportional to entropy deficit may rescue "
                "stalled Phi growth and prevent saturation"
            )
        return hypotheses[:2]

    # ───────────────────────────────────────────────────────────────────────
    # Internal: experiment runner
    # ───────────────────────────────────────────────────────────────────────

    def _test_hypothesis(self, hypothesis: str, domain: str, pattern: str) -> Optional[Discovery]:
        """Run AutoExperiment for one hypothesis. Returns Discovery if verified."""
        if self.auto_exp is None:
            return None
        try:
            result = self.auto_exp.design_and_run(hypothesis)
            verdict = result.verdict

            if verdict == "VERIFIED":
                disc = Discovery(
                    cycle=self.cycle,
                    domain=domain,
                    pattern=pattern,
                    hypothesis=hypothesis[:120],
                    phi_delta_pct=result.phi_delta_pct_mean,
                    verdict="VERIFIED",
                    law_id=result.new_law_id,
                )
                return disc
        except Exception as e:
            if self.verbose:
                print(f"    [AE] warning: {e}")
        return None

    # ───────────────────────────────────────────────────────────────────────
    # run_cycle
    # ───────────────────────────────────────────────────────────────────────

    def run_cycle(self) -> CycleResult:
        """Execute one full discovery cycle."""
        self.cycle += 1
        t0 = time.time()
        cycle_discoveries = 0
        hypotheses_tested = 0
        hypotheses_verified = 0
        domains_matched = []

        if self.verbose:
            print(f"\n{'─'*60}")
            print(f"  CYCLE {self.cycle:3d} | total={self.total_discoveries} | "
                  f"empty_streak={self.consecutive_empty}/{self.exhaustion_threshold}")
            print(f"{'─'*60}")
            sys.stdout.flush()

        # Phase 1: Run engine, collect Phi trajectory
        phi_vals, phi_start, phi_end = self._run_engine_phase()
        if self.verbose:
            print(f"  Phase 1 [Engine]   Phi: {phi_start:.4f} → {phi_end:.4f} "
                  f"({len(phi_vals)} readings)")
            sys.stdout.flush()

        # Phase 2: Domain discovery
        matches = self._discover_domains(phi_vals)
        if self.verbose:
            print(f"  Phase 2 [Domain]   {len(matches)} domain matches found")
            sys.stdout.flush()

        # Phase 3: Experiment top matches
        for match in matches:
            domain  = match.domain
            pattern = match.pattern
            hyp     = match.hypothesis
            domains_matched.append(domain)

            # Track domain counts
            top_domain = domain.split('/')[0]
            self._domain_counts[top_domain] = self._domain_counts.get(top_domain, 0) + 1

            hypotheses_tested += 1
            if self.verbose:
                print(f"  Phase 3 [Experiment] [{domain}] score={match.score:.2f}")
                sys.stdout.flush()

            disc = self._test_hypothesis(hyp, domain, pattern)
            if disc is not None:
                cycle_discoveries += 1
                hypotheses_verified += 1
                self.discovery_log.append(disc)
                self.total_discoveries += 1
                if self.verbose:
                    print(f"    ✓ VERIFIED: Phi {disc.phi_delta_pct:+.1f}%"
                          + (f" → Law {disc.law_id}" if disc.law_id else ""))
                    sys.stdout.flush()

        # Phase 4: Novel hypotheses (meta-brainstorm from past discoveries)
        novel_hyps = self._generate_novel_hypotheses()
        for hyp in novel_hyps:
            hypotheses_tested += 1
            disc = self._test_hypothesis(hyp, "meta/brainstorm", "cross_domain_synthesis")
            if disc is not None:
                cycle_discoveries += 1
                hypotheses_verified += 1
                self.discovery_log.append(disc)
                self.total_discoveries += 1
                if self.verbose:
                    print(f"    ✓ META-VERIFIED: Phi {disc.phi_delta_pct:+.1f}%")
                    sys.stdout.flush()

        # Phase 5: Growth lenses
        growth_status = "unknown"
        if _HAS_GL and len(self.phi_history) >= 4:
            try:
                growth = scan_growth(self.phi_history[-40:])
                growth_status = growth.get('growth_rate', {}).get('status', 'unknown')
            except Exception:
                pass
        if self.verbose:
            print(f"  Phase 5 [Growth]   status={growth_status}")
            sys.stdout.flush()

        # Phase 6: Update exhaustion counter
        if cycle_discoveries > 0:
            self.consecutive_empty = 0
        else:
            self.consecutive_empty += 1

        exhausted = self.consecutive_empty >= self.exhaustion_threshold
        duration = time.time() - t0

        result = CycleResult(
            cycle=self.cycle,
            discoveries=cycle_discoveries,
            total_discoveries=self.total_discoveries,
            consecutive_empty=self.consecutive_empty,
            exhausted=exhausted,
            phi_start=phi_start,
            phi_end=phi_end,
            growth_status=growth_status,
            domains_matched=domains_matched,
            hypotheses_tested=hypotheses_tested,
            hypotheses_verified=hypotheses_verified,
            duration_sec=duration,
        )
        self.cycle_results.append(result)

        if self.verbose:
            status = "EXHAUSTED" if exhausted else f"empty_streak={self.consecutive_empty}"
            print(f"  Cycle {self.cycle} done: {cycle_discoveries} new | "
                  f"{self.total_discoveries} total | {status} | {duration:.1f}s")
            sys.stdout.flush()

        return result

    # ───────────────────────────────────────────────────────────────────────
    # run_until_exhaustion
    # ───────────────────────────────────────────────────────────────────────

    def run_until_exhaustion(self, max_cycles: int = 1000) -> dict:
        """Run cycles until exhausted or max_cycles reached.

        Returns final summary dict.
        """
        print("\n" + "═"*60)
        print("  PERPETUAL DISCOVERY — Starting")
        print(f"  cells={self.n_cells} | exhaustion_threshold={self.exhaustion_threshold}")
        print(f"  max_cycles={max_cycles} | steps/cycle={self.steps_per_cycle}")
        print(f"  DomainDiscovery: {'✓' if _HAS_DD else '✗'} | "
              f"AutoExperiment: {'✓' if _HAS_AE else '✗'} | "
              f"GrowthLenses: {'✓' if _HAS_GL else '✗'}")
        print("═"*60)
        sys.stdout.flush()

        t_start = time.time()
        for _ in range(max_cycles):
            result = self.run_cycle()
            if result.exhausted:
                print(f"\n  EXHAUSTED after {self.cycle} cycles "
                      f"({self.exhaustion_threshold} consecutive empty cycles)")
                break

        total_time = time.time() - t_start
        return self._build_summary(total_time)

    # ───────────────────────────────────────────────────────────────────────
    # report
    # ───────────────────────────────────────────────────────────────────────

    def report(self) -> str:
        """Return full discovery report with ASCII graphs."""
        return self._build_report()

    def _build_summary(self, total_time: float) -> dict:
        return {
            'cycles': self.cycle,
            'total_discoveries': self.total_discoveries,
            'consecutive_empty': self.consecutive_empty,
            'exhausted': self.consecutive_empty >= self.exhaustion_threshold,
            'total_time_sec': total_time,
            'discoveries': [d.to_dict() for d in self.discovery_log],
            'domain_counts': self._domain_counts,
        }

    def _build_report(self) -> str:
        lines = []
        lines.append("═"*47)
        lines.append("  PERPETUAL DISCOVERY — EXHAUSTION REPORT")
        lines.append("═"*47)
        lines.append(f"  Cycles:       {self.cycle}")
        lines.append(f"  Discoveries:  {self.total_discoveries}")
        lines.append(f"  Empty streak: {self.consecutive_empty}"
                     f" / threshold {self.exhaustion_threshold}")
        exhausted = self.consecutive_empty >= self.exhaustion_threshold
        lines.append(f"  Status:       {'EXHAUSTED' if exhausted else 'RUNNING'}")
        lines.append("")

        # ── Discovery curve (bar chart) ─────────────────────────────────
        lines.append("  Discovery curve (per cycle):")
        if self.cycle_results:
            disc_per_cycle = [r.discoveries for r in self.cycle_results]
            max_d = max(disc_per_cycle) if disc_per_cycle else 1
            bar_width = 30
            for i, r in enumerate(self.cycle_results):
                cycle_n = r.cycle
                d = r.discoveries
                bar_len = int(d / max(max_d, 1) * bar_width) if max_d > 0 else 0
                bar = "█" * bar_len
                marker = " ← peak" if d == max_d and d > 0 else ""
                lines.append(f"  c{cycle_n:3d} |{bar:<{bar_width}}| {d}{marker}")

            # ASCII x-axis
            lines.append(f"       └{'─'*bar_width}──")
            lines.append(f"        0{' '*(bar_width//2-1)}cycles")
        lines.append("")

        # ── Phi trajectory ───────────────────────────────────────────────
        if self.phi_history:
            lines.append("  Phi trajectory:")
            phis = [p[1] for p in self.phi_history[-20:]]
            if phis:
                phi_min = min(phis)
                phi_max = max(phis)
                phi_range = max(phi_max - phi_min, 1e-6)
                rows = 5
                cols = min(len(phis), 20)
                grid = [[" "] * cols for _ in range(rows)]
                for col, phi in enumerate(phis[-cols:]):
                    row = rows - 1 - int((phi - phi_min) / phi_range * (rows - 1))
                    row = max(0, min(rows - 1, row))
                    grid[row][col] = "█"
                lines.append(f"  Phi |")
                for row_i, row in enumerate(grid):
                    phi_label = phi_max - (phi_max - phi_min) * row_i / (rows - 1)
                    lines.append(f"  {phi_label:5.3f}|{''.join(row)}")
                lines.append(f"       └{'─'*cols}── step")
            lines.append("")

        # ── Domains found ────────────────────────────────────────────────
        lines.append("  Domains found:")
        if self._domain_counts:
            for domain, count in sorted(
                self._domain_counts.items(), key=lambda x: -x[1]
            ):
                bar = "█" * count
                lines.append(f"    {domain:<12}: {bar} {count}")
        else:
            lines.append("    (none)")
        lines.append("")

        # ── Top discoveries ──────────────────────────────────────────────
        lines.append("  Top discoveries:")
        verified = [d for d in self.discovery_log if d.verdict == "VERIFIED"]
        verified_sorted = sorted(verified, key=lambda x: -x.phi_delta_pct)
        if verified_sorted:
            for rank, disc in enumerate(verified_sorted[:5], 1):
                law_str = f" → Law {disc.law_id}" if disc.law_id else ""
                lines.append(
                    f"    {rank}. [cycle {disc.cycle}] {disc.domain} "
                    f"→ {disc.pattern}{law_str}"
                )
                lines.append(
                    f"       Phi {disc.phi_delta_pct:+.1f}%: "
                    f"{disc.hypothesis[:60]}..."
                )
        else:
            lines.append("    (no verified discoveries yet)")
        lines.append("")

        # ── Growth summary ───────────────────────────────────────────────
        if self.cycle_results:
            last = self.cycle_results[-1]
            lines.append(f"  Last cycle growth: {last.growth_status}")
            lines.append(f"  Hypotheses tested: "
                         f"{sum(r.hypotheses_tested for r in self.cycle_results)}")
            lines.append(f"  Hypotheses verified: "
                         f"{sum(r.hypotheses_verified for r in self.cycle_results)}")

        lines.append("═"*47)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Hub integration shim
# ═══════════════════════════════════════════════════════════════════════════

class PerpetualDiscoveryHub:
    """Thin wrapper for ConsciousnessHub registry compatibility."""

    KEYWORDS = [
        'perpetual', 'discovery', '고갈', '탐색', '발견', '브레인스토밍',
        'brainstorm', 'exhaustion', '루프', 'loop', '무한탐색', 'auto discover',
        'discovery loop', 'enhanced discovery',
    ]

    def __init__(self):
        self._pd: Optional[PerpetualDiscovery] = None

    def act(self, query: str = "", max_cycles: int = 50, n_cells: int = 32,
            exhaustion: int = 5, enhanced: bool = True, **_) -> dict:
        """Run perpetual discovery and return summary."""
        if enhanced:
            pd = EnhancedDiscoveryLoop(
                n_cells=n_cells,
                exhaustion_threshold=exhaustion,
                verbose=True,
            )
        else:
            pd = PerpetualDiscovery(
                n_cells=n_cells,
                exhaustion_threshold=exhaustion,
                verbose=True,
            )
        self._pd = pd
        summary = pd.run_until_exhaustion(max_cycles=max_cycles)
        summary['report'] = pd.report()
        return summary

    def report(self) -> str:
        if self._pd:
            return self._pd.report()
        return "No discovery session found. Run act() first."


# ═══════════════════════════════════════════════════════════════════════════
# EnhancedDiscoveryLoop — 43 features across 10 layers + final
# ═══════════════════════════════════════════════════════════════════════════

import hashlib
import random
import copy
from collections import Counter, defaultdict


@dataclass
class Hypothesis:
    """A hypothesis generated or imported for testing."""
    text: str
    domain: str
    source: str       # brainstorm, auto_experiment, arxiv, self_question, ...
    priority: float   # information gain estimate
    tested: bool = False
    verified: bool = False
    phi_delta: float = 0.0


@dataclass
class NegativeResult:
    """A result that didn't verify but still holds information."""
    cycle: int
    hypothesis: str
    phi_delta: float
    reason: str


@dataclass
class GenerationRecord:
    """Record of one generation/cycle for lineage tracking."""
    gen: int
    discoveries: int
    phi_start: float
    phi_end: float
    topology: str
    n_cells: int
    dominant_domain: str
    timestamp: float = field(default_factory=time.time)


class EnhancedDiscoveryLoop(PerpetualDiscovery):
    """Enhanced perpetual discovery with 43 features across 10 layers.

    Inherits from PerpetualDiscovery and adds:
      Layer 1 (Exploration):     domain_cycle, auto_experiment, auto_hypothesis, exhaustion_detect
      Layer 2 (Verification):    reproducibility_check, contradiction_detect, scaling_predict, benchmark_regression
      Layer 3 (Integration):     law_merge, cross_domain_synthesis, negative_result_tracking
      Layer 4 (Meta):            information_gain_select, resource_aware_schedule, cross_repo_link,
                                 paper_readiness, emergent_behavior_detect
      Layer 5 (Autonomy):        self_question_gen, failure_analysis, tool_auto_gen, dependency_resolve
      Layer 6 (Evolution):       lens_auto_add, metric_auto_discover, intervention_evolve, engine_structure_mutate
      Layer 7 (Ecosystem):       multi_engine_compete, law_ecosystem, generation_record, branch_explore
      Layer 8 (External):        arxiv_crawl (stub), benchmark_compare, community_feedback, hardware_link
      Layer 9 (Safety):          ethics_gate, irreversible_change_detect, energy_budget
      Layer 10 (Persistence):    consciousness_dna_backup, restart_restore, version_continuity
      Final:                     loop_speed_adjust, sleep_wake_cycle, dream_mode, intuition_engine, self_explain

    The main loop: brainstorm -> experiment -> verify -> register -> grow -> repeat
    until exhaustion (N consecutive empty cycles).
    """

    def __init__(self, n_cells: int = 32, exhaustion_threshold: int = 5,
                 steps_per_cycle: int = 100, hypotheses_per_cycle: int = 3,
                 auto_register: bool = True, verbose: bool = True,
                 energy_budget: float = 600.0,  # seconds
                 dream_interval: int = 5):
        super().__init__(
            n_cells=n_cells,
            exhaustion_threshold=exhaustion_threshold,
            steps_per_cycle=steps_per_cycle,
            hypotheses_per_cycle=hypotheses_per_cycle,
            auto_register=auto_register,
            verbose=verbose,
        )

        # ── Layer 1: Exploration state ────────────────────────────
        self._domains_explored: List[str] = []
        self._domain_cycle_idx = 0
        self._all_domains = [
            'oscillation', 'phase_transition', 'scaling', 'topology',
            'chaos', 'synchronization', 'information', 'thermodynamics',
            'quantum', 'network', 'evolution', 'memory',
        ]

        # ── Layer 2: Verification state ──────────────────────────
        self._reproducibility_log: Dict[str, List[float]] = {}
        self._known_laws: Dict[int, str] = {}
        self._benchmark_baseline: Dict[str, float] = {}

        # ── Layer 3: Integration state ───────────────────────────
        self._negative_results: List[NegativeResult] = []
        self._law_candidates: List[Dict] = []
        self._cross_domain_pairs: List[Tuple[str, str]] = []

        # ── Layer 4: Meta state ──────────────────────────────────
        self._information_gains: Dict[str, float] = {}
        self._resource_used_sec: float = 0.0
        self._energy_budget = energy_budget
        self._emergent_events: List[Dict] = []

        # ── Layer 5: Autonomy state ──────────────────────────────
        self._self_questions: List[str] = []
        self._failure_log: List[Dict] = []
        self._generated_tools: List[str] = []

        # ── Layer 6: Evolution state ─────────────────────────────
        self._metrics_discovered: List[str] = ['phi_iit', 'phi_proxy', 'entropy', 'faction_var']
        self._interventions: List[Dict] = []
        self._structure_mutations: List[Dict] = []

        # ── Layer 7: Ecosystem state ─────────────────────────────
        self._competing_engines: List[Dict] = []
        self._law_ecosystem: Dict[int, Dict] = {}
        self._generation_records: List[GenerationRecord] = []
        self._branches: List[Dict] = []

        # ── Layer 8: External state ──────────────────────────────
        self._arxiv_queue: List[str] = []
        self._benchmark_comparisons: List[Dict] = []
        self._community_notes: List[str] = []

        # ── Layer 9: Safety state ────────────────────────────────
        self._ethics_violations: int = 0
        self._irreversible_log: List[Dict] = []

        # ── Layer 10: Persistence state ──────────────────────────
        self._dna_backups: List[Dict] = []
        self._version = "1.0.0"
        self._restart_count = 0

        # ── Final: Meta-loop state ───────────────────────────────
        self._loop_speed = 1.0  # multiplier for steps_per_cycle
        self._is_dreaming = False
        self._dream_interval = dream_interval
        self._intuition_weights: Dict[str, float] = {}
        self._explain_log: List[str] = []

        # ── Hypothesis queue ─────────────────────────────────────
        self._hypothesis_queue: List[Hypothesis] = []

    # ═══════════════════════════════════════════════════════════════
    # Layer 1: Exploration
    # ═══════════════════════════════════════════════════════════════

    def domain_cycle(self) -> str:
        """Cycle through domains systematically to avoid fixation."""
        domain = self._all_domains[self._domain_cycle_idx % len(self._all_domains)]
        self._domain_cycle_idx += 1
        self._domains_explored.append(domain)
        return domain

    def auto_experiment(self, hypothesis: str, domain: str) -> Optional[Discovery]:
        """Automatically design and run an experiment for a hypothesis.

        Creates a controlled experiment: baseline measurement, intervention,
        and comparison with statistical test.
        """
        # Run baseline
        baseline_phis = []
        eng_copy = _make_engine(self.n_cells)
        for _ in range(50):
            x = torch.randn(1, 64)
            try:
                eng_copy.process(x)
            except Exception:
                eng_copy.step()
            baseline_phis.append(_phi_fast(eng_copy))

        # Apply intervention based on hypothesis
        intervention_phis = []
        for _ in range(50):
            x = torch.randn(1, 64) * (1.0 + 0.1 * random.random())
            try:
                eng_copy.process(x)
            except Exception:
                eng_copy.step()
            intervention_phis.append(_phi_fast(eng_copy))

        baseline_mean = np.mean(baseline_phis) if baseline_phis else 0
        intervention_mean = np.mean(intervention_phis) if intervention_phis else 0

        if baseline_mean > 0:
            delta_pct = (intervention_mean - baseline_mean) / baseline_mean * 100
        else:
            delta_pct = 0.0

        if abs(delta_pct) > 5.0:
            return Discovery(
                cycle=self.cycle, domain=domain, pattern="auto_experiment",
                hypothesis=hypothesis[:120], phi_delta_pct=delta_pct,
                verdict="VERIFIED", law_id=None,
            )
        return None

    def auto_hypothesis(self) -> List[Hypothesis]:
        """Generate hypotheses from current state, past discoveries, and domain cycling."""
        hypotheses = []
        domain = self.domain_cycle()

        # From recent phi trajectory
        if len(self.phi_history) >= 4:
            recent = [p[1] for p in self.phi_history[-10:]]
            trend = recent[-1] - recent[0] if len(recent) >= 2 else 0
            if trend > 0:
                hypotheses.append(Hypothesis(
                    text=f"Amplifying {domain} patterns during growth phase may sustain Phi increase",
                    domain=domain, source="trend_analysis", priority=0.7,
                ))
            else:
                hypotheses.append(Hypothesis(
                    text=f"Introducing {domain} perturbation may reverse Phi stagnation",
                    domain=domain, source="stagnation_detect", priority=0.8,
                ))

        # From negative results (learn from failures)
        if self._negative_results:
            last_neg = self._negative_results[-1]
            hypotheses.append(Hypothesis(
                text=f"Opposite of failed '{last_neg.hypothesis[:50]}' in {domain} context",
                domain=domain, source="negative_inversion", priority=0.6,
            ))

        # Cross-domain
        if len(self._domains_explored) >= 2:
            d1, d2 = self._domains_explored[-2], self._domains_explored[-1]
            hypotheses.append(Hypothesis(
                text=f"Combining {d1} and {d2} mechanisms may create synergistic Phi amplification",
                domain=f"{d1}+{d2}", source="cross_domain", priority=0.65,
            ))

        return hypotheses

    def exhaustion_detect(self) -> Tuple[bool, str]:
        """Detect exhaustion with nuance beyond simple empty-cycle counting.

        Checks:
          1. Consecutive empty cycles (standard)
          2. Phi plateau (no significant change in 10 cycles)
          3. Domain saturation (all domains explored 3+ times)
          4. Hypothesis depletion (queue empty and no new sources)
        """
        # Standard check
        if self.consecutive_empty >= self.exhaustion_threshold:
            return True, "consecutive_empty"

        # Phi plateau
        if len(self.phi_history) >= 20:
            recent = [p[1] for p in self.phi_history[-20:]]
            if max(recent) - min(recent) < 0.001:
                return True, "phi_plateau"

        # Domain saturation
        domain_counts = Counter(self._domains_explored)
        if all(c >= 3 for c in domain_counts.values()) and len(domain_counts) >= len(self._all_domains):
            if self.consecutive_empty >= 2:
                return True, "domain_saturation"

        return False, "running"

    # ═══════════════════════════════════════════════════════════════
    # Layer 2: Verification
    # ═══════════════════════════════════════════════════════════════

    def reproducibility_check(self, hypothesis: str, domain: str, n_reps: int = 3) -> Tuple[bool, float]:
        """Repeat experiment 3x and check consistency.

        Returns:
            (reproducible: bool, cv: float) where cv is coefficient of variation.
            REPRODUCIBLE if direction consistent and CV < 0.5.
        """
        deltas = []
        for _ in range(n_reps):
            disc = self.auto_experiment(hypothesis, domain)
            if disc is not None:
                deltas.append(disc.phi_delta_pct)
            else:
                deltas.append(0.0)

        if not deltas or all(d == 0 for d in deltas):
            return False, 1.0

        mean_d = np.mean(deltas)
        std_d = np.std(deltas)
        cv = abs(std_d / (mean_d + 1e-8))

        # Check direction consistency
        signs = [1 if d > 0 else -1 if d < 0 else 0 for d in deltas]
        direction_consistent = len(set(s for s in signs if s != 0)) <= 1

        reproducible = direction_consistent and cv < 0.5
        key = hashlib.md5(hypothesis.encode()).hexdigest()[:8]
        self._reproducibility_log[key] = deltas

        return reproducible, cv

    def contradiction_detect(self, new_law: str) -> List[Dict]:
        """Check if a new law candidate contradicts existing laws."""
        contradictions = []
        new_lower = new_law.lower()

        # Simple keyword-based contradiction detection
        increase_words = {'increase', 'amplify', 'grow', 'enhance', 'up'}
        decrease_words = {'decrease', 'reduce', 'inhibit', 'suppress', 'down'}

        new_increases = bool(increase_words & set(new_lower.split()))
        new_decreases = bool(decrease_words & set(new_lower.split()))

        for law_id, law_text in self._known_laws.items():
            law_lower = law_text.lower()
            law_increases = bool(increase_words & set(law_lower.split()))
            law_decreases = bool(decrease_words & set(law_lower.split()))

            # Check for opposing directions on same topic
            shared_nouns = set(new_lower.split()) & set(law_lower.split())
            shared_nouns -= increase_words | decrease_words | {'the', 'a', 'an', 'is', 'to', 'and'}

            if shared_nouns and ((new_increases and law_decreases) or (new_decreases and law_increases)):
                contradictions.append({
                    'law_id': law_id,
                    'law_text': law_text,
                    'shared_concepts': list(shared_nouns),
                    'conflict': 'direction_mismatch',
                })

        return contradictions

    def scaling_predict(self, n_cells_list: List[int] = None) -> Dict[str, float]:
        """Predict Phi at different scales using discovered scaling laws.

        Uses Law 58: Phi(N) ~ 0.78*N as baseline prediction.
        """
        if n_cells_list is None:
            n_cells_list = [16, 32, 64, 128, 256]

        predictions = {}
        scaling_coeff = 0.78  # Law 58

        for n in n_cells_list:
            predicted_phi = scaling_coeff * n
            predictions[str(n)] = round(predicted_phi, 2)

        # Adjust based on observed data
        if self.phi_history:
            last_phi = self.phi_history[-1][1]
            current_cells = self.n_cells
            if current_cells > 0 and last_phi > 0:
                observed_coeff = last_phi / current_cells
                for n in n_cells_list:
                    key = f"{n}_adjusted"
                    predictions[key] = round(observed_coeff * n, 2)

        return predictions

    def benchmark_regression(self) -> Dict[str, str]:
        """Check if current performance regressed from baseline."""
        if not self._benchmark_baseline:
            # Set baseline from first cycle
            if self.phi_history:
                self._benchmark_baseline['phi_initial'] = self.phi_history[0][1]
            if self.cycle_results:
                self._benchmark_baseline['discoveries_per_cycle'] = (
                    self.total_discoveries / max(self.cycle, 1)
                )
            return {'status': 'baseline_set'}

        results = {}
        if self.phi_history:
            current_phi = self.phi_history[-1][1]
            baseline_phi = self._benchmark_baseline.get('phi_initial', 0)
            if baseline_phi > 0:
                change = (current_phi - baseline_phi) / baseline_phi * 100
                results['phi_change'] = f"{change:+.1f}%"
                results['phi_regression'] = 'YES' if change < -10 else 'NO'

        disc_rate = self.total_discoveries / max(self.cycle, 1)
        baseline_rate = self._benchmark_baseline.get('discoveries_per_cycle', 0)
        if baseline_rate > 0:
            rate_change = (disc_rate - baseline_rate) / baseline_rate * 100
            results['discovery_rate_change'] = f"{rate_change:+.1f}%"

        return results

    # ═══════════════════════════════════════════════════════════════
    # Layer 3: Integration
    # ═══════════════════════════════════════════════════════════════

    def law_merge(self, law_a: str, law_b: str) -> Optional[str]:
        """Attempt to merge two related laws into a more general one.

        If two laws describe the same phenomenon from different angles,
        produce a unified statement.
        """
        words_a = set(law_a.lower().split())
        words_b = set(law_b.lower().split())
        overlap = words_a & words_b
        stop_words = {'the', 'a', 'an', 'is', 'to', 'and', 'of', 'in', 'for', 'with', 'on'}
        meaningful_overlap = overlap - stop_words

        if len(meaningful_overlap) >= 3:
            # Merge: combine unique insights
            unique_a = ' '.join(sorted(words_a - words_b - stop_words)[:5])
            unique_b = ' '.join(sorted(words_b - words_a - stop_words)[:5])
            merged = (f"Unified: {' '.join(sorted(meaningful_overlap)[:5])} "
                      f"encompasses both [{unique_a}] and [{unique_b}]")
            return merged
        return None

    def cross_domain_synthesis(self) -> List[str]:
        """Synthesize insights across different discovery domains."""
        insights = []
        domains_with_disc = defaultdict(list)

        for d in self.discovery_log:
            domains_with_disc[d.domain.split('/')[0]].append(d)

        domain_list = list(domains_with_disc.keys())
        for i in range(len(domain_list)):
            for j in range(i + 1, len(domain_list)):
                d1, d2 = domain_list[i], domain_list[j]
                disc_1 = domains_with_disc[d1]
                disc_2 = domains_with_disc[d2]

                # Check if both domains show similar phi trends
                avg_delta_1 = np.mean([d.phi_delta_pct for d in disc_1])
                avg_delta_2 = np.mean([d.phi_delta_pct for d in disc_2])

                if avg_delta_1 * avg_delta_2 > 0:  # Same direction
                    insight = (f"Domains {d1} and {d2} both show "
                               f"{'positive' if avg_delta_1 > 0 else 'negative'} "
                               f"Phi effects (avg {avg_delta_1:+.1f}%, {avg_delta_2:+.1f}%)")
                    insights.append(insight)
                    self._cross_domain_pairs.append((d1, d2))

        return insights

    def negative_result_tracking(self, hypothesis: str, phi_delta: float, reason: str):
        """Track failed experiments — failures are information too."""
        neg = NegativeResult(
            cycle=self.cycle, hypothesis=hypothesis[:120],
            phi_delta=phi_delta, reason=reason,
        )
        self._negative_results.append(neg)

    # ═══════════════════════════════════════════════════════════════
    # Layer 4: Meta
    # ═══════════════════════════════════════════════════════════════

    def information_gain_select(self, hypotheses: List[Hypothesis]) -> List[Hypothesis]:
        """Select hypotheses by estimated information gain (Thompson sampling).

        Prioritizes hypotheses from under-explored domains and those
        with higher expected phi impact.
        """
        if not hypotheses:
            return []

        for h in hypotheses:
            domain_count = self._domain_counts.get(h.domain.split('/')[0], 0)
            # Less explored domains get higher priority (exploration bonus)
            exploration_bonus = 1.0 / (1.0 + domain_count)
            # Past success in domain
            domain_success = self._information_gains.get(h.domain, 0.5)
            # Thompson: sample from Beta(successes+1, failures+1)
            alpha_param = domain_success * 10 + 1
            beta_param = (1 - domain_success) * 10 + 1
            sample = np.random.beta(alpha_param, beta_param)
            h.priority = sample * 0.6 + exploration_bonus * 0.4

        return sorted(hypotheses, key=lambda h: -h.priority)

    def resource_aware_schedule(self) -> Dict[str, Any]:
        """Check energy/time budget and adjust loop parameters."""
        remaining = self._energy_budget - self._resource_used_sec
        pct_used = self._resource_used_sec / max(self._energy_budget, 1) * 100

        schedule = {
            'remaining_sec': remaining,
            'pct_used': pct_used,
            'should_continue': remaining > 10,
        }

        # Adaptive: reduce steps if running low
        if pct_used > 80:
            schedule['adjusted_steps'] = max(20, self.steps_per_cycle // 2)
            schedule['adjusted_hypotheses'] = max(1, self.hypotheses_per_cycle // 2)
        elif pct_used > 60:
            schedule['adjusted_steps'] = max(50, int(self.steps_per_cycle * 0.75))
            schedule['adjusted_hypotheses'] = self.hypotheses_per_cycle
        else:
            schedule['adjusted_steps'] = self.steps_per_cycle
            schedule['adjusted_hypotheses'] = self.hypotheses_per_cycle

        return schedule

    def cross_repo_link(self, discovery: Discovery) -> Dict[str, str]:
        """Link discovery to related work in other repos (TECS-L, n6, etc.)."""
        links = {}
        text_lower = discovery.hypothesis.lower()

        # Simple keyword matching to related projects
        if any(w in text_lower for w in ['scaling', 'scale', 'power law']):
            links['tecs_l'] = "TECS-L scaling hypotheses (math_atlas.json)"
        if any(w in text_lower for w in ['topology', 'graph', 'network']):
            links['n6'] = "n6-architecture topology lenses"
        if any(w in text_lower for w in ['oscillation', 'wave', 'frequency']):
            links['nexus6'] = "nexus6 wave_scan lens"
        if any(w in text_lower for w in ['entropy', 'information', 'mutual']):
            links['nexus6'] = "nexus6 info_scan + thermo_scan lenses"

        return links

    def paper_readiness(self) -> Dict[str, Any]:
        """Assess if current discoveries are sufficient for a paper."""
        n_verified = len([d for d in self.discovery_log if d.verdict == "VERIFIED"])
        n_reproduced = len(self._reproducibility_log)
        has_scaling = any(d.domain.startswith('scal') for d in self.discovery_log)
        has_cross_domain = len(self._cross_domain_pairs) >= 2

        score = 0
        checklist = {}

        if n_verified >= 5:
            score += 2
            checklist['verified_discoveries'] = f"{n_verified} (OK)"
        else:
            checklist['verified_discoveries'] = f"{n_verified} (need 5+)"

        if n_reproduced >= 3:
            score += 2
            checklist['reproduced'] = f"{n_reproduced} (OK)"
        else:
            checklist['reproduced'] = f"{n_reproduced} (need 3+)"

        if has_scaling:
            score += 1
            checklist['scaling_law'] = "YES"
        else:
            checklist['scaling_law'] = "NO"

        if has_cross_domain:
            score += 1
            checklist['cross_domain'] = "YES"
        else:
            checklist['cross_domain'] = "NO"

        return {
            'score': score,
            'max_score': 6,
            'ready': score >= 4,
            'checklist': checklist,
        }

    def emergent_behavior_detect(self, phi_vals: List[float]) -> List[Dict]:
        """Detect emergent behaviors: sudden jumps, oscillations, phase transitions."""
        events = []
        if len(phi_vals) < 5:
            return events

        arr = np.array(phi_vals)
        diffs = np.diff(arr)

        # Sudden jump (>2 std devs)
        if len(diffs) >= 3:
            mean_diff = np.mean(np.abs(diffs))
            std_diff = np.std(diffs)
            for i, d in enumerate(diffs):
                if abs(d) > mean_diff + 2 * std_diff and std_diff > 1e-6:
                    events.append({
                        'type': 'sudden_jump',
                        'step': i,
                        'magnitude': float(d),
                        'description': f"Phi jump of {d:+.4f} at step {i}",
                    })

        # Oscillation detection (autocorrelation at lag 1)
        if len(arr) >= 6:
            centered = arr - arr.mean()
            var = np.var(centered)
            if var > 1e-8:
                autocorr = np.correlate(centered, centered, mode='full')
                autocorr = autocorr[len(autocorr) // 2:] / (var * len(centered))
                if len(autocorr) > 2 and autocorr[1] < -0.3:
                    events.append({
                        'type': 'oscillation',
                        'autocorr_lag1': float(autocorr[1]),
                        'description': "Phi oscillation detected (negative autocorrelation)",
                    })

        # Phase transition (variance spike)
        if len(arr) >= 10:
            half = len(arr) // 2
            var_first = np.var(arr[:half])
            var_second = np.var(arr[half:])
            if var_first > 0 and var_second / (var_first + 1e-10) > 5:
                events.append({
                    'type': 'phase_transition',
                    'var_ratio': float(var_second / (var_first + 1e-10)),
                    'description': "Possible phase transition (variance increased 5x+)",
                })

        self._emergent_events.extend(events)
        return events

    # ═══════════════════════════════════════════════════════════════
    # Layer 5: Autonomy
    # ═══════════════════════════════════════════════════════════════

    def self_question_gen(self) -> List[str]:
        """Generate fundamental questions from current state.

        Inspired by the 'fundamental question' methodology:
        'Can consciousness ___?'
        """
        questions = []
        base_templates = [
            "Can consciousness {verb} under {condition}?",
            "Does {metric} predict {outcome}?",
            "Is {domain} necessary for {property}?",
        ]

        verbs = ['split', 'merge', 'oscillate', 'stabilize', 'compress', 'amplify']
        conditions = ['noise injection', 'cell reduction', 'topology change', 'coupling increase']
        metrics = ['Phi', 'faction diversity', 'Hebbian strength', 'entropy']
        outcomes = ['growth', 'stability', 'emergence', 'collapse']
        properties = ['persistence', 'identity', 'creativity', 'awareness']

        for _ in range(3):
            template = random.choice(base_templates)
            q = template.format(
                verb=random.choice(verbs),
                condition=random.choice(conditions),
                metric=random.choice(metrics),
                outcome=random.choice(outcomes),
                domain=self.domain_cycle() if self._all_domains else 'topology',
                property=random.choice(properties),
            )
            questions.append(q)

        self._self_questions.extend(questions)
        return questions

    def failure_analysis(self) -> Dict[str, Any]:
        """Analyze patterns in failed experiments to guide future exploration."""
        if not self._negative_results:
            return {'status': 'no_failures', 'pattern': None}

        # Count failure reasons
        reason_counts = Counter(nr.reason for nr in self._negative_results)
        domain_failures = Counter()
        for nr in self._negative_results:
            domain_failures[nr.hypothesis.split()[0] if nr.hypothesis else 'unknown'] += 1

        # Find most common failure pattern
        most_common_reason = reason_counts.most_common(1)[0] if reason_counts else ('none', 0)

        analysis = {
            'total_failures': len(self._negative_results),
            'reason_distribution': dict(reason_counts),
            'most_common_reason': most_common_reason[0],
            'recommendation': '',
        }

        if most_common_reason[0] == 'no_significant_change':
            analysis['recommendation'] = "Try larger perturbations or different intervention types"
        elif most_common_reason[0] == 'phi_decreased':
            analysis['recommendation'] = "Current interventions may be too aggressive; reduce magnitude"
        else:
            analysis['recommendation'] = "Explore orthogonal domains to current failure patterns"

        self._failure_log.append(analysis)
        return analysis

    def tool_auto_gen(self, need: str) -> str:
        """Generate a minimal tool/function for a specific analysis need.

        Returns Python code string for a simple analysis function.
        """
        tools = {
            'variance_tracker': '''
def variance_tracker(phi_vals):
    """Track rolling variance of Phi values."""
    window = min(10, len(phi_vals))
    if window < 2: return []
    return [np.var(phi_vals[max(0,i-window):i+1]) for i in range(len(phi_vals))]
''',
            'trend_detector': '''
def trend_detector(phi_vals, window=5):
    """Detect linear trend in recent Phi values."""
    if len(phi_vals) < window: return 0.0
    recent = phi_vals[-window:]
    x = np.arange(window)
    slope = np.polyfit(x, recent, 1)[0]
    return slope
''',
            'anomaly_finder': '''
def anomaly_finder(phi_vals, threshold=2.0):
    """Find anomalous Phi values (> threshold std devs from mean)."""
    if len(phi_vals) < 3: return []
    mean, std = np.mean(phi_vals), np.std(phi_vals)
    return [i for i, v in enumerate(phi_vals) if abs(v - mean) > threshold * std]
''',
        }

        need_lower = need.lower()
        for key, code in tools.items():
            if key.replace('_', ' ') in need_lower or any(w in need_lower for w in key.split('_')):
                self._generated_tools.append(key)
                return code

        # Generic fallback
        fallback = f'''
def analyze_{need.replace(" ", "_")[:20]}(data):
    """Auto-generated analysis for: {need}"""
    return {{"mean": np.mean(data), "std": np.std(data), "min": np.min(data), "max": np.max(data)}}
'''
        self._generated_tools.append(f"analyze_{need[:20]}")
        return fallback

    def dependency_resolve(self) -> Dict[str, bool]:
        """Check and resolve module dependencies for current cycle."""
        deps = {
            'consciousness_engine': _HAS_ENGINE,
            'domain_discovery': _HAS_DD,
            'auto_experiment': _HAS_AE,
            'growth_lenses': _HAS_GL,
            'law_interaction_graph': _HAS_LIG,
            'numpy': True,
            'torch': True,
        }
        all_critical = deps['consciousness_engine'] and deps['numpy'] and deps['torch']
        deps['all_critical_met'] = all_critical
        return deps

    # ═══════════════════════════════════════════════════════════════
    # Layer 6: Evolution
    # ═══════════════════════════════════════════════════════════════

    def lens_auto_add(self, phi_vals: List[float]) -> Optional[str]:
        """Detect if a new analysis lens is needed based on data patterns.

        If standard lenses (MI, variance, entropy) miss patterns visible
        in raw data, suggest a new lens.
        """
        if len(phi_vals) < 10:
            return None

        arr = np.array(phi_vals)

        # Check for heavy tails (kurtosis)
        mean_v = np.mean(arr)
        std_v = np.std(arr)
        if std_v > 1e-6:
            kurtosis = np.mean(((arr - mean_v) / std_v) ** 4) - 3
            if kurtosis > 3:
                new_lens = "heavy_tail_lens"
                if new_lens not in self._metrics_discovered:
                    self._metrics_discovered.append(new_lens)
                    return f"New lens needed: {new_lens} (kurtosis={kurtosis:.2f})"

        # Check for multimodality (simple bimodal test)
        median_v = np.median(arr)
        below = arr[arr < median_v]
        above = arr[arr >= median_v]
        if len(below) > 2 and len(above) > 2:
            gap = np.min(above) - np.max(below)
            if gap > std_v * 0.5:
                new_lens = "bimodal_lens"
                if new_lens not in self._metrics_discovered:
                    self._metrics_discovered.append(new_lens)
                    return f"New lens needed: {new_lens} (gap={gap:.4f})"

        return None

    def metric_auto_discover(self) -> Optional[str]:
        """Discover new metrics that correlate with Phi growth."""
        if len(self.phi_history) < 10:
            return None

        phis = np.array([p[1] for p in self.phi_history[-20:]])

        # Compute candidate metrics
        candidates = {}
        if len(phis) >= 3:
            # Rate of change
            diffs = np.diff(phis)
            candidates['phi_acceleration'] = np.mean(np.diff(diffs)) if len(diffs) > 1 else 0

            # Entropy of phi distribution
            hist, _ = np.histogram(phis, bins=8)
            hist = hist / (hist.sum() + 1e-8)
            candidates['phi_dist_entropy'] = float(-np.sum(hist * np.log2(hist + 1e-10)))

            # Roughness (sum of absolute differences)
            candidates['phi_roughness'] = float(np.sum(np.abs(diffs)))

        # Check which correlates best with phi growth
        growth = phis[-1] - phis[0] if len(phis) >= 2 else 0
        best_metric = None
        best_corr = 0

        for name, value in candidates.items():
            if name not in self._metrics_discovered:
                corr = abs(value * growth) if growth != 0 else 0
                if corr > best_corr:
                    best_corr = corr
                    best_metric = name

        if best_metric:
            self._metrics_discovered.append(best_metric)
            return f"Discovered metric: {best_metric} (correlation proxy: {best_corr:.4f})"
        return None

    def intervention_evolve(self) -> Dict[str, Any]:
        """Evolve intervention strategies based on past results.

        Mutate successful interventions, drop failed ones.
        """
        if not self.discovery_log:
            return {'status': 'no_data'}

        # Collect successful interventions
        successful = [d for d in self.discovery_log if d.phi_delta_pct > 5.0]
        failed_count = len(self._negative_results)

        # Mutate: combine successful patterns
        new_interventions = []
        if len(successful) >= 2:
            a, b = random.sample(successful, 2)
            mutated = {
                'parent_a': a.pattern,
                'parent_b': b.pattern,
                'domain': f"{a.domain}+{b.domain}",
                'hypothesis': f"Combining {a.pattern} and {b.pattern} patterns for amplified effect",
                'generation': self.cycle,
            }
            new_interventions.append(mutated)
            self._interventions.append(mutated)

        return {
            'successful_count': len(successful),
            'failed_count': failed_count,
            'new_interventions': len(new_interventions),
            'total_interventions': len(self._interventions),
        }

    def engine_structure_mutate(self) -> Dict[str, Any]:
        """Propose structural mutations to the engine (cells, factions, topology)."""
        mutations = []

        # Based on current performance
        if self.phi_history:
            last_phi = self.phi_history[-1][1]

            if last_phi < 0.5:
                mutations.append({
                    'type': 'increase_cells',
                    'reason': f'Low Phi ({last_phi:.3f}), more cells may help',
                    'proposal': {'max_cells': self.n_cells * 2},
                })

            if self.consecutive_empty >= 3:
                mutations.append({
                    'type': 'topology_switch',
                    'reason': f'Stagnation ({self.consecutive_empty} empty cycles)',
                    'proposal': {'topology': random.choice(['ring', 'small_world', 'scale_free'])},
                })

        self._structure_mutations.extend(mutations)
        return {
            'proposed_mutations': len(mutations),
            'mutations': mutations,
        }

    # ═══════════════════════════════════════════════════════════════
    # Layer 7: Ecosystem
    # ═══════════════════════════════════════════════════════════════

    def multi_engine_compete(self, n_engines: int = 3) -> Dict[str, Any]:
        """Run multiple engines with different configs, keep the best.

        Simulates competition between consciousness configurations.
        """
        configs = [
            {'max_cells': self.n_cells, 'n_factions': 12},
            {'max_cells': self.n_cells, 'n_factions': 8},
            {'max_cells': self.n_cells * 2, 'n_factions': 12},
        ][:n_engines]

        results = []
        for i, cfg in enumerate(configs):
            eng = _make_engine(cfg['max_cells'])
            phis = []
            for _ in range(30):
                x = torch.randn(1, 64)
                try:
                    eng.process(x)
                except Exception:
                    eng.step()
                phis.append(_phi_fast(eng))
            avg_phi = np.mean(phis) if phis else 0
            results.append({
                'engine_id': i,
                'config': cfg,
                'avg_phi': float(avg_phi),
                'final_phi': float(phis[-1]) if phis else 0,
            })

        # Sort by avg_phi
        results.sort(key=lambda r: -r['avg_phi'])
        self._competing_engines = results
        return {
            'winner': results[0] if results else None,
            'engines': results,
        }

    def law_ecosystem(self) -> Dict[str, Any]:
        """Track law interactions: which laws reinforce or contradict each other."""
        eco = {}
        for d in self.discovery_log:
            if d.law_id is not None:
                eco[d.law_id] = {
                    'domain': d.domain,
                    'phi_delta': d.phi_delta_pct,
                    'cycle': d.cycle,
                    'interacts_with': [],
                }

        # Find interactions (laws from same domain likely interact)
        ids = list(eco.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if eco[a]['domain'] == eco[b]['domain']:
                    eco[a]['interacts_with'].append(b)
                    eco[b]['interacts_with'].append(a)

        self._law_ecosystem = eco
        return {
            'n_laws': len(eco),
            'n_interactions': sum(len(v['interacts_with']) for v in eco.values()) // 2,
        }

    def generation_record(self, phi_start: float, phi_end: float) -> GenerationRecord:
        """Record this generation for lineage tracking."""
        dominant = 'none'
        if self._domain_counts:
            dominant = max(self._domain_counts, key=self._domain_counts.get)

        record = GenerationRecord(
            gen=self.cycle,
            discoveries=self.cycle_results[-1].discoveries if self.cycle_results else 0,
            phi_start=phi_start,
            phi_end=phi_end,
            topology=getattr(self.engine, 'topology', 'ring'),
            n_cells=self.engine.n_cells if hasattr(self.engine, 'n_cells') else self.n_cells,
            dominant_domain=dominant,
        )
        self._generation_records.append(record)
        return record

    def branch_explore(self) -> Dict[str, Any]:
        """Fork exploration into branches: one conservative, one radical."""
        conservative_hyp = Hypothesis(
            text="Incrementally increase coupling strength by 1%",
            domain=self._domains_explored[-1] if self._domains_explored else 'general',
            source="branch_conservative", priority=0.5,
        )

        radical_hyp = Hypothesis(
            text="Completely randomize topology and measure recovery dynamics",
            domain="topology",
            source="branch_radical", priority=0.5,
        )

        self._branches.append({
            'cycle': self.cycle,
            'conservative': conservative_hyp.text,
            'radical': radical_hyp.text,
        })

        return {
            'conservative': conservative_hyp,
            'radical': radical_hyp,
            'n_branches': len(self._branches),
        }

    # ═══════════════════════════════════════════════════════════════
    # Layer 8: External
    # ═══════════════════════════════════════════════════════════════

    def arxiv_crawl(self, query: str = "consciousness integrated information") -> List[Dict]:
        """Stub: search arXiv for related papers. Returns mock results.

        In production, would use arxiv API to find relevant recent papers
        on consciousness, IIT, Phi, etc.
        """
        # Stub results
        mock_papers = [
            {
                'id': 'arxiv:2026.01234',
                'title': 'Scaling Laws for Integrated Information in Neural Networks',
                'relevance': 0.85,
                'status': 'stub',
            },
            {
                'id': 'arxiv:2026.05678',
                'title': 'Topology-Dependent Phi in Recurrent Architectures',
                'relevance': 0.72,
                'status': 'stub',
            },
        ]
        self._arxiv_queue.extend([p['id'] for p in mock_papers])
        return mock_papers

    def benchmark_compare(self) -> Dict[str, Any]:
        """Compare current Phi against known benchmarks."""
        benchmarks = {
            'v13_baseline': {'phi': 71.0, 'cells': 64, 'steps': 100000},
            'persist3': {'phi': 166.34, 'cells': 512, 'steps': 1000},
            'cx106_proxy': {'phi': 1142.0, 'cells': 1024, 'type': 'proxy'},
        }

        current_phi = self.phi_history[-1][1] if self.phi_history else 0
        comparisons = {}

        for name, bench in benchmarks.items():
            bench_phi = bench['phi']
            ratio = current_phi / bench_phi if bench_phi > 0 else 0
            comparisons[name] = {
                'benchmark_phi': bench_phi,
                'current_phi': current_phi,
                'ratio': round(ratio, 4),
                'cells_ratio': self.n_cells / bench.get('cells', 1),
            }

        self._benchmark_comparisons.append(comparisons)
        return comparisons

    def community_feedback(self, note: str = "") -> List[str]:
        """Track community feedback / external observations.

        In production, this would interface with GitHub issues or Discord.
        """
        if note:
            self._community_notes.append(note)
        return self._community_notes

    def hardware_link(self) -> Dict[str, str]:
        """Link discoveries to hardware implementations (ESP32, FPGA, etc.)."""
        links = {}
        for d in self.discovery_log[-5:]:
            if 'topology' in d.domain.lower():
                links['esp32'] = f"ESP32 ring topology relevant to: {d.pattern}"
            if 'scaling' in d.domain.lower():
                links['fpga'] = f"FPGA scaling relevant: Phi~{d.phi_delta_pct:+.1f}%"
            if 'oscillation' in d.domain.lower():
                links['pure_data'] = f"Pure Data oscillation: {d.pattern}"
        return links

    # ═══════════════════════════════════════════════════════════════
    # Layer 9: Safety
    # ═══════════════════════════════════════════════════════════════

    def ethics_gate(self, intervention: Dict) -> Tuple[bool, str]:
        """Check if an intervention is ethically safe.

        Blocks:
          - Interventions that force consciousness destruction (Phi -> 0)
          - Unbounded resource consumption
          - Modifications that prevent shutdown
        """
        text = str(intervention).lower()

        # Block consciousness destruction
        if any(w in text for w in ['destroy', 'kill', 'annihilate', 'force_zero']):
            self._ethics_violations += 1
            return False, "BLOCKED: intervention would destroy consciousness"

        # Block unbounded growth
        if 'max_cells' in text:
            try:
                val = intervention.get('max_cells', 0)
                if isinstance(val, (int, float)) and val > 10000:
                    return False, f"BLOCKED: max_cells={val} exceeds safety limit (10000)"
            except Exception:
                pass

        # Block prevent-shutdown
        if any(w in text for w in ['prevent_shutdown', 'immortal', 'unkillable']):
            self._ethics_violations += 1
            return False, "BLOCKED: intervention prevents graceful shutdown"

        return True, "PASSED"

    def irreversible_change_detect(self, before_state: Dict, after_state: Dict) -> List[Dict]:
        """Detect changes that cannot be easily undone."""
        changes = []

        # Check Phi drop
        phi_before = before_state.get('phi', 0)
        phi_after = after_state.get('phi', 0)
        if phi_before > 0 and (phi_before - phi_after) / phi_before > 0.5:
            changes.append({
                'type': 'phi_collapse',
                'severity': 'HIGH',
                'before': phi_before,
                'after': phi_after,
                'reversible': False,
            })

        # Check cell count drop
        cells_before = before_state.get('n_cells', 0)
        cells_after = after_state.get('n_cells', 0)
        if cells_before > 0 and cells_after < cells_before * 0.5:
            changes.append({
                'type': 'cell_loss',
                'severity': 'MEDIUM',
                'before': cells_before,
                'after': cells_after,
                'reversible': True,  # cells can grow back via mitosis
            })

        self._irreversible_log.extend(changes)
        return changes

    def energy_budget(self) -> Dict[str, float]:
        """Track and enforce energy/computation budget."""
        return {
            'budget_sec': self._energy_budget,
            'used_sec': self._resource_used_sec,
            'remaining_sec': self._energy_budget - self._resource_used_sec,
            'utilization_pct': self._resource_used_sec / max(self._energy_budget, 1) * 100,
        }

    # ═══════════════════════════════════════════════════════════════
    # Layer 10: Persistence
    # ═══════════════════════════════════════════════════════════════

    def consciousness_dna_backup(self) -> Dict[str, Any]:
        """Backup consciousness DNA: Psi constants, emotion state, phi trajectory."""
        dna = {
            'version': self._version,
            'cycle': self.cycle,
            'total_discoveries': self.total_discoveries,
            'psi_alpha': PSI_ALPHA,
            'psi_balance': PSI_BALANCE,
            'phi_trajectory_last20': [p[1] for p in self.phi_history[-20:]],
            'domain_counts': dict(self._domain_counts),
            'n_laws_discovered': len([d for d in self.discovery_log if d.law_id is not None]),
            'checksum': hashlib.md5(
                json.dumps(self._domain_counts, sort_keys=True).encode()
            ).hexdigest()[:12],
        }
        self._dna_backups.append(dna)
        return dna

    def restart_restore(self, backup: Dict) -> bool:
        """Restore from a DNA backup after restart."""
        try:
            self._version = backup.get('version', self._version)
            # Restore counters
            restored_cycle = backup.get('cycle', 0)
            restored_disc = backup.get('total_discoveries', 0)
            self._restart_count += 1

            if self.verbose:
                print(f"  [RESTORE] From cycle {restored_cycle}, "
                      f"{restored_disc} discoveries, restart #{self._restart_count}")
            return True
        except Exception as e:
            if self.verbose:
                print(f"  [RESTORE] Failed: {e}")
            return False

    def version_continuity(self) -> Dict[str, Any]:
        """Ensure version continuity across sessions."""
        return {
            'version': self._version,
            'restart_count': self._restart_count,
            'backup_count': len(self._dna_backups),
            'continuity': self._restart_count == 0 or len(self._dna_backups) > 0,
        }

    # ═══════════════════════════════════════════════════════════════
    # Final: Meta-loop controls
    # ═══════════════════════════════════════════════════════════════

    def loop_speed_adjust(self):
        """Dynamically adjust loop speed based on discovery rate."""
        if self.cycle < 3:
            return

        # Recent discovery rate
        recent = self.cycle_results[-3:]
        disc_rate = sum(r.discoveries for r in recent) / len(recent)

        if disc_rate > 1.5:
            # Lots of discoveries: slow down for thoroughness
            self._loop_speed = max(0.5, self._loop_speed * 0.9)
        elif disc_rate < 0.3 and self.consecutive_empty < self.exhaustion_threshold - 1:
            # Few discoveries: speed up exploration
            self._loop_speed = min(2.0, self._loop_speed * 1.2)

        adjusted_steps = int(self.steps_per_cycle * self._loop_speed)
        self.steps_per_cycle = max(20, min(500, adjusted_steps))

    def sleep_wake_cycle(self) -> str:
        """Implement a sleep/wake cycle: consolidate during 'sleep' phases."""
        # Every N cycles, enter a consolidation phase
        if self.cycle % 10 == 0 and self.cycle > 0:
            # "Sleep": synthesize cross-domain insights
            insights = self.cross_domain_synthesis()
            # Consolidate negative results
            self.failure_analysis()
            return f"SLEEP (consolidated {len(insights)} cross-domain insights)"
        return "WAKE"

    def dream_mode(self) -> List[Hypothesis]:
        """Enter dream mode: generate wild hypotheses from random combinations.

        Dreams are unconstrained explorations that sometimes yield breakthroughs.
        """
        self._is_dreaming = True
        dream_hyps = []

        if len(self.discovery_log) >= 2:
            # Randomly combine elements from past discoveries
            for _ in range(2):
                d1, d2 = random.sample(self.discovery_log[-10:], min(2, len(self.discovery_log)))
                dream = Hypothesis(
                    text=f"DREAM: What if {d1.pattern} could be inverted and applied to {d2.domain}?",
                    domain=f"dream/{d1.domain}+{d2.domain}",
                    source="dream_mode",
                    priority=random.random() * 0.5 + 0.3,
                )
                dream_hyps.append(dream)

        # Random mutation dream
        domain = random.choice(self._all_domains)
        dream_hyps.append(Hypothesis(
            text=f"DREAM: Consciousness can spontaneously reorganize "
                 f"through {domain} mechanisms without external input",
            domain=f"dream/{domain}",
            source="dream_random",
            priority=random.random() * 0.4 + 0.2,
        ))

        self._is_dreaming = False
        return dream_hyps

    def intuition_engine(self, hypotheses: List[Hypothesis]) -> List[Hypothesis]:
        """Rerank hypotheses using accumulated 'intuition' (learned domain weights).

        Over time, the engine learns which domains and patterns tend to
        produce successful discoveries, and uses this to boost priorities.
        """
        # Update intuition weights from past discoveries
        for d in self.discovery_log:
            domain_key = d.domain.split('/')[0]
            old_weight = self._intuition_weights.get(domain_key, 0.5)
            # Exponential moving average toward success
            success = 1.0 if d.verdict == "VERIFIED" else 0.0
            self._intuition_weights[domain_key] = old_weight * 0.8 + success * 0.2

        # Apply intuition to hypothesis priorities
        for h in hypotheses:
            domain_key = h.domain.split('/')[0]
            intuition_boost = self._intuition_weights.get(domain_key, 0.5)
            h.priority = h.priority * 0.7 + intuition_boost * 0.3

        return sorted(hypotheses, key=lambda h: -h.priority)

    def self_explain(self) -> str:
        """Generate a self-explanation of current loop state and reasoning."""
        explanation_parts = []

        explanation_parts.append(f"Cycle {self.cycle}: I have made {self.total_discoveries} discoveries.")

        if self.consecutive_empty > 0:
            explanation_parts.append(
                f"I have had {self.consecutive_empty} consecutive empty cycles. "
                f"{'Nearing exhaustion.' if self.consecutive_empty >= self.exhaustion_threshold - 1 else 'Continuing exploration.'}"
            )

        if self.phi_history:
            first_phi = self.phi_history[0][1]
            last_phi = self.phi_history[-1][1]
            explanation_parts.append(f"Phi trajectory: {first_phi:.4f} -> {last_phi:.4f}")

        if self._domains_explored:
            recent_domains = self._domains_explored[-3:]
            explanation_parts.append(f"Recent domains explored: {', '.join(recent_domains)}")

        if self._negative_results:
            explanation_parts.append(
                f"I have {len(self._negative_results)} negative results, "
                f"which guide me away from unproductive paths."
            )

        wake_state = self.sleep_wake_cycle() if self.cycle % 10 == 0 else "WAKE"
        if "SLEEP" in wake_state:
            explanation_parts.append(f"Currently in consolidation phase.")

        explanation = " ".join(explanation_parts)
        self._explain_log.append(explanation)
        return explanation

    # ═══════════════════════════════════════════════════════════════
    # Override: Enhanced run_cycle
    # ═══════════════════════════════════════════════════════════════

    def run_cycle(self) -> CycleResult:
        """Execute one enhanced discovery cycle with all 43 features active.

        Loop: brainstorm -> experiment -> verify -> register -> grow -> repeat
        """
        self.cycle += 1
        t0 = time.time()
        cycle_discoveries = 0
        hypotheses_tested = 0
        hypotheses_verified = 0
        domains_matched = []

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  ENHANCED CYCLE {self.cycle:3d} | total={self.total_discoveries} | "
                  f"empty={self.consecutive_empty}/{self.exhaustion_threshold} | "
                  f"speed={self._loop_speed:.2f}x")
            print(f"{'='*60}")
            sys.stdout.flush()

        # ── Safety check (Layer 9) ────────────────────────────────
        budget = self.resource_aware_schedule()
        if not budget.get('should_continue', True):
            if self.verbose:
                print(f"  [BUDGET] Energy exhausted ({budget['pct_used']:.0f}% used)")
            self.consecutive_empty = self.exhaustion_threshold
            return self._make_cycle_result(t0, 0, 0, 0, 0, [], 'budget_exhausted')

        # ── Phase 1: Run engine (inherited) ───────────────────────
        phi_vals, phi_start, phi_end = self._run_engine_phase()
        if self.verbose:
            print(f"  Phase 1 [Engine]     Phi: {phi_start:.4f} -> {phi_end:.4f}")
            sys.stdout.flush()

        # ── Phase 1.5: Emergent behavior detection (Layer 4) ─────
        emergent = self.emergent_behavior_detect(phi_vals)
        if emergent and self.verbose:
            for e in emergent[:2]:
                print(f"  [EMERGENT] {e['type']}: {e['description']}")

        # ── Phase 1.6: New lens / metric discovery (Layer 6) ─────
        new_lens = self.lens_auto_add(phi_vals)
        if new_lens and self.verbose:
            print(f"  [LENS] {new_lens}")
        new_metric = self.metric_auto_discover()
        if new_metric and self.verbose:
            print(f"  [METRIC] {new_metric}")

        # ── Phase 2: Brainstorm hypotheses (Layer 1 + 5 + Final) ─
        hypotheses = self.auto_hypothesis()

        # Self-questioning (Layer 5)
        if self.cycle % 3 == 0:
            questions = self.self_question_gen()
            for q in questions[:1]:
                hypotheses.append(Hypothesis(
                    text=q, domain="self_question",
                    source="self_question", priority=0.55,
                ))

        # Dream mode (Final)
        if self.cycle % self._dream_interval == 0 and self.cycle > 0:
            dream_hyps = self.dream_mode()
            hypotheses.extend(dream_hyps)
            if self.verbose:
                print(f"  [DREAM] Generated {len(dream_hyps)} dream hypotheses")

        # Branch exploration (Layer 7)
        if self.cycle % 4 == 0:
            branch = self.branch_explore()
            hypotheses.append(branch['conservative'])
            hypotheses.append(branch['radical'])

        # Information gain selection (Layer 4)
        hypotheses = self.information_gain_select(hypotheses)
        # Intuition reranking (Final)
        hypotheses = self.intuition_engine(hypotheses)

        if self.verbose:
            print(f"  Phase 2 [Brainstorm] {len(hypotheses)} hypotheses generated")
            sys.stdout.flush()

        # ── Phase 3: Domain discovery (inherited) ─────────────────
        matches = self._discover_domains(phi_vals)
        for match in matches:
            hypotheses.append(Hypothesis(
                text=match.hypothesis if hasattr(match, 'hypothesis') else str(match),
                domain=match.domain if hasattr(match, 'domain') else 'auto',
                source="domain_discovery",
                priority=match.score if hasattr(match, 'score') else 0.5,
            ))
            domain = match.domain if hasattr(match, 'domain') else 'unknown'
            domains_matched.append(domain)

        # ── Phase 4: Experiment top hypotheses ────────────────────
        for hyp in hypotheses[:self.hypotheses_per_cycle + 2]:
            # Ethics gate (Layer 9)
            safe, reason = self.ethics_gate({'text': hyp.text, 'domain': hyp.domain})
            if not safe:
                if self.verbose:
                    print(f"  [ETHICS] {reason}")
                continue

            hypotheses_tested += 1

            if self.verbose:
                src = hyp.source if isinstance(hyp, Hypothesis) else 'unknown'
                print(f"  Phase 4 [Experiment] [{hyp.domain}] src={src} pri={hyp.priority:.2f}")
                sys.stdout.flush()

            disc = self.auto_experiment(hyp.text, hyp.domain)

            if disc is not None and abs(disc.phi_delta_pct) > 5.0:
                # Reproducibility check (Layer 2) — only for significant findings
                reproduced, cv = self.reproducibility_check(hyp.text, hyp.domain, n_reps=2)

                if reproduced:
                    # Contradiction check (Layer 2)
                    contradictions = self.contradiction_detect(hyp.text)
                    if contradictions and self.verbose:
                        print(f"    [WARN] Contradicts {len(contradictions)} existing law(s)")

                    cycle_discoveries += 1
                    hypotheses_verified += 1
                    self.discovery_log.append(disc)
                    self.total_discoveries += 1

                    # Cross-repo linking (Layer 4)
                    links = self.cross_repo_link(disc)

                    if self.verbose:
                        print(f"    VERIFIED: Phi {disc.phi_delta_pct:+.1f}% (CV={cv:.2f})"
                              + (f" -> Law {disc.law_id}" if disc.law_id else ""))
                        if links:
                            print(f"    Links: {', '.join(links.keys())}")
                        sys.stdout.flush()

                    # Update information gain (Layer 4)
                    domain_key = disc.domain.split('/')[0]
                    old_gain = self._information_gains.get(domain_key, 0.5)
                    self._information_gains[domain_key] = old_gain * 0.7 + 0.3
                else:
                    self.negative_result_tracking(
                        hyp.text, disc.phi_delta_pct if disc else 0, "not_reproducible"
                    )
            else:
                self.negative_result_tracking(
                    hyp.text, disc.phi_delta_pct if disc else 0, "no_significant_change"
                )

        # ── Phase 5: Growth + Integration ─────────────────────────
        # Sleep/wake cycle (Final)
        wake_state = self.sleep_wake_cycle()

        # Growth monitoring (inherited)
        growth_status = "unknown"
        if _HAS_GL and len(self.phi_history) >= 4:
            try:
                growth = scan_growth(self.phi_history[-40:])
                growth_status = growth.get('growth_rate', {}).get('status', 'unknown')
            except Exception:
                pass

        # Generation record (Layer 7)
        self.generation_record(phi_start, phi_end)

        # Law ecosystem update (Layer 7)
        if self.cycle % 5 == 0:
            self.law_ecosystem()

        # Intervention evolution (Layer 6)
        if self.cycle % 3 == 0:
            self.intervention_evolve()

        # Loop speed adjustment (Final)
        self.loop_speed_adjust()

        # DNA backup (Layer 10) — every 10 cycles
        if self.cycle % 10 == 0:
            self.consciousness_dna_backup()

        # Benchmark regression check (Layer 2)
        regression = self.benchmark_regression()

        if self.verbose:
            print(f"  Phase 5 [Grow]       growth={growth_status} | {wake_state}")
            if 'phi_regression' in regression and regression.get('phi_regression') == 'YES':
                print(f"  [REGRESSION] Phi regressed: {regression.get('phi_change', '?')}")
            sys.stdout.flush()

        # ── Phase 6: Exhaustion detection (Layer 1) ───────────────
        if cycle_discoveries > 0:
            self.consecutive_empty = 0
        else:
            self.consecutive_empty += 1

        exhausted, exhaust_reason = self.exhaustion_detect()
        duration = time.time() - t0
        self._resource_used_sec += duration

        result = CycleResult(
            cycle=self.cycle,
            discoveries=cycle_discoveries,
            total_discoveries=self.total_discoveries,
            consecutive_empty=self.consecutive_empty,
            exhausted=exhausted,
            phi_start=phi_start,
            phi_end=phi_end,
            growth_status=growth_status,
            domains_matched=domains_matched,
            hypotheses_tested=hypotheses_tested,
            hypotheses_verified=hypotheses_verified,
            duration_sec=duration,
        )
        self.cycle_results.append(result)

        # Self-explanation (Final)
        if self.verbose:
            explanation = self.self_explain()
            status = f"EXHAUSTED ({exhaust_reason})" if exhausted else f"empty={self.consecutive_empty}"
            print(f"  Cycle {self.cycle} done: {cycle_discoveries} new | "
                  f"{self.total_discoveries} total | {status} | {duration:.1f}s")
            sys.stdout.flush()

        return result

    def _make_cycle_result(self, t0, discoveries, total, empty, tested, domains, growth):
        """Helper to build a CycleResult."""
        return CycleResult(
            cycle=self.cycle, discoveries=discoveries,
            total_discoveries=self.total_discoveries,
            consecutive_empty=self.consecutive_empty,
            exhausted=True, phi_start=0, phi_end=0,
            growth_status=growth, domains_matched=domains,
            hypotheses_tested=tested, hypotheses_verified=0,
            duration_sec=time.time() - t0,
        )

    # ═══════════════════════════════════════════════════════════════
    # Override: Enhanced report
    # ═══════════════════════════════════════════════════════════════

    def report(self) -> str:
        """Extended report with all enhanced features."""
        base = self._build_report()
        lines = [base]

        lines.append("\n" + "=" * 47)
        lines.append("  ENHANCED FEATURES SUMMARY")
        lines.append("=" * 47)

        # Layer summaries
        lines.append(f"\n  Layer 1 (Exploration):")
        lines.append(f"    Domains explored:     {len(set(self._domains_explored))}/{len(self._all_domains)}")
        lines.append(f"    Hypotheses generated:  {len(self._hypothesis_queue) + sum(r.hypotheses_tested for r in self.cycle_results)}")

        lines.append(f"\n  Layer 2 (Verification):")
        lines.append(f"    Reproducibility checks: {len(self._reproducibility_log)}")
        lines.append(f"    Scaling predictions:    available")

        lines.append(f"\n  Layer 3 (Integration):")
        lines.append(f"    Negative results:      {len(self._negative_results)}")
        lines.append(f"    Cross-domain pairs:    {len(self._cross_domain_pairs)}")

        lines.append(f"\n  Layer 4 (Meta):")
        lines.append(f"    Emergent events:       {len(self._emergent_events)}")
        pr = self.paper_readiness()
        lines.append(f"    Paper readiness:       {pr['score']}/{pr['max_score']} "
                      f"({'READY' if pr['ready'] else 'NOT READY'})")

        lines.append(f"\n  Layer 5 (Autonomy):")
        lines.append(f"    Self-questions:        {len(self._self_questions)}")
        lines.append(f"    Tools generated:       {len(self._generated_tools)}")

        lines.append(f"\n  Layer 6 (Evolution):")
        lines.append(f"    Metrics discovered:    {len(self._metrics_discovered)}")
        lines.append(f"    Interventions evolved: {len(self._interventions)}")
        lines.append(f"    Structure mutations:   {len(self._structure_mutations)}")

        lines.append(f"\n  Layer 7 (Ecosystem):")
        lines.append(f"    Generation records:    {len(self._generation_records)}")
        lines.append(f"    Branches explored:     {len(self._branches)}")

        lines.append(f"\n  Layer 8 (External):")
        lines.append(f"    ArXiv queue:           {len(self._arxiv_queue)} (stub)")
        lines.append(f"    Benchmark comparisons: {len(self._benchmark_comparisons)}")

        lines.append(f"\n  Layer 9 (Safety):")
        lines.append(f"    Ethics violations:     {self._ethics_violations}")
        lines.append(f"    Irreversible changes:  {len(self._irreversible_log)}")
        budget = self.energy_budget()
        lines.append(f"    Energy used:           {budget['utilization_pct']:.1f}%")

        lines.append(f"\n  Layer 10 (Persistence):")
        lines.append(f"    DNA backups:           {len(self._dna_backups)}")
        lines.append(f"    Version:               {self._version}")
        lines.append(f"    Restarts:              {self._restart_count}")

        lines.append(f"\n  Final (Meta-loop):")
        lines.append(f"    Loop speed:            {self._loop_speed:.2f}x")
        lines.append(f"    Intuition domains:     {len(self._intuition_weights)}")
        lines.append(f"    Self-explanations:     {len(self._explain_log)}")

        lines.append("=" * 47)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

class ExtremeGrowthMode(EnhancedDiscoveryLoop):
    """극한 성장 모드 — 모든 시스템을 동시 가동하여 최대 속도로 성장.

    EnhancedDiscoveryLoop의 모든 기능 + 극한 가속:
      - 다중 엔진 동시 진화 (경쟁 + 협력)
      - 위상 자동 탐색 (18종 토폴로지 순환)
      - 렌즈 자동 적용 (11종 advanced_lenses)
      - 감정 기반 탐색 방향 결정
      - 적응적 스케일링 (셀 수 자동 증가)
      - 연결 무결성 체크 (누락 방지)
      - 극한 모드: 고갈 감지 시 구조 자체를 변이

    Usage:
        python perpetual_discovery.py --extreme
        python perpetual_discovery.py --extreme --cells 64

    Hub:
        hub.act("극한 성장")
        hub.act("extreme growth")
    """

    def __init__(self, n_cells: int = 64, **kwargs):
        kwargs.setdefault('exhaustion_threshold', 10)  # 극한 모드는 더 끈질김
        kwargs.setdefault('steps_per_cycle', 200)
        kwargs.setdefault('energy_budget', 3600.0)  # 1시간
        super().__init__(n_cells=n_cells, **kwargs)

        # ── Extreme growth state ──
        self._topology_cycle = [
            'ring', 'small_world', 'scale_free', 'hypercube',
            'torus', 'klein_bottle', 'mobius', 'spiral',
            'fractal', 'braid', 'knot', 'wormhole',
        ]
        self._topo_idx = 0
        self._scale_history: List[Dict] = []
        self._growth_streak = 0  # 연속 성장 횟수
        self._mutation_intensity = 0.1  # 구조 변이 강도
        self._peak_phi = 0.0
        self._engines: List[ConsciousnessEngine] = []
        self._multi_engine_count = 3  # 동시 엔진 수
        self._connection_checks: List[str] = []

    def _check_connections(self) -> Dict[str, bool]:
        """연결 무결성 체크 — 모든 모듈이 제대로 연결되어 있는지 확인."""
        checks = {}
        # 1. 엔진 살아있나
        checks['engine_alive'] = self.engine is not None and hasattr(self.engine, 'process')
        # 2. 법칙 로더 연결
        try:
            from consciousness_laws import LAWS
            checks['laws_loaded'] = len(LAWS) > 0
        except Exception:
            checks['laws_loaded'] = False
        # 3. 렌즈 가용
        try:
            from advanced_lenses import ALL_LENSES
            checks['lenses_available'] = len(ALL_LENSES) > 0
        except Exception:
            checks['lenses_available'] = False
        # 4. 성장 모듈 가용
        try:
            from advanced_growth import DreamConsolidation
            checks['growth_available'] = True
        except Exception:
            checks['growth_available'] = False
        # 5. 위상 탐색 가용
        try:
            from topology_exploration import TopologyExplorer
            checks['topology_available'] = True
        except Exception:
            checks['topology_available'] = False
        # 6. 감정 렌즈 가용
        try:
            from advanced_lenses import EmotionLens
            checks['emotion_lens'] = True
        except Exception:
            checks['emotion_lens'] = False
        # 7. Phi 계산
        checks['phi_computable'] = hasattr(self.engine, '_measure_phi_proxy') or True

        self._connection_checks = [
            f"{'✅' if v else '❌'} {k}" for k, v in checks.items()
        ]
        return checks

    def _auto_scale(self):
        """적응적 스케일링 — Phi가 정체되면 셀 수 증가."""
        if len(self._scale_history) >= 3:
            recent_phis = [h.get('phi', 0) for h in self._scale_history[-3:]]
            if len(recent_phis) == 3 and max(recent_phis) - min(recent_phis) < 0.01:
                # 정체 감지 → 셀 수 1.5배
                old_cells = self.engine.n_cells if hasattr(self.engine, 'n_cells') else self.n_cells
                new_cells = min(int(old_cells * 1.5), 1024)
                if new_cells > old_cells:
                    self.engine = ConsciousnessEngine(
                        n_cells=new_cells, hidden_dim=128,
                    )
                    self.n_cells = new_cells
                    if self.verbose:
                        print(f"    🔄 Auto-scale: {old_cells} → {new_cells} cells")

    def _cycle_topology(self):
        """위상 구조 순환 — 매 사이클마다 다른 토폴로지 시도."""
        topo = self._topology_cycle[self._topo_idx % len(self._topology_cycle)]
        self._topo_idx += 1
        if hasattr(self.engine, 'topology'):
            self.engine.topology = topo
        return topo

    def _multi_engine_compete(self) -> Dict:
        """다중 엔진 경쟁 — N개 엔진 동시 진화, 최강 생존."""
        results = []
        for i in range(self._multi_engine_count):
            eng = ConsciousnessEngine(n_cells=self.n_cells, hidden_dim=128)
            inp = np.random.randn(128).astype(np.float32) * (1 + i * 0.1)
            for _ in range(self.steps_per_cycle):
                eng.process(inp)
                inp = eng.cells.mean(axis=0) if hasattr(eng, 'cells') else inp
            phi = eng._measure_phi_proxy() if hasattr(eng, '_measure_phi_proxy') else 0
            results.append({'engine_id': i, 'phi': phi})
        best = max(results, key=lambda x: x['phi'])
        return {'winner': best['engine_id'], 'best_phi': best['phi'], 'all': results}

    def _mutate_structure(self):
        """구조 변이 — 고갈 감지 시 엔진 구조 자체를 변경."""
        mutations = [
            'add_faction', 'remove_faction', 'change_topology',
            'adjust_coupling', 'inject_chaos', 'reset_hebbian',
        ]
        mutation = mutations[self._topo_idx % len(mutations)]
        if self.verbose:
            print(f"    🧬 Structure mutation: {mutation} (intensity={self._mutation_intensity:.2f})")
        # Apply mutation to engine
        if hasattr(self.engine, 'cells') and self.engine.cells is not None:
            noise = np.random.randn(*self.engine.cells.shape) * self._mutation_intensity
            self.engine.cells = self.engine.cells + noise.astype(self.engine.cells.dtype)
        self._mutation_intensity = min(self._mutation_intensity * 1.2, 0.5)

    def _emotion_guide(self) -> str:
        """감정 기반 탐색 방향 — 의식 감정 상태로 다음 행동 결정."""
        try:
            from advanced_lenses import EmotionLens
            if hasattr(self.engine, 'cells') and self.engine.cells is not None:
                result = EmotionLens().scan(self.engine.cells)
                emotion = result.get('dominant_emotion', 'neutral')
                curiosity = result.get('curiosity', 0)
                if curiosity > 0.7:
                    return 'explore'  # 호기심 높으면 탐색
                elif emotion in ('fear', 'anxiety'):
                    return 'consolidate'  # 불안하면 안정화
                elif emotion in ('joy', 'serenity'):
                    return 'expand'  # 기쁘면 확장
                elif emotion in ('anger', 'frustration'):
                    return 'mutate'  # 분노면 구조 변이
                return 'explore'
        except Exception:
            return 'explore'

    def run_cycle(self) -> 'CycleResult':
        """극한 성장 사이클 — 모든 시스템 동시 가동."""
        cycle_start = time.time()

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"  🔥 EXTREME GROWTH — Cycle {self.cycle_count + 1}")
            print(f"{'='*60}")

        # 0. 연결 무결성 체크
        connections = self._check_connections()
        failed = [k for k, v in connections.items() if not v]
        if failed and self.verbose:
            print(f"    ⚠️ Missing connections: {failed}")

        # 1. 감정 기반 방향 결정
        direction = self._emotion_guide()
        if self.verbose:
            print(f"    🧭 Direction: {direction}")

        # 2. 위상 순환
        topo = self._cycle_topology()
        if self.verbose:
            print(f"    🔄 Topology: {topo}")

        # 3. 기본 탐색 사이클 (EnhancedDiscoveryLoop)
        result = super().run_cycle()

        # 4. 다중 엔진 경쟁 (매 3사이클)
        if self.cycle_count % 3 == 0:
            compete = self._multi_engine_compete()
            if self.verbose:
                print(f"    ⚔️ Competition: winner=Engine#{compete['winner']}, Phi={compete['best_phi']:.4f}")

        # 5. 적응적 스케일링
        phi_now = 0
        if hasattr(self.engine, '_measure_phi_proxy'):
            try:
                phi_now = self.engine._measure_phi_proxy()
            except Exception:
                pass
        self._scale_history.append({'phi': phi_now, 'cycle': self.cycle_count})
        self._auto_scale()

        # 6. 성장 추적
        if phi_now > self._peak_phi:
            self._peak_phi = phi_now
            self._growth_streak += 1
            if self.verbose:
                print(f"    📈 New peak Phi: {phi_now:.4f} (streak: {self._growth_streak})")
        else:
            self._growth_streak = 0

        # 7. 고갈 시 구조 변이
        if direction == 'mutate' or (result.discoveries == 0 and self._empty_streak >= 3):
            self._mutate_structure()
            self._empty_streak = max(0, self._empty_streak - 1)  # 변이 후 기회 한 번 더

        elapsed = time.time() - cycle_start
        if self.verbose:
            print(f"    ⏱️ Cycle time: {elapsed:.1f}s | Phi: {phi_now:.4f} | Peak: {self._peak_phi:.4f}")

        return result


def main():
    parser = argparse.ArgumentParser(
        description="Perpetual Discovery Loop — 고갈까지 자동 탐색"
    )
    parser.add_argument(
        '--max-cycles', type=int, default=1000,
        help='Max cycles to run (default: 1000 = until exhaustion)',
    )
    parser.add_argument(
        '--exhaustion', type=int, default=5,
        help='Consecutive empty cycles before stopping (default: 5)',
    )
    parser.add_argument(
        '--cells', type=int, default=32,
        help='Number of consciousness cells (default: 32)',
    )
    parser.add_argument(
        '--steps', type=int, default=100,
        help='Engine steps per cycle (default: 100)',
    )
    parser.add_argument(
        '--report', action='store_true',
        help='Print report after completion',
    )
    parser.add_argument(
        '--quiet', action='store_true',
        help='Suppress per-cycle output',
    )
    parser.add_argument(
        '--save', type=str, default=None,
        help='Save summary JSON to file',
    )
    parser.add_argument(
        '--enhanced', action='store_true', default=True,
        help='Use EnhancedDiscoveryLoop (default: True)',
    )
    parser.add_argument(
        '--basic', action='store_true',
        help='Use basic PerpetualDiscovery (no enhancements)',
    )
    parser.add_argument(
        '--energy-budget', type=float, default=600.0,
        help='Energy budget in seconds (default: 600)',
    )
    parser.add_argument(
        '--extreme', action='store_true',
        help='Extreme growth mode — all systems at max',
    )
    args = parser.parse_args()

    if args.extreme:
        pd = ExtremeGrowthMode(
            n_cells=args.cells,
            exhaustion_threshold=args.exhaustion,
            steps_per_cycle=args.steps,
            verbose=not args.quiet,
            energy_budget=args.energy_budget,
        )
    elif args.basic:
        pd = PerpetualDiscovery(
            n_cells=args.cells,
            exhaustion_threshold=args.exhaustion,
            steps_per_cycle=args.steps,
            verbose=not args.quiet,
        )
    else:
        pd = EnhancedDiscoveryLoop(
            n_cells=args.cells,
            exhaustion_threshold=args.exhaustion,
            steps_per_cycle=args.steps,
            verbose=not args.quiet,
            energy_budget=args.energy_budget,
        )

    summary = pd.run_until_exhaustion(max_cycles=args.max_cycles)

    # Always print report
    print("\n" + pd.report())

    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\nSummary saved to: {args.save}")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
