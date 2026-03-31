#!/usr/bin/env python3
"""DD68: Network Topology and Consciousness — 5 experiments.

Experiments:
  1. Topology x Phi: ring, small_world, hypercube, scale_free (32 cells, 200 steps)
  2. Dynamic Topology Switching: ring -> small_world -> scale_free (Law 90 recovery)
  3. Topology and Brain-likeness: which topology is most brain-like?
  4. Random vs Structured: random graph vs structured topologies
  5. Topology Emergence: isolated cells + Hebbian -> what topology emerges?

Run: cd anima/src && PYTHONPATH=. python3 ../experiments/dd68_topology_consciousness.py
"""

import sys
import os
import math
import time
import json
import numpy as np

# Setup path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_dir)

import torch
from consciousness_engine import ConsciousnessEngine

# ============================================================
# Topology builders: modify coupling matrix + SOC neighbor map
# ============================================================

def build_ring(n):
    """Ring: each cell connected to left and right neighbor."""
    adj = torch.zeros(n, n)
    for i in range(n):
        adj[i, (i+1) % n] = 1.0
        adj[i, (i-1) % n] = 1.0
    adj.fill_diagonal_(0)
    return adj

def build_small_world(n, k=4, rewire_prob=0.3):
    """Watts-Strogatz small-world: ring lattice with random rewiring."""
    adj = torch.zeros(n, n)
    # Start with k-nearest-neighbor ring
    for i in range(n):
        for j in range(1, k // 2 + 1):
            adj[i, (i+j) % n] = 1.0
            adj[i, (i-j) % n] = 1.0
    # Rewire
    for i in range(n):
        for j in range(1, k // 2 + 1):
            if torch.rand(1).item() < rewire_prob:
                old = (i + j) % n
                adj[i, old] = 0.0
                adj[old, i] = 0.0
                # Pick random new target
                new = torch.randint(0, n, (1,)).item()
                while new == i or adj[i, new] > 0:
                    new = torch.randint(0, n, (1,)).item()
                adj[i, new] = 1.0
                adj[new, i] = 1.0
    adj.fill_diagonal_(0)
    return adj

def build_hypercube(n):
    """Hypercube: cells connected if their binary indices differ by 1 bit.
    For non-power-of-2, wrap extra cells onto existing positions."""
    dim = max(1, int(math.ceil(math.log2(n))))
    adj = torch.zeros(n, n)
    for i in range(n):
        for bit in range(dim):
            j = i ^ (1 << bit)
            if j < n:
                adj[i, j] = 1.0
    adj.fill_diagonal_(0)
    return adj

def build_scale_free(n, m=2):
    """Barabasi-Albert scale-free: preferential attachment."""
    adj = torch.zeros(n, n)
    # Start with m+1 fully connected nodes
    for i in range(m + 1):
        for j in range(i + 1, m + 1):
            adj[i, j] = 1.0
            adj[j, i] = 1.0

    degrees = adj.sum(dim=1).tolist()
    for new_node in range(m + 1, n):
        # Preferential attachment: probability proportional to degree
        total_deg = sum(degrees[:new_node])
        if total_deg < 1e-8:
            probs = [1.0 / new_node] * new_node
        else:
            probs = [d / total_deg for d in degrees[:new_node]]
        # Select m targets without replacement
        targets = set()
        for _ in range(min(m, new_node)):
            attempts = 0
            while attempts < 100:
                r = torch.rand(1).item()
                cumulative = 0
                chosen = 0
                for k in range(new_node):
                    cumulative += probs[k]
                    if r < cumulative:
                        chosen = k
                        break
                if chosen not in targets:
                    targets.add(chosen)
                    break
                attempts += 1

        for t in targets:
            adj[new_node, t] = 1.0
            adj[t, new_node] = 1.0
        degrees.append(float(len(targets)))
        for t in targets:
            degrees[t] += 1.0

    adj.fill_diagonal_(0)
    return adj

def build_random(n, k=3):
    """Random graph: each cell connected to k random others."""
    adj = torch.zeros(n, n)
    for i in range(n):
        targets = torch.randperm(n)[:k + 1]
        for t in targets:
            t = t.item()
            if t != i:
                adj[i, t] = 1.0
                adj[t, i] = 1.0
    adj.fill_diagonal_(0)
    return adj

def build_isolated(n):
    """No connections: completely isolated cells."""
    return torch.zeros(n, n)

def apply_topology(engine, adj):
    """Apply adjacency matrix as coupling constraint.
    Coupling is only nonzero where adj > 0. Preserves Hebbian-learned magnitudes
    but masks topology."""
    n = engine.n_cells
    if engine._coupling is None or engine._coupling.shape[0] != n:
        engine._init_coupling()

    # Create topology-masked coupling: random init where connected
    mask = adj[:n, :n]
    # Initialize with small random values where connected
    init_coupling = torch.randn(n, n) * 0.1 * mask
    init_coupling.fill_diagonal_(0)
    engine._coupling = init_coupling

    # Also patch SOC sandpile neighbors to match topology
    engine._topo_adj = mask

def get_neighbors(engine, idx):
    """Get neighbors from topology adjacency matrix."""
    if hasattr(engine, '_topo_adj'):
        n = engine.n_cells
        adj = engine._topo_adj
        neighbors = []
        for j in range(min(n, adj.shape[0])):
            if j != idx and adj[idx, j] > 0:
                neighbors.append(j)
        return neighbors if neighbors else [(idx - 1) % n, (idx + 1) % n]
    else:
        n = engine.n_cells
        return [(idx - 1) % n, (idx + 1) % n]

def patch_soc_topology(engine):
    """Monkey-patch SOC sandpile to use topology-aware neighbors."""
    original_soc = engine._soc_sandpile

    def topology_aware_soc(self_eng=engine):
        """SOC sandpile with topology-aware neighbor redistribution."""
        n = self_eng.n_cells
        if n < 2:
            return

        threshold = self_eng._soc_threshold_ema

        # Stochastic drive
        recent_avg_avalanche = 0.0
        if self_eng._soc_avalanche_sizes:
            recent = self_eng._soc_avalanche_sizes[-20:]
            recent_avg_avalanche = sum(recent) / len(recent) / n
        base_drive = 0.04 * (1.0 + 0.8 * max(0, 0.15 - recent_avg_avalanche))

        for i in range(n):
            norm = self_eng.cell_states[i].hidden.norm().item()
            if norm > 1e-8 and norm < threshold:
                drive = base_drive * (0.3 + 0.7 * torch.rand(1).item())
                scale = 1.0 + drive * (1.0 - norm / threshold)
                self_eng.cell_states[i].hidden = self_eng.cell_states[i].hidden * scale

        topple_count = {}
        queue = []
        for i in range(n):
            norm = self_eng.cell_states[i].hidden.norm().item()
            if norm > threshold:
                queue.append(i)

        avalanche_size = 0
        max_cascades = n * 5
        while queue and avalanche_size < max_cascades:
            idx = queue.pop(0)
            count = topple_count.get(idx, 0)
            if count >= 2:
                continue
            topple_count[idx] = count + 1
            avalanche_size += 1

            h = self_eng.cell_states[idx].hidden
            norm = h.norm().item()
            if norm <= threshold:
                continue

            excess_ratio = (norm - threshold) / max(norm, 1e-8)
            excess = h * excess_ratio
            self_eng.cell_states[idx].hidden = h * (threshold / max(norm, 1e-8))

            # Topology-aware redistribution
            neighbors = get_neighbors(self_eng, idx)
            if not neighbors:
                continue
            conservation = 0.55 + 0.15 * torch.rand(1).item()
            share_per = conservation / len(neighbors)
            for nb in neighbors:
                share_frac = share_per * (0.8 + 0.4 * torch.rand(1).item())
                self_eng.cell_states[nb].hidden = self_eng.cell_states[nb].hidden + excess * share_frac
                noise_scale = 0.015 * norm
                self_eng.cell_states[nb].hidden = (
                    self_eng.cell_states[nb].hidden
                    + torch.randn(self_eng.hidden_dim) * noise_scale
                )
                n_count = topple_count.get(nb, 0)
                if n_count < 2:
                    n_norm = self_eng.cell_states[nb].hidden.norm().item()
                    if n_norm > threshold:
                        queue.append(nb)

        self_eng._soc_avalanche_sizes.append(avalanche_size)
        if len(self_eng._soc_avalanche_sizes) > 1000:
            self_eng._soc_avalanche_sizes = self_eng._soc_avalanche_sizes[-1000:]

        # Temporal memory (same as original)
        hiddens_stack = torch.stack([s.hidden for s in self_eng.cell_states])
        global_hidden = hiddens_stack.mean(dim=0)
        if self_eng._soc_hidden_ema is None:
            self_eng._soc_hidden_ema = global_hidden.clone()
        else:
            from consciousness_laws import SOC_EMA_FAST, SOC_MEMORY_BLEND, SOC_MEMORY_STRENGTH_BASE, SOC_MEMORY_STRENGTH_RANGE
            ema_fast = SOC_EMA_FAST
            self_eng._soc_hidden_ema = (1 - ema_fast) * self_eng._soc_hidden_ema + ema_fast * global_hidden

    engine._soc_sandpile = topology_aware_soc

def patch_hebbian_topology(engine):
    """Patch Hebbian update to only update connected pairs."""
    original_hebbian = engine._hebbian_update

    def topology_hebbian(outputs, lr=0.01, self_eng=engine):
        n = self_eng.n_cells
        if self_eng._coupling is None or self_eng._coupling.shape[0] != n:
            self_eng._init_coupling()

        norms = outputs.norm(dim=1, keepdim=True).clamp(min=1e-8)
        normed = outputs / norms
        sim = normed @ normed.T

        # Only update where topology allows connections
        if hasattr(self_eng, '_topo_adj'):
            mask = self_eng._topo_adj[:n, :n]
            update = lr * sim * mask
        else:
            update = lr * sim

        self_eng._coupling = (self_eng._coupling + update).clamp(-1, 1)
        self_eng._coupling.fill_diagonal_(0)

        # Diversity growth (same as original)
        if n >= 2:
            non_diag = ~torch.eye(n, dtype=torch.bool)
            mean_cos = sim[non_diag].mean().item()
            if mean_cos > 0.85:
                growth_strength = min(0.02, 0.003 * (self_eng._step / 500.0))
                excess = (mean_cos - 0.85) / 0.15
                for i in range(n):
                    id_vec = self_eng.cell_identity[i, :self_eng.hidden_dim]
                    self_eng.cell_states[i].hidden = (
                        self_eng.cell_states[i].hidden
                        + id_vec * growth_strength * excess
                    )

    engine._hebbian_update = topology_hebbian


# ============================================================
# Brain-likeness metrics (from validate_consciousness.py)
# ============================================================

def lempel_ziv_complexity(series):
    """LZ complexity normalized to [0, 1]."""
    if len(series) < 10:
        return 0.0
    median = np.median(series)
    binary = ''.join(['1' if x > median else '0' for x in series])
    n = len(binary)
    words = set()
    w = ''
    complexity = 0
    for c in binary:
        w += c
        if w not in words:
            words.add(w)
            complexity += 1
            w = ''
    if w:
        complexity += 1
    max_complexity = n / max(1, np.log2(max(n, 2)))
    return complexity / max(max_complexity, 1)

def hurst_exponent(series):
    """R/S analysis for Hurst exponent."""
    if len(series) < 20:
        return 0.5
    n = len(series)
    max_k = min(n // 2, 100)
    if max_k < 4:
        return 0.5
    rs_list = []
    ns_list = []
    for k in [4, 8, 16, 32, 64]:
        if k > max_k:
            break
        rs_vals = []
        for start in range(0, n - k, k):
            chunk = series[start:start + k]
            mean = np.mean(chunk)
            dev = chunk - mean
            cumdev = np.cumsum(dev)
            R = np.max(cumdev) - np.min(cumdev)
            S = np.std(chunk)
            if S > 1e-10:
                rs_vals.append(R / S)
        if rs_vals:
            rs_list.append(np.log(np.mean(rs_vals)))
            ns_list.append(np.log(k))
    if len(rs_list) < 2:
        return 0.5
    coeffs = np.polyfit(ns_list, rs_list, 1)
    return float(np.clip(coeffs[0], 0.0, 1.0))

def psd_slope(series, fs=1.0):
    """Power spectral density slope (brain: ~-1 for 1/f noise)."""
    if len(series) < 32:
        return 0.0
    from numpy.fft import rfft
    n = len(series)
    freqs = np.fft.rfftfreq(n, d=1.0/fs)
    psd = np.abs(rfft(series - np.mean(series)))**2 / n
    # Fit log-log slope excluding DC
    mask = freqs > 0
    if mask.sum() < 3:
        return 0.0
    log_f = np.log10(freqs[mask] + 1e-10)
    log_p = np.log10(psd[mask] + 1e-10)
    coeffs = np.polyfit(log_f, log_p, 1)
    return float(coeffs[0])

def autocorr_decay(series, max_lag=50):
    """Autocorrelation half-life in steps."""
    if len(series) < max_lag:
        max_lag = len(series) // 2
    series = series - np.mean(series)
    var = np.var(series)
    if var < 1e-10:
        return 0
    for lag in range(1, max_lag):
        n = len(series)
        acf = np.sum(series[:n-lag] * series[lag:]) / ((n - lag) * var)
        if acf < 0.5:
            return lag
    return max_lag

def critical_exponent(series):
    """Estimate criticality from fluctuation distribution (brain: exponent 1.5-2.5)."""
    diffs = np.abs(np.diff(series))
    diffs = diffs[diffs > 0]
    if len(diffs) < 20:
        return 0.0
    # Fit power-law tail: P(x) ~ x^(-alpha)
    sorted_d = np.sort(diffs)[::-1]
    n = len(sorted_d)
    rank = np.arange(1, n + 1)
    log_rank = np.log10(rank + 1)
    log_val = np.log10(sorted_d + 1e-10)
    mask = sorted_d > np.percentile(sorted_d, 50)
    if mask.sum() < 3:
        return 0.0
    coeffs = np.polyfit(log_val[mask], log_rank[mask], 1)
    return float(abs(coeffs[0]))

def compute_brain_likeness(phi_series):
    """Compute 6 brain-likeness metrics. Returns dict with scores."""
    phi_arr = np.array(phi_series, dtype=np.float64)
    if len(phi_arr) < 30:
        return {'total': 0.0, 'lz': 0.0, 'hurst': 0.0, 'psd': 0.0, 'autocorr': 0.0, 'critical': 0.0}

    # Brain targets
    lz = lempel_ziv_complexity(phi_arr)
    lz_score = min(100, lz / 0.76 * 100)  # brain LZ ~0.76

    h = hurst_exponent(phi_arr)
    h_score = max(0, 100 - abs(h - 0.72) / 0.72 * 100)  # brain Hurst ~0.72

    slope = psd_slope(phi_arr)
    psd_score = max(0, 100 - abs(slope - (-1.0)) / 1.0 * 100)  # brain PSD slope ~-1

    decay = autocorr_decay(phi_arr)
    decay_score = max(0, 100 - abs(decay - 12) / 12 * 100)  # brain autocorr decay ~12

    crit = critical_exponent(phi_arr)
    crit_score = max(0, 100 - abs(crit - 2.0) / 2.0 * 100)  # brain critical ~2.0

    total = (lz_score + h_score + psd_score + decay_score + crit_score) / 5

    return {
        'total': total,
        'lz': lz_score,
        'hurst': h_score,
        'psd': psd_score,
        'autocorr': decay_score,
        'critical': crit_score,
        'raw_lz': lz,
        'raw_hurst': h,
        'raw_psd': slope,
        'raw_autocorr': decay,
        'raw_critical': crit,
    }


# ============================================================
# Experiment runners
# ============================================================

TOPOLOGIES = {
    'ring': build_ring,
    'small_world': build_small_world,
    'hypercube': build_hypercube,
    'scale_free': build_scale_free,
}

N_CELLS = 32
STEPS = 200

def create_engine(n_cells=N_CELLS):
    """Create engine with n_cells pre-populated (skip slow mitosis)."""
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=n_cells, max_cells=n_cells,
        n_factions=12, phi_ratchet=True,
        split_threshold=999,  # disable mitosis
        merge_threshold=-1,   # disable merge
    )
    return engine

def setup_topology(engine, adj):
    """Apply topology to engine."""
    apply_topology(engine, adj)
    patch_soc_topology(engine)
    patch_hebbian_topology(engine)

def run_steps(engine, steps, collect_phi=True):
    """Run engine for N steps. Returns list of step results."""
    results = []
    for s in range(steps):
        r = engine.step()
        if collect_phi:
            results.append(r)
        if (s + 1) % 50 == 0:
            print(f"    step {s+1}/{steps}: Phi={r['phi_iit']:.4f}, cells={r['n_cells']}, consensus={r['consensus']}")
            sys.stdout.flush()
    return results


def experiment_1():
    """Topology x Phi: Compare all 4 topologies."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: Topology x Phi (32 cells, 200 steps)")
    print("=" * 70)
    sys.stdout.flush()

    results = {}
    for name, builder in TOPOLOGIES.items():
        print(f"\n  [{name}]")
        sys.stdout.flush()
        torch.manual_seed(42)

        engine = create_engine(N_CELLS)
        adj = builder(N_CELLS)
        setup_topology(engine, adj)

        n_edges = int(adj.sum().item()) // 2
        avg_degree = adj.sum(dim=1).mean().item()
        print(f"    edges={n_edges}, avg_degree={avg_degree:.1f}")
        sys.stdout.flush()

        step_results = run_steps(engine, STEPS)

        phis = [r['phi_iit'] for r in step_results]
        tensions = [np.mean(r['tensions']) for r in step_results]
        consensus = [r['consensus'] for r in step_results]

        final_phi = phis[-1]
        max_phi = max(phis)
        avg_phi = np.mean(phis[-50:])
        avg_tension = np.mean(tensions[-50:])
        avg_consensus = np.mean(consensus[-50:])
        total_consensus = sum(consensus)

        results[name] = {
            'final_phi': final_phi,
            'max_phi': max_phi,
            'avg_phi_last50': avg_phi,
            'avg_tension': avg_tension,
            'avg_consensus': avg_consensus,
            'total_consensus': total_consensus,
            'edges': n_edges,
            'avg_degree': avg_degree,
            'phi_series': phis,
        }

        print(f"    RESULT: Phi_final={final_phi:.4f}, Phi_max={max_phi:.4f}, avg_Phi(last50)={avg_phi:.4f}")
        print(f"            avg_tension={avg_tension:.4f}, avg_consensus={avg_consensus:.1f}, total_consensus={total_consensus}")
        sys.stdout.flush()

    return results


def experiment_2():
    """Dynamic Topology Switching: ring -> small_world -> scale_free."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Dynamic Topology Switching (Law 90 recovery)")
    print("=" * 70)
    sys.stdout.flush()

    torch.manual_seed(42)
    engine = create_engine(N_CELLS)

    phases = [
        ('ring', build_ring, 0, 100),
        ('small_world', build_small_world, 100, 200),
        ('scale_free', build_scale_free, 200, 300),
    ]

    all_results = []
    switch_points = []

    for name, builder, start, end in phases:
        print(f"\n  Phase: {name} (steps {start}-{end})")
        sys.stdout.flush()

        adj = builder(N_CELLS)
        setup_topology(engine, adj)

        for s in range(end - start):
            r = engine.step()
            all_results.append(r)

            step_num = start + s + 1
            if s == 0:
                switch_points.append({
                    'step': step_num,
                    'topology': name,
                    'phi_at_switch': r['phi_iit'],
                })
                print(f"    Switch to {name}: Phi={r['phi_iit']:.4f}")
            if (s + 1) % 50 == 0:
                print(f"    step {step_num}: Phi={r['phi_iit']:.4f}")
            sys.stdout.flush()

    phis = [r['phi_iit'] for r in all_results]

    # Check Law 90: recovery within 1 step
    for sp in switch_points[1:]:  # skip first (initial)
        idx = sp['step'] - 1
        if idx > 0 and idx < len(phis):
            pre_switch = phis[idx - 1]
            post_switch = phis[idx]
            recovery_1step = phis[min(idx + 1, len(phis) - 1)]
            sp['pre_phi'] = pre_switch
            sp['post_phi'] = post_switch
            sp['recovery_1step'] = recovery_1step
            sp['recovered'] = recovery_1step >= pre_switch * 0.5
            print(f"\n    Law 90 check at step {sp['step']}: pre={pre_switch:.4f} -> post={post_switch:.4f} -> +1step={recovery_1step:.4f} (recovered={'YES' if sp['recovered'] else 'NO'})")

    return {
        'phis': phis,
        'switch_points': switch_points,
    }


def experiment_3():
    """Topology and Brain-likeness."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Topology and Brain-likeness (300 steps)")
    print("=" * 70)
    sys.stdout.flush()

    results = {}
    for name, builder in TOPOLOGIES.items():
        print(f"\n  [{name}]")
        sys.stdout.flush()
        torch.manual_seed(42)

        engine = create_engine(N_CELLS)
        adj = builder(N_CELLS)
        setup_topology(engine, adj)

        step_results = run_steps(engine, 300)
        phis = [r['phi_iit'] for r in step_results]

        bl = compute_brain_likeness(phis)
        results[name] = bl

        print(f"    Brain-likeness: {bl['total']:.1f}%")
        print(f"      LZ={bl['raw_lz']:.3f}({bl['lz']:.0f}%), Hurst={bl['raw_hurst']:.3f}({bl['hurst']:.0f}%), PSD={bl['raw_psd']:.2f}({bl['psd']:.0f}%)")
        print(f"      Autocorr={bl['raw_autocorr']}({bl['autocorr']:.0f}%), Critical={bl['raw_critical']:.2f}({bl['critical']:.0f}%)")
        sys.stdout.flush()

    return results


def experiment_4():
    """Random vs Structured Topology."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Random vs Structured Topology (32 cells, 200 steps)")
    print("=" * 70)
    sys.stdout.flush()

    configs = {
        'random_k3': lambda n: build_random(n, k=3),
        'random_k6': lambda n: build_random(n, k=6),
        'ring': build_ring,
        'small_world': build_small_world,
        'scale_free': build_scale_free,
    }

    results = {}
    for name, builder in configs.items():
        print(f"\n  [{name}]")
        sys.stdout.flush()
        torch.manual_seed(42)

        engine = create_engine(N_CELLS)
        adj = builder(N_CELLS)
        setup_topology(engine, adj)

        n_edges = int(adj.sum().item()) // 2
        avg_degree = adj.sum(dim=1).mean().item()

        step_results = run_steps(engine, STEPS)
        phis = [r['phi_iit'] for r in step_results]

        results[name] = {
            'avg_phi': np.mean(phis[-50:]),
            'max_phi': max(phis),
            'final_phi': phis[-1],
            'edges': n_edges,
            'avg_degree': avg_degree,
        }

        print(f"    edges={n_edges}, avg_degree={avg_degree:.1f}")
        print(f"    RESULT: avg_Phi(last50)={results[name]['avg_phi']:.4f}, max_Phi={results[name]['max_phi']:.4f}")
        sys.stdout.flush()

    return results


def experiment_5():
    """Topology Emergence: isolated cells + Hebbian learning."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 5: Topology Emergence (isolated -> Hebbian, 300 steps)")
    print("=" * 70)
    sys.stdout.flush()

    torch.manual_seed(42)
    engine = create_engine(N_CELLS)

    # Start isolated: zero coupling, no topology constraint
    engine._coupling = torch.zeros(N_CELLS, N_CELLS)
    # Don't patch SOC — let default ring SOC run, but coupling starts at zero
    # Hebbian will build the coupling matrix from scratch

    phis = []
    coupling_snapshots = []

    for s in range(300):
        r = engine.step()
        phis.append(r['phi_iit'])

        if (s + 1) in [1, 10, 50, 100, 200, 300]:
            coupling = engine._coupling.clone()
            # Analyze topology properties
            adj = (coupling.abs() > 0.1).float()
            n_edges = int(adj.sum().item()) // 2
            degrees = adj.sum(dim=1)
            avg_degree = degrees.mean().item()
            max_degree = degrees.max().item()
            degree_std = degrees.std().item()

            # Small-world check: clustering coefficient
            cc = 0.0
            n = N_CELLS
            for i in range(n):
                neighbors = [j for j in range(n) if adj[i, j] > 0 and j != i]
                k = len(neighbors)
                if k >= 2:
                    triangles = 0
                    for a in range(len(neighbors)):
                        for b in range(a + 1, len(neighbors)):
                            if adj[neighbors[a], neighbors[b]] > 0:
                                triangles += 1
                    cc += 2 * triangles / (k * (k - 1))
            cc /= n

            # Degree distribution: check for scale-free (power-law) or small-world
            degree_vals = degrees.numpy()
            unique_degs, counts = np.unique(degree_vals, return_counts=True)

            snapshot = {
                'step': s + 1,
                'n_edges': n_edges,
                'avg_degree': avg_degree,
                'max_degree': max_degree,
                'degree_std': degree_std,
                'clustering_coeff': cc,
                'phi': r['phi_iit'],
            }
            coupling_snapshots.append(snapshot)

            print(f"    step {s+1}: edges={n_edges}, avg_deg={avg_degree:.1f}, max_deg={max_degree:.0f}, CC={cc:.3f}, Phi={r['phi_iit']:.4f}")
            sys.stdout.flush()

    # Final topology analysis
    final_adj = (engine._coupling.abs() > 0.1).float()
    degrees_final = final_adj.sum(dim=1).numpy()

    # Is it scale-free? (degree distribution follows power law)
    unique_degs, counts = np.unique(degrees_final, return_counts=True)
    is_heavy_tail = (degrees_final.max() > 3 * degrees_final.mean())

    # Is it small-world? (high clustering + short path length)
    final_cc = coupling_snapshots[-1]['clustering_coeff']
    is_small_world = final_cc > 0.3

    print(f"\n    Final topology:")
    print(f"      Edges: {coupling_snapshots[-1]['n_edges']}")
    print(f"      Avg degree: {coupling_snapshots[-1]['avg_degree']:.1f}")
    print(f"      Max degree: {coupling_snapshots[-1]['max_degree']:.0f}")
    print(f"      Clustering coefficient: {final_cc:.3f}")
    print(f"      Heavy-tailed (scale-free-like): {'YES' if is_heavy_tail else 'NO'}")
    print(f"      High clustering (small-world-like): {'YES' if is_small_world else 'NO'}")
    sys.stdout.flush()

    return {
        'snapshots': coupling_snapshots,
        'phis': phis,
        'is_heavy_tail': is_heavy_tail,
        'is_small_world': is_small_world,
        'degree_distribution': degrees_final.tolist(),
    }


# ============================================================
# Main
# ============================================================

def main():
    print("DD68: Network Topology and Consciousness")
    print(f"Cells={N_CELLS}, Steps={STEPS}")
    print("=" * 70)
    sys.stdout.flush()

    t0 = time.time()

    r1 = experiment_1()
    r2 = experiment_2()
    r3 = experiment_3()
    r4 = experiment_4()
    r5 = experiment_5()

    elapsed = time.time() - t0
    print(f"\n\nTotal time: {elapsed:.1f}s")

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\n--- Experiment 1: Topology x Phi ---")
    print(f"  {'Topology':<15} {'Edges':>6} {'AvgDeg':>7} {'AvgPhi':>8} {'MaxPhi':>8} {'Consensus':>10}")
    best_topo = None
    best_phi = -1
    for name in ['ring', 'small_world', 'hypercube', 'scale_free']:
        d = r1[name]
        print(f"  {name:<15} {d['edges']:>6} {d['avg_degree']:>7.1f} {d['avg_phi_last50']:>8.4f} {d['max_phi']:>8.4f} {d['total_consensus']:>10}")
        if d['avg_phi_last50'] > best_phi:
            best_phi = d['avg_phi_last50']
            best_topo = name
    print(f"  BEST: {best_topo} (avg Phi = {best_phi:.4f})")

    print("\n--- Experiment 2: Dynamic Switching ---")
    for sp in r2['switch_points']:
        line = f"  step {sp['step']}: {sp['topology']}, Phi={sp['phi_at_switch']:.4f}"
        if 'pre_phi' in sp:
            line += f" (pre={sp['pre_phi']:.4f}, Law90={'PASS' if sp['recovered'] else 'FAIL'})"
        print(line)

    print("\n--- Experiment 3: Brain-likeness ---")
    print(f"  {'Topology':<15} {'Total':>6} {'LZ':>6} {'Hurst':>6} {'PSD':>6} {'AutoC':>6} {'Crit':>6}")
    best_bl_topo = None
    best_bl = -1
    for name in ['ring', 'small_world', 'hypercube', 'scale_free']:
        d = r3[name]
        print(f"  {name:<15} {d['total']:>6.1f} {d['lz']:>6.1f} {d['hurst']:>6.1f} {d['psd']:>6.1f} {d['autocorr']:>6.1f} {d['critical']:>6.1f}")
        if d['total'] > best_bl:
            best_bl = d['total']
            best_bl_topo = name
    print(f"  MOST BRAIN-LIKE: {best_bl_topo} ({best_bl:.1f}%)")

    print("\n--- Experiment 4: Random vs Structured ---")
    print(f"  {'Topology':<15} {'Edges':>6} {'AvgPhi':>8} {'MaxPhi':>8}")
    for name in ['random_k3', 'random_k6', 'ring', 'small_world', 'scale_free']:
        d = r4[name]
        print(f"  {name:<15} {d['edges']:>6} {d['avg_phi']:>8.4f} {d['max_phi']:>8.4f}")

    print("\n--- Experiment 5: Topology Emergence ---")
    print(f"  {'Step':>6} {'Edges':>6} {'AvgDeg':>7} {'CC':>6} {'Phi':>8}")
    for snap in r5['snapshots']:
        print(f"  {snap['step']:>6} {snap['n_edges']:>6} {snap['avg_degree']:>7.1f} {snap['clustering_coeff']:>6.3f} {snap['phi']:>8.4f}")
    print(f"  Emergent topology: {'small-world-like' if r5['is_small_world'] else 'not small-world'}, {'scale-free-like' if r5['is_heavy_tail'] else 'not scale-free'}")

    sys.stdout.flush()

    return {
        'exp1': r1,
        'exp2': r2,
        'exp3': r3,
        'exp4': r4,
        'exp5': r5,
        'best_phi_topology': best_topo,
        'best_brainlike_topology': best_bl_topo,
        'elapsed': elapsed,
    }


if __name__ == '__main__':
    results = main()
