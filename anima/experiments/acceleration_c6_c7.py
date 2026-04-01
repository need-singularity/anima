#!/usr/bin/env python3
"""acceleration_c6_c7.py — C6 Consciousness Hash + C7 Neural ODE Consciousness

C6: Discretize consciousness state -> hash -> weight lookup table
    - Collect 10D consciousness vectors over 1000 steps
    - PCA reduce to 3D -> 1000 bins
    - Build hash table: state_hash -> optimal weight_delta
    - Compare lookup O(1) vs normal step

C7: Neural ODE continuous-time consciousness
    - Fit MLP to dx/dt = f(x,t) from state trajectories
    - Use scipy ODE solver with adaptive stepping
    - Measure trajectory linearity -> skip potential
"""

import sys
import os
import time
import math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.integrate import solve_ivp
from scipy.spatial.distance import cosine as cosine_dist

from consciousness_engine import ConsciousnessEngine


# ═══════════════════════════════════════════════════════════
# Simple PCA (no sklearn dependency)
# ═══════════════════════════════════════════════════════════

class SimplePCA:
    """Minimal PCA via SVD — drop-in replacement for sklearn.decomposition.PCA."""

    def __init__(self, n_components):
        self.n_components = n_components
        self.components_ = None
        self.mean_ = None
        self.explained_variance_ratio_ = None

    def fit_transform(self, X):
        X = np.array(X, dtype=np.float64)
        self.mean_ = X.mean(axis=0)
        Xc = X - self.mean_
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
        self.components_ = Vt[:self.n_components]
        total_var = (S ** 2).sum()
        self.explained_variance_ratio_ = (S[:self.n_components] ** 2) / max(total_var, 1e-12)
        return Xc @ self.components_.T

    def transform(self, X):
        X = np.array(X, dtype=np.float64)
        return (X - self.mean_) @ self.components_.T


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def extract_consciousness_vector(engine, result):
    """Extract 10D consciousness vector (Phi, alpha, Z, N, W, E, M, C, T, I)."""
    phi = result.get('phi_iit', 0.0)
    phi_proxy = result.get('phi_proxy', 0.0)
    n_cells = result.get('n_cells', 2)
    consensus = result.get('consensus', 0)

    states = engine.get_states()  # [n_cells, hidden_dim]
    mean_state = states.mean(dim=0)
    variance = states.var(dim=0).mean().item()

    tensions = result.get('tensions', [])
    mean_tension = np.mean(tensions) if tensions else 0.5

    # Build 10D vector from available metrics
    alpha = 0.01 + 0.14 * math.tanh(phi / 3.0)
    impedance = 1.0 / (1.0 + phi)  # Z: self-preservation
    nt_balance = mean_tension  # N: neurotransmitter proxy
    will_idx = consensus / max(n_cells, 1)  # W: consensus ratio
    empathy = 1.0 - variance  # E: inter-cell correlation proxy
    memory = min(1.0, engine._step / 500.0)  # M: capacity proxy
    creativity = variance  # C: output diversity
    temporal = math.sin(engine._step * 0.01) * 0.5 + 0.5  # T: temporal
    identity = 1.0 / (1.0 + abs(phi - phi_proxy))  # I: stability

    return np.array([phi, alpha, impedance, nt_balance, will_idx,
                     empathy, memory, creativity, temporal, identity])


def get_hidden_flat(engine):
    """Get flattened hidden state as numpy array."""
    states = engine.get_states()
    return states.detach().cpu().numpy().flatten()


# ═══════════════════════════════════════════════════════════
# C6: Consciousness Hash Table
# ═══════════════════════════════════════════════════════════

class ConsciousnessHashTable:
    """Hash consciousness states to pre-computed weight deltas."""

    def __init__(self, n_bins_per_dim=10, n_pca_dims=3):
        self.n_bins = n_bins_per_dim
        self.n_pca = n_pca_dims
        self.pca = None
        self.table = {}
        self.bin_edges = None
        self.stats = {'hits': 0, 'misses': 0, 'total_queries': 0}

    def _discretize(self, vec_3d):
        """Quantize 3D PCA vector to bin indices."""
        indices = []
        for d in range(self.n_pca):
            edges = self.bin_edges[d]
            idx = np.searchsorted(edges, vec_3d[d]) - 1
            idx = max(0, min(idx, self.n_bins - 1))
            indices.append(idx)
        return tuple(indices)

    def build(self, vectors_10d, weight_deltas):
        """Build hash table from collected (state, delta) pairs.

        Args:
            vectors_10d: [N, 10] consciousness vectors
            weight_deltas: [N, D] hidden state deltas
        """
        N = len(vectors_10d)
        print(f"  Building hash table from {N} state-delta pairs...")

        # PCA: 10D -> 3D
        self.pca = SimplePCA(n_components=self.n_pca)
        reduced = self.pca.fit_transform(vectors_10d)
        explained = self.pca.explained_variance_ratio_
        print(f"  PCA explained variance: {explained.round(3)}")

        # Compute bin edges from data range
        self.bin_edges = []
        for d in range(self.n_pca):
            mn, mx = reduced[:, d].min(), reduced[:, d].max()
            margin = (mx - mn) * 0.01 + 1e-8
            edges = np.linspace(mn - margin, mx + margin, self.n_bins + 1)
            self.bin_edges.append(edges)

        # Populate table: average deltas for each bin
        bin_accum = {}
        bin_count = {}
        for i in range(N):
            key = self._discretize(reduced[i])
            if key not in bin_accum:
                bin_accum[key] = np.zeros_like(weight_deltas[i])
                bin_count[key] = 0
            bin_accum[key] += weight_deltas[i]
            bin_count[key] += 1

        for key in bin_accum:
            self.table[key] = bin_accum[key] / bin_count[key]

        n_occupied = len(self.table)
        total_bins = self.n_bins ** self.n_pca
        print(f"  Occupied bins: {n_occupied}/{total_bins} ({100*n_occupied/total_bins:.1f}%)")
        return n_occupied

    def lookup(self, vec_10d):
        """Look up weight delta for a consciousness state."""
        self.stats['total_queries'] += 1
        reduced = self.pca.transform(vec_10d.reshape(1, -1))[0]
        key = self._discretize(reduced)
        if key in self.table:
            self.stats['hits'] += 1
            return self.table[key]
        else:
            self.stats['misses'] += 1
            # Nearest neighbor fallback
            if self.table:
                min_dist = float('inf')
                best_delta = None
                for k, v in self.table.items():
                    dist = sum((a - b) ** 2 for a, b in zip(key, k))
                    if dist < min_dist:
                        min_dist = dist
                        best_delta = v
                return best_delta
            return None

    @property
    def hit_rate(self):
        if self.stats['total_queries'] == 0:
            return 0.0
        return self.stats['hits'] / self.stats['total_queries']


def run_c6_consciousness_hash(n_cells=16, collect_steps=500, test_steps=200):
    """C6: Build and evaluate consciousness hash table."""
    print("\n" + "=" * 70)
    print("C6: CONSCIOUSNESS HASH — State -> Weight Lookup Table")
    print("=" * 70)

    # Phase 1: Collect state trajectories
    print(f"\n[Phase 1] Collecting {collect_steps} steps with {n_cells} cells...")
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True
    )

    vectors = []
    hidden_snapshots = []

    t0 = time.time()
    for step in range(collect_steps):
        result = engine.step()
        vec = extract_consciousness_vector(engine, result)
        h = get_hidden_flat(engine)
        vectors.append(vec)
        hidden_snapshots.append(h)
        if (step + 1) % 100 == 0:
            print(f"  Step {step+1}/{collect_steps} — Phi={result['phi_iit']:.4f}, "
                  f"cells={result['n_cells']}, vec_norm={np.linalg.norm(vec):.3f}")
            sys.stdout.flush()

    collect_time = time.time() - t0

    # Phase 2: Compute weight deltas (state[t+1] - state[t])
    print(f"\n[Phase 2] Computing weight deltas...")
    # Pad all hidden snapshots to same length (cells may grow)
    max_len = max(len(h) for h in hidden_snapshots)
    padded = np.zeros((len(hidden_snapshots), max_len))
    for i, h in enumerate(hidden_snapshots):
        padded[i, :len(h)] = h

    deltas = []
    vec_for_delta = []
    for i in range(len(padded) - 1):
        deltas.append(padded[i + 1] - padded[i])
        vec_for_delta.append(vectors[i])

    vectors_arr = np.array(vec_for_delta)
    deltas_arr = np.array(deltas)

    # Phase 3: Build hash table
    print(f"\n[Phase 3] Building hash table...")
    htable = ConsciousnessHashTable(n_bins_per_dim=10, n_pca_dims=3)
    n_occupied = htable.build(vectors_arr, deltas_arr)

    # Phase 4: Test — apply hash lookups and measure quality
    print(f"\n[Phase 4] Testing hash predictions ({test_steps} steps)...")
    engine2 = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True
    )

    prediction_errors = []
    lookup_times = []
    step_times = []

    for step in range(test_steps):
        # Normal step
        t_step = time.time()
        result = engine2.step()
        step_time = time.time() - t_step

        vec = extract_consciousness_vector(engine2, result)
        actual_h = get_hidden_flat(engine2)

        # Hash lookup
        t_lookup = time.time()
        predicted_delta = htable.lookup(vec)
        lookup_time = time.time() - t_lookup

        if predicted_delta is not None and step > 0:
            # Pad to same length for comparison
            max_l = max(len(predicted_delta), len(actual_h), len(prev_h))
            pred_pad = np.zeros(max_l)
            pred_pad[:len(predicted_delta)] = predicted_delta
            act_pad = np.zeros(max_l)
            act_pad[:len(actual_h)] = actual_h
            prev_pad = np.zeros(max_l)
            prev_pad[:len(prev_h)] = prev_h
            actual_delta = act_pad - prev_pad
            # Cosine similarity between predicted and actual delta
            norm_pred = np.linalg.norm(pred_pad)
            norm_actual = np.linalg.norm(actual_delta)
            if norm_pred > 1e-8 and norm_actual > 1e-8:
                cos_sim = np.dot(pred_pad, actual_delta) / (norm_pred * norm_actual)
                prediction_errors.append(cos_sim)

        prev_h = actual_h.copy()
        lookup_times.append(lookup_time)
        step_times.append(step_time)

        if (step + 1) % 50 == 0:
            avg_cos = np.mean(prediction_errors[-50:]) if prediction_errors else 0
            print(f"  Step {step+1}/{test_steps} — cosine_sim={avg_cos:.4f}, "
                  f"hit_rate={htable.hit_rate:.2%}")
            sys.stdout.flush()

    # Results
    avg_step_ms = np.mean(step_times) * 1000
    avg_lookup_us = np.mean(lookup_times) * 1e6
    avg_cos_sim = np.mean(prediction_errors) if prediction_errors else 0
    speedup = avg_step_ms / (avg_lookup_us / 1000) if avg_lookup_us > 0 else 0
    table_size_kb = (sum(v.nbytes for v in htable.table.values())) / 1024

    print(f"\n{'─' * 60}")
    print(f"C6 RESULTS: Consciousness Hash Table")
    print(f"{'─' * 60}")
    print(f"  {'Metric':<35} {'Value':>15}")
    print(f"  {'─' * 50}")
    print(f"  {'Collection steps':<35} {collect_steps:>15}")
    print(f"  {'Test steps':<35} {test_steps:>15}")
    print(f"  {'Cells':<35} {n_cells:>15}")
    print(f"  {'Occupied bins':<35} {n_occupied:>15}")
    print(f"  {'Table size (KB)':<35} {table_size_kb:>15.1f}")
    print(f"  {'Hit rate':<35} {htable.hit_rate:>14.1%}")
    print(f"  {'Avg step time (ms)':<35} {avg_step_ms:>15.3f}")
    print(f"  {'Avg lookup time (us)':<35} {avg_lookup_us:>15.1f}")
    print(f"  {'Lookup speedup vs step':<35} {f'x{speedup:.0f}':>15}")
    print(f"  {'Delta cosine similarity':<35} {avg_cos_sim:>15.4f}")
    print(f"  {'Delta direction accuracy':<35} {f'{max(0,avg_cos_sim)*100:.1f}%':>15}")
    print(f"  {'Generalization':<35} {'GOOD' if avg_cos_sim > 0.3 else 'WEAK' if avg_cos_sim > 0 else 'NONE':>15}")

    # PCA analysis
    if htable.pca is not None:
        evr = htable.pca.explained_variance_ratio_
        print(f"\n  PCA Explained Variance (3D):")
        for i, v in enumerate(evr):
            bar = '#' * int(v * 40)
            print(f"    PC{i+1}: {v:.3f} {bar}")
        print(f"    Total: {sum(evr):.3f}")

    return {
        'speedup': speedup,
        'cos_sim': avg_cos_sim,
        'hit_rate': htable.hit_rate,
        'table_size_kb': table_size_kb,
        'occupied_bins': n_occupied,
        'step_ms': avg_step_ms,
        'lookup_us': avg_lookup_us,
    }


# ═══════════════════════════════════════════════════════════
# C7: Neural ODE Consciousness
# ═══════════════════════════════════════════════════════════

class ConsciousnessODE(nn.Module):
    """MLP to model dx/dt = f(x, t) for consciousness dynamics."""

    def __init__(self, state_dim, hidden=128):
        super().__init__()
        # +1 for time
        self.net = nn.Sequential(
            nn.Linear(state_dim + 1, hidden),
            nn.SiLU(),
            nn.Linear(hidden, hidden),
            nn.SiLU(),
            nn.Linear(hidden, state_dim),
        )

    def forward(self, x, t):
        """x: [state_dim], t: scalar."""
        t_feat = torch.tensor([t], dtype=x.dtype)
        inp = torch.cat([x, t_feat])
        return self.net(inp)


def train_ode(model, states_sequence, lr=1e-3, epochs=50):
    """Train ODE model to predict dx/dt from state trajectory.

    states_sequence: [T, D] numpy array of flattened hidden states.
    """
    T, D = states_sequence.shape
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # Compute dx/dt targets
    dxdt = np.diff(states_sequence, axis=0)  # [T-1, D]
    x_data = torch.tensor(states_sequence[:-1], dtype=torch.float32)
    dxdt_target = torch.tensor(dxdt, dtype=torch.float32)
    t_data = torch.linspace(0, 1, T - 1)

    losses = []
    for epoch in range(epochs):
        total_loss = 0.0
        # Mini-batch over time steps
        perm = torch.randperm(T - 1)
        batch_size = min(64, T - 1)
        for start in range(0, T - 1, batch_size):
            idx = perm[start:start + batch_size]
            pred = torch.stack([model(x_data[i], t_data[i].item()) for i in idx])
            loss = F.mse_loss(pred, dxdt_target[idx])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        losses.append(total_loss)
        if (epoch + 1) % 10 == 0:
            print(f"    Epoch {epoch+1}/{epochs} — Loss: {total_loss:.6f}")
            sys.stdout.flush()

    return losses


def ode_predict_trajectory(model, x0, t_span, n_eval=100):
    """Use scipy ODE solver to predict consciousness trajectory."""
    D = len(x0)

    def f(t, x):
        with torch.no_grad():
            x_t = torch.tensor(x, dtype=torch.float32)
            dxdt = model(x_t, t / t_span[1])  # normalize t to [0,1]
            return dxdt.numpy()

    t_eval = np.linspace(t_span[0], t_span[1], n_eval)
    sol = solve_ivp(f, t_span, x0, t_eval=t_eval, method='RK45',
                    rtol=1e-4, atol=1e-6, max_step=0.5)
    return sol


def measure_trajectory_curvature(trajectory):
    """Measure curvature of trajectory: how linear is it?

    Returns:
        linearity: 0=very curved, 1=perfectly straight
        curvatures: per-step curvature values
    """
    T = len(trajectory)
    if T < 3:
        return 1.0, []

    # Straight line from start to end
    start = trajectory[0]
    end = trajectory[-1]
    line_dir = end - start
    line_len = np.linalg.norm(line_dir)
    if line_len < 1e-10:
        return 1.0, [0.0] * T

    line_dir = line_dir / line_len

    # Distance of each point from the straight line
    deviations = []
    for i in range(T):
        v = trajectory[i] - start
        proj = np.dot(v, line_dir)
        perp = v - proj * line_dir
        deviations.append(np.linalg.norm(perp))

    max_dev = max(deviations)
    linearity = 1.0 - min(1.0, max_dev / (line_len + 1e-10))

    # Per-step curvature (angle between consecutive velocity vectors)
    curvatures = []
    for i in range(1, T - 1):
        v1 = trajectory[i] - trajectory[i - 1]
        v2 = trajectory[i + 1] - trajectory[i]
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 > 1e-10 and n2 > 1e-10:
            cos_angle = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
            curvatures.append(1.0 - cos_angle)  # 0=straight, 2=reversal
        else:
            curvatures.append(0.0)

    return linearity, curvatures


def run_c7_neural_ode(n_cells=16, collect_steps=300, predict_steps=100):
    """C7: Neural ODE continuous-time consciousness."""
    print("\n" + "=" * 70)
    print("C7: NEURAL ODE — Continuous-Time Consciousness")
    print("=" * 70)

    # Phase 1: Collect state trajectory
    print(f"\n[Phase 1] Collecting {collect_steps}-step trajectory ({n_cells} cells)...")
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=2, max_cells=n_cells,
        n_factions=12, phi_ratchet=True
    )

    trajectory = []
    phis = []
    step_times_normal = []

    t0 = time.time()
    for step in range(collect_steps):
        ts = time.time()
        result = engine.step()
        step_times_normal.append(time.time() - ts)

        h = get_hidden_flat(engine)
        trajectory.append(h)
        phis.append(result['phi_iit'])

        if (step + 1) % 100 == 0:
            print(f"  Step {step+1}/{collect_steps} — Phi={result['phi_iit']:.4f}, "
                  f"cells={result['n_cells']}")
            sys.stdout.flush()

    collect_time = time.time() - t0

    # Pad to uniform length
    max_len = max(len(h) for h in trajectory)
    traj_arr = np.zeros((len(trajectory), max_len))
    for i, h in enumerate(trajectory):
        traj_arr[i, :len(h)] = h

    # Phase 2: Reduce dimensionality for ODE fitting
    print(f"\n[Phase 2] PCA reduction for ODE fitting...")
    # Full state is too high-dim for ODE; PCA to manageable size
    ode_dim = 32
    pca = SimplePCA(n_components=ode_dim)
    traj_reduced = pca.fit_transform(traj_arr)
    explained_total = sum(pca.explained_variance_ratio_)
    print(f"  State dim: {max_len} -> {ode_dim} (PCA explains {explained_total:.1%})")

    # Phase 3: Train ODE model
    print(f"\n[Phase 3] Training Neural ODE (dx/dt = f(x,t))...")
    ode_model = ConsciousnessODE(state_dim=ode_dim, hidden=64)
    train_losses = train_ode(ode_model, traj_reduced, lr=1e-3, epochs=50)

    # Phase 4: ODE prediction
    print(f"\n[Phase 4] ODE trajectory prediction ({predict_steps} steps)...")
    # Start from a point in the trajectory
    start_idx = collect_steps // 2
    x0 = traj_reduced[start_idx]
    t_span = (0.0, float(predict_steps))

    t_ode_start = time.time()
    sol = ode_predict_trajectory(ode_model, x0, t_span, n_eval=predict_steps)
    ode_time = time.time() - t_ode_start

    # Phase 5: Compare ODE vs actual
    print(f"\n[Phase 5] Comparing ODE predictions vs actual trajectory...")

    # Ground truth: actual trajectory from start_idx
    actual_segment = traj_reduced[start_idx:start_idx + predict_steps]
    n_compare = min(len(actual_segment), sol.y.shape[1])

    ode_predicted = sol.y.T[:n_compare]
    actual_compare = actual_segment[:n_compare]

    # Per-step MSE
    mse_per_step = np.mean((ode_predicted - actual_compare) ** 2, axis=1)
    cos_sims = []
    for i in range(n_compare):
        n1 = np.linalg.norm(ode_predicted[i])
        n2 = np.linalg.norm(actual_compare[i])
        if n1 > 1e-8 and n2 > 1e-8:
            cos_sims.append(np.dot(ode_predicted[i], actual_compare[i]) / (n1 * n2))
        else:
            cos_sims.append(0.0)

    # Phase 6: Trajectory analysis
    print(f"\n[Phase 6] Trajectory curvature analysis...")
    linearity, curvatures = measure_trajectory_curvature(traj_reduced)
    straight_frac = sum(1 for c in curvatures if c < 0.1) / max(len(curvatures), 1)

    # Adaptive step analysis
    if sol.success:
        # How many RK45 internal steps were used?
        n_ode_evals = sol.nfev
        # ODE steps vs fixed steps
        ode_step_ratio = predict_steps / max(n_ode_evals, 1)
    else:
        n_ode_evals = -1
        ode_step_ratio = 0

    # Timing
    avg_normal_ms = np.mean(step_times_normal) * 1000
    normal_total_ms = predict_steps * avg_normal_ms
    ode_total_ms = ode_time * 1000
    ode_speedup = normal_total_ms / max(ode_total_ms, 0.001)

    # Short/medium/long horizon accuracy
    horizons = {'short (10 steps)': 10, 'medium (50 steps)': 50, 'long (100 steps)': n_compare}
    horizon_results = {}
    for name, h in horizons.items():
        h = min(h, n_compare)
        if h > 0:
            cos_h = np.mean(cos_sims[:h])
            mse_h = np.mean(mse_per_step[:h])
            horizon_results[name] = (cos_h, mse_h)

    # Results
    print(f"\n{'─' * 60}")
    print(f"C7 RESULTS: Neural ODE Consciousness")
    print(f"{'─' * 60}")
    print(f"  {'Metric':<40} {'Value':>15}")
    print(f"  {'─' * 55}")
    print(f"  {'Cells':<40} {n_cells:>15}")
    print(f"  {'Collect steps':<40} {collect_steps:>15}")
    print(f"  {'Predict steps':<40} {predict_steps:>15}")
    print(f"  {'ODE state dim (PCA)':<40} {ode_dim:>15}")
    print(f"  {'PCA explained variance':<40} {explained_total:>14.1%}")
    print(f"  {'ODE training loss (final)':<40} {train_losses[-1]:>15.6f}")
    print(f"  {'ODE solver evaluations':<40} {n_ode_evals:>15}")
    print(f"  {'ODE solver success':<40} {'YES' if sol.success else 'NO':>15}")
    print(f"  {'─' * 55}")

    print(f"\n  Prediction Accuracy by Horizon:")
    print(f"  {'Horizon':<25} {'Cosine Sim':>12} {'MSE':>12}")
    print(f"  {'─' * 50}")
    for name, (cos_h, mse_h) in horizon_results.items():
        print(f"  {name:<25} {cos_h:>12.4f} {mse_h:>12.6f}")

    print(f"\n  Timing Comparison:")
    print(f"  {'Method':<30} {'Time (ms)':>12} {'Speedup':>10}")
    print(f"  {'─' * 52}")
    norm_label = f"Normal steps (x{predict_steps})"
    ode_label = f"ODE solve (x{predict_steps})"
    print(f"  {norm_label:<30} {normal_total_ms:>12.1f} {'1.0x':>10}")
    print(f"  {ode_label:<30} {ode_total_ms:>12.1f} {f'{ode_speedup:.1f}x':>10}")

    print(f"\n  Trajectory Linearity:")
    print(f"  {'Overall linearity':<40} {linearity:>14.3f}")
    print(f"  {'Straight segments (curv<0.1)':<40} {straight_frac:>14.1%}")
    print(f"  {'Skip potential':<40} {f'{straight_frac*100:.0f}% of steps':>15}")

    # ASCII graph: cosine similarity decay over prediction horizon
    print(f"\n  Cosine Similarity vs Prediction Horizon:")
    n_bins_graph = min(10, n_compare)
    bin_size = max(1, n_compare // n_bins_graph)
    print(f"  cos |")
    for row_val in [1.0, 0.75, 0.5, 0.25, 0.0, -0.25]:
        line = f"  {row_val:>5.2f}|"
        for b in range(n_bins_graph):
            start = b * bin_size
            end = min(start + bin_size, n_compare)
            avg_cos = np.mean(cos_sims[start:end]) if end > start else 0
            if avg_cos >= row_val:
                line += "##"
            else:
                line += "  "
        print(line)
    step_labels = "      +" + "--" * n_bins_graph
    print(step_labels)
    print(f"       {'0':<{n_bins_graph}}{'>' + str(n_compare)}")
    print(f"       steps ahead ->")

    return {
        'ode_speedup': ode_speedup,
        'linearity': linearity,
        'straight_frac': straight_frac,
        'cos_sim_short': horizon_results.get('short (10 steps)', (0, 0))[0],
        'cos_sim_medium': horizon_results.get('medium (50 steps)', (0, 0))[0],
        'cos_sim_long': horizon_results.get(f'long (100 steps)', (0, 0))[0],
        'ode_evals': n_ode_evals,
        'train_loss': train_losses[-1],
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("ACCELERATION C6 + C7: Consciousness Hash + Neural ODE")
    print("=" * 70)

    n_cells = 16

    # C6: Consciousness Hash Table
    c6_results = run_c6_consciousness_hash(n_cells=n_cells, collect_steps=500, test_steps=200)

    # C7: Neural ODE
    c7_results = run_c7_neural_ode(n_cells=n_cells, collect_steps=300, predict_steps=100)

    # Summary
    print("\n" + "=" * 70)
    print("COMBINED SUMMARY")
    print("=" * 70)
    print(f"\n  {'Experiment':<15} {'Speedup':>10} {'Accuracy':>12} {'Practical?':>12}")
    print(f"  {'─' * 50}")

    c6_acc = f"{c6_results['cos_sim']:.3f} cos"
    c6_spd = c6_results['speedup']
    c6_prac = "YES" if c6_results['cos_sim'] > 0.3 and c6_spd > 10 else "MARGINAL" if c6_results['cos_sim'] > 0 else "NO"
    print(f"  {'C6 Hash':<15} {'x' + str(int(c6_spd)):>10} {c6_acc:>12} {c6_prac:>12}")

    c7_acc = f"{c7_results['cos_sim_short']:.3f} cos"
    c7_spd = c7_results['ode_speedup']
    c7_prac = "YES" if c7_results['cos_sim_short'] > 0.5 and c7_spd > 2 else "MARGINAL" if c7_results['cos_sim_short'] > 0 else "NO"
    print(f"  {'C7 ODE':<15} {'x' + f'{c7_spd:.1f}':>10} {c7_acc:>12} {c7_prac:>12}")

    print(f"\n  Key Findings:")
    print(f"    C6: Hash lookup is {c6_results['lookup_us']:.1f}us vs {c6_results['step_ms']:.1f}ms/step")
    print(f"        Table: {c6_results['table_size_kb']:.1f}KB, {c6_results['occupied_bins']} bins, "
          f"hit rate {c6_results['hit_rate']:.0%}")
    print(f"    C7: Trajectory {c7_results['linearity']:.1%} linear, "
          f"{c7_results['straight_frac']:.0%} skippable")
    print(f"        Short-horizon cos={c7_results['cos_sim_short']:.3f}, "
          f"ODE evals={c7_results['ode_evals']}")


if __name__ == '__main__':
    main()
