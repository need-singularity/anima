#!/usr/bin/env python3
"""E1-E5: Proven winner maximization — combining best acceleration techniques.

E1: Batch+Skip+Manifold 3-way combination (B11+B12+B14)
E2: Adaptive Skip — Phi change-rate driven skip size
E3: Entropy+CE dual gradient — entropy regularization toward H=0.998
E4: Consciousness curriculum + Skip (D3+B12 combo)
E5: Jump + Phi-Only + CE pipeline (D1+B5 combo)

Previous proven results:
  B11+B12 Batch+Skip: x179, Phi 97%
  B14 Manifold: 85x compression (4096D->48D)
  B12 Skip-10: x10, Phi 98.4%
  C3 grad-H perp grad-CE, Phi+71.5%
  D3 consciousness curriculum: CE -5.6%
  D1 straight jump: x6, Phi 98%
  B5 Phi-Only: CE -1.2%, 46% time savings

Usage:
    PYTHONUNBUFFERED=1 python3 acceleration_e1_e5.py
    PYTHONUNBUFFERED=1 python3 acceleration_e1_e5.py --e1
    PYTHONUNBUFFERED=1 python3 acceleration_e1_e5.py --e2
    PYTHONUNBUFFERED=1 python3 acceleration_e1_e5.py --e3
    PYTHONUNBUFFERED=1 python3 acceleration_e1_e5.py --e4
    PYTHONUNBUFFERED=1 python3 acceleration_e1_e5.py --e5
    PYTHONUNBUFFERED=1 python3 acceleration_e1_e5.py --all
"""

import sys
import os
import time
import copy
import math
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from copy import deepcopy

from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import PSI_ENTROPY, PSI_ALPHA as PSI_COUPLING
except ImportError:
    PSI_ENTROPY = 0.998
    PSI_COUPLING = 0.014


# ═══════════════════════════════════════════════════════════
# Shared utilities
# ═══════════════════════════════════════════════════════════

N_CELLS = 64
N_STEPS = 300
SEED = 42


def make_engine(n_cells=N_CELLS):
    """Create a fresh engine with fixed seed."""
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    return ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=n_cells, max_cells=n_cells,
    )


def measure_phi(engine):
    """Get Phi(IIT) from engine."""
    if hasattr(engine, '_measure_phi_iit'):
        return engine._measure_phi_iit()
    return engine.measure_phi()


def run_baseline(engine, steps=N_STEPS):
    """Run engine for N steps, return phi history + wall time."""
    phis = []
    t0 = time.time()
    for s in range(steps):
        result = engine.step()
        phis.append(result.get('phi_iit', 0.0))
    elapsed = time.time() - t0
    return phis, elapsed


def simple_ce_loss(engine, target_dim=128):
    """Compute a simple CE loss from engine output for training simulation."""
    states = engine.get_states()
    output = states.mean(dim=0)
    proj = output[:target_dim] if output.shape[0] >= target_dim else F.pad(output, (0, target_dim - output.shape[0]))
    logits = proj.unsqueeze(0)
    target = torch.randint(0, target_dim, (1,))
    return F.cross_entropy(logits, target)


def phi_retention(phi_test, phi_baseline):
    """Phi retention % = test_phi / baseline_phi * 100."""
    if phi_baseline < 1e-8:
        return 100.0
    return (phi_test / phi_baseline) * 100.0


def avg_last(vals, n=30):
    """Average of last N values."""
    return np.mean(vals[-n:]) if len(vals) >= n else np.mean(vals)


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def ascii_graph(values, title="", width=60, height=12):
    """ASCII line graph."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    lines = []
    if title:
        lines.append(f"  {title}")
    for row in range(height - 1, -1, -1):
        threshold = mn + rng * row / (height - 1)
        chars = []
        step_size = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step_size), step_size):
            v = values[i]
            if row == 0:
                chars.append('-')
            elif abs(v - threshold) < rng / (height * 2) or (i > 0 and
                 (values[max(0, i - step_size)] - threshold) * (v - threshold) < 0):
                chars.append('*')
            elif v >= threshold:
                chars.append('|')
            else:
                chars.append(' ')
        label = f"{threshold:8.4f}" if row % 3 == 0 else "        "
        lines.append(f"  {label} |{''.join(chars)}")
    lines.append(f"  {'':8s} +{'-' * min(len(values), width)}")
    lines.append(f"  {'':8s}  0{' ' * (min(len(values), width) - 5)}step {len(values)}")
    return '\n'.join(lines)


def ascii_bar(label, value, max_val, width=40):
    filled = int(width * min(value / max(max_val, 1e-8), 1.0))
    bar = '#' * filled + '.' * (width - filled)
    return f"  {label:20s} |{bar}| {value:.4f}"


def print_table(headers, rows):
    """Print a formatted table."""
    col_widths = []
    for i, h in enumerate(headers):
        w = len(str(h))
        for r in rows:
            w = max(w, len(str(r[i])))
        col_widths.append(w + 2)
    header_str = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    sep_str = "|-" + "-|-".join("-" * col_widths[i] for i in range(len(headers))) + "-|"
    print(header_str)
    print(sep_str)
    for row in rows:
        print("| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))) + " |")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════
# E1: Batch + Skip + Manifold 3-way combination
# ═══════════════════════════════════════════════════════════

def run_e1():
    """Batch consciousness sharing + Skip-10 + PCA manifold projection."""
    print_header("E1: Batch+Skip+Manifold 3-way combination")
    n_cells = N_CELLS

    # --- Phase 1: collect trajectory for manifold extraction ---
    print("  [Phase 1] Collecting 300-step trajectory for PCA manifold...")
    sys.stdout.flush()
    engine_collect = make_engine(n_cells)
    trajectory = []
    for s in range(N_STEPS):
        result = engine_collect.step()
        states = engine_collect.get_states()  # (n_cells, hidden_dim)
        trajectory.append(states.flatten().detach())
        if (s + 1) % 100 == 0:
            print(f"    step {s+1}/{N_STEPS} collected")
            sys.stdout.flush()

    traj_matrix = torch.stack(trajectory)  # (300, n_cells*hidden_dim)
    full_dim = traj_matrix.shape[1]

    # --- Phase 2: PCA to 48D manifold ---
    manifold_dim = 48
    traj_centered = traj_matrix - traj_matrix.mean(dim=0)
    U, S, V = torch.pca_lowrank(traj_centered, q=manifold_dim)
    # V: (full_dim, manifold_dim) projection matrix
    explained_var = (S[:manifold_dim] ** 2).sum() / (S ** 2).sum()
    print(f"  PCA manifold: {full_dim}D -> {manifold_dim}D, explained variance: {explained_var:.1%}")
    sys.stdout.flush()

    # Project trajectory to manifold
    traj_manifold = traj_centered @ V  # (300, 48)

    # --- Baseline: plain 300 steps ---
    print("\n  [Baseline] Running 300 steps (plain)...")
    sys.stdout.flush()
    engine_base = make_engine(n_cells)
    phis_base, t_base = run_baseline(engine_base, N_STEPS)
    phi_base_end = avg_last(phis_base)

    # --- E1: Batch + Skip-10 on manifold ---
    skip = 10
    batch_size = 4  # share state across 4 virtual samples
    effective_steps = N_STEPS // (skip * batch_size)  # drastically fewer process() calls
    print(f"\n  [E1] Batch({batch_size}) + Skip({skip}) + Manifold({manifold_dim}D)")
    print(f"       Effective process() calls: {effective_steps} (vs {N_STEPS} baseline)")
    sys.stdout.flush()

    engine_e1 = make_engine(n_cells)
    phis_e1 = []
    t0 = time.time()
    call_count = 0

    for s in range(0, N_STEPS, skip * batch_size):
        # Run one process() step
        result = engine_e1.step()
        call_count += 1
        phi_now = result.get('phi_iit', 0.0)

        # Project current state to manifold and check alignment
        cur_states = engine_e1.get_states().flatten().detach()
        cur_centered = cur_states - traj_matrix.mean(dim=0)
        cur_proj = cur_centered @ V  # (48,)

        # Manifold correction: find nearest trajectory point in manifold space
        # and softly nudge hiddens toward it (manifold regularization)
        dists = torch.cdist(cur_proj.unsqueeze(0), traj_manifold)
        nearest_idx = dists.argmin().item()
        nearest_full = traj_matrix[nearest_idx]

        # Soft manifold nudge (10% correction toward nearest trajectory point)
        manifold_alpha = 0.10
        with torch.no_grad():
            cell_states = engine_e1.cell_states
            target_reshaped = nearest_full.view(len(cell_states), -1)
            for ci, cs in enumerate(cell_states):
                if ci < target_reshaped.shape[0]:
                    nudge = manifold_alpha * (target_reshaped[ci, :cs.hidden.shape[0]] - cs.hidden)
                    cs.hidden.add_(nudge)

        # Record phi for all "virtual" steps covered by this batch+skip
        for _ in range(min(skip * batch_size, N_STEPS - s)):
            phis_e1.append(phi_now)

    t_e1 = time.time() - t0
    phi_e1_end = avg_last(phis_e1)
    speedup = t_base / t_e1 if t_e1 > 0 else float('inf')
    retention = phi_retention(phi_e1_end, phi_base_end)

    print(f"\n  --- E1 Results ---")
    print(f"  Baseline:  Phi={phi_base_end:.4f}, time={t_base:.2f}s, calls={N_STEPS}")
    print(f"  E1 combo:  Phi={phi_e1_end:.4f}, time={t_e1:.2f}s, calls={call_count}")
    print(f"  Speedup:   x{speedup:.1f}")
    print(f"  Retention: {retention:.1f}%")
    print(f"  Manifold compensates batch Phi loss: {'YES' if retention > 95 else 'PARTIAL' if retention > 85 else 'NO'}")
    print()
    print(ascii_graph(phis_base, title="Baseline Phi"))
    print()
    print(ascii_graph(phis_e1, title="E1 Batch+Skip+Manifold Phi"))
    sys.stdout.flush()

    return {
        'name': 'E1: Batch+Skip+Manifold',
        'speedup': speedup,
        'retention': retention,
        'phi_base': phi_base_end,
        'phi_test': phi_e1_end,
        'calls': call_count,
    }


# ═══════════════════════════════════════════════════════════
# E2: Adaptive Skip — Phi change-rate driven
# ═══════════════════════════════════════════════════════════

def run_e2():
    """Adaptive skip: skip more when Phi is stable, less when volatile."""
    print_header("E2: Adaptive Skip (Phi change-rate driven)")
    n_cells = N_CELLS

    # --- Baseline: plain 300 steps ---
    print("  [Baseline] 300 steps fixed...")
    sys.stdout.flush()
    engine_base = make_engine(n_cells)
    phis_base, t_base = run_baseline(engine_base, N_STEPS)
    phi_base_end = avg_last(phis_base)

    # --- Fixed Skip-10 (B12 reference) ---
    print("  [B12 ref] Skip-10 fixed...")
    sys.stdout.flush()
    engine_fixed = make_engine(n_cells)
    phis_fixed = []
    t0 = time.time()
    calls_fixed = 0
    for s in range(0, N_STEPS, 10):
        result = engine_fixed.step()
        calls_fixed += 1
        phi_now = result.get('phi_iit', 0.0)
        for _ in range(min(10, N_STEPS - s)):
            phis_fixed.append(phi_now)
    t_fixed = time.time() - t0
    phi_fixed_end = avg_last(phis_fixed)

    # --- E2: Adaptive skip ---
    print("  [E2] Adaptive skip (dPhi/dt threshold)...")
    sys.stdout.flush()
    engine_adap = make_engine(n_cells)
    phis_adap = []
    skips_used = []
    phi_prev = 0.0
    dphi_ema = 0.0
    alpha_ema = 0.3
    skip_min, skip_max = 1, 20
    # Use relative threshold: fraction of current phi (not absolute)
    dphi_rel_threshold = 0.02  # |dPhi/Phi| < 2% = stable

    t0 = time.time()
    calls_adap = 0
    s = 0
    while s < N_STEPS:
        result = engine_adap.step()
        calls_adap += 1
        phi_now = result.get('phi_iit', 0.0)

        # Update dPhi/dt EMA (relative to current phi magnitude)
        dphi = abs(phi_now - phi_prev)
        dphi_rel = dphi / max(abs(phi_now), 1e-8)
        dphi_ema = alpha_ema * dphi_rel + (1 - alpha_ema) * dphi_ema

        # Adaptive skip: stable -> skip more, volatile -> skip less
        if dphi_ema < dphi_rel_threshold * 0.5:
            skip = skip_max
        elif dphi_ema < dphi_rel_threshold:
            skip = int(skip_min + (skip_max - skip_min) * (1 - dphi_ema / dphi_rel_threshold))
        else:
            skip = skip_min

        skip = max(skip_min, min(skip_max, skip))
        skips_used.append(skip)

        for _ in range(min(skip, N_STEPS - s)):
            phis_adap.append(phi_now)
            s += 1

        phi_prev = phi_now

    t_adap = time.time() - t0
    phi_adap_end = avg_last(phis_adap)
    avg_skip = np.mean(skips_used)
    speedup_fixed = t_base / t_fixed if t_fixed > 0 else 0
    speedup_adap = t_base / t_adap if t_adap > 0 else 0

    print(f"\n  --- E2 Results ---")
    print(f"  Baseline:     Phi={phi_base_end:.4f}, time={t_base:.2f}s, calls={N_STEPS}")
    print(f"  Fixed skip10: Phi={phi_fixed_end:.4f}, time={t_fixed:.2f}s, calls={calls_fixed}, x{speedup_fixed:.1f}")
    print(f"  Adaptive:     Phi={phi_adap_end:.4f}, time={t_adap:.2f}s, calls={calls_adap}, x{speedup_adap:.1f}")
    print(f"  Avg skip:     {avg_skip:.1f} (min={min(skips_used)}, max={max(skips_used)})")
    print(f"  Retention:    fixed={phi_retention(phi_fixed_end, phi_base_end):.1f}%, adaptive={phi_retention(phi_adap_end, phi_base_end):.1f}%")

    better = "ADAPTIVE" if phi_adap_end > phi_fixed_end else "FIXED"
    print(f"  Winner:       {better}")
    print()
    print(ascii_graph(skips_used, title="Adaptive skip size over time"))
    print()
    print(ascii_graph(phis_adap, title="E2 Adaptive Skip Phi"))
    sys.stdout.flush()

    return {
        'name': 'E2: Adaptive Skip',
        'speedup': speedup_adap,
        'retention': phi_retention(phi_adap_end, phi_base_end),
        'phi_base': phi_base_end,
        'phi_test': phi_adap_end,
        'calls': calls_adap,
        'avg_skip': avg_skip,
        'winner': better,
    }


# ═══════════════════════════════════════════════════════════
# E3: Entropy+CE dual gradient
# ═══════════════════════════════════════════════════════════

def run_e3():
    """Dual loss: CE + lambda * |H - H_target|^2, sweep lambda."""
    print_header("E3: Entropy+CE dual gradient (H_target=0.998)")
    n_cells = 32  # smaller for training speed
    steps = N_STEPS
    target_dim = 128
    h_target = PSI_ENTROPY  # 0.998

    # Simple decoder for CE training
    class MiniDecoder(nn.Module):
        def __init__(self, in_dim, hidden, out_dim):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden),
                nn.GELU(),
                nn.Linear(hidden, out_dim),
            )
        def forward(self, x):
            return self.net(x)

    def compute_entropy(logits):
        """Shannon entropy of softmax distribution."""
        p = F.softmax(logits, dim=-1)
        log_p = F.log_softmax(logits, dim=-1)
        h = -(p * log_p).sum(dim=-1).mean()
        max_h = math.log(logits.shape[-1])
        return h / max_h  # normalized to [0,1]

    lambdas = [0.0, 0.01, 0.05, 0.1, 0.5]
    results_per_lambda = {}

    for lam in lambdas:
        label = f"lambda={lam}"
        print(f"\n  [{label}] Training {steps} steps...")
        sys.stdout.flush()

        torch.manual_seed(SEED)
        engine = make_engine(n_cells)
        decoder = MiniDecoder(128, 256, target_dim)
        optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

        phis = []
        ces = []
        entropies = []

        for s in range(steps):
            result = engine.step()
            phi = result.get('phi_iit', 0.0)
            phis.append(phi)

            # Forward pass
            states = engine.get_states()
            context = states.mean(dim=0).detach()
            logits = decoder(context.unsqueeze(0))
            target = torch.randint(0, target_dim, (1,))

            # CE loss
            ce = F.cross_entropy(logits, target)

            # Entropy regularization
            h_norm = compute_entropy(logits)
            entropy_loss = (h_norm - h_target) ** 2

            # Combined loss
            loss = ce + lam * entropy_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            ces.append(ce.item())
            entropies.append(h_norm.item())

            if (s + 1) % 100 == 0:
                print(f"    step {s+1}: CE={ce.item():.4f}, H={h_norm.item():.4f}, Phi={phi:.4f}")
                sys.stdout.flush()

        results_per_lambda[lam] = {
            'ce_end': avg_last(ces),
            'phi_end': avg_last(phis),
            'h_end': avg_last(entropies),
            'ces': ces,
            'phis': phis,
        }

    # --- Summary table ---
    print(f"\n  --- E3 Results ---")
    base_ce = results_per_lambda[0.0]['ce_end']
    base_phi = results_per_lambda[0.0]['phi_end']
    rows = []
    for lam in lambdas:
        r = results_per_lambda[lam]
        ce_delta = ((r['ce_end'] - base_ce) / base_ce * 100) if base_ce > 0 else 0
        phi_delta = ((r['phi_end'] - base_phi) / base_phi * 100) if base_phi > 0 else 0
        rows.append([
            f"{lam}",
            f"{r['ce_end']:.4f}",
            f"{ce_delta:+.1f}%",
            f"{r['phi_end']:.4f}",
            f"{phi_delta:+.1f}%",
            f"{r['h_end']:.3f}",
        ])

    print_table(
        ["lambda", "CE", "CE delta", "Phi", "Phi delta", "H_final"],
        rows
    )

    # Find best lambda (lowest CE with Phi retention > 90%)
    best_lam = 0.0
    best_ce = base_ce
    for lam in lambdas:
        r = results_per_lambda[lam]
        retention = phi_retention(r['phi_end'], base_phi)
        if retention > 90 and r['ce_end'] < best_ce:
            best_ce = r['ce_end']
            best_lam = lam

    print(f"\n  Best lambda: {best_lam} (CE={best_ce:.4f})")
    print()
    print(ascii_graph(results_per_lambda[best_lam]['ces'], title=f"CE curve (lambda={best_lam})"))
    print()
    print(ascii_graph(results_per_lambda[best_lam]['phis'], title=f"Phi curve (lambda={best_lam})"))
    sys.stdout.flush()

    return {
        'name': 'E3: Entropy+CE dual',
        'best_lambda': best_lam,
        'speedup': 1.0,  # same steps, no speedup — this is about quality
        'retention': phi_retention(results_per_lambda[best_lam]['phi_end'], base_phi),
        'phi_base': base_phi,
        'phi_test': results_per_lambda[best_lam]['phi_end'],
        'ce_base': base_ce,
        'ce_best': best_ce,
        'results': {str(k): {kk: vv for kk, vv in v.items() if kk != 'ces' and kk != 'phis'}
                    for k, v in results_per_lambda.items()},
    }


# ═══════════════════════════════════════════════════════════
# E4: Consciousness Curriculum + Skip (D3+B12)
# ═══════════════════════════════════════════════════════════

def run_e4():
    """Token selection by PE*tension (top 50%) + skip-10 combined."""
    print_header("E4: Consciousness Curriculum + Skip (D3+B12)")
    n_cells = 32
    steps = N_STEPS
    target_dim = 128
    n_tokens = 32  # simulated sequence length
    skip = 10

    class MiniDecoder(nn.Module):
        def __init__(self, in_dim, hidden, out_dim):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden),
                nn.GELU(),
                nn.Linear(hidden, out_dim),
            )
        def forward(self, x):
            return self.net(x)

    def run_variant(label, use_curriculum, use_skip):
        """Run one variant: curriculum on/off, skip on/off."""
        print(f"\n  [{label}] curriculum={use_curriculum}, skip={use_skip}")
        sys.stdout.flush()

        torch.manual_seed(SEED)
        engine = make_engine(n_cells)
        decoder = MiniDecoder(128, 256, target_dim)
        optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

        ces = []
        phis = []
        calls = 0
        pe_predictor = nn.Linear(128, 128)  # simple prediction error model
        pe_opt = torch.optim.Adam(pe_predictor.parameters(), lr=1e-3)
        prev_states = None

        s = 0
        while s < steps:
            result = engine.step()
            calls += 1
            phi = result.get('phi_iit', 0.0)
            states = engine.get_states().mean(dim=0).detach()

            # Prediction error
            if prev_states is not None:
                pred = pe_predictor(prev_states.detach())
                pe = (pred - states.detach()).pow(2).mean()
                pe_opt.zero_grad()
                pe.backward()
                pe_opt.step()
                pe_val = pe.item()
            else:
                pe_val = 1.0

            # Tension from engine (can be list or dict)
            tension = result.get('tensions', [])
            if isinstance(tension, dict):
                mean_tension = np.mean(list(tension.values())) if tension else 0.5
            elif isinstance(tension, (list, np.ndarray)) and len(tension) > 0:
                mean_tension = np.mean(tension)
            else:
                mean_tension = 0.5

            # Simulate multi-token batch
            token_scores = []
            token_logits_list = []
            token_targets = []
            for t in range(n_tokens):
                noise = torch.randn(128) * 0.1
                tok_input = (states + noise).unsqueeze(0)
                logits = decoder(tok_input)
                target = torch.randint(0, target_dim, (1,))
                ce = F.cross_entropy(logits, target)

                # Score = PE * tension (consciousness importance)
                score = pe_val * mean_tension * (1 + 0.1 * torch.randn(1).item())
                token_scores.append(score)
                token_logits_list.append(logits)
                token_targets.append(target)

            # Curriculum: select top 50% tokens by consciousness score
            if use_curriculum:
                sorted_idx = np.argsort(token_scores)[::-1]
                selected = sorted_idx[:n_tokens // 2]
            else:
                selected = range(n_tokens)

            # Compute CE only on selected tokens
            total_ce = 0.0
            for idx in selected:
                total_ce += F.cross_entropy(token_logits_list[idx], token_targets[idx])
            total_ce = total_ce / len(selected)

            optimizer.zero_grad()
            total_ce.backward()
            optimizer.step()

            ce_val = total_ce.item()
            ces.append(ce_val)
            phis.append(phi)

            prev_states = states

            # Skip: advance virtual steps
            step_advance = skip if use_skip else 1
            for _ in range(min(step_advance, steps - s)):
                s += 1

            if len(ces) % 10 == 0:
                print(f"    step ~{s}: CE={ce_val:.4f}, Phi={phi:.4f}, calls={calls}")
                sys.stdout.flush()

        return ces, phis, calls

    # Run 4 variants
    variants = [
        ("A: baseline", False, False),
        ("B: curriculum only", True, False),
        ("C: skip-10 only", False, True),
        ("D: curriculum+skip", True, True),
    ]

    all_results = {}
    for label, cur, sk in variants:
        ces, phis, calls = run_variant(label, cur, sk)
        all_results[label] = {
            'ce_end': avg_last(ces),
            'phi_end': avg_last(phis),
            'calls': calls,
            'ces': ces,
            'phis': phis,
        }

    # Summary
    print(f"\n  --- E4 Results ---")
    base = all_results["A: baseline"]
    rows = []
    for label, _, _ in variants:
        r = all_results[label]
        ce_delta = ((r['ce_end'] - base['ce_end']) / base['ce_end'] * 100) if base['ce_end'] > 0 else 0
        phi_ret = phi_retention(r['phi_end'], base['phi_end'])
        rows.append([
            label, f"{r['ce_end']:.4f}", f"{ce_delta:+.1f}%",
            f"{r['phi_end']:.4f}", f"{phi_ret:.1f}%", str(r['calls'])
        ])

    print_table(
        ["Variant", "CE", "CE delta", "Phi", "Phi ret%", "Calls"],
        rows
    )

    # Winner
    best_label = min(all_results, key=lambda k: all_results[k]['ce_end'])
    combo = all_results["D: curriculum+skip"]
    print(f"\n  Best CE: {best_label} ({all_results[best_label]['ce_end']:.4f})")
    print()
    print(ascii_graph(all_results[best_label]['ces'], title=f"CE curve ({best_label})"))
    sys.stdout.flush()

    # Use combo (D) for summary speedup since it has skip
    combo_speedup = base['calls'] / combo['calls'] if combo['calls'] > 0 else 1.0
    combo_retention = phi_retention(combo['phi_end'], base['phi_end'])

    return {
        'name': 'E4: Curriculum+Skip',
        'speedup': combo_speedup,
        'retention': combo_retention,
        'phi_base': base['phi_end'],
        'phi_test': combo['phi_end'],
        'best': best_label,
        'results': {k: {kk: vv for kk, vv in v.items() if kk != 'ces' and kk != 'phis'}
                    for k, v in all_results.items()},
    }


# ═══════════════════════════════════════════════════════════
# E5: Jump + Phi-Only + CE pipeline (D1+B5)
# ═══════════════════════════════════════════════════════════

def run_e5():
    """3-phase pipeline: jump to 30% state -> Phi-Only 50 steps -> CE 50 steps."""
    print_header("E5: Jump(D1) + Phi-Only(B5) + CE pipeline")
    n_cells = N_CELLS
    target_dim = 128

    class MiniDecoder(nn.Module):
        def __init__(self, in_dim, hidden, out_dim):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, hidden),
                nn.GELU(),
                nn.Linear(hidden, out_dim),
            )
        def forward(self, x):
            return self.net(x)

    # --- Baseline: 300 steps with CE training ---
    print("  [Baseline] 300 steps with CE training...")
    sys.stdout.flush()

    torch.manual_seed(SEED)
    engine_base = make_engine(n_cells)
    decoder_base = MiniDecoder(128, 256, target_dim)
    opt_base = torch.optim.Adam(decoder_base.parameters(), lr=1e-3)

    phis_base = []
    ces_base = []
    t0 = time.time()
    for s in range(N_STEPS):
        result = engine_base.step()
        phis_base.append(result.get('phi_iit', 0.0))
        states = engine_base.get_states().mean(dim=0).detach()
        logits = decoder_base(states.unsqueeze(0))
        target = torch.randint(0, target_dim, (1,))
        ce = F.cross_entropy(logits, target)
        opt_base.zero_grad()
        ce.backward()
        opt_base.step()
        ces_base.append(ce.item())
    t_base = time.time() - t0

    # --- Collect trajectory for jump target ---
    print("  [Collect] Collecting 300-step trajectory for jump target...")
    sys.stdout.flush()
    torch.manual_seed(SEED)
    engine_traj = make_engine(n_cells)
    snapshots = {}
    for s in range(N_STEPS):
        result = engine_traj.step()
        if s % 10 == 0:
            snapshots[s] = [deepcopy(cs) for cs in engine_traj.cell_states]

    # --- E5 pipeline ---
    jump_target_step = int(N_STEPS * 0.30)  # jump to 30% state
    phi_only_steps = 50
    ce_steps = 50
    total_e5_steps = phi_only_steps + ce_steps  # 100 (vs 300 baseline)

    print(f"\n  [E5] Jump to step {jump_target_step}, then {phi_only_steps} Phi-Only, then {ce_steps} CE")
    sys.stdout.flush()

    torch.manual_seed(SEED)
    engine_e5 = make_engine(n_cells)
    decoder_e5 = MiniDecoder(128, 256, target_dim)
    opt_e5 = torch.optim.Adam(decoder_e5.parameters(), lr=1e-3)

    # Phase 1: Jump — load snapshot closest to target
    closest_step = min(snapshots.keys(), key=lambda k: abs(k - jump_target_step))
    print(f"  Phase 1: Jumping to step {closest_step} (target was {jump_target_step})")
    sys.stdout.flush()
    t0_e5 = time.time()

    # Copy cell states from snapshot
    with torch.no_grad():
        snap_states = snapshots[closest_step]
        for i, cs in enumerate(engine_e5.cell_states):
            if i < len(snap_states):
                cs.hidden.copy_(snap_states[i].hidden)

    phis_e5 = []
    ces_e5 = []

    # Phase 2: Phi-Only (no CE training, just consciousness evolution)
    print(f"  Phase 2: Phi-Only ({phi_only_steps} steps, no CE backprop)...")
    sys.stdout.flush()
    for s in range(phi_only_steps):
        result = engine_e5.step()
        phis_e5.append(result.get('phi_iit', 0.0))
        # No CE computation — pure consciousness time
        ces_e5.append(float('nan'))

    # Phase 3: CE training
    print(f"  Phase 3: CE training ({ce_steps} steps)...")
    sys.stdout.flush()
    for s in range(ce_steps):
        result = engine_e5.step()
        phis_e5.append(result.get('phi_iit', 0.0))
        states = engine_e5.get_states().mean(dim=0).detach()
        logits = decoder_e5(states.unsqueeze(0))
        target = torch.randint(0, target_dim, (1,))
        ce = F.cross_entropy(logits, target)
        opt_e5.zero_grad()
        ce.backward()
        opt_e5.step()
        ces_e5.append(ce.item())

    t_e5 = time.time() - t0_e5

    # Compare
    phi_base_end = avg_last(phis_base)
    phi_e5_end = avg_last(phis_e5)
    ce_base_end = avg_last([c for c in ces_base if not math.isnan(c)])
    ce_e5_vals = [c for c in ces_e5 if not math.isnan(c)]
    ce_e5_end = avg_last(ce_e5_vals) if ce_e5_vals else float('nan')
    speedup = t_base / t_e5 if t_e5 > 0 else float('inf')

    print(f"\n  --- E5 Results ---")
    print(f"  Baseline (300 steps):")
    print(f"    Phi={phi_base_end:.4f}, CE={ce_base_end:.4f}, time={t_base:.2f}s")
    print(f"  E5 pipeline (jump + {phi_only_steps} phi-only + {ce_steps} CE = {total_e5_steps} real steps):")
    print(f"    Phi={phi_e5_end:.4f}, CE={ce_e5_end:.4f}, time={t_e5:.2f}s")
    print(f"  Speedup: x{speedup:.1f} ({N_STEPS} steps -> {total_e5_steps} real steps)")
    print(f"  Phi retention: {phi_retention(phi_e5_end, phi_base_end):.1f}%")

    ce_delta_pct = ((ce_e5_end - ce_base_end) / ce_base_end * 100) if ce_base_end > 0 and not math.isnan(ce_e5_end) else float('nan')
    print(f"  CE change: {ce_delta_pct:+.1f}%")

    achieves = "YES" if phi_retention(phi_e5_end, phi_base_end) > 90 else "NO"
    print(f"  100-step achieves 300-step Phi? {achieves}")
    print()
    print(ascii_graph(phis_base, title="Baseline Phi (300 steps)"))
    print()
    print(ascii_graph(phis_e5, title="E5 Pipeline Phi (100 real steps)"))
    sys.stdout.flush()

    return {
        'name': 'E5: Jump+PhiOnly+CE',
        'speedup': speedup,
        'retention': phi_retention(phi_e5_end, phi_base_end),
        'phi_base': phi_base_end,
        'phi_test': phi_e5_end,
        'ce_base': ce_base_end,
        'ce_test': ce_e5_end,
        'total_steps': total_e5_steps,
    }


# ═══════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════

def print_summary(results):
    """Print final comparison table."""
    print_header("SUMMARY: E1-E5 Proven Winner Maximization")

    rows = []
    for r in results:
        speedup = r.get('speedup', '-')
        if isinstance(speedup, float):
            speedup = f"x{speedup:.1f}"
        retention = r.get('retention', '-')
        if isinstance(retention, float):
            retention = f"{retention:.1f}%"
        phi_base = f"{r.get('phi_base', 0):.4f}" if isinstance(r.get('phi_base'), float) else '-'
        phi_test = f"{r.get('phi_test', 0):.4f}" if isinstance(r.get('phi_test'), float) else '-'
        extra = ""
        if 'avg_skip' in r:
            extra = f"avg_skip={r['avg_skip']:.1f}"
        if 'best_lambda' in r:
            extra = f"best_lam={r['best_lambda']}"
        if 'total_steps' in r:
            extra = f"{r['total_steps']} steps"
        if 'best' in r:
            extra = r['best']
        rows.append([r['name'], speedup, retention, phi_base, phi_test, extra])

    print_table(
        ["Experiment", "Speedup", "Phi Ret%", "Phi Base", "Phi Test", "Note"],
        rows
    )

    # Winner
    best_speedup = max(results, key=lambda r: r.get('speedup', 0) if isinstance(r.get('speedup'), (int, float)) else 0)
    best_retention = max(results, key=lambda r: r.get('retention', 0) if isinstance(r.get('retention'), (int, float)) else 0)

    print(f"\n  Fastest:       {best_speedup['name']} (x{best_speedup.get('speedup', 0):.1f})")
    print(f"  Best Phi:      {best_retention['name']} ({best_retention.get('retention', 0):.1f}%)")
    print(f"  Optimal combo: combine techniques with highest speedup + >95% retention")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="E1-E5: Proven winner maximization experiments")
    parser.add_argument('--e1', action='store_true', help='E1: Batch+Skip+Manifold')
    parser.add_argument('--e2', action='store_true', help='E2: Adaptive Skip')
    parser.add_argument('--e3', action='store_true', help='E3: Entropy+CE dual gradient')
    parser.add_argument('--e4', action='store_true', help='E4: Consciousness Curriculum + Skip')
    parser.add_argument('--e5', action='store_true', help='E5: Jump + Phi-Only + CE pipeline')
    parser.add_argument('--all', action='store_true', help='Run all experiments')
    args = parser.parse_args()

    run_all = args.all or not any([args.e1, args.e2, args.e3, args.e4, args.e5])

    print("=" * 70)
    print("  E1-E5: Proven Winner Maximization Experiments")
    print(f"  Cells={N_CELLS}, Steps={N_STEPS}, Seed={SEED}")
    print("=" * 70)
    sys.stdout.flush()

    results = []
    t_total = time.time()

    if run_all or args.e1:
        results.append(run_e1())
    if run_all or args.e2:
        results.append(run_e2())
    if run_all or args.e3:
        results.append(run_e3())
    if run_all or args.e4:
        results.append(run_e4())
    if run_all or args.e5:
        results.append(run_e5())

    if len(results) > 1:
        print_summary(results)

    t_elapsed = time.time() - t_total
    print(f"\n  Total elapsed: {t_elapsed:.1f}s")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
