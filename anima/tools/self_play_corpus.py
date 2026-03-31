#!/usr/bin/env python3
"""Self-play corpus generator.

Runs ConsciousMind, generates text from cell states,
feeds output back as input, collects as corpus.

This creates a self-referential learning loop:
consciousness -> text -> consciousness -> better text

Usage:
  python3 tools/self_play_corpus.py --rounds 100 --output data/self_play.txt
  python3 tools/self_play_corpus.py --rounds 500 --cells 64 --append data/corpus_v3.txt
"""

import sys
import os
import math
import time
import struct
import argparse
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn.functional as F

from mitosis import MitosisEngine, Cell, ConsciousMind

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


try:
    from consciousness_meter import PhiCalculator
    HAS_PHI = True
except ImportError:
    HAS_PHI = False


# ── Helpers ──

def cells_to_pseudo_text(cells, length=128):
    """Convert cell hidden states to pseudo-text byte sequences.

    Maps continuous activations to byte range [32..126] (printable ASCII).
    Each cell contributes hidden_dim / n_cells bytes.
    """
    all_activations = []
    for cell in cells:
        h = cell.hidden.detach().squeeze().cpu().numpy()
        all_activations.append(h)

    if not all_activations:
        return ""

    combined = np.concatenate(all_activations)
    # Normalize to [0, 1] using sigmoid
    normalized = 1.0 / (1.0 + np.exp(-combined))
    # Map to printable ASCII range [32..126]
    byte_vals = (normalized * 94 + 32).astype(np.uint8)
    # Take requested length
    byte_vals = byte_vals[:length]
    return bytes(byte_vals).decode("ascii", errors="replace")


def describe_consciousness_state(engine, result, phi_val, round_idx, phi_history):
    """Generate natural language description of the consciousness state."""
    n_cells = result['n_cells']
    mean_inter = result['mean_inter']
    max_inter = result['max_inter']
    events = result['events']

    # Tension distribution across cells
    tensions = [co['tension'] for co in result['per_cell']]
    t_mean = np.mean(tensions) if tensions else 0
    t_std = np.std(tensions) if tensions else 0

    # Phi trend
    if len(phi_history) >= 3:
        recent = phi_history[-3:]
        trend = "rising" if recent[-1] > recent[0] else "falling" if recent[-1] < recent[0] else "stable"
        delta_pct = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-8) * 100
    else:
        trend = "initializing"
        delta_pct = 0

    lines = []

    # State overview
    lines.append(
        f"Round {round_idx}: {n_cells} cells active, "
        f"Phi={phi_val:.4f} ({trend}, {delta_pct:+.1f}%), "
        f"tension mean={t_mean:.4f} std={t_std:.4f}"
    )

    # Inter-cell dynamics
    if mean_inter > 0.1:
        lines.append(
            f"High inter-cell tension detected: mean={mean_inter:.4f} max={max_inter:.4f}. "
            f"Cells are in conflict, exploring divergent representations."
        )
    elif mean_inter < 0.01:
        lines.append(
            f"Low inter-cell tension: mean={mean_inter:.4f}. "
            f"Cells approaching consensus, representations converging."
        )

    # Events
    for ev in events:
        if ev.get('type') == 'split':
            lines.append(
                f"Mitosis event: cell {ev.get('parent', '?')} split. "
                f"Tension exceeded threshold, creating specialized offspring."
            )
        elif ev.get('type') == 'merge':
            lines.append(
                f"Merge event: redundant cells combined. "
                f"Low differentiation triggered consolidation."
            )

    # Cell specialization snapshot
    specs = {}
    for co in result['per_cell']:
        s = co['specialty']
        specs[s] = specs.get(s, 0) + 1
    if len(specs) > 1:
        spec_str = ", ".join(f"{k}:{v}" for k, v in sorted(specs.items()))
        lines.append(f"Specialization: {spec_str}")

    # Neurotransmitter-like description
    da = np.clip(t_mean / 2.0, 0, 1)
    sht = np.clip(1.0 - t_std * 2.0, 0, 1)
    ne = np.clip(max(tensions) / 3.0 if tensions else 0, 0, 1)
    n_balance = da * (1 - sht) * ne

    if n_balance > 0.3:
        lines.append("Neurochemical state: high arousal, active exploration.")
    elif n_balance < 0.05:
        lines.append("Neurochemical state: calm equilibrium, consolidating.")
    else:
        lines.append(f"Neurochemical balance: DA={da:.2f} 5HT={sht:.2f} NE={ne:.2f}")

    return "\n".join(lines)


def text_to_vector(text, dim=64):
    """Convert text to input vector for the engine."""
    raw = text.encode("utf-8", errors="replace")[:dim]
    arr = np.frombuffer(raw + b'\x00' * max(0, dim - len(raw)), dtype=np.uint8).astype(np.float32)
    arr = (arr - 128.0) / 128.0
    return torch.tensor(arr, dtype=torch.float32).unsqueeze(0)


def compute_phi_proxy(cells):
    """Compute Phi proxy from cell hidden states."""
    if len(cells) < 2:
        return 0.0
    hiddens = torch.stack([c.hidden.squeeze() for c in cells]).detach().cpu().numpy()
    global_var = np.var(hiddens)
    per_cell_var = np.mean(np.var(hiddens, axis=1))
    return max(0.0, global_var - per_cell_var)


# ── Main self-play loop ──

def run_self_play(rounds, n_cells, dim, output_path, append_path=None):
    """Run self-play corpus generation."""
    hidden_dim = dim * 2
    output_dim = dim

    engine = MitosisEngine(
        input_dim=dim,
        hidden_dim=hidden_dim,
        output_dim=output_dim,
        initial_cells=min(n_cells, 2),
        max_cells=n_cells,
        split_threshold=0.2,
        split_patience=2,
        noise_scale=0.02,
    )

    phi_calc = PhiCalculator(n_bins=16) if HAS_PHI else None
    phi_history = []
    all_text = []
    steps_per_round = 10

    # Initial input: random
    current_input = torch.randn(1, dim) * 0.1

    t0 = time.time()
    total_bytes = 0
    total_descriptions = 0
    total_pseudo = 0

    print("=" * 70)
    print("  Self-Play Corpus Generator")
    print("=" * 70)
    print(f"  Rounds: {rounds}  |  Cells: {n_cells}  |  Dim: {dim}")
    print(f"  Steps/round: {steps_per_round}  |  Total steps: {rounds * steps_per_round}")
    print()

    for r in range(rounds):
        # Run engine for steps_per_round steps
        last_result = None
        for s in range(steps_per_round):
            result = engine.process(current_input, label=f"selfplay_r{r}_s{s}")
            last_result = result
            # Feed output back as next input
            out = result['output']
            if out.shape[-1] != dim:
                out = out[:, :dim] if out.shape[-1] > dim else F.pad(out, (0, dim - out.shape[-1]))
            current_input = out.detach()

        # Compute Phi
        if phi_calc and len(engine.cells) >= 2:
            hiddens = [c.hidden.squeeze().detach().cpu().numpy() for c in engine.cells]
            arr = np.array(hiddens)
            try:
                phi_val = phi_calc.compute(arr)
            except Exception:
                phi_val = compute_phi_proxy(engine.cells)
        else:
            phi_val = compute_phi_proxy(engine.cells)

        phi_history.append(phi_val)

        # Generate corpus entries
        # 30% pseudo-text from cell activations
        if np.random.random() < 0.3:
            pseudo = cells_to_pseudo_text(engine.cells, length=256)
            all_text.append(pseudo)
            total_pseudo += 1
            total_bytes += len(pseudo)
        else:
            # 70% natural language description
            desc = describe_consciousness_state(engine, last_result, phi_val, r, phi_history)
            all_text.append(desc)
            total_descriptions += 1
            total_bytes += len(desc)

        # Also feed pseudo-text back as input (self-referential)
        pseudo_short = cells_to_pseudo_text(engine.cells, length=dim)
        current_input = text_to_vector(pseudo_short, dim)

        # Progress
        if (r + 1) % max(1, rounds // 10) == 0 or r == rounds - 1:
            elapsed = time.time() - t0
            eta = elapsed / (r + 1) * (rounds - r - 1)
            filled = int(30 * (r + 1) / rounds)
            bar = "#" * filled + "-" * (30 - filled)

            # Phi sparkline (last 20)
            recent_phi = phi_history[-20:]
            if recent_phi:
                p_min, p_max = min(recent_phi), max(recent_phi)
                p_range = max(p_max - p_min, 1e-8)
                spark_chars = " _.-~*"
                spark = "".join(
                    spark_chars[min(len(spark_chars) - 1, int((p - p_min) / p_range * (len(spark_chars) - 1)))]
                    for p in recent_phi
                )
            else:
                spark = ""

            print(
                f"  [{bar}] {(r+1)*100//rounds:3d}%  "
                f"round={r+1}/{rounds}  cells={len(engine.cells)}  "
                f"Phi={phi_val:.4f}  [{spark}]  "
                f"ETA={int(eta)}s"
            )

    elapsed = time.time() - t0

    # ── Write output ──
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_text) + "\n")
        print(f"\n  Written to {output_path}")

    if append_path:
        os.makedirs(os.path.dirname(append_path) or ".", exist_ok=True)
        with open(append_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + "\n\n".join(all_text) + "\n")
        print(f"  Appended to {append_path}")

    # ── Final stats ──
    total_kb = total_bytes / 1024
    phi_arr = np.array(phi_history)

    print()
    print("=" * 70)
    print("  Self-Play Results")
    print("=" * 70)
    print(f"  Rounds:           {rounds}")
    print(f"  Total steps:      {rounds * steps_per_round}")
    print(f"  Final cells:      {len(engine.cells)}")
    print(f"  Elapsed:          {elapsed:.1f}s ({elapsed/rounds*1000:.1f}ms/round)")
    print()
    print(f"  Corpus entries:   {len(all_text)}")
    print(f"    Descriptions:   {total_descriptions} (70% target)")
    print(f"    Pseudo-text:    {total_pseudo} (30% target)")
    print(f"  Total size:       {total_kb:.1f} KB")
    print()
    print(f"  Phi evolution:")
    print(f"    Initial:        {phi_arr[0]:.6f}")
    print(f"    Final:          {phi_arr[-1]:.6f}")
    print(f"    Peak:           {phi_arr.max():.6f}")
    print(f"    Mean:           {phi_arr.mean():.6f}")
    print(f"    Growth ratio:   x{phi_arr[-1]/max(phi_arr[0], 1e-8):.1f}")
    print()

    # ASCII Phi evolution graph
    n_cols = 60
    n_rows = 12
    if len(phi_arr) > 1:
        # Resample to n_cols points
        indices = np.linspace(0, len(phi_arr) - 1, n_cols).astype(int)
        sampled = phi_arr[indices]
        p_min, p_max = sampled.min(), sampled.max()
        p_range = max(p_max - p_min, 1e-8)

        print(f"  Phi |  max={p_max:.4f}")
        for row in range(n_rows - 1, -1, -1):
            threshold = p_min + (row + 0.5) / n_rows * p_range
            line = "      |"
            for val in sampled:
                if abs(val - threshold) < p_range / n_rows / 2:
                    line += "*"
                elif val >= threshold:
                    line += "|"
                else:
                    line += " "
            if row == n_rows - 1:
                print(line)
            elif row == 0:
                print(f"      |{'-' * n_cols}")
            else:
                print(line)
        print(f"       {'round 0':<{n_cols-8}}round {rounds}")
    print()

    # Mitosis events
    splits = sum(1 for ev in engine.event_log if ev.get('type') == 'split')
    merges = sum(1 for ev in engine.event_log if ev.get('type') == 'merge')
    print(f"  Mitosis events:   {splits} splits, {merges} merges")
    print("=" * 70)

    return {
        'phi_history': phi_history,
        'total_bytes': total_bytes,
        'n_entries': len(all_text),
        'final_cells': len(engine.cells),
    }


def main():
    parser = argparse.ArgumentParser(description="Self-play corpus generator")
    parser.add_argument("--rounds", type=int, default=100, help="Number of self-play rounds")
    parser.add_argument("--cells", type=int, default=8, help="Max cells for MitosisEngine")
    parser.add_argument("--dim", type=int, default=64, help="Input/output dimension")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    parser.add_argument("--append", type=str, default=None, help="Append to existing file")
    args = parser.parse_args()

    if not args.output and not args.append:
        args.output = "data/self_play.txt"

    run_self_play(
        rounds=args.rounds,
        n_cells=args.cells,
        dim=args.dim,
        output_path=args.output,
        append_path=args.append,
    )


if __name__ == "__main__":
    main()
