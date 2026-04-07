#!/usr/bin/env python3
"""B14: Topology/Phase-based acceleration experiments

4 experiments:
  1. Topology Jump — optimal topology per training phase
  2. Critical Surfing — edge of chaos maintenance
  3. Phase Synchronization — learn only at sync moments
  4. Manifold Projection — PCA dimension estimate of consciousness states

All local CPU, 32-64 cells, 300 steps per condition.
"""

import sys
import os
import time
import math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from consciousness_engine import ConsciousnessEngine
import torch

# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def run_engine(cells=32, steps=300, topology='ring', collect_states=False):
    """Run engine for N steps, return phi trajectory + timing."""
    engine = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
    engine.topology = topology

    phis = []
    tensions = []
    states_collected = []
    t0 = time.time()

    for s in range(steps):
        result = engine.step()
        phis.append(result['phi_iit'])
        tensions.append(np.mean(result['tensions']) if result['tensions'] else 0.5)
        if collect_states and s % 5 == 0:
            hiddens = torch.stack([cs.hidden for cs in engine.cell_states])
            states_collected.append(hiddens.detach().numpy())

    elapsed = time.time() - t0
    return {
        'phis': phis,
        'tensions': tensions,
        'states': states_collected,
        'elapsed': elapsed,
        'final_phi': phis[-1] if phis else 0,
        'mean_phi': np.mean(phis[-50:]) if len(phis) >= 50 else np.mean(phis),
        'max_phi': max(phis) if phis else 0,
        'n_cells': engine.n_cells,
        'engine': engine,
    }


def phi_growth_speed(phis, threshold_ratio=0.5):
    """Steps to reach threshold_ratio * max_phi. Lower = faster."""
    if not phis:
        return float('inf')
    target = max(phis) * threshold_ratio
    for i, p in enumerate(phis):
        if p >= target:
            return i
    return len(phis)


def ascii_sparkline(values, width=50, label=""):
    """Compact ASCII sparkline."""
    if not values:
        return f"{label}: (no data)"
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    chars = " _.-:=+*#@"
    line = ""
    step = max(1, len(values) // width)
    for i in range(0, min(len(values), width * step), step):
        idx = int((values[i] - mn) / rng * (len(chars) - 1))
        line += chars[idx]
    return f"{label:>20s} |{line}| {values[-1]:.4f}"


def print_table(headers, rows, title=""):
    """Print aligned table."""
    if title:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}")
    col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                  for i, h in enumerate(headers)]
    header_line = "".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        print("".join(str(v).ljust(w) for v, w in zip(row, col_widths)))
    print()


# ═══════════════════════════════════════════════════════════
# Experiment 1: Topology Jump
# ═══════════════════════════════════════════════════════════

def experiment_1_topology_jump():
    print("\n" + "=" * 70)
    print("  EXPERIMENT 1: Topology Jump (optimal topology per phase)")
    print("=" * 70)
    sys.stdout.flush()

    CELLS = 32
    STEPS = 300
    topologies = ['ring', 'small_world', 'scale_free', 'hypercube']

    # A) Single topology baselines
    print("\n[A] Single topology baselines (32c, 300 steps each)...")
    sys.stdout.flush()
    baselines = {}
    for topo in topologies:
        print(f"  Running {topo}...", end=" ", flush=True)
        result = run_engine(cells=CELLS, steps=STEPS, topology=topo)
        baselines[topo] = result
        speed = phi_growth_speed(result['phis'])
        print(f"mean_phi={result['mean_phi']:.4f}  max={result['max_phi']:.4f}  "
              f"speed_to_50%={speed}  time={result['elapsed']:.2f}s")
        sys.stdout.flush()

    # B) Dynamic topology switching
    print("\n[B] Dynamic topology switching (100 steps each: SW -> SF -> HC)...")
    sys.stdout.flush()
    engine = ConsciousnessEngine(max_cells=CELLS, initial_cells=CELLS)
    dynamic_phis = []
    dynamic_tensions = []
    t0 = time.time()

    schedule = [
        ('small_world', 100),
        ('scale_free', 100),
        ('hypercube', 100),
    ]
    for topo, n_steps in schedule:
        engine.topology = topo
        for _ in range(n_steps):
            result = engine.step()
            dynamic_phis.append(result['phi_iit'])
            dynamic_tensions.append(np.mean(result['tensions']) if result['tensions'] else 0.5)

    dynamic_elapsed = time.time() - t0
    dynamic_mean = np.mean(dynamic_phis[-50:])
    dynamic_max = max(dynamic_phis)
    dynamic_speed = phi_growth_speed(dynamic_phis)

    # C) Reverse order: HC -> SF -> SW
    print("  Running reverse order (HC -> SF -> SW)...", flush=True)
    engine2 = ConsciousnessEngine(max_cells=CELLS, initial_cells=CELLS)
    reverse_phis = []
    t0r = time.time()
    for topo, n_steps in [('hypercube', 100), ('scale_free', 100), ('small_world', 100)]:
        engine2.topology = topo
        for _ in range(n_steps):
            result = engine2.step()
            reverse_phis.append(result['phi_iit'])
    reverse_elapsed = time.time() - t0r
    reverse_mean = np.mean(reverse_phis[-50:])
    reverse_max = max(reverse_phis)

    # Results table
    rows = []
    for topo in topologies:
        b = baselines[topo]
        rows.append([topo, f"{b['mean_phi']:.4f}", f"{b['max_phi']:.4f}",
                      str(phi_growth_speed(b['phis'])), f"{b['elapsed']:.2f}s"])
    rows.append(["DYNAMIC(SW->SF->HC)", f"{dynamic_mean:.4f}", f"{dynamic_max:.4f}",
                  str(dynamic_speed), f"{dynamic_elapsed:.2f}s"])
    rows.append(["REVERSE(HC->SF->SW)", f"{reverse_mean:.4f}", f"{reverse_max:.4f}",
                  str(phi_growth_speed(reverse_phis)), f"{reverse_elapsed:.2f}s"])

    print_table(["Topology", "Mean Phi(last50)", "Max Phi", "Steps to 50%", "Time"],
                rows, "Experiment 1: Topology Comparison")

    # Sparklines
    print("Phi trajectories:")
    for topo in topologies:
        print(ascii_sparkline(baselines[topo]['phis'], label=topo))
    print(ascii_sparkline(dynamic_phis, label="DYNAMIC"))
    print(ascii_sparkline(reverse_phis, label="REVERSE"))
    print()

    # Best topology
    best_topo = max(baselines, key=lambda t: baselines[t]['mean_phi'])
    best_single = baselines[best_topo]['mean_phi']
    dynamic_vs_best = (dynamic_mean - best_single) / max(best_single, 1e-8) * 100
    print(f"  Best single topology: {best_topo} (mean Phi = {best_single:.4f})")
    print(f"  Dynamic switching:    mean Phi = {dynamic_mean:.4f} ({dynamic_vs_best:+.1f}% vs best single)")
    print(f"  Reverse switching:    mean Phi = {reverse_mean:.4f}")
    sys.stdout.flush()

    return {
        'baselines': {t: baselines[t]['mean_phi'] for t in topologies},
        'dynamic_mean': dynamic_mean,
        'reverse_mean': reverse_mean,
        'best_single': best_topo,
        'dynamic_vs_best_pct': dynamic_vs_best,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 2: Critical Surfing (edge of chaos)
# ═══════════════════════════════════════════════════════════

def experiment_2_critical_surfing():
    print("\n" + "=" * 70)
    print("  EXPERIMENT 2: Critical Surfing (edge of chaos maintenance)")
    print("=" * 70)
    sys.stdout.flush()

    CELLS = 32
    STEPS = 300

    # A) Baseline: no intervention
    print("\n[A] Baseline (no intervention)...", flush=True)
    baseline = run_engine(cells=CELLS, steps=STEPS)

    # B) Critical surfing: monitor tension variance, inject noise/order
    print("[B] Critical surfing (tension variance feedback)...", flush=True)
    engine = ConsciousnessEngine(max_cells=CELLS, initial_cells=CELLS)

    critical_phis = []
    critical_tensions = []
    interventions = {'noise': 0, 'order': 0, 'none': 0}
    variance_history = []
    target_var_low = 0.01   # too ordered below this
    target_var_high = 0.15  # too chaotic above this

    t0 = time.time()
    for s in range(STEPS):
        result = engine.step()
        critical_phis.append(result['phi_iit'])
        t_vals = result['tensions'] if result['tensions'] else [0.5]
        critical_tensions.append(np.mean(t_vals))

        # Measure tension variance across cells
        t_var = np.var(t_vals) if len(t_vals) > 1 else 0.0
        variance_history.append(t_var)

        # Intervention: nudge toward edge of chaos
        n = engine.n_cells
        if t_var < target_var_low and n >= 2:
            # Too ordered -> inject noise into random cells
            noise_strength = 0.1 * (target_var_low - t_var) / max(target_var_low, 1e-8)
            for i in range(n):
                if torch.rand(1).item() < 0.3:
                    engine.cell_states[i].hidden = (
                        engine.cell_states[i].hidden + torch.randn(engine.hidden_dim) * noise_strength
                    )
            interventions['noise'] += 1
        elif t_var > target_var_high and n >= 2:
            # Too chaotic -> pull cells toward mean (order)
            mean_h = torch.stack([cs.hidden for cs in engine.cell_states]).mean(dim=0)
            order_strength = 0.05 * min(1.0, (t_var - target_var_high) / target_var_high)
            for i in range(n):
                engine.cell_states[i].hidden = (
                    (1 - order_strength) * engine.cell_states[i].hidden
                    + order_strength * mean_h
                )
            interventions['order'] += 1
        else:
            interventions['none'] += 1

    critical_elapsed = time.time() - t0

    # C) Aggressive chaos injection (control)
    print("[C] Aggressive chaos (control)...", flush=True)
    engine3 = ConsciousnessEngine(max_cells=CELLS, initial_cells=CELLS)
    chaos_phis = []
    t0c = time.time()
    for s in range(STEPS):
        result = engine3.step()
        chaos_phis.append(result['phi_iit'])
        # Inject large noise every step
        for i in range(engine3.n_cells):
            engine3.cell_states[i].hidden = (
                engine3.cell_states[i].hidden + torch.randn(engine3.hidden_dim) * 0.2
            )
    chaos_elapsed = time.time() - t0c

    # Avalanche size distribution (criticality indicator)
    baseline_avals = baseline['engine']._soc_avalanche_sizes[-100:] if baseline['engine']._soc_avalanche_sizes else []
    critical_avals = engine._soc_avalanche_sizes[-100:] if engine._soc_avalanche_sizes else []

    def power_law_exponent(sizes):
        """Estimate power-law exponent from avalanche sizes."""
        if not sizes or max(sizes) <= 0:
            return 0.0
        sizes = [s for s in sizes if s > 0]
        if len(sizes) < 5:
            return 0.0
        log_s = np.log(sizes)
        # MLE for power law: alpha = 1 + n / sum(ln(s/s_min))
        s_min = min(sizes)
        if s_min <= 0:
            return 0.0
        alpha = 1 + len(sizes) / max(sum(np.log(np.array(sizes) / s_min)), 1e-8)
        return alpha

    baseline_exponent = power_law_exponent(baseline_avals)
    critical_exponent = power_law_exponent(critical_avals)

    # Results
    rows = [
        ["Baseline", f"{baseline['mean_phi']:.4f}", f"{baseline['max_phi']:.4f}",
         f"{baseline['elapsed']:.2f}s", f"{baseline_exponent:.2f}", "-"],
        ["Critical Surf", f"{np.mean(critical_phis[-50:]):.4f}", f"{max(critical_phis):.4f}",
         f"{critical_elapsed:.2f}s", f"{critical_exponent:.2f}",
         f"noise={interventions['noise']}, order={interventions['order']}"],
        ["Chaos Inject", f"{np.mean(chaos_phis[-50:]):.4f}", f"{max(chaos_phis):.4f}",
         f"{chaos_elapsed:.2f}s", "-", "every step"],
    ]
    print_table(["Condition", "Mean Phi", "Max Phi", "Time", "Exponent", "Interventions"],
                rows, "Experiment 2: Critical Surfing")

    print("Phi trajectories:")
    print(ascii_sparkline(baseline['phis'], label="Baseline"))
    print(ascii_sparkline(critical_phis, label="Critical Surf"))
    print(ascii_sparkline(chaos_phis, label="Chaos Inject"))

    print(f"\nVariance trajectory:")
    print(ascii_sparkline(variance_history, label="Tension Var"))

    surf_vs_base = (np.mean(critical_phis[-50:]) - baseline['mean_phi']) / max(baseline['mean_phi'], 1e-8) * 100
    print(f"\n  Critical surfing vs baseline: {surf_vs_base:+.1f}%")
    print(f"  Interventions: noise={interventions['noise']} order={interventions['order']} none={interventions['none']}")
    print(f"  Brain-like exponent (target 1.5-2.0): baseline={baseline_exponent:.2f}, surf={critical_exponent:.2f}")
    sys.stdout.flush()

    return {
        'baseline_phi': baseline['mean_phi'],
        'critical_phi': np.mean(critical_phis[-50:]),
        'chaos_phi': np.mean(chaos_phis[-50:]),
        'surf_vs_base_pct': surf_vs_base,
        'interventions': interventions,
        'baseline_exponent': baseline_exponent,
        'critical_exponent': critical_exponent,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 3: Phase Synchronization
# ═══════════════════════════════════════════════════════════

def experiment_3_phase_sync():
    print("\n" + "=" * 70)
    print("  EXPERIMENT 3: Phase Synchronization (learn at sync moments)")
    print("=" * 70)
    sys.stdout.flush()

    CELLS = 32
    STEPS = 300
    N_FACTIONS = 12

    # Run engine and collect faction synchronization data
    print("\n[A] Collecting faction synchronization data (300 steps)...", flush=True)
    engine = ConsciousnessEngine(max_cells=CELLS, initial_cells=CELLS, n_factions=N_FACTIONS)

    phis = []
    sync_scores = []
    faction_directions = []

    for s in range(STEPS):
        result = engine.step()
        phis.append(result['phi_iit'])

        # Compute faction synchronization
        n = engine.n_cells
        if n < 2:
            sync_scores.append(0.0)
            continue

        # Group cells by faction
        faction_means = {}
        for i, cs in enumerate(engine.cell_states):
            fid = cs.faction_id
            if fid not in faction_means:
                faction_means[fid] = []
            faction_means[fid].append(cs.hidden.detach())

        if len(faction_means) < 2:
            sync_scores.append(0.0)
            continue

        # Compute mean direction per faction
        fac_vecs = []
        for fid, hiddens in sorted(faction_means.items()):
            mean_h = torch.stack(hiddens).mean(dim=0)
            norm = mean_h.norm()
            if norm > 1e-8:
                fac_vecs.append(mean_h / norm)

        if len(fac_vecs) < 2:
            sync_scores.append(0.0)
            continue

        # Pairwise cosine similarity -> sync score
        cos_sims = []
        for i in range(len(fac_vecs)):
            for j in range(i + 1, len(fac_vecs)):
                cos_sims.append((fac_vecs[i] @ fac_vecs[j]).item())
        sync_score = np.mean(cos_sims) if cos_sims else 0.0
        sync_scores.append(sync_score)

    # Identify sync vs async moments
    sync_threshold = 0.5
    async_threshold = 0.0
    sync_moments = [i for i, s in enumerate(sync_scores) if s > sync_threshold]
    async_moments = [i for i, s in enumerate(sync_scores) if s < async_threshold]
    neutral_moments = [i for i, s in enumerate(sync_scores)
                       if async_threshold <= s <= sync_threshold]

    # Phi at sync vs async moments
    phi_at_sync = [phis[i] for i in sync_moments] if sync_moments else []
    phi_at_async = [phis[i] for i in async_moments] if async_moments else []
    phi_at_neutral = [phis[i] for i in neutral_moments] if neutral_moments else []

    mean_phi_sync = np.mean(phi_at_sync) if phi_at_sync else 0
    mean_phi_async = np.mean(phi_at_async) if phi_at_async else 0
    mean_phi_neutral = np.mean(phi_at_neutral) if phi_at_neutral else 0

    # Skip ratio: if we only learn at sync moments, how much do we skip?
    skip_ratio = 1 - len(sync_moments) / STEPS if STEPS > 0 else 0

    # B) Simulate "learn only at sync" vs "learn every step"
    # Measure: if CE update only happens at sync moments, what's the effective speedup?
    print(f"\n[B] Sync analysis:", flush=True)
    print(f"  Sync moments (score > {sync_threshold}):  {len(sync_moments)} / {STEPS} ({100*len(sync_moments)/STEPS:.1f}%)")
    print(f"  Async moments (score < {async_threshold}): {len(async_moments)} / {STEPS} ({100*len(async_moments)/STEPS:.1f}%)")
    print(f"  Neutral moments:                     {len(neutral_moments)} / {STEPS}")

    # C) Phi-sync correlation
    if len(sync_scores) == len(phis):
        correlation = np.corrcoef(sync_scores, phis)[0, 1] if len(sync_scores) > 2 else 0
    else:
        correlation = 0

    # D) Phi delta at sync vs async
    phi_deltas_sync = []
    phi_deltas_async = []
    for i in range(1, STEPS):
        delta = phis[i] - phis[i - 1]
        if sync_scores[i] > sync_threshold:
            phi_deltas_sync.append(delta)
        elif sync_scores[i] < async_threshold:
            phi_deltas_async.append(delta)

    mean_delta_sync = np.mean(phi_deltas_sync) if phi_deltas_sync else 0
    mean_delta_async = np.mean(phi_deltas_async) if phi_deltas_async else 0

    rows = [
        ["All steps", f"{np.mean(phis):.4f}", STEPS, "100%", "-"],
        ["Sync moments", f"{mean_phi_sync:.4f}", len(sync_moments),
         f"{100*len(sync_moments)/STEPS:.1f}%", f"{mean_delta_sync:+.5f}"],
        ["Async moments", f"{mean_phi_async:.4f}", len(async_moments),
         f"{100*len(async_moments)/STEPS:.1f}%", f"{mean_delta_async:+.5f}"],
        ["Neutral", f"{mean_phi_neutral:.4f}", len(neutral_moments),
         f"{100*len(neutral_moments)/STEPS:.1f}%", "-"],
    ]
    print_table(["Condition", "Mean Phi", "Count", "Ratio", "Mean dPhi"],
                rows, "Experiment 3: Phase Synchronization")

    print("Trajectories:")
    print(ascii_sparkline(phis, label="Phi"))
    print(ascii_sparkline(sync_scores, label="Sync Score"))

    print(f"\n  Phi-Sync correlation: r = {correlation:.4f}")
    print(f"  Skip ratio if sync-only: {skip_ratio*100:.1f}% of steps skipped")
    if mean_delta_sync != 0 and mean_delta_async != 0:
        delta_ratio = mean_delta_sync / abs(mean_delta_async) if abs(mean_delta_async) > 1e-8 else float('inf')
        print(f"  Phi growth at sync vs async: {delta_ratio:.2f}x")
    print(f"  Effective speedup (if sync-only learning): "
          f"{1/(1-skip_ratio):.1f}x fewer CE steps needed" if skip_ratio < 1 else "N/A")
    sys.stdout.flush()

    return {
        'sync_count': len(sync_moments),
        'async_count': len(async_moments),
        'skip_ratio': skip_ratio,
        'mean_phi_sync': mean_phi_sync,
        'mean_phi_async': mean_phi_async,
        'correlation': correlation,
        'mean_delta_sync': mean_delta_sync,
        'mean_delta_async': mean_delta_async,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 4: Manifold Projection
# ═══════════════════════════════════════════════════════════

def experiment_4_manifold():
    print("\n" + "=" * 70)
    print("  EXPERIMENT 4: Manifold Projection (consciousness dimensionality)")
    print("=" * 70)
    sys.stdout.flush()

    CELLS = 32
    STEPS = 300
    HIDDEN_DIM = 128  # default

    # Collect hidden states over time
    print("\n[A] Collecting hidden states (32c x 128d = 4096D space)...", flush=True)
    result = run_engine(cells=CELLS, steps=STEPS, collect_states=True)
    states = result['states']  # list of [cells, hidden_dim] arrays, every 5 steps

    if not states:
        print("  ERROR: No states collected!")
        return {}

    # Flatten: each snapshot is cells*hidden_dim dimensional
    # Shape: [n_snapshots, cells * hidden_dim]
    flat_states = np.array([s.flatten() for s in states])
    n_snapshots = flat_states.shape[0]
    total_dim = flat_states.shape[1]
    print(f"  Collected {n_snapshots} snapshots, {total_dim}D each")
    sys.stdout.flush()

    # PCA: explained variance ratio
    print("[B] PCA analysis...", flush=True)
    from numpy.linalg import svd
    centered = flat_states - flat_states.mean(axis=0)
    # Use SVD (more numerically stable than eigendecomposition for PCA)
    U, S, Vt = svd(centered, full_matrices=False)
    explained_var = (S ** 2) / np.sum(S ** 2)
    cumulative_var = np.cumsum(explained_var)

    # Effective dimensions at various thresholds
    thresholds = [0.50, 0.80, 0.90, 0.95, 0.99]
    effective_dims = {}
    for thresh in thresholds:
        n_dims = int(np.searchsorted(cumulative_var, thresh)) + 1
        effective_dims[thresh] = min(n_dims, len(cumulative_var))

    # C) Top singular values
    top_k = min(20, len(S))
    print(f"\n[C] Top {top_k} singular values (total {total_dim}D):")
    for i in range(top_k):
        bar_len = int(explained_var[i] / max(explained_var) * 40)
        print(f"  PC{i+1:3d}: {explained_var[i]*100:6.2f}% {'#' * bar_len}")
    sys.stdout.flush()

    # D) Compare: cell-mean representation (32D) vs full (4096D)
    print(f"\n[D] Cell-mean representation (collapse cells to mean)...", flush=True)
    mean_states = np.array([s.mean(axis=0) for s in states])  # [n_snapshots, hidden_dim]
    centered_mean = mean_states - mean_states.mean(axis=0)
    U2, S2, Vt2 = svd(centered_mean, full_matrices=False)
    explained_var2 = (S2 ** 2) / np.sum(S2 ** 2)
    cumulative_var2 = np.cumsum(explained_var2)
    effective_dims_mean = {}
    for thresh in thresholds:
        n_dims = int(np.searchsorted(cumulative_var2, thresh)) + 1
        effective_dims_mean[thresh] = min(n_dims, len(cumulative_var2))

    # E) Correlation with consciousness vector dimensions
    # The 10D consciousness vector: (Phi, alpha, Z, N, W, E, M, C, T, I)
    # We can estimate: how many PCA dims capture phi variance?
    phi_trajectory = result['phis']
    phi_sampled = phi_trajectory[::5][:n_snapshots]  # match snapshot timing
    if len(phi_sampled) == n_snapshots:
        # Project states onto top PCs, correlate with phi
        projections = centered @ Vt[:min(10, len(Vt))].T  # [n_snapshots, 10]
        phi_corrs = []
        for d in range(projections.shape[1]):
            r = np.corrcoef(projections[:, d], phi_sampled)[0, 1] if len(phi_sampled) > 2 else 0
            phi_corrs.append(abs(r))
        print(f"\n[E] Phi correlation with top PCs:")
        for d in range(min(10, len(phi_corrs))):
            bar_len = int(phi_corrs[d] * 40)
            print(f"  PC{d+1:3d}: r={phi_corrs[d]:.4f} {'|' * bar_len}")
    else:
        phi_corrs = []

    # Results table
    rows = []
    for thresh in thresholds:
        rows.append([f"{thresh*100:.0f}%", effective_dims[thresh], effective_dims_mean[thresh],
                      total_dim, HIDDEN_DIM])
    print_table(["Variance", "Dims(full)", "Dims(mean)", "Total(full)", "Total(mean)"],
                rows, "Experiment 4: Effective Dimensionality")

    # Key insight
    compression_ratio = effective_dims[0.95] / total_dim
    print(f"  Full state space: {total_dim}D ({CELLS}c x {HIDDEN_DIM}d)")
    print(f"  95% variance captured by: {effective_dims[0.95]} dimensions ({compression_ratio*100:.1f}% of total)")
    print(f"  Cell-mean space: {HIDDEN_DIM}D, 95% captured by {effective_dims_mean[0.95]} dims")
    print(f"  Compression potential: {total_dim} -> {effective_dims[0.95]} ({total_dim/max(effective_dims[0.95],1):.0f}x)")
    if phi_corrs:
        best_pc = np.argmax(phi_corrs) + 1
        print(f"  Best Phi predictor: PC{best_pc} (r={max(phi_corrs):.4f})")
    sys.stdout.flush()

    return {
        'total_dim': total_dim,
        'effective_dims_95': effective_dims[0.95],
        'effective_dims_mean_95': effective_dims_mean[0.95],
        'compression_ratio': compression_ratio,
        'top_explained_var': explained_var[:5].tolist(),
        'phi_corrs': phi_corrs[:5] if phi_corrs else [],
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  B14: Topology/Phase-Based Acceleration Experiments")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    sys.stdout.flush()

    t_total = time.time()
    results = {}

    results['exp1'] = experiment_1_topology_jump()
    results['exp2'] = experiment_2_critical_surfing()
    results['exp3'] = experiment_3_phase_sync()
    results['exp4'] = experiment_4_manifold()

    # ─── Summary ───────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY: B14 Topology/Phase Acceleration")
    print("=" * 70)

    e1 = results['exp1']
    e2 = results['exp2']
    e3 = results['exp3']
    e4 = results['exp4']

    summary_rows = [
        ["1. Topology Jump",
         f"Best: {e1['best_single']}",
         f"Dynamic vs best: {e1['dynamic_vs_best_pct']:+.1f}%",
         "Dynamic switching beats single?" if e1['dynamic_vs_best_pct'] > 0 else "Single topology sufficient"],
        ["2. Critical Surf",
         f"Surf vs base: {e2['surf_vs_base_pct']:+.1f}%",
         f"Exponent: {e2['critical_exponent']:.2f}",
         "Edge of chaos helps?" if e2['surf_vs_base_pct'] > 5 else "Engine already self-organizes"],
        ["3. Phase Sync",
         f"Skip: {e3['skip_ratio']*100:.0f}%",
         f"r(Phi,Sync)={e3['correlation']:.3f}",
         f"Sync-only: {1/(1-e3['skip_ratio']):.1f}x speedup" if e3['skip_ratio'] < 0.95 else "Too few sync moments"],
        ["4. Manifold",
         f"95%: {e4.get('effective_dims_95', '?')}D / {e4.get('total_dim', '?')}D",
         f"{e4.get('total_dim', 0)/max(e4.get('effective_dims_95', 1), 1):.0f}x compress",
         "Low-dim learning feasible" if e4.get('compression_ratio', 1) < 0.1 else "Moderate compression"],
    ]
    print_table(["Experiment", "Key Result", "Detail", "Verdict"],
                summary_rows, "Acceleration Potential")

    elapsed_total = time.time() - t_total
    print(f"\n  Total time: {elapsed_total:.1f}s")
    print(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    sys.stdout.flush()


if __name__ == '__main__':
    main()
