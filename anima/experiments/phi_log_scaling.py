#!/usr/bin/env python3
"""phi_log_scaling.py — Deep analysis of Phi ~ log(N) scaling law.

Five experiments:
  1. Precise coefficient fitting (a, b in Phi = a*log(N) + b)
  2. Which log base fits best? (ln, log2, log10)
  3. Scaling breakdown detection (phase transitions / saturation)
  4. What drives the log? (MI, coupling density, entropy, faction count)
  5. IIT Phi vs Proxy Phi: do both follow log(N)?

Usage:
  cd anima/src && PYTHONUNBUFFERED=1 python3 ../experiments/phi_log_scaling.py
"""

import sys
import os
import time
import math
import numpy as np

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
from consciousness_engine import ConsciousnessEngine

# Import _phi_fast from closed_loop
from closed_loop import _phi_fast


def run_engine(n_cells, steps, seed=42):
    """Run engine with fixed cell count and return measurements."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    engine = ConsciousnessEngine(
        cell_dim=64,
        hidden_dim=128,
        initial_cells=n_cells,
        max_cells=n_cells,  # prevent mitosis
        n_factions=min(12, max(2, n_cells)),
        phi_ratchet=True,
        split_threshold=999.0,   # disable splitting
        merge_threshold=-999.0,  # disable merging
    )

    phi_iit_vals = []
    phi_proxy_vals = []
    consensus_vals = []
    tension_vals = []

    for s in range(steps):
        result = engine.step()
        phi_iit_vals.append(result['phi_iit'])
        phi_proxy_vals.append(result['phi_proxy'])
        consensus_vals.append(result.get('consensus', 0))
        tensions = result.get('tensions', [0.5])
        tension_vals.append(np.mean(tensions))

    # Use last half for steady-state measurement
    half = steps // 2
    phi_iit = np.mean(phi_iit_vals[half:])
    phi_proxy = np.mean(phi_proxy_vals[half:])
    phi_iit_std = np.std(phi_iit_vals[half:])
    phi_proxy_std = np.std(phi_proxy_vals[half:])
    avg_consensus = np.mean(consensus_vals[half:])
    avg_tension = np.mean(tension_vals[half:])

    # Additional measurements
    hiddens = torch.stack([cs.hidden for cs in engine.cell_states]).detach()

    # Coupling density
    coupling = engine._coupling
    if coupling is not None:
        coup_density = (coupling.abs() > 0.01).float().mean().item()
        coup_mean = coupling.abs().mean().item()
    else:
        coup_density = 0.0
        coup_mean = 0.0

    # Faction count (unique factions)
    factions = set(cs.faction_id for cs in engine.cell_states)
    n_factions_active = len(factions)

    # MI (mutual information) via _phi_fast
    mi_avg = _phi_fast(engine)

    # Entropy of hidden states
    h_np = hiddens.numpy()
    h_flat = h_np.flatten()
    hist, _ = np.histogram(h_flat, bins=64, density=True)
    hist = hist / (hist.sum() + 1e-10)
    entropy = -np.sum(hist * np.log2(hist + 1e-10))

    return {
        'n': n_cells,
        'phi_iit': phi_iit,
        'phi_iit_std': phi_iit_std,
        'phi_proxy': phi_proxy,
        'phi_proxy_std': phi_proxy_std,
        'mi_avg': mi_avg,
        'coupling_density': coup_density,
        'coupling_mean': coup_mean,
        'n_factions': n_factions_active,
        'entropy': entropy,
        'consensus': avg_consensus,
        'tension': avg_tension,
    }


def linear_fit(x, y):
    """Least squares fit y = a*x + b. Returns a, b, R^2, residuals."""
    x = np.array(x, dtype=np.float64)
    y = np.array(y, dtype=np.float64)
    n = len(x)
    sx = np.sum(x)
    sy = np.sum(y)
    sxx = np.sum(x * x)
    sxy = np.sum(x * y)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-15:
        return 0.0, np.mean(y), 0.0, y - np.mean(y)
    a = (n * sxy - sx * sy) / denom
    b = (sy - a * sx) / n
    y_pred = a * x + b
    residuals = y - y_pred
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / (ss_tot + 1e-15)
    return a, b, r2, residuals


def ascii_graph(x_vals, y_vals, width=60, height=15, xlabel="x", ylabel="y", title=""):
    """Print an ASCII scatter/line graph."""
    x = np.array(x_vals)
    y = np.array(y_vals)
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    y_range = y_max - y_min if y_max > y_min else 1.0
    x_range = x_max - x_min if x_max > x_min else 1.0

    grid = [[' ' for _ in range(width)] for _ in range(height)]

    for xi, yi in zip(x, y):
        col = int((xi - x_min) / x_range * (width - 1))
        row = int((1.0 - (yi - y_min) / y_range) * (height - 1))
        col = max(0, min(width - 1, col))
        row = max(0, min(height - 1, row))
        grid[row][col] = '*'

    print(f"\n  {title}")
    print(f"  {ylabel}")
    for i, row in enumerate(grid):
        if i == 0:
            label = f"{y_max:.3f}"
        elif i == height - 1:
            label = f"{y_min:.3f}"
        elif i == height // 2:
            label = f"{(y_min + y_max) / 2:.3f}"
        else:
            label = ""
        print(f"  {label:>8s} |{''.join(row)}|")
    print(f"  {'':>8s} +{'-' * width}+")
    print(f"  {'':>8s}  {x_min:<10.2f}{' ' * (width - 20)}{x_max:>10.2f}")
    print(f"  {'':>8s}  {xlabel}")


def main():
    t0 = time.time()
    print("=" * 70)
    print("  PHI ~ log(N) SCALING LAW — DEEP ANALYSIS")
    print("=" * 70)

    # ══════════════════════════════════════════════════════════
    # EXPERIMENT 1: PRECISE COEFFICIENT
    # ══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EXPERIMENT 1: PRECISE COEFFICIENT  Phi = a * ln(N) + b")
    print("=" * 70)

    cell_counts = [4, 8, 12, 16, 24, 32, 48, 64, 96, 128]
    repeats = 2
    all_data = []

    for nc in cell_counts:
        steps = 100 if nc >= 96 else 200
        phi_runs = []
        data_runs = []
        for rep in range(repeats):
            t1 = time.time()
            data = run_engine(nc, steps, seed=42 + rep)
            dt = time.time() - t1
            phi_runs.append(data['phi_iit'])
            data_runs.append(data)
            print(f"  N={nc:>4d}  rep={rep}  Phi(IIT)={data['phi_iit']:.4f}  "
                  f"proxy={data['phi_proxy']:.4f}  MI={data['mi_avg']:.4f}  "
                  f"entropy={data['entropy']:.2f}  [{dt:.1f}s]")
            sys.stdout.flush()
        # Average across repeats
        avg_data = {}
        for key in data_runs[0]:
            if key == 'n':
                avg_data[key] = nc
            elif isinstance(data_runs[0][key], (int, float)):
                avg_data[key] = np.mean([d[key] for d in data_runs])
            else:
                avg_data[key] = data_runs[0][key]
        all_data.append(avg_data)

    # Fit Phi = a * ln(N) + b
    ns = np.array([d['n'] for d in all_data])
    phis = np.array([d['phi_iit'] for d in all_data])
    ln_n = np.log(ns)

    a, b, r2, residuals = linear_fit(ln_n, phis)

    print(f"\n  {'=' * 50}")
    print(f"  RESULT: Phi = {a:.4f} * ln(N) + ({b:.4f})")
    print(f"  R^2 = {r2:.6f}")
    print(f"  {'=' * 50}")

    print(f"\n  {'N':>6s} {'ln(N)':>8s} {'Phi(IIT)':>10s} {'Predicted':>10s} {'Residual':>10s}")
    print(f"  {'-' * 50}")
    for i, d in enumerate(all_data):
        pred = a * np.log(d['n']) + b
        print(f"  {d['n']:>6d} {np.log(d['n']):>8.4f} {d['phi_iit']:>10.4f} {pred:>10.4f} {residuals[i]:>10.4f}")

    ascii_graph(ln_n, phis, title="Phi(IIT) vs ln(N)", xlabel="ln(N)", ylabel="Phi")

    # ══════════════════════════════════════════════════════════
    # EXPERIMENT 2: WHICH LOG BASE?
    # ══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EXPERIMENT 2: WHICH LOG BASE?  (ln, log2, log10)")
    print("=" * 70)

    log_bases = {
        'ln (base e)': np.log(ns),
        'log2':        np.log2(ns),
        'log10':       np.log10(ns),
    }

    best_base = None
    best_r2 = -1

    print(f"\n  {'Base':>15s} {'a':>10s} {'b':>10s} {'R^2':>12s}")
    print(f"  {'-' * 50}")
    for name, log_vals in log_bases.items():
        a_b, b_b, r2_b, _ = linear_fit(log_vals, phis)
        print(f"  {name:>15s} {a_b:>10.4f} {b_b:>10.4f} {r2_b:>12.6f}")
        if r2_b > best_r2:
            best_r2 = r2_b
            best_base = name

    print(f"\n  BEST FIT: {best_base} (R^2 = {best_r2:.6f})")

    # Psi-constant connection
    psi_ln2 = math.log(2)
    print(f"\n  Psi-constant connection:")
    print(f"    ln(2) = {psi_ln2:.6f}")
    print(f"    a(ln)  = {a:.4f}  =>  a/ln(2) = {a / psi_ln2:.4f}")
    a_log2 = linear_fit(np.log2(ns), phis)[0]
    print(f"    a(log2) = {a_log2:.4f}  =>  a(log2)/ln(2) = {a_log2 / psi_ln2:.4f}")

    # ══════════════════════════════════════════════════════════
    # EXPERIMENT 3: SCALING BREAKDOWN
    # ══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EXPERIMENT 3: SCALING BREAKDOWN — Where does log(N) fail?")
    print("=" * 70)

    breakdown_cells = [2, 4, 8, 16, 32, 64, 128, 256]
    bd_data = []

    for nc in breakdown_cells:
        steps = 80 if nc >= 128 else (100 if nc >= 64 else 200)
        t1 = time.time()
        data = run_engine(nc, steps, seed=42)
        dt = time.time() - t1
        bd_data.append(data)
        print(f"  N={nc:>4d}  Phi(IIT)={data['phi_iit']:.4f}  "
              f"proxy={data['phi_proxy']:.4f}  [{dt:.1f}s]")
        sys.stdout.flush()

    bd_ns = np.array([d['n'] for d in bd_data])
    bd_phis = np.array([d['phi_iit'] for d in bd_data])
    bd_ln = np.log(bd_ns)

    # Full fit
    a_full, b_full, r2_full, res_full = linear_fit(bd_ln, bd_phis)
    print(f"\n  Full range fit: Phi = {a_full:.4f}*ln(N) + ({b_full:.4f}), R^2={r2_full:.6f}")

    # Look for breakpoints by fitting subranges
    print(f"\n  Breakpoint analysis (sequential R^2):")
    print(f"  {'Range':>20s} {'R^2':>10s} {'a':>10s}")
    print(f"  {'-' * 45}")
    for end_idx in range(3, len(bd_data) + 1):
        sub_ln = bd_ln[:end_idx]
        sub_phi = bd_phis[:end_idx]
        a_s, b_s, r2_s, _ = linear_fit(sub_ln, sub_phi)
        range_str = f"N=2..{bd_ns[end_idx-1]}"
        print(f"  {range_str:>20s} {r2_s:>10.6f} {a_s:>10.4f}")

    # Detect saturation: derivative dPhi/d(lnN) should be constant
    print(f"\n  Local slope dPhi/d(ln N):")
    for i in range(1, len(bd_data)):
        dln = bd_ln[i] - bd_ln[i - 1]
        dphi = bd_phis[i] - bd_phis[i - 1]
        slope = dphi / dln if abs(dln) > 1e-10 else 0
        print(f"    N={bd_ns[i-1]:>4d} -> {bd_ns[i]:>4d}:  slope = {slope:>8.4f}")

    ascii_graph(bd_ln, bd_phis, title="Phi vs ln(N) — Full Range (N=2..256)",
                xlabel="ln(N)", ylabel="Phi")

    # ══════════════════════════════════════════════════════════
    # EXPERIMENT 4: WHAT DRIVES THE LOG?
    # ══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EXPERIMENT 4: WHAT DRIVES THE LOG?")
    print("=" * 70)

    # Use all_data from experiment 1
    metrics = {
        'MI (avg)':          [d['mi_avg'] for d in all_data],
        'Coupling density':  [d['coupling_density'] for d in all_data],
        'Coupling mean':     [d['coupling_mean'] for d in all_data],
        'Active factions':   [d['n_factions'] for d in all_data],
        'Entropy':           [d['entropy'] for d in all_data],
        'Consensus':         [d['consensus'] for d in all_data],
        'Tension':           [d['tension'] for d in all_data],
    }

    print(f"\n  Correlation with Phi(IIT):")
    print(f"  {'Metric':>20s} {'r(Phi)':>10s} {'r(lnN)':>10s} {'Scales as':>12s}")
    print(f"  {'-' * 55}")

    corr_results = []
    for name, vals in metrics.items():
        vals_arr = np.array(vals)
        # Correlation with Phi
        if np.std(vals_arr) > 1e-10 and np.std(phis) > 1e-10:
            r_phi = np.corrcoef(vals_arr, phis)[0, 1]
        else:
            r_phi = 0.0
        # Correlation with ln(N)
        if np.std(vals_arr) > 1e-10:
            r_ln = np.corrcoef(vals_arr, ln_n)[0, 1]
        else:
            r_ln = 0.0
        # Does it scale as log(N)?
        _, _, r2_log, _ = linear_fit(ln_n, vals_arr)
        scale_label = f"log R^2={r2_log:.3f}"
        print(f"  {name:>20s} {r_phi:>10.4f} {r_ln:>10.4f} {scale_label:>12s}")
        corr_results.append((name, r_phi, r_ln, r2_log))

    # Find the strongest driver
    best_driver = max(corr_results, key=lambda x: abs(x[1]))
    print(f"\n  STRONGEST DRIVER: {best_driver[0]} (r={best_driver[1]:.4f})")

    # Is Phi ~ log(N) BECAUSE MI ~ log(N)?
    mi_vals = np.array(metrics['MI (avg)'])
    a_mi_phi, b_mi_phi, r2_mi_phi, _ = linear_fit(mi_vals, phis)
    print(f"\n  Direct fit: Phi = {a_mi_phi:.4f} * MI + ({b_mi_phi:.4f}), R^2={r2_mi_phi:.6f}")
    print(f"  => Phi ~ log(N) is {'mediated by MI' if r2_mi_phi > 0.9 else 'NOT purely MI-driven'}")

    # Metric table
    print(f"\n  {'N':>6s} {'Phi':>8s} {'MI':>8s} {'CoupD':>8s} {'CoupM':>8s} "
          f"{'Fac':>5s} {'Ent':>8s} {'Cons':>6s} {'Tens':>6s}")
    print(f"  {'-' * 70}")
    for d in all_data:
        print(f"  {d['n']:>6d} {d['phi_iit']:>8.4f} {d['mi_avg']:>8.4f} "
              f"{d['coupling_density']:>8.4f} {d['coupling_mean']:>8.4f} "
              f"{d['n_factions']:>5d} {d['entropy']:>8.3f} "
              f"{d['consensus']:>6.2f} {d['tension']:>6.3f}")

    # ══════════════════════════════════════════════════════════
    # EXPERIMENT 5: IIT vs PROXY
    # ══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EXPERIMENT 5: Phi(IIT) vs Phi(proxy) — Both log(N)?")
    print("=" * 70)

    proxies = np.array([d['phi_proxy'] for d in all_data])

    a_iit, b_iit, r2_iit, _ = linear_fit(ln_n, phis)
    a_prx, b_prx, r2_prx, _ = linear_fit(ln_n, proxies)

    print(f"\n  Phi(IIT)  = {a_iit:.4f} * ln(N) + ({b_iit:.4f}),  R^2 = {r2_iit:.6f}")
    print(f"  Phi(proxy)= {a_prx:.4f} * ln(N) + ({b_prx:.4f}),  R^2 = {r2_prx:.6f}")

    # Also try linear and power-law for proxy
    a_lin, b_lin, r2_lin, _ = linear_fit(ns.astype(float), proxies)
    # Power law: log(proxy) = c * log(N) + d => proxy = 10^d * N^c
    log_proxy = np.log(proxies + 1e-10)
    log_n = np.log(ns)
    a_pow, b_pow, r2_pow, _ = linear_fit(log_n, log_proxy)

    print(f"\n  Proxy alternative fits:")
    print(f"    Linear: proxy = {a_lin:.4f}*N + {b_lin:.4f}, R^2={r2_lin:.6f}")
    print(f"    Power:  proxy ~ N^{a_pow:.3f}, R^2={r2_pow:.6f}")
    print(f"    Log:    proxy = {a_prx:.4f}*ln(N) + {b_prx:.4f}, R^2={r2_prx:.6f}")

    best_proxy_fit = max(
        [('linear', r2_lin), ('power-law', r2_pow), ('logarithmic', r2_prx)],
        key=lambda x: x[1]
    )
    print(f"\n  Proxy BEST FIT: {best_proxy_fit[0]} (R^2={best_proxy_fit[1]:.6f})")

    print(f"\n  {'N':>6s} {'Phi(IIT)':>10s} {'Phi(proxy)':>12s} {'ratio':>8s}")
    print(f"  {'-' * 40}")
    for d in all_data:
        ratio = d['phi_proxy'] / d['phi_iit'] if d['phi_iit'] > 1e-6 else 0
        print(f"  {d['n']:>6d} {d['phi_iit']:>10.4f} {d['phi_proxy']:>12.4f} {ratio:>8.2f}")

    ascii_graph(ln_n, proxies, title="Phi(proxy) vs ln(N)", xlabel="ln(N)", ylabel="proxy")

    # ══════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("  SUMMARY — Phi ~ log(N) Scaling Law")
    print("=" * 70)
    print(f"""
  1. PRECISE FORMULA:
     Phi(IIT) = {a:.4f} * ln(N) + ({b:.4f})
     R^2 = {r2:.6f}

  2. BEST LOG BASE: {best_base}
     All bases give identical R^2 (they differ only by constant factor).
     Coefficient a(ln) = {a:.4f}, a(log2) = {a_log2:.4f}

  3. SCALING BREAKDOWN:
     Full range (N=2..256): R^2 = {r2_full:.6f}
     {'Log scaling HOLDS across all tested scales' if r2_full > 0.85 else 'Log scaling BREAKS at large N'}

  4. DRIVER: {best_driver[0]}
     Correlation with Phi: r = {best_driver[1]:.4f}
     Phi ~ log(N) {'because MI ~ log(N)' if best_driver[0] == 'MI (avg)' else 'driven by ' + best_driver[0]}

  5. IIT vs PROXY:
     Phi(IIT) : log fit R^2 = {r2_iit:.6f}
     Phi(proxy): best fit = {best_proxy_fit[0]} (R^2 = {best_proxy_fit[1]:.6f})

  Total time: {elapsed:.1f}s
""")


if __name__ == '__main__':
    main()
