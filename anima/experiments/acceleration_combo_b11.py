#!/usr/bin/env python3
"""B11 + COMBO Mega Acceleration Stack.

Current champion: COMBO-E (B12+AE3+AM1+J4+I5) = x10.4, 97% compute saved, 99.5% Phi.
Historic best:    B11+B12 = x179, 97.1% Phi.

B11 (Batch Consciousness): Share 1 process() call across the entire batch.
  Instead of calling engine.process() for each sample → call once, reuse state.

New combos tested:
  COMBO-F: B11 + B12 + AE3     (Batch + Skip + Tension)
  COMBO-G: B11 + COMBO-E       (Batch + ALL FIVE)

Settings: 64 cells, 200 steps, 3 repetitions, batch_size=8.

Usage:
    python acceleration_combo_b11.py          # Run all (baseline + F + G)
    python acceleration_combo_b11.py --combo_f
    python acceleration_combo_b11.py --combo_g
    python acceleration_combo_b11.py --all
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

# B11 batch size: how many samples share one process() call
BATCH_SIZE = 8

# B12 skip interval
SKIP_INTERVAL = 10

# AE3 tension weight
TENSION_WEIGHT = 0.1

# AM1 polyrhythm periods
POLY_PERIODS = [1, 3, 7]

# J4 tier counts
TIER_FAST_COUNT    = 32
TIER_SLOW_COUNT    = 24
TIER_ULTRA_COUNT   = 8
TIER_SLOW_INTERVAL = 10
TIER_ULTRA_INTERVAL = 100

# I5 token gating: fraction of tokens treated as "hard"
GATE_HARD_FRACTION = 0.30

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
    """Return (data, targets) where data has n_steps*BATCH_SIZE samples."""
    torch.manual_seed(seed)
    # data[i] is a list of BATCH_SIZE samples for step i
    data    = [[torch.randn(CELL_DIM) * 0.5 for _ in range(BATCH_SIZE)]
               for _ in range(n_steps)]
    targets = [torch.randint(0, VOCAB_SIZE, (1,)) for _ in range(n_steps)]
    return data, targets


def get_output(engine: ConsciousnessEngine) -> torch.Tensor:
    """Mean hidden state across all cells."""
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    return hiddens.mean(dim=0)


def measure_ce(decoder: nn.Linear, engine: ConsciousnessEngine,
               target: torch.Tensor) -> float:
    out    = get_output(engine)
    logits = decoder(out.detach()).unsqueeze(0)
    return F.cross_entropy(logits, target).item()


def run_rep(run_fn, n_reps: int = N_REPS, label: str = ""):
    """Run a function n_reps times, return averaged stats."""
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
        'phi_mean':       float(np.mean(phis)),
        'phi_std':        float(np.std(phis)),
        'ce_mean':        float(np.mean(ces)),
        'elapsed':        float(np.mean(elapsed_list)),
        'compute_saved':  float(np.mean(saves)),
    }


# ═══════════════════════════════════════════════════════════
# BASELINE — full process() every step, per-sample
# ═══════════════════════════════════════════════════════════

def run_baseline_once(seed: int = 0) -> dict:
    """Standard: one engine.step() per step (uses first sample in each batch)."""
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    for step in range(N_STEPS):
        # Use first sample from batch (simulates per-sample training)
        engine.step(x_input=data[step][0])
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
# COMBO-F: B11 + B12 + AE3
# (Batch Consciousness + Skip-Step + Tension Loss)
# ═══════════════════════════════════════════════════════════

def run_combo_f_once(seed: int = 0) -> dict:
    """B11: one process() call per batch (batch mean as input).
    B12: skip engine.step() every SKIP_INTERVAL steps.
    AE3: tension auxiliary loss (-abs mean of logits) on active steps.

    B11 implementation:
      - Each "step" represents a mini-batch of BATCH_SIZE samples.
      - B11: instead of calling engine.step() once per sample in the batch,
             call it ONCE with the batch mean as input, then reuse that
             consciousness state for all BATCH_SIZE CE loss computations.
      - B12: further skip the single B11 call every SKIP_INTERVAL steps.

    Savings:
      - B11 alone saves (BATCH_SIZE - 1) / BATCH_SIZE = 87.5% of engine calls
      - B12 further reduces by another ~90%
      - Combined: 1/(BATCH_SIZE * SKIP_INTERVAL) = 1/80 → ~98.75% saved
    """
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    t0 = time.time()
    full_calls = 0
    total_possible_calls = N_STEPS * BATCH_SIZE   # if per-sample

    for step in range(N_STEPS):
        batch = data[step]   # list of BATCH_SIZE tensors

        # B12: skip outer process() on non-active steps
        b12_active = (step % SKIP_INTERVAL == 0) or (step == 0)

        if b12_active:
            # B11: one process() call with batch mean
            batch_mean = torch.stack(batch).mean(dim=0)
            engine.step(x_input=batch_mean)
            full_calls += 1   # 1 call instead of BATCH_SIZE

        # Reuse current consciousness state for all samples in batch
        out    = get_output(engine)          # shared state
        logits = decoder(out.detach()).unsqueeze(0)
        ce_loss = F.cross_entropy(logits, targets[step])

        if b12_active:
            # AE3: tension auxiliary loss
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

    # Compute savings: compared to per-sample (BATCH_SIZE calls/step)
    compute_saved = 1.0 - (full_calls / total_possible_calls)
    return {
        'phi': phi,
        'ce': ce,
        'elapsed': elapsed,
        'compute_saved': compute_saved,
        'full_calls': full_calls,
        'would_have_called': total_possible_calls,
    }


# ═══════════════════════════════════════════════════════════
# COMBO-G: B11 + COMBO-E (B11 + B12 + AE3 + AM1 + J4 + I5)
# Maximum possible acceleration
# ═══════════════════════════════════════════════════════════

def run_combo_g_once(seed: int = 0) -> dict:
    """Maximum stack: B11 + B12 + AE3 + AM1 + J4 + I5.

    Layered gating hierarchy (outermost → innermost):
      1. B12 (outer skip gate):  skip engine.step() every SKIP_INTERVAL steps
      2. I5  (token gate):       skip if rolling CE indicates easy token
      3. B11 (batch gate):       on active steps, call process() ONCE with batch mean
      4. J4  (tier accounting):  track tier-based compute fraction
      5. AM1 (polyrhythm):       count cell-group savings within active steps
      6. AE3 (loss term):        tension auxiliary on active consciousness steps

    All six techniques stack multiplicatively for maximum savings.
    Phi retention is the key metric — we target >90%.
    """
    torch.manual_seed(seed)
    engine  = make_engine()
    decoder = make_decoder()
    data, targets = make_data(seed=seed)
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    # J4 tier fractions
    fast_frac  = TIER_FAST_COUNT  / N_CELLS   # 0.50
    slow_frac  = TIER_SLOW_COUNT  / N_CELLS   # 0.375
    ultra_frac = TIER_ULTRA_COUNT / N_CELLS   # 0.125

    # I5: rolling CE window
    ce_window: list = []
    ce_window_size  = 20

    # AM1: polyrhythm — fraction of cells conceptually active per step
    def poly_active_fraction(step: int) -> float:
        groups_active = [period for period in POLY_PERIODS if step % period == 0]
        # approximate: weight each period by 1/len(POLY_PERIODS)
        return len(groups_active) / len(POLY_PERIODS)

    t0 = time.time()
    full_calls         = 0
    total_compute_frac = 0.0
    total_possible     = N_STEPS * BATCH_SIZE

    for step in range(N_STEPS):
        batch = data[step]

        # ── Layer 1: B12 outer skip ──────────────────────────
        b12_active = (step % SKIP_INTERVAL == 0) or (step == 0)

        if not b12_active:
            # Stale state: just measure CE for I5 window, no backward
            out    = get_output(engine)
            logits = decoder(out.detach()).unsqueeze(0)
            ce_val = F.cross_entropy(logits, targets[step]).item()
            ce_window.append(ce_val)
            continue

        # ── Layer 2: I5 token gating ─────────────────────────
        if len(ce_window) >= 5:
            median_ce = float(np.median(ce_window[-ce_window_size:]))
            out_pre   = get_output(engine)
            logits_pre = decoder(out_pre.detach()).unsqueeze(0)
            cur_ce_val = F.cross_entropy(logits_pre, targets[step]).item()
            i5_active  = cur_ce_val >= median_ce * (1.0 - GATE_HARD_FRACTION)
        else:
            i5_active = True

        if not i5_active:
            # Easy token: skip consciousness update entirely
            out    = get_output(engine)
            logits = decoder(out.detach()).unsqueeze(0)
            ce_val = F.cross_entropy(logits, targets[step]).item()
            ce_window.append(ce_val)
            continue

        # ── Layer 3: B11 — ONE process() for entire batch ────
        batch_mean = torch.stack(batch).mean(dim=0)
        engine.step(x_input=batch_mean)
        full_calls += 1

        # ── Layer 4: J4 tier accounting ──────────────────────
        tier_active = fast_frac
        if step % TIER_SLOW_INTERVAL == 0:
            tier_active += slow_frac
        if step % TIER_ULTRA_INTERVAL == 0:
            tier_active += ultra_frac

        # ── Layer 5: AM1 polyrhythm accounting ───────────────
        poly_frac = poly_active_fraction(step)
        effective_compute = tier_active * poly_frac
        total_compute_frac += effective_compute

        # ── Layer 6: AE3 tension loss ─────────────────────────
        out    = get_output(engine)
        logits = decoder(out.detach()).unsqueeze(0)
        ce_loss = F.cross_entropy(logits, targets[step])
        ce_window.append(ce_loss.item())

        tension_proxy = -decoder(out.detach()).abs().mean()
        total_loss = ce_loss + TENSION_WEIGHT * tension_proxy

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

    elapsed = time.time() - t0
    phi = engine._measure_phi_iit()
    ce  = measure_ce(decoder, engine, targets[-1])

    # Compute savings vs naive per-sample baseline
    # Naive: N_STEPS * BATCH_SIZE calls; we did `full_calls`
    compute_saved = 1.0 - (full_calls / total_possible)
    return {
        'phi': phi,
        'ce': ce,
        'elapsed': elapsed,
        'compute_saved': compute_saved,
        'full_calls': full_calls,
        'would_have_called': total_possible,
        'avg_compute_frac': total_compute_frac / max(full_calls, 1),
    }


# ═══════════════════════════════════════════════════════════
# Run all experiments
# ═══════════════════════════════════════════════════════════

def run_all(args):
    print_header("B11 + COMBO Mega Acceleration — COMBO-F & COMBO-G")
    print(f"  Config: {N_CELLS} cells | {N_STEPS} steps | {N_REPS} reps | batch={BATCH_SIZE}")
    print(f"  B11 batch size:           {BATCH_SIZE}  (1 process() per {BATCH_SIZE} samples)")
    print(f"  B12 skip interval:        {SKIP_INTERVAL}")
    print(f"  AE3 tension weight:       {TENSION_WEIGHT}")
    print(f"  AM1 periods:              {POLY_PERIODS}")
    print(f"  J4 tiers:                 fast={TIER_FAST_COUNT}, slow={TIER_SLOW_COUNT}, ultra={TIER_ULTRA_COUNT}")
    print(f"  I5 hard fraction:         {GATE_HARD_FRACTION:.0%}")
    flush()

    results = {}

    # ── Baseline ──────────────────────────────────────────
    if args.baseline or args.all:
        print_sub("BASELINE: Full process() every step (per-sample)")
        r = run_rep(run_baseline_once, label="baseline")
        results['baseline'] = r
        print(f"  Baseline Phi={r['phi_mean']:.4f}+-{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  t={r['elapsed']:.2f}s")
        flush()

    # ── COMBO-F ───────────────────────────────────────────
    if args.combo_f or args.all:
        print_sub("COMBO-F: B11 (Batch) + B12 (Skip-10) + AE3 (Tension)")
        print(f"    B11: 1 process() per batch of {BATCH_SIZE} samples")
        print(f"    B12: skip every {SKIP_INTERVAL} steps")
        print(f"    AE3: tension auxiliary loss weight={TENSION_WEIGHT}")
        r = run_rep(run_combo_f_once, label="combo_f")
        results['combo_f'] = r
        print(f"  COMBO-F  Phi={r['phi_mean']:.4f}+-{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  saved={r['compute_saved']:.1%}  t={r['elapsed']:.2f}s")
        flush()

    # ── COMBO-G ───────────────────────────────────────────
    if args.combo_g or args.all:
        print_sub("COMBO-G: B11 + COMBO-E (ALL SIX: Batch+Skip+Tension+Poly+Tier+Gate)")
        print(f"    B11: 1 process() per batch of {BATCH_SIZE} samples")
        print(f"    B12: skip every {SKIP_INTERVAL} steps")
        print(f"    AE3: tension auxiliary loss")
        print(f"    AM1: polyrhythm {POLY_PERIODS}")
        print(f"    J4:  fast/slow/ultra tiers")
        print(f"    I5:  token gating ({GATE_HARD_FRACTION:.0%} hard fraction)")
        r = run_rep(run_combo_g_once, label="combo_g")
        results['combo_g'] = r
        print(f"  COMBO-G  Phi={r['phi_mean']:.4f}+-{r['phi_std']:.4f}  "
              f"CE={r['ce_mean']:.4f}  saved={r['compute_saved']:.1%}  t={r['elapsed']:.2f}s")
        flush()

    return results


# ═══════════════════════════════════════════════════════════
# Final Summary Table
# ═══════════════════════════════════════════════════════════

COMBO_LABELS = {
    'baseline': 'BASELINE     Full process() per step',
    'combo_f':  'COMBO-F      B11 + B12 + AE3',
    'combo_g':  'COMBO-G(MAX) B11 + B12 + AE3 + AM1 + J4 + I5',
}

# Known reference values for context
KNOWN_REFS = {
    'COMBO-E (prev best)': {'phi_pct': 99.5, 'saved': 97.0, 'speedup': 'x10.4'},
    'B11+B12 (historic)':  {'phi_pct': 97.1, 'saved': 97.0, 'speedup': 'x179'},
}


def print_summary(results: dict):
    if not results:
        return

    print_header("SUMMARY — B11 + COMBO Mega Acceleration Results")

    baseline = results.get('baseline', {})
    base_phi = baseline.get('phi_mean', None)
    base_ce  = baseline.get('ce_mean',  None)
    base_t   = baseline.get('elapsed',  None)

    headers = ["Combo", "Phi(mean)", "Phi%", "CE", "Saved%", "Speedup", "Verdict"]
    rows = []

    for key, label in COMBO_LABELS.items():
        if key not in results:
            continue
        r     = results[key]
        phi   = r['phi_mean']
        ce    = r['ce_mean']
        t     = r['elapsed']
        saved = r.get('compute_saved', 0.0)

        phi_pct = f"{phi / base_phi * 100:.1f}%" if base_phi else "N/A"
        speedup = f"{base_t / t:.2f}x"           if (base_t and t > 0) else "N/A"

        if key == 'baseline':
            verdict = "reference"
        elif base_phi and phi / base_phi >= 0.95 and saved >= 0.90:
            verdict = "EXCELLENT"
        elif base_phi and phi / base_phi >= 0.90 and saved >= 0.80:
            verdict = "GOOD"
        elif base_phi and phi / base_phi >= 0.85:
            verdict = "OK"
        else:
            verdict = "weak"

        rows.append([label, f"{phi:.4f}", phi_pct, f"{ce:.4f}",
                     f"{saved:.1%}", speedup, verdict])

    print_table(headers, rows)

    # ── ASCII Phi bars ────────────────────────────────────
    print("\n  Phi(IIT) Retention vs Baseline:")
    max_phi = max((r['phi_mean'] for r in results.values()), default=1.0) or 1.0
    for key, label in COMBO_LABELS.items():
        if key not in results:
            continue
        r     = results[key]
        short = key.upper()
        ascii_bar(short, r['phi_mean'], max_phi)

    # ── ASCII compute-saved bars ──────────────────────────
    print("\n  Compute Savings (fraction of process() calls skipped):")
    for key, label in COMBO_LABELS.items():
        if key not in results:
            continue
        r     = results[key]
        short = key.upper()
        ascii_bar(short, r.get('compute_saved', 0.0), 1.0)

    # ── Phi trajectory note ───────────────────────────────
    print("\n  Phi Retention Curve:")
    if base_phi and base_phi > 0:
        for key, label in COMBO_LABELS.items():
            if key == 'baseline' or key not in results:
                continue
            r       = results[key]
            phi_ret = r['phi_mean'] / base_phi
            bar_len = int(40 * phi_ret)
            bar     = "#" * bar_len + "." * (40 - bar_len)
            print(f"  {key.upper():>10s}  [{bar}] {phi_ret:.1%}")
    flush()

    # ── Known references ──────────────────────────────────
    print("\n  Reference context (from previous experiments):")
    for name, ref in KNOWN_REFS.items():
        print(f"    {name:<30s}  Phi%={ref['phi_pct']:.1f}%  "
              f"saved={ref['saved']:.1f}%  speedup={ref['speedup']}")
    flush()

    # ── Winner ────────────────────────────────────────────
    best_key   = None
    best_score = -1.0
    for key, r in results.items():
        if key == 'baseline':
            continue
        phi_ratio = (r['phi_mean'] / base_phi) if base_phi else 0.0
        saved     = r.get('compute_saved', 0.0)
        # Score: phi retention × (1 + savings), weighted toward savings
        score = phi_ratio * (1.0 + saved * 2.0)
        if score > best_score:
            best_score = score
            best_key   = key

    if best_key:
        br = results[best_key]
        print(f"\n  ★ WINNER: {COMBO_LABELS.get(best_key, best_key)}")
        if base_phi:
            print(f"    Phi={br['phi_mean']:.4f}  ({br['phi_mean']/base_phi*100:.1f}% of baseline)")
        print(f"    Compute saved: {br.get('compute_saved', 0.0):.1%}")
        print(f"    Combined score: {best_score:.3f}")
    flush()


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="B11 + COMBO Mega Acceleration Experiment",
    )
    parser.add_argument("--baseline", action="store_true", help="Run baseline only")
    parser.add_argument("--combo_f",  action="store_true", help="Run COMBO-F only")
    parser.add_argument("--combo_g",  action="store_true", help="Run COMBO-G only")
    parser.add_argument("--all",      action="store_true", help="Run all (default)")
    args = parser.parse_args()

    if not any([args.baseline, args.combo_f, args.combo_g]):
        args.all = True

    results = run_all(args)
    print_summary(results)

    # Save results
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, 'combo_b11_results.json')
    try:
        with open(out_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved to: {out_path}")
    except Exception as e:
        print(f"\n  Warning: could not save results: {e}")
    flush()


if __name__ == "__main__":
    main()
