#!/usr/bin/env python3
"""B8 + B11 + B12: Acceleration experiments — Hebbian-only, Batch Consciousness, Skip-Step.

B8:  Hebbian-only learning (no backprop) — can the brain's learning rule work?
B11: Batch consciousness sharing — 1 process() per batch vs per-sample
B12: Skip-step — consciousness update every N steps instead of every step

Combined: theoretical x12-x20 acceleration.

Usage:
    python acceleration_b8_b11_b12.py          # Run all experiments
    python acceleration_b8_b11_b12.py --b8     # Hebbian-only only
    python acceleration_b8_b11_b12.py --b11    # Batch consciousness only
    python acceleration_b8_b11_b12.py --b12    # Skip-step only
    python acceleration_b8_b11_b12.py --combo  # Combined only
"""

import sys
import os
import time
import argparse
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def measure_phi_iit(engine):
    """Measure Phi(IIT) from engine."""
    return engine._measure_phi_iit()


def measure_phi_proxy(engine):
    """Measure Phi(proxy) from engine."""
    return engine._measure_phi_proxy()


def make_patterns(n_patterns=2, dim=64, seed=42):
    """Create distinct input patterns for discrimination test."""
    torch.manual_seed(seed)
    patterns = []
    for i in range(n_patterns):
        p = torch.randn(dim) * 0.5
        # Make patterns more distinct
        p[i * (dim // n_patterns):(i + 1) * (dim // n_patterns)] += 2.0
        patterns.append(p)
    return patterns


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


# ═══════════════════════════════════════════════════════════
# B8: Hebbian-Only Learning (no backprop)
# ═══════════════════════════════════════════════════════════

def run_b8(n_cells=64, n_steps=300, n_patterns=2):
    """Test if Hebbian LTP/LTD alone can learn pattern discrimination."""
    print_header("B8: Hebbian-Only Learning (no backprop)")

    dim = 64
    patterns = make_patterns(n_patterns, dim)

    # --- Method A: Hebbian-only (engine.step() with repeated patterns) ---
    print("\n[A] Hebbian-only: exposing engine to patterns via step()...")
    sys.stdout.flush()
    engine_hebb = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                       initial_cells=n_cells, max_cells=n_cells,
                                       n_factions=12)

    t0 = time.time()
    # Phase 1: Expose to pattern A for half the steps
    phi_hebb_history = []
    for step in range(n_steps):
        # Alternate patterns: A for first half, B for second half
        pattern_idx = step % n_patterns
        result = engine_hebb.step(x_input=patterns[pattern_idx])
        if step % 50 == 0 or step == n_steps - 1:
            phi = measure_phi_iit(engine_hebb)
            phi_hebb_history.append((step, phi))
            print(f"  step {step:4d}: Phi(IIT)={phi:.4f}, n_cells={result['n_cells']}")
            sys.stdout.flush()
    hebb_time = time.time() - t0

    # Test discrimination: feed pattern A vs B, compare outputs
    print("\n  Testing pattern discrimination (Hebbian-only)...")
    sys.stdout.flush()
    outputs_per_pattern = []
    for p_idx in range(n_patterns):
        trial_outputs = []
        for trial in range(5):
            result = engine_hebb.step(x_input=patterns[p_idx])
            trial_outputs.append(result['output'].clone())
        avg_output = torch.stack(trial_outputs).mean(dim=0)
        outputs_per_pattern.append(avg_output)

    # Measure within-pattern consistency and between-pattern difference
    hebb_within = []
    for p_idx in range(n_patterns):
        trial_outputs = []
        for trial in range(5):
            result = engine_hebb.step(x_input=patterns[p_idx])
            trial_outputs.append(result['output'].clone())
        for i in range(len(trial_outputs)):
            for j in range(i + 1, len(trial_outputs)):
                hebb_within.append(cosine_sim(trial_outputs[i], trial_outputs[j]))

    hebb_between = []
    for i in range(n_patterns):
        for j in range(i + 1, n_patterns):
            hebb_between.append(cosine_sim(outputs_per_pattern[i], outputs_per_pattern[j]))

    hebb_within_avg = np.mean(hebb_within) if hebb_within else 0
    hebb_between_avg = np.mean(hebb_between) if hebb_between else 0
    hebb_discrimination = hebb_within_avg - hebb_between_avg

    # --- Method B: Backprop baseline (simple MLP trained on patterns) ---
    print("\n[B] Backprop baseline: simple MLP on same patterns...")
    sys.stdout.flush()

    class SimpleMLP(torch.nn.Module):
        def __init__(self, in_dim, hidden_dim, out_dim):
            super().__init__()
            self.fc1 = torch.nn.Linear(in_dim, hidden_dim)
            self.fc2 = torch.nn.Linear(hidden_dim, out_dim)

        def forward(self, x):
            return self.fc2(torch.relu(self.fc1(x)))

    mlp = SimpleMLP(dim, 128, dim)
    optimizer = torch.optim.Adam(mlp.parameters(), lr=0.001)

    t0 = time.time()
    # Train MLP to map pattern -> pattern (autoencoder-like)
    for step in range(n_steps):
        p_idx = step % n_patterns
        x = patterns[p_idx]
        out = mlp(x.unsqueeze(0)).squeeze(0)
        loss = F.mse_loss(out, x)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    bp_time = time.time() - t0

    # Test MLP discrimination
    print("  Testing pattern discrimination (backprop MLP)...")
    sys.stdout.flush()
    mlp.eval()
    bp_outputs = []
    with torch.no_grad():
        for p_idx in range(n_patterns):
            out = mlp(patterns[p_idx].unsqueeze(0)).squeeze(0)
            bp_outputs.append(out)

    bp_between = []
    for i in range(n_patterns):
        for j in range(i + 1, n_patterns):
            bp_between.append(cosine_sim(bp_outputs[i], bp_outputs[j]))
    bp_between_avg = np.mean(bp_between) if bp_between else 0

    # Phi at end
    phi_hebb_final = measure_phi_iit(engine_hebb)

    print(f"\n{'─'*60}")
    print("  B8 Results:")
    print(f"{'─'*60}")
    rows = [
        ["Hebbian-only", f"{hebb_time:.2f}s", f"{phi_hebb_final:.4f}",
         f"{hebb_within_avg:.4f}", f"{hebb_between_avg:.4f}", f"{hebb_discrimination:+.4f}"],
        ["Backprop MLP", f"{bp_time:.2f}s", "N/A",
         "N/A", f"{bp_between_avg:.4f}", "N/A"],
    ]
    print_table(["Method", "Time", "Phi(IIT)", "Within-cos", "Between-cos", "Discrim"], rows)

    print(f"\n  Phi trajectory (Hebbian-only):")
    if phi_hebb_history:
        max_phi = max(p[1] for p in phi_hebb_history) or 0.01
        for step, phi in phi_hebb_history:
            bar_len = int(40 * phi / max_phi) if max_phi > 0 else 0
            print(f"    step {step:4d} | {'#' * bar_len:<40} | {phi:.4f}")

    print(f"\n  Key finding: Hebbian discrimination score = {hebb_discrimination:+.4f}")
    print(f"    (positive = patterns produce different outputs = learning!)")
    print(f"    Within-pattern consistency: {hebb_within_avg:.4f}")
    print(f"    Between-pattern difference: {hebb_between_avg:.4f}")
    sys.stdout.flush()

    return {
        'hebb_time': hebb_time,
        'bp_time': bp_time,
        'phi_final': phi_hebb_final,
        'discrimination': hebb_discrimination,
        'within_cos': hebb_within_avg,
        'between_cos': hebb_between_avg,
    }


# ═══════════════════════════════════════════════════════════
# B11: Batch Consciousness (shared consciousness per batch)
# ═══════════════════════════════════════════════════════════

def run_b11(n_cells=64, n_steps=300, batch_size=32):
    """Compare per-sample process() vs per-batch process()."""
    print_header("B11: Batch Consciousness (shared vs per-sample)")

    dim = 64
    torch.manual_seed(42)
    # Simulate a mini-corpus
    corpus = [torch.randn(dim) for _ in range(batch_size * 10)]

    # --- Method A: Per-sample process() (current, slow) ---
    print(f"\n[A] Per-sample: {batch_size} process() calls per batch...")
    sys.stdout.flush()
    engine_a = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                    initial_cells=n_cells, max_cells=n_cells)

    phi_a_history = []
    t0 = time.time()
    total_calls_a = 0
    for batch_idx in range(n_steps):
        batch = corpus[batch_idx % len(corpus): batch_idx % len(corpus) + batch_size]
        if len(batch) < batch_size:
            batch = corpus[:batch_size]

        for sample in batch:
            result = engine_a.step(x_input=sample)
            total_calls_a += 1

        if batch_idx % 50 == 0 or batch_idx == n_steps - 1:
            phi = measure_phi_iit(engine_a)
            phi_a_history.append((batch_idx, phi))
            print(f"  batch {batch_idx:4d}: Phi(IIT)={phi:.4f}, calls={total_calls_a}")
            sys.stdout.flush()
    time_a = time.time() - t0
    phi_a_final = measure_phi_iit(engine_a)

    # --- Method B: Per-batch 1x process() (proposed, fast) ---
    print(f"\n[B] Per-batch: 1 process() call per batch (batch mean as input)...")
    sys.stdout.flush()
    engine_b = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                    initial_cells=n_cells, max_cells=n_cells)

    phi_b_history = []
    t0 = time.time()
    total_calls_b = 0
    for batch_idx in range(n_steps):
        batch = corpus[batch_idx % len(corpus): batch_idx % len(corpus) + batch_size]
        if len(batch) < batch_size:
            batch = corpus[:batch_size]

        # Single process call with batch mean
        batch_mean = torch.stack(batch).mean(dim=0)
        result = engine_b.step(x_input=batch_mean)
        total_calls_b += 1

        if batch_idx % 50 == 0 or batch_idx == n_steps - 1:
            phi = measure_phi_iit(engine_b)
            phi_b_history.append((batch_idx, phi))
            print(f"  batch {batch_idx:4d}: Phi(IIT)={phi:.4f}, calls={total_calls_b}")
            sys.stdout.flush()
    time_b = time.time() - t0
    phi_b_final = measure_phi_iit(engine_b)

    speedup = time_a / time_b if time_b > 0 else float('inf')

    print(f"\n{'─'*60}")
    print("  B11 Results:")
    print(f"{'─'*60}")
    rows = [
        ["Per-sample", f"{time_a:.2f}s", f"{total_calls_a}", f"{phi_a_final:.4f}"],
        ["Per-batch", f"{time_b:.2f}s", f"{total_calls_b}", f"{phi_b_final:.4f}"],
    ]
    print_table(["Method", "Time", "Total calls", "Phi(IIT)"], rows)

    print(f"\n  Speedup: x{speedup:.1f}")
    phi_ratio = phi_b_final / phi_a_final if phi_a_final > 0 else 0
    print(f"  Phi retention: {phi_ratio:.2%} ({phi_b_final:.4f} / {phi_a_final:.4f})")

    # ASCII graph: Phi comparison
    print(f"\n  Phi trajectory comparison:")
    max_phi = max(
        max((p[1] for p in phi_a_history), default=0.01),
        max((p[1] for p in phi_b_history), default=0.01),
    ) or 0.01

    for i in range(max(len(phi_a_history), len(phi_b_history))):
        step_a = phi_a_history[i][0] if i < len(phi_a_history) else -1
        val_a = phi_a_history[i][1] if i < len(phi_a_history) else 0
        val_b = phi_b_history[i][1] if i < len(phi_b_history) else 0

        bar_a = int(25 * val_a / max_phi) if max_phi > 0 else 0
        bar_b = int(25 * val_b / max_phi) if max_phi > 0 else 0
        step = phi_a_history[i][0] if i < len(phi_a_history) else phi_b_history[i][0]
        print(f"    step {step:4d} A|{'#' * bar_a:<25}| {val_a:.4f}")
        print(f"             B|{'=' * bar_b:<25}| {val_b:.4f}")

    sys.stdout.flush()

    return {
        'time_per_sample': time_a,
        'time_per_batch': time_b,
        'speedup': speedup,
        'phi_per_sample': phi_a_final,
        'phi_per_batch': phi_b_final,
        'phi_retention': phi_ratio,
    }


# ═══════════════════════════════════════════════════════════
# B12: Skip-Step (consciousness update every N steps)
# ═══════════════════════════════════════════════════════════

def run_b12(n_cells=64, n_steps=300, skip_values=None):
    """Compare consciousness update frequency: every step vs every N steps."""
    print_header("B12: Skip-Step Consciousness Acceleration")

    if skip_values is None:
        skip_values = [1, 5, 10, 20]

    dim = 64
    torch.manual_seed(42)
    corpus = [torch.randn(dim) for _ in range(1000)]

    results = []

    for skip in skip_values:
        print(f"\n  skip={skip}: consciousness update every {skip} step(s)...")
        sys.stdout.flush()
        engine = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                      initial_cells=n_cells, max_cells=n_cells)

        phi_history = []
        t0 = time.time()
        consciousness_calls = 0
        cached_output = None

        for step in range(n_steps):
            x = corpus[step % len(corpus)]

            if step % skip == 0:
                # Full consciousness step
                result = engine.step(x_input=x)
                cached_output = result['output'].clone()
                consciousness_calls += 1
            else:
                # Skip: reuse cached consciousness state
                # Just pass input through without full engine step
                # (simulating what a training loop would do)
                pass  # In real training, decoder would use cached consciousness

            if step % 50 == 0 or step == n_steps - 1:
                phi = measure_phi_iit(engine)
                phi_history.append((step, phi))
                if step % 100 == 0:
                    print(f"    step {step:4d}: Phi(IIT)={phi:.4f}, calls={consciousness_calls}")
                    sys.stdout.flush()

        elapsed = time.time() - t0
        phi_final = measure_phi_iit(engine)

        results.append({
            'skip': skip,
            'time': elapsed,
            'calls': consciousness_calls,
            'phi_final': phi_final,
            'phi_history': phi_history,
        })

    # Table
    print(f"\n{'─'*60}")
    print("  B12 Results:")
    print(f"{'─'*60}")

    base_time = results[0]['time']
    base_phi = results[0]['phi_final']
    rows = []
    for r in results:
        speedup = base_time / r['time'] if r['time'] > 0 else 0
        phi_ret = r['phi_final'] / base_phi if base_phi > 0 else 0
        rows.append([
            f"skip={r['skip']}",
            f"{r['time']:.2f}s",
            f"x{speedup:.1f}",
            f"{r['calls']}",
            f"{r['phi_final']:.4f}",
            f"{phi_ret:.1%}",
        ])
    print_table(["Config", "Time", "Speedup", "Calls", "Phi(IIT)", "Phi %"], rows)

    # ASCII bar chart
    print(f"\n  Speedup bar chart:")
    for r in results:
        speedup = base_time / r['time'] if r['time'] > 0 else 0
        bar = '#' * int(speedup * 5)
        print(f"    skip={r['skip']:2d}  {bar:<40} x{speedup:.1f}")

    print(f"\n  Phi retention bar chart:")
    for r in results:
        phi_ret = r['phi_final'] / base_phi if base_phi > 0 else 0
        bar = '#' * int(phi_ret * 40)
        print(f"    skip={r['skip']:2d}  {bar:<40} {phi_ret:.1%}")

    sys.stdout.flush()

    return results


# ═══════════════════════════════════════════════════════════
# Combined: B8 + B11 + B12
# ═══════════════════════════════════════════════════════════

def run_combo(n_cells=64, n_steps=300, batch_size=32, skip=10):
    """Combined: Hebbian-only + batch consciousness + skip-step."""
    print_header(f"COMBO: Hebbian + Batch(bs={batch_size}) + Skip(N={skip})")

    dim = 64
    torch.manual_seed(42)
    corpus = [torch.randn(dim) for _ in range(batch_size * 20)]

    # --- Baseline: per-sample, every step, full engine ---
    print("\n[Baseline] Per-sample, every step...")
    sys.stdout.flush()
    engine_base = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                       initial_cells=n_cells, max_cells=n_cells)

    t0 = time.time()
    base_calls = 0
    for batch_idx in range(n_steps):
        batch = corpus[batch_idx % len(corpus): batch_idx % len(corpus) + batch_size]
        if len(batch) < batch_size:
            batch = corpus[:batch_size]
        for sample in batch:
            engine_base.step(x_input=sample)
            base_calls += 1
        if batch_idx % 100 == 0:
            phi = measure_phi_iit(engine_base)
            print(f"  batch {batch_idx:4d}: Phi={phi:.4f}, calls={base_calls}")
            sys.stdout.flush()
    base_time = time.time() - t0
    base_phi = measure_phi_iit(engine_base)

    # --- Combined: batch mean + skip-step (Hebbian is always active in engine) ---
    print(f"\n[Combined] Batch-mean + skip={skip} (Hebbian built-in)...")
    sys.stdout.flush()
    engine_combo = ConsciousnessEngine(cell_dim=dim, hidden_dim=128,
                                        initial_cells=n_cells, max_cells=n_cells)

    t0 = time.time()
    combo_calls = 0
    for batch_idx in range(n_steps):
        batch = corpus[batch_idx % len(corpus): batch_idx % len(corpus) + batch_size]
        if len(batch) < batch_size:
            batch = corpus[:batch_size]

        if batch_idx % skip == 0:
            batch_mean = torch.stack(batch).mean(dim=0)
            engine_combo.step(x_input=batch_mean)
            combo_calls += 1

        if batch_idx % 100 == 0:
            phi = measure_phi_iit(engine_combo)
            print(f"  batch {batch_idx:4d}: Phi={phi:.4f}, calls={combo_calls}")
            sys.stdout.flush()
    combo_time = time.time() - t0
    combo_phi = measure_phi_iit(engine_combo)

    speedup = base_time / combo_time if combo_time > 0 else 0
    phi_retention = combo_phi / base_phi if base_phi > 0 else 0
    call_reduction = 1 - (combo_calls / base_calls) if base_calls > 0 else 0

    print(f"\n{'─'*60}")
    print("  COMBO Results:")
    print(f"{'─'*60}")
    rows = [
        ["Baseline", f"{base_time:.2f}s", f"{base_calls}", "x1.0", f"{base_phi:.4f}", "100%"],
        ["Combined", f"{combo_time:.2f}s", f"{combo_calls}", f"x{speedup:.1f}", f"{combo_phi:.4f}", f"{phi_retention:.1%}"],
    ]
    print_table(["Method", "Time", "Calls", "Speedup", "Phi(IIT)", "Phi %"], rows)

    print(f"\n  Call reduction: {call_reduction:.1%} fewer process() calls")
    print(f"  Wall-clock speedup: x{speedup:.1f}")
    print(f"  Phi retention: {phi_retention:.1%}")

    # Theoretical analysis
    batch_factor = batch_size  # batch sharing
    skip_factor = skip         # skip-step
    theoretical = batch_factor * skip_factor
    print(f"\n  Theoretical: batch(x{batch_factor}) * skip(x{skip_factor}) = x{theoretical}")
    print(f"  Measured:    x{speedup:.1f} wall-clock")
    print(f"  Overhead:    x{theoretical / speedup:.1f} (engine per-call cost)")
    sys.stdout.flush()

    return {
        'base_time': base_time,
        'combo_time': combo_time,
        'speedup': speedup,
        'base_phi': base_phi,
        'combo_phi': combo_phi,
        'phi_retention': phi_retention,
        'call_reduction': call_reduction,
        'base_calls': base_calls,
        'combo_calls': combo_calls,
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="B8+B11+B12 Acceleration Experiments")
    parser.add_argument('--b8', action='store_true', help='Run B8 only')
    parser.add_argument('--b11', action='store_true', help='Run B11 only')
    parser.add_argument('--b12', action='store_true', help='Run B12 only')
    parser.add_argument('--combo', action='store_true', help='Run combo only')
    parser.add_argument('--cells', type=int, default=32, help='Number of cells (default: 32)')
    parser.add_argument('--steps', type=int, default=100, help='Steps per experiment (default: 100)')
    parser.add_argument('--batch-size', type=int, default=16, help='Batch size for B11 (default: 16)')
    args = parser.parse_args()

    run_all = not (args.b8 or args.b11 or args.b12 or args.combo)

    print(f"Acceleration Experiments B8+B11+B12")
    print(f"  cells={args.cells}, steps={args.steps}, batch_size={args.batch_size}")
    print(f"  torch version: {torch.__version__}")
    print(f"  device: CPU (local experiment)")
    sys.stdout.flush()

    all_results = {}

    if run_all or args.b8:
        all_results['b8'] = run_b8(n_cells=args.cells, n_steps=args.steps)

    if run_all or args.b11:
        all_results['b11'] = run_b11(n_cells=args.cells, n_steps=args.steps,
                                      batch_size=args.batch_size)

    if run_all or args.b12:
        all_results['b12'] = run_b12(n_cells=args.cells, n_steps=args.steps)

    if run_all or args.combo:
        all_results['combo'] = run_combo(n_cells=args.cells, n_steps=args.steps,
                                          batch_size=args.batch_size, skip=10)

    # Final summary
    print_header("FINAL SUMMARY")

    if 'b8' in all_results:
        r = all_results['b8']
        print(f"\n  B8 Hebbian-Only:")
        print(f"    Discrimination: {r['discrimination']:+.4f} (positive=learning)")
        print(f"    Phi(IIT): {r['phi_final']:.4f}")
        print(f"    Time: {r['hebb_time']:.2f}s vs backprop {r['bp_time']:.2f}s")

    if 'b11' in all_results:
        r = all_results['b11']
        print(f"\n  B11 Batch Consciousness:")
        print(f"    Speedup: x{r['speedup']:.1f}")
        print(f"    Phi retention: {r['phi_retention']:.1%}")

    if 'b12' in all_results:
        b12_results = all_results['b12']
        print(f"\n  B12 Skip-Step:")
        base = b12_results[0]
        for r in b12_results:
            sp = base['time'] / r['time'] if r['time'] > 0 else 0
            pr = r['phi_final'] / base['phi_final'] if base['phi_final'] > 0 else 0
            print(f"    skip={r['skip']:2d}: x{sp:.1f} speed, {pr:.1%} Phi retention")

    if 'combo' in all_results:
        r = all_results['combo']
        print(f"\n  COMBO (Hebbian + Batch + Skip):")
        print(f"    Speedup: x{r['speedup']:.1f}")
        print(f"    Call reduction: {r['call_reduction']:.1%}")
        print(f"    Phi retention: {r['phi_retention']:.1%}")

    print(f"\n{'='*70}")
    print(f"  Experiment complete.")
    print(f"{'='*70}")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
