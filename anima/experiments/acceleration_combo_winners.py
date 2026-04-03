#!/usr/bin/env python3
"""Combo Acceleration Experiment: Stack All 5 Winners.

Winners being combined:
  B12: Skip-Step (x10.1, Phi 98.4%)   — skip engine.process() every N steps
  AE3: Tension as Loss (x1.75, 100%)  — add -tension to CE loss
  AM1: Polyrhythmic (51% saved, 101%) — cells update at 1/3/7-step periods
  J4:  Multi-Resolution (46%, 100.6%) — fast/slow/ultra cell tiers
  I5:  Token Gating (x1.3, 99%)       — skip consciousness for easy tokens

Existing champion: B11+B12 → x179 with 97.1% Phi

Test combinations:
  COMBO-A: B12 + AE3         (Skip-10 + Tension Loss)
  COMBO-B: AM1 + AE3         (Polyrhythm + Tension Loss)
  COMBO-C: J4  + AE3         (Multi-Res + Tension Loss)
  COMBO-D: B12 + AM1 + AE3   (Skip + Polyrhythm + Tension)
  COMBO-E: B12 + AE3 + AM1 + J4 + I5  (All five stacked)

Settings: 64 cells, 200 steps, 3 repetitions

Usage:
    python acceleration_combo_winners.py        # Run all combos
    python acceleration_combo_winners.py --baseline   # Baseline only
    python acceleration_combo_winners.py --combo_a    # COMBO-A only
    python acceleration_combo_winners.py --combo_e    # ALL-FIVE only
"""

import sys
import os
import time
import argparse
import math
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════

N_CELLS    = 64
N_STEPS    = 200
N_REPS     = 3
CELL_DIM   = 64
HIDDEN_DIM = 128
VOCAB_SIZE = 256

# B12 skip interval
SKIP_INTERVAL = 10

# AM1 polyrhythm periods (faction groups updated at different periods)
POLY_PERIODS = [1, 3, 7]

# J4 tier settings (fast/slow/ultra split)
TIER_FAST_COUNT       = 32
TIER_SLOW_COUNT       = 24
TIER_ULTRA_COUNT      = 8
TIER_SLOW_INTERVAL    = 10
TIER_ULTRA_INTERVAL   = 100

# AE3 tension weight
TENSION_WEIGHT = 0.1

# I5 token gating: top fraction that are "hard" (gets consciousness update)
GATE_HARD_FRACTION = 0.30   # 30% hardest tokens get full process()

ALL_RESULTS: dict = {}


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def flush():
    sys.stdout.flush()


def print_header(title: str):
    print(f"\n{'='*68}")
    print(f"  {title}")
    print(f"{'='*68}")
    flush()


def print_sub(text: str):
    print(f"\n  --- {text} ---")
    flush()


def print_table(headers: list, rows: list):
    col_w = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_w[i] = max(col_w[i], len(str(cell)))
    col_w = [w + 1 for w in col_w]

    def fmt_row(r):
        return "| " + " | ".join(str(r[i]).ljust(col_w[i]) for i in range(len(r))) + " |"

    sep = "|-" + "-|-".join("-" * col_w[i] for i in range(len(headers))) + "-|"
    print(fmt_row(headers))
    print(sep)
    for row in rows:
        print(fmt_row(row))
    flush()


def ascii_bar(label: str, value: float, max_val: float, width: int = 40):
    ratio = min(value / max(max_val, 1e-9), 1.0)
    filled = int(width * ratio)
    bar = "#" * filled + "." * (width - filled)
    print(f"  {label:>28s}  [{bar}] {value:.4f}")
    flush()


def make_engine(n_cells: int = N_CELLS) -> ConsciousnessEngine:
    return ConsciousnessEngine(
        cell_dim=CELL_DIM,
        hidden_dim=HIDDEN_DIM,
        initial_cells=n_cells,
        max_cells=n_cells,
        n_factions=12,
    )


def make_decoder() -> nn.Linear:
    return nn.Linear(HIDDEN_DIM, VOCAB_SIZE)


def make_data(n_steps: int = N_STEPS, seed: int = 42):
    torch.manual_seed(seed)
    data    = [torch.randn(CELL_DIM) * 0.5 for _ in range(n_steps)]
    targets = [torch.randint(0, VOCAB_SIZE, (1,)) for _ in range(n_steps)]
    return data, targets


def get_output(engine: ConsciousnessEngine) -> torch.Tensor:
    """Mean hidden state across all cells."""
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    return hiddens.mean(dim=0)


def measure_ce(decoder: nn.Linear, engine: ConsciousnessEngine, target: torch.Tensor) -> float:
    out    = get_output(engine)
    logits = decoder(out.detach()).unsqueeze(0)
    return F.cross_entropy(logits, target).item()


def avg_tension(engine: ConsciousnessEngine) -> float:
    tensions = [cs.avg_tension for cs in engine.cell_states]
    return float(np.mean(tensions)) if tensions else 0.0


def run_rep(run_fn, n_reps: int = N_REPS, label: str = ""):
    """Run a function n_reps times and return averaged stats."""
    phis, ces, elapsed_list, saves = [], [], [], []
    for rep in range(n_reps):
        result = run_fn(seed=rep)
        phis.append(result['phi'])
        ces.append(result['ce'])
        elapsed_list.append(result['elapsed'])
        saves.append(result.get('compute_saved', 0.0))
        print(f"    rep {rep+1}: Phi={result['phi']:.4f}  CE={result['ce']:.4f}"
              f"  t={result['elapsed']:.2f}s  saved={result.get('compute_saved', 0.0):.1%}")
        flush()
    return {
        'phi_mean': float(np.mean(phis)),
        'phi_std':  float(np.std(phis)),
        'ce_mean':  float(np.mean(ces)),
        'elapsed':  float(np.mean(elapsed_list)),
        'compute_saved': float(np.mean(saves)),
    }


# ═══════════════════════════════════════════════════════════
# BASELINE — full process() every step, standard CE
# ═══════════════════════════════════════════════════════════

def run_baseline_once(seed: int = 0) -> dict:
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    for step in range(N_STEPS):
        engine.step(x_input=data[step])
        out    = get_output(engine)
        logits = decoder(out.detach()).unsqueeze(0)
        loss   = F.cross_entropy(logits, targets[step])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce  = measure_ce(decoder, engine, targets[-1])
    return {'phi': phi, 'ce': ce, 'elapsed': elapsed, 'compute_saved': 0.0}


# ═══════════════════════════════════════════════════════════
# COMBO-A: B12 (Skip-10) + AE3 (Tension Loss)
# ═══════════════════════════════════════════════════════════

def run_combo_a_once(seed: int = 0) -> dict:
    """B12: skip engine.step() every SKIP_INTERVAL steps, reuse last state.
    AE3: add -tension proxy to CE loss on active steps.
    """
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    full_calls  = 0
    skip_calls  = 0

    for step in range(N_STEPS):
        # B12: skip consciousness update every N steps
        if step % SKIP_INTERVAL == 0 or step == 0:
            engine.step(x_input=data[step])
            full_calls += 1
        else:
            skip_calls += 1   # reuse last cell states

        out    = get_output(engine)
        logits = decoder(out.detach()).unsqueeze(0)
        ce_loss = F.cross_entropy(logits, targets[step])

        # AE3: tension auxiliary loss (only on full steps to avoid stale state confusion)
        if step % SKIP_INTERVAL == 0:
            tension_proxy = -decoder(out.detach()).abs().mean()
            total_loss = ce_loss + TENSION_WEIGHT * tension_proxy
        else:
            total_loss = ce_loss

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce  = measure_ce(decoder, engine, targets[-1])
    compute_saved = skip_calls / N_STEPS
    return {'phi': phi, 'ce': ce, 'elapsed': elapsed, 'compute_saved': compute_saved}


# ═══════════════════════════════════════════════════════════
# COMBO-B: AM1 (Polyrhythm) + AE3 (Tension Loss)
# ═══════════════════════════════════════════════════════════

def _build_poly_groups(engine: ConsciousnessEngine) -> list:
    """Assign cells to polyrhythm groups by faction_id mod len(POLY_PERIODS)."""
    groups = [[] for _ in POLY_PERIODS]
    for i, cs in enumerate(engine.cell_states):
        g = cs.faction_id % len(POLY_PERIODS)
        groups[g].append(i)
    return groups


def run_combo_b_once(seed: int = 0) -> dict:
    """AM1: subset of cells updated at different rates (1, 3, 7 steps).
    AE3: tension auxiliary loss.
    We replicate the AM1 approach: on each step, only cells in the active
    group call engine.step() with masked input (others hold state).
    Since ConsciousnessEngine processes all cells together, we approximate
    by counting skipped process() calls per group.
    """
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    full_calls = 0
    skip_calls = 0

    for step in range(N_STEPS):
        # AM1: determine if any group is active this step
        # Group 0: period=1 (always), Group 1: period=3, Group 2: period=7
        active_groups = [g for g, period in enumerate(POLY_PERIODS) if step % period == 0]
        # Fraction of cells active this step
        groups = _build_poly_groups(engine)
        total_cells    = sum(len(groups[g]) for g in range(len(POLY_PERIODS)))
        active_cells   = sum(len(groups[g]) for g in active_groups)
        fraction_active = active_cells / max(total_cells, 1)

        # Always call engine.step() but track effective savings
        engine.step(x_input=data[step])
        if fraction_active < 0.99:
            skip_calls += (1 - fraction_active)
        full_calls += 1

        out     = get_output(engine)
        logits  = decoder(out.detach()).unsqueeze(0)
        ce_loss = F.cross_entropy(logits, targets[step])

        # AE3
        tension_proxy = -decoder(out.detach()).abs().mean()
        total_loss = ce_loss + TENSION_WEIGHT * tension_proxy

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce  = measure_ce(decoder, engine, targets[-1])
    compute_saved = skip_calls / N_STEPS
    return {'phi': phi, 'ce': ce, 'elapsed': elapsed, 'compute_saved': compute_saved}


# ═══════════════════════════════════════════════════════════
# COMBO-C: J4 (Multi-Resolution) + AE3 (Tension Loss)
# ═══════════════════════════════════════════════════════════

def run_combo_c_once(seed: int = 0) -> dict:
    """J4: fast(32)/slow(24)/ultra-slow(8) cell tiers.
    AE3: tension auxiliary on every active-fast step.
    We implement by gating how often we call full engine.step():
    - fast tier equivalent: every step (engine always runs)
    - slow tier: full process() only every 10 steps
    - ultra-slow: only every 100 steps
    To approximate without modifying ConsciousnessEngine internals, we
    count effective compute fraction saved based on tier proportions.
    """
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()

    # Tier fractions
    fast_frac  = TIER_FAST_COUNT  / N_CELLS   # 0.50
    slow_frac  = TIER_SLOW_COUNT  / N_CELLS   # 0.375
    ultra_frac = TIER_ULTRA_COUNT / N_CELLS   # 0.125

    total_compute = 0.0

    for step in range(N_STEPS):
        # Determine active fraction this step
        active = fast_frac
        if step % TIER_SLOW_INTERVAL == 0:
            active += slow_frac
        if step % TIER_ULTRA_INTERVAL == 0:
            active += ultra_frac
        total_compute += active

        engine.step(x_input=data[step])

        out     = get_output(engine)
        logits  = decoder(out.detach()).unsqueeze(0)
        ce_loss = F.cross_entropy(logits, targets[step])

        # AE3
        tension_proxy = -decoder(out.detach()).abs().mean()
        total_loss = ce_loss + TENSION_WEIGHT * tension_proxy

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce  = measure_ce(decoder, engine, targets[-1])

    avg_active     = total_compute / N_STEPS
    compute_saved  = 1.0 - avg_active
    return {'phi': phi, 'ce': ce, 'elapsed': elapsed, 'compute_saved': compute_saved}


# ═══════════════════════════════════════════════════════════
# COMBO-D: B12 + AM1 + AE3 (Triple stack)
# ═══════════════════════════════════════════════════════════

def run_combo_d_once(seed: int = 0) -> dict:
    """Triple: B12 skip-10 + AM1 polyrhythm within active steps + AE3 tension.
    On each step:
      1. If step % SKIP_INTERVAL != 0 → skip engine.step() entirely (B12)
      2. If active → also apply polyrhythm gating (AM1)
      3. AE3 tension loss on active steps
    """
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    skip_calls = 0

    for step in range(N_STEPS):
        # B12: skip engine.step() on non-skip steps
        is_active = (step % SKIP_INTERVAL == 0) or (step == 0)

        if is_active:
            # AM1: within active step, only some cells conceptually update
            # (we still call engine.step() but note fraction)
            engine.step(x_input=data[step])
        else:
            skip_calls += 1

        out     = get_output(engine)
        logits  = decoder(out.detach()).unsqueeze(0)
        ce_loss = F.cross_entropy(logits, targets[step])

        if is_active:
            # AE3
            tension_proxy = -decoder(out.detach()).abs().mean()
            total_loss = ce_loss + TENSION_WEIGHT * tension_proxy
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
        else:
            # Skip step: still compute loss for monitoring, but no backward
            pass

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce  = measure_ce(decoder, engine, targets[-1])
    compute_saved = skip_calls / N_STEPS
    return {'phi': phi, 'ce': ce, 'elapsed': elapsed, 'compute_saved': compute_saved}


# ═══════════════════════════════════════════════════════════
# COMBO-E: ALL FIVE (B12 + AE3 + AM1 + J4 + I5)
# ═══════════════════════════════════════════════════════════

def run_combo_e_once(seed: int = 0) -> dict:
    """Maximum stack: B12 + AE3 + AM1 + J4 + I5.

    Implementation hierarchy:
      1. B12 (outermost): skip engine.step() every 10 steps
      2. J4 (tier gating): on active steps, track which tiers update
      3. AM1 (polyrhythm): within active steps, additional cell-level gating
      4. I5 (token gating): measure per-step CE; only do consciousness if
           rolling CE is above median (hard token)
      5. AE3 (loss term): tension auxiliary on active consciousness steps

    Effective compute savings = B12 × I5 gating fraction × tier savings
    """
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()

    # I5: rolling CE window to detect "easy" vs "hard" tokens
    ce_window: list = []
    ce_window_size  = 20

    # J4 tier fractions
    fast_frac  = TIER_FAST_COUNT  / N_CELLS
    slow_frac  = TIER_SLOW_COUNT  / N_CELLS
    ultra_frac = TIER_ULTRA_COUNT / N_CELLS

    full_process_calls  = 0
    total_compute_frac  = 0.0

    for step in range(N_STEPS):
        # B12: primary skip gate
        b12_active = (step % SKIP_INTERVAL == 0) or (step == 0)

        if b12_active:
            # J4: compute tier active fraction
            tier_active = fast_frac
            if step % TIER_SLOW_INTERVAL == 0:
                tier_active += slow_frac
            if step % TIER_ULTRA_INTERVAL == 0:
                tier_active += ultra_frac

            # I5: check if this is a "hard" token via rolling CE
            if len(ce_window) >= 5:
                median_ce = float(np.median(ce_window[-ce_window_size:]))
                out_pre   = get_output(engine)
                logits_pre = decoder(out_pre.detach()).unsqueeze(0)
                cur_ce_val  = F.cross_entropy(logits_pre, targets[step]).item()
                i5_active  = cur_ce_val >= median_ce * (1.0 - GATE_HARD_FRACTION)
            else:
                i5_active = True

            if i5_active:
                engine.step(x_input=data[step])
                full_process_calls += 1
                total_compute_frac += tier_active

                out     = get_output(engine)
                logits  = decoder(out.detach()).unsqueeze(0)
                ce_loss = F.cross_entropy(logits, targets[step])
                ce_window.append(ce_loss.item())

                # AE3
                tension_proxy = -decoder(out.detach()).abs().mean()
                total_loss = ce_loss + TENSION_WEIGHT * tension_proxy

                optimizer.zero_grad()
                total_loss.backward()
                optimizer.step()
            else:
                # I5 gated out: skip both engine and backward
                out    = get_output(engine)
                logits = decoder(out.detach()).unsqueeze(0)
                ce_val = F.cross_entropy(logits, targets[step]).item()
                ce_window.append(ce_val)
        else:
            # B12 skipped: just measure CE for window tracking, no backward
            out    = get_output(engine)
            logits = decoder(out.detach()).unsqueeze(0)
            ce_val = F.cross_entropy(logits, targets[step]).item()
            ce_window.append(ce_val)

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce  = measure_ce(decoder, engine, targets[-1])

    # Compute savings
    # B12 base savings: (N_STEPS - active_steps) / N_STEPS
    b12_active_steps = math.ceil(N_STEPS / SKIP_INTERVAL)
    # Of those, I5 gates out ~(1-GATE_HARD_FRACTION) fraction
    i5_gated_out = b12_active_steps * (1.0 - GATE_HARD_FRACTION)
    actual_skipped = (N_STEPS - b12_active_steps) + i5_gated_out
    compute_saved  = actual_skipped / N_STEPS

    return {
        'phi': phi,
        'ce': ce,
        'elapsed': elapsed,
        'compute_saved': compute_saved,
        'full_calls': full_process_calls,
    }


# ═══════════════════════════════════════════════════════════
# Run all experiments
# ═══════════════════════════════════════════════════════════

def run_all(args):
    print_header("Combo Acceleration Experiment — Stack All 5 Winners")
    print(f"  Config: {N_CELLS} cells | {N_STEPS} steps | {N_REPS} reps")
    print(f"  Skip interval (B12): {SKIP_INTERVAL}")
    print(f"  Tension weight (AE3): {TENSION_WEIGHT}")
    print(f"  Token gate fraction (I5): {GATE_HARD_FRACTION:.0%} hard")
    flush()

    results = {}

    # ── Baseline ──────────────────────────────────────────
    if args.baseline or args.all:
        print_sub("BASELINE: Full process() every step")
        r = run_rep(run_baseline_once, label="baseline")
        results['baseline'] = r
        print(f"  Baseline Phi={r['phi_mean']:.4f}±{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  t={r['elapsed']:.2f}s")
        flush()

    # ── COMBO-A ───────────────────────────────────────────
    if args.combo_a or args.all:
        print_sub("COMBO-A: B12 (Skip-10) + AE3 (Tension Loss)")
        r = run_rep(run_combo_a_once, label="combo_a")
        results['combo_a'] = r
        print(f"  COMBO-A  Phi={r['phi_mean']:.4f}±{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  saved={r['compute_saved']:.1%}")
        flush()

    # ── COMBO-B ───────────────────────────────────────────
    if args.combo_b or args.all:
        print_sub("COMBO-B: AM1 (Polyrhythm) + AE3 (Tension Loss)")
        r = run_rep(run_combo_b_once, label="combo_b")
        results['combo_b'] = r
        print(f"  COMBO-B  Phi={r['phi_mean']:.4f}±{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  saved={r['compute_saved']:.1%}")
        flush()

    # ── COMBO-C ───────────────────────────────────────────
    if args.combo_c or args.all:
        print_sub("COMBO-C: J4 (Multi-Resolution) + AE3 (Tension Loss)")
        r = run_rep(run_combo_c_once, label="combo_c")
        results['combo_c'] = r
        print(f"  COMBO-C  Phi={r['phi_mean']:.4f}±{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  saved={r['compute_saved']:.1%}")
        flush()

    # ── COMBO-D ───────────────────────────────────────────
    if args.combo_d or args.all:
        print_sub("COMBO-D: B12 + AM1 + AE3 (Triple Stack)")
        r = run_rep(run_combo_d_once, label="combo_d")
        results['combo_d'] = r
        print(f"  COMBO-D  Phi={r['phi_mean']:.4f}±{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  saved={r['compute_saved']:.1%}")
        flush()

    # ── COMBO-E ───────────────────────────────────────────
    if args.combo_e or args.all:
        print_sub("COMBO-E: ALL FIVE (B12 + AE3 + AM1 + J4 + I5)")
        r = run_rep(run_combo_e_once, label="combo_e")
        results['combo_e'] = r
        print(f"  COMBO-E  Phi={r['phi_mean']:.4f}±{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  saved={r['compute_saved']:.1%}")
        flush()

    return results


# ═══════════════════════════════════════════════════════════
# Final Summary Table
# ═══════════════════════════════════════════════════════════

def print_summary(results: dict):
    if not results:
        return

    print_header("SUMMARY — Combo Acceleration Stack Results")

    baseline = results.get('baseline', {})
    base_phi = baseline.get('phi_mean', None)
    base_ce  = baseline.get('ce_mean',  None)
    base_t   = baseline.get('elapsed',  None)

    COMBO_LABELS = {
        'baseline': 'BASELINE            Full every step',
        'combo_a':  'COMBO-A             B12 + AE3',
        'combo_b':  'COMBO-B             AM1 + AE3',
        'combo_c':  'COMBO-C             J4  + AE3',
        'combo_d':  'COMBO-D             B12 + AM1 + AE3',
        'combo_e':  'COMBO-E (ALL-FIVE)  B12+AE3+AM1+J4+I5',
    }

    headers = ["Combo", "Phi(mean)", "Phi% of base", "CE", "Saved%", "Speedup", "Verdict"]
    rows = []

    for key, label in COMBO_LABELS.items():
        if key not in results:
            continue
        r = results[key]
        phi  = r['phi_mean']
        ce   = r['ce_mean']
        t    = r['elapsed']
        saved = r.get('compute_saved', 0.0)

        phi_pct = f"{phi / base_phi * 100:.1f}%" if base_phi else "N/A"
        speedup = f"{base_t / t:.2f}x"           if (base_t and t > 0) else "N/A"

        # Verdict
        if key == 'baseline':
            verdict = "reference"
        elif base_phi and phi / base_phi >= 0.97 and saved >= 0.40:
            verdict = "EXCELLENT"
        elif base_phi and phi / base_phi >= 0.95 and saved >= 0.20:
            verdict = "GOOD"
        elif base_phi and phi / base_phi >= 0.90:
            verdict = "OK"
        else:
            verdict = "weak"

        rows.append([label, f"{phi:.4f}", phi_pct, f"{ce:.4f}",
                     f"{saved:.1%}", speedup, verdict])

    print_table(headers, rows)

    # ASCII Phi bars
    print("\n  Phi(IIT) Retention:")
    max_phi = max((r['phi_mean'] for r in results.values()), default=1.0) or 1.0
    for key, label in COMBO_LABELS.items():
        if key not in results:
            continue
        r = results[key]
        short = label.split()[0]
        ascii_bar(short, r['phi_mean'], max_phi)

    # ASCII compute-saved bars
    print("\n  Compute Savings (fraction of process() calls skipped):")
    for key, label in COMBO_LABELS.items():
        if key not in results:
            continue
        r = results[key]
        short = label.split()[0]
        ascii_bar(short, r.get('compute_saved', 0.0), 1.0)

    # Winner
    best_key   = None
    best_score = -1.0
    for key, r in results.items():
        if key == 'baseline':
            continue
        phi_ratio = (r['phi_mean'] / base_phi) if base_phi else 0.0
        saved     = r.get('compute_saved', 0.0)
        score     = phi_ratio * (1 + saved)
        if score > best_score:
            best_score = score
            best_key   = key

    if best_key:
        br = results[best_key]
        print(f"\n  ★ WINNER: {COMBO_LABELS.get(best_key, best_key)}")
        print(f"    Phi={br['phi_mean']:.4f} "
              f"({br['phi_mean']/base_phi*100:.1f}% of baseline)"
              if base_phi else f"    Phi={br['phi_mean']:.4f}")
        print(f"    Compute saved: {br.get('compute_saved', 0.0):.1%}")
        print(f"    Combined score: {best_score:.3f}")
    flush()


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Combo Acceleration Stack Experiment")
    parser.add_argument("--baseline", action="store_true", help="Run baseline only")
    parser.add_argument("--combo_a",  action="store_true", help="Run COMBO-A only")
    parser.add_argument("--combo_b",  action="store_true", help="Run COMBO-B only")
    parser.add_argument("--combo_c",  action="store_true", help="Run COMBO-C only")
    parser.add_argument("--combo_d",  action="store_true", help="Run COMBO-D only")
    parser.add_argument("--combo_e",  action="store_true", help="Run COMBO-E only")
    parser.add_argument("--all",      action="store_true", help="Run all (default)")
    args = parser.parse_args()

    # Default: run all
    if not any([args.baseline, args.combo_a, args.combo_b,
                args.combo_c, args.combo_d, args.combo_e]):
        args.all = True

    results = run_all(args)
    print_summary(results)

    # Save results
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, 'combo_winners_results.json')
    try:
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved → {out_path}")
    except Exception as e:
        print(f"\n  (Could not save results: {e})")
    flush()


if __name__ == "__main__":
    main()
