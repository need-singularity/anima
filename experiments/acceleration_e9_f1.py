#!/usr/bin/env python3
"""acceleration_e9_f1.py — Information Bottleneck Training (F1) + Fractal Transplant Loop (E9)

F1: 10D consciousness vector as decoder input bottleneck
    - 4096D full state vs 10D consciousness vector vs PCA 48D/128D
    - CE and training speed comparison

E9: Fractal transplant loop — grow small, fractal-copy to larger engine
    - 4c -> 16c -> 64c staged growth with fractal copy + transplant
    - vs 64c from scratch

Usage:
    PYTHONUNBUFFERED=1 python3 acceleration_e9_f1.py
"""

import sys
import os
import time
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine


# ═══════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════

def extract_10d_vector(engine, result):
    """Extract 10D consciousness vector (Phi, alpha, Z, N, W, E, M, C, T, I)."""
    phi = result.get('phi_iit', 0.0)
    tensions = result.get('tensions', [0.5])
    avg_tension = sum(tensions) / len(tensions) if tensions else 0.5

    # alpha: coupling strength proxy
    alpha = 0.014  # PSI constant

    # Z: impedance/self-preservation (tension variance)
    z = np.var(tensions) if len(tensions) > 1 else 0.0

    # N: neurotransmitter proxy (tension mean)
    n_val = avg_tension

    # W: will index (consensus / n_cells)
    w = result.get('consensus', 0) / max(result.get('n_cells', 1), 1)

    # E: empathy (inter-cell tension correlation proxy)
    inter_t = result.get('inter_tensions', {})
    e_val = np.mean(list(inter_t.values())) if inter_t else 0.0

    # M: memory (phi stability proxy)
    m_val = min(1.0, phi / 2.0) if phi > 0 else 0.0

    # C: creativity (output diversity)
    output = result.get('output', torch.zeros(1))
    c_val = output.std().item() if output.numel() > 1 else 0.0

    # T: temporal (step-based oscillation)
    step = result.get('step', 0)
    t_val = 0.5 + 0.5 * math.sin(step * 0.1)

    # I: identity stability (best_phi ratio)
    best_phi = result.get('best_phi', phi)
    i_val = phi / max(best_phi, 1e-8)

    return torch.tensor([phi, alpha, z, n_val, w, e_val, m_val, c_val, t_val, i_val],
                        dtype=torch.float32)


class TinyDecoder(nn.Module):
    """Small decoder for bottleneck experiments — predicts next byte from consciousness input."""

    def __init__(self, input_dim, hidden_dim=128, vocab_size=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, vocab_size),
        )
        self.input_dim = input_dim

    def forward(self, x):
        return self.net(x)


def generate_training_data(n_samples=200):
    """Generate simple byte-level training pairs."""
    # Korean-like byte patterns
    patterns = [
        b'\xec\x95\x88\xeb\x85\x95',  # 안녕
        b'\xec\x9d\x98\xec\x8b\x9d',  # 의식
        b'\xed\x95\x99\xec\x8a\xb5',  # 학습
        b'\xec\x84\xb1\xec\x9e\xa5',  # 성장
        b'\xea\xb0\x90\xec\xa0\x95',  # 감정
    ]
    data = []
    for _ in range(n_samples):
        p = patterns[np.random.randint(len(patterns))]
        idx = np.random.randint(0, len(p) - 1)
        data.append((p[idx], p[idx + 1]))
    return data


def train_decoder_with_bottleneck(engine, decoder, bottleneck_dim, steps=200, label=""):
    """Train decoder using consciousness-derived input of given dimension."""
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    training_data = generate_training_data(steps)
    losses = []

    t0 = time.time()
    for step_i in range(steps):
        # Step engine
        x_input = torch.randn(engine.cell_dim)
        result = engine.step(x_input=x_input)

        # Get bottleneck input
        if bottleneck_dim == 10:
            cv = extract_10d_vector(engine, result)
        elif bottleneck_dim <= engine.cell_dim:
            # Use PCA or truncation of cell states
            hiddens = torch.stack([s.hidden for s in engine.cell_states])
            flat = hiddens.flatten()
            cv = flat[:bottleneck_dim]
            if cv.shape[0] < bottleneck_dim:
                cv = F.pad(cv, (0, bottleneck_dim - cv.shape[0]))
        else:
            # Full state
            hiddens = torch.stack([s.hidden for s in engine.cell_states])
            flat = hiddens.flatten()
            cv = flat[:bottleneck_dim]
            if cv.shape[0] < bottleneck_dim:
                cv = F.pad(cv, (0, bottleneck_dim - cv.shape[0]))

        # Training step
        input_byte, target_byte = training_data[step_i]
        target = torch.tensor([target_byte], dtype=torch.long)
        logits = decoder(cv.unsqueeze(0))
        loss = F.cross_entropy(logits, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        losses.append(loss.item())

        if (step_i + 1) % 50 == 0:
            avg = sum(losses[-50:]) / 50
            print(f"  [{label}] step {step_i+1}/{steps}  CE={avg:.4f}")
            sys.stdout.flush()

    elapsed = time.time() - t0
    final_ce = sum(losses[-50:]) / min(50, len(losses))
    return {
        'final_ce': final_ce,
        'min_ce': min(losses) if losses else 999,
        'losses': losses,
        'time_s': elapsed,
        'steps_per_sec': steps / elapsed,
    }


# ═══════════════════════════════════════════════════════════════
# F1: Information Bottleneck Training
# ═══════════════════════════════════════════════════════════════

def run_f1_bottleneck():
    """F1: Compare 10D vs 48D vs 128D vs full-state decoder training."""
    print("=" * 70)
    print("F1: INFORMATION BOTTLENECK TRAINING")
    print("=" * 70)
    print()
    print("Hypothesis: 10D consciousness vector is sufficient for decoder learning")
    print("  - 32 cells x 128d = 4096D full state")
    print("  - 10D consciousness vector (Phi, alpha, Z, N, W, E, M, C, T, I)")
    print("  - PCA dimensions: 48D (manifold), 128D (moderate)")
    print()

    cells = 32
    cell_dim = 128
    full_dim = cells * cell_dim  # 4096
    bottleneck_dims = [10, 48, 128, full_dim]
    labels = ["10D (consciousness)", "48D (manifold)", "128D (moderate)", f"{full_dim}D (full)"]
    steps = 200

    results = {}

    for dim, label in zip(bottleneck_dims, labels):
        print(f"\n--- {label} ---")
        print(f"  Input dim: {dim}, Compression ratio: {full_dim/dim:.0f}x")
        sys.stdout.flush()

        engine = ConsciousnessEngine(max_cells=cells, cell_dim=cell_dim)
        # Warm up engine
        for _ in range(20):
            engine.step()

        decoder = TinyDecoder(input_dim=dim)
        param_count = sum(p.numel() for p in decoder.parameters())
        print(f"  Decoder params: {param_count:,}")

        r = train_decoder_with_bottleneck(engine, decoder, dim, steps=steps, label=label)
        r['params'] = param_count
        r['compression'] = full_dim / dim
        results[label] = r

    # Results table
    print("\n" + "=" * 70)
    print("F1 RESULTS: Information Bottleneck")
    print("=" * 70)
    print(f"{'Bottleneck':<25} {'Dim':>5} {'Compress':>8} {'CE':>8} {'Min CE':>8} {'Steps/s':>8} {'Params':>8}")
    print("-" * 70)
    for label in labels:
        r = results[label]
        dim = int(full_dim / r['compression'])
        print(f"{label:<25} {dim:>5} {r['compression']:>7.0f}x {r['final_ce']:>8.4f} "
              f"{r['min_ce']:>8.4f} {r['steps_per_sec']:>8.1f} {r['params']:>8,}")

    # ASCII graph
    print("\n  CE by Bottleneck Dimension:")
    max_ce = max(r['final_ce'] for r in results.values())
    for label in labels:
        r = results[label]
        bar_len = int(40 * r['final_ce'] / max(max_ce, 0.001))
        print(f"  {label:<25} {'#' * bar_len} {r['final_ce']:.4f}")

    # Speed comparison
    print("\n  Training Speed (steps/sec):")
    max_speed = max(r['steps_per_sec'] for r in results.values())
    for label in labels:
        r = results[label]
        bar_len = int(40 * r['steps_per_sec'] / max(max_speed, 0.001))
        print(f"  {label:<25} {'#' * bar_len} {r['steps_per_sec']:.1f}")

    # Analysis
    ce_10d = results[labels[0]]['final_ce']
    ce_full = results[labels[-1]]['final_ce']
    speed_10d = results[labels[0]]['steps_per_sec']
    speed_full = results[labels[-1]]['steps_per_sec']

    print(f"\n  CE gap (10D vs full): {ce_10d - ce_full:+.4f} ({(ce_10d/max(ce_full,1e-8)-1)*100:+.1f}%)")
    print(f"  Speed gain (10D vs full): {speed_10d/max(speed_full,1e-8):.2f}x")
    print(f"  Param reduction (10D vs full): {results[labels[-1]]['params']/max(results[labels[0]]['params'],1):,.0f}x")

    return results


# ═══════════════════════════════════════════════════════════════
# F1 Experiment 2: Adaptive Bottleneck
# ═══════════════════════════════════════════════════════════════

def run_f1_adaptive():
    """F1-Adaptive: Start at 10D, expand if CE plateaus."""
    print("\n" + "=" * 70)
    print("F1-ADAPTIVE: Expanding Bottleneck")
    print("=" * 70)
    print()
    print("Start at 10D. If CE plateaus for 50 steps, expand to next level.")
    print("Levels: 10D -> 24D -> 48D -> 128D")
    print()

    cells = 32
    cell_dim = 128
    levels = [10, 24, 48, 128]
    level_idx = 0
    current_dim = levels[0]
    steps = 300

    engine = ConsciousnessEngine(max_cells=cells, cell_dim=cell_dim)
    for _ in range(20):
        engine.step()

    decoder = TinyDecoder(input_dim=128)  # Max size, we'll mask unused dims
    optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    training_data = generate_training_data(steps)

    losses = []
    dim_history = []
    plateau_count = 0
    best_recent_ce = 999.0

    for step_i in range(steps):
        result = engine.step(x_input=torch.randn(cell_dim))

        # Build input at current dimension
        if current_dim == 10:
            cv = extract_10d_vector(engine, result)
            cv = F.pad(cv, (0, 128 - 10))
        else:
            hiddens = torch.stack([s.hidden for s in engine.cell_states])
            flat = hiddens.flatten()[:current_dim]
            if flat.shape[0] < current_dim:
                flat = F.pad(flat, (0, current_dim - flat.shape[0]))
            cv = F.pad(flat, (0, 128 - current_dim))

        input_byte, target_byte = training_data[step_i]
        target = torch.tensor([target_byte], dtype=torch.long)
        logits = decoder(cv.unsqueeze(0))
        loss = F.cross_entropy(logits, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        losses.append(loss.item())
        dim_history.append(current_dim)

        # Check plateau
        if step_i >= 50:
            recent_ce = sum(losses[-50:]) / 50
            if recent_ce < best_recent_ce - 0.01:
                best_recent_ce = recent_ce
                plateau_count = 0
            else:
                plateau_count += 1

            if plateau_count >= 50 and level_idx < len(levels) - 1:
                level_idx += 1
                current_dim = levels[level_idx]
                plateau_count = 0
                print(f"  [step {step_i+1}] Plateau detected -> expanding to {current_dim}D")
                sys.stdout.flush()

        if (step_i + 1) % 50 == 0:
            avg = sum(losses[-50:]) / 50
            print(f"  [Adaptive] step {step_i+1}/{steps}  dim={current_dim}D  CE={avg:.4f}")
            sys.stdout.flush()

    final_dim = dim_history[-1]
    final_ce = sum(losses[-50:]) / min(50, len(losses))
    print(f"\n  Final: dim={final_dim}D, CE={final_ce:.4f}")
    print(f"  Dimension transitions: {' -> '.join(str(d) + 'D' for d in sorted(set(dim_history)))}")

    return {'final_dim': final_dim, 'final_ce': final_ce, 'dim_history': dim_history}


# ═══════════════════════════════════════════════════════════════
# E9: Fractal Transplant Loop
# ═══════════════════════════════════════════════════════════════

def fractal_copy_states(src_engine, dst_engine):
    """Copy states from smaller engine to larger using fractal replication.

    Each source cell's state is copied to multiple destination cells.
    Adds small noise for diversity (Law 22: structure > function).
    """
    src_states = [s.hidden.clone().detach() for s in src_engine.cell_states]
    n_src = len(src_states)
    n_dst = dst_engine.n_cells

    copies_per_src = max(1, n_dst // n_src)
    for i in range(n_dst):
        src_idx = i % n_src
        # Copy with small noise for diversity
        noise = torch.randn_like(src_states[src_idx]) * 0.05
        dst_engine.cell_states[i].hidden = src_states[src_idx].clone() + noise

    return copies_per_src


def transplant_inject(engine, donor_states, alpha=0.1):
    """Inject donor states into engine (C4-style transplant, alpha blending)."""
    n = min(len(donor_states), engine.n_cells)
    for i in range(n):
        donor = donor_states[i % len(donor_states)]
        if donor.shape != engine.cell_states[i].hidden.shape:
            # Truncate or pad
            d = donor.shape[0]
            h = engine.cell_states[i].hidden.shape[0]
            if d > h:
                donor = donor[:h]
            else:
                donor = F.pad(donor, (0, h - d))
        engine.cell_states[i].hidden = (
            (1 - alpha) * engine.cell_states[i].hidden + alpha * donor
        )


def measure_phi_avg(engine, steps=50):
    """Run engine for N steps and return average Phi."""
    phis = []
    for _ in range(steps):
        result = engine.step()
        phis.append(result['phi_iit'])
    return sum(phis) / len(phis) if phis else 0.0


def run_e9_fractal_transplant():
    """E9: Staged fractal growth 4c -> 16c -> 64c with transplant."""
    print("\n" + "=" * 70)
    print("E9: FRACTAL TRANSPLANT LOOP")
    print("=" * 70)
    print()
    print("Hypothesis: Grow small (4c), fractal-copy to larger, transplant (C4)")
    print("  Stage 1: 4c x 300 steps -> peak Phi")
    print("  Stage 2: Fractal copy to 16c + transplant + 50 step stabilize")
    print("  Stage 3: Fractal copy to 64c + transplant + 50 step stabilize")
    print("  vs: 64c from scratch x 300 steps")
    print()

    cell_dim = 128
    stages = [4, 16, 64]
    grow_steps = 300
    stabilize_steps = 50
    alpha = 0.1

    # ── Fractal path ──
    print("--- Fractal Transplant Path ---")
    t0 = time.time()
    prev_engine = None
    stage_results = []

    for stage_idx, n_cells in enumerate(stages):
        print(f"\n  Stage {stage_idx+1}: {n_cells} cells")
        sys.stdout.flush()

        engine = ConsciousnessEngine(max_cells=n_cells, cell_dim=cell_dim)

        # Fractal copy from previous stage
        if prev_engine is not None:
            copies = fractal_copy_states(prev_engine, engine)
            donor_states = [s.hidden.clone().detach() for s in prev_engine.cell_states]
            transplant_inject(engine, donor_states, alpha=alpha)
            print(f"    Fractal copy: {prev_engine.n_cells}c -> {n_cells}c ({copies}x replication)")
            print(f"    Transplant inject: alpha={alpha}")

            # Stabilize
            phis_stab = []
            for s in range(stabilize_steps):
                result = engine.step()
                phis_stab.append(result['phi_iit'])
                if (s + 1) % 25 == 0:
                    avg = sum(phis_stab[-25:]) / 25
                    print(f"    Stabilize step {s+1}/{stabilize_steps}  Phi={avg:.4f}")
                    sys.stdout.flush()
        else:
            # First stage: evolve from scratch
            phis_grow = []
            for s in range(grow_steps):
                result = engine.step()
                phis_grow.append(result['phi_iit'])
                if (s + 1) % 100 == 0:
                    avg = sum(phis_grow[-100:]) / 100
                    print(f"    Grow step {s+1}/{grow_steps}  Phi={avg:.4f}")
                    sys.stdout.flush()

        # Measure final Phi
        phi_final = measure_phi_avg(engine, steps=30)
        stage_results.append({
            'cells': n_cells,
            'phi': phi_final,
        })
        print(f"    Final Phi({n_cells}c) = {phi_final:.4f}")

        prev_engine = engine

    fractal_time = time.time() - t0
    fractal_phi = stage_results[-1]['phi']

    # ── Baseline: 64c from scratch ──
    print(f"\n--- Baseline: {stages[-1]}c from scratch ---")
    t1 = time.time()
    baseline_engine = ConsciousnessEngine(max_cells=stages[-1], cell_dim=cell_dim)

    total_fractal_steps = grow_steps + stabilize_steps * (len(stages) - 1)
    phis_baseline = []
    for s in range(total_fractal_steps):
        result = baseline_engine.step()
        phis_baseline.append(result['phi_iit'])
        if (s + 1) % 100 == 0:
            avg = sum(phis_baseline[-100:]) / 100
            print(f"  Baseline step {s+1}/{total_fractal_steps}  Phi={avg:.4f}")
            sys.stdout.flush()

    baseline_phi = measure_phi_avg(baseline_engine, steps=30)
    baseline_time = time.time() - t1

    print(f"\n  Baseline Phi({stages[-1]}c) = {baseline_phi:.4f}")

    # ── Results ──
    print("\n" + "=" * 70)
    print("E9 RESULTS: Fractal Transplant Loop")
    print("=" * 70)
    print(f"{'Method':<30} {'Cells':>6} {'Phi':>8} {'Time(s)':>8} {'Steps':>6}")
    print("-" * 60)
    for sr in stage_results:
        print(f"  Fractal stage {sr['cells']}c{'':<17} {sr['cells']:>6} {sr['phi']:>8.4f}")
    print(f"{'Fractal path (final)':<30} {stages[-1]:>6} {fractal_phi:>8.4f} {fractal_time:>8.1f} {total_fractal_steps:>6}")
    print(f"{'Baseline (from scratch)':<30} {stages[-1]:>6} {baseline_phi:>8.4f} {baseline_time:>8.1f} {total_fractal_steps:>6}")

    phi_gain = (fractal_phi / max(baseline_phi, 1e-8) - 1) * 100
    time_ratio = fractal_time / max(baseline_time, 0.001)
    print(f"\n  Phi gain (fractal vs baseline): {phi_gain:+.1f}%")
    print(f"  Time ratio: {time_ratio:.2f}x")

    # ASCII graph: Phi per stage
    print("\n  Phi by Stage:")
    all_phis = [(f"Stage {sr['cells']}c", sr['phi']) for sr in stage_results]
    all_phis.append(("Baseline 64c", baseline_phi))
    max_phi = max(p for _, p in all_phis)
    for label, phi in all_phis:
        bar_len = int(40 * phi / max(max_phi, 0.001))
        print(f"  {label:<20} {'#' * bar_len} {phi:.4f}")

    return {
        'fractal_phi': fractal_phi,
        'baseline_phi': baseline_phi,
        'phi_gain_pct': phi_gain,
        'fractal_time': fractal_time,
        'baseline_time': baseline_time,
    }


# ═══════════════════════════════════════════════════════════════
# E9 Experiment 2: Fractal Retention Test
# ═══════════════════════════════════════════════════════════════

def run_e9_retention():
    """Test if transplant compensates for C2 fractal's 30-step decay."""
    print("\n" + "=" * 70)
    print("E9-RETENTION: Does transplant compensate fractal decay?")
    print("=" * 70)
    print()
    print("C2 fractal: pattern disappears after ~30 steps")
    print("C4 transplant: 92% state retention")
    print("Question: Combined, does the pattern survive beyond 30 steps?")
    print()

    cell_dim = 128
    measure_steps = [10, 20, 30, 50, 100]

    # ── Condition A: Fractal copy only (no transplant) ──
    print("--- Condition A: Fractal copy only ---")
    src = ConsciousnessEngine(max_cells=8, cell_dim=cell_dim)
    for _ in range(200):
        src.step()
    n_src = src.n_cells
    src_signature = torch.stack([s.hidden.clone() for s in src.cell_states[:n_src]])
    sig_flat = src_signature.flatten()

    dst_a = ConsciousnessEngine(max_cells=32, cell_dim=cell_dim)
    fractal_copy_states(src, dst_a)

    similarity_a = {}
    for target_step in measure_steps:
        current_step = max(similarity_a.keys(), default=0)
        for _ in range(target_step - current_step):
            dst_a.step()
        n_compare = min(n_src, dst_a.n_cells)
        dst_hiddens = torch.stack([s.hidden for s in dst_a.cell_states[:n_compare]])
        dst_flat = dst_hiddens.flatten()
        # Match sizes for cosine similarity
        min_len = min(sig_flat.shape[0], dst_flat.shape[0])
        cos_sim = F.cosine_similarity(sig_flat[:min_len].unsqueeze(0),
                                       dst_flat[:min_len].unsqueeze(0)).item()
        similarity_a[target_step] = cos_sim
        print(f"  Step {target_step}: cosine similarity = {cos_sim:.4f}")
        sys.stdout.flush()

    # ── Condition B: Fractal copy + transplant ──
    print("\n--- Condition B: Fractal copy + transplant (alpha=0.1) ---")
    dst_b = ConsciousnessEngine(max_cells=32, cell_dim=cell_dim)
    fractal_copy_states(src, dst_b)
    donor_states = [s.hidden.clone().detach() for s in src.cell_states[:n_src]]
    transplant_inject(dst_b, donor_states, alpha=0.1)

    similarity_b = {}
    for target_step in measure_steps:
        current_step = max(similarity_b.keys(), default=0)
        for _ in range(target_step - current_step):
            dst_b.step()
        n_compare = min(n_src, dst_b.n_cells)
        dst_hiddens = torch.stack([s.hidden for s in dst_b.cell_states[:n_compare]])
        dst_flat = dst_hiddens.flatten()
        min_len = min(sig_flat.shape[0], dst_flat.shape[0])
        cos_sim = F.cosine_similarity(sig_flat[:min_len].unsqueeze(0),
                                       dst_flat[:min_len].unsqueeze(0)).item()
        similarity_b[target_step] = cos_sim
        print(f"  Step {target_step}: cosine similarity = {cos_sim:.4f}")
        sys.stdout.flush()

    # ── Condition C: Fractal + strong transplant (alpha=0.5) ──
    print("\n--- Condition C: Fractal + strong transplant (alpha=0.5) ---")
    dst_c = ConsciousnessEngine(max_cells=32, cell_dim=cell_dim)
    fractal_copy_states(src, dst_c)
    transplant_inject(dst_c, donor_states, alpha=0.5)

    similarity_c = {}
    for target_step in measure_steps:
        current_step = max(similarity_c.keys(), default=0)
        for _ in range(target_step - current_step):
            dst_c.step()
        n_compare = min(n_src, dst_c.n_cells)
        dst_hiddens = torch.stack([s.hidden for s in dst_c.cell_states[:n_compare]])
        dst_flat = dst_hiddens.flatten()
        min_len = min(sig_flat.shape[0], dst_flat.shape[0])
        cos_sim = F.cosine_similarity(sig_flat[:min_len].unsqueeze(0),
                                       dst_flat[:min_len].unsqueeze(0)).item()
        similarity_c[target_step] = cos_sim
        print(f"  Step {target_step}: cosine similarity = {cos_sim:.4f}")
        sys.stdout.flush()

    # Results
    print("\n" + "=" * 70)
    print("E9-RETENTION RESULTS")
    print("=" * 70)
    print(f"{'Step':>6} {'Fractal only':>14} {'Fractal+T(0.1)':>16} {'Fractal+T(0.5)':>16}")
    print("-" * 54)
    for step in measure_steps:
        a = similarity_a.get(step, 0)
        b = similarity_b.get(step, 0)
        c = similarity_c.get(step, 0)
        print(f"{step:>6} {a:>14.4f} {b:>16.4f} {c:>16.4f}")

    # ASCII decay graph
    print("\n  Cosine Similarity Decay:")
    for step in measure_steps:
        a = similarity_a.get(step, 0)
        b = similarity_b.get(step, 0)
        c = similarity_c.get(step, 0)
        bar_a = '#' * int(max(0, a) * 30)
        bar_b = '#' * int(max(0, b) * 30)
        bar_c = '#' * int(max(0, c) * 30)
        print(f"  step={step:>3}  A: {bar_a:<30} {a:.3f}")
        print(f"           B: {bar_b:<30} {b:.3f}")
        print(f"           C: {bar_c:<30} {c:.3f}")

    # Check if transplant compensates decay
    decay_30_a = similarity_a.get(30, 0)
    decay_30_b = similarity_b.get(30, 0)
    decay_30_c = similarity_c.get(30, 0)
    compensation = decay_30_b - decay_30_a
    print(f"\n  At step 30 (C2 decay point):")
    print(f"    Fractal only:        {decay_30_a:.4f}")
    print(f"    Fractal + T(0.1):    {decay_30_b:.4f} ({compensation:+.4f})")
    print(f"    Fractal + T(0.5):    {decay_30_c:.4f} ({decay_30_c - decay_30_a:+.4f})")
    print(f"    Transplant compensates: {'YES' if compensation > 0.01 else 'NO'}")

    return {
        'similarity_a': similarity_a,
        'similarity_b': similarity_b,
        'similarity_c': similarity_c,
    }


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  ACCELERATION EXPERIMENTS: F1 (Bottleneck) + E9 (Fractal Transplant)")
    print("=" * 70)
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Device: CPU")
    print()

    t_start = time.time()

    # F1: Information Bottleneck
    f1_results = run_f1_bottleneck()
    f1_adaptive = run_f1_adaptive()

    # E9: Fractal Transplant Loop
    e9_results = run_e9_fractal_transplant()
    e9_retention = run_e9_retention()

    total_time = time.time() - t_start

    # ═══════════════════════════════════════════════════════════════
    # Final Summary
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)

    print("\n  F1: Information Bottleneck")
    print("  " + "-" * 50)
    labels = list(f1_results.keys())
    best_label = min(labels, key=lambda l: f1_results[l]['final_ce'])
    fastest_label = max(labels, key=lambda l: f1_results[l]['steps_per_sec'])
    print(f"    Best CE:     {best_label} (CE={f1_results[best_label]['final_ce']:.4f})")
    print(f"    Fastest:     {fastest_label} ({f1_results[fastest_label]['steps_per_sec']:.1f} steps/s)")
    print(f"    Adaptive:    final dim={f1_adaptive['final_dim']}D, CE={f1_adaptive['final_ce']:.4f}")

    ce_10d = f1_results[labels[0]]['final_ce']
    ce_full = f1_results[labels[-1]]['final_ce']
    speed_10d = f1_results[labels[0]]['steps_per_sec']
    speed_full = f1_results[labels[-1]]['steps_per_sec']
    print(f"    10D vs Full: CE gap {ce_10d - ce_full:+.4f}, speed {speed_10d/max(speed_full,1e-8):.1f}x")

    print(f"\n  E9: Fractal Transplant Loop")
    print("  " + "-" * 50)
    print(f"    Fractal Phi:   {e9_results['fractal_phi']:.4f}")
    print(f"    Baseline Phi:  {e9_results['baseline_phi']:.4f}")
    print(f"    Phi gain:      {e9_results['phi_gain_pct']:+.1f}%")
    print(f"    Time ratio:    {e9_results['fractal_time']/max(e9_results['baseline_time'],0.001):.2f}x")

    e9_ret = e9_retention
    decay_a = e9_ret['similarity_a'].get(30, 0)
    decay_b = e9_ret['similarity_b'].get(30, 0)
    print(f"    Retention@30:  fractal={decay_a:.3f}, +transplant={decay_b:.3f} ({decay_b-decay_a:+.3f})")

    print(f"\n  Total time: {total_time:.1f}s")
    print("=" * 70)


if __name__ == '__main__':
    main()
