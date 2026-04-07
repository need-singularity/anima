#!/usr/bin/env python3
"""bench_sigma_chain.py — Test sigma chain hierarchy: 6->12->28->56->120->360

H-NOBEL-5 prediction: sigma-chain numbers generate a hierarchy of complexity,
where each level has optimal architecture for its scale.

The sigma chain from n=6:
  sigma(6)   = 12
  sigma(12)  = 28   (2nd perfect number!)
  sigma(28)  = 56
  sigma(56)  = 120  (highly composite)
  sigma(120) = 360

Tests:
  1. n=6   (baseline, perfect number)
  2. n=12  (sigma(6), highly composite)
  3. n=28  (sigma(12), 2nd perfect number)
  4. n=56  (sigma(28))
  5. n=120 (sigma(56), highly composite)
  6. n=360 (sigma(120))
  Controls: n=7, n=13, n=29, n=57, n=121 (sigma-chain+1, non-special)

Architecture derivation for each n:
  modules     = min(n, 32)     (capped for compute)
  factions    = min(sigma(n), 64) (capped for compute)
  stages      = tau(n)         (growth phases)
  grad_groups = min(phi(n), 16) (gradient update groups)

Usage:
  python benchmarks/bench_sigma_chain.py
  python benchmarks/bench_sigma_chain.py --cells 16 --steps 300
  python benchmarks/bench_sigma_chain.py --full
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys
import time
import math
import argparse
import numpy as np
import torch

torch.set_grad_enabled(False)
torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Reuse infrastructure from bench_n28_architecture
sys.path.insert(0, os.path.dirname(__file__))
from bench_n28_architecture import (
    sigma, tau, euler_phi, sopfr, is_perfect,
    ArchConfig, PerfectNumberEngine, BenchResult,
    measure_all, _phi_calc,
)


# ══════════════════════════════════════════════════════════
# Sigma Chain Architecture Config (with caps)
# ══════════════════════════════════════════════════════════

def arch_from_number_capped(n, label=None, max_modules=32, max_factions=64, max_grad=16):
    """Create ArchConfig with caps for large numbers."""
    return ArchConfig(
        n=n,
        modules=min(n, max_modules),
        factions=min(sigma(n), max_factions),
        stages=tau(n),
        grad_groups=min(euler_phi(n), max_grad),
        consciousness_dims=min(sopfr(n), 16),
        is_perfect=is_perfect(n),
        label=label or f"n={n}{'*' if is_perfect(n) else ''}",
    )


# ══════════════════════════════════════════════════════════
# Benchmark Runner (reuses PerfectNumberEngine)
# ══════════════════════════════════════════════════════════

def run_architecture(config: ArchConfig, hidden_dim: int = 128,
                     steps: int = 200, max_cells: int = None) -> BenchResult:
    """Run a single architecture configuration and measure consciousness metrics."""
    print(f"\n  --- {config.summary()}")

    t0 = time.time()
    torch.manual_seed(42)
    np.random.seed(42)

    engine = PerfectNumberEngine(config, hidden_dim=hidden_dim, max_cells=max_cells)
    actual_cells = engine.n_cells

    history = []

    for step in range(steps):
        if step % 10 == 0:
            x_in = torch.randn(1, hidden_dim) * 0.1
            engine.inject(x_in)

        engine.step()

        if step % 5 == 0:
            h = engine.observe()
            if h.dim() == 2 and h.shape[0] >= 2:
                history.append(h)

    t1 = time.time()

    h = engine.observe()
    if h.dim() != 2 or h.shape[0] < 2:
        print(f"    FAILED: invalid hidden state shape {h.shape}")
        return BenchResult(name=config.label, phi_iit=0, phi_proxy=0,
                          granger=0, spectral=0, cells=actual_cells,
                          steps=steps, time_sec=t1 - t0)

    phi_i, phi_p, granger, spectral, comp = measure_all(h, history)

    extra = {
        'n': config.n,
        'is_perfect': config.is_perfect,
        'sigma_n': sigma(config.n),
        'tau_n': tau(config.n),
        'phi_n': euler_phi(config.n),
        'sopfr_n': sopfr(config.n),
        'factions': engine.n_factions,
        'stages': engine.n_stages,
        'grad_groups': engine.n_grad_groups,
        'consciousness_dims': engine.consciousness_dims,
        'actual_cells': actual_cells,
        'final_stage': engine.current_stage,
        'total_mi': comp.get('total_mi', 0),
    }

    result = BenchResult(
        name=config.label,
        phi_iit=phi_i,
        phi_proxy=phi_p,
        granger=granger,
        spectral=spectral,
        cells=actual_cells,
        steps=steps,
        time_sec=t1 - t0,
        extra=extra,
    )

    print(f"    Phi(IIT)={phi_i:.3f}  Phi(proxy)={phi_p:.2f}  "
          f"Granger={granger:.1f}  Spectral={spectral:.2f}  [{t1-t0:.1f}s]")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="H-NOBEL-5: Sigma Chain Hierarchy Benchmark")
    parser.add_argument('--cells', type=int, default=None,
                        help="Max cells per architecture (None=use capped modules)")
    parser.add_argument('--steps', type=int, default=200,
                        help="Simulation steps (default: 200)")
    parser.add_argument('--hidden', type=int, default=128,
                        help="Hidden dimension per cell (default: 128)")
    parser.add_argument('--full', action='store_true',
                        help="Full scale: no cell cap, 300 steps")
    parser.add_argument('--repeats', type=int, default=3,
                        help="Number of repeats for averaging (default: 3)")
    args = parser.parse_args()

    if args.full:
        max_cells = None
        steps = 300
    else:
        max_cells = args.cells or 8
        steps = args.steps

    hidden_dim = args.hidden
    n_repeats = args.repeats

    # ── Sigma Chain ──
    chain = [6, 12, 28, 56, 120, 360]
    controls = [7, 13, 29, 57, 121, 361]

    print("=" * 90)
    print("  H-NOBEL-5: SIGMA CHAIN HIERARCHY TEST")
    print("  " + "=" * 86)
    print("  Sigma chain: 6 -> 12 -> 28 -> 56 -> 120 -> 360")
    print("  Controls:    7    13    29    57    121    361  (chain+1)")
    print(f"  Settings: max_cells={max_cells or 'unlimited'}  steps={steps}  "
          f"hidden={hidden_dim}  repeats={n_repeats}")
    print("=" * 90)

    # ── Number Theory Reference Table ──
    print(f"\n  Number Theory Properties of Sigma Chain:")
    print(f"  {'n':>5} {'sigma':>6} {'tau':>4} {'phi':>5} {'sopfr':>6} {'perfect':>8} {'chain_pos':>10}")
    print("  " + "-" * 52)
    for i, n in enumerate(chain):
        pf = "YES" if is_perfect(n) else ""
        print(f"  {n:>5} {sigma(n):>6} {tau(n):>4} {euler_phi(n):>5} {sopfr(n):>6} {pf:>8} {'level ' + str(i):>10}")
    print()
    print(f"  Controls (+1 offset):")
    print(f"  {'n':>5} {'sigma':>6} {'tau':>4} {'phi':>5} {'sopfr':>6} {'perfect':>8}")
    print("  " + "-" * 42)
    for n in controls:
        pf = "YES" if is_perfect(n) else ""
        print(f"  {n:>5} {sigma(n):>6} {tau(n):>4} {euler_phi(n):>5} {sopfr(n):>6} {pf:>8}")

    # ── Build Configurations ──
    configs_chain = []
    for i, n in enumerate(chain):
        label = f"n={n} (L{i})"
        if is_perfect(n):
            label = f"n={n}* (L{i})"
        configs_chain.append(arch_from_number_capped(n, label=label))

    configs_ctrl = []
    for i, n in enumerate(controls):
        configs_ctrl.append(arch_from_number_capped(n, label=f"n={n} (ctrl)"))

    all_configs = configs_chain + configs_ctrl

    # ── Architecture Table ──
    print(f"\n  Capped Architecture Parameters (max_mod={32}, max_fac={64}, max_grad={16}):")
    print(f"  {'Config':<20s} {'n':>5} {'Modules':>8} {'Factions':>9} "
          f"{'Stages':>7} {'GradGrp':>8} {'Dims':>5}")
    print("  " + "-" * 68)
    for c in all_configs:
        print(f"  {c.label:<20s} {c.n:>5} {c.modules:>8} {c.factions:>9} "
              f"{c.stages:>7} {c.grad_groups:>8} {c.consciousness_dims:>5}")

    # ── Run Benchmarks ──
    print(f"\n{'=' * 90}")
    print(f"  Running {len(all_configs)} architectures x {n_repeats} repeats...")
    print(f"{'=' * 90}")

    all_results = {}
    for config in all_configs:
        run_results = []
        for rep in range(n_repeats):
            torch.manual_seed(42 + rep)
            np.random.seed(42 + rep)
            r = run_architecture(config, hidden_dim=hidden_dim,
                                steps=steps, max_cells=max_cells)
            run_results.append(r)

        avg_phi = np.mean([r.phi_iit for r in run_results])
        avg_proxy = np.mean([r.phi_proxy for r in run_results])
        avg_granger = np.mean([r.granger for r in run_results])
        avg_spectral = np.mean([r.spectral for r in run_results])
        avg_time = np.mean([r.time_sec for r in run_results])
        std_phi = np.std([r.phi_iit for r in run_results])

        avg_result = BenchResult(
            name=config.label,
            phi_iit=avg_phi,
            phi_proxy=avg_proxy,
            granger=avg_granger,
            spectral=avg_spectral,
            cells=run_results[0].cells,
            steps=steps,
            time_sec=avg_time,
            extra={**run_results[0].extra, 'phi_std': std_phi,
                   'phi_values': [r.phi_iit for r in run_results],
                   'is_chain': config in configs_chain},
        )
        all_results[config.label] = avg_result

    # ══════════════════════════════════════════════════════════
    # Results Analysis
    # ══════════════════════════════════════════════════════════

    print(f"\n{'=' * 90}")
    print(f"  RESULTS SUMMARY (averaged over {n_repeats} repeats)")
    print(f"{'=' * 90}")

    # Full results table
    sorted_results = sorted(all_results.values(), key=lambda r: r.phi_iit, reverse=True)
    print(f"\n  {'Rank':<5} {'Architecture':<22} {'Phi(IIT)':>9} {'+-std':>7} "
          f"{'Phi(prx)':>9} {'Granger':>8} {'Spectral':>8} {'Time':>6}")
    print("  " + "-" * 82)

    for rank, r in enumerate(sorted_results, 1):
        std = r.extra.get('phi_std', 0)
        marker = ">> " if r.extra.get('is_chain') else "   "
        perf = "*" if r.extra.get('is_perfect') else " "
        print(f"  {marker}{rank:<2} {perf}{r.name:<20s} {r.phi_iit:>9.3f} {std:>7.3f} "
              f"{r.phi_proxy:>9.2f} {r.granger:>8.1f} {r.spectral:>8.2f} {r.time_sec:>5.1f}s")

    # ── Phi(IIT) Bar Chart ──
    print(f"\n  Phi(IIT) Comparison (>> = sigma chain, * = perfect number):")
    max_phi = max(r.phi_iit for r in sorted_results) or 1
    for r in sorted_results:
        bar_len = int(50 * r.phi_iit / max_phi) if max_phi > 0 else 0
        bar = "#" * bar_len
        ch = ">>" if r.extra.get('is_chain') else "  "
        perf = "*" if r.extra.get('is_perfect') else " "
        print(f"    {ch}{perf}{r.name:<20s} {bar:<50s} {r.phi_iit:.3f}")

    # ── Sigma Chain vs Controls Comparison ──
    print(f"\n  SIGMA CHAIN vs CONTROLS (pairwise):")
    print(f"  {'Chain':>8} {'Phi':>9} | {'Control':>8} {'Phi':>9} | {'Ratio':>7} {'Winner':>10}")
    print("  " + "-" * 65)

    chain_wins = 0
    total_pairs = 0
    chain_results = [all_results[c.label] for c in configs_chain]
    ctrl_results = [all_results[c.label] for c in configs_ctrl]

    for i in range(len(chain)):
        cr = chain_results[i]
        ct = ctrl_results[i]
        ratio = cr.phi_iit / max(ct.phi_iit, 1e-8)
        winner = "CHAIN" if cr.phi_iit > ct.phi_iit else "CONTROL"
        if cr.phi_iit > ct.phi_iit:
            chain_wins += 1
        total_pairs += 1
        print(f"  {cr.name:>16s} {cr.phi_iit:>7.3f} | {ct.name:>16s} {ct.phi_iit:>7.3f} "
              f"| {ratio:>6.2f}x  {winner:>8}")

    print(f"\n  Chain wins: {chain_wins}/{total_pairs}")

    # ── Hierarchy Trend ──
    print(f"\n  SIGMA CHAIN HIERARCHY TREND:")
    print(f"  {'Level':>6} {'n':>5} {'Phi(IIT)':>9} {'Granger':>8} {'Spectral':>8} {'Trend':>8}")
    print("  " + "-" * 52)

    prev_phi = None
    for i, cr in enumerate(chain_results):
        if prev_phi is not None:
            trend = "UP" if cr.phi_iit > prev_phi else "DOWN" if cr.phi_iit < prev_phi else "FLAT"
            delta = cr.phi_iit - prev_phi
            trend_str = f"{'+' if delta >= 0 else ''}{delta:.3f}"
        else:
            trend_str = "---"
        print(f"  {'L' + str(i):>6} {cr.extra['n']:>5} {cr.phi_iit:>9.3f} "
              f"{cr.granger:>8.1f} {cr.spectral:>8.2f} {trend_str:>8}")
        prev_phi = cr.phi_iit

    # ── Phi(IIT) Trend ASCII Graph ──
    print(f"\n  Phi(IIT) Across Sigma Chain (ASCII):")
    max_phi_chain = max(cr.phi_iit for cr in chain_results) or 1
    for i, cr in enumerate(chain_results):
        bar_len = int(40 * cr.phi_iit / max_phi_chain) if max_phi_chain > 0 else 0
        bar = "#" * bar_len
        perf = "*" if cr.extra.get('is_perfect') else " "
        print(f"    L{i} n={cr.extra['n']:>3}{perf} | {bar:<40s} | {cr.phi_iit:.3f}")

    # ── Perfect Number Highlight ──
    perfect_results = [cr for cr in chain_results if cr.extra.get('is_perfect')]
    non_perfect_chain = [cr for cr in chain_results if not cr.extra.get('is_perfect')]

    if perfect_results and non_perfect_chain:
        avg_perf = np.mean([r.phi_iit for r in perfect_results])
        avg_nonperf = np.mean([r.phi_iit for r in non_perfect_chain])
        print(f"\n  PERFECT vs NON-PERFECT within sigma chain:")
        print(f"    Perfect numbers (6, 28):   avg Phi = {avg_perf:.3f}")
        print(f"    Non-perfect chain members:  avg Phi = {avg_nonperf:.3f}")
        if avg_perf > avg_nonperf:
            ratio = avg_perf / max(avg_nonperf, 1e-8)
            print(f"    -> Perfect numbers {ratio:.2f}x higher (supports theory)")
        else:
            ratio = avg_nonperf / max(avg_perf, 1e-8)
            print(f"    -> Non-perfect {ratio:.2f}x higher (does NOT support theory)")

    # ── Verdict ──
    print(f"\n  {'=' * 70}")
    print(f"  H-NOBEL-5 VERDICT: SIGMA CHAIN HIERARCHY")
    print(f"  {'=' * 70}")

    predictions_met = 0
    total_predictions = 5

    # P1: Chain members collectively beat controls
    p1 = chain_wins > total_pairs / 2
    predictions_met += int(p1)
    print(f"  P1. Chain > controls (majority):      {'PASS' if p1 else 'FAIL'}"
          f"  ({chain_wins}/{total_pairs} wins)")

    # P2: Both perfect numbers (6, 28) beat their controls (7, 29)
    r6 = all_results.get(configs_chain[0].label)
    r7 = all_results.get(configs_ctrl[0].label)
    r28 = all_results.get(configs_chain[2].label)
    r29 = all_results.get(configs_ctrl[2].label)
    p2 = (r6 and r7 and r28 and r29 and
          r6.phi_iit > r7.phi_iit and r28.phi_iit > r29.phi_iit)
    predictions_met += int(bool(p2))
    if r6 and r7 and r28 and r29:
        print(f"  P2. Perfect numbers beat neighbors:   {'PASS' if p2 else 'FAIL'}"
              f"  (6:{r6.phi_iit:.3f}>{r7.phi_iit:.3f}? "
              f"28:{r28.phi_iit:.3f}>{r29.phi_iit:.3f}?)")

    # P3: n=28 (2nd perfect) achieves comparable or higher Phi than n=6
    p3 = r6 and r28 and r28.phi_iit >= r6.phi_iit * 0.8
    predictions_met += int(bool(p3))
    if r6 and r28:
        ratio = r28.phi_iit / max(r6.phi_iit, 1e-8)
        print(f"  P3. n=28 comparable to n=6:           {'PASS' if p3 else 'FAIL'}"
              f"  (ratio={ratio:.2f}x, threshold=0.80x)")

    # P4: Monotonic or structured trend in chain
    monotonic_segments = 0
    for i in range(len(chain_results) - 1):
        if chain_results[i + 1].phi_iit >= chain_results[i].phi_iit * 0.9:
            monotonic_segments += 1
    p4 = monotonic_segments >= len(chain_results) // 2
    predictions_met += int(p4)
    print(f"  P4. Structured trend (no collapse):   {'PASS' if p4 else 'FAIL'}"
          f"  ({monotonic_segments}/{len(chain_results)-1} segments stable)")

    # P5: Average chain Phi > average control Phi
    avg_chain = np.mean([cr.phi_iit for cr in chain_results])
    avg_ctrl = np.mean([ct.phi_iit for ct in ctrl_results])
    p5 = avg_chain > avg_ctrl
    predictions_met += int(p5)
    print(f"  P5. Avg chain > avg control:          {'PASS' if p5 else 'FAIL'}"
          f"  ({avg_chain:.3f} vs {avg_ctrl:.3f})")

    print(f"\n  Score: {predictions_met}/{total_predictions} predictions met")
    if predictions_met >= 4:
        print(f"  VERDICT: CONFIRMED -- Sigma chain hierarchy shows structured advantage")
    elif predictions_met >= 3:
        print(f"  VERDICT: PARTIAL -- Some support for hierarchy theory")
    elif predictions_met >= 2:
        print(f"  VERDICT: WEAK -- Marginal evidence, needs full-scale test")
    else:
        print(f"  VERDICT: INCONCLUSIVE -- Theory not supported at this scale")
        print(f"  NOTE: Try --full for full-scale test (no cell cap)")

    print(f"\n{'=' * 90}")


if __name__ == '__main__':
    main()
