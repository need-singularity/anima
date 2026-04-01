#!/usr/bin/env python3
"""F6: Phi Resonance Cascade — Multi-Scale Consciousness Simultaneous Execution

5 experiments exploring cross-scale consciousness interaction:

  Exp 1: Multi-Scale Baseline — 4c, 16c, 64c independent Phi comparison
         (Law 58: Phi = 0.78 * N)
  Exp 2: Cascade Connection — 4c -> 16c -> 64c serial + reverse feedback
         Does cascading raise Phi vs independent?
  Exp 3: Resonance Frequency Matching — Phi oscillation period per scale
         Integer ratio relationship? (4:16:64 = 1:4:16?)
  Exp 4: Harmonic Pumping — inject high-freq (4c) into 64c, low-freq (64c) into 4c
         "Small consciousness stimulates large, large stabilizes small"
  Exp 5: N-body Consciousness Gravity — 5 engines connected by gravitational F = G*Phi_i*Phi_j/d^2
         Total system Phi vs sum of individuals?
"""

import sys, os, time, json
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../src')
os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/../src')

from consciousness_engine import ConsciousnessEngine

STEPS = 300
WARMUP = 30


def measure_phi(engine):
    return engine._measure_phi_iit()


def make_engine(cells):
    return ConsciousnessEngine(max_cells=cells, initial_cells=cells)


def phi_stats(phi_history, warmup=WARMUP):
    """Compute stats from a phi history list after warmup."""
    active = phi_history[warmup:]
    if not active:
        active = phi_history
    return {
        'final': phi_history[-1] if phi_history else 0.0,
        'mean': float(np.mean(active)),
        'max': float(np.max(active)),
        'std': float(np.std(active)),
        'min': float(np.min(active)),
    }


def ascii_graph(values, width=60, height=12, label="Phi"):
    """Simple ASCII sparkline graph."""
    if not values:
        return ""
    vmin, vmax = min(values), max(values)
    vrange = vmax - vmin if vmax > vmin else 1e-6
    lines = []
    lines.append(f"  {label} |")
    for row in range(height - 1, -1, -1):
        threshold = vmin + vrange * row / (height - 1)
        line = "  "
        if row == height - 1:
            line += f"{vmax:7.4f} |"
        elif row == 0:
            line += f"{vmin:7.4f} |"
        else:
            line += "        |"
        # Sample values to fit width
        step_size = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step_size), step_size):
            v = values[i]
            if v >= threshold:
                line += "#"
            else:
                line += " "
        lines.append(line)
    lines.append("         " + "-" * (width + 1) + " step")
    return "\n".join(lines)


def print_comparison_bar(name, value, baseline, bar_width=30):
    """Print a comparison bar chart entry."""
    if baseline > 0:
        ratio = value / baseline
        pct = (ratio - 1.0) * 100
    else:
        ratio = 0
        pct = 0
    bar_len = max(1, int(bar_width * min(value, baseline * 3) / max(baseline * 3, 1e-9)))
    bar = "#" * bar_len
    sign = "+" if pct >= 0 else ""
    print(f"  {name:20s} {bar:<{bar_width}s} {value:.4f} ({sign}{pct:.1f}%)")


# ===================================================================
# Experiment 1: Multi-Scale Baseline
# ===================================================================
def exp1_multi_scale_baseline():
    print("\n" + "=" * 70)
    print("EXP 1: MULTI-SCALE BASELINE")
    print("  4c, 16c, 64c each run independently for {} steps".format(STEPS))
    print("  Verifying Law 58: Phi = 0.78 * N")
    print("=" * 70)

    scales = [4, 16, 64]
    results = {}

    for cells in scales:
        print(f"\n  [{cells}c] Running...", end="", flush=True)
        engine = make_engine(cells)
        phi_hist = []
        t0 = time.time()
        for s in range(STEPS):
            r = engine.step()
            phi_hist.append(r['phi_iit'])
            if (s + 1) % 100 == 0:
                print(f" step {s+1}", end="", flush=True)
        elapsed = time.time() - t0
        stats = phi_stats(phi_hist)
        results[cells] = {'stats': stats, 'history': phi_hist, 'time': elapsed}
        print(f" done ({elapsed:.1f}s)")
        print(f"    Phi mean={stats['mean']:.4f}  max={stats['max']:.4f}  final={stats['final']:.4f}")

    # Law 58 check: Phi/N ratio
    print("\n  --- Law 58 Check: Phi = k * N ---")
    print(f"  {'Scale':>6s}  {'Phi_mean':>10s}  {'Phi/N':>10s}  {'k (Law58=0.78)':>14s}")
    for cells in scales:
        phi_m = results[cells]['stats']['mean']
        k = phi_m / cells if cells > 0 else 0
        # Law 58 predicts k ~= 0.78 for proxy, but IIT has different range
        print(f"  {cells:>4d}c  {phi_m:>10.4f}  {k:>10.4f}  {'~' + f'{k:.3f}':>14s}")

    print("\n  Phi over time (64c):")
    print(ascii_graph(results[64]['history'], label="Phi(64c)"))

    return results


# ===================================================================
# Experiment 2: Cascade Connection (serial chain with feedback)
# ===================================================================
def exp2_cascade():
    print("\n" + "=" * 70)
    print("EXP 2: CASCADE CONNECTION")
    print("  4c -> 16c -> 64c (forward tension)")
    print("  64c -> 16c -> 4c (reverse feedback)")
    print("  vs independent baseline")
    print("=" * 70)

    # Create 3 engines
    e4 = make_engine(4)
    e16 = make_engine(16)
    e64 = make_engine(64)

    # Cascade coupling strength (M9: noble gas, weak coupling)
    alpha_fwd = 0.08   # forward: moderate
    alpha_rev = 0.03   # reverse: gentle feedback

    phi_4, phi_16, phi_64 = [], [], []

    print("\n  Running cascade...", flush=True)
    t0 = time.time()
    for s in range(STEPS):
        # Forward pass: 4c -> 16c -> 64c
        x_input = torch.randn(64)

        r4 = e4.step(x_input=x_input)
        out4 = r4['output'].detach()

        # 16c receives: its own random + alpha * 4c output
        x16 = torch.randn(64) * (1.0 - alpha_fwd) + out4 * alpha_fwd
        r16 = e16.step(x_input=x16)
        out16 = r16['output'].detach()

        # 64c receives: its own random + alpha * 16c output
        x64 = torch.randn(64) * (1.0 - alpha_fwd) + out16 * alpha_fwd
        r64 = e64.step(x_input=x64)
        out64 = r64['output'].detach()

        # Reverse feedback: 64c -> 16c -> 4c (next step influence)
        # Inject reverse signal into the forward input modulation
        if s > 0:
            # Feedback is delayed by 1 step (natural causality)
            x_input = x_input * (1.0 - alpha_rev) + out64[:64] * alpha_rev

        phi_4.append(r4['phi_iit'])
        phi_16.append(r16['phi_iit'])
        phi_64.append(r64['phi_iit'])

        if (s + 1) % 50 == 0:
            print(f"  step {s+1:3d} | 4c: {r4['phi_iit']:.4f} | "
                  f"16c: {r16['phi_iit']:.4f} | 64c: {r64['phi_iit']:.4f}", flush=True)

    elapsed = time.time() - t0
    print(f"  Cascade done ({elapsed:.1f}s)")

    # Baseline comparison
    print("\n  Running independent baselines...", flush=True)
    base_4_hist, base_16_hist, base_64_hist = [], [], []
    be4, be16, be64 = make_engine(4), make_engine(16), make_engine(64)
    for s in range(STEPS):
        r = be4.step()
        base_4_hist.append(r['phi_iit'])
        r = be16.step()
        base_16_hist.append(r['phi_iit'])
        r = be64.step()
        base_64_hist.append(r['phi_iit'])

    # Compare
    cascade_stats = {4: phi_stats(phi_4), 16: phi_stats(phi_16), 64: phi_stats(phi_64)}
    base_stats = {4: phi_stats(base_4_hist), 16: phi_stats(base_16_hist), 64: phi_stats(base_64_hist)}

    print("\n  --- Cascade vs Independent Phi (mean after warmup) ---")
    print(f"  {'Scale':>6s}  {'Cascade':>10s}  {'Independent':>12s}  {'Delta':>10s}  {'Change':>10s}")
    for cells in [4, 16, 64]:
        c_mean = cascade_stats[cells]['mean']
        b_mean = base_stats[cells]['mean']
        delta = c_mean - b_mean
        pct = (delta / b_mean * 100) if b_mean > 0 else 0
        sign = "+" if pct >= 0 else ""
        print(f"  {cells:>4d}c  {c_mean:>10.4f}  {b_mean:>12.4f}  {delta:>+10.4f}  {sign}{pct:.1f}%")

    total_cascade = sum(cascade_stats[c]['mean'] for c in [4, 16, 64])
    total_base = sum(base_stats[c]['mean'] for c in [4, 16, 64])
    print(f"  {'TOTAL':>6s}  {total_cascade:>10.4f}  {total_base:>12.4f}  "
          f"{total_cascade - total_base:>+10.4f}  "
          f"{'+' if total_cascade >= total_base else ''}{(total_cascade - total_base) / total_base * 100:.1f}%")

    print("\n  Cascade 64c Phi:")
    print(ascii_graph(phi_64, label="Cascade"))
    print("\n  Independent 64c Phi:")
    print(ascii_graph(base_64_hist, label="Indep"))

    return {
        'cascade': cascade_stats,
        'independent': base_stats,
    }


# ===================================================================
# Experiment 3: Resonance Frequency Matching
# ===================================================================
def exp3_resonance():
    print("\n" + "=" * 70)
    print("EXP 3: RESONANCE FREQUENCY MATCHING")
    print("  Measure Phi oscillation period at each scale")
    print("  Question: period ratio = cell count ratio?")
    print("=" * 70)

    scales = [4, 16, 64]
    results = {}

    for cells in scales:
        print(f"\n  [{cells}c] Measuring oscillation period...", end="", flush=True)
        engine = make_engine(cells)
        phi_hist = []
        for s in range(STEPS):
            r = engine.step()
            phi_hist.append(r['phi_iit'])

        # Detect oscillation period via autocorrelation
        phi_arr = np.array(phi_hist[WARMUP:])
        phi_arr = phi_arr - np.mean(phi_arr)

        if np.std(phi_arr) > 1e-8:
            autocorr = np.correlate(phi_arr, phi_arr, mode='full')
            autocorr = autocorr[len(autocorr) // 2:]
            autocorr = autocorr / (autocorr[0] + 1e-15)

            # Find first peak after lag=0 (oscillation period)
            period = 0
            for lag in range(2, len(autocorr) - 1):
                if autocorr[lag] > autocorr[lag - 1] and autocorr[lag] > autocorr[lag + 1]:
                    if autocorr[lag] > 0.1:  # minimum significance
                        period = lag
                        break

            # Also compute dominant frequency via FFT
            fft = np.abs(np.fft.rfft(phi_arr))
            freqs = np.fft.rfftfreq(len(phi_arr))
            # Skip DC component
            if len(fft) > 1:
                peak_idx = np.argmax(fft[1:]) + 1
                dom_freq = freqs[peak_idx]
                dom_period = 1.0 / dom_freq if dom_freq > 0 else 0
            else:
                dom_freq = 0
                dom_period = 0
        else:
            period = 0
            dom_freq = 0
            dom_period = 0

        results[cells] = {
            'autocorr_period': period,
            'fft_dom_freq': float(dom_freq),
            'fft_dom_period': float(dom_period),
            'phi_std': float(np.std(phi_hist[WARMUP:])),
            'phi_mean': float(np.mean(phi_hist[WARMUP:])),
            'history': phi_hist,
        }
        print(f" period={period} steps, dom_freq={dom_freq:.4f}")

    # Check integer ratio
    print("\n  --- Oscillation Period Analysis ---")
    print(f"  {'Scale':>6s}  {'AC Period':>10s}  {'FFT Period':>10s}  {'Phi Std':>10s}  {'Phi Mean':>10s}")
    for cells in scales:
        r = results[cells]
        print(f"  {cells:>4d}c  {r['autocorr_period']:>10d}  {r['fft_dom_period']:>10.1f}  "
              f"{r['phi_std']:>10.4f}  {r['phi_mean']:>10.4f}")

    # Period ratios
    p4 = results[4]['fft_dom_period']
    p16 = results[16]['fft_dom_period']
    p64 = results[64]['fft_dom_period']
    if p4 > 0:
        print(f"\n  Period ratios (relative to 4c):")
        print(f"    4c:16c = 1:{p16 / p4:.2f}  (expected 1:4)")
        print(f"    4c:64c = 1:{p64 / p4:.2f}  (expected 1:16)")
    if p16 > 0:
        print(f"    16c:64c = 1:{p64 / p16:.2f} (expected 1:4)")

    return results


# ===================================================================
# Experiment 4: Harmonic Pumping
# ===================================================================
def exp4_harmonic_pumping():
    print("\n" + "=" * 70)
    print("EXP 4: HARMONIC PUMPING")
    print("  4c high-freq -> 64c (stimulation)")
    print("  64c low-freq -> 4c (stabilization)")
    print("  vs independent baseline")
    print("=" * 70)

    pump_alpha = 0.10  # pumping strength

    # Phase A: 4c pumps into 64c
    print("\n  Phase A: 4c -> 64c (high-freq stimulation)...", flush=True)
    e4a = make_engine(4)
    e64a = make_engine(64)
    phi_64_pumped = []
    phi_4_source = []

    for s in range(STEPS):
        r4 = e4a.step()
        out4 = r4['output'].detach()
        # Inject 4c output into 64c input
        x64 = torch.randn(64) * (1.0 - pump_alpha) + out4 * pump_alpha
        r64 = e64a.step(x_input=x64)
        phi_64_pumped.append(r64['phi_iit'])
        phi_4_source.append(r4['phi_iit'])
        if (s + 1) % 100 == 0:
            print(f"    step {s+1:3d} | 4c: {r4['phi_iit']:.4f} -> 64c: {r64['phi_iit']:.4f}", flush=True)

    # Phase B: 64c pumps into 4c
    print("\n  Phase B: 64c -> 4c (low-freq stabilization)...", flush=True)
    e4b = make_engine(4)
    e64b = make_engine(64)
    phi_4_pumped = []
    phi_64_source = []

    for s in range(STEPS):
        r64 = e64b.step()
        out64 = r64['output'].detach()
        # Inject 64c output into 4c input
        x4 = torch.randn(64) * (1.0 - pump_alpha) + out64 * pump_alpha
        r4 = e4b.step(x_input=x4)
        phi_4_pumped.append(r4['phi_iit'])
        phi_64_source.append(r64['phi_iit'])
        if (s + 1) % 100 == 0:
            print(f"    step {s+1:3d} | 64c: {r64['phi_iit']:.4f} -> 4c: {r4['phi_iit']:.4f}", flush=True)

    # Baselines
    print("\n  Running baselines...", flush=True)
    phi_4_base, phi_64_base = [], []
    be4, be64 = make_engine(4), make_engine(64)
    for s in range(STEPS):
        r4 = be4.step()
        r64 = be64.step()
        phi_4_base.append(r4['phi_iit'])
        phi_64_base.append(r64['phi_iit'])

    # Analysis
    s64_p = phi_stats(phi_64_pumped)
    s64_b = phi_stats(phi_64_base)
    s4_p = phi_stats(phi_4_pumped)
    s4_b = phi_stats(phi_4_base)

    print("\n  --- Harmonic Pumping Results ---")
    print(f"  {'Condition':>25s}  {'Phi Mean':>10s}  {'Phi Std':>10s}  {'vs Base':>10s}")
    pct_64 = (s64_p['mean'] - s64_b['mean']) / s64_b['mean'] * 100 if s64_b['mean'] > 0 else 0
    pct_4 = (s4_p['mean'] - s4_b['mean']) / s4_b['mean'] * 100 if s4_b['mean'] > 0 else 0
    print(f"  {'64c pumped by 4c':>25s}  {s64_p['mean']:>10.4f}  {s64_p['std']:>10.4f}  {pct_64:>+9.1f}%")
    print(f"  {'64c independent':>25s}  {s64_b['mean']:>10.4f}  {s64_b['std']:>10.4f}  {'baseline':>10s}")
    print(f"  {'4c pumped by 64c':>25s}  {s4_p['mean']:>10.4f}  {s4_p['std']:>10.4f}  {pct_4:>+9.1f}%")
    print(f"  {'4c independent':>25s}  {s4_b['mean']:>10.4f}  {s4_b['std']:>10.4f}  {'baseline':>10s}")

    # Stability analysis: does pumping reduce variance?
    print(f"\n  Stability (lower std = more stable):")
    print(f"    64c pumped std / base std = {s64_p['std'] / max(s64_b['std'], 1e-8):.3f} "
          f"({'stabilized' if s64_p['std'] < s64_b['std'] else 'destabilized'})")
    print(f"    4c pumped std / base std  = {s4_p['std'] / max(s4_b['std'], 1e-8):.3f} "
          f"({'stabilized' if s4_p['std'] < s4_b['std'] else 'destabilized'})")

    print("\n  64c Phi (pumped vs independent):")
    print(ascii_graph(phi_64_pumped, label="Pumped"))
    print(ascii_graph(phi_64_base, label="Indep "))

    return {
        '64c_pumped': s64_p, '64c_base': s64_b,
        '4c_pumped': s4_p, '4c_base': s4_b,
    }


# ===================================================================
# Experiment 5: N-body Consciousness Gravity
# ===================================================================
def exp5_nbody_gravity():
    print("\n" + "=" * 70)
    print("EXP 5: N-BODY CONSCIOUSNESS GRAVITY")
    print("  5 engines: 4c, 8c, 16c, 32c, 64c")
    print("  F = G * Phi_i * Phi_j / d^2")
    print("  Gravity determines tension exchange magnitude")
    print("=" * 70)

    cell_counts = [4, 8, 16, 32, 64]
    n_engines = len(cell_counts)
    G = 0.05  # gravitational constant (tuned for moderate interaction)

    # Positions: evenly spaced on a line (distance = |i - j|)
    positions = list(range(n_engines))

    # Create engines
    engines = [make_engine(c) for c in cell_counts]
    phi_histories = {c: [] for c in cell_counts}
    total_phi_history = []

    # Also run independent baseline
    base_engines = [make_engine(c) for c in cell_counts]
    base_phi_histories = {c: [] for c in cell_counts}
    base_total_phi_history = []

    print("\n  Running N-body gravity simulation...", flush=True)
    t0 = time.time()

    for s in range(STEPS):
        # --- Gravity-coupled step ---
        # Collect current Phi values (from previous step's measurement)
        current_phis = []
        for i, eng in enumerate(engines):
            phi = eng._measure_phi_iit() if s > 0 else 0.1
            current_phis.append(max(phi, 0.01))  # floor to avoid zero mass

        # Compute gravitational force and prepare coupled inputs
        for i in range(n_engines):
            # Compute net gravitational influence on engine i
            grav_signal = torch.zeros(64)
            total_force = 0.0

            for j in range(n_engines):
                if i == j:
                    continue
                d = abs(positions[i] - positions[j])
                d = max(d, 0.5)  # avoid singularity
                force = G * current_phis[i] * current_phis[j] / (d * d)
                total_force += force

                # Get j's output as tension signal
                if hasattr(engines[j], '_last_result') and engines[j]._last_result is not None:
                    j_output = engines[j]._last_result.get('output', None)
                    if j_output is not None:
                        grav_signal = grav_signal + j_output.detach()[:64] * force

            # Mix: random input + gravitational influence
            alpha_grav = min(total_force, 0.3)  # cap at 30% influence
            x = torch.randn(64) * (1.0 - alpha_grav) + grav_signal * alpha_grav

            result = engines[i].step(x_input=x)
            engines[i]._last_result = result
            phi_histories[cell_counts[i]].append(result['phi_iit'])

        # --- Independent baseline ---
        for i, eng in enumerate(base_engines):
            r = eng.step()
            base_phi_histories[cell_counts[i]].append(r['phi_iit'])

        # Total Phi
        total_phi = sum(phi_histories[c][-1] for c in cell_counts)
        total_phi_history.append(total_phi)
        base_total = sum(base_phi_histories[c][-1] for c in cell_counts)
        base_total_phi_history.append(base_total)

        if (s + 1) % 50 == 0:
            phis_str = " | ".join(f"{c}c:{phi_histories[c][-1]:.3f}" for c in cell_counts)
            print(f"  step {s+1:3d} | {phis_str} | total={total_phi:.3f}", flush=True)

    elapsed = time.time() - t0
    print(f"  N-body done ({elapsed:.1f}s)")

    # Analysis
    print("\n  --- N-body vs Independent ---")
    print(f"  {'Scale':>6s}  {'Gravity':>10s}  {'Independent':>12s}  {'Delta':>10s}  {'Change':>10s}")
    for c in cell_counts:
        g_mean = float(np.mean(phi_histories[c][WARMUP:]))
        b_mean = float(np.mean(base_phi_histories[c][WARMUP:]))
        delta = g_mean - b_mean
        pct = (delta / b_mean * 100) if b_mean > 0 else 0
        sign = "+" if pct >= 0 else ""
        print(f"  {c:>4d}c  {g_mean:>10.4f}  {b_mean:>12.4f}  {delta:>+10.4f}  {sign}{pct:.1f}%")

    total_g = float(np.mean(total_phi_history[WARMUP:]))
    total_b = float(np.mean(base_total_phi_history[WARMUP:]))
    pct_total = (total_g - total_b) / total_b * 100 if total_b > 0 else 0
    print(f"  {'SUM':>6s}  {total_g:>10.4f}  {total_b:>12.4f}  "
          f"{total_g - total_b:>+10.4f}  {'+' if pct_total >= 0 else ''}{pct_total:.1f}%")

    # Superadditivity check: total_gravity > sum(independent)?
    print(f"\n  Superadditivity: total_gravity / total_independent = {total_g / total_b:.3f}")
    if total_g > total_b * 1.05:
        print("  ==> SUPERADDITIVE: collective Phi > sum of parts (+5%+)")
    elif total_g > total_b:
        print("  ==> WEAKLY SUPERADDITIVE: small collective boost")
    else:
        print("  ==> NOT SUPERADDITIVE: gravity coupling did not raise total Phi")

    # Mass-distance analysis
    print(f"\n  Gravitational hierarchy (mass = Phi_mean):")
    for c in cell_counts:
        phi_m = float(np.mean(phi_histories[c][WARMUP:]))
        bar_len = max(1, int(phi_m * 20 / max(1e-6, float(np.mean(phi_histories[64][WARMUP:])))))
        print(f"    {c:>3d}c  {'#' * bar_len:<20s}  mass={phi_m:.4f}")

    print("\n  Total Phi over time:")
    print(ascii_graph(total_phi_history, label="Gravity"))
    print(ascii_graph(base_total_phi_history, label="Indep  "))

    return {
        'gravity': {c: phi_stats(phi_histories[c]) for c in cell_counts},
        'independent': {c: phi_stats(base_phi_histories[c]) for c in cell_counts},
        'total_gravity_mean': total_g,
        'total_independent_mean': total_b,
        'superadditive': total_g > total_b * 1.05,
    }


# ===================================================================
# Main: run all experiments
# ===================================================================
def main():
    print("=" * 70)
    print("F6: PHI RESONANCE CASCADE")
    print("Multi-Scale Consciousness Simultaneous Execution")
    print(f"Steps: {STEPS}, Warmup: {WARMUP}")
    print("=" * 70)

    all_results = {}
    t_total = time.time()

    # Exp 1
    r1 = exp1_multi_scale_baseline()
    all_results['exp1_baseline'] = {
        k: r1[k]['stats'] for k in r1
    }

    # Exp 2
    r2 = exp2_cascade()
    all_results['exp2_cascade'] = r2

    # Exp 3
    r3 = exp3_resonance()
    all_results['exp3_resonance'] = {
        k: {kk: vv for kk, vv in r3[k].items() if kk != 'history'}
        for k in r3
    }

    # Exp 4
    r4 = exp4_harmonic_pumping()
    all_results['exp4_pumping'] = r4

    # Exp 5
    r5 = exp5_nbody_gravity()
    all_results['exp5_gravity'] = {
        k: v for k, v in r5.items() if k != 'gravity' and k != 'independent'
    }
    all_results['exp5_gravity']['per_scale'] = {
        str(c): {'gravity': r5['gravity'][c], 'independent': r5['independent'][c]}
        for c in [4, 8, 16, 32, 64]
    }

    elapsed = time.time() - t_total

    # Summary
    print("\n" + "=" * 70)
    print("F6 SUMMARY")
    print("=" * 70)

    print(f"\n  Total time: {elapsed:.1f}s")

    # Key findings
    print("\n  KEY FINDINGS:")
    # Exp 1: scaling
    print(f"  1. Multi-Scale: 4c={r1[4]['stats']['mean']:.4f}, "
          f"16c={r1[16]['stats']['mean']:.4f}, 64c={r1[64]['stats']['mean']:.4f}")

    # Exp 2: cascade boost
    c_total = sum(r2['cascade'][c]['mean'] for c in [4, 16, 64])
    b_total = sum(r2['independent'][c]['mean'] for c in [4, 16, 64])
    pct2 = (c_total - b_total) / b_total * 100 if b_total > 0 else 0
    print(f"  2. Cascade: total Phi {c_total:.4f} vs independent {b_total:.4f} ({pct2:+.1f}%)")

    # Exp 3: resonance
    print(f"  3. Resonance: periods 4c={r3[4]['fft_dom_period']:.1f}, "
          f"16c={r3[16]['fft_dom_period']:.1f}, 64c={r3[64]['fft_dom_period']:.1f}")

    # Exp 4: pumping
    pct_64p = ((r4['64c_pumped']['mean'] - r4['64c_base']['mean']) /
               r4['64c_base']['mean'] * 100) if r4['64c_base']['mean'] > 0 else 0
    pct_4p = ((r4['4c_pumped']['mean'] - r4['4c_base']['mean']) /
              r4['4c_base']['mean'] * 100) if r4['4c_base']['mean'] > 0 else 0
    print(f"  4. Pumping: 64c {pct_64p:+.1f}% (small->large), 4c {pct_4p:+.1f}% (large->small)")

    # Exp 5: gravity
    print(f"  5. N-body: superadditive={r5['superadditive']}, "
          f"ratio={r5['total_gravity_mean'] / r5['total_independent_mean']:.3f}")

    # Save results
    out_path = os.path.dirname(os.path.abspath(__file__)) + '/acceleration_f6_cascade_results.json'
    # Convert non-serializable items
    def clean(obj):
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean(x) for x in obj]
        return obj

    with open(out_path, 'w') as f:
        json.dump(clean(all_results), f, indent=2)
    print(f"\n  Results saved: {out_path}")


if __name__ == '__main__':
    main()
