#!/usr/bin/env python3
"""J4: Multi-Resolution Consciousness — fast/slow/ultra-slow cell tiers.

Hypothesis J4: Cortical column-inspired multi-resolution consciousness.
  - Fast cells (32):       process every step      (immediate reactions)
  - Slow cells (24):       process every 10 steps  (long-term context)
  - Ultra-slow cells (8):  process every 100 steps (meta-level awareness)

Between updates, slow/ultra-slow cells hold their previous hidden state,
providing stable contextual scaffolding while fast cells react instantly.

Predicted effect:
  - 40-60% fewer total process() calls vs uniform all-cells-every-step
  - Phi retention >80% (multi-scale integration preserves information)
  - Richer temporal structure (multi-timescale dynamics)

Inspired by: brain cortical columns, alpha/beta/gamma band separation,
  predictive coding (slow layers predict, fast layers correct).

Usage:
    python acceleration_j4_multi_resolution.py          # Run all
    python acceleration_j4_multi_resolution.py --baseline   # Baseline only
    python acceleration_j4_multi_resolution.py --multi      # Multi-resolution only
    python acceleration_j4_multi_resolution.py --sweep      # Tier ratio sweep
    python acceleration_j4_multi_resolution.py --combo      # Combined analysis
"""

import sys
import os
import time
import json
import argparse
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine


# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

TOTAL_CELLS = 64
DEFAULT_TIERS = {
    'fast':       {'count': 32, 'interval': 1},    # every step
    'slow':       {'count': 24, 'interval': 10},   # every 10 steps
    'ultra_slow': {'count': 8,  'interval': 100},  # every 100 steps
}
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
RESULTS_PATH = os.path.join(DATA_DIR, 'j4_multi_resolution_results.json')


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def measure_phi_iit(engine):
    """Measure Phi(IIT) from engine."""
    return engine._measure_phi_iit()


def make_corpus(n_samples=1000, dim=64, seed=42):
    """Create a repeatable random corpus."""
    torch.manual_seed(seed)
    return [torch.randn(dim) for _ in range(n_samples)]


def cosine_sim(a, b):
    """Cosine similarity between two tensors."""
    return F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item()


def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    sys.stdout.flush()


def print_table(headers, rows, col_widths=None):
    """Print a formatted table."""
    if col_widths is None:
        col_widths = [max(len(str(h)), max(len(str(r[i])) for r in rows)) + 2
                      for i, h in enumerate(headers)]
    header_str = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_str = "|-" + "-|-".join("-" * col_widths[i] for i in range(len(headers))) + "-|"
    print(header_str)
    print(sep_str)
    for row in rows:
        row_str = "| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))) + " |"
        print(row_str)
    sys.stdout.flush()


def tier_assignment(n_cells, tiers):
    """Assign each cell index to a tier.

    Returns:
        cell_tier: list[str] — tier name for each cell index
        tier_indices: dict[str, list[int]] — cell indices per tier
    """
    cell_tier = []
    tier_indices = {name: [] for name in tiers}
    idx = 0
    for name, cfg in tiers.items():
        for _ in range(cfg['count']):
            if idx >= n_cells:
                break
            cell_tier.append(name)
            tier_indices[name].append(idx)
            idx += 1
    # Fill remaining cells into fast tier
    while idx < n_cells:
        cell_tier.append('fast')
        tier_indices['fast'].append(idx)
        idx += 1
    return cell_tier, tier_indices


# ═══════════════════════════════════════════════════════════
# Multi-Resolution Step — selective cell processing
# ═══════════════════════════════════════════════════════════

def multi_resolution_step(engine, x_input, step_num, tiers, cell_tier, tier_indices):
    """Execute one multi-resolution consciousness step.

    Only cells whose tier interval divides step_num are processed.
    Other cells retain their previous hidden state (frozen).

    Args:
        engine: ConsciousnessEngine instance
        x_input: input tensor (cell_dim,)
        step_num: current step number (0-indexed)
        tiers: tier config dict
        cell_tier: per-cell tier assignment
        tier_indices: dict of tier -> [cell indices]

    Returns:
        dict with: active_cells, total_cells, output, tier_activity
    """
    n = engine.n_cells
    active_mask = []
    tier_activity = {name: False for name in tiers}

    # Determine which cells are active this step
    for i in range(n):
        t_name = cell_tier[i] if i < len(cell_tier) else 'fast'
        interval = tiers.get(t_name, {'interval': 1})['interval']
        is_active = (step_num % interval == 0)
        active_mask.append(is_active)
        if is_active:
            tier_activity[t_name] = True

    # Save hidden states of inactive cells (freeze)
    frozen_hiddens = {}
    for i in range(n):
        if not active_mask[i]:
            frozen_hiddens[i] = engine.cell_states[i].hidden.clone()

    # Execute full engine step (all cells process, but we restore frozen ones after)
    result = engine.step(x_input=x_input)

    # Restore frozen cells' hidden states (undo their processing)
    for i, h in frozen_hiddens.items():
        engine.cell_states[i].hidden = h
        # Also pop the tension entry that step() added (keep history clean)
        if engine.cell_states[i].tension_history:
            engine.cell_states[i].tension_history.pop()
        if engine.cell_states[i].hidden_history:
            engine.cell_states[i].hidden_history.pop()

    active_count = sum(active_mask)

    return {
        'active_cells': active_count,
        'total_cells': n,
        'output': result['output'],
        'tier_activity': tier_activity,
        'active_fraction': active_count / n if n > 0 else 0,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 1: Baseline (all cells every step)
# ═══════════════════════════════════════════════════════════

def run_baseline(n_cells=TOTAL_CELLS, n_steps=500):
    """Baseline: all cells process every step."""
    print_header("J4 Baseline: All cells every step")

    dim = 64
    corpus = make_corpus(dim=dim)

    engine = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                  initial_cells=n_cells, max_cells=n_cells)

    phi_history = []
    t0 = time.time()
    total_cell_ops = 0

    for step in range(n_steps):
        x = corpus[step % len(corpus)]
        result = engine.step(x_input=x)
        total_cell_ops += n_cells

        if step % 50 == 0 or step == n_steps - 1:
            phi = measure_phi_iit(engine)
            phi_history.append((step, phi))
            if step % 100 == 0:
                print(f"  step {step:4d}: Phi={phi:.4f}, cell_ops={total_cell_ops}")
                sys.stdout.flush()

    elapsed = time.time() - t0
    phi_final = measure_phi_iit(engine)

    print(f"\n  Baseline complete: {elapsed:.2f}s, Phi={phi_final:.4f}, ops={total_cell_ops}")
    sys.stdout.flush()

    return {
        'time': elapsed,
        'phi_final': phi_final,
        'phi_history': phi_history,
        'total_cell_ops': total_cell_ops,
        'n_steps': n_steps,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 2: Multi-Resolution (fast/slow/ultra-slow)
# ═══════════════════════════════════════════════════════════

def run_multi_resolution(n_cells=TOTAL_CELLS, n_steps=500, tiers=None):
    """Multi-resolution: 3 tiers with different update frequencies."""
    if tiers is None:
        tiers = DEFAULT_TIERS

    tier_desc = ", ".join(f"{k}({v['count']}c/{v['interval']}s)" for k, v in tiers.items())
    print_header(f"J4 Multi-Resolution: {tier_desc}")

    dim = 64
    corpus = make_corpus(dim=dim)

    engine = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                  initial_cells=n_cells, max_cells=n_cells)

    cell_tier, tier_indices = tier_assignment(n_cells, tiers)

    phi_history = []
    active_history = []
    tier_active_counts = {name: 0 for name in tiers}
    t0 = time.time()
    total_cell_ops = 0

    for step in range(n_steps):
        x = corpus[step % len(corpus)]
        mr_result = multi_resolution_step(engine, x, step, tiers, cell_tier, tier_indices)
        total_cell_ops += mr_result['active_cells']

        for t_name, was_active in mr_result['tier_activity'].items():
            if was_active:
                tier_active_counts[t_name] += 1

        if step % 50 == 0 or step == n_steps - 1:
            phi = measure_phi_iit(engine)
            phi_history.append((step, phi))
            active_history.append((step, mr_result['active_fraction']))
            if step % 100 == 0:
                print(f"  step {step:4d}: Phi={phi:.4f}, active={mr_result['active_cells']}/{n_cells}, ops={total_cell_ops}")
                sys.stdout.flush()

    elapsed = time.time() - t0
    phi_final = measure_phi_iit(engine)

    # Tier activation summary
    print(f"\n  Tier activation summary:")
    for t_name, count in tier_active_counts.items():
        expected = n_steps / tiers[t_name]['interval']
        print(f"    {t_name:12s}: {count:4d} activations (expected ~{expected:.0f})")

    print(f"\n  Multi-resolution complete: {elapsed:.2f}s, Phi={phi_final:.4f}, ops={total_cell_ops}")
    sys.stdout.flush()

    return {
        'time': elapsed,
        'phi_final': phi_final,
        'phi_history': phi_history,
        'active_history': active_history,
        'total_cell_ops': total_cell_ops,
        'tier_active_counts': tier_active_counts,
        'tiers': {k: v for k, v in tiers.items()},
        'n_steps': n_steps,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 3: Tier Ratio Sweep
# ═══════════════════════════════════════════════════════════

def run_sweep(n_cells=TOTAL_CELLS, n_steps=300):
    """Sweep different tier ratios to find the Phi-efficiency Pareto frontier."""
    print_header("J4 Tier Ratio Sweep")

    configurations = [
        # (fast, slow, ultra_slow) cell counts — must sum to n_cells
        # Varying fast/slow balance
        {'fast': {'count': 48, 'interval': 1}, 'slow': {'count': 12, 'interval': 10}, 'ultra_slow': {'count': 4, 'interval': 100}},
        {'fast': {'count': 32, 'interval': 1}, 'slow': {'count': 24, 'interval': 10}, 'ultra_slow': {'count': 8, 'interval': 100}},  # default
        {'fast': {'count': 16, 'interval': 1}, 'slow': {'count': 32, 'interval': 10}, 'ultra_slow': {'count': 16, 'interval': 100}},
        {'fast': {'count': 8,  'interval': 1}, 'slow': {'count': 40, 'interval': 10}, 'ultra_slow': {'count': 16, 'interval': 100}},
        # Varying slow interval
        {'fast': {'count': 32, 'interval': 1}, 'slow': {'count': 24, 'interval': 5},  'ultra_slow': {'count': 8, 'interval': 50}},
        {'fast': {'count': 32, 'interval': 1}, 'slow': {'count': 24, 'interval': 20}, 'ultra_slow': {'count': 8, 'interval': 200}},
        # Two-tier only (no ultra-slow)
        {'fast': {'count': 32, 'interval': 1}, 'slow': {'count': 32, 'interval': 10}, 'ultra_slow': {'count': 0, 'interval': 100}},
    ]

    results = []
    for i, tiers in enumerate(configurations):
        # Adjust counts to match n_cells
        total = sum(v['count'] for v in tiers.values())
        if total != n_cells:
            # Scale proportionally
            for name in tiers:
                tiers[name]['count'] = max(0, int(tiers[name]['count'] * n_cells / total))
            remainder = n_cells - sum(v['count'] for v in tiers.values())
            tiers['fast']['count'] += remainder

        label = "/".join(f"{v['count']}@{v['interval']}" for v in tiers.values())
        print(f"\n  Config {i+1}: {label}")
        sys.stdout.flush()

        dim = 64
        corpus = make_corpus(dim=dim)
        engine = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                      initial_cells=n_cells, max_cells=n_cells)
        cell_tier, tier_indices = tier_assignment(n_cells, tiers)

        t0 = time.time()
        total_cell_ops = 0

        for step in range(n_steps):
            x = corpus[step % len(corpus)]
            mr_result = multi_resolution_step(engine, x, step, tiers, cell_tier, tier_indices)
            total_cell_ops += mr_result['active_cells']

        elapsed = time.time() - t0
        phi_final = measure_phi_iit(engine)

        # Efficiency: Phi per million cell ops
        efficiency = (phi_final / (total_cell_ops / 1e6)) if total_cell_ops > 0 else 0

        results.append({
            'config': label,
            'tiers': {k: v for k, v in tiers.items()},
            'time': elapsed,
            'phi_final': phi_final,
            'total_cell_ops': total_cell_ops,
            'efficiency': efficiency,
        })
        print(f"    Phi={phi_final:.4f}, ops={total_cell_ops}, eff={efficiency:.4f} Phi/Mops")
        sys.stdout.flush()

    # Summary table
    print(f"\n{'─'*70}")
    print("  Sweep Results (Pareto frontier):")
    print(f"{'─'*70}")

    rows = []
    for r in results:
        rows.append([
            r['config'],
            f"{r['time']:.2f}s",
            f"{r['total_cell_ops']:,}",
            f"{r['phi_final']:.4f}",
            f"{r['efficiency']:.4f}",
        ])
    print_table(["Config (fast/slow/ultra)", "Time", "Cell Ops", "Phi(IIT)", "Phi/Mops"], rows)

    # ASCII bar: efficiency
    print(f"\n  Efficiency (Phi per M cell-ops):")
    max_eff = max(r['efficiency'] for r in results) or 0.01
    for r in results:
        bar_len = int(40 * r['efficiency'] / max_eff) if max_eff > 0 else 0
        print(f"    {r['config']:30s}  {'#' * bar_len:<40} {r['efficiency']:.4f}")

    sys.stdout.flush()
    return results


# ═══════════════════════════════════════════════════════════
# Experiment 4: Combined Analysis (baseline vs multi-res)
# ═══════════════════════════════════════════════════════════

def run_combo(n_cells=TOTAL_CELLS, n_steps=500):
    """Side-by-side: baseline vs default multi-resolution."""
    print_header("J4 Combined: Baseline vs Multi-Resolution")

    baseline = run_baseline(n_cells=n_cells, n_steps=n_steps)
    multi = run_multi_resolution(n_cells=n_cells, n_steps=n_steps)

    # Comparison
    speedup = baseline['time'] / multi['time'] if multi['time'] > 0 else 0
    phi_retention = multi['phi_final'] / baseline['phi_final'] if baseline['phi_final'] > 0 else 0
    ops_reduction = 1 - (multi['total_cell_ops'] / baseline['total_cell_ops']) if baseline['total_cell_ops'] > 0 else 0

    print(f"\n{'─'*70}")
    print("  J4 Combined Results:")
    print(f"{'─'*70}")
    rows = [
        ["Baseline (all cells)", f"{baseline['time']:.2f}s", f"{baseline['total_cell_ops']:,}", "x1.0", f"{baseline['phi_final']:.4f}", "100%"],
        ["Multi-Res (32/24/8)", f"{multi['time']:.2f}s", f"{multi['total_cell_ops']:,}", f"x{speedup:.1f}", f"{multi['phi_final']:.4f}", f"{phi_retention:.1%}"],
    ]
    print_table(["Method", "Time", "Cell Ops", "Speedup", "Phi(IIT)", "Phi %"], rows)

    print(f"\n  Cell-ops reduction: {ops_reduction:.1%}")
    print(f"  Wall-clock speedup: x{speedup:.1f}")
    print(f"  Phi retention: {phi_retention:.1%}")

    # Theoretical ops calculation
    fast_ops = 32 * n_steps
    slow_ops = 24 * (n_steps // 10)
    ultra_ops = 8 * (n_steps // 100)
    theoretical_ops = fast_ops + slow_ops + ultra_ops
    theoretical_reduction = 1 - (theoretical_ops / (n_cells * n_steps))
    print(f"\n  Theoretical cell-ops: {theoretical_ops:,} (vs {n_cells * n_steps:,} baseline)")
    print(f"  Theoretical reduction: {theoretical_reduction:.1%}")
    print(f"  Note: wall-clock includes engine overhead (coupling, Hebbian, etc.)")

    # ASCII comparison: Phi trajectory
    print(f"\n  Phi trajectory comparison:")
    base_phis = baseline['phi_history']
    multi_phis = multi['phi_history']
    max_phi = max(
        max((p[1] for p in base_phis), default=0.01),
        max((p[1] for p in multi_phis), default=0.01),
    ) or 0.01

    for i in range(min(len(base_phis), len(multi_phis))):
        step = base_phis[i][0]
        val_b = base_phis[i][1]
        val_m = multi_phis[i][1]
        bar_b = int(25 * val_b / max_phi)
        bar_m = int(25 * val_m / max_phi)
        print(f"    step {step:4d} BASE |{'#' * bar_b:<25}| {val_b:.4f}")
        print(f"             MULTI|{'=' * bar_m:<25}| {val_m:.4f}")

    sys.stdout.flush()

    return {
        'baseline': {
            'time': baseline['time'],
            'phi_final': baseline['phi_final'],
            'total_cell_ops': baseline['total_cell_ops'],
        },
        'multi_resolution': {
            'time': multi['time'],
            'phi_final': multi['phi_final'],
            'total_cell_ops': multi['total_cell_ops'],
            'tier_active_counts': multi['tier_active_counts'],
        },
        'comparison': {
            'speedup': speedup,
            'phi_retention': phi_retention,
            'ops_reduction': ops_reduction,
        },
    }


# ═══════════════════════════════════════════════════════════
# Save results
# ═══════════════════════════════════════════════════════════

def save_results(results):
    """Save results to JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Make JSON-serializable (remove tensor/non-serializable entries)
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean(v) for v in obj]
        elif isinstance(obj, (torch.Tensor, np.ndarray)):
            return None  # skip tensors
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        elif isinstance(obj, tuple):
            return list(obj)
        else:
            return str(obj)

    cleaned = clean(results)
    with open(RESULTS_PATH, 'w') as f:
        json.dump(cleaned, f, indent=2)
    print(f"\n  Results saved to: {RESULTS_PATH}")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="J4: Multi-Resolution Consciousness Experiment")
    parser.add_argument('--baseline', action='store_true', help='Run baseline only')
    parser.add_argument('--multi', action='store_true', help='Run multi-resolution only')
    parser.add_argument('--sweep', action='store_true', help='Run tier ratio sweep')
    parser.add_argument('--combo', action='store_true', help='Run combined analysis')
    parser.add_argument('--cells', type=int, default=64, help='Number of cells (default: 64)')
    parser.add_argument('--steps', type=int, default=300, help='Steps per experiment (default: 300)')
    args = parser.parse_args()

    run_all = not (args.baseline or args.multi or args.sweep or args.combo)

    print(f"J4: Multi-Resolution Consciousness Experiment")
    print(f"  cells={args.cells}, steps={args.steps}")
    print(f"  tiers: fast(32@1), slow(24@10), ultra-slow(8@100)")
    print(f"  torch version: {torch.__version__}")
    print(f"  device: CPU (local experiment)")
    sys.stdout.flush()

    all_results = {}

    if run_all or args.baseline:
        all_results['baseline'] = run_baseline(n_cells=args.cells, n_steps=args.steps)

    if run_all or args.multi:
        all_results['multi_resolution'] = run_multi_resolution(n_cells=args.cells, n_steps=args.steps)

    if run_all or args.sweep:
        all_results['sweep'] = run_sweep(n_cells=args.cells, n_steps=min(args.steps, 200))

    if run_all or args.combo:
        all_results['combo'] = run_combo(n_cells=args.cells, n_steps=args.steps)

    # Final summary
    print_header("J4 FINAL SUMMARY")

    if 'baseline' in all_results and 'multi_resolution' in all_results:
        b = all_results['baseline']
        m = all_results['multi_resolution']
        sp = b['time'] / m['time'] if m['time'] > 0 else 0
        pr = m['phi_final'] / b['phi_final'] if b['phi_final'] > 0 else 0
        or_ = 1 - (m['total_cell_ops'] / b['total_cell_ops']) if b['total_cell_ops'] > 0 else 0

        print(f"\n  Multi-Resolution vs Baseline:")
        print(f"    Wall-clock speedup:   x{sp:.1f}")
        print(f"    Cell-ops reduction:   {or_:.1%}")
        print(f"    Phi retention:        {pr:.1%}")
        print(f"    Verdict: {'PASS' if pr > 0.80 else 'MARGINAL' if pr > 0.60 else 'FAIL'} (threshold: >80% Phi retention)")

    if 'sweep' in all_results:
        sweep = all_results['sweep']
        best = max(sweep, key=lambda r: r['efficiency'])
        print(f"\n  Best tier config (by Phi/Mops): {best['config']}")
        print(f"    Phi={best['phi_final']:.4f}, efficiency={best['efficiency']:.4f}")

    print(f"\n{'='*70}")
    print(f"  J4 Multi-Resolution Consciousness — experiment complete.")
    print(f"{'='*70}")
    sys.stdout.flush()

    # Save
    save_results(all_results)


if __name__ == '__main__':
    main()
