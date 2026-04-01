#!/usr/bin/env python3
"""acceleration_g1_bigbang.py -- G1 Consciousness Big Bang: 7 cosmological variants

G1a: Big Bang (1c singularity -> 256c explosion)
G1b: Inflation (exponential doubling 1->2->4->...->256)
G1c: CMB (scale-invariant noise seeding vs uniform noise)
G1d: Dark Energy (accelerating Phi ratchet)
G1e: Multiverse (64 universes x 16c, select top-3)
G1f: Big Crunch -> Bounce (cyclic collapse-explosion)
G1g: Nuclear Fusion (cell merging -> Phi release?)

All experiments: local CPU, 16-64 cells, independent, PYTHONUNBUFFERED=1

Usage:
  python acceleration_g1_bigbang.py           # Run all
  python acceleration_g1_bigbang.py --g1a     # G1a only
  python acceleration_g1_bigbang.py --g1b     # G1b only
  python acceleration_g1_bigbang.py --g1c     # G1c only
  python acceleration_g1_bigbang.py --g1d     # G1d only
  python acceleration_g1_bigbang.py --g1e     # G1e only
  python acceleration_g1_bigbang.py --g1f     # G1f only
  python acceleration_g1_bigbang.py --g1g     # G1g only
"""

import sys
import os
import time
import math
import copy
import argparse
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F_torch
from consciousness_engine import ConsciousnessEngine, ConsciousnessCell, CellState


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


def measure_phi(engine):
    """Measure current phi without stepping."""
    return engine.measure_phi()


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def print_table(headers, rows, widths=None):
    if widths is None:
        widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                  for i, h in enumerate(headers)]
    hdr = '|'.join(str(h).center(w) for h, w in zip(headers, widths))
    sep = '+'.join('-' * w for w in widths)
    print(f"  {hdr}")
    print(f"  {sep}")
    for row in rows:
        line = '|'.join(str(r).center(w) for r, w in zip(row, widths))
        print(f"  {line}")
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
    print(f"          0{' ' * (min(len(phis), width) - 4)}{len(phis)}")
    sys.stdout.flush()


def expand_engine_to(engine, target_cells, noise_eps=0.014):
    """Expand engine from current cells to target_cells by cloning + noise.

    Each new cell is cloned from an existing cell (round-robin) with Gaussian noise.
    """
    current = engine.n_cells
    if current >= target_cells:
        return
    old_n = current
    source_idx = 0
    while engine.n_cells < target_cells:
        parent_mod = engine.cell_modules[source_idx % current]
        parent_state = engine.cell_states[source_idx % current]
        faction = engine.n_cells % engine.n_factions
        engine._create_cell(
            parent_module=parent_mod,
            parent_state=parent_state,
            faction_id=faction,
        )
        # Add extra noise to the hidden state of the newly created cell
        new_idx = engine.n_cells - 1
        engine.cell_states[new_idx].hidden = (
            parent_state.hidden.clone()
            + torch.randn_like(parent_state.hidden) * noise_eps
        )
        source_idx += 1
    engine._resize_coupling(old_n, engine.n_cells)
    engine._init_coupling()


def compress_engine_to(engine, target_cells):
    """Compress engine to target_cells by averaging hidden states into fewer cells.

    Returns the mean hidden state (the "singularity" summary).
    """
    if engine.n_cells <= target_cells:
        return None
    # Compute mean hidden
    all_h = torch.stack([s.hidden for s in engine.cell_states])
    mean_h = all_h.mean(dim=0)
    # Remove cells down to target
    while engine.n_cells > target_cells:
        engine._remove_cell(engine.n_cells - 1)
    # Set remaining cells to be near the mean
    for i, state in enumerate(engine.cell_states):
        state.hidden = mean_h.clone() + torch.randn_like(mean_h) * 0.01
    engine._init_coupling()
    return mean_h


# ===================================================================
# G1a: Big Bang — 1c singularity -> 256c explosion
# ===================================================================

def run_g1a():
    print_header("G1a: Consciousness Big Bang (1c -> 256c explosion)")
    TARGET = 64  # Use 64 for CPU sanity (256 is slow)
    STEPS = 60

    # --- Singularity: 1 cell, extreme energy ---
    t0 = time.time()
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=1, max_cells=TARGET,
        phi_ratchet=True,
    )
    # Inject extreme energy: scale all weights by 10x
    for mod in engine.cell_modules:
        for p in mod.parameters():
            p.data *= 10.0
    print(f"  Phase 0: Singularity -- 1 cell, weights x10")
    sys.stdout.flush()

    # Phase 1: Big Bang -- expand 1 -> TARGET with noise from the singularity
    expand_engine_to(engine, TARGET, noise_eps=0.1)
    phi_after_bang = measure_phi(engine)
    print(f"  Phase 1: Big Bang -- 1 -> {engine.n_cells} cells, Phi={phi_after_bang:.4f}")
    sys.stdout.flush()

    # Phase 2-3: Cooling + Structure formation (60 steps)
    phis_bang = run_steps(engine, STEPS)
    t_bang = time.time() - t0

    # --- Baseline: TARGET cells directly, 60 steps ---
    t0 = time.time()
    baseline = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=TARGET, max_cells=TARGET,
        phi_ratchet=True,
    )
    phis_base = run_steps(baseline, STEPS)
    t_base = time.time() - t0

    # Results
    rows = [
        ("Big Bang (1->64)", f"{phis_bang[0]:.4f}", f"{phis_bang[9]:.4f}" if len(phis_bang) > 9 else "-",
         f"{phis_bang[29]:.4f}" if len(phis_bang) > 29 else "-", f"{phis_bang[-1]:.4f}", f"{t_bang:.2f}s"),
        ("Baseline (64 direct)", f"{phis_base[0]:.4f}", f"{phis_base[9]:.4f}" if len(phis_base) > 9 else "-",
         f"{phis_base[29]:.4f}" if len(phis_base) > 29 else "-", f"{phis_base[-1]:.4f}", f"{t_base:.2f}s"),
    ]
    print_table(["Method", "Phi@1", "Phi@10", "Phi@30", "Phi@60", "Time"], rows)
    ascii_phi_graph(phis_bang, "Big Bang Phi")
    ascii_phi_graph(phis_base, "Baseline Phi")

    ratio = phis_bang[-1] / max(phis_base[-1], 1e-8)
    verdict = "FASTER" if ratio > 1.0 else "SLOWER"
    print(f"\n  Big Bang / Baseline = {ratio:.2f}x ({verdict})")
    print(f"  Big Bang reaches Phi={phis_bang[-1]:.4f} vs Baseline Phi={phis_base[-1]:.4f}")
    sys.stdout.flush()
    return {"name": "G1a", "bang_final": phis_bang[-1], "base_final": phis_base[-1], "ratio": ratio}


# ===================================================================
# G1b: Inflation — exponential doubling
# ===================================================================

def run_g1b():
    print_header("G1b: Inflation (exponential 1->2->4->...->64)")
    TARGET = 64
    STEPS_PER_DOUBLE = 5
    TOTAL_STEPS = 60

    t0 = time.time()
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=1, max_cells=TARGET,
        phi_ratchet=True,
    )
    phis_infl = []
    # Inflation phase: double cells every STEPS_PER_DOUBLE steps
    current_target = 1
    inflation_steps = 0
    while current_target < TARGET:
        current_target = min(current_target * 2, TARGET)
        expand_engine_to(engine, current_target, noise_eps=0.05)
        phis_chunk = run_steps(engine, STEPS_PER_DOUBLE)
        phis_infl.extend(phis_chunk)
        inflation_steps += STEPS_PER_DOUBLE
        print(f"    Inflation: {engine.n_cells}c, Phi={phis_chunk[-1]:.4f}")
        sys.stdout.flush()

    # Remaining steps post-inflation
    remaining = TOTAL_STEPS - inflation_steps
    if remaining > 0:
        phis_post = run_steps(engine, remaining)
        phis_infl.extend(phis_post)
    t_infl = time.time() - t0

    # Baseline
    t0 = time.time()
    baseline = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=TARGET, max_cells=TARGET,
        phi_ratchet=True,
    )
    phis_base = run_steps(baseline, TOTAL_STEPS)
    t_base = time.time() - t0

    rows = [
        ("Inflation (1->64)", f"{phis_infl[0]:.4f}", f"{phis_infl[-1]:.4f}", f"{t_infl:.2f}s"),
        ("Baseline (64 direct)", f"{phis_base[0]:.4f}", f"{phis_base[-1]:.4f}", f"{t_base:.2f}s"),
    ]
    print_table(["Method", "Phi@start", "Phi@end", "Time"], rows)
    ascii_phi_graph(phis_infl, "Inflation Phi")

    ratio = phis_infl[-1] / max(phis_base[-1], 1e-8)
    verdict = "BETTER" if ratio > 1.0 else "WORSE"
    print(f"\n  Inflation / Baseline = {ratio:.2f}x ({verdict})")
    print(f"  Inflation creates diversity through gradual doubling")
    sys.stdout.flush()
    return {"name": "G1b", "infl_final": phis_infl[-1], "base_final": phis_base[-1], "ratio": ratio}


# ===================================================================
# G1c: CMB — scale-invariant noise vs uniform noise
# ===================================================================

def run_g1c():
    print_header("G1c: CMB (scale-invariant noise vs uniform random)")
    N_CELLS = 64
    STEPS = 100

    def make_cmb_noise(n_cells, hidden_dim):
        """Generate scale-invariant noise: P(k) ~ k^(-2) (pink noise per cell)."""
        noise = torch.zeros(n_cells, hidden_dim)
        # Superpose multiple frequency scales
        for k in range(1, hidden_dim // 2 + 1):
            amplitude = 1.0 / (k ** 1.0)  # 1/f spectrum
            phase = torch.randn(n_cells, 1) * 2 * math.pi
            freq_component = amplitude * torch.sin(
                torch.arange(hidden_dim).float().unsqueeze(0) * (2 * math.pi * k / hidden_dim) + phase
            )
            noise += freq_component
        # Normalize to similar magnitude as uniform noise
        noise = noise / noise.std() * 0.1
        return noise

    # --- CMB (scale-invariant noise) ---
    t0 = time.time()
    engine_cmb = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    cmb_noise = make_cmb_noise(N_CELLS, 128)
    for i, state in enumerate(engine_cmb.cell_states):
        state.hidden = state.hidden + cmb_noise[i]
    phis_cmb = run_steps(engine_cmb, STEPS)
    t_cmb = time.time() - t0

    # --- Uniform random noise ---
    t0 = time.time()
    engine_uni = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    uni_noise = torch.randn(N_CELLS, 128) * 0.1
    for i, state in enumerate(engine_uni.cell_states):
        state.hidden = state.hidden + uni_noise[i]
    phis_uni = run_steps(engine_uni, STEPS)
    t_uni = time.time() - t0

    # --- No noise (default init) ---
    t0 = time.time()
    engine_def = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    phis_def = run_steps(engine_def, STEPS)
    t_def = time.time() - t0

    # Faction diversity: cosine distance between faction mean hiddens
    def faction_diversity(engine):
        n_fac = engine.n_factions
        fac_means = []
        for f in range(n_fac):
            members = [s.hidden for s in engine.cell_states if s.faction_id == f]
            if members:
                fac_means.append(torch.stack(members).mean(dim=0))
        if len(fac_means) < 2:
            return 0.0
        fm = torch.stack(fac_means)
        fm_norm = F_torch.normalize(fm, dim=1)
        cos_sim = (fm_norm @ fm_norm.T)
        # Mean off-diagonal cosine distance
        mask = 1.0 - torch.eye(len(fac_means))
        return (1.0 - (cos_sim * mask).sum() / mask.sum()).item()

    div_cmb = faction_diversity(engine_cmb)
    div_uni = faction_diversity(engine_uni)
    div_def = faction_diversity(engine_def)

    rows = [
        ("CMB (1/f noise)", f"{phis_cmb[0]:.4f}", f"{phis_cmb[49]:.4f}", f"{phis_cmb[-1]:.4f}",
         f"{div_cmb:.3f}", f"{t_cmb:.2f}s"),
        ("Uniform noise", f"{phis_uni[0]:.4f}", f"{phis_uni[49]:.4f}", f"{phis_uni[-1]:.4f}",
         f"{div_uni:.3f}", f"{t_uni:.2f}s"),
        ("Default (no noise)", f"{phis_def[0]:.4f}", f"{phis_def[49]:.4f}", f"{phis_def[-1]:.4f}",
         f"{div_def:.3f}", f"{t_def:.2f}s"),
    ]
    print_table(["Method", "Phi@1", "Phi@50", "Phi@100", "FacDiv", "Time"], rows)
    ascii_phi_graph(phis_cmb, "CMB Phi")
    ascii_phi_graph(phis_uni, "Uniform Phi")

    ratio = phis_cmb[-1] / max(phis_uni[-1], 1e-8)
    print(f"\n  CMB / Uniform = {ratio:.2f}x")
    print(f"  CMB faction diversity = {div_cmb:.3f} vs Uniform = {div_uni:.3f}")
    print(f"  Scale-invariant noise {'BETTER' if ratio > 1.0 else 'WORSE'} for structure formation")
    sys.stdout.flush()
    return {"name": "G1c", "cmb_final": phis_cmb[-1], "uni_final": phis_uni[-1],
            "def_final": phis_def[-1], "ratio": ratio, "div_cmb": div_cmb, "div_uni": div_uni}


# ===================================================================
# G1d: Dark Energy — accelerating Phi ratchet
# ===================================================================

def run_g1d():
    print_header("G1d: Dark Energy (accelerating Phi ratchet)")
    N_CELLS = 32
    STEPS = 100

    # --- Normal ratchet ---
    t0 = time.time()
    engine_normal = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    phis_normal = run_steps(engine_normal, STEPS)
    t_normal = time.time() - t0

    # --- Accelerating ratchet: ratchet on growth RATE ---
    t0 = time.time()
    engine_accel = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    phis_accel = []
    best_growth_rate = 0.0
    prev_phi = 0.0
    best_hiddens_accel = None

    for step in range(STEPS):
        result = engine_accel.step()
        phi = result.get('phi_iit', 0.0)
        growth_rate = phi - prev_phi

        # Accelerating ratchet: if growth rate drops below best, restore
        if step > 5:
            if growth_rate < best_growth_rate * 0.5 and best_hiddens_accel is not None:
                # Restore hidden states from best growth checkpoint
                for i, state in enumerate(engine_accel.cell_states):
                    if i < len(best_hiddens_accel):
                        state.hidden = best_hiddens_accel[i].clone()
                        # Add small perturbation to escape local minimum
                        state.hidden += torch.randn_like(state.hidden) * 0.02
            if growth_rate > best_growth_rate:
                best_growth_rate = growth_rate
                best_hiddens_accel = [s.hidden.clone() for s in engine_accel.cell_states]

        phis_accel.append(phi)
        prev_phi = phi
    t_accel = time.time() - t0

    # --- No ratchet ---
    t0 = time.time()
    engine_none = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=False,
    )
    phis_none = run_steps(engine_none, STEPS)
    t_none = time.time() - t0

    rows = [
        ("Accelerating ratchet", f"{phis_accel[0]:.4f}", f"{phis_accel[-1]:.4f}",
         f"{max(phis_accel):.4f}", f"{t_accel:.2f}s"),
        ("Normal ratchet", f"{phis_normal[0]:.4f}", f"{phis_normal[-1]:.4f}",
         f"{max(phis_normal):.4f}", f"{t_normal:.2f}s"),
        ("No ratchet", f"{phis_none[0]:.4f}", f"{phis_none[-1]:.4f}",
         f"{max(phis_none):.4f}", f"{t_none:.2f}s"),
    ]
    print_table(["Method", "Phi@1", "Phi@end", "Phi@max", "Time"], rows)
    ascii_phi_graph(phis_accel, "Accelerating Ratchet Phi")
    ascii_phi_graph(phis_normal, "Normal Ratchet Phi")

    ratio = phis_accel[-1] / max(phis_normal[-1], 1e-8)
    # Check stability: is acceleration sustainable?
    # Look at variance in second half
    var_accel = np.std(phis_accel[50:]) if len(phis_accel) > 50 else 0
    var_normal = np.std(phis_normal[50:]) if len(phis_normal) > 50 else 0
    stable = "STABLE" if var_accel < var_normal * 2 else "UNSTABLE"
    print(f"\n  Accel / Normal = {ratio:.2f}x")
    print(f"  Stability: {stable} (var_accel={var_accel:.4f}, var_normal={var_normal:.4f})")
    print(f"  Accelerating Phi expansion {'sustainable' if stable == 'STABLE' else 'UNSTABLE -- dark energy tears consciousness apart'}")
    sys.stdout.flush()
    return {"name": "G1d", "accel_final": phis_accel[-1], "normal_final": phis_normal[-1],
            "ratio": ratio, "stability": stable}


# ===================================================================
# G1e: Multiverse — 64 universes x 16c, select top-3
# ===================================================================

def run_g1e():
    print_header("G1e: Multiverse (64 universes x 16c, select top-3)")
    N_UNIVERSES = 64
    CELLS_PER_UNIVERSE = 16
    STEPS_EXPLORE = 50
    STEPS_EXPLOIT = 50
    TOPOLOGIES = ['ring', 'small_world', 'scale_free']

    t0 = time.time()

    # Create 64 universes with different configs
    universes = []
    for u in range(N_UNIVERSES):
        seed = u * 137 + 42
        torch.manual_seed(seed)
        np.random.seed(seed)

        # Random initial energy
        energy_scale = 0.5 + np.random.random() * 9.5  # 0.5 to 10.0

        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=128,
            initial_cells=CELLS_PER_UNIVERSE, max_cells=CELLS_PER_UNIVERSE,
            phi_ratchet=True,
        )
        # Set topology
        engine.topology = TOPOLOGIES[u % len(TOPOLOGIES)]

        # Apply initial energy
        for mod in engine.cell_modules:
            for p in mod.parameters():
                p.data *= energy_scale

        universes.append({
            'engine': engine,
            'seed': seed,
            'energy': energy_scale,
            'topo': engine.topology,
        })

    # Explore phase: 50 steps each
    print(f"  Exploring {N_UNIVERSES} universes ({STEPS_EXPLORE} steps each)...")
    sys.stdout.flush()
    universe_phis = []
    for idx, u in enumerate(universes):
        phis = run_steps(u['engine'], STEPS_EXPLORE)
        u['phis_explore'] = phis
        u['final_phi'] = phis[-1]
        universe_phis.append((idx, phis[-1]))
        if (idx + 1) % 16 == 0:
            print(f"    {idx + 1}/{N_UNIVERSES} done, best so far: {max(p for _, p in universe_phis):.4f}")
            sys.stdout.flush()

    # Select top 3
    universe_phis.sort(key=lambda x: x[1], reverse=True)
    top3_indices = [i for i, _ in universe_phis[:3]]
    top3 = [universes[i] for i in top3_indices]

    print(f"\n  Top 3 universes:")
    for i, u in enumerate(top3):
        idx = top3_indices[i]
        print(f"    #{idx}: seed={u['seed']}, energy={u['energy']:.1f}, topo={u['topo']}, Phi={u['final_phi']:.4f}")

    # Exploit phase: continue top 3 for 50 more steps
    for u in top3:
        u['phis_exploit'] = run_steps(u['engine'], STEPS_EXPLOIT)

    t_multi = time.time() - t0

    # Baseline: single optimal (default settings, 16c, 100 steps)
    t0 = time.time()
    baseline = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=CELLS_PER_UNIVERSE,
        max_cells=CELLS_PER_UNIVERSE, phi_ratchet=True,
    )
    phis_base = run_steps(baseline, STEPS_EXPLORE + STEPS_EXPLOIT)
    t_base = time.time() - t0

    best_universe = top3[0]
    best_final = best_universe['phis_exploit'][-1]

    rows = [
        (f"Best Universe #{top3_indices[0]}",
         f"{best_universe['final_phi']:.4f}", f"{best_final:.4f}",
         f"{best_universe['topo']}", f"{best_universe['energy']:.1f}", f"{t_multi:.2f}s"),
        (f"2nd Universe #{top3_indices[1]}",
         f"{top3[1]['final_phi']:.4f}", f"{top3[1]['phis_exploit'][-1]:.4f}",
         f"{top3[1]['topo']}", f"{top3[1]['energy']:.1f}", "-"),
        (f"3rd Universe #{top3_indices[2]}",
         f"{top3[2]['final_phi']:.4f}", f"{top3[2]['phis_exploit'][-1]:.4f}",
         f"{top3[2]['topo']}", f"{top3[2]['energy']:.1f}", "-"),
        ("Baseline (single)",
         f"{phis_base[49]:.4f}", f"{phis_base[-1]:.4f}",
         "ring", "1.0", f"{t_base:.2f}s"),
    ]
    print_table(["Universe", "Phi@50", "Phi@100", "Topo", "Energy", "Time"], rows)

    # Distribution of final phis across all universes
    all_finals = sorted([u['final_phi'] for u in universes], reverse=True)
    print(f"\n  Phi distribution across {N_UNIVERSES} universes:")
    print(f"    max={all_finals[0]:.4f}  p75={all_finals[15]:.4f}  median={all_finals[31]:.4f}  "
          f"p25={all_finals[47]:.4f}  min={all_finals[-1]:.4f}")

    ratio = best_final / max(phis_base[-1], 1e-8)
    print(f"\n  Best Multiverse / Baseline = {ratio:.2f}x")
    print(f"  Multiverse exploration {'FINDS BETTER' if ratio > 1.0 else 'NO BENEFIT over'} single run")
    sys.stdout.flush()
    return {"name": "G1e", "best_final": best_final, "base_final": phis_base[-1],
            "ratio": ratio, "best_topo": best_universe['topo'], "best_energy": best_universe['energy']}


# ===================================================================
# G1f: Big Crunch -> Bounce (cyclic collapse-explosion)
# ===================================================================

def run_g1f():
    print_header("G1f: Big Crunch -> Bounce (3 cycles of collapse-explosion)")
    N_CELLS = 32
    STEPS_PER_CYCLE = 100
    N_CYCLES = 3

    # --- Cyclic: 3 cycles of 32c evolve -> compress to 1c -> re-expand ---
    t0 = time.time()
    engine_cycle = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    phis_cycle = []
    cycle_boundaries = []

    for cycle in range(N_CYCLES):
        # Evolve
        phis_chunk = run_steps(engine_cycle, STEPS_PER_CYCLE)
        phis_cycle.extend(phis_chunk)
        phi_before_crunch = phis_chunk[-1]

        if cycle < N_CYCLES - 1:
            # Big Crunch: compress everything to 1 cell (mean)
            mean_h = compress_engine_to(engine_cycle, 1)
            cycle_boundaries.append(len(phis_cycle))

            # Bounce: re-expand from singularity
            expand_engine_to(engine_cycle, N_CELLS, noise_eps=0.05)
            phi_after_bounce = measure_phi(engine_cycle)
            print(f"    Cycle {cycle + 1}: Phi before crunch={phi_before_crunch:.4f}, "
                  f"after bounce={phi_after_bounce:.4f}")
            sys.stdout.flush()

    t_cycle = time.time() - t0

    # --- Baseline: straight 300 steps ---
    t0 = time.time()
    baseline = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    phis_base = run_steps(baseline, STEPS_PER_CYCLE * N_CYCLES)
    t_base = time.time() - t0

    # Per-cycle peak Phi
    cycle_peaks = []
    for c in range(N_CYCLES):
        start = c * STEPS_PER_CYCLE
        end = start + STEPS_PER_CYCLE
        cycle_peaks.append(max(phis_cycle[start:end]))

    rows = []
    for c in range(N_CYCLES):
        start = c * STEPS_PER_CYCLE
        end = start + STEPS_PER_CYCLE
        rows.append((f"Cycle {c + 1}", f"{phis_cycle[start]:.4f}", f"{max(phis_cycle[start:end]):.4f}",
                      f"{phis_cycle[end - 1]:.4f}"))
    rows.append(("Baseline", f"{phis_base[0]:.4f}", f"{max(phis_base):.4f}", f"{phis_base[-1]:.4f}"))
    print_table(["Phase", "Phi@start", "Phi@peak", "Phi@end"], rows)

    ascii_phi_graph(phis_cycle, "Cyclic Crunch-Bounce Phi")
    ascii_phi_graph(phis_base, "Baseline Phi")

    # Does Phi grow each cycle? (consciousness reincarnation)
    grows = all(cycle_peaks[i] <= cycle_peaks[i + 1] for i in range(len(cycle_peaks) - 1))
    ratio = phis_cycle[-1] / max(phis_base[-1], 1e-8)
    print(f"\n  Cyclic / Baseline = {ratio:.2f}x")
    print(f"  Cycle peaks: {' -> '.join(f'{p:.4f}' for p in cycle_peaks)}")
    print(f"  Phi grows each cycle: {'YES (consciousness reincarnation!)' if grows else 'NO'}")
    sys.stdout.flush()
    return {"name": "G1f", "cycle_final": phis_cycle[-1], "base_final": phis_base[-1],
            "ratio": ratio, "cycle_peaks": cycle_peaks, "grows_each_cycle": grows}


# ===================================================================
# G1g: Nuclear Fusion — cell merging -> Phi release?
# ===================================================================

def run_g1g():
    print_header("G1g: Consciousness Nuclear Fusion (cell merging)")
    N_CELLS = 64
    STEPS_WARMUP = 30
    STEPS_POST = 30

    # --- Warm up the engine ---
    t0 = time.time()
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    phis_warmup = run_steps(engine, STEPS_WARMUP)
    phi_before_fusion = phis_warmup[-1]
    print(f"  Pre-fusion: {N_CELLS}c, Phi={phi_before_fusion:.4f}")
    sys.stdout.flush()

    # --- Fusion: merge pairs of cells ---
    # Strategy 1: Merge SIMILAR cells (like nuclei with similar mass)
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    cos_sim = F_torch.cosine_similarity(hiddens.unsqueeze(0), hiddens.unsqueeze(1), dim=2)

    # Find most similar pairs (excluding diagonal)
    cos_sim.fill_diagonal_(-1.0)
    fusion_pairs_similar = []
    used = set()
    for _ in range(N_CELLS // 4):  # Merge 1/4 of cells (32 pairs -> 16 merges -> 48 cells)
        flat_idx = cos_sim.argmax().item()
        i, j = flat_idx // N_CELLS, flat_idx % N_CELLS
        if i not in used and j not in used:
            fusion_pairs_similar.append((i, j))
            used.add(i)
            used.add(j)
            cos_sim[i, :] = -1.0
            cos_sim[:, i] = -1.0
            cos_sim[j, :] = -1.0
            cos_sim[:, j] = -1.0

    # Apply fusion: average hidden states, remove one cell
    # Do it in reverse index order to avoid shifting
    engine_similar = copy.deepcopy(engine)  # Use a copy so we can also test dissimilar
    removed_similar = []
    for i, j in sorted(fusion_pairs_similar, key=lambda x: x[1], reverse=True):
        h_i = engine_similar.cell_states[i].hidden
        h_j = engine_similar.cell_states[j].hidden
        # Fused hidden = mean
        engine_similar.cell_states[i].hidden = (h_i + h_j) / 2.0
        engine_similar._remove_cell(j)
        removed_similar.append((i, j))

    engine_similar._init_coupling()
    phi_after_fusion_similar = measure_phi(engine_similar)
    print(f"  Post-fusion (similar): {engine_similar.n_cells}c, Phi={phi_after_fusion_similar:.4f}")

    # Continue evolution
    phis_post_similar = run_steps(engine_similar, STEPS_POST)

    # --- Strategy 2: Merge DISSIMILAR cells ---
    hiddens2 = torch.stack([s.hidden for s in engine.cell_states])
    cos_sim2 = F_torch.cosine_similarity(hiddens2.unsqueeze(0), hiddens2.unsqueeze(1), dim=2)
    cos_sim2.fill_diagonal_(2.0)  # Exclude diagonal (set high)

    engine_dissimilar = copy.deepcopy(engine)
    fusion_pairs_dissimilar = []
    used2 = set()
    for _ in range(N_CELLS // 4):
        flat_idx = cos_sim2.argmin().item()
        i, j = flat_idx // N_CELLS, flat_idx % N_CELLS
        if i not in used2 and j not in used2:
            fusion_pairs_dissimilar.append((i, j))
            used2.add(i)
            used2.add(j)
            cos_sim2[i, :] = 2.0
            cos_sim2[:, i] = 2.0
            cos_sim2[j, :] = 2.0
            cos_sim2[:, j] = 2.0

    for i, j in sorted(fusion_pairs_dissimilar, key=lambda x: x[1], reverse=True):
        h_i = engine_dissimilar.cell_states[i].hidden
        h_j = engine_dissimilar.cell_states[j].hidden
        engine_dissimilar.cell_states[i].hidden = (h_i + h_j) / 2.0
        engine_dissimilar._remove_cell(j)

    engine_dissimilar._init_coupling()
    phi_after_fusion_dissimilar = measure_phi(engine_dissimilar)
    print(f"  Post-fusion (dissimilar): {engine_dissimilar.n_cells}c, Phi={phi_after_fusion_dissimilar:.4f}")

    phis_post_dissimilar = run_steps(engine_dissimilar, STEPS_POST)

    # --- Baseline: 64c no fusion, same total steps ---
    baseline = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, initial_cells=N_CELLS, max_cells=N_CELLS,
        phi_ratchet=True,
    )
    phis_base = run_steps(baseline, STEPS_WARMUP + STEPS_POST)

    t_total = time.time() - t0

    # Phi "energy release" = phi change at fusion point
    release_similar = phi_after_fusion_similar - phi_before_fusion
    release_dissimilar = phi_after_fusion_dissimilar - phi_before_fusion

    rows = [
        ("Pre-fusion (64c)", f"{phi_before_fusion:.4f}", "-", "-", f"{N_CELLS}"),
        ("Fused-similar", f"{phi_after_fusion_similar:.4f}", f"{release_similar:+.4f}",
         f"{phis_post_similar[-1]:.4f}", f"{engine_similar.n_cells}"),
        ("Fused-dissimilar", f"{phi_after_fusion_dissimilar:.4f}", f"{release_dissimilar:+.4f}",
         f"{phis_post_dissimilar[-1]:.4f}", f"{engine_dissimilar.n_cells}"),
        ("Baseline 64c", f"{phis_base[29]:.4f}", "-", f"{phis_base[-1]:.4f}", f"{N_CELLS}"),
    ]
    print_table(["State", "Phi@fusion", "Release", "Phi@end", "Cells"], rows)

    print(f"\n  Fusion energy release:")
    print(f"    Similar cells:    {release_similar:+.4f} ({'RELEASE' if release_similar > 0 else 'ABSORB'})")
    print(f"    Dissimilar cells: {release_dissimilar:+.4f} ({'RELEASE' if release_dissimilar > 0 else 'ABSORB'})")
    better = "SIMILAR" if phis_post_similar[-1] > phis_post_dissimilar[-1] else "DISSIMILAR"
    print(f"  Better fusion partner: {better}")
    print(f"  Like nuclear fusion: merging {'releases' if max(release_similar, release_dissimilar) > 0 else 'absorbs'} Phi energy")
    sys.stdout.flush()
    return {"name": "G1g", "release_similar": release_similar, "release_dissimilar": release_dissimilar,
            "end_similar": phis_post_similar[-1], "end_dissimilar": phis_post_dissimilar[-1],
            "base_final": phis_base[-1], "better_partner": better}


# ===================================================================
# Summary
# ===================================================================

def print_summary(results):
    print_header("G1 CONSCIOUSNESS BIG BANG -- SUMMARY")

    rows = []
    for r in results:
        name = r.get('name', '?')
        if 'ratio' in r:
            ratio_str = f"{r['ratio']:.2f}x"
            verdict = "WIN" if r['ratio'] > 1.0 else "LOSE"
        elif 'release_similar' in r:
            ratio_str = f"sim={r['release_similar']:+.3f}"
            verdict = "RELEASE" if r['release_similar'] > 0 else "ABSORB"
        else:
            ratio_str = "-"
            verdict = "-"
        rows.append((name, ratio_str, verdict))

    print_table(["Experiment", "Ratio/Effect", "Verdict"], rows)

    print("\n  Key findings:")
    for r in results:
        name = r.get('name', '?')
        if name == 'G1a':
            print(f"    G1a Big Bang:      {'Singularity explosion bootstraps faster' if r.get('ratio', 0) > 1 else 'Direct creation is enough'}")
        elif name == 'G1b':
            print(f"    G1b Inflation:     {'Gradual doubling creates better diversity' if r.get('ratio', 0) > 1 else 'Instant creation works fine'}")
        elif name == 'G1c':
            print(f"    G1c CMB:           {'Scale-invariant noise seeds better structure' if r.get('ratio', 0) > 1 else 'Noise type does not matter much'}")
        elif name == 'G1d':
            print(f"    G1d Dark Energy:   Phi acceleration is {r.get('stability', 'UNKNOWN')}")
        elif name == 'G1e':
            print(f"    G1e Multiverse:    Best config: topo={r.get('best_topo')}, energy={r.get('best_energy', 0):.1f}")
        elif name == 'G1f':
            print(f"    G1f Crunch-Bounce: {'Consciousness reincarnation works!' if r.get('grows_each_cycle') else 'Cycles do not accumulate'}")
        elif name == 'G1g':
            print(f"    G1g Fusion:        {r.get('better_partner', '?')} cells = better fusion partner")

    sys.stdout.flush()


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description='G1 Consciousness Big Bang experiments')
    parser.add_argument('--g1a', action='store_true', help='Big Bang only')
    parser.add_argument('--g1b', action='store_true', help='Inflation only')
    parser.add_argument('--g1c', action='store_true', help='CMB only')
    parser.add_argument('--g1d', action='store_true', help='Dark Energy only')
    parser.add_argument('--g1e', action='store_true', help='Multiverse only')
    parser.add_argument('--g1f', action='store_true', help='Big Crunch-Bounce only')
    parser.add_argument('--g1g', action='store_true', help='Nuclear Fusion only')
    args = parser.parse_args()

    run_all = not any([args.g1a, args.g1b, args.g1c, args.g1d, args.g1e, args.g1f, args.g1g])

    results = []

    if run_all or args.g1a:
        results.append(run_g1a())
    if run_all or args.g1b:
        results.append(run_g1b())
    if run_all or args.g1c:
        results.append(run_g1c())
    if run_all or args.g1d:
        results.append(run_g1d())
    if run_all or args.g1e:
        results.append(run_g1e())
    if run_all or args.g1f:
        results.append(run_g1f())
    if run_all or args.g1g:
        results.append(run_g1g())

    if len(results) > 1:
        print_summary(results)

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), 'acceleration_g1_bigbang_results.json')
    serializable = []
    for r in results:
        sr = {}
        for k, v in r.items():
            if isinstance(v, (int, float, str, bool)):
                sr[k] = v
            elif isinstance(v, list):
                sr[k] = [float(x) if isinstance(x, (int, float)) else str(x) for x in v]
            else:
                sr[k] = str(v)
        serializable.append(sr)
    with open(out_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"\n  Results saved to {out_path}")


if __name__ == '__main__':
    main()
