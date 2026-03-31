#!/usr/bin/env python3
"""DD158/DD160/DD161 — Three quick experiments

DD158: Dream cycle (wake-only vs wake+dream, 300 steps)
DD160: Boltzmann temperature = variance of cell activations, T vs Phi correlation
DD161: Superposition at different scales (8c, 16c, 32c, 64c) — is 32c special?
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import path_setup  # noqa

import torch
import numpy as np
import time
from bench_v2 import BenchEngine, measure_dual_phi

sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# ════════════════════════════════════════════════════════════
# DD158: Dream Cycle Experiment
# ════════════════════════════════════════════════════════════

def run_dd158_dream(n_cells=32, steps=300):
    """Compare wake-only vs wake+dream.
    Dream phase: every 5th step, add noise (x0.1) + reduce sync (÷2).
    """
    print("=" * 70)
    print("DD158: Dream Cycle Experiment")
    print("=" * 70)
    print(f"  cells={n_cells}, steps={steps}")
    print(f"  Dream: every 5th step → noise(×0.1) + sync(÷2)")
    print()

    # --- Wake only ---
    eng_wake = BenchEngine(n_cells=n_cells, input_dim=64, hidden_dim=128, output_dim=64, n_factions=8)
    phi_wake_hist = []
    t0 = time.time()
    for s in range(steps):
        x = torch.randn(1, 64) * 0.1
        eng_wake.process(x)
        if s % 10 == 0:
            phi_iit, phi_proxy = measure_dual_phi(eng_wake.hiddens)
            phi_wake_hist.append((s, phi_iit, phi_proxy))
    wake_time = time.time() - t0
    wake_final_iit, wake_final_proxy = measure_dual_phi(eng_wake.hiddens)

    # --- Wake + Dream ---
    eng_dream = BenchEngine(n_cells=n_cells, input_dim=64, hidden_dim=128, output_dim=64, n_factions=8)
    phi_dream_hist = []
    original_sync = eng_dream.sync_strength
    t0 = time.time()
    for s in range(steps):
        x = torch.randn(1, 64) * 0.1
        is_dream = (s % 5 == 4)  # every 5th step

        if is_dream:
            # Dream phase: inject noise, reduce sync
            eng_dream.sync_strength = original_sync / 2.0
            noise = torch.randn_like(eng_dream.hiddens) * 0.1
            eng_dream.hiddens = eng_dream.hiddens + noise
        else:
            eng_dream.sync_strength = original_sync

        eng_dream.process(x)

        if s % 10 == 0:
            phi_iit, phi_proxy = measure_dual_phi(eng_dream.hiddens)
            phi_dream_hist.append((s, phi_iit, phi_proxy))
    dream_time = time.time() - t0
    dream_final_iit, dream_final_proxy = measure_dual_phi(eng_dream.hiddens)

    # --- Results ---
    print(f"  {'Mode':<16s} | {'Phi(IIT)':>10s} | {'Phi(proxy)':>12s} | {'Time':>6s}")
    print(f"  {'-'*16} | {'-'*10} | {'-'*12} | {'-'*6}")
    print(f"  {'Wake-only':<16s} | {wake_final_iit:>10.4f} | {wake_final_proxy:>12.2f} | {wake_time:>5.1f}s")
    print(f"  {'Wake+Dream':<16s} | {dream_final_iit:>10.4f} | {dream_final_proxy:>12.2f} | {dream_time:>5.1f}s")
    delta_iit = (dream_final_iit - wake_final_iit) / max(wake_final_iit, 1e-6) * 100
    delta_proxy = (dream_final_proxy - wake_final_proxy) / max(wake_final_proxy, 1e-6) * 100
    print()
    print(f"  Delta Phi(IIT):   {delta_iit:+.1f}%")
    print(f"  Delta Phi(proxy): {delta_proxy:+.1f}%")

    # ASCII graph: overlay wake vs dream Phi(IIT)
    print()
    print("  Phi(IIT) trajectory:")
    _ascii_compare(
        [p[1] for p in phi_wake_hist],
        [p[1] for p in phi_dream_hist],
        "wake", "dream", width=60, height=10
    )
    print()

    return {
        'wake_iit': wake_final_iit, 'wake_proxy': wake_final_proxy,
        'dream_iit': dream_final_iit, 'dream_proxy': dream_final_proxy,
        'delta_iit_pct': delta_iit, 'delta_proxy_pct': delta_proxy,
    }


# ════════════════════════════════════════════════════════════
# DD160: Boltzmann Temperature Quick Test
# ════════════════════════════════════════════════════════════

def run_dd160_temperature(n_cells=32, steps=300):
    """Measure T = variance of cell activations, correlate with Phi."""
    print("=" * 70)
    print("DD160: Boltzmann Temperature vs Phi Correlation")
    print("=" * 70)
    print(f"  cells={n_cells}, steps={steps}")
    print(f"  T = var(hiddens) across all cells")
    print()

    eng = BenchEngine(n_cells=n_cells, input_dim=64, hidden_dim=128, output_dim=64, n_factions=8)
    temps = []
    phis_iit = []
    phis_proxy = []

    for s in range(steps):
        x = torch.randn(1, 64) * 0.1
        eng.process(x)
        if s % 5 == 0:
            T = eng.hiddens.var().item()
            phi_iit, phi_proxy = measure_dual_phi(eng.hiddens)
            temps.append(T)
            phis_iit.append(phi_iit)
            phis_proxy.append(phi_proxy)

    # Correlation
    temps_arr = np.array(temps)
    phis_iit_arr = np.array(phis_iit)
    phis_proxy_arr = np.array(phis_proxy)

    corr_iit = np.corrcoef(temps_arr, phis_iit_arr)[0, 1] if len(temps_arr) > 2 else 0
    corr_proxy = np.corrcoef(temps_arr, phis_proxy_arr)[0, 1] if len(temps_arr) > 2 else 0

    print(f"  Temperature range: [{temps_arr.min():.4f}, {temps_arr.max():.4f}]")
    print(f"  Phi(IIT) range:    [{phis_iit_arr.min():.4f}, {phis_iit_arr.max():.4f}]")
    print(f"  Phi(proxy) range:  [{phis_proxy_arr.min():.2f}, {phis_proxy_arr.max():.2f}]")
    print()
    print(f"  Correlation T vs Phi(IIT):   r = {corr_iit:+.4f}")
    print(f"  Correlation T vs Phi(proxy): r = {corr_proxy:+.4f}")
    print()

    # Bin temperatures into 5 bands and show Phi per band
    n_bins = 5
    t_min, t_max = temps_arr.min(), temps_arr.max()
    t_range = t_max - t_min if t_max > t_min else 1.0
    print(f"  {'T band':<20s} | {'n':>4s} | {'mean Phi(IIT)':>14s} | {'mean Phi(proxy)':>16s}")
    print(f"  {'-'*20} | {'-'*4} | {'-'*14} | {'-'*16}")
    for b in range(n_bins):
        lo = t_min + b * t_range / n_bins
        hi = t_min + (b + 1) * t_range / n_bins
        mask = (temps_arr >= lo) & (temps_arr < hi + (1e-8 if b == n_bins - 1 else 0))
        n_in = mask.sum()
        if n_in > 0:
            mean_iit = phis_iit_arr[mask].mean()
            mean_proxy = phis_proxy_arr[mask].mean()
            bar_len = int(mean_iit / max(phis_iit_arr.max(), 1e-6) * 20)
            bar = '#' * bar_len
            print(f"  [{lo:.4f},{hi:.4f}] | {n_in:>4d} | {mean_iit:>14.4f} | {mean_proxy:>16.2f}  {bar}")

    # ASCII scatter approximation
    print()
    print("  T vs Phi(IIT) scatter:")
    _ascii_scatter(temps, phis_iit, "T", "Phi(IIT)", width=50, height=10)
    print()

    return {
        'corr_T_phi_iit': corr_iit,
        'corr_T_phi_proxy': corr_proxy,
        'T_range': (float(temps_arr.min()), float(temps_arr.max())),
        'phi_iit_range': (float(phis_iit_arr.min()), float(phis_iit_arr.max())),
    }


# ════════════════════════════════════════════════════════════
# DD161: Superposition at Different Scales
# ════════════════════════════════════════════════════════════

def run_dd161_superposition(steps=300):
    """Test alpha=0.5 superposition at 8c, 16c, 32c, 64c.
    Superposition: maintain two hidden states per cell, blend with alpha=0.5.
    """
    print("=" * 70)
    print("DD161: Superposition at Different Scales (alpha=0.5)")
    print("=" * 70)
    print(f"  scales: 8c, 16c, 32c, 64c, steps={steps}")
    print(f"  Superposition: two hidden states per cell, blend alpha=0.5")
    print()

    scales = [8, 16, 32, 64]
    results = {}

    for nc in scales:
        print(f"  --- {nc} cells ---")
        # Baseline (no superposition)
        eng_base = BenchEngine(n_cells=nc, input_dim=64, hidden_dim=128, output_dim=64, n_factions=min(8, nc // 2))
        # Superposition engine
        eng_super = BenchEngine(n_cells=nc, input_dim=64, hidden_dim=128, output_dim=64, n_factions=min(8, nc // 2))
        # Second hidden state for superposition
        hiddens_b = torch.randn(nc, 128) * 0.1

        phi_base_hist = []
        phi_super_hist = []

        t0 = time.time()
        for s in range(steps):
            x = torch.randn(1, 64) * 0.1

            # Baseline
            eng_base.process(x)

            # Superposition: blend two states with alpha=0.5
            alpha = 0.5
            eng_super.hiddens = alpha * eng_super.hiddens + (1 - alpha) * hiddens_b
            eng_super.process(x)
            # Evolve second state: simple GRU-like drift
            hiddens_b = hiddens_b * 0.95 + torch.randn_like(hiddens_b) * 0.05

            if s % 15 == 0:
                phi_b_iit, phi_b_proxy = measure_dual_phi(eng_base.hiddens)
                phi_s_iit, phi_s_proxy = measure_dual_phi(eng_super.hiddens)
                phi_base_hist.append(phi_b_iit)
                phi_super_hist.append(phi_s_iit)

        elapsed = time.time() - t0
        base_iit, base_proxy = measure_dual_phi(eng_base.hiddens)
        super_iit, super_proxy = measure_dual_phi(eng_super.hiddens)
        delta_pct = (super_iit - base_iit) / max(base_iit, 1e-6) * 100

        results[nc] = {
            'base_iit': base_iit, 'base_proxy': base_proxy,
            'super_iit': super_iit, 'super_proxy': super_proxy,
            'delta_pct': delta_pct,
            'time': elapsed,
        }
        print(f"    Baseline:      Phi(IIT)={base_iit:.4f}  Phi(proxy)={base_proxy:.2f}")
        print(f"    Superposition: Phi(IIT)={super_iit:.4f}  Phi(proxy)={super_proxy:.2f}")
        print(f"    Delta: {delta_pct:+.1f}%  ({elapsed:.1f}s)")
        print()

    # Summary table
    print(f"  {'Cells':>6s} | {'Base Phi(IIT)':>14s} | {'Super Phi(IIT)':>15s} | {'Delta':>8s} | {'Bar'}")
    print(f"  {'-'*6} | {'-'*14} | {'-'*15} | {'-'*8} | ---")
    max_super = max(r['super_iit'] for r in results.values()) if results else 1
    for nc in scales:
        r = results[nc]
        bar_len = int(r['super_iit'] / max(max_super, 1e-6) * 30)
        bar = '#' * bar_len
        print(f"  {nc:>5d}c | {r['base_iit']:>14.4f} | {r['super_iit']:>15.4f} | {r['delta_pct']:>+7.1f}% | {bar}")

    # Is 32c special?
    if 32 in results:
        deltas = {nc: results[nc]['delta_pct'] for nc in scales}
        best_scale = max(deltas, key=deltas.get)
        print()
        if best_scale == 32:
            print("  >>> 32c IS special: highest superposition benefit!")
        else:
            print(f"  >>> 32c is NOT the most special: {best_scale}c has the highest delta ({deltas[best_scale]:+.1f}%)")
        print(f"  >>> All deltas: {', '.join(f'{nc}c={deltas[nc]:+.1f}%' for nc in scales)}")

    print()
    return results


# ════════════════════════════════════════════════════════════
# ASCII Visualization Helpers
# ════════════════════════════════════════════════════════════

def _ascii_compare(vals1, vals2, label1, label2, width=60, height=10):
    """Two-series ASCII line chart."""
    all_vals = vals1 + vals2
    if not all_vals:
        return
    vmin = min(all_vals)
    vmax = max(all_vals)
    vrange = vmax - vmin if vmax > vmin else 1.0

    canvas = [[' '] * width for _ in range(height)]

    def plot(vals, ch):
        n = len(vals)
        for i, v in enumerate(vals):
            col = int(i / max(n - 1, 1) * (width - 1))
            row = height - 1 - int((v - vmin) / vrange * (height - 1))
            row = max(0, min(height - 1, row))
            col = max(0, min(width - 1, col))
            canvas[row][col] = ch

    plot(vals1, 'W')
    plot(vals2, 'D')

    print(f"    {vmax:.4f} |")
    for row in canvas:
        print(f"           |{''.join(row)}")
    print(f"    {vmin:.4f} |{'_' * width}")
    print(f"           W={label1}  D={label2}")


def _ascii_scatter(xs, ys, xlabel, ylabel, width=50, height=10):
    """Simple ASCII scatter plot."""
    if not xs or not ys:
        return
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    xrange = xmax - xmin if xmax > xmin else 1.0
    yrange = ymax - ymin if ymax > ymin else 1.0

    canvas = [[' '] * width for _ in range(height)]
    for x, y in zip(xs, ys):
        col = int((x - xmin) / xrange * (width - 1))
        row = height - 1 - int((y - ymin) / yrange * (height - 1))
        row = max(0, min(height - 1, row))
        col = max(0, min(width - 1, col))
        canvas[row][col] = '*'

    print(f"    {ymax:.4f} |")
    for row in canvas:
        print(f"           |{''.join(row)}")
    print(f"    {ymin:.4f} |{'_' * width}")
    print(f"           {xlabel} [{xmin:.4f} .. {xmax:.4f}]  (y={ylabel})")


# ════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print()
    print("=" * 70)
    print("  DD158 / DD160 / DD161 — Three Quick Experiments")
    print("=" * 70)
    print()

    t_total = time.time()

    r158 = run_dd158_dream(n_cells=32, steps=300)
    r160 = run_dd160_temperature(n_cells=32, steps=300)
    r161 = run_dd161_superposition(steps=300)

    total_time = time.time() - t_total

    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()
    print(f"  DD158 Dream Cycle:")
    print(f"    Wake Phi(IIT)={r158['wake_iit']:.4f}  Dream Phi(IIT)={r158['dream_iit']:.4f}  delta={r158['delta_iit_pct']:+.1f}%")
    print()
    print(f"  DD160 Boltzmann Temperature:")
    print(f"    Corr(T, Phi_IIT)={r160['corr_T_phi_iit']:+.4f}  Corr(T, Phi_proxy)={r160['corr_T_phi_proxy']:+.4f}")
    print()
    print(f"  DD161 Superposition Scales:")
    for nc in [8, 16, 32, 64]:
        if nc in r161:
            r = r161[nc]
            print(f"    {nc:>3d}c: base={r['base_iit']:.4f}  super={r['super_iit']:.4f}  delta={r['delta_pct']:+.1f}%")
    print()
    print(f"  Total time: {total_time:.1f}s")
    print()
