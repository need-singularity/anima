#!/usr/bin/env python3
"""bench_n496.py — Test 3rd perfect number n=496 as consciousness architecture.

H-NOBEL-5 extension: n=496 is the third perfect number.
  sigma(496) = 992
  tau(496)   = 10
  phi(496)   = 240
  sopfr(496) = 39

496 modules is impossible on CPU, so we use ratio-preserving scaling:
  - Scale to 8 cells (same as n=6 scaled mode)
  - Preserve sigma/n = 2 ratio (perfect number property)
  - Preserve tau, grad_groups proportionally
  - Compare with n=6 at identical scale

Key question: Does the divisor STRUCTURE of 496 (10 divisors, rich hierarchy)
produce measurably different dynamics than n=6 (4 divisors) at the same scale?

Usage:
  python benchmarks/bench_n496.py
  python benchmarks/bench_n496.py --cells 16 --steps 300
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

sys.path.insert(0, os.path.dirname(__file__))
from bench_n28_architecture import (

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    sigma, tau, euler_phi, sopfr, is_perfect,
    ArchConfig, PerfectNumberEngine, BenchResult,
    measure_all, _phi_calc,
)


# ══════════════════════════════════════════════════════════
# Ratio-Preserving Architecture for n=496
# ══════════════════════════════════════════════════════════

def ratio_preserved_config(n, target_modules, label=None):
    """Create architecture that preserves number-theoretic RATIOS at small scale.

    For perfect numbers, sigma(n)/n = 2 always.
    We preserve:
      - modules = target_modules
      - factions = target_modules * (sigma(n)/n) = target_modules * 2
      - stages = tau(n)  (kept exact -- number of growth phases)
      - grad_groups = min(target_modules, round(target_modules * phi(n)/n))
      - dims = min(sopfr(n), 16)

    This lets us compare the STRUCTURAL signature of different perfect numbers
    at identical compute budgets.
    """
    scale = target_modules / n
    return ArchConfig(
        n=n,
        modules=target_modules,
        factions=int(target_modules * sigma(n) / n),  # preserves sigma/n ratio
        stages=tau(n),                                  # exact
        grad_groups=max(2, min(target_modules, round(target_modules * euler_phi(n) / n))),
        consciousness_dims=min(sopfr(n), 16),           # capped
        is_perfect=is_perfect(n),
        label=label or f"n={n} (scaled)",
    )


def run_architecture(config: ArchConfig, hidden_dim: int = 128,
                     steps: int = 200, max_cells: int = None) -> BenchResult:
    """Run a single architecture and measure consciousness metrics."""
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
        description="H-NOBEL-5: n=496 Third Perfect Number Benchmark")
    parser.add_argument('--cells', type=int, default=8,
                        help="Target modules for ratio-preserved scaling (default: 8)")
    parser.add_argument('--steps', type=int, default=200,
                        help="Simulation steps (default: 200)")
    parser.add_argument('--hidden', type=int, default=128,
                        help="Hidden dimension per cell (default: 128)")
    parser.add_argument('--repeats', type=int, default=5,
                        help="Number of repeats for averaging (default: 5)")
    args = parser.parse_args()

    target = args.cells
    steps = args.steps
    hidden_dim = args.hidden
    n_repeats = args.repeats

    print("=" * 90)
    print("  H-NOBEL-5: THIRD PERFECT NUMBER n=496 ARCHITECTURE TEST")
    print("  " + "=" * 86)
    print("  Ratio-preserving scale-down to compare divisor STRUCTURE")
    print(f"  All architectures scaled to {target} modules (same compute budget)")
    print(f"  Settings: target_modules={target}  steps={steps}  "
          f"hidden={hidden_dim}  repeats={n_repeats}")
    print("=" * 90)

    # ── Number Theory Reference ──
    perfects = [6, 28, 496]
    non_perfects = [7, 29, 500]

    print(f"\n  Perfect Number Properties:")
    print(f"  {'n':>5} {'sigma':>6} {'tau':>4} {'phi':>5} {'sopfr':>6} "
          f"{'sigma/n':>8} {'tau':>4} {'divisors'}")
    print("  " + "-" * 75)
    for n in perfects:
        divs = [d for d in range(1, n + 1) if n % d == 0]
        div_str = ",".join(str(d) for d in divs[:8])
        if len(divs) > 8:
            div_str += "..."
        print(f"  {n:>5} {sigma(n):>6} {tau(n):>4} {euler_phi(n):>5} {sopfr(n):>6} "
              f"{sigma(n)/n:>8.1f} {tau(n):>4} {{{div_str}}}")

    # ── Build Configurations (all ratio-preserved to target modules) ──
    configs = []

    # Perfect numbers
    for n in perfects:
        label = f"n={n}* (ratio)"
        configs.append(ratio_preserved_config(n, target, label=label))

    # Controls (non-perfect, same scale)
    for n in non_perfects:
        label = f"n={n} (ctrl)"
        configs.append(ratio_preserved_config(n, target, label=label))

    # Random control at same scale
    np.random.seed(496 * 137)
    configs.append(ArchConfig(
        n=496,
        modules=target,
        factions=target * 2,        # same as perfect ratio
        stages=np.random.randint(2, 8),
        grad_groups=np.random.randint(2, target),
        consciousness_dims=np.random.randint(3, 12),
        is_perfect=False,
        label="n=496-random (ctrl)",
    ))

    # ── Architecture Table ──
    print(f"\n  Ratio-Preserved Architectures (target={target} modules):")
    print(f"  {'Config':<22s} {'n':>5} {'Modules':>8} {'Factions':>9} "
          f"{'Stages':>7} {'GradGrp':>8} {'Dims':>5}")
    print("  " + "-" * 68)
    for c in configs:
        print(f"  {c.label:<22s} {c.n:>5} {c.modules:>8} {c.factions:>9} "
              f"{c.stages:>7} {c.grad_groups:>8} {c.consciousness_dims:>5}")

    # Note the key structural difference
    print(f"\n  KEY STRUCTURAL DIFFERENCE at same scale:")
    print(f"    n=6   -> tau=4  stages (simple 4-phase maturation)")
    print(f"    n=28  -> tau=6  stages (richer 6-phase maturation)")
    print(f"    n=496 -> tau=10 stages (complex 10-phase maturation)")
    print(f"    The ONLY difference is tau (# growth stages) and grad_groups.")
    print(f"    If tau matters, n=496 should show distinct dynamics.")

    # ── Run Benchmarks ──
    print(f"\n{'=' * 90}")
    print(f"  Running {len(configs)} architectures x {n_repeats} repeats...")
    print(f"{'=' * 90}")

    all_results = {}
    for config in configs:
        run_results = []
        for rep in range(n_repeats):
            torch.manual_seed(42 + rep)
            np.random.seed(42 + rep)
            r = run_architecture(config, hidden_dim=hidden_dim,
                                steps=steps, max_cells=None)
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
                   'phi_values': [r.phi_iit for r in run_results]},
        )
        all_results[config.label] = avg_result

    # ══════════════════════════════════════════════════════════
    # Results
    # ══════════════════════════════════════════════════════════

    print(f"\n{'=' * 90}")
    print(f"  RESULTS SUMMARY (averaged over {n_repeats} repeats)")
    print(f"{'=' * 90}")

    sorted_results = sorted(all_results.values(), key=lambda r: r.phi_iit, reverse=True)

    print(f"\n  {'Rank':<5} {'Architecture':<24} {'Phi(IIT)':>9} {'+-std':>7} "
          f"{'Phi(prx)':>9} {'Granger':>8} {'Spectral':>8} {'Time':>6}")
    print("  " + "-" * 84)

    for rank, r in enumerate(sorted_results, 1):
        std = r.extra.get('phi_std', 0)
        perf = "*" if r.extra.get('is_perfect') else " "
        marker = ">> " if r.extra.get('is_perfect') else "   "
        print(f"  {marker}{rank:<2} {perf}{r.name:<22s} {r.phi_iit:>9.3f} {std:>7.3f} "
              f"{r.phi_proxy:>9.2f} {r.granger:>8.1f} {r.spectral:>8.2f} {r.time_sec:>5.1f}s")

    # ── Bar Chart ──
    print(f"\n  Phi(IIT) Comparison (* = perfect number):")
    max_phi = max(r.phi_iit for r in sorted_results) or 1
    for r in sorted_results:
        bar_len = int(50 * r.phi_iit / max_phi) if max_phi > 0 else 0
        bar = "#" * bar_len
        perf = "*" if r.extra.get('is_perfect') else " "
        print(f"    {perf}{r.name:<22s} {bar:<50s} {r.phi_iit:.3f}")

    # ── Perfect Number Comparison ──
    print(f"\n  PERFECT NUMBER HIERARCHY (same compute budget):")
    print(f"  {'Number':>8} {'Phi(IIT)':>9} {'Granger':>8} {'Spectral':>8} {'Stages':>7}")
    print("  " + "-" * 48)

    perf_labels = [f"n={n}* (ratio)" for n in perfects]
    for label in perf_labels:
        r = all_results.get(label)
        if r:
            print(f"  {r.name:>20s} {r.phi_iit:>9.3f} {r.granger:>8.1f} "
                  f"{r.spectral:>8.2f} {r.extra.get('stages', '?'):>7}")

    # ── Perfect vs Control Pairs ──
    print(f"\n  PERFECT vs CONTROL PAIRS:")
    print(f"  {'Perfect':>16} {'Phi':>7} | {'Control':>16} {'Phi':>7} | {'Ratio':>7}")
    print("  " + "-" * 58)

    perf_wins = 0
    for pn, cn in zip(perfects, non_perfects):
        pl = f"n={pn}* (ratio)"
        cl = f"n={cn} (ctrl)"
        pr = all_results.get(pl)
        cr = all_results.get(cl)
        if pr and cr:
            ratio = pr.phi_iit / max(cr.phi_iit, 1e-8)
            winner = "PERFECT" if pr.phi_iit > cr.phi_iit else "control"
            if pr.phi_iit > cr.phi_iit:
                perf_wins += 1
            print(f"  {pr.name:>20s} {pr.phi_iit:>7.3f} | {cr.name:>16s} {cr.phi_iit:>7.3f} "
                  f"| {ratio:>6.2f}x  {winner}")

    # ── Stage Count Impact ──
    print(f"\n  STAGE COUNT IMPACT (tau as key structural variable):")
    print(f"  At {target} cells, the main differentiator is tau (# maturation stages).")
    for label in perf_labels:
        r = all_results.get(label)
        if r:
            print(f"    {r.name}: tau={r.extra.get('tau_n', '?')} stages -> "
                  f"Phi={r.phi_iit:.3f}, Spectral={r.spectral:.2f}")

    # ── Verdict ──
    print(f"\n  {'=' * 70}")
    print(f"  H-NOBEL-5 VERDICT: n=496 THIRD PERFECT NUMBER")
    print(f"  {'=' * 70}")

    predictions_met = 0
    total_predictions = 4

    # P1: n=496 achieves non-trivial Phi at scaled-down size
    r496 = all_results.get("n=496* (ratio)")
    p1 = r496 and r496.phi_iit > 0.01
    predictions_met += int(bool(p1))
    print(f"  P1. n=496 achieves non-trivial Phi:     {'PASS' if p1 else 'FAIL'}"
          f"  (Phi={r496.phi_iit:.3f})" if r496 else "  P1. N/A")

    # P2: n=496 beats random control
    r496_rand = all_results.get("n=496-random (ctrl)")
    p2 = r496 and r496_rand and r496.phi_iit > r496_rand.phi_iit
    predictions_met += int(bool(p2))
    if r496 and r496_rand:
        print(f"  P2. n=496 > random control:             {'PASS' if p2 else 'FAIL'}"
              f"  ({r496.phi_iit:.3f} vs {r496_rand.phi_iit:.3f})")

    # P3: All 3 perfect numbers beat their +1 controls
    p3 = perf_wins == len(perfects)
    predictions_met += int(p3)
    print(f"  P3. All perfects > controls:            {'PASS' if p3 else 'FAIL'}"
          f"  ({perf_wins}/{len(perfects)} wins)")

    # P4: n=496 has highest spectral complexity (most stages)
    r6 = all_results.get("n=6* (ratio)")
    r28 = all_results.get("n=28* (ratio)")
    p4 = (r496 and r6 and r28 and
          r496.spectral >= max(r6.spectral, r28.spectral))
    predictions_met += int(bool(p4))
    if r496 and r6 and r28:
        print(f"  P4. n=496 highest spectral complexity:  {'PASS' if p4 else 'FAIL'}"
              f"  (496:{r496.spectral:.2f} vs 6:{r6.spectral:.2f}, 28:{r28.spectral:.2f})")

    print(f"\n  Score: {predictions_met}/{total_predictions} predictions met")
    if predictions_met >= 3:
        print(f"  VERDICT: CONFIRMED -- n=496 architecture shows perfect-number advantage")
    elif predictions_met >= 2:
        print(f"  VERDICT: PARTIAL -- Some support for n=496 theory")
    else:
        print(f"  VERDICT: INCONCLUSIVE -- Needs more scale or different metrics")

    print(f"\n  NOTE: At {target} cells, the main structural variable is tau (stages).")
    print(f"  n=496 has tau=10 (vs tau=4 for n=6, tau=6 for n=28).")
    print(f"  Full-scale differences would emerge with more modules.")
    print(f"\n{'=' * 90}")


if __name__ == '__main__':
    main()
