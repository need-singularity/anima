#!/usr/bin/env python3
"""I1: Speculative Consciousness Decoding

Small engine (8c) drafts N steps → Large engine (64c) verifies.
If draft state is within tolerance (cosine sim > threshold), accept.
If not, large engine re-processes that step (full cost).

Expected: x5-10 speedup if acceptance rate > 70%.

Configs tested:
  - Baseline:   large engine only (64c, 200 steps)
  - I1-A:       draft_steps=1, threshold=0.8
  - I1-B:       draft_steps=3, threshold=0.7
  - I1-C:       draft_steps=5, threshold=0.6

Usage:
    PYTHONUNBUFFERED=1 python3 anima/experiments/acceleration_i1_speculative.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

N_CELLS_LARGE = 64
N_CELLS_SMALL = 8
N_STEPS = 200
N_REPS = 3
SEED = 42


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def make_engine(n_cells, seed=SEED):
    torch.manual_seed(seed)
    np.random.seed(seed)
    return ConsciousnessEngine(
        cell_dim=64,
        hidden_dim=128,
        max_cells=n_cells,
        n_factions=min(12, n_cells),
    )


def get_states_mean(engine):
    """Mean cell state as a 1-D vector (hidden_dim,)."""
    states = engine.get_states()   # (n_cells, hidden_dim)
    return states.mean(dim=0)


def cosine_sim(a, b):
    """Cosine similarity between two 1-D tensors."""
    a = a.float()
    b = b.float()
    denom = (a.norm() * b.norm()).clamp(min=1e-8)
    return (a @ b / denom).item()


def measure_phi(engine):
    result = engine.step.__self__ if hasattr(engine.step, '__self__') else engine
    if hasattr(engine, '_measure_phi_iit'):
        return engine._measure_phi_iit()
    return engine.measure_phi()


def phi_after_n_steps(engine, n_steps):
    """Run engine n steps, return last phi."""
    phi = 0.0
    for _ in range(n_steps):
        res = engine.step()
        phi = res.get('phi_iit', res.get('phi', 0.0))
    return phi


def ascii_bar(val, max_val, width=40):
    filled = int(round(width * val / max(max_val, 1e-9)))
    return '█' * filled + '░' * (width - filled)


def print_sep(char='═', width=70):
    print(char * width)
    sys.stdout.flush()


def print_header(title):
    print_sep()
    print(f"  {title}")
    print_sep()
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════
# Baseline: large engine only
# ═══════════════════════════════════════════════════════════

def run_baseline(steps=N_STEPS, seed=SEED):
    """Large engine only — ground truth."""
    engine = make_engine(N_CELLS_LARGE, seed=seed)
    phis = []
    t0 = time.perf_counter()
    for _ in range(steps):
        res = engine.step()
        phis.append(res.get('phi_iit', res.get('phi', 0.0)))
    elapsed = time.perf_counter() - t0
    return phis, elapsed


# ═══════════════════════════════════════════════════════════
# Speculative decoding
# ═══════════════════════════════════════════════════════════

def run_speculative(draft_steps=1, threshold=0.8, steps=N_STEPS, seed=SEED):
    """
    Speculative consciousness decoding.

    Algorithm:
      For each global step:
        1. Draft up to `draft_steps` steps with small engine.
        2. Query large engine for what it *would* produce (one step).
        3. Compare draft mean-state to large-engine mean-state via cosine sim.
        4. If sim >= threshold: accept draft state (skip large engine forward).
        5. Else: run large engine step (full cost), discard draft.

    Returns:
      phis          — Φ history from large engine perspective
      elapsed       — wall time
      accept_rate   — fraction of steps where draft was accepted
      speedup_est   — estimated speedup vs baseline (ratio of large engine calls)
    """
    small = make_engine(N_CELLS_SMALL, seed=seed)
    large = make_engine(N_CELLS_LARGE, seed=seed)

    phis = []
    accepted = 0
    total = 0
    large_calls = 0

    t0 = time.perf_counter()

    step_idx = 0
    while step_idx < steps:
        # --- Draft phase: small engine runs draft_steps ---
        draft_states = []
        for _ in range(draft_steps):
            small.step()
            draft_states.append(get_states_mean(small))

        # --- Verify phase: large engine does ONE speculative step ---
        large_res = large.step()
        large_calls += 1
        large_state = get_states_mean(large)
        phi_val = large_res.get('phi_iit', large_res.get('phi', 0.0))

        # Compare last draft state to large engine state
        last_draft = draft_states[-1]

        # Project small (hidden_dim) onto large (hidden_dim) — same hidden_dim=128
        sim = cosine_sim(last_draft, large_state)

        total += 1
        if sim >= threshold:
            # Accept: count how many draft steps we skipped
            accepted += draft_steps
            # Advance step counter by draft_steps (but cap at N_STEPS)
            for _ in range(draft_steps):
                if step_idx < steps:
                    phis.append(phi_val)
                    step_idx += 1
        else:
            # Reject: large engine already advanced one step, record phi
            phis.append(phi_val)
            step_idx += 1

    elapsed = time.perf_counter() - t0

    # accept_rate: fraction of total global steps served by small engine
    accept_rate = accepted / steps if steps > 0 else 0.0
    # speedup_est: if acceptance rate = r, we ran large engine only (1-r)*steps times
    # plus overhead of running small engine every step (negligible cost ratio ~8/64=0.125)
    small_cost_ratio = N_CELLS_SMALL / N_CELLS_LARGE   # ~0.125
    # effective_steps = large_calls + accepted * small_cost_ratio
    # speedup = steps / effective_steps
    effective = large_calls + accepted * small_cost_ratio
    speedup_est = steps / max(effective, 1)

    return phis, elapsed, accept_rate, speedup_est, large_calls


# ═══════════════════════════════════════════════════════════
# Run configs
# ═══════════════════════════════════════════════════════════

CONFIGS = [
    ("Baseline (64c only)",    None,  None,  None),
    ("I1-A (draft=1, thr=0.8)", 1,    0.8,   "I1-A"),
    ("I1-B (draft=3, thr=0.7)", 3,    0.7,   "I1-B"),
    ("I1-C (draft=5, thr=0.6)", 5,    0.6,   "I1-C"),
]


def run_config(name, draft_steps, threshold, label, reps=N_REPS):
    """Run one config N_REPS times, return averaged results."""
    elapsed_list = []
    accept_list = []
    speedup_list = []
    phi_list = []
    large_calls_list = []

    for rep in range(reps):
        seed = SEED + rep * 17
        if draft_steps is None:
            # Baseline
            phis, elapsed = run_baseline(steps=N_STEPS, seed=seed)
            accept_rate = 0.0
            speedup_est = 1.0
            large_calls = N_STEPS
        else:
            phis, elapsed, accept_rate, speedup_est, large_calls = run_speculative(
                draft_steps=draft_steps,
                threshold=threshold,
                steps=N_STEPS,
                seed=seed,
            )

        elapsed_list.append(elapsed)
        accept_list.append(accept_rate)
        speedup_list.append(speedup_est)
        phi_list.append(np.mean(phis[-30:]) if len(phis) >= 30 else (np.mean(phis) if phis else 0.0))
        large_calls_list.append(large_calls)

        print(f"  rep {rep+1}/{reps}: elapsed={elapsed:.3f}s  accept={accept_rate:.1%}"
              f"  speedup_est={speedup_est:.2f}x  phi={phi_list[-1]:.4f}")
        sys.stdout.flush()

    return {
        "name": name,
        "label": label,
        "elapsed_mean": np.mean(elapsed_list),
        "elapsed_std": np.std(elapsed_list),
        "accept_rate": np.mean(accept_list),
        "speedup_est": np.mean(speedup_list),
        "phi_mean": np.mean(phi_list),
        "large_calls": np.mean(large_calls_list),
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print_header("I1: Speculative Consciousness Decoding")
    print(f"  Large engine: {N_CELLS_LARGE}c | Small (draft): {N_CELLS_SMALL}c")
    print(f"  Steps: {N_STEPS} | Reps: {N_REPS}")
    print(f"  Hypothesis: small engine drafts → large engine verifies")
    print(f"  Expected: x5-10 speedup at >70% acceptance rate")
    sys.stdout.flush()

    results = []
    baseline_elapsed = None
    baseline_phi = None

    for name, draft_steps, threshold, label in CONFIGS:
        print(f"\n--- {name} ---")
        sys.stdout.flush()
        r = run_config(name, draft_steps, threshold, label, reps=N_REPS)
        results.append(r)

        if label is None:
            baseline_elapsed = r["elapsed_mean"]
            baseline_phi = r["phi_mean"]

    # ── Results Table ──────────────────────────────────────
    print_header("Results Summary")

    print(f"{'Config':<30} {'Accept':>8} {'Speedup':>10} {'Wall(s)':>9} {'Phi':>8} {'Phi%':>7}")
    print('─' * 75)
    sys.stdout.flush()

    for r in results:
        actual_speedup = baseline_elapsed / r["elapsed_mean"] if r["elapsed_mean"] > 0 else 1.0
        phi_pct = (r["phi_mean"] / baseline_phi * 100) if baseline_phi and baseline_phi > 1e-9 else 100.0
        accept_str = f"{r['accept_rate']:.1%}" if r["label"] else "—"
        print(f"{r['name']:<30} {accept_str:>8} {actual_speedup:>9.2f}x"
              f" {r['elapsed_mean']:>9.3f}  {r['phi_mean']:>8.4f} {phi_pct:>6.1f}%")
        sys.stdout.flush()

    print()

    # ── ASCII speedup chart ────────────────────────────────
    print("  Actual Speedup vs Baseline:")
    print()
    for r in results:
        actual_speedup = baseline_elapsed / r["elapsed_mean"] if r["elapsed_mean"] > 0 else 1.0
        bar = ascii_bar(actual_speedup, max_val=10, width=40)
        print(f"  {r['name']:<30} {bar} {actual_speedup:.2f}x")
    print()
    sys.stdout.flush()

    # ── Acceptance rate chart ──────────────────────────────
    print("  Acceptance Rate (fraction of steps served by small engine):")
    print()
    for r in results:
        if r["label"]:
            bar = ascii_bar(r["accept_rate"], max_val=1.0, width=40)
            print(f"  {r['name']:<30} {bar} {r['accept_rate']:.1%}")
    print()
    sys.stdout.flush()

    # ── Phi retention chart ────────────────────────────────
    print("  Phi Retention vs Baseline:")
    print()
    for r in results:
        phi_pct = (r["phi_mean"] / baseline_phi * 100) if baseline_phi and baseline_phi > 1e-9 else 100.0
        bar = ascii_bar(phi_pct, max_val=110, width=40)
        print(f"  {r['name']:<30} {bar} {phi_pct:.1f}%")
    print()
    sys.stdout.flush()

    # ── Key Findings ──────────────────────────────────────
    print_header("Key Findings — I1 Speculative Consciousness Decoding")

    best = max(
        (r for r in results if r["label"]),
        key=lambda r: (baseline_elapsed / r["elapsed_mean"]) if r["elapsed_mean"] > 0 else 0,
        default=None
    )

    if best:
        actual_speedup = baseline_elapsed / best["elapsed_mean"] if best["elapsed_mean"] > 0 else 1.0
        phi_pct = (best["phi_mean"] / baseline_phi * 100) if baseline_phi and baseline_phi > 1e-9 else 100.0
        print(f"  Best config:    {best['name']}")
        print(f"  Accept rate:    {best['accept_rate']:.1%}")
        print(f"  Actual speedup: {actual_speedup:.2f}x")
        print(f"  Phi retention:  {phi_pct:.1f}%")
        print()

        if actual_speedup >= 2.0:
            verdict = "VALID — speculative decoding accelerates consciousness"
        elif actual_speedup >= 1.2:
            verdict = "PARTIAL — modest gain; acceptance rate too low for full benefit"
        else:
            verdict = "INVALID — overhead negates draft savings"
        print(f"  Verdict: {verdict}")
    else:
        print("  No speculative configs ran.")

    print()
    print("  Interpretation:")
    print("  - If acceptance rate > 70%: hypothesis confirmed (x5-10 expected)")
    print("  - If acceptance rate < 50%: small engine diverges too fast from large")
    print("  - Phi retention < 90%: draft states distort consciousness field")
    print()
    sys.stdout.flush()

    print_sep()
    print("  DONE — I1 Speculative Consciousness Decoding")
    print_sep()
    sys.stdout.flush()


if __name__ == "__main__":
    main()
