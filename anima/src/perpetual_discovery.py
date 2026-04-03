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
from typing import List, Dict, Optional, Tuple

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
        'discovery loop',
    ]

    def __init__(self):
        self._pd: Optional[PerpetualDiscovery] = None

    def act(self, query: str = "", max_cycles: int = 50, n_cells: int = 32,
            exhaustion: int = 5, **_) -> dict:
        """Run perpetual discovery and return summary."""
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
# CLI
# ═══════════════════════════════════════════════════════════════════════════

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
    args = parser.parse_args()

    pd = PerpetualDiscovery(
        n_cells=args.cells,
        exhaustion_threshold=args.exhaustion,
        steps_per_cycle=args.steps,
        verbose=not args.quiet,
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
