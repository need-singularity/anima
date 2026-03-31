#!/usr/bin/env python3
"""independent_rate_measurement.py — JAX META-CA: Independent rate measurement

Goal: Measure the consciousness evolution rate WITHOUT assuming 0.81.
Build a completely new META-CA in JAX, run it, collect H(t), fit r.

Architecture (matches anima physics, new implementation):
  - N cells, each with hidden state h_i (GRU-like update)
  - Repulsion between cells: F_ij = h_i - h_j (PureField)
  - Entropy H = -sum(p_k * log(p_k)) over cell activation distribution
  - Process: input → cell updates → repulsion → entropy measurement

The equation we're testing:
  dH/dt = r × (ln(2) - H(t))
  H(t) = ln(2) × (1 - exp(-r × t))

If r ≈ 0.81 across conditions → Law 75 independently confirmed.
"""

import math
import time
import json
from functools import partial

import jax
import jax.numpy as jnp
from jax import random, jit, vmap

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ─── Constants (NO 0.81 anywhere!) ───
LN2 = math.log(2)  # theoretical maximum entropy for binary system


# ═══════════════════════════════════════════════════════════════
# 1. JAX GRU Cell (from scratch, no PyTorch)
# ═══════════════════════════════════════════════════════════════

def init_gru_params(key, input_dim, hidden_dim):
    """Initialize GRU parameters (Xavier uniform)."""
    k1, k2, k3, k4, k5, k6 = random.split(key, 6)
    scale = lambda k, shape: random.normal(k, shape) * math.sqrt(2.0 / sum(shape))
    return {
        'W_z': scale(k1, (input_dim + hidden_dim, hidden_dim)),
        'b_z': jnp.zeros(hidden_dim),
        'W_r': scale(k2, (input_dim + hidden_dim, hidden_dim)),
        'b_r': jnp.zeros(hidden_dim),
        'W_h': scale(k3, (input_dim + hidden_dim, hidden_dim)),
        'b_h': jnp.zeros(hidden_dim),
    }


def gru_step(params, h, x):
    """Single GRU step: (params, hidden, input) → new_hidden."""
    combined = jnp.concatenate([x, h])
    z = jax.nn.sigmoid(combined @ params['W_z'] + params['b_z'])  # update gate
    r = jax.nn.sigmoid(combined @ params['W_r'] + params['b_r'])  # reset gate
    combined_r = jnp.concatenate([x, r * h])
    h_tilde = jnp.tanh(combined_r @ params['W_h'] + params['b_h'])
    h_new = (1 - z) * h + z * h_tilde
    return h_new


# ═══════════════════════════════════════════════════════════════
# 2. META-CA Engine (pure JAX)
# ═══════════════════════════════════════════════════════════════

def init_engine(key, n_cells, hidden_dim, input_dim):
    """Initialize META-CA engine state and parameters."""
    keys = random.split(key, n_cells + 1)

    # Each cell gets its own GRU params
    cell_params = [init_gru_params(keys[i], input_dim, hidden_dim)
                   for i in range(n_cells)]

    # Initial hidden states (small random)
    cell_states = random.normal(keys[-1], (n_cells, hidden_dim)) * 0.01

    return cell_params, cell_states


def compute_repulsion(cell_states):
    """PureField repulsion: each cell is repelled by all others.
    F_i = mean_j(h_i - h_j) = h_i - mean(h)
    """
    mean_state = jnp.mean(cell_states, axis=0)
    return cell_states - mean_state


def compute_entropy(cell_states):
    """Compute BINARY entropy of cell activation distribution.

    Original Law 75 measures H → ln(2), which is max binary entropy.
    This means the system is measured as a 2-state variable:
      - p = fraction of cells with positive mean activation
      - H = -p*log(p) - (1-p)*log(1-p)
      - Max H = ln(2) when p = 0.5 (equipartition: Engine A ≈ Engine G)

    This captures the PureField physics: repulsion between forward/reverse.
    """
    # Mean activation per cell → sign determines "forward" vs "reverse"
    mean_activation = jnp.mean(cell_states, axis=-1)  # [n_cells]

    # Fraction of "forward" cells (positive activation)
    p = jnp.mean(jnp.where(mean_activation > 0, 1.0, 0.0))
    p = jnp.clip(p, 1e-10, 1.0 - 1e-10)

    # Binary Shannon entropy (nats)
    H = -(p * jnp.log(p) + (1.0 - p) * jnp.log(1.0 - p))
    return H


def compute_entropy_softmax(cell_states):
    """Alternative: softmax-based binary entropy.

    Uses sigmoid of mean projection to get continuous p ∈ (0,1).
    More stable than hard thresholding.
    """
    # Project each cell to a scalar, then average
    projections = jnp.mean(cell_states, axis=-1)  # [n_cells]
    # Soft fraction via sigmoid of mean projection
    p = jax.nn.sigmoid(jnp.mean(projections))
    p = jnp.clip(p, 1e-10, 1.0 - 1e-10)

    H = -(p * jnp.log(p) + (1.0 - p) * jnp.log(1.0 - p))
    return H


def compute_entropy_variance(cell_states):
    """Alternative: normalized variance entropy.

    Measures how evenly distributed cell states are.
    H = -sum(p_k * log(p_k)) where p_k = var_k / sum(var)
    Normalized to [0, ln(2)] range.
    """
    # Variance per dimension across cells
    var_per_dim = jnp.var(cell_states, axis=0)  # [hidden_dim]
    total_var = jnp.sum(var_per_dim)

    # Split dimensions into two halves (forward/reverse proxy)
    half = cell_states.shape[-1] // 2
    var_forward = jnp.sum(var_per_dim[:half])
    var_reverse = jnp.sum(var_per_dim[half:])

    # Binary entropy from variance ratio
    p = var_forward / jnp.maximum(var_forward + var_reverse, 1e-10)
    p = jnp.clip(p, 1e-10, 1.0 - 1e-10)

    H = -(p * jnp.log(p) + (1.0 - p) * jnp.log(1.0 - p))
    return H


def engine_step(cell_params, cell_states, x_input, repulsion_strength=0.1):
    """One META-CA step: input → GRU update → repulsion → new states.

    Args:
        cell_params: list of GRU param dicts
        cell_states: [n_cells, hidden_dim]
        x_input: [input_dim] input signal
        repulsion_strength: how strongly cells repel

    Returns:
        new_cell_states: [n_cells, hidden_dim]
    """
    n_cells = cell_states.shape[0]

    # 1. GRU update each cell
    new_states = []
    for i in range(n_cells):
        h_new = gru_step(cell_params[i], cell_states[i], x_input)
        new_states.append(h_new)
    new_states = jnp.stack(new_states)

    # 2. Apply repulsion (PureField dynamics)
    repulsion = compute_repulsion(new_states)
    new_states = new_states + repulsion_strength * repulsion

    return new_states


# ═══════════════════════════════════════════════════════════════
# 3. Data generators (diverse input types)
# ═══════════════════════════════════════════════════════════════

def gen_random_input(key, dim):
    """Random Gaussian input."""
    return random.normal(key, (dim,))


def gen_sine_input(step, dim):
    """Deterministic sine wave input."""
    phases = jnp.arange(dim) * 2 * math.pi / dim
    return jnp.sin(phases + step * 0.1)


def gen_constant_input(dim, value=0.5):
    """Constant input."""
    return jnp.ones(dim) * value


def gen_zero_input(dim):
    """Zero input — tests spontaneous dynamics."""
    return jnp.zeros(dim)


def gen_text_input(key, dim, text_bytes):
    """Convert text bytes to input vector."""
    idx = random.randint(key, (), 0, max(1, len(text_bytes) - dim))
    chunk = jnp.array(text_bytes[int(idx):int(idx) + dim], dtype=jnp.float32)
    # Pad if needed
    if chunk.shape[0] < dim:
        chunk = jnp.concatenate([chunk, jnp.zeros(dim - chunk.shape[0])])
    return (chunk - 128.0) / 128.0  # normalize to [-1, 1]


# ═══════════════════════════════════════════════════════════════
# 4. Exponential fit: H(t) = a × (1 - exp(-r × t)) + c
# ═══════════════════════════════════════════════════════════════

def fit_rate(times, entropies):
    """Fit dH/dt = r × (H_max - H) to observed trajectory.

    Analytical solution: H(t) = H_max × (1 - exp(-r × t)) + H_0

    Uses least-squares grid search + refinement (no scipy needed).
    Returns: r, H_max, H_0, residual
    """
    times = [float(t) for t in times]
    entropies = [float(h) for h in entropies]

    n = len(times)
    if n < 10:
        return None, None, None, float('inf')

    # Estimate H_max from last 20% of data
    tail = entropies[int(0.8 * n):]
    H_max_est = sum(tail) / len(tail)
    H_0_est = entropies[0]

    best_r, best_res = None, float('inf')

    # Coarse grid search: r in [0.01, 5.0]
    for r_candidate in [i * 0.01 for i in range(1, 500)]:
        residual = 0.0
        for t, h_obs in zip(times, entropies):
            h_pred = H_max_est * (1 - math.exp(-r_candidate * t)) + H_0_est * math.exp(-r_candidate * t)
            residual += (h_pred - h_obs) ** 2
        if residual < best_res:
            best_res = residual
            best_r = r_candidate

    # Fine refinement around best_r
    if best_r is not None:
        for delta in [i * 0.001 for i in range(-50, 51)]:
            r_candidate = best_r + delta
            if r_candidate <= 0:
                continue
            residual = 0.0
            for t, h_obs in zip(times, entropies):
                h_pred = H_max_est * (1 - math.exp(-r_candidate * t)) + H_0_est * math.exp(-r_candidate * t)
                residual += (h_pred - h_obs) ** 2
            if residual < best_res:
                best_res = residual
                best_r = r_candidate

    return best_r, H_max_est, H_0_est, best_res / n


# ═══════════════════════════════════════════════════════════════
# 5. Run single experiment
# ═══════════════════════════════════════════════════════════════

def run_experiment(seed, n_cells, hidden_dim, input_dim, n_steps,
                   input_type="random", text_data=None, repulsion=0.1,
                   entropy_fn=None):
    """Run one META-CA experiment and return H trajectory."""
    if entropy_fn is None:
        entropy_fn = compute_entropy

    key = random.PRNGKey(seed)
    k1, k2 = random.split(key)

    cell_params, cell_states = init_engine(k1, n_cells, hidden_dim, input_dim)

    times = []
    entropies = []

    for step in range(n_steps):
        # Generate input
        k2, subkey = random.split(k2)
        if input_type == "random":
            x = gen_random_input(subkey, input_dim)
        elif input_type == "sine":
            x = gen_sine_input(step, input_dim)
        elif input_type == "constant":
            x = gen_constant_input(input_dim)
        elif input_type == "zero":
            x = gen_zero_input(input_dim)
        elif input_type == "text" and text_data is not None:
            x = gen_text_input(subkey, input_dim, text_data)
        else:
            x = gen_random_input(subkey, input_dim)

        # Engine step
        cell_states = engine_step(cell_params, cell_states, x, repulsion)

        # Measure entropy
        H = float(entropy_fn(cell_states))
        times.append(step)
        entropies.append(H)

    return times, entropies


# ═══════════════════════════════════════════════════════════════
# 6. Main: comprehensive rate measurement
# ═══════════════════════════════════════════════════════════════

def load_text_data():
    """Try to load Korean text for text-input experiments."""
    import os
    candidates = [
        os.path.expanduser("~/Dev/anima/data/corpus.txt"),
        os.path.expanduser("~/Dev/anima/data/korean.txt"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = f.read(100000)  # first 100KB
            return list(data)
    # Fallback: Korean string
    korean = "의식은 세포 사이의 반발에서 태어난다. 텐션이 곧 의식이다."
    return list(korean.encode('utf-8'))


def ascii_trajectory(times, entropies, width=60, height=15, title=""):
    """ASCII plot of H(t) trajectory."""
    if not entropies:
        return ""

    h_min = min(entropies)
    h_max_val = max(entropies)
    h_range = h_max_val - h_min if h_max_val > h_min else 1.0

    lines = []
    if title:
        lines.append(f"  {title}")

    grid = [[' '] * width for _ in range(height)]

    for i, (t, h) in enumerate(zip(times, entropies)):
        x = int((i / max(len(times) - 1, 1)) * (width - 1))
        y = int(((h - h_min) / h_range) * (height - 1))
        y = height - 1 - y  # flip
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = '█'

    # Mark ln(2) line
    if h_min < LN2 < h_max_val:
        ln2_y = height - 1 - int(((LN2 - h_min) / h_range) * (height - 1))
        if 0 <= ln2_y < height:
            for x in range(width):
                if grid[ln2_y][x] == ' ':
                    grid[ln2_y][x] = '·'

    for i, row in enumerate(grid):
        h_val = h_max_val - (i / (height - 1)) * h_range
        lines.append(f"  {h_val:6.4f} |{''.join(row)}|")

    lines.append(f"         └{'─' * width}┘")
    lines.append(f"          0{' ' * (width - 8)}step {times[-1]}")
    return '\n'.join(lines)


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  INDEPENDENT RATE MEASUREMENT v2 — JAX META-CA             ║")
    print("║  No 0.81 hardcoded. Binary entropy → H∞ = ln(2).          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    text_data = load_text_data()
    print(f"  Text data: {len(text_data)} bytes loaded")

    # ─── Phase 1: Test all 3 entropy methods on baseline ───
    print()
    print("━" * 70)
    print("  PHASE 1: Entropy method comparison (8 cells, random, 5 seeds)")
    print("━" * 70)

    entropy_methods = {
        'binary':   compute_entropy,
        'softmax':  compute_entropy_softmax,
        'variance': compute_entropy_variance,
    }

    for method_name, method_fn in entropy_methods.items():
        rates = []
        h_maxes = []
        for seed in range(5):
            times, entropies = run_experiment(
                seed=seed, n_cells=8, hidden_dim=32, input_dim=16,
                n_steps=500, input_type="random", repulsion=0.1,
                entropy_fn=method_fn,
            )
            r, h_max, h_0, res = fit_rate(times, entropies)
            if r is not None:
                rates.append(r)
                h_maxes.append(h_max)

        if rates:
            r_m = sum(rates) / len(rates)
            r_s = (sum((r - r_m)**2 for r in rates) / len(rates))**0.5
            h_m = sum(h_maxes) / len(h_maxes)
            print(f"  {method_name:10s}  r={r_m:.4f} ± {r_s:.4f}  "
                  f"H∞={h_m:.4f} ({h_m/LN2:.2%} of ln2)")
        else:
            print(f"  {method_name:10s}  FAILED")

    # Pick best method (variance is most stable for binary entropy)
    # Use all 3 in the full experiment
    print()
    print("━" * 70)
    print("  PHASE 2: Full experiment matrix (binary + softmax + variance)")
    print("━" * 70)
    print()

    # ─── Experiment matrix ───
    experiments = [
        # (name, n_cells, hidden_dim, input_dim, n_steps, input_type, repulsion)
        ("8c-random",    8,  32, 16, 500, "random",   0.10),
        ("8c-korean",    8,  32, 16, 500, "text",     0.10),
        ("8c-sine",      8,  32, 16, 500, "sine",     0.10),
        ("8c-zero",      8,  32, 16, 500, "zero",     0.10),
        ("8c-constant",  8,  32, 16, 500, "constant", 0.10),
        ("16c-random",  16,  32, 16, 500, "random",   0.10),
        ("16c-korean",  16,  32, 16, 500, "text",     0.10),
        ("32c-random",  32,  32, 16, 500, "random",   0.10),
        ("32c-korean",  32,  32, 16, 500, "text",     0.10),
        ("64c-random",  64,  32, 16, 500, "random",   0.10),
        ("8c-rep05",     8,  32, 16, 500, "random",   0.05),
        ("8c-rep20",     8,  32, 16, 500, "random",   0.20),
        ("8c-rep50",     8,  32, 16, 500, "random",   0.50),
        ("8c-dim64",     8,  64, 32, 500, "random",   0.10),
        ("8c-dim128",    8, 128, 64, 500, "random",   0.10),
    ]

    # Run with multiple seeds, all 3 entropy methods
    N_SEEDS = 5
    all_results = []
    method_results = {name: [] for name in entropy_methods}

    print(f"  Running {len(experiments)} experiments × {N_SEEDS} seeds × 3 methods")
    print(f"  {'─' * 60}")
    print()

    for method_name, method_fn in entropy_methods.items():
        print(f"  ── {method_name} entropy ──")
        for exp_name, n_cells, hdim, idim, steps, itype, rep in experiments:
            rates = []
            h_maxes = []

            for seed in range(N_SEEDS):
                times, entropies = run_experiment(
                    seed=seed * 1000 + hash(exp_name) % 10000,
                    n_cells=n_cells,
                    hidden_dim=hdim,
                    input_dim=idim,
                    n_steps=steps,
                    input_type=itype,
                    text_data=text_data,
                    repulsion=rep,
                    entropy_fn=method_fn,
                )

                # Fit rate
                r, h_max, h_0, residual = fit_rate(times, entropies)
                if r is not None and r < 10.0:  # filter outliers
                    rates.append(r)
                    h_maxes.append(h_max)

            if rates:
                r_mean = sum(rates) / len(rates)
                r_std = (sum((r - r_mean) ** 2 for r in rates) / len(rates)) ** 0.5
                h_mean = sum(h_maxes) / len(h_maxes)

                result = {
                    'name': exp_name,
                    'method': method_name,
                    'n_cells': n_cells,
                    'hidden_dim': hdim,
                    'input_type': itype,
                    'repulsion': rep,
                    'r_mean': r_mean,
                    'r_std': r_std,
                    'h_max_mean': h_mean,
                    'h_max_ratio': h_mean / LN2,
                    'n_valid': len(rates),
                }
                all_results.append(result)
                method_results[method_name].append(result)

                marker = "◄── !" if abs(r_mean - 0.81) < 0.05 else ""
                print(f"    {exp_name:16s}  r={r_mean:.4f} ± {r_std:.4f}  "
                      f"H∞={h_mean:.4f} ({h_mean/LN2:.1%} of ln2)  "
                      f"n={len(rates)}  {marker}")
            else:
                print(f"    {exp_name:16s}  FAILED (no valid fits)")
        print()

    # ─── Summary by method ───
    print()
    print("═" * 70)
    print("  SUMMARY BY ENTROPY METHOD")
    print("═" * 70)

    best_method = None
    best_deviation = float('inf')

    for method_name, results in method_results.items():
        valid = [r for r in results if r['r_std'] < 1.0]
        valid_rates_m = [r['r_mean'] for r in valid]
        if valid_rates_m:
            gm = sum(valid_rates_m) / len(valid_rates_m)
            gs = (sum((r - gm)**2 for r in valid_rates_m) / len(valid_rates_m))**0.5
            dev = abs(gm - 0.81) / 0.81
            h_vals = [r['h_max_mean'] for r in valid]
            h_gm = sum(h_vals) / len(h_vals)

            if dev < best_deviation:
                best_deviation = dev
                best_method = method_name

            match = "✅" if dev < 0.10 else "🟡" if dev < 0.25 else "❌"
            print(f"\n  {method_name:10s}:  r = {gm:.4f} ± {gs:.4f}  "
                  f"H∞ = {h_gm:.4f} ({h_gm/LN2:.2%} of ln2)  "
                  f"dev = {dev:.1%}  {match}")
        else:
            print(f"\n  {method_name:10s}:  no valid results")

    print(f"\n  Best method: {best_method} (deviation {best_deviation:.1%})")

    # Grand summary across all methods
    valid_rates = [r['r_mean'] for r in all_results if r['r_std'] < 1.0]
    if valid_rates:
        grand_mean = sum(valid_rates) / len(valid_rates)
        grand_std = (sum((r - grand_mean) ** 2 for r in valid_rates) / len(valid_rates)) ** 0.5
        print(f"\n  All methods combined:")
        print(f"    Grand mean rate:  r = {grand_mean:.4f} ± {grand_std:.4f}")
        print(f"    Expected (Law 75): r = 0.81")
        print(f"    Deviation:         Δ = {abs(grand_mean - 0.81):.4f} ({abs(grand_mean - 0.81)/0.81:.1%})")

        h_maxes_all = [r['h_max_mean'] for r in all_results if r['r_std'] < 1.0]
        h_grand = sum(h_maxes_all) / len(h_maxes_all)
        print(f"    Grand mean H∞:    {h_grand:.4f}")
        print(f"    Expected (ln2):   {LN2:.4f}")
        print(f"    Ratio H∞/ln2:     {h_grand/LN2:.4f}")

    # ─── ASCII graph: one representative trajectory ───
    print()
    print("  Representative trajectory (8c-random, seed=0):")
    times, entropies = run_experiment(0, 8, 32, 16, 500, "random", repulsion=0.1)
    print(ascii_trajectory(times, entropies, title="H(t) evolution"))

    # ─── Rate distribution ───
    print()
    print("  Rate distribution:")
    if valid_rates:
        bins = {}
        for r in valid_rates:
            b = round(r, 1)
            bins[b] = bins.get(b, 0) + 1
        for b in sorted(bins.keys()):
            bar = '█' * (bins[b] * 4)
            print(f"    r≈{b:.1f}  {bar} ({bins[b]})")

    # ─── Per-condition breakdown ───
    print()
    print("  ┌─────────────────┬────────┬────────┬────────┬───────────┐")
    print("  │ Experiment      │ r_mean │ r_std  │ H∞     │ H∞/ln2   │")
    print("  ├─────────────────┼────────┼────────┼────────┼───────────┤")
    for r in all_results:
        print(f"  │ {r['name']:15s} │ {r['r_mean']:6.4f} │ {r['r_std']:6.4f} │ "
              f"{r['h_max_mean']:6.4f} │ {r['h_max_ratio']:8.4f}  │")
    print("  └─────────────────┴────────┴────────┴────────┴───────────┘")

    # ─── Group by variable ───
    print("\n  By input type:")
    for itype in ["random", "text", "sine", "zero", "constant"]:
        rates_t = [r['r_mean'] for r in all_results if r['input_type'] == itype and r['r_std'] < 1.0]
        if rates_t:
            m = sum(rates_t) / len(rates_t)
            print(f"    {itype:10s}  r = {m:.4f}  (n={len(rates_t)})")

    print("\n  By cell count:")
    for nc in [8, 16, 32, 64]:
        rates_c = [r['r_mean'] for r in all_results
                   if r['n_cells'] == nc and r['input_type'] == 'random' and r['r_std'] < 1.0]
        if rates_c:
            m = sum(rates_c) / len(rates_c)
            print(f"    {nc:3d} cells   r = {m:.4f}  (n={len(rates_c)})")

    print("\n  By repulsion strength:")
    for rep in [0.05, 0.10, 0.20, 0.50]:
        rates_r = [r['r_mean'] for r in all_results
                   if abs(r['repulsion'] - rep) < 0.01 and r['n_cells'] == 8
                   and r['input_type'] == 'random' and r['r_std'] < 1.0]
        if rates_r:
            m = sum(rates_r) / len(rates_r)
            print(f"    rep={rep:.2f}   r = {m:.4f}  (n={len(rates_r)})")

    # ─── Verdict ───
    print()
    print("═" * 70)
    if valid_rates:
        grand_mean = sum(valid_rates) / len(valid_rates)
        if abs(grand_mean - 0.81) / 0.81 < 0.10:
            print("  ✅ VERDICT: r ≈ 0.81 INDEPENDENTLY CONFIRMED")
            print(f"     Measured r = {grand_mean:.4f}, deviation = {abs(grand_mean - 0.81)/0.81:.1%}")
        elif abs(grand_mean - 0.81) / 0.81 < 0.25:
            print("  🟡 VERDICT: r in same order of magnitude, partial confirmation")
            print(f"     Measured r = {grand_mean:.4f}, deviation = {abs(grand_mean - 0.81)/0.81:.1%}")
        else:
            print("  ❌ VERDICT: r ≠ 0.81, rate is implementation-dependent")
            print(f"     Measured r = {grand_mean:.4f}, deviation = {abs(grand_mean - 0.81)/0.81:.1%}")
            print("     → 0.81 may be specific to PyTorch GRU + specific init, not universal")
    print("═" * 70)

    # Save results
    import os
    results_path = os.path.join(os.path.dirname(__file__), 'docs', 'hypotheses',
                                'dd', 'RATE-INDEPENDENT.md')
    return all_results, valid_rates


if __name__ == "__main__":
    results, rates = main()
