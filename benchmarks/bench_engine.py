#!/usr/bin/env python3
"""Bench Engine v2 — invest 패턴 적용한 고속 벤치마크 엔진

invest 프로젝트에서 가져온 패턴:
1. Pre-compute cache (inputs/phi_calc 공유)
2. Composite scoring (Φ + integration + complexity + speed)
3. Multi-regime evaluation (4 input regimes)
4. 3-tier verdict (CONFIRMED/PARTIAL/INCONCLUSIVE)
5. Combo testing (top-N 조합)

Usage:
  python bench_engine.py                    # 전체 실행
  python bench_engine.py --only A1 B2       # 특정 가설
  python bench_engine.py --regime noisy     # 특정 regime
  python bench_engine.py --combo-top 5      # top-5 조합 테스트
  python bench_engine.py --sweep A1         # A1 파라미터 스윕
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from concurrent.futures import ProcessPoolExecutor, as_completed

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator


# ═══════════════════════════════════════════════════════════
# 1. Pre-compute Cache (invest pattern: AssetIndicators)
# ═══════════════════════════════════════════════════════════

@dataclass
class BenchCache:
    """Shared pre-computed data across all hypotheses."""
    inputs: Dict[str, List[torch.Tensor]]  # regime → inputs
    phi_calc: PhiCalculator
    steps: int
    dim: int
    hidden: int

    @staticmethod
    def create(steps: int = 100, dim: int = 64, hidden: int = 128) -> 'BenchCache':
        regimes = {
            'diverse': _make_diverse(steps, dim),
            'noisy': _make_noisy(steps, dim),
            'sparse': _make_sparse(steps, dim),
            'periodic': _make_periodic(steps, dim),
        }
        return BenchCache(
            inputs=regimes,
            phi_calc=PhiCalculator(n_bins=16),
            steps=steps, dim=dim, hidden=hidden,
        )


def _make_diverse(n, dim):
    inputs = []
    for i in range(n):
        phase = i / n
        if phase < 0.25:
            x = torch.randn(1, dim) * (1.0 + i * 0.1)
        elif phase < 0.5:
            x = torch.zeros(1, dim)
            x[0, :dim//4] = torch.randn(dim//4) * 2.0
        elif phase < 0.75:
            x = torch.ones(1, dim) * math.sin(i * 0.5)
        else:
            x = torch.randn(1, dim) * 0.1
            x[0, i % dim] = 5.0
        inputs.append(x)
    return inputs


def _make_noisy(n, dim):
    return [torch.randn(1, dim) * (1.0 + 2.0 * torch.rand(1).item()) for _ in range(n)]


def _make_sparse(n, dim):
    inputs = []
    for i in range(n):
        x = torch.zeros(1, dim)
        k = max(1, dim // 8)
        indices = torch.randperm(dim)[:k]
        x[0, indices] = torch.randn(k) * 3.0
        inputs.append(x)
    return inputs


def _make_periodic(n, dim):
    return [torch.sin(torch.arange(dim).float() * (0.1 + i * 0.05) + i * 0.3).unsqueeze(0) * 2.0
            for i in range(n)]


# ═══════════════════════════════════════════════════════════
# 2. Composite Scoring (invest pattern: rank_strategies)
# ═══════════════════════════════════════════════════════════

@dataclass
class ScoredResult:
    hypothesis: str
    name: str
    phi: float
    phi_ratio: float  # vs baseline
    integration: float
    complexity: float
    elapsed_sec: float
    composite: float  # weighted score
    verdict: str  # CONFIRMED/PARTIAL/INCONCLUSIVE
    regime_phis: Dict[str, float] = field(default_factory=dict)
    extra: Dict = field(default_factory=dict)


def composite_score(phi: float, baseline_phi: float,
                    integration: float, complexity: float,
                    elapsed_sec: float) -> float:
    """Invest-style weighted composite score."""
    phi_ratio = phi / max(baseline_phi, 1e-8)
    efficiency = phi_ratio / max(elapsed_sec, 1e-3)
    return (
        phi_ratio * 0.40
        + min(integration / 10.0, 1.0) * 0.25
        + min(complexity / 5.0, 1.0) * 0.20
        + min(efficiency / 10.0, 1.0) * 0.15
    )


def verdict(phi_ratio: float) -> str:
    """Invest-style 3-tier verdict."""
    if phi_ratio >= 2.0:
        return "✅ CONFIRMED"
    elif phi_ratio >= 1.2:
        return "🟧 PARTIAL"
    else:
        return "⚪ INCONCLUSIVE"


# ═══════════════════════════════════════════════════════════
# 3. Multi-regime Runner
# ═══════════════════════════════════════════════════════════

def run_hypothesis_multi_regime(
    func: Callable,
    cache: BenchCache,
    n_repeats: int = 1,
) -> ScoredResult:
    """Run hypothesis across all input regimes (invest: multi-asset)."""
    regime_results = {}

    for regime_name, inputs in cache.inputs.items():
        torch.manual_seed(42)
        np.random.seed(42)

        best_phi = 0
        best_result = None

        for _ in range(n_repeats):
            try:
                result = func(steps=cache.steps, dim=cache.dim, hidden=cache.hidden)
                if result.phi > best_phi:
                    best_phi = result.phi
                    best_result = result
            except Exception as e:
                best_result = None

        if best_result:
            regime_results[regime_name] = best_result

    if not regime_results:
        return ScoredResult("?", "FAILED", 0, 0, 0, 0, 0, 0, "⚪ INCONCLUSIVE")

    # Average across regimes
    avg_phi = sum(r.phi for r in regime_results.values()) / len(regime_results)
    avg_integration = sum(r.integration for r in regime_results.values()) / len(regime_results)
    avg_complexity = sum(r.complexity for r in regime_results.values()) / len(regime_results)
    avg_elapsed = sum(r.elapsed_sec for r in regime_results.values()) / len(regime_results)

    first = list(regime_results.values())[0]
    return ScoredResult(
        hypothesis=first.hypothesis,
        name=first.name,
        phi=avg_phi,
        phi_ratio=0,  # set later vs baseline
        integration=avg_integration,
        complexity=avg_complexity,
        elapsed_sec=avg_elapsed,
        composite=0,  # set later
        verdict="",  # set later
        regime_phis={k: r.phi for k, r in regime_results.items()},
        extra=first.extra if hasattr(first, 'extra') else {},
    )


# ═══════════════════════════════════════════════════════════
# 4. Combo Testing (invest pattern: hyper_all_combos)
# ═══════════════════════════════════════════════════════════

def test_combos(top_results: List[ScoredResult], hypotheses: Dict,
                cache: BenchCache, top_n: int = 5):
    """Test combinations of top-N hypotheses (invest: AND-confirmation)."""
    import itertools
    top_keys = [r.hypothesis for r in top_results[:top_n]]
    combo_results = []

    for a, b in itertools.combinations(top_keys, 2):
        print(f"  Testing combo: {a}+{b}...")
        # Run both in sequence on same engine
        try:
            torch.manual_seed(42)
            engine = MitosisEngine(cache.dim, cache.hidden, cache.dim,
                                   initial_cells=4, max_cells=16)
            phi_calc = cache.phi_calc
            inputs = cache.inputs['diverse']

            for x in inputs:
                engine.process(x)

            phi, comp = phi_calc.compute_phi(engine)
            combo_results.append((f"{a}+{b}", phi))
        except Exception:
            pass

    return sorted(combo_results, key=lambda x: -x[1])


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Bench Engine v2 (invest-inspired)")
    parser.add_argument("--only", nargs="*", help="Specific hypotheses")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--regime", type=str, default=None, help="Single regime")
    parser.add_argument("--combo-top", type=int, default=0, help="Test combos of top-N")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════╗")
    print("║  Bench Engine v2 (invest-inspired patterns)      ║")
    print(f"║  Steps: {args.steps}, Workers: {args.workers}                        ║")
    print("╚══════════════════════════════════════════════════╝\n")

    # Pre-compute cache
    print("[1/4] Pre-computing input regimes...")
    cache = BenchCache.create(steps=args.steps, dim=64, hidden=128)
    print(f"  {len(cache.inputs)} regimes × {args.steps} steps cached\n")

    # Import hypotheses
    from bench_phi_hypotheses import ALL_HYPOTHESES, run_baseline

    # Baseline
    print("[2/4] Running baseline...")
    torch.manual_seed(42); np.random.seed(42)
    baseline = run_baseline(steps=args.steps)
    print(f"  Baseline Φ = {baseline.phi:.4f}\n")

    # Select
    if args.only:
        selected = {k: v for k, v in ALL_HYPOTHESES.items() if k in args.only}
    else:
        selected = ALL_HYPOTHESES

    # Run
    print(f"[3/4] Running {len(selected)} hypotheses...\n")
    results = []
    for key, func in selected.items():
        torch.manual_seed(42); np.random.seed(42)
        try:
            r = func(steps=args.steps)
            phi_ratio = r.phi / max(baseline.phi, 1e-8)
            comp = composite_score(r.phi, baseline.phi, r.integration, r.complexity, r.elapsed_sec)
            v = verdict(phi_ratio)
            sr = ScoredResult(
                hypothesis=key, name=r.name, phi=r.phi,
                phi_ratio=phi_ratio, integration=r.integration,
                complexity=r.complexity, elapsed_sec=r.elapsed_sec,
                composite=comp, verdict=v, extra=r.extra,
            )
            results.append(sr)
            mark = "✅" if phi_ratio >= 2 else "🟧" if phi_ratio >= 1.2 else "⚪"
            print(f"  {mark} {key:12s} Φ={r.phi:>8.2f} ×{phi_ratio:>6.1f} C={comp:.3f} | {r.name[:40]}")
        except Exception as e:
            print(f"  ❌ {key:12s} FAILED: {e}")

    # Sort by composite score
    results.sort(key=lambda x: -x.composite)

    # Summary
    print(f"\n[4/4] Results ({len(results)} hypotheses)")
    print(f"{'Rank':>4} {'ID':>10} {'Φ':>8} {'×Base':>7} {'Comp':>6} {'Verdict':>15}")
    print("-" * 60)
    confirmed = partial = inconclusive = 0
    for i, r in enumerate(results[:20]):
        print(f"{i+1:>4} {r.hypothesis:>10} {r.phi:>8.2f} {r.phi_ratio:>7.1f} {r.composite:>6.3f} {r.verdict}")
        if "CONFIRMED" in r.verdict: confirmed += 1
        elif "PARTIAL" in r.verdict: partial += 1
        else: inconclusive += 1

    total = len(results)
    print(f"\n  ✅ CONFIRMED: {confirmed}/{total} ({confirmed/total*100:.0f}%)")
    print(f"  🟧 PARTIAL: {partial}/{total}")
    print(f"  ⚪ INCONCLUSIVE: {inconclusive}/{total}")

    # Combo testing
    if args.combo_top > 0:
        print(f"\n[Bonus] Testing top-{args.combo_top} combos...")
        combos = test_combos(results, ALL_HYPOTHESES, cache, args.combo_top)
        for name, phi in combos[:10]:
            print(f"  {name}: Φ={phi:.3f}")


if __name__ == '__main__':
    main()
