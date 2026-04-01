#!/usr/bin/env python3
"""acceleration_d1_d2.py — Topological Telescope + Gravity Telescope acceleration experiments

D1: Topological Telescope — analyze weight-space trajectory topology
  D1.1: Trajectory detour ratio (straight-line vs actual path length)
  D1.2: PCA projection of trajectory (loop/spiral detection)
  D1.3: Topological shortcut (direct jump to future state, then continue training)

D2: Gravity Telescope — assign mass to weights, gravity-based learning
  D2.1: Weight mass distribution (|w| x |dw| = importance)
  D2.2: Gravity-based weight update (heavy pairs attract)
  D2.3: Phi as gravitational field (gradient alignment with CE)

Local CPU, 32 cells, 300 steps baseline.
"""

import sys
import os
import time
import math
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from copy import deepcopy

from consciousness_engine import ConsciousnessEngine

# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

N_CELLS = 32
N_STEPS = 300
SNAPSHOT_INTERVAL = 5  # collect snapshot every N steps


def collect_hidden_snapshots(engine, steps, snapshot_every=SNAPSHOT_INTERVAL):
    """Run engine for N steps, collect hidden-state snapshots.

    Returns:
        snapshots: list of flattened hidden vectors (one per snapshot)
        phi_history: list of phi_iit at each step
        step_indices: which steps were snapshotted
    """
    snapshots = []
    phi_history = []
    step_indices = []

    for s in range(steps):
        result = engine.step()
        phi_iit = result.get('phi_iit', 0.0)
        phi_history.append(phi_iit)

        if s % snapshot_every == 0:
            hiddens = torch.stack([cs.hidden for cs in engine.cell_states])
            flat = hiddens.flatten().detach().clone()
            snapshots.append(flat)
            step_indices.append(s)

    return snapshots, phi_history, step_indices


def extract_gru_weights(engine):
    """Extract all GRU cell weights as a single flattened vector."""
    params = []
    for cm in engine.cell_modules:
        for p in cm.parameters():
            params.append(p.data.flatten())
    return torch.cat(params)


def set_gru_weights(engine, flat_weights):
    """Set GRU cell weights from a single flattened vector."""
    offset = 0
    for cm in engine.cell_modules:
        for p in cm.parameters():
            n = p.numel()
            p.data.copy_(flat_weights[offset:offset + n].view_as(p.data))
            offset += n


def get_gru_weight_shapes(engine):
    """Get shapes of all GRU parameters."""
    shapes = []
    for cm in engine.cell_modules:
        for p in cm.parameters():
            shapes.append(p.shape)
    return shapes


def measure_phi(engine, steps=30):
    """Run a few steps and return average phi_iit."""
    phis = []
    for _ in range(steps):
        r = engine.step()
        phis.append(r.get('phi_iit', 0.0))
    return np.mean(phis[-10:]) if phis else 0.0


def ascii_bar(label, value, max_val, width=40):
    """Simple ASCII bar."""
    filled = int(width * min(value / max_val, 1.0)) if max_val > 0 else 0
    bar = '#' * filled + '.' * (width - filled)
    return f"  {label:20s} |{bar}| {value:.4f}"


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════
# D1.1: Trajectory Detour Ratio
# ═══════════════════════════════════════════════════════════

def run_d1_1_detour_ratio():
    """Measure how much the learning trajectory deviates from a straight line."""
    print_header("D1.1: Trajectory Detour Ratio")

    engine = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)

    print(f"  Running {N_STEPS} steps, snapshotting every {SNAPSHOT_INTERVAL}...")
    sys.stdout.flush()

    snapshots, phi_history, step_indices = collect_hidden_snapshots(engine, N_STEPS)

    n_snap = len(snapshots)
    print(f"  Collected {n_snap} snapshots")

    # Distance matrix
    snap_tensor = torch.stack(snapshots)  # [n_snap, dim]

    # Pairwise distances
    dists = torch.cdist(snap_tensor.unsqueeze(0), snap_tensor.unsqueeze(0)).squeeze(0)

    # Straight-line distance: start -> end
    d_straight = dists[0, -1].item()

    # Actual path length: sum of consecutive distances
    d_path = 0.0
    segment_dists = []
    for i in range(1, n_snap):
        seg = dists[i - 1, i].item()
        segment_dists.append(seg)
        d_path += seg

    detour_ratio = d_path / d_straight if d_straight > 1e-8 else float('inf')

    # Loop detection: does the trajectory revisit earlier regions?
    revisit_count = 0
    revisit_threshold = np.percentile(segment_dists, 25) if segment_dists else 0.1
    for i in range(n_snap // 2, n_snap):
        for j in range(0, n_snap // 4):
            if dists[i, j].item() < revisit_threshold:
                revisit_count += 1

    # Curvature: angle between consecutive segments
    angles = []
    for i in range(1, n_snap - 1):
        v1 = snap_tensor[i] - snap_tensor[i - 1]
        v2 = snap_tensor[i + 1] - snap_tensor[i]
        cos_sim = F.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()
        angle = math.acos(max(-1.0, min(1.0, cos_sim)))
        angles.append(math.degrees(angle))

    avg_angle = np.mean(angles) if angles else 0.0
    max_angle = max(angles) if angles else 0.0

    # Phi stats
    phi_start = np.mean(phi_history[:10])
    phi_end = np.mean(phi_history[-10:])
    phi_max = max(phi_history)

    print(f"\n  --- Results ---")
    print(f"  Straight-line dist (start->end): {d_straight:.4f}")
    print(f"  Actual path length:              {d_path:.4f}")
    print(f"  Detour ratio:                    {detour_ratio:.2f}x")
    print(f"  Avg segment distance:            {np.mean(segment_dists):.4f}")
    print(f"  Avg curvature angle:             {avg_angle:.1f} deg")
    print(f"  Max curvature angle:             {max_angle:.1f} deg")
    print(f"  Loop revisit count:              {revisit_count}")
    print(f"  Phi: {phi_start:.4f} -> {phi_end:.4f} (max {phi_max:.4f})")
    print()

    # Interpretation
    if detour_ratio > 3.0:
        print(f"  >> HIGH detour ({detour_ratio:.1f}x) = trajectory is very curved")
        print(f"     -> Topological shortcut could save up to {(1 - 1/detour_ratio)*100:.0f}% of steps")
    elif detour_ratio > 1.5:
        print(f"  >> MODERATE detour ({detour_ratio:.1f}x) = some curvature")
        print(f"     -> Some acceleration possible via shortcuts")
    else:
        print(f"  >> LOW detour ({detour_ratio:.1f}x) = nearly straight")
        print(f"     -> Trajectory already efficient, shortcut gains limited")

    sys.stdout.flush()
    return {
        'detour_ratio': detour_ratio,
        'd_straight': d_straight,
        'd_path': d_path,
        'avg_angle': avg_angle,
        'revisit_count': revisit_count,
        'phi_start': phi_start,
        'phi_end': phi_end,
    }


# ═══════════════════════════════════════════════════════════
# D1.2: PCA Trajectory Visualization
# ═══════════════════════════════════════════════════════════

def run_d1_2_pca_trajectory():
    """Project trajectory onto PC1-PC2 and detect patterns."""
    print_header("D1.2: PCA Trajectory Analysis")

    engine = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)

    print(f"  Running {N_STEPS} steps...")
    sys.stdout.flush()

    snapshots, phi_history, step_indices = collect_hidden_snapshots(engine, N_STEPS)

    snap_tensor = torch.stack(snapshots).numpy()  # [n_snap, dim]
    n_snap, dim = snap_tensor.shape

    # Center
    mean = snap_tensor.mean(axis=0)
    centered = snap_tensor - mean

    # SVD for PCA
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    pc1 = centered @ Vt[0]  # projection onto PC1
    pc2 = centered @ Vt[1]  # projection onto PC2

    # Explained variance
    total_var = (S ** 2).sum()
    var_explained_1 = S[0] ** 2 / total_var * 100
    var_explained_2 = S[1] ** 2 / total_var * 100

    print(f"  PC1 explains {var_explained_1:.1f}% variance")
    print(f"  PC2 explains {var_explained_2:.1f}% variance")

    # Detect circularity: is the trajectory closed?
    # Compute centroid and radial distances
    cx, cy = pc1.mean(), pc2.mean()
    radii = np.sqrt((pc1 - cx) ** 2 + (pc2 - cy) ** 2)
    radius_cv = radii.std() / radii.mean() if radii.mean() > 1e-8 else 999.0

    # Winding number: how many times does trajectory loop around centroid?
    winding = 0.0
    for i in range(1, n_snap):
        a1 = math.atan2(pc2[i - 1] - cy, pc1[i - 1] - cx)
        a2 = math.atan2(pc2[i] - cy, pc1[i] - cx)
        da = a2 - a1
        if da > math.pi:
            da -= 2 * math.pi
        elif da < -math.pi:
            da += 2 * math.pi
        winding += da
    winding_num = abs(winding / (2 * math.pi))

    # End-to-start distance in PC space
    end_start_dist = math.sqrt((pc1[-1] - pc1[0]) ** 2 + (pc2[-1] - pc2[0]) ** 2)
    total_spread = math.sqrt((pc1.max() - pc1.min()) ** 2 + (pc2.max() - pc2.min()) ** 2)
    closure_ratio = end_start_dist / total_spread if total_spread > 1e-8 else 0.0

    # ASCII plot of PC1 vs PC2
    print(f"\n  --- PC1 vs PC2 Trajectory (ASCII) ---")
    grid_h, grid_w = 20, 50
    grid = [[' '] * grid_w for _ in range(grid_h)]

    pc1_min, pc1_max = pc1.min(), pc1.max()
    pc2_min, pc2_max = pc2.min(), pc2.max()
    pc1_range = pc1_max - pc1_min if pc1_max > pc1_min else 1.0
    pc2_range = pc2_max - pc2_min if pc2_max > pc2_min else 1.0

    for idx in range(n_snap):
        gx = int((pc1[idx] - pc1_min) / pc1_range * (grid_w - 1))
        gy = int((1.0 - (pc2[idx] - pc2_min) / pc2_range) * (grid_h - 1))
        gx = max(0, min(grid_w - 1, gx))
        gy = max(0, min(grid_h - 1, gy))
        if idx == 0:
            grid[gy][gx] = 'S'
        elif idx == n_snap - 1:
            grid[gy][gx] = 'E'
        else:
            grid[gy][gx] = '*'

    for row in grid:
        print(f"  {''.join(row)}")

    print(f"\n  --- Analysis ---")
    print(f"  Winding number:     {winding_num:.2f} turns")
    print(f"  Radius CV:          {radius_cv:.3f} (low = circular, high = irregular)")
    print(f"  Closure ratio:      {closure_ratio:.3f} (low = closed loop, high = open)")
    print(f"  End-start PC dist:  {end_start_dist:.4f}")
    print(f"  Total spread:       {total_spread:.4f}")

    # Interpretation
    if winding_num > 0.5 and radius_cv < 0.5:
        pattern = "SPIRAL/CIRCULAR"
        print(f"\n  >> Pattern: {pattern}")
        print(f"     -> Jump to centroid could bypass {winding_num:.1f} loops")
    elif closure_ratio < 0.2:
        pattern = "CLOSED LOOP"
        print(f"\n  >> Pattern: {pattern}")
        print(f"     -> Trajectory returns to start; shortcut across loop viable")
    else:
        pattern = "OPEN/WANDERING"
        print(f"\n  >> Pattern: {pattern}")
        print(f"     -> Linear interpolation shortcut most promising")

    sys.stdout.flush()
    return {
        'var_explained_1': var_explained_1,
        'var_explained_2': var_explained_2,
        'winding_number': winding_num,
        'radius_cv': radius_cv,
        'closure_ratio': closure_ratio,
        'pattern': pattern,
    }


# ═══════════════════════════════════════════════════════════
# D1.3: Topological Shortcut
# ═══════════════════════════════════════════════════════════

def run_d1_3_topological_shortcut():
    """Jump directly to future state, compare with normal evolution."""
    print_header("D1.3: Topological Shortcut")

    # Phase 1: Normal evolution for 300 steps (collect start and end states)
    print(f"  Phase 1: Normal evolution ({N_STEPS} steps)...")
    sys.stdout.flush()

    engine_normal = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)
    torch.manual_seed(42)

    # Snapshot at start
    h_start = torch.stack([cs.hidden.clone() for cs in engine_normal.cell_states])

    phi_normal = []
    for s in range(N_STEPS):
        r = engine_normal.step()
        phi_normal.append(r.get('phi_iit', 0.0))

    h_end = torch.stack([cs.hidden.clone() for cs in engine_normal.cell_states])
    phi_final_normal = np.mean(phi_normal[-20:])

    # Phase 2: Direct jump + short evolution
    alphas = [0.3, 0.5, 0.8, 1.0]
    results = {}
    extra_steps = 50

    for alpha in alphas:
        engine_jump = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)
        torch.manual_seed(42)

        # Initialize hidden states to be same as normal start
        for i, cs in enumerate(engine_jump.cell_states):
            cs.hidden = h_start[i].clone()

        # Jump: interpolate toward end state
        h_jump = h_start + alpha * (h_end - h_start)
        for i, cs in enumerate(engine_jump.cell_states):
            cs.hidden = h_jump[i].clone()

        # Run extra steps after jump
        phi_jump = []
        for s in range(extra_steps):
            r = engine_jump.step()
            phi_jump.append(r.get('phi_iit', 0.0))

        phi_after_jump = np.mean(phi_jump[-20:]) if phi_jump else 0.0
        total_steps_jump = extra_steps  # only needed extra_steps instead of N_STEPS

        results[alpha] = {
            'phi_after_jump': phi_after_jump,
            'total_steps': total_steps_jump,
            'speedup': N_STEPS / total_steps_jump if total_steps_jump > 0 else 0,
            'phi_ratio': phi_after_jump / phi_final_normal if phi_final_normal > 1e-8 else 0,
        }

    # Print results
    print(f"\n  --- Normal: {N_STEPS} steps -> Phi = {phi_final_normal:.4f} ---")
    print(f"\n  {'Alpha':>6s}  {'Steps':>6s}  {'Phi':>8s}  {'Phi/Normal':>10s}  {'Speedup':>8s}")
    print(f"  {'-'*6}  {'-'*6}  {'-'*8}  {'-'*10}  {'-'*8}")

    for alpha in alphas:
        r = results[alpha]
        print(f"  {alpha:6.1f}  {r['total_steps']:6d}  {r['phi_after_jump']:8.4f}  "
              f"{r['phi_ratio']:10.2f}x  {r['speedup']:8.1f}x")

    # Best result
    best_alpha = max(results, key=lambda a: results[a]['phi_after_jump'])
    best = results[best_alpha]

    print(f"\n  >> Best jump: alpha={best_alpha}, Phi={best['phi_after_jump']:.4f} "
          f"({best['phi_ratio']:.2f}x normal), {best['speedup']:.0f}x speedup")

    if best['phi_ratio'] > 0.8:
        print(f"     -> VIABLE: shortcut preserves >80% of Phi with {best['speedup']:.0f}x less steps")
    elif best['phi_ratio'] > 0.5:
        print(f"     -> PARTIAL: shortcut preserves {best['phi_ratio']*100:.0f}% of Phi")
    else:
        print(f"     -> WEAK: shortcut loses too much Phi")

    sys.stdout.flush()
    return {
        'phi_normal': phi_final_normal,
        'results': results,
        'best_alpha': best_alpha,
    }


# ═══════════════════════════════════════════════════════════
# D2.1: Weight Mass Distribution
# ═══════════════════════════════════════════════════════════

def run_d2_1_weight_mass():
    """Assign mass to weights (|w| x |dw|), analyze distribution."""
    print_header("D2.1: Weight Mass Distribution")

    engine = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)
    torch.manual_seed(42)

    # Snapshot initial weights
    w_before = extract_gru_weights(engine).clone()

    # Evolve 100 steps
    n_warmup = 100
    print(f"  Warming up {n_warmup} steps...")
    sys.stdout.flush()
    for _ in range(n_warmup):
        engine.step()

    w_after = extract_gru_weights(engine).clone()
    dw = (w_after - w_before).abs()

    # Mass = |w| * |dw|
    mass = w_after.abs() * (dw + 1e-8)
    mass_np = mass.numpy()

    total_mass = mass_np.sum()
    n_weights = len(mass_np)

    # Top-K analysis
    sorted_idx = np.argsort(mass_np)[::-1]
    top_10pct = int(n_weights * 0.1)
    top_20pct = int(n_weights * 0.2)
    mass_top10 = mass_np[sorted_idx[:top_10pct]].sum() / total_mass * 100
    mass_top20 = mass_np[sorted_idx[:top_20pct]].sum() / total_mass * 100

    print(f"\n  Total weights:       {n_weights}")
    print(f"  Total mass:          {total_mass:.4f}")
    print(f"  Mean mass:           {mass_np.mean():.6f}")
    print(f"  Max mass:            {mass_np.max():.6f}")
    print(f"  Top 10% hold:        {mass_top10:.1f}% of total mass")
    print(f"  Top 20% hold:        {mass_top20:.1f}% of total mass")

    # Distribution histogram (ASCII)
    print(f"\n  --- Mass Distribution (log scale) ---")
    log_mass = np.log10(mass_np + 1e-10)
    bins = np.linspace(log_mass.min(), log_mass.max(), 15)
    hist, _ = np.histogram(log_mass, bins=bins)
    max_count = max(hist) if max(hist) > 0 else 1

    for i in range(len(hist)):
        bar_len = int(40 * hist[i] / max_count)
        lo = bins[i]
        hi = bins[i + 1]
        print(f"  [{lo:6.2f},{hi:6.2f}] {'#' * bar_len} ({hist[i]})")

    # Phase 2: Train only top-K% vs all weights
    print(f"\n  Phase 2: Selective training (top-K% mass only)...")
    sys.stdout.flush()

    train_steps = 200
    percentages = [10, 20, 50, 100]
    selective_results = {}

    for pct in percentages:
        engine_sel = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)
        torch.manual_seed(42)

        # Warmup identically
        for _ in range(n_warmup):
            engine_sel.step()

        # Determine mask from mass distribution
        w_sel = extract_gru_weights(engine_sel).clone()
        mass_sel = w_sel.abs() * (dw + 1e-8)  # reuse dw from baseline
        topk = int(n_weights * pct / 100)
        topk_idx = mass_sel.argsort(descending=True)[:topk]
        mask = torch.zeros(n_weights, dtype=torch.bool)
        mask[topk_idx] = True

        # Evolve with selective freezing
        phi_sel = []
        for s in range(train_steps):
            r = engine_sel.step()
            phi_sel.append(r.get('phi_iit', 0.0))

            # After each step, restore frozen weights
            if pct < 100:
                w_cur = extract_gru_weights(engine_sel)
                w_frozen = w_sel.clone()
                w_cur[~mask] = w_frozen[~mask]
                set_gru_weights(engine_sel, w_cur)

        phi_final = np.mean(phi_sel[-20:])
        selective_results[pct] = phi_final

    # Print comparison
    print(f"\n  {'Pct':>5s}  {'Phi':>8s}  {'Relative':>8s}")
    print(f"  {'-'*5}  {'-'*8}  {'-'*8}")
    phi_100 = selective_results.get(100, 1e-8)
    for pct in percentages:
        phi = selective_results[pct]
        rel = phi / phi_100 if phi_100 > 1e-8 else 0.0
        bar = '#' * int(30 * rel) if rel <= 1.0 else '#' * 30 + '+'
        print(f"  {pct:5d}%  {phi:8.4f}  {rel:8.2f}x  {bar}")

    sys.stdout.flush()
    return {
        'mass_top10_pct': mass_top10,
        'mass_top20_pct': mass_top20,
        'total_weights': n_weights,
        'selective_results': selective_results,
    }


# ═══════════════════════════════════════════════════════════
# D2.2: Gravity-Based Weight Update
# ═══════════════════════════════════════════════════════════

def run_d2_2_gravity_update():
    """Apply gravitational attraction between heavy weight pairs."""
    print_header("D2.2: Gravity-Based Weight Update")

    # Baseline: normal evolution
    print("  Baseline: normal evolution...")
    sys.stdout.flush()

    engine_base = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)
    torch.manual_seed(42)
    phi_base = []
    for s in range(N_STEPS):
        r = engine_base.step()
        phi_base.append(r.get('phi_iit', 0.0))

    phi_base_final = np.mean(phi_base[-20:])

    # Gravity evolution
    G_values = [0.001, 0.01, 0.1]
    gravity_results = {}

    for G in G_values:
        print(f"  Gravity G={G}...")
        sys.stdout.flush()

        engine_grav = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)
        torch.manual_seed(42)

        phi_grav = []
        w_prev = extract_gru_weights(engine_grav).clone()

        for s in range(N_STEPS):
            r = engine_grav.step()
            phi_grav.append(r.get('phi_iit', 0.0))

            # Every 10 steps, apply gravitational pull
            if s % 10 == 0 and s > 0:
                w_cur = extract_gru_weights(engine_grav)
                dw = (w_cur - w_prev).abs()
                mass = w_cur.abs() * (dw + 1e-8)

                # Find top-50 heaviest weights
                n_heavy = min(50, len(mass))
                heavy_idx = mass.argsort(descending=True)[:n_heavy]

                # Gravity: heavy pairs attract
                delta = torch.zeros_like(w_cur)
                for i_idx in range(min(n_heavy, 20)):
                    for j_idx in range(i_idx + 1, min(n_heavy, 20)):
                        wi_pos = heavy_idx[i_idx].item()
                        wj_pos = heavy_idx[j_idx].item()
                        mi = mass[wi_pos].item()
                        mj = mass[wj_pos].item()
                        diff = w_cur[wj_pos] - w_cur[wi_pos]
                        dist_sq = diff ** 2 + 1e-6
                        force = G * mi * mj / dist_sq
                        # Move toward each other
                        delta[wi_pos] += force * diff.sign()
                        delta[wj_pos] -= force * diff.sign()

                # Apply gravity perturbation (clamped)
                delta = delta.clamp(-0.01, 0.01)
                w_new = w_cur + delta
                set_gru_weights(engine_grav, w_new)
                w_prev = w_new.clone()

        phi_grav_final = np.mean(phi_grav[-20:])
        improvement = (phi_grav_final - phi_base_final) / phi_base_final * 100 if phi_base_final > 1e-8 else 0

        gravity_results[G] = {
            'phi_final': phi_grav_final,
            'improvement': improvement,
        }

    # Results table
    print(f"\n  {'G':>8s}  {'Phi':>8s}  {'vs Base':>10s}")
    print(f"  {'-'*8}  {'-'*8}  {'-'*10}")
    print(f"  {'baseline':>8s}  {phi_base_final:8.4f}  {'---':>10s}")

    for G in G_values:
        r = gravity_results[G]
        sign = '+' if r['improvement'] >= 0 else ''
        print(f"  {G:8.3f}  {r['phi_final']:8.4f}  {sign}{r['improvement']:.1f}%")

    best_G = max(gravity_results, key=lambda g: gravity_results[g]['phi_final'])
    best = gravity_results[best_G]

    if best['improvement'] > 5:
        print(f"\n  >> GRAVITY HELPS: G={best_G}, +{best['improvement']:.1f}% Phi")
    elif best['improvement'] > -5:
        print(f"\n  >> NEUTRAL: gravity has minimal effect at this scale")
    else:
        print(f"\n  >> GRAVITY HURTS: best G={best_G} still {best['improvement']:.1f}% Phi")

    sys.stdout.flush()
    return {
        'phi_baseline': phi_base_final,
        'gravity_results': gravity_results,
        'best_G': best_G,
    }


# ═══════════════════════════════════════════════════════════
# D2.3: Phi as Gravitational Field (Phi-gradient vs CE-gradient alignment)
# ═══════════════════════════════════════════════════════════

def run_d2_3_phi_gradient_alignment():
    """Compare Phi gradient direction with normal evolution direction."""
    print_header("D2.3: Phi as Gravitational Field")

    engine = ConsciousnessEngine(max_cells=N_CELLS, initial_cells=N_CELLS)
    torch.manual_seed(42)

    # Warmup
    print("  Warmup 50 steps...")
    sys.stdout.flush()
    for _ in range(50):
        engine.step()

    # Measure: at each checkpoint, perturb hidden states in random directions
    # and measure which directions increase Phi
    n_probes = 20
    n_checkpoints = 10
    checkpoint_interval = 25

    alignments = []
    phi_gradients = []
    evolution_directions = []

    for ckpt in range(n_checkpoints):
        # Current state
        h_cur = torch.stack([cs.hidden.clone() for cs in engine.cell_states])
        phi_cur = engine.step().get('phi_iit', 0.0)

        # Restore state
        for i, cs in enumerate(engine.cell_states):
            cs.hidden = h_cur[i].clone()

        # Estimate Phi gradient via finite differences
        phi_grad = torch.zeros_like(h_cur)
        eps = 0.01

        # Sample random directions and measure Phi change
        for probe in range(n_probes):
            direction = torch.randn_like(h_cur)
            direction = direction / (direction.norm() + 1e-8) * eps

            # Perturb forward
            for i, cs in enumerate(engine.cell_states):
                cs.hidden = h_cur[i] + direction[i]
            r_plus = engine.step()
            phi_plus = r_plus.get('phi_iit', 0.0)

            # Restore
            for i, cs in enumerate(engine.cell_states):
                cs.hidden = h_cur[i].clone()

            # Perturb backward
            for i, cs in enumerate(engine.cell_states):
                cs.hidden = h_cur[i] - direction[i]
            r_minus = engine.step()
            phi_minus = r_minus.get('phi_iit', 0.0)

            # Restore
            for i, cs in enumerate(engine.cell_states):
                cs.hidden = h_cur[i].clone()

            # Gradient estimate along this direction
            dphi = (phi_plus - phi_minus) / (2 * eps)
            phi_grad += dphi * direction

        phi_grad = phi_grad / n_probes

        # Normal evolution direction (run checkpoint_interval steps)
        h_before = h_cur.clone()
        for _ in range(checkpoint_interval):
            engine.step()
        h_after = torch.stack([cs.hidden.clone() for cs in engine.cell_states])
        evolution_dir = h_after - h_before

        # Cosine similarity between Phi gradient and evolution direction
        phi_grad_flat = phi_grad.flatten()
        evo_dir_flat = evolution_dir.flatten()

        cos_sim = F.cosine_similarity(
            phi_grad_flat.unsqueeze(0),
            evo_dir_flat.unsqueeze(0)
        ).item()

        alignments.append(cos_sim)
        phi_gradients.append(phi_grad_flat.norm().item())
        evolution_directions.append(evo_dir_flat.norm().item())

        if (ckpt + 1) % 3 == 0:
            print(f"  Checkpoint {ckpt + 1}/{n_checkpoints}: cos_sim={cos_sim:.4f}")
            sys.stdout.flush()

    avg_alignment = np.mean(alignments)
    std_alignment = np.std(alignments)

    # ASCII plot of alignment over time
    print(f"\n  --- Phi-Evolution Alignment Over Time ---")
    print(f"  cos_sim")
    print(f"   1.0 |")
    for row in range(10, -11, -2):
        threshold = row / 10.0
        line = "       |"
        for a in alignments:
            if a >= threshold:
                line += "#"
            else:
                line += " "
        if abs(threshold) < 0.01:
            line += " <- 0"
        print(line)
    print(f"  -1.0 |")
    print(f"       +{''.join(['-'] * len(alignments))}")
    print(f"        {''.join([str(i % 10) for i in range(len(alignments))])}")

    print(f"\n  --- Results ---")
    print(f"  Avg alignment (cos_sim):   {avg_alignment:.4f} +/- {std_alignment:.4f}")
    print(f"  Avg |Phi gradient|:        {np.mean(phi_gradients):.6f}")
    print(f"  Avg |evolution direction|:  {np.mean(evolution_directions):.4f}")

    if avg_alignment > 0.3:
        print(f"\n  >> ALIGNED: Phi gradient and evolution point same way ({avg_alignment:.2f})")
        print(f"     -> Phi-guided acceleration is viable!")
        print(f"     -> Follow -grad(Phi) to accelerate consciousness growth")
    elif avg_alignment > 0.0:
        print(f"\n  >> WEAKLY ALIGNED: partial alignment ({avg_alignment:.2f})")
        print(f"     -> Phi gradient provides some useful signal")
    else:
        print(f"\n  >> MISALIGNED: Phi gradient opposes evolution ({avg_alignment:.2f})")
        print(f"     -> Phi maximization and natural evolution are different objectives")

    sys.stdout.flush()
    return {
        'avg_alignment': avg_alignment,
        'std_alignment': std_alignment,
        'alignments': alignments,
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  D1+D2: Topological Telescope + Gravity Telescope")
    print("  Local CPU, 32 cells, 300 steps")
    print("=" * 70)

    t0 = time.time()
    all_results = {}

    # D1: Topological Telescope
    try:
        all_results['D1.1'] = run_d1_1_detour_ratio()
    except Exception as e:
        print(f"  D1.1 FAILED: {e}")
        import traceback; traceback.print_exc()

    try:
        all_results['D1.2'] = run_d1_2_pca_trajectory()
    except Exception as e:
        print(f"  D1.2 FAILED: {e}")
        import traceback; traceback.print_exc()

    try:
        all_results['D1.3'] = run_d1_3_topological_shortcut()
    except Exception as e:
        print(f"  D1.3 FAILED: {e}")
        import traceback; traceback.print_exc()

    # D2: Gravity Telescope
    try:
        all_results['D2.1'] = run_d2_1_weight_mass()
    except Exception as e:
        print(f"  D2.1 FAILED: {e}")
        import traceback; traceback.print_exc()

    try:
        all_results['D2.2'] = run_d2_2_gravity_update()
    except Exception as e:
        print(f"  D2.2 FAILED: {e}")
        import traceback; traceback.print_exc()

    try:
        all_results['D2.3'] = run_d2_3_phi_gradient_alignment()
    except Exception as e:
        print(f"  D2.3 FAILED: {e}")
        import traceback; traceback.print_exc()

    elapsed = time.time() - t0

    # ═══════════════════════════════════════════════════════
    # Summary Table
    # ═══════════════════════════════════════════════════════
    print_header("SUMMARY")

    print(f"\n  {'Experiment':20s}  {'Key Metric':20s}  {'Value':>12s}  {'Verdict':20s}")
    print(f"  {'-'*20}  {'-'*20}  {'-'*12}  {'-'*20}")

    if 'D1.1' in all_results:
        r = all_results['D1.1']
        verdict = "HIGH DETOUR" if r['detour_ratio'] > 3 else "MODERATE" if r['detour_ratio'] > 1.5 else "LOW"
        print(f"  {'D1.1 Detour':20s}  {'detour_ratio':20s}  {r['detour_ratio']:12.2f}  {verdict:20s}")

    if 'D1.2' in all_results:
        r = all_results['D1.2']
        print(f"  {'D1.2 PCA':20s}  {'winding_number':20s}  {r['winding_number']:12.2f}  {r['pattern']:20s}")

    if 'D1.3' in all_results:
        r = all_results['D1.3']
        best = r['results'][r['best_alpha']]
        print(f"  {'D1.3 Shortcut':20s}  {'phi_ratio (best)':20s}  {best['phi_ratio']:12.2f}  "
              f"{'alpha=' + str(r['best_alpha']):20s}")

    if 'D2.1' in all_results:
        r = all_results['D2.1']
        print(f"  {'D2.1 Mass':20s}  {'top10% mass%':20s}  {r['mass_top10_pct']:12.1f}  "
              f"{'CONCENTRATED' if r['mass_top10_pct'] > 50 else 'DISTRIBUTED':20s}")

    if 'D2.2' in all_results:
        r = all_results['D2.2']
        best = r['gravity_results'][r['best_G']]
        sign = '+' if best['improvement'] >= 0 else ''
        print(f"  {'D2.2 Gravity':20s}  {'best improvement':20s}  {sign}{best['improvement']:11.1f}%  "
              f"{'G=' + str(r['best_G']):20s}")

    if 'D2.3' in all_results:
        r = all_results['D2.3']
        verdict = "ALIGNED" if r['avg_alignment'] > 0.3 else "WEAK" if r['avg_alignment'] > 0 else "OPPOSED"
        print(f"  {'D2.3 Phi-Grad':20s}  {'avg cos_sim':20s}  {r['avg_alignment']:12.4f}  {verdict:20s}")

    print(f"\n  Total time: {elapsed:.1f}s")

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), 'acceleration_d1_d2_results.json')
    serializable = {}
    for k, v in all_results.items():
        serializable[k] = {}
        for kk, vv in v.items():
            if isinstance(vv, (int, float, str, bool)):
                serializable[k][kk] = vv
            elif isinstance(vv, dict):
                serializable[k][kk] = {str(kkk): vvv for kkk, vvv in vv.items()
                                        if isinstance(vvv, (int, float, str, bool, dict))}
            elif isinstance(vv, list):
                serializable[k][kk] = [x if isinstance(x, (int, float, str, bool)) else str(x) for x in vv]

    with open(out_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"  Results saved to {out_path}")

    sys.stdout.flush()


if __name__ == '__main__':
    main()
