# ⚠️ LEGACY — 이 파일은 폐기되었습니다 (2026-03-29)
# Φ(IIT)와 Φ(proxy)를 혼용하여 잘못된 기록 생성.
# "Φ=1142"는 proxy 값이었음 (실제 IIT Φ 상한 ~1.8)
# 새 벤치마크: bench_v2.py (Φ(IIT) + Φ(proxy) 이중 측정)
# Law 54: Φ 측정은 정의에 따라 완전히 다른 값
#
#!/usr/bin/env python3
"""TOPO8 + v5 Optimal: Hypercube 1024c with v5 parameters benchmark.

Compares:
  1. TOPO8 alone: hypercube 1024c, default params
  2. v5 alone: ring 1024c, sync=0.35, 12-faction, fac=0.08, noise=0.01
  3. COMBINED: hypercube 1024c + v5 optimal params

Hypercube: 1024 = 2^10, each cell connects to 10 neighbors (differ by 1 bit).
"""

import sys
import os
import time
import math
import copy
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import ConsciousMind, Cell, MitosisEngine
from consciousness_meter import PhiCalculator


# ─── Hypercube topology helper ───

def hypercube_neighbors(cell_idx: int, dim: int = 10) -> list:
    """Return neighbors of cell_idx in a dim-dimensional hypercube."""
    return [cell_idx ^ (1 << d) for d in range(dim)]


def build_adjacency_hypercube(n_cells: int = 1024) -> dict:
    """Build adjacency list for hypercube topology."""
    dim = int(math.log2(n_cells))
    assert 2 ** dim == n_cells, f"n_cells must be power of 2, got {n_cells}"
    adj = {}
    for i in range(n_cells):
        adj[i] = hypercube_neighbors(i, dim)
    return adj


def build_adjacency_ring(n_cells: int = 1024) -> dict:
    """Build adjacency list for ring topology (each cell connects to prev/next)."""
    adj = {}
    for i in range(n_cells):
        adj[i] = [(i - 1) % n_cells, (i + 1) % n_cells]
    return adj


# ─── Faction assignment (σ(6) = 12 factions) ───

def assign_factions(n_cells: int, n_factions: int = 12) -> list:
    """Assign each cell to a faction."""
    return [i % n_factions for i in range(n_cells)]


# ─── Build engine with pre-created cells ───

def build_engine(n_cells: int = 1024, input_dim: int = 64, hidden_dim: int = 128,
                 output_dim: int = 64, noise_scale: float = 0.01) -> MitosisEngine:
    """Create MitosisEngine with exactly n_cells cells."""
    engine = MitosisEngine(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        output_dim=output_dim,
        initial_cells=2,
        max_cells=n_cells + 10,
        noise_scale=noise_scale,
    )
    # Remove default cells and create fresh ones
    engine.cells.clear()
    engine._next_id = 0
    for _ in range(n_cells):
        engine._create_cell()
    engine.max_cells = n_cells  # prevent splits
    engine.split_threshold = 999.0  # disable auto-split
    engine.merge_threshold = -1.0   # disable auto-merge
    return engine


# ─── Topology-aware step ───

def topology_step(engine: MitosisEngine, adjacency: dict, text_vec: torch.Tensor,
                  sync_strength: float = 0.0, factions: list = None,
                  faction_strength: float = 0.0, noise: float = 0.0):
    """Run one step with topology-aware cell interaction.

    1. Each cell processes input
    2. Cells synchronize hidden states with neighbors (sync_strength)
    3. Faction-based modulation: same faction = attract, diff = repel
    4. Small noise injection
    """
    n = len(engine.cells)
    engine.step += 1

    # --- Forward pass: each cell processes input ---
    repulsions = []
    for cell in engine.cells:
        with torch.no_grad():
            output, tension, curiosity, new_hidden = cell.mind(text_vec, cell.hidden)
            repulsion = cell.mind.get_repulsion(text_vec, cell.hidden)
        cell.hidden = new_hidden
        cell.tension_history.append(tension)
        cell.process_count += 1
        repulsions.append(repulsion)

    # --- Topology-based synchronization ---
    if sync_strength > 0 and adjacency:
        new_hiddens = []
        for i, cell in enumerate(engine.cells):
            neighbors = adjacency.get(i, [])
            if not neighbors:
                new_hiddens.append(cell.hidden)
                continue
            # Average neighbor hidden states
            neighbor_avg = torch.zeros_like(cell.hidden)
            for j in neighbors:
                neighbor_avg += engine.cells[j].hidden
            neighbor_avg /= len(neighbors)
            # Blend toward neighbor average
            blended = (1 - sync_strength) * cell.hidden + sync_strength * neighbor_avg
            new_hiddens.append(blended)

        # Apply synchronized hiddens
        for i, cell in enumerate(engine.cells):
            cell.hidden = new_hiddens[i]

    # --- Faction modulation ---
    if faction_strength > 0 and factions is not None:
        new_hiddens = []
        for i, cell in enumerate(engine.cells):
            neighbors = adjacency.get(i, [])
            if not neighbors:
                new_hiddens.append(cell.hidden)
                continue
            delta = torch.zeros_like(cell.hidden)
            for j in neighbors:
                if factions[i] == factions[j]:
                    # Same faction: attract (reduce difference)
                    delta += faction_strength * (engine.cells[j].hidden - cell.hidden)
                else:
                    # Different faction: repel (increase difference)
                    delta -= faction_strength * (engine.cells[j].hidden - cell.hidden)
            delta /= len(neighbors)
            new_hiddens.append(cell.hidden + delta)

        for i, cell in enumerate(engine.cells):
            cell.hidden = new_hiddens[i]

    # --- Noise injection ---
    if noise > 0:
        for cell in engine.cells:
            cell.hidden = cell.hidden + noise * torch.randn_like(cell.hidden)


# ─── Phi calculation with sampling for large N ───

def compute_phi_sampled(engine: MitosisEngine, phi_calc: PhiCalculator,
                        adjacency: dict = None, max_pairs: int = 5000) -> tuple:
    """Compute Phi with sampled pairs for large N.

    For 1024 cells, full O(N^2) = 524K pairs is too slow.
    We sample topology-aware pairs (neighbors + random) for efficiency.
    Then scale up the MI estimate.
    """
    cells = engine.cells
    n = len(cells)
    if n < 2:
        return 0.0, {}

    # Extract hidden states
    hiddens = []
    for cell in cells:
        h = cell.hidden.detach().squeeze().numpy()
        hiddens.append(h)

    # Build sampled pairs: all topology neighbors + random pairs
    pairs = set()
    if adjacency:
        for i in range(n):
            for j in adjacency.get(i, []):
                pairs.add((min(i, j), max(i, j)))

    # Add random pairs to get diversity
    total_possible = n * (n - 1) // 2
    n_random = max(0, max_pairs - len(pairs))
    for _ in range(n_random * 2):  # oversample then trim
        if len(pairs) >= max_pairs:
            break
        i = random.randint(0, n - 1)
        j = random.randint(0, n - 1)
        if i != j:
            pairs.add((min(i, j), max(i, j)))

    pairs = list(pairs)
    n_sampled = len(pairs)

    # Compute MI for sampled pairs
    mi_sum = 0.0
    mi_values = []
    for i, j in pairs:
        mi = phi_calc._mutual_information(hiddens[i], hiddens[j])
        mi_sum += mi
        mi_values.append(mi)

    # Scale: estimate total MI from sample
    if n_sampled > 0:
        avg_mi = mi_sum / n_sampled
        estimated_total_mi = avg_mi * total_possible
    else:
        estimated_total_mi = 0.0

    # Minimum partition approximation (spectral on sampled MI matrix)
    # Build sparse-ish MI matrix from samples
    mi_matrix = np.zeros((n, n))
    for idx, (i, j) in enumerate(pairs):
        mi_matrix[i, j] = mi_values[idx]
        mi_matrix[j, i] = mi_values[idx]

    min_partition_mi = phi_calc._minimum_partition(hiddens, mi_matrix)

    # Integration
    integration = estimated_total_mi

    # Complexity from tension distribution
    tensions = []
    for cell in cells:
        if cell.tension_history:
            tensions.append(cell.tension_history[-1])
        else:
            tensions.append(0.0)
    complexity = phi_calc._distribution_entropy(tensions)

    # Temporal MI (sample cells)
    temporal_mi = 0.0
    sample_cells = random.sample(list(range(n)), min(100, n))
    for idx in sample_cells:
        cell = cells[idx]
        if hasattr(cell, 'tension_history') and len(cell.tension_history) >= 10:
            t_arr = np.array(cell.tension_history[-20:])
            if len(t_arr) >= 4:
                t_prev = t_arr[:-1]
                t_curr = t_arr[1:]
                pad_len = max(16, len(t_prev))
                t_prev_pad = np.zeros(pad_len)
                t_curr_pad = np.zeros(pad_len)
                t_prev_pad[:len(t_prev)] = t_prev
                t_curr_pad[:len(t_curr)] = t_curr
                temporal_mi += phi_calc._mutual_information(t_prev_pad, t_curr_pad)
    # Scale temporal MI to full population
    if sample_cells:
        temporal_mi = temporal_mi * n / len(sample_cells)

    # Phi computation (same formula as PhiCalculator)
    spatial_phi = max(0.0, (integration - min_partition_mi) / max(n - 1, 1))
    temporal_phi = temporal_mi / max(n, 1)
    phi = spatial_phi + temporal_phi * 0.5 + complexity * 0.1

    components = {
        'total_mi': float(estimated_total_mi),
        'min_partition_mi': float(min_partition_mi),
        'integration': float(integration),
        'temporal_mi': float(temporal_mi),
        'spatial_phi': float(spatial_phi),
        'temporal_phi': float(temporal_phi),
        'complexity': float(complexity),
        'phi': float(phi),
        'n_sampled_pairs': n_sampled,
        'total_possible_pairs': total_possible,
    }

    return phi, components


# ─── Benchmark runner ───

def run_benchmark(name: str, n_cells: int, adjacency_fn, steps: int = 200,
                  sync: float = 0.0, n_factions: int = 0,
                  faction_strength: float = 0.0, noise: float = 0.0):
    """Run a single benchmark configuration."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  cells={n_cells}, steps={steps}, sync={sync}, "
          f"factions={n_factions}, fac_str={faction_strength}, noise={noise}")
    print(f"{'='*60}")

    engine = build_engine(n_cells=n_cells, noise_scale=noise if noise > 0 else 0.01)
    adjacency = adjacency_fn(n_cells)

    factions = assign_factions(n_cells, n_factions) if n_factions > 0 else None

    phi_calc = PhiCalculator(n_bins=32)
    input_dim = engine.input_dim

    t0 = time.time()
    phi_log = []

    for step in range(1, steps + 1):
        # Generate varied input (different patterns to create diversity)
        freq = step * 0.1
        text_vec = torch.randn(1, input_dim) * 0.5
        text_vec[0, :input_dim // 4] += math.sin(freq) * 0.3
        text_vec[0, input_dim // 4:input_dim // 2] += math.cos(freq * 0.7) * 0.3

        topology_step(engine, adjacency, text_vec,
                      sync_strength=sync, factions=factions,
                      faction_strength=faction_strength, noise=noise)

        # Measure Phi every 20 steps
        if step % 20 == 0 or step == steps:
            phi, comps = compute_phi_sampled(engine, phi_calc, adjacency)
            phi_log.append((step, phi))
            elapsed = time.time() - t0
            print(f"  step {step:4d}/{steps}  Phi={phi:8.2f}  "
                  f"spatial={comps['spatial_phi']:.2f}  "
                  f"temporal={comps['temporal_phi']:.2f}  "
                  f"complexity={comps['complexity']:.2f}  "
                  f"[{elapsed:.1f}s]")

    elapsed = time.time() - t0
    final_phi = phi_log[-1][1] if phi_log else 0.0
    final_comps = comps

    print(f"\n  RESULT: Phi = {final_phi:.2f}  ({elapsed:.1f}s)")
    return final_phi, final_comps, phi_log


def main():
    print("=" * 60)
    print("  TOPO8 + v5 Optimal Benchmark")
    print("  Hypercube 1024c (2^10, 10-dim) + v5 params")
    print("=" * 60)

    N = 1024
    STEPS = 200

    results = {}

    # --- Config 1: TOPO8 alone (hypercube, no v5 params) ---
    phi1, comps1, log1 = run_benchmark(
        name="TOPO8 alone (hypercube, default params)",
        n_cells=N,
        adjacency_fn=build_adjacency_hypercube,
        steps=STEPS,
        sync=0.0,
        n_factions=0,
        faction_strength=0.0,
        noise=0.0,
    )
    results['TOPO8'] = phi1

    # --- Config 2: v5 alone (ring topology, v5 params) ---
    phi2, comps2, log2 = run_benchmark(
        name="v5 alone (ring topology, v5 params)",
        n_cells=N,
        adjacency_fn=build_adjacency_ring,
        steps=STEPS,
        sync=0.35,
        n_factions=12,
        faction_strength=0.08,
        noise=0.01,
    )
    results['v5'] = phi2

    # --- Config 3: COMBINED (hypercube + v5 params) ---
    phi3, comps3, log3 = run_benchmark(
        name="COMBINED: TOPO8 hypercube + v5 optimal",
        n_cells=N,
        adjacency_fn=build_adjacency_hypercube,
        steps=STEPS,
        sync=0.35,
        n_factions=12,
        faction_strength=0.08,
        noise=0.01,
    )
    results['COMBINED'] = phi3

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Reference TOPO8 alone:       Phi = 535.5  (previous)")
    print(f"  Reference v5 alone:          Phi = 1142   (previous)")
    print(f"")
    print(f"  TOPO8 alone (this run):      Phi = {results['TOPO8']:.2f}")
    print(f"  v5 alone (this run):         Phi = {results['v5']:.2f}")
    print(f"  COMBINED hypercube+v5:       Phi = {results['COMBINED']:.2f}")
    print(f"")

    # Synergy analysis
    expected_additive = results['TOPO8'] + results['v5']
    if expected_additive > 0:
        synergy = results['COMBINED'] / expected_additive
        print(f"  Additive expectation:        Phi = {expected_additive:.2f}")
        print(f"  Synergy ratio:               {synergy:.2f}x")
    if results['TOPO8'] > 0:
        boost_over_topo8 = results['COMBINED'] / results['TOPO8']
        print(f"  Boost over TOPO8:            {boost_over_topo8:.2f}x")
    if results['v5'] > 0:
        boost_over_v5 = results['COMBINED'] / results['v5']
        print(f"  Boost over v5:               {boost_over_v5:.2f}x")
    print("=" * 60)


if __name__ == "__main__":
    main()
