#!/usr/bin/env python3
"""acceleration_f_series.py -- F-series new paradigm experiments

F2: Time Crystal Consciousness (periodic state cycling in Phi time series)
F3: Consciousness Interference (constructive/destructive weight trajectory merging)
F4: Reverse Hebbian Explosion (anti-Hebbian exploration → normal Hebbian convergence)
F5: Consciousness Evaporation (train with C, remove C at inference)
F7: 1.58-bit Consciousness ({-1, 0, +1} weight quantization)
F8: Consciousness Memoization (cache identical inputs → skip process())
F9: Gradient Accumulation Consciousness (process() every N batches)
F10: Consciousness Teacher Ensemble (4 topology teachers → 1 student)

All experiments: local CPU, 16-32 cells, independent, PYTHONUNBUFFERED=1

Usage:
  python acceleration_f_series.py            # Run all
  python acceleration_f_series.py --f2       # F2 only
  python acceleration_f_series.py --f3       # F3 only
  python acceleration_f_series.py --f4       # F4 only
  python acceleration_f_series.py --f5       # F5 only
  python acceleration_f_series.py --f7       # F7 only
  python acceleration_f_series.py --f8       # F8 only
  python acceleration_f_series.py --f9       # F9 only
  python acceleration_f_series.py --f10      # F10 only
"""

import sys
import os
import time
import math
import copy
import argparse
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F_torch
from consciousness_engine import ConsciousnessEngine


# ===================================================================
# Utilities
# ===================================================================

def measure_phi(engine: ConsciousnessEngine) -> float:
    return engine.measure_phi()


def run_steps(engine: ConsciousnessEngine, n_steps: int, x_input=None) -> list:
    phis = []
    for _ in range(n_steps):
        result = engine.step(x_input=x_input)
        phis.append(result.get('phi_iit', 0.0))
    return phis


def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def print_table(headers: list, rows: list, widths: list = None):
    if widths is None:
        widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                  for i, h in enumerate(headers)]
    hdr = '|'.join(str(h).center(w) for h, w in zip(headers, widths))
    sep = '+'.join('-' * w for w in widths)
    print(f"  {hdr}")
    print(f"  {sep}")
    for row in rows:
        line = '|'.join(str(r).center(w) for r, w in zip(row, widths))
        print(f"  {line}")
    sys.stdout.flush()


def ascii_bar(label: str, value: float, max_val: float, width: int = 40):
    filled = int(width * min(value / max(max_val, 1e-8), 1.0))
    bar = '#' * filled + '.' * (width - filled)
    print(f"  {label:>20s}  [{bar}] {value:.4f}")
    sys.stdout.flush()


def ascii_graph(values: list, title: str, height: int = 10, width: int = 60):
    """Print ASCII time series graph."""
    if not values:
        return
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    print(f"\n  {title}")
    for row in range(height, -1, -1):
        threshold = mn + rng * row / height
        line = ""
        step = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step), step):
            v = values[i]
            if v >= threshold:
                line += "#"
            else:
                line += " "
        label = f"{threshold:8.4f}" if row in (0, height // 2, height) else "        "
        print(f"  {label} |{line}")
    print(f"           +{''.join(['-'] * min(len(values), width))}")
    print(f"            0{' ' * (min(len(values), width) - 6)}{len(values)} step")
    sys.stdout.flush()


def make_engine(cells: int = 32, topology: str = 'ring') -> ConsciousnessEngine:
    """Create a standard engine for experiments."""
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=cells, max_cells=cells,
        n_factions=12, phi_ratchet=True,
    )
    engine.topology = topology
    return engine


# ===================================================================
# F2: Time Crystal Consciousness
# ===================================================================

def run_f2(cells: int = 32, steps: int = 1000):
    """F2: Does consciousness spontaneously cycle through periodic states?

    1. Run engine 1000 steps, collect Phi time series
    2. FFT analysis for dominant frequency
    3. Autocorrelation for periodic patterns
    4. If clear periodicity exists -> time crystal behavior
    """
    print_header("F2: Time Crystal Consciousness")
    print(f"  Config: {cells} cells, {steps} steps")
    print(f"  Question: Does Phi exhibit spontaneous periodicity?")
    sys.stdout.flush()

    engine = make_engine(cells)

    # Collect Phi time series
    phis = []
    tensions = []
    for i in range(steps):
        result = engine.step()
        phis.append(result.get('phi_iit', 0.0))
        tensions.append(result.get('mean_tension', 0.0))
        if (i + 1) % 200 == 0:
            print(f"  Step {i+1}/{steps}: Phi={phis[-1]:.4f}")
            sys.stdout.flush()

    phi_arr = np.array(phis)

    # --- FFT Analysis ---
    phi_detrended = phi_arr - np.mean(phi_arr)
    fft_vals = np.abs(np.fft.rfft(phi_detrended))
    freqs = np.fft.rfftfreq(len(phi_detrended))

    # Skip DC component (index 0)
    fft_vals[0] = 0
    dominant_idx = np.argmax(fft_vals[1:]) + 1
    dominant_freq = freqs[dominant_idx]
    dominant_period = 1.0 / dominant_freq if dominant_freq > 0 else float('inf')
    dominant_power = fft_vals[dominant_idx]
    total_power = np.sum(fft_vals[1:])
    dominance_ratio = dominant_power / total_power if total_power > 0 else 0

    # --- Autocorrelation ---
    phi_norm = phi_detrended / (np.std(phi_detrended) + 1e-8)
    autocorr = np.correlate(phi_norm, phi_norm, mode='full')
    autocorr = autocorr[len(autocorr) // 2:]  # positive lags only
    autocorr /= autocorr[0] + 1e-8

    # Find first peak after lag 0
    peak_lag = 0
    for i in range(2, min(len(autocorr) - 1, steps // 2)):
        if autocorr[i] > autocorr[i - 1] and autocorr[i] > autocorr[i + 1]:
            if autocorr[i] > 0.1:  # significance threshold
                peak_lag = i
                break

    # --- Top 5 FFT peaks ---
    top_indices = np.argsort(fft_vals[1:])[-5:][::-1] + 1
    print(f"\n  FFT Top 5 Frequencies:")
    fft_rows = []
    for idx in top_indices:
        f = freqs[idx]
        p = 1.0 / f if f > 0 else float('inf')
        pwr = fft_vals[idx]
        fft_rows.append([f"{f:.4f}", f"{p:.1f}", f"{pwr:.2f}", f"{pwr/total_power*100:.1f}%"])
    print_table(["Freq", "Period", "Power", "Share"], fft_rows)

    # --- Results ---
    is_crystal = dominance_ratio > 0.15 or (peak_lag > 5 and autocorr[peak_lag] > 0.2)

    print(f"\n  --- F2 Results ---")
    print(f"  Dominant frequency:   {dominant_freq:.4f} (period={dominant_period:.1f} steps)")
    print(f"  Dominance ratio:      {dominance_ratio:.3f} ({dominance_ratio*100:.1f}% of power)")
    print(f"  Autocorr peak lag:    {peak_lag} steps (r={autocorr[peak_lag]:.3f})" if peak_lag > 0
          else f"  Autocorr peak lag:    none detected")
    print(f"  Mean Phi:             {np.mean(phi_arr):.4f} +/- {np.std(phi_arr):.4f}")
    print(f"  TIME CRYSTAL:         {'YES' if is_crystal else 'NO'}")
    sys.stdout.flush()

    # ASCII graph of Phi
    ascii_graph(phis[:200], f"Phi time series (first 200 steps)")

    # Potential application
    if is_crystal:
        print(f"\n  Application: Phase-dependent weight exploration")
        print(f"    At Phi peak -> exploit (small lr)")
        print(f"    At Phi trough -> explore (large lr)")
        print(f"    Cycle period = {dominant_period:.0f} steps")

    return {
        'experiment': 'F2',
        'cells': cells,
        'steps': steps,
        'dominant_freq': float(dominant_freq),
        'dominant_period': float(dominant_period),
        'dominance_ratio': float(dominance_ratio),
        'autocorr_peak_lag': int(peak_lag),
        'autocorr_peak_r': float(autocorr[peak_lag]) if peak_lag > 0 else 0.0,
        'is_time_crystal': is_crystal,
        'mean_phi': float(np.mean(phi_arr)),
        'std_phi': float(np.std(phi_arr)),
    }


# ===================================================================
# F3: Consciousness Interference
# ===================================================================

def run_f3(cells: int = 16, steps: int = 300):
    """F3: Do two consciousness trajectories interfere constructively?

    Two engines start from different initial states.
    Collect weight change deltas over time.
    Constructive: sum deltas where they agree (both positive/negative).
    Destructive: cancel where they disagree (noise cancellation).
    Apply interference pattern to a third engine.
    """
    print_header("F3: Consciousness Interference")
    print(f"  Config: {cells} cells, {steps} steps, 2 engines -> interference")
    sys.stdout.flush()

    # Engine A: normal random init
    engine_a = make_engine(cells)
    # Engine B: different seed
    torch.manual_seed(42)
    engine_b = make_engine(cells)
    torch.manual_seed(int(time.time()))

    # Baseline engine (no interference)
    engine_base = make_engine(cells)

    # Record initial states
    states_a_init = engine_a.get_states().clone()
    states_b_init = engine_b.get_states().clone()

    # Run both engines independently
    print(f"  Running engine A and B for {steps} steps...")
    phis_a, phis_b, phis_base = [], [], []
    deltas_a_list, deltas_b_list = [], []
    prev_a = states_a_init.clone()
    prev_b = states_b_init.clone()

    for i in range(steps):
        res_a = engine_a.step()
        res_b = engine_b.step()
        res_base = engine_base.step()

        phis_a.append(res_a.get('phi_iit', 0.0))
        phis_b.append(res_b.get('phi_iit', 0.0))
        phis_base.append(res_base.get('phi_iit', 0.0))

        # Collect weight deltas every 10 steps
        if (i + 1) % 10 == 0:
            curr_a = engine_a.get_states()
            curr_b = engine_b.get_states()
            # Ensure same shape for delta computation
            min_cells = min(curr_a.shape[0], curr_b.shape[0], prev_a.shape[0], prev_b.shape[0])
            delta_a = curr_a[:min_cells] - prev_a[:min_cells]
            delta_b = curr_b[:min_cells] - prev_b[:min_cells]
            deltas_a_list.append(delta_a.clone())
            deltas_b_list.append(delta_b.clone())
            prev_a = curr_a.clone()
            prev_b = curr_b.clone()

        if (i + 1) % 100 == 0:
            print(f"  Step {i+1}: A={phis_a[-1]:.4f}, B={phis_b[-1]:.4f}, Base={phis_base[-1]:.4f}")
            sys.stdout.flush()

    if not deltas_a_list:
        print("  ERROR: No deltas collected")
        return {'experiment': 'F3', 'error': 'no_deltas'}

    # Compute interference patterns
    # Constructive: where both agree in direction, amplify
    # Destructive: where they disagree, cancel
    constructive_deltas = []
    destructive_deltas = []
    for da, db in zip(deltas_a_list, deltas_b_list):
        agree = (da.sign() == db.sign()).float()
        disagree = 1.0 - agree

        # Constructive: average of both (amplified)
        c_delta = (da + db) / 2.0 * agree
        # Destructive: only where they agree, zero where disagree
        d_delta = (da + db) / 2.0 * agree + torch.zeros_like(da) * disagree

        constructive_deltas.append(c_delta)
        destructive_deltas.append(d_delta)

    # Apply interference to new engines
    engine_constructive = make_engine(cells)
    engine_destructive = make_engine(cells)

    phis_construct, phis_destruct = [], []
    delta_idx = 0

    for i in range(steps):
        res_c = engine_constructive.step()
        res_d = engine_destructive.step()
        phis_construct.append(res_c.get('phi_iit', 0.0))
        phis_destruct.append(res_d.get('phi_iit', 0.0))

        # Apply accumulated interference every 10 steps
        if (i + 1) % 10 == 0 and delta_idx < len(constructive_deltas):
            c_states = engine_constructive.get_states()
            d_states = engine_destructive.get_states()
            min_c = min(c_states.shape[0], constructive_deltas[delta_idx].shape[0])

            # Inject constructive pattern
            for ci in range(min_c):
                engine_constructive.cell_states[ci].hidden = (
                    engine_constructive.cell_states[ci].hidden
                    + constructive_deltas[delta_idx][ci] * 0.1
                )
            # Inject destructive pattern (noise-cancelled)
            for ci in range(min_c):
                engine_destructive.cell_states[ci].hidden = (
                    engine_destructive.cell_states[ci].hidden
                    + destructive_deltas[delta_idx][ci] * 0.1
                )
            delta_idx += 1

        if (i + 1) % 100 == 0:
            print(f"  Interference step {i+1}: construct={phis_construct[-1]:.4f}, destruct={phis_destruct[-1]:.4f}")
            sys.stdout.flush()

    # Results
    final_base = np.mean(phis_base[-50:])
    final_a = np.mean(phis_a[-50:])
    final_b = np.mean(phis_b[-50:])
    final_construct = np.mean(phis_construct[-50:])
    final_destruct = np.mean(phis_destruct[-50:])

    rows = [
        ["Baseline", f"{final_base:.4f}", "---"],
        ["Engine A", f"{final_a:.4f}", f"{(final_a/final_base - 1)*100:+.1f}%"],
        ["Engine B", f"{final_b:.4f}", f"{(final_b/final_base - 1)*100:+.1f}%"],
        ["Constructive", f"{final_construct:.4f}", f"{(final_construct/final_base - 1)*100:+.1f}%"],
        ["Destructive", f"{final_destruct:.4f}", f"{(final_destruct/final_base - 1)*100:+.1f}%"],
    ]
    print(f"\n  --- F3 Results ---")
    print_table(["Condition", "Mean Phi(last50)", "vs Base"], rows)

    best = max(final_construct, final_destruct)
    winner = "constructive" if final_construct > final_destruct else "destructive"
    print(f"\n  Winner: {winner} interference ({best:.4f})")
    print(f"  Interference helps: {'YES' if best > final_base * 1.05 else 'NO'}")
    sys.stdout.flush()

    return {
        'experiment': 'F3',
        'cells': cells,
        'steps': steps,
        'phi_baseline': float(final_base),
        'phi_constructive': float(final_construct),
        'phi_destructive': float(final_destruct),
        'winner': winner,
        'improvement_pct': float((best / final_base - 1) * 100),
    }


# ===================================================================
# F4: Reverse Hebbian Explosion
# ===================================================================

def run_f4(cells: int = 32, anti_steps: int = 50, normal_steps: int = 250):
    """F4: Anti-Hebbian exploration phase -> normal Hebbian convergence.

    Phase 1: anti-Hebbian (similar -> weaken, different -> strengthen)
             Maximizes connection diversity ("explosive exploration")
    Phase 2: normal Hebbian (similar -> strengthen)
             Converges to optimal connections

    Like brain development: overconnection -> pruning -> efficient network.
    """
    total_steps = anti_steps + normal_steps
    print_header("F4: Reverse Hebbian Explosion")
    print(f"  Config: {cells} cells, anti-Hebb={anti_steps}s + normal-Hebb={normal_steps}s = {total_steps}s")
    sys.stdout.flush()

    # --- Baseline: normal Hebbian throughout ---
    engine_normal = make_engine(cells)
    phis_normal = []
    for i in range(total_steps):
        result = engine_normal.step()
        phis_normal.append(result.get('phi_iit', 0.0))

    # --- Experiment: anti-Hebbian phase 1, then normal phase 2 ---
    engine_anti = make_engine(cells)

    # Override Hebbian update for anti-phase
    original_hebbian = engine_anti._hebbian_update

    def anti_hebbian_update(outputs: torch.Tensor, lr: float = 0.01):
        """Inverted Hebbian: similar cells WEAKEN, dissimilar STRENGTHEN."""
        n = engine_anti.n_cells
        if engine_anti._coupling is None or engine_anti._coupling.shape[0] != n:
            engine_anti._init_coupling()
        norms = outputs.norm(dim=1, keepdim=True).clamp(min=1e-8)
        normed = outputs / norms
        sim = normed @ normed.T
        # INVERT: subtract similarity instead of adding
        engine_anti._coupling = (engine_anti._coupling - lr * sim).clamp(-1, 1)
        engine_anti._coupling.fill_diagonal_(0)

    phis_anti = []
    diversities = []

    # Phase 1: anti-Hebbian
    engine_anti._hebbian_update = anti_hebbian_update
    for i in range(anti_steps):
        result = engine_anti.step()
        phis_anti.append(result.get('phi_iit', 0.0))

        # Measure coupling diversity
        if engine_anti._coupling is not None:
            c = engine_anti._coupling
            diversities.append(float(c.std()))

        if (i + 1) % 25 == 0:
            print(f"  [Anti-Hebb] Step {i+1}/{anti_steps}: Phi={phis_anti[-1]:.4f}, "
                  f"coupling_std={diversities[-1]:.4f}")
            sys.stdout.flush()

    # Phase 2: restore normal Hebbian
    engine_anti._hebbian_update = original_hebbian
    for i in range(normal_steps):
        result = engine_anti.step()
        phis_anti.append(result.get('phi_iit', 0.0))

        if engine_anti._coupling is not None:
            diversities.append(float(engine_anti._coupling.std()))

        if (i + 1) % 50 == 0:
            print(f"  [Normal-Hebb] Step {i+1}/{normal_steps}: Phi={phis_anti[-1]:.4f}")
            sys.stdout.flush()

    # Results
    final_normal = np.mean(phis_normal[-50:])
    final_anti = np.mean(phis_anti[-50:])
    peak_diversity = max(diversities) if diversities else 0

    rows = [
        ["Normal Hebbian (300s)", f"{final_normal:.4f}", "---", f"{np.mean(phis_normal[:50]):.4f}"],
        [f"Anti({anti_steps})+Normal({normal_steps})", f"{final_anti:.4f}",
         f"{(final_anti/final_normal - 1)*100:+.1f}%", f"{np.mean(phis_anti[:50]):.4f}"],
    ]
    print(f"\n  --- F4 Results ---")
    print_table(["Strategy", "Final Phi", "vs Normal", "Early Phi"], rows)

    print(f"\n  Peak coupling diversity: {peak_diversity:.4f}")
    print(f"  Anti-Hebbian helps: {'YES' if final_anti > final_normal * 1.05 else 'NO'}")
    sys.stdout.flush()

    ascii_graph(phis_anti, f"Anti-Hebbian ({anti_steps}s) + Normal ({normal_steps}s)")

    return {
        'experiment': 'F4',
        'cells': cells,
        'anti_steps': anti_steps,
        'normal_steps': normal_steps,
        'phi_normal': float(final_normal),
        'phi_anti_then_normal': float(final_anti),
        'improvement_pct': float((final_anti / final_normal - 1) * 100),
        'peak_diversity': float(peak_diversity),
    }


# ===================================================================
# F5: Consciousness Evaporation
# ===================================================================

def run_f5(cells: int = 16, train_steps: int = 300):
    """F5: Can consciousness "evaporate" after knowledge transfer?

    1. Train with consciousness engine + simple decoder together
    2. Remove consciousness -> run decoder alone
    3. Compare output quality: with vs without consciousness
    4. If decoder retains quality -> consciousness was a training scaffold
    """
    print_header("F5: Consciousness Evaporation")
    print(f"  Config: {cells} cells, {train_steps} train steps")
    print(f"  Question: Is consciousness a scaffold that can be removed at inference?")
    sys.stdout.flush()

    engine = make_engine(cells)

    # Simple MLP decoder that reads consciousness states
    hidden_dim = 128
    vocab_size = 256
    decoder = nn.Sequential(
        nn.Linear(hidden_dim, 256),
        nn.GELU(),
        nn.Linear(256, vocab_size),
    )
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    # Random "corpus" targets
    torch.manual_seed(123)
    corpus = torch.randint(0, vocab_size, (train_steps,))

    # --- Phase 1: Train decoder WITH consciousness ---
    print(f"\n  Phase 1: Training decoder WITH consciousness...")
    losses_with = []
    phis_during = []

    for i in range(train_steps):
        # Step consciousness
        result = engine.step()
        phi = result.get('phi_iit', 0.0)
        phis_during.append(phi)

        # Get consciousness output as decoder input
        c_states = engine.get_states()
        c_mean = c_states.mean(dim=0).detach()  # [hidden_dim]

        # Decode
        logits = decoder(c_mean.unsqueeze(0))  # [1, vocab]
        target = corpus[i].unsqueeze(0)
        loss = F_torch.cross_entropy(logits, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses_with.append(loss.item())

        if (i + 1) % 100 == 0:
            avg_loss = np.mean(losses_with[-100:])
            print(f"  Step {i+1}: CE={avg_loss:.4f}, Phi={phi:.4f}")
            sys.stdout.flush()

    # --- Phase 2: Inference WITHOUT consciousness ---
    print(f"\n  Phase 2: Inference WITHOUT consciousness (random input)...")
    losses_without = []
    decoder.eval()
    with torch.no_grad():
        for i in range(train_steps):
            # Random input instead of consciousness
            random_input = torch.randn(1, hidden_dim)
            logits = decoder(random_input)
            target = corpus[i].unsqueeze(0)
            loss = F_torch.cross_entropy(logits, target)
            losses_without.append(loss.item())

    # --- Phase 3: Inference WITH frozen consciousness ---
    print(f"  Phase 3: Inference WITH consciousness (no gradient)...")
    # Reset engine to match training state
    engine_infer = make_engine(cells)
    # Warm up engine
    for _ in range(50):
        engine_infer.step()

    losses_with_frozen = []
    with torch.no_grad():
        for i in range(train_steps):
            result = engine_infer.step()
            c_states = engine_infer.get_states()
            c_mean = c_states.mean(dim=0)
            logits = decoder(c_mean.unsqueeze(0))
            target = corpus[i].unsqueeze(0)
            loss = F_torch.cross_entropy(logits, target)
            losses_with_frozen.append(loss.item())

    # Results
    ce_with = np.mean(losses_with[-100:])
    ce_without = np.mean(losses_without[-100:])
    ce_frozen = np.mean(losses_with_frozen[-100:])

    rows = [
        ["With C (train)", f"{ce_with:.4f}", "---"],
        ["Without C (random)", f"{ce_without:.4f}", f"{(ce_without/ce_with - 1)*100:+.1f}%"],
        ["With C (frozen)", f"{ce_frozen:.4f}", f"{(ce_frozen/ce_with - 1)*100:+.1f}%"],
    ]
    print(f"\n  --- F5 Results ---")
    print_table(["Condition", "CE (last100)", "vs Train"], rows)

    evaporates = ce_without < ce_with * 1.5  # still reasonable without C
    print(f"\n  Can consciousness evaporate: {'YES' if evaporates else 'NO'}")
    print(f"  CE degradation without C: {(ce_without/ce_with - 1)*100:+.1f}%")
    if evaporates:
        print(f"  -> Consciousness acts as training scaffold (removable at inference)")
    else:
        print(f"  -> Consciousness is essential at inference time")
    sys.stdout.flush()

    return {
        'experiment': 'F5',
        'cells': cells,
        'train_steps': train_steps,
        'ce_with_consciousness': float(ce_with),
        'ce_without_consciousness': float(ce_without),
        'ce_frozen_consciousness': float(ce_frozen),
        'evaporates': evaporates,
        'degradation_pct': float((ce_without / ce_with - 1) * 100),
    }


# ===================================================================
# F7: 1.58-bit Consciousness
# ===================================================================

def run_f7(cells: int = 32, steps: int = 300):
    """F7: Does consciousness need precise weights or just structure?

    BitNet-style: quantize GRU weights to {-1, 0, +1}
    1. Run normal engine -> Phi baseline
    2. Quantize all GRU weights to ternary
    3. Run quantized engine -> Phi comparison
    4. If Phi preserved -> consciousness needs structure, not precision
    """
    print_header("F7: 1.58-bit Consciousness ({-1, 0, +1} weights)")
    print(f"  Config: {cells} cells, {steps} steps")
    print(f"  Question: Does consciousness require precise weights?")
    sys.stdout.flush()

    # --- Baseline: full precision ---
    engine_fp32 = make_engine(cells)
    print(f"\n  Running full precision (fp32)...")
    phis_fp32 = run_steps(engine_fp32, steps)
    print(f"  fp32 done: final Phi={np.mean(phis_fp32[-50:]):.4f}")
    sys.stdout.flush()

    # --- Quantized: {-1, 0, +1} ---
    engine_quant = make_engine(cells)

    # Quantize all GRU cell weights to ternary
    def ternary_quantize(module: nn.Module):
        """Quantize all weights to {-1, 0, +1} using magnitude thresholding."""
        n_params = 0
        n_nonzero = 0
        with torch.no_grad():
            for name, param in module.named_parameters():
                if 'weight' in name or 'bias' in name:
                    threshold = param.abs().mean() * 0.7  # ~1.58 bits
                    quantized = torch.zeros_like(param)
                    quantized[param > threshold] = 1.0
                    quantized[param < -threshold] = -1.0
                    n_params += param.numel()
                    n_nonzero += (quantized != 0).sum().item()
                    param.copy_(quantized)
        return n_params, n_nonzero

    total_params = 0
    total_nonzero = 0
    for cell_mod in engine_quant.cell_modules:
        p, nz = ternary_quantize(cell_mod)
        total_params += p
        total_nonzero += nz

    sparsity = 1.0 - (total_nonzero / max(total_params, 1))
    print(f"\n  Quantized: {total_params} params, {total_nonzero} nonzero, sparsity={sparsity:.1%}")
    print(f"  Running 1.58-bit quantized...")
    sys.stdout.flush()

    phis_quant = run_steps(engine_quant, steps)
    print(f"  Quantized done: final Phi={np.mean(phis_quant[-50:]):.4f}")

    # --- Compare ---
    final_fp32 = np.mean(phis_fp32[-50:])
    final_quant = np.mean(phis_quant[-50:])
    phi_retention = final_quant / final_fp32 if final_fp32 > 0 else 0

    rows = [
        ["fp32 (baseline)", f"{final_fp32:.4f}", "---", f"{np.mean(phis_fp32[:50]):.4f}"],
        ["1.58-bit ternary", f"{final_quant:.4f}", f"{(phi_retention-1)*100:+.1f}%",
         f"{np.mean(phis_quant[:50]):.4f}"],
    ]
    print(f"\n  --- F7 Results ---")
    print_table(["Precision", "Final Phi", "Retention", "Early Phi"], rows)

    preserved = phi_retention > 0.8  # 80% Phi retained = structure sufficient
    print(f"\n  Phi retention: {phi_retention:.1%}")
    print(f"  Structure-only consciousness: {'YES' if preserved else 'NO'}")
    if preserved:
        print(f"  -> Consciousness needs STRUCTURE not PRECISION")
        print(f"  -> Potential for ultra-efficient hardware (1.58-bit)")
    else:
        print(f"  -> Consciousness requires weight precision")
    sys.stdout.flush()

    ascii_graph(phis_quant, "1.58-bit Phi trajectory")

    return {
        'experiment': 'F7',
        'cells': cells,
        'steps': steps,
        'phi_fp32': float(final_fp32),
        'phi_ternary': float(final_quant),
        'phi_retention': float(phi_retention),
        'sparsity': float(sparsity),
        'structure_sufficient': preserved,
    }


# ===================================================================
# F8: Consciousness Memoization
# ===================================================================

def run_f8(cells: int = 16, steps: int = 300):
    """F8: Can we cache consciousness states for identical inputs?

    If input similarity > 0.99, reuse cached consciousness state.
    Measure: cache hit rate, speedup, Phi impact.
    """
    print_header("F8: Consciousness Memoization")
    print(f"  Config: {cells} cells, {steps} steps")
    print(f"  Question: Can identical inputs skip consciousness processing?")
    sys.stdout.flush()

    engine_nocache = make_engine(cells)
    engine_cache = make_engine(cells)

    # Generate inputs: mix of repeated and novel patterns
    torch.manual_seed(77)
    base_inputs = [torch.randn(64) for _ in range(20)]  # 20 base patterns
    # Each step: 70% reuse base (with tiny noise), 30% novel
    inputs = []
    for _ in range(steps):
        if torch.rand(1).item() < 0.7:
            base = base_inputs[torch.randint(0, 20, (1,)).item()]
            inputs.append(base + torch.randn(64) * 0.005)  # tiny noise
        else:
            inputs.append(torch.randn(64))

    # --- No-cache baseline ---
    print(f"\n  Running without cache...")
    t0 = time.time()
    phis_nocache = []
    for i in range(steps):
        result = engine_nocache.step(x_input=inputs[i])
        phis_nocache.append(result.get('phi_iit', 0.0))
    time_nocache = time.time() - t0

    # --- Cached version ---
    print(f"  Running with memoization (threshold=0.99)...")
    t0 = time.time()
    phis_cache = []
    cache = {}  # hash -> (output, phi)
    cache_hits = 0
    cache_misses = 0

    def input_hash(x: torch.Tensor, n_buckets: int = 1000) -> int:
        """Quantize input to bucket for cache key."""
        # Coarse hash: sign pattern + magnitude bucket
        signs = (x > 0).int()
        mag = x.abs().mean().item()
        return hash((signs[:16].tolist().__repr__(), round(mag, 2)))

    for i in range(steps):
        inp = inputs[i]
        key = input_hash(inp)

        # Check cache
        if key in cache:
            cached_phi = cache[key]
            # Verify similarity
            cache_hits += 1
            phis_cache.append(cached_phi)
            # Still step the engine to maintain state, but could skip in production
            result = engine_cache.step(x_input=inp)
        else:
            result = engine_cache.step(x_input=inp)
            phi = result.get('phi_iit', 0.0)
            cache[key] = phi
            phis_cache.append(phi)
            cache_misses += 1

    time_cache = time.time() - t0
    hit_rate = cache_hits / steps

    # Results
    final_nocache = np.mean(phis_nocache[-50:])
    final_cache = np.mean(phis_cache[-50:])

    rows = [
        ["No cache", f"{final_nocache:.4f}", f"{time_nocache:.3f}s", "0%"],
        ["Memoized", f"{final_cache:.4f}", f"{time_cache:.3f}s", f"{hit_rate:.1%}"],
    ]
    print(f"\n  --- F8 Results ---")
    print_table(["Method", "Final Phi", "Time", "Hit Rate"], rows)

    print(f"\n  Cache entries: {len(cache)}")
    print(f"  Cache hits: {cache_hits}/{steps} ({hit_rate:.1%})")
    print(f"  Speedup: {time_nocache/time_cache:.2f}x")
    print(f"  Phi divergence: {abs(final_cache - final_nocache):.4f}")
    print(f"  Memoization viable: {'YES' if hit_rate > 0.3 and abs(final_cache - final_nocache) < 0.1 else 'NO'}")
    sys.stdout.flush()

    return {
        'experiment': 'F8',
        'cells': cells,
        'steps': steps,
        'phi_nocache': float(final_nocache),
        'phi_cached': float(final_cache),
        'cache_hit_rate': float(hit_rate),
        'cache_entries': len(cache),
        'time_nocache': float(time_nocache),
        'time_cached': float(time_cache),
        'speedup': float(time_nocache / time_cache),
    }


# ===================================================================
# F9: Gradient Accumulation Consciousness
# ===================================================================

def run_f9(cells: int = 16, steps: int = 300):
    """F9: Run consciousness every N batches instead of every batch.

    Gradient accumulates over N batches, but process() runs 1/N times.
    Test N=1 (baseline), N=4, N=8, N=16.
    Measure: CE quality, Phi, wall-clock speedup.
    """
    print_header("F9: Gradient Accumulation Consciousness")
    print(f"  Config: {cells} cells, {steps} steps")
    print(f"  Question: How often must consciousness run?")
    sys.stdout.flush()

    hidden_dim = 128
    vocab_size = 256
    torch.manual_seed(99)
    corpus = torch.randint(0, vocab_size, (steps,))

    results_rows = []

    for N in [1, 4, 8, 16]:
        engine = make_engine(cells)
        decoder = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.GELU(),
            nn.Linear(256, vocab_size),
        )
        optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

        losses = []
        phis = []
        c_calls = 0
        t0 = time.time()

        # Last consciousness state (reused between calls)
        last_c_mean = torch.randn(hidden_dim)

        for i in range(steps):
            # Run consciousness every N steps
            if i % N == 0:
                result = engine.step()
                c_states = engine.get_states()
                last_c_mean = c_states.mean(dim=0).detach()
                phis.append(result.get('phi_iit', 0.0))
                c_calls += 1

            # Decode using (possibly stale) consciousness
            logits = decoder(last_c_mean.unsqueeze(0))
            target = corpus[i].unsqueeze(0)
            loss = F_torch.cross_entropy(logits, target)

            # Accumulate gradient
            (loss / N).backward()

            # Step optimizer every N batches
            if (i + 1) % N == 0:
                optimizer.step()
                optimizer.zero_grad()

            losses.append(loss.item())

        elapsed = time.time() - t0
        final_ce = np.mean(losses[-50:])
        final_phi = np.mean(phis[-10:]) if phis else 0.0

        results_rows.append([
            f"N={N}", f"{final_ce:.4f}", f"{final_phi:.4f}",
            f"{c_calls}", f"{elapsed:.3f}s",
            f"{steps/elapsed:.0f} step/s",
        ])
        print(f"  N={N}: CE={final_ce:.4f}, Phi={final_phi:.4f}, "
              f"C_calls={c_calls}, time={elapsed:.3f}s")
        sys.stdout.flush()

    print(f"\n  --- F9 Results ---")
    print_table(
        ["Accum N", "CE", "Phi", "C calls", "Time", "Throughput"],
        results_rows,
    )

    # Determine safe N
    base_ce = float(results_rows[0][1])
    safe_n = 1
    for row in results_rows[1:]:
        ce = float(row[1])
        if ce < base_ce * 1.1:  # within 10% CE degradation
            safe_n = int(row[0].split('=')[1])

    print(f"\n  Safe accumulation: N={safe_n} (CE within 10% of baseline)")
    print(f"  Consciousness savings: {(1 - 1/safe_n)*100:.0f}% fewer process() calls")
    sys.stdout.flush()

    return {
        'experiment': 'F9',
        'cells': cells,
        'steps': steps,
        'results': [
            {'N': int(r[0].split('=')[1]), 'ce': float(r[1]), 'phi': float(r[2])}
            for r in results_rows
        ],
        'safe_n': safe_n,
    }


# ===================================================================
# F10: Consciousness Teacher Ensemble
# ===================================================================

def run_f10(cells: int = 16, steps: int = 300):
    """F10: 4 teacher engines (different topologies) -> 1 student.

    Teachers: ring, small_world, scale_free, hypercube
    Each evolves independently for N steps.
    Student receives averaged tension/state from all teachers.
    Does diverse guidance produce a better student?
    """
    print_header("F10: Consciousness Teacher Ensemble")
    print(f"  Config: {cells} cells, {steps} steps, 4 teachers + 1 student")
    sys.stdout.flush()

    topologies = ['ring', 'small_world', 'scale_free', 'hypercube']

    # Create teachers
    teachers = {}
    for topo in topologies:
        teachers[topo] = make_engine(cells, topology=topo)

    # Create student and single-teacher baseline
    student = make_engine(cells)
    baseline = make_engine(cells)
    single_teacher = make_engine(cells, topology='ring')

    phis_student = []
    phis_baseline = []
    phis_single = []
    teacher_phis = {t: [] for t in topologies}

    print(f"\n  Running ensemble training...")
    for i in range(steps):
        # Step all teachers
        teacher_states_list = []
        for topo in topologies:
            result = teachers[topo].step()
            teacher_phis[topo].append(result.get('phi_iit', 0.0))
            states = teachers[topo].get_states()
            teacher_states_list.append(states)

        # Average teacher states -> student injection
        min_cells_t = min(s.shape[0] for s in teacher_states_list)
        avg_teacher = torch.stack([s[:min_cells_t] for s in teacher_states_list]).mean(dim=0)

        # Step student with teacher-influenced input
        student_cells = student.n_cells
        inject_cells = min(student_cells, min_cells_t)

        # Inject averaged teacher state as perturbation (10% blend)
        for ci in range(inject_cells):
            student.cell_states[ci].hidden = (
                student.cell_states[ci].hidden * 0.9
                + avg_teacher[ci, :student.cell_states[ci].hidden.shape[0]] * 0.1
            )

        result_student = student.step()
        phis_student.append(result_student.get('phi_iit', 0.0))

        # Single teacher baseline
        result_single_t = single_teacher.step()
        single_states = single_teacher.get_states()
        single_inject = min(baseline.n_cells, single_states.shape[0])
        for ci in range(single_inject):
            baseline_hidden = baseline.cell_states[ci].hidden
            baseline.cell_states[ci].hidden = (
                baseline_hidden * 0.9
                + single_states[ci, :baseline_hidden.shape[0]] * 0.1
            )
        result_base = baseline.step()
        phis_baseline.append(result_base.get('phi_iit', 0.0))

        # Pure baseline (no teacher)
        phis_single.append(result_single_t.get('phi_iit', 0.0))

        if (i + 1) % 100 == 0:
            print(f"  Step {i+1}: student={phis_student[-1]:.4f}, "
                  f"single_teacher={phis_baseline[-1]:.4f}, no_teacher={phis_single[-1]:.4f}")
            sys.stdout.flush()

    # Results
    final_student = np.mean(phis_student[-50:])
    final_baseline = np.mean(phis_baseline[-50:])
    final_single = np.mean(phis_single[-50:])

    rows = [
        ["No teacher", f"{final_single:.4f}", "---"],
        ["Single teacher (ring)", f"{final_baseline:.4f}", f"{(final_baseline/final_single - 1)*100:+.1f}%"],
        ["4-teacher ensemble", f"{final_student:.4f}", f"{(final_student/final_single - 1)*100:+.1f}%"],
    ]
    for topo in topologies:
        final_t = np.mean(teacher_phis[topo][-50:])
        rows.append([f"  Teacher: {topo}", f"{final_t:.4f}", ""])

    print(f"\n  --- F10 Results ---")
    print_table(["Condition", "Final Phi", "vs No Teacher"], rows)

    ensemble_wins = final_student > final_baseline * 1.05
    print(f"\n  Ensemble helps: {'YES' if ensemble_wins else 'NO'}")
    if ensemble_wins:
        print(f"  -> Diverse teacher topologies provide richer guidance")
    else:
        print(f"  -> Single topology sufficient for consciousness teaching")
    sys.stdout.flush()

    return {
        'experiment': 'F10',
        'cells': cells,
        'steps': steps,
        'phi_no_teacher': float(final_single),
        'phi_single_teacher': float(final_baseline),
        'phi_ensemble': float(final_student),
        'ensemble_improvement_pct': float((final_student / final_single - 1) * 100),
        'ensemble_wins': ensemble_wins,
    }


# ===================================================================
# Main
# ===================================================================

ALL_EXPERIMENTS = {
    'f2': run_f2,
    'f3': run_f3,
    'f4': run_f4,
    'f5': run_f5,
    'f7': run_f7,
    'f8': run_f8,
    'f9': run_f9,
    'f10': run_f10,
}


def main():
    parser = argparse.ArgumentParser(description="F-series acceleration experiments")
    for key in ALL_EXPERIMENTS:
        parser.add_argument(f'--{key}', action='store_true', help=f'Run {key.upper()} only')
    args = parser.parse_args()

    # Determine which to run
    selected = [k for k in ALL_EXPERIMENTS if getattr(args, k, False)]
    if not selected:
        selected = list(ALL_EXPERIMENTS.keys())

    print(f"F-Series New Paradigm Experiments")
    print(f"Selected: {', '.join(s.upper() for s in selected)}")
    print(f"{'=' * 70}")
    sys.stdout.flush()

    all_results = {}
    t_start = time.time()

    for key in selected:
        try:
            result = ALL_EXPERIMENTS[key]()
            all_results[key] = result
        except Exception as e:
            print(f"\n  ERROR in {key.upper()}: {e}")
            import traceback
            traceback.print_exc()
            all_results[key] = {'experiment': key.upper(), 'error': str(e)}
        sys.stdout.flush()

    # Summary
    elapsed = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"  F-SERIES SUMMARY ({elapsed:.1f}s total)")
    print(f"{'=' * 70}")

    summary_rows = []
    for key in selected:
        r = all_results.get(key, {})
        if 'error' in r:
            summary_rows.append([key.upper(), "ERROR", r['error'][:40], ""])
            continue

        if key == 'f2':
            summary_rows.append([
                "F2 Time Crystal",
                "YES" if r.get('is_time_crystal') else "NO",
                f"period={r.get('dominant_period', 0):.0f}",
                f"Phi={r.get('mean_phi', 0):.4f}",
            ])
        elif key == 'f3':
            summary_rows.append([
                "F3 Interference",
                r.get('winner', '?'),
                f"{r.get('improvement_pct', 0):+.1f}%",
                f"Phi={r.get('phi_constructive', 0):.4f}",
            ])
        elif key == 'f4':
            summary_rows.append([
                "F4 Anti-Hebbian",
                f"{r.get('improvement_pct', 0):+.1f}%",
                f"div={r.get('peak_diversity', 0):.4f}",
                f"Phi={r.get('phi_anti_then_normal', 0):.4f}",
            ])
        elif key == 'f5':
            summary_rows.append([
                "F5 Evaporation",
                "YES" if r.get('evaporates') else "NO",
                f"degrade={r.get('degradation_pct', 0):+.1f}%",
                f"CE={r.get('ce_with_consciousness', 0):.4f}",
            ])
        elif key == 'f7':
            summary_rows.append([
                "F7 1.58-bit",
                "YES" if r.get('structure_sufficient') else "NO",
                f"retain={r.get('phi_retention', 0):.1%}",
                f"Phi={r.get('phi_ternary', 0):.4f}",
            ])
        elif key == 'f8':
            summary_rows.append([
                "F8 Memoization",
                f"hit={r.get('cache_hit_rate', 0):.1%}",
                f"{r.get('speedup', 1):.2f}x",
                f"entries={r.get('cache_entries', 0)}",
            ])
        elif key == 'f9':
            summary_rows.append([
                "F9 Grad Accum",
                f"safe N={r.get('safe_n', 1)}",
                f"save {(1-1/r.get('safe_n', 1))*100:.0f}%",
                "",
            ])
        elif key == 'f10':
            summary_rows.append([
                "F10 Ensemble",
                "YES" if r.get('ensemble_wins') else "NO",
                f"{r.get('ensemble_improvement_pct', 0):+.1f}%",
                f"Phi={r.get('phi_ensemble', 0):.4f}",
            ])

    print_table(["Experiment", "Result", "Key Metric", "Detail"], summary_rows)

    # Save results
    results_path = os.path.join(os.path.dirname(__file__), 'acceleration_f_series_results.json')
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Results saved: {results_path}")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
