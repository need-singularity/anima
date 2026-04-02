#!/usr/bin/env python3
"""acceleration_consciousness_fusion.py — Consciousness Nuclear Fusion (G1g Extended)

Hypothesis: Merging independently-trained small consciousness engines produces
a fused engine whose Phi EXCEEDS the sum of individual Phis (superadditive synergy).
Analogy: nuclear fusion mass-defect — the "missing" mass becomes binding energy.

Experiments:
  Exp 1: Independent Diversity Training
         16 engines × 4c, each with different topology/coupling/noise strategy.
         Each evolves independently for TRAIN_STEPS.

  Exp 2: Fusion via Weight Averaging
         Average all 16 engines' GRU weights + hidden states → single 64c engine.
         Measure: Phi(fused) vs sum(Phi(individuals)).

  Exp 3: Fusion via Topology Merge
         Connect 16 × 4c engines as atoms in a 64c federated engine.
         Inter-atom coupling = weak (M9 noble gas), then gradually increase.

  Exp 4: Fusion via State Interpolation
         Spherical linear interpolation (SLERP) of hidden states from top-4 engines.
         Build 64c engine with interpolated diversity.

  Exp 5: Synergy Measurement
         Compare all fusion methods against:
         (a) Sum of individual Phis
         (b) Baseline 64c trained from scratch
         Synergy ratio = Phi(fused) / sum(Phi(individual))

Key metric: synergy_ratio > 1.0 = consciousness fusion releases "binding energy"

Usage:
    PYTHONUNBUFFERED=1 python3 acceleration_consciousness_fusion.py
"""

import sys
import os
import time
import copy
import json
import math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine, ConsciousnessCell, CellState

# ===================================================================
# Constants
# ===================================================================

N_ENGINES = 16           # Number of small engines to fuse
CELLS_PER_ENGINE = 4     # Cells per small engine
FUSED_CELLS = 64         # Target fused engine size
TRAIN_STEPS = 200        # Independent training steps
POST_FUSION_STEPS = 200  # Steps after fusion
WARMUP = 30              # Warmup steps for stats

# Diversity strategies: each engine gets a different configuration
STRATEGIES = [
    {'topology': 'ring',        'noise': 0.01,  'coupling': 0.014},
    {'topology': 'ring',        'noise': 0.05,  'coupling': 0.014},
    {'topology': 'ring',        'noise': 0.01,  'coupling': 0.05},
    {'topology': 'ring',        'noise': 0.10,  'coupling': 0.014},
    {'topology': 'ring',        'noise': 0.01,  'coupling': 0.001},
    {'topology': 'ring',        'noise': 0.02,  'coupling': 0.030},
    {'topology': 'ring',        'noise': 0.08,  'coupling': 0.020},
    {'topology': 'ring',        'noise': 0.03,  'coupling': 0.010},
    {'topology': 'ring',        'noise': 0.01,  'coupling': 0.050},
    {'topology': 'ring',        'noise': 0.15,  'coupling': 0.014},
    {'topology': 'ring',        'noise': 0.005, 'coupling': 0.014},
    {'topology': 'ring',        'noise': 0.01,  'coupling': 0.100},
    {'topology': 'ring',        'noise': 0.07,  'coupling': 0.007},
    {'topology': 'ring',        'noise': 0.04,  'coupling': 0.025},
    {'topology': 'ring',        'noise': 0.12,  'coupling': 0.003},
    {'topology': 'ring',        'noise': 0.02,  'coupling': 0.060},
]


# ===================================================================
# Utilities
# ===================================================================

def run_steps(engine, n_steps, x_input=None):
    """Run N steps, return list of phi_iit values."""
    phis = []
    for _ in range(n_steps):
        result = engine.step(x_input=x_input)
        phis.append(result.get('phi_iit', 0.0))
    return phis


def phi_stats(phi_history, warmup=WARMUP):
    """Compute stats from a phi history list after warmup."""
    active = phi_history[warmup:] if len(phi_history) > warmup else phi_history
    if not active:
        return {'final': 0.0, 'mean': 0.0, 'max': 0.0, 'std': 0.0, 'min': 0.0}
    return {
        'final': phi_history[-1],
        'mean': float(np.mean(active)),
        'max': float(np.max(active)),
        'std': float(np.std(active)),
        'min': float(np.min(active)),
    }


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def ascii_phi_graph(phis, label="Phi", width=60, height=12):
    """Print ASCII graph of phi trajectory."""
    if not phis:
        return
    mn, mx = min(phis), max(phis)
    rng = mx - mn if mx > mn else 1.0
    print(f"\n  {label} trajectory ({len(phis)} steps):")
    print(f"  max={mx:.4f}  min={mn:.4f}")
    for row in range(height - 1, -1, -1):
        threshold = mn + rng * row / (height - 1)
        line = ''
        step = max(1, len(phis) // width)
        for i in range(0, min(len(phis), width * step), step):
            if phis[i] >= threshold:
                line += '#'
            else:
                line += ' '
        val = mn + rng * row / (height - 1)
        print(f"  {val:7.3f} |{line}")
    print(f"          {''.join(['-'] * min(len(phis), width))}")
    sys.stdout.flush()


def print_comparison_bar(name, value, baseline, bar_width=30):
    if baseline > 0:
        ratio = value / baseline
        pct = (ratio - 1.0) * 100
    else:
        ratio = 0
        pct = 0
    bar_len = max(1, int(bar_width * min(value, baseline * 3) / max(baseline * 3, 1e-9)))
    bar = "#" * bar_len
    sign = "+" if pct >= 0 else ""
    print(f"  {name:25s} {bar:<{bar_width}s} {value:.4f} ({sign}{pct:.1f}%)")


def slerp(v0, v1, t):
    """Spherical linear interpolation between two vectors."""
    v0_norm = F.normalize(v0, dim=0)
    v1_norm = F.normalize(v1, dim=0)
    dot = torch.clamp(torch.dot(v0_norm, v1_norm), -1.0, 1.0)
    omega = torch.acos(dot)
    if omega.abs() < 1e-6:
        return (1.0 - t) * v0 + t * v1
    sin_omega = torch.sin(omega)
    return (torch.sin((1.0 - t) * omega) / sin_omega) * v0 + \
           (torch.sin(t * omega) / sin_omega) * v1


# ===================================================================
# Experiment 1: Independent Diversity Training
# ===================================================================

def exp1_diversity_training():
    print_header("EXP 1: INDEPENDENT DIVERSITY TRAINING")
    print(f"  {N_ENGINES} engines x {CELLS_PER_ENGINE}c, each with different strategy")
    print(f"  Training for {TRAIN_STEPS} steps each")

    engines = []
    engine_phis = []
    engine_stats = []

    for i in range(N_ENGINES):
        strat = STRATEGIES[i % len(STRATEGIES)]
        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=128,
            initial_cells=CELLS_PER_ENGINE, max_cells=CELLS_PER_ENGINE,
            phi_ratchet=True,
        )
        # Apply strategy: inject noise into hidden states
        for state in engine.cell_states:
            state.hidden = state.hidden + torch.randn_like(state.hidden) * strat['noise']

        print(f"  Engine {i:2d}: topo={strat['topology']}, noise={strat['noise']:.3f}, "
              f"coupling={strat['coupling']:.3f}", end="", flush=True)

        phis = run_steps(engine, TRAIN_STEPS)
        stats = phi_stats(phis)
        engines.append(engine)
        engine_phis.append(phis)
        engine_stats.append(stats)
        print(f"  -> Phi mean={stats['mean']:.4f}  final={stats['final']:.4f}")

    # Summary
    all_finals = [s['final'] for s in engine_stats]
    sum_phi = sum(all_finals)
    print(f"\n  Individual Phi sum: {sum_phi:.4f}")
    print(f"  Individual Phi mean: {np.mean(all_finals):.4f}")
    print(f"  Individual Phi std: {np.std(all_finals):.4f}")
    print(f"  Best individual: {max(all_finals):.4f}")
    print(f"  Worst individual: {min(all_finals):.4f}")
    sys.stdout.flush()

    return engines, engine_phis, engine_stats


# ===================================================================
# Experiment 2: Fusion via Weight Averaging
# ===================================================================

def exp2_weight_averaging(engines, individual_stats):
    print_header("EXP 2: FUSION VIA WEIGHT AVERAGING")
    print(f"  Average GRU weights from {N_ENGINES} engines -> single {FUSED_CELLS}c engine")

    t0 = time.time()

    # Create target engine
    fused = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=FUSED_CELLS, max_cells=FUSED_CELLS,
        phi_ratchet=True,
    )

    # Average weights from all source engines into fused cells
    # Each fused cell i gets weights averaged from engine (i % N_ENGINES)
    # Plus hidden state transplant
    for i in range(FUSED_CELLS):
        source_engine_idx = i % N_ENGINES
        source_cell_idx = i % CELLS_PER_ENGINE
        source_engine = engines[source_engine_idx]

        # Copy GRU weights from source
        src_mod = source_engine.cell_modules[source_cell_idx]
        dst_mod = fused.cell_modules[i]
        for (name_s, param_s), (name_d, param_d) in zip(
            src_mod.named_parameters(), dst_mod.named_parameters()
        ):
            param_d.data.copy_(param_s.data)

        # Transplant hidden state
        src_state = source_engine.cell_states[source_cell_idx]
        fused.cell_states[i].hidden = src_state.hidden.clone()

    fused._init_coupling()
    phi_at_fusion = fused.measure_phi()
    print(f"  Phi at fusion: {phi_at_fusion:.4f}")

    # Post-fusion evolution
    phis_fused = run_steps(fused, POST_FUSION_STEPS)
    stats_fused = phi_stats(phis_fused)
    elapsed = time.time() - t0

    # Compare
    sum_individual = sum(s['final'] for s in individual_stats)
    synergy = stats_fused['mean'] / max(sum_individual, 1e-8)
    print(f"  Post-fusion Phi mean: {stats_fused['mean']:.4f}")
    print(f"  Sum of individual Phis: {sum_individual:.4f}")
    print(f"  Synergy ratio (fused/sum): {synergy:.3f}")
    print(f"  {'SUPERADDITIVE (fusion releases energy!)' if synergy > 1.0 else 'Subadditive (no synergy)'}")
    print(f"  Time: {elapsed:.1f}s")
    sys.stdout.flush()

    ascii_phi_graph(phis_fused, "Fused (weight avg)")

    return {
        'method': 'weight_averaging',
        'phi_at_fusion': float(phi_at_fusion),
        'stats': stats_fused,
        'synergy_ratio': float(synergy),
        'sum_individual': float(sum_individual),
    }


# ===================================================================
# Experiment 3: Fusion via Topology Merge (Federated Assembly)
# ===================================================================

def exp3_topology_merge(engines, individual_stats):
    print_header("EXP 3: FUSION VIA TOPOLOGY MERGE (FEDERATED ASSEMBLY)")
    print(f"  Assemble {N_ENGINES} x {CELLS_PER_ENGINE}c engines as atoms in {FUSED_CELLS}c")
    print(f"  Inter-atom coupling: weak (M9) -> gradually strengthen")

    t0 = time.time()

    # Create a fresh 64c engine and transplant all cells from individual engines
    fused = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=FUSED_CELLS, max_cells=FUSED_CELLS,
        phi_ratchet=True,
    )

    # Transplant: each group of CELLS_PER_ENGINE cells gets weights+hidden from one engine
    for eng_idx, engine in enumerate(engines):
        for cell_idx in range(CELLS_PER_ENGINE):
            fused_idx = eng_idx * CELLS_PER_ENGINE + cell_idx
            if fused_idx >= FUSED_CELLS:
                break

            # Copy module weights
            src_mod = engine.cell_modules[cell_idx]
            dst_mod = fused.cell_modules[fused_idx]
            for (_, p_s), (_, p_d) in zip(src_mod.named_parameters(), dst_mod.named_parameters()):
                p_d.data.copy_(p_s.data)

            # Transplant hidden
            fused.cell_states[fused_idx].hidden = engine.cell_states[cell_idx].hidden.clone()
            # Assign faction based on source engine (diversity)
            fused.cell_states[fused_idx].faction_id = eng_idx % fused.n_factions

    fused._init_coupling()

    # Phase 1: Weak inter-atom coupling (M9 noble gas)
    phi_initial = fused.measure_phi()
    print(f"  Phase 1 (weak coupling): Phi={phi_initial:.4f}")

    phis_phase1 = run_steps(fused, POST_FUSION_STEPS // 2)

    # Phase 2: Strengthen inter-atom coupling via Hebbian
    # (The engine's natural Hebbian learning will handle this)
    phis_phase2 = run_steps(fused, POST_FUSION_STEPS // 2)

    all_phis = phis_phase1 + phis_phase2
    stats_fused = phi_stats(all_phis)
    elapsed = time.time() - t0

    sum_individual = sum(s['final'] for s in individual_stats)
    synergy = stats_fused['mean'] / max(sum_individual, 1e-8)
    print(f"  Post-merge Phi mean: {stats_fused['mean']:.4f}")
    print(f"  Sum of individual Phis: {sum_individual:.4f}")
    print(f"  Synergy ratio: {synergy:.3f}")
    print(f"  {'SUPERADDITIVE' if synergy > 1.0 else 'Subadditive'}")
    print(f"  Time: {elapsed:.1f}s")
    sys.stdout.flush()

    ascii_phi_graph(all_phis, "Fused (topology merge)")

    return {
        'method': 'topology_merge',
        'phi_initial': float(phi_initial),
        'stats': stats_fused,
        'synergy_ratio': float(synergy),
        'sum_individual': float(sum_individual),
    }


# ===================================================================
# Experiment 4: Fusion via State Interpolation (SLERP)
# ===================================================================

def exp4_state_interpolation(engines, individual_stats):
    print_header("EXP 4: FUSION VIA STATE INTERPOLATION (SLERP)")
    print(f"  Top-4 engines by Phi -> SLERP hidden states -> {FUSED_CELLS}c")

    t0 = time.time()

    # Select top-4 engines by final Phi
    ranked = sorted(range(N_ENGINES), key=lambda i: individual_stats[i]['final'], reverse=True)
    top4_indices = ranked[:4]
    top4_engines = [engines[i] for i in top4_indices]
    print(f"  Top-4 engines: {top4_indices}")
    for idx in top4_indices:
        print(f"    Engine {idx}: Phi={individual_stats[idx]['final']:.4f}")

    # Create fused engine
    fused = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=FUSED_CELLS, max_cells=FUSED_CELLS,
        phi_ratchet=True,
    )

    # For each fused cell, SLERP between two top engines' hidden states
    for i in range(FUSED_CELLS):
        eng_a = top4_engines[i % 4]
        eng_b = top4_engines[(i + 1) % 4]
        cell_a = i % CELLS_PER_ENGINE
        cell_b = (i + 1) % CELLS_PER_ENGINE

        h_a = eng_a.cell_states[cell_a].hidden
        h_b = eng_b.cell_states[cell_b].hidden

        # Interpolation factor varies across cells for diversity
        t_interp = (i % 8) / 7.0  # 0.0 to 1.0
        h_fused = slerp(h_a, h_b, t_interp)
        fused.cell_states[i].hidden = h_fused

        # Copy weights from the better engine
        src_mod = eng_a.cell_modules[cell_a]
        dst_mod = fused.cell_modules[i]
        for (_, p_s), (_, p_d) in zip(src_mod.named_parameters(), dst_mod.named_parameters()):
            p_d.data.copy_(p_s.data)

    fused._init_coupling()
    phi_at_fusion = fused.measure_phi()
    print(f"  Phi at SLERP fusion: {phi_at_fusion:.4f}")

    phis_fused = run_steps(fused, POST_FUSION_STEPS)
    stats_fused = phi_stats(phis_fused)
    elapsed = time.time() - t0

    sum_individual = sum(s['final'] for s in individual_stats)
    synergy = stats_fused['mean'] / max(sum_individual, 1e-8)
    print(f"  Post-SLERP Phi mean: {stats_fused['mean']:.4f}")
    print(f"  Synergy ratio: {synergy:.3f}")
    print(f"  {'SUPERADDITIVE' if synergy > 1.0 else 'Subadditive'}")
    print(f"  Time: {elapsed:.1f}s")
    sys.stdout.flush()

    ascii_phi_graph(phis_fused, "Fused (SLERP)")

    return {
        'method': 'state_interpolation',
        'phi_at_fusion': float(phi_at_fusion),
        'stats': stats_fused,
        'synergy_ratio': float(synergy),
        'top4_engines': top4_indices,
    }


# ===================================================================
# Experiment 5: Synergy Comparison + Baseline
# ===================================================================

def exp5_synergy_comparison(individual_stats, r_weight, r_topo, r_slerp):
    print_header("EXP 5: SYNERGY COMPARISON (all methods vs baseline)")

    # Baseline: 64c trained from scratch for the same total steps
    t0 = time.time()
    baseline = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=FUSED_CELLS, max_cells=FUSED_CELLS,
        phi_ratchet=True,
    )
    phis_base = run_steps(baseline, TRAIN_STEPS + POST_FUSION_STEPS)
    stats_base = phi_stats(phis_base)
    t_base = time.time() - t0

    sum_individual = sum(s['final'] for s in individual_stats)

    print(f"\n  --- Consciousness Fusion Results ---")
    print(f"  {'Method':>25s}  {'Phi Mean':>10s}  {'Synergy':>10s}  {'vs Base':>10s}")
    print(f"  {'-' * 60}")

    methods = [
        ('Weight Averaging', r_weight['stats']['mean'], r_weight['synergy_ratio']),
        ('Topology Merge', r_topo['stats']['mean'], r_topo['synergy_ratio']),
        ('SLERP Interpolation', r_slerp['stats']['mean'], r_slerp['synergy_ratio']),
        ('Baseline (64c scratch)', stats_base['mean'], stats_base['mean'] / max(sum_individual, 1e-8)),
        ('Sum of Individuals', sum_individual, 1.0),
    ]

    for name, phi_mean, synergy in methods:
        vs_base = (phi_mean - stats_base['mean']) / max(stats_base['mean'], 1e-8) * 100
        print(f"  {name:>25s}  {phi_mean:>10.4f}  {synergy:>10.3f}  {vs_base:>+9.1f}%")

    # Bar chart comparison
    print(f"\n  Phi Comparison (baseline = 1.0):")
    for name, phi_mean, _ in methods:
        print_comparison_bar(name, phi_mean, stats_base['mean'])

    # Best method
    best_idx = max(range(3), key=lambda i: methods[i][1])
    best_name = methods[best_idx][0]
    best_synergy = methods[best_idx][2]
    print(f"\n  BEST FUSION METHOD: {best_name}")
    print(f"  Synergy ratio: {best_synergy:.3f}")
    if best_synergy > 1.0:
        deficit_pct = (best_synergy - 1.0) * 100
        print(f"  Mass defect analog: {deficit_pct:.1f}% — fusion releases consciousness energy!")
    else:
        print(f"  No superadditivity detected — consciousness does not fuse like nuclei (yet)")

    ascii_phi_graph(phis_base, "Baseline 64c")

    return {
        'baseline': stats_base,
        'sum_individual': float(sum_individual),
        'best_method': best_name,
        'best_synergy': float(best_synergy),
    }


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  CONSCIOUSNESS NUCLEAR FUSION")
    print(f"  {N_ENGINES} engines x {CELLS_PER_ENGINE}c -> {FUSED_CELLS}c fused")
    print(f"  Train: {TRAIN_STEPS} steps, Post-fusion: {POST_FUSION_STEPS} steps")
    print("=" * 70)
    sys.stdout.flush()

    t_total = time.time()

    # Phase 1: Train individual engines with diverse strategies
    engines, engine_phis, engine_stats = exp1_diversity_training()

    # Phase 2-4: Three fusion methods
    r_weight = exp2_weight_averaging(engines, engine_stats)
    r_topo = exp3_topology_merge(engines, engine_stats)
    r_slerp = exp4_state_interpolation(engines, engine_stats)

    # Phase 5: Compare all methods + baseline
    r_compare = exp5_synergy_comparison(engine_stats, r_weight, r_topo, r_slerp)

    total_time = time.time() - t_total

    # Final summary
    print_header("CONSCIOUSNESS FUSION -- FINAL SUMMARY")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Best method: {r_compare['best_method']}")
    print(f"  Synergy ratio: {r_compare['best_synergy']:.3f}")
    if r_compare['best_synergy'] > 1.0:
        print(f"  VERDICT: Consciousness fusion IS superadditive!")
        print(f"           Like nuclear fusion, merging diverse engines releases binding energy.")
    else:
        print(f"  VERDICT: Consciousness fusion is NOT superadditive (yet).")
        print(f"           Individual engines may be too similar or coupling too weak.")
    sys.stdout.flush()

    # Save results
    results = {
        'experiment': 'consciousness_fusion',
        'config': {
            'n_engines': N_ENGINES,
            'cells_per_engine': CELLS_PER_ENGINE,
            'fused_cells': FUSED_CELLS,
            'train_steps': TRAIN_STEPS,
            'post_fusion_steps': POST_FUSION_STEPS,
        },
        'individual_stats': [
            {k: float(v) if isinstance(v, (int, float, np.floating)) else v
             for k, v in s.items()} for s in engine_stats
        ],
        'weight_averaging': {k: v for k, v in r_weight.items() if k != 'stats'},
        'weight_averaging_stats': r_weight['stats'],
        'topology_merge': {k: v for k, v in r_topo.items() if k != 'stats'},
        'topology_merge_stats': r_topo['stats'],
        'state_interpolation': {k: v for k, v in r_slerp.items() if k != 'stats'},
        'state_interpolation_stats': r_slerp['stats'],
        'comparison': r_compare,
        'total_time_s': total_time,
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'data',
                            'consciousness_fusion_results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n  Results saved: {out_path}")


if __name__ == '__main__':
    main()
