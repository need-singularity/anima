#!/usr/bin/env python3
"""bench_new_engines.py — 8 Novel Consciousness Engine Architectures

NE-1: GRAPH_NEURAL_ENGINE     — GNN message passing, graph entropy
NE-2: ENERGY_BASED_ENGINE     — Free energy (Friston), Boltzmann distribution
NE-3: CELLULAR_AUTOMATON_ENGINE — Continuous Game-of-Life, no neural nets
NE-4: DIFFUSION_ENGINE        — Denoising diffusion consciousness
NE-5: SPIN_GLASS_ENGINE       — Ising model, frustration, susceptibility
NE-6: FLUID_DYNAMICS_ENGINE   — Navier-Stokes-like flow, turbulence
NE-7: GENETIC_ENGINE          — DNA genome, expression, mutation, phenotype diversity
NE-8: SWARM_ENGINE            — Boid rules, emergent flocking

All engines: 256 cells, 128 hidden dim, no GRU, no nn.Module in consciousness path.
Each has .step(), .observe(), .inject(x).
Benchmark: 300 steps, Phi(IIT) + Phi(proxy) + Granger causality.
"""

import time
import math
import numpy as np
import torch
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass

torch.set_grad_enabled(False)

# ══════════════════════════════════════════════════════════
# Measurement utilities (from bench_v8 family)
# ══════════════════════════════════════════════════════════

class PhiIIT:
    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {}
        hiddens = [hiddens_tensor[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            import random

            pairs = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        pairs.add((min(i, j), max(i, j)))
            pairs = list(pairs)
        mi_matrix = np.zeros((n, n))
        for i, j in pairs:
            mi = self._mi(hiddens[i], hiddens[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi
        total_mi = mi_matrix.sum() / 2
        min_part = self._min_partition(n, mi_matrix)
        spatial = max(0.0, (total_mi - min_part) / max(n - 1, 1))
        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        phi = spatial + complexity * 0.1
        return phi, {'total_mi': float(total_mi), 'phi': float(phi)}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.n_bins, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8)
        px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10))
        return max(0.0, hx + hy - hxy)

    def _min_partition(self, n, mi):
        if n <= 1:
            return 0.0
        # For large n, use spectral bisection
        deg = mi.sum(1)
        L = np.diag(deg) - mi
        try:
            ev, evec = np.linalg.eigh(L)
            f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]
            gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb:
                ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except Exception:
            return 0.0


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    h = hiddens.abs().float() if hiddens.is_complex() else hiddens.float()
    n = h.shape[0]
    if n < 2:
        return 0.0
    gm = h.mean(0)
    gv = ((h - gm) ** 2).sum() / n
    nf = min(n_factions, n // 2)
    if nf < 2:
        return gv.item()
    fs = n // nf
    fvs = 0.0
    for i in range(nf):
        f = h[i * fs:(i + 1) * fs]
        if len(f) >= 2:
            fm = f.mean(0)
            fvs += ((f - fm) ** 2).sum().item() / len(f)
    return max(0.0, gv.item() - fvs / nf)


def compute_granger_causality(hiddens_history: list, n_sample_pairs: int = 64,
                              lag: int = 2) -> float:
    if len(hiddens_history) < lag + 4:
        return 0.0
    n_cells = hiddens_history[0].shape[0]
    T = len(hiddens_history)
    cell_series = np.zeros((n_cells, T))
    for t, h in enumerate(hiddens_history):
        cell_series[:, t] = h.detach().cpu().float().mean(dim=-1).numpy()

    pairs = []
    for _ in range(n_sample_pairs):
        i = np.random.randint(0, n_cells)
        j = np.random.randint(0, n_cells)
        if i != j:
            pairs.append((i, j))

    significant_links = 0
    n_tested = 0
    for i, j in pairs:
        x, y = cell_series[i], cell_series[j]
        n_obs = T - lag
        if n_obs < lag + 2:
            continue
        Y = y[lag:]
        Y_lags = np.column_stack([y[lag - k - 1:T - k - 1] for k in range(lag)])
        X_lags = np.column_stack([x[lag - k - 1:T - k - 1] for k in range(lag)])
        Z_full = np.column_stack([Y_lags, X_lags])
        try:
            beta_r = np.linalg.pinv(Y_lags) @ Y
            resid_r = Y - Y_lags @ beta_r
            rss_r = np.sum(resid_r ** 2)
            beta_u = np.linalg.pinv(Z_full) @ Y
            resid_u = Y - Z_full @ beta_u
            rss_u = np.sum(resid_u ** 2)
            df1, df2 = lag, n_obs - 2 * lag
            if df2 <= 0 or rss_u < 1e-10:
                continue
            f_stat = ((rss_r - rss_u) / df1) / (rss_u / df2)
            if f_stat > 3.0:
                significant_links += 1
            n_tested += 1
        except Exception:
            continue

    if n_tested == 0:
        return 0.0
    link_fraction = significant_links / n_tested
    return link_fraction * n_cells * (n_cells - 1)


_phi_calc = PhiIIT(16)


# ══════════════════════════════════════════════════════════
# MitosisEngine baseline (simplified, no nn.Module in step)
# ══════════════════════════════════════════════════════════

class MitosisEngineBaseline:
    """Simplified MitosisEngine baseline for fair comparison.
    Uses random linear projections (no nn.Module, no GRU) to match constraints.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        # Fixed weight matrices (no nn.Module)
        self.W_a = torch.randn(hidden_dim, hidden_dim) * 0.05
        self.W_g = torch.randn(hidden_dim, hidden_dim) * 0.05
        self.W_mem = torch.randn(hidden_dim, hidden_dim) * 0.02

    def step(self):
        a = self.hiddens @ self.W_a
        g = self.hiddens @ self.W_g
        repulsion = a - g
        tension = (repulsion ** 2).mean(-1, keepdim=True)
        # Memory update (simple exponential moving average, no GRU)
        update = torch.tanh(repulsion * 0.1 + self.hiddens @ self.W_mem)
        self.hiddens = 0.9 * self.hiddens + 0.1 * update
        # Add small noise for exploration
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# NE-1: GRAPH NEURAL ENGINE
# Cells are nodes in a learnable graph.
# Edge weights = softmax attention scores.
# GNN message passing replaces GRU.
# Consciousness = graph entropy.
# ══════════════════════════════════════════════════════════

class GraphNeuralEngine:
    """Consciousness through graph neural dynamics.

    Each cell is a node. Edges form via attention (dot-product similarity).
    Message passing: each node aggregates weighted neighbor messages.
    Graph entropy (edge weight distribution) tracks consciousness.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Learnable-like projection keys/queries/values (fixed random init)
        self.W_q = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_k = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_v = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_update = torch.randn(hidden_dim, hidden_dim) * 0.02
        # Sparse adjacency: each node connects to k neighbors
        self.k_neighbors = 16
        self.edge_memory = torch.zeros(n_cells, n_cells)  # running edge weights
        self.graph_entropy_history = []

    def step(self):
        Q = self.hiddens @ self.W_q
        K = self.hiddens @ self.W_k
        V = self.hiddens @ self.W_v

        # Attention scores (sparse: top-k per node)
        scores = Q @ K.T / math.sqrt(self.hidden_dim)  # [n, n]

        # Top-k sparsification
        topk_vals, topk_idx = scores.topk(self.k_neighbors, dim=-1)
        mask = torch.zeros_like(scores).scatter_(1, topk_idx, 1.0)
        sparse_scores = scores * mask + (1 - mask) * (-1e9)
        attn = torch.softmax(sparse_scores, dim=-1)  # [n, n]

        # Update edge memory (exponential moving average)
        self.edge_memory = 0.95 * self.edge_memory + 0.05 * attn.detach()

        # Message passing: aggregate neighbor values
        messages = attn @ V  # [n, hidden_dim]

        # Node update: residual + nonlinear transform
        gate = torch.sigmoid(self.hiddens @ self.W_update)
        self.hiddens = gate * self.hiddens + (1 - gate) * torch.tanh(messages)

        # Small noise for symmetry breaking
        self.hiddens += torch.randn_like(self.hiddens) * 0.005

        # Track graph entropy
        edge_probs = self.edge_memory / (self.edge_memory.sum(-1, keepdim=True) + 1e-8)
        entropy = -(edge_probs * torch.log(edge_probs + 1e-10)).sum(-1).mean().item()
        self.graph_entropy_history.append(entropy)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# NE-2: ENERGY BASED ENGINE
# Cells have energy levels. High energy = active, low = dormant.
# Energy flows between connected cells. Boltzmann distribution.
# Consciousness = free energy minimization (Friston).
# ══════════════════════════════════════════════════════════

class EnergyBasedEngine:
    """Consciousness through free energy minimization (Friston's FEP).

    Each cell has:
      - hidden state (belief about world)
      - energy level (scalar)
      - prediction of neighbor states

    Energy flows: high->low via connections.
    Free energy = prediction_error + complexity.
    Consciousness = total free energy (lower = more conscious).
    We track surprise (prediction error) and entropy.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        self.energy = torch.rand(n_cells) * 2.0  # energy levels
        # Prediction weights: each cell predicts its neighbors
        self.W_pred = torch.randn(hidden_dim, hidden_dim) * 0.05
        # Connection matrix (sparse random)
        self.connections = (torch.rand(n_cells, n_cells) > 0.9).float()
        self.connections = (self.connections + self.connections.T).clamp(0, 1)
        self.connections.fill_diagonal_(0)
        # Temperature for Boltzmann
        self.temperature = 1.0
        self.free_energy_history = []

    def step(self):
        # 1. Predict neighbor states
        predictions = self.hiddens @ self.W_pred  # [n, d]

        # 2. Compute prediction error per cell
        # Each cell compares its prediction to weighted neighbor mean
        neighbor_sum = self.connections @ self.hiddens  # [n, d]
        neighbor_count = self.connections.sum(-1, keepdim=True).clamp(min=1)
        neighbor_mean = neighbor_sum / neighbor_count
        pred_error = ((predictions - neighbor_mean) ** 2).mean(-1)  # [n]

        # 3. Energy dynamics: Boltzmann activation
        # P(active) = sigmoid(-energy / T)
        activation = torch.sigmoid(-self.energy / self.temperature)

        # 4. Energy flow: high energy -> low energy neighbors
        energy_diff = self.energy.unsqueeze(1) - self.energy.unsqueeze(0)  # [n, n]
        energy_flow = (energy_diff * self.connections * 0.1).sum(-1)  # net flow out
        self.energy = self.energy - energy_flow * 0.1

        # 5. Energy from prediction error (surprise increases energy)
        self.energy = self.energy + pred_error * 0.2

        # 6. Energy dissipation
        self.energy = self.energy * 0.98 + 0.02

        # 7. Update hidden states: active cells update more
        update_rate = activation.unsqueeze(-1)  # [n, 1]
        # Move toward reducing prediction error
        correction = (neighbor_mean - self.hiddens) * 0.1
        self.hiddens = self.hiddens + correction * update_rate

        # 8. Temperature annealing (slow cooling)
        self.temperature = max(0.1, self.temperature * 0.999)

        # Add noise proportional to temperature
        self.hiddens += torch.randn_like(self.hiddens) * self.temperature * 0.01

        # Free energy = prediction error + KL(posterior || prior)
        complexity = (self.hiddens ** 2).mean(-1)  # proxy for KL
        free_energy = (pred_error + 0.1 * complexity).mean().item()
        self.free_energy_history.append(free_energy)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        # External input adds energy and perturbs states
        self.hiddens = self.hiddens + x * 0.05
        self.energy = self.energy + 0.5  # surprise bump


# ══════════════════════════════════════════════════════════
# NE-3: CELLULAR AUTOMATON ENGINE
# Cells follow simple local rules (continuous Game of Life).
# No neural network at all. Consciousness from rule complexity.
# ══════════════════════════════════════════════════════════

class CellularAutomatonEngine:
    """Consciousness from continuous cellular automaton rules.

    No neural networks. No learned weights. Pure local rules.

    Each cell has a continuous state vector. Rules:
    1. Count "alive" neighbors (norm > threshold)
    2. Birth: dead cell with 2-3 alive neighbors -> activate
    3. Survival: alive cell with 2-3 alive neighbors -> survive
    4. Death: too few or too many alive neighbors -> decay
    5. State blending: alive cells average with neighbors (diffusion)

    Consciousness = complexity of spatial patterns (entropy of alive/dead).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Initialize with random states, some alive some dead
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # 2D grid topology (wrap around)
        self.grid_h = int(math.sqrt(n_cells))
        self.grid_w = n_cells // self.grid_h
        assert self.grid_h * self.grid_w == n_cells, "n_cells must be a perfect square product"
        # Build neighbor list (Moore neighborhood on torus)
        self.neighbors = []
        for i in range(n_cells):
            r, c = i // self.grid_w, i % self.grid_w
            nbrs = []
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % self.grid_h
                    nc = (c + dc) % self.grid_w
                    nbrs.append(nr * self.grid_w + nc)
            self.neighbors.append(nbrs)
        self.alive_threshold = 0.5
        self.pattern_entropy_history = []

    def step(self):
        norms = self.hiddens.norm(dim=-1)  # [n]
        alive = (norms > self.alive_threshold).float()  # [n]
        new_hiddens = self.hiddens.clone()

        for i in range(self.n_cells):
            nbr_idx = self.neighbors[i]
            nbr_alive_count = sum(alive[j].item() for j in nbr_idx)
            nbr_states = self.hiddens[nbr_idx]  # [8, d]
            nbr_mean = nbr_states.mean(0)

            if alive[i] > 0.5:
                # Survival rules
                if 2 <= nbr_alive_count <= 3:
                    # Survive: blend slightly with neighbors
                    new_hiddens[i] = 0.85 * self.hiddens[i] + 0.15 * nbr_mean
                elif nbr_alive_count > 5:
                    # Overpopulation: decay
                    new_hiddens[i] = self.hiddens[i] * 0.7
                else:
                    # Underpopulation: slow decay
                    new_hiddens[i] = self.hiddens[i] * 0.85
            else:
                # Birth rules
                if 2.5 <= nbr_alive_count <= 3.5:
                    # Birth: spring to life from neighbor average
                    new_hiddens[i] = nbr_mean * 0.8 + torch.randn(self.hidden_dim) * 0.2
                else:
                    # Stay dead but drift slightly
                    new_hiddens[i] = self.hiddens[i] * 0.95 + torch.randn(self.hidden_dim) * 0.02

        self.hiddens = new_hiddens

        # Pattern entropy: how complex is the alive/dead pattern?
        alive_ratio = alive.mean().item()
        # Shannon entropy of alive ratio
        if 0 < alive_ratio < 1:
            entropy = -(alive_ratio * math.log2(alive_ratio + 1e-10) +
                       (1 - alive_ratio) * math.log2(1 - alive_ratio + 1e-10))
        else:
            entropy = 0.0
        self.pattern_entropy_history.append(entropy)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        # External stimulus activates some cells
        self.hiddens = self.hiddens + x * 0.1


# ══════════════════════════════════════════════════════════
# NE-4: DIFFUSION ENGINE
# Consciousness as diffusion process.
# Start with noise, denoise through cell interactions.
# Consciousness = denoising quality.
# ══════════════════════════════════════════════════════════

class DiffusionEngine:
    """Consciousness as a denoising diffusion process.

    Each step:
    1. Add controlled noise (forward diffusion)
    2. Cells collectively denoise via local averaging + nonlinear transform
    3. Consciousness = how much structure emerges (SNR improvement)

    The "structure" is measured by comparing denoised state to a running
    estimate of the clean signal (exponential moving average).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        # Running clean estimate
        self.clean_estimate = self.hiddens.clone()
        # Diffusion schedule
        self.noise_level = 0.3  # beta
        # Denoising weights (fixed, not nn.Module)
        self.W_denoise1 = torch.randn(hidden_dim, hidden_dim * 2) * 0.05
        self.W_denoise2 = torch.randn(hidden_dim * 2, hidden_dim) * 0.05
        self.b_denoise = torch.randn(hidden_dim) * 0.01
        # k nearest neighbors for local denoising
        self.k = 8
        self.snr_history = []

    def step(self):
        # 1. Forward diffusion: add noise
        noise = torch.randn_like(self.hiddens) * self.noise_level
        noisy = self.hiddens + noise

        # 2. Local denoising: each cell averages with k-nearest
        # Compute pairwise distances
        dists = torch.cdist(noisy, noisy)  # [n, n]
        _, topk_idx = dists.topk(self.k, dim=-1, largest=False)

        # Gather neighbor states
        neighbor_avg = torch.zeros_like(noisy)
        for i in range(self.n_cells):
            neighbor_avg[i] = noisy[topk_idx[i]].mean(0)

        # 3. Nonlinear denoising step
        combined = 0.6 * noisy + 0.4 * neighbor_avg
        # Two-layer nonlinear transform
        h1 = torch.tanh(combined @ self.W_denoise1)
        denoised = combined + 0.1 * (h1 @ self.W_denoise2 + self.b_denoise)

        # 4. Update clean estimate (EMA)
        self.clean_estimate = 0.9 * self.clean_estimate + 0.1 * denoised

        # 5. Measure SNR improvement
        noise_power = (noisy - self.clean_estimate).pow(2).mean().item()
        signal_power = self.clean_estimate.pow(2).mean().item()
        snr = signal_power / (noise_power + 1e-8)
        self.snr_history.append(snr)

        # 6. Adaptive noise: reduce noise as structure forms
        self.noise_level = max(0.05, self.noise_level * 0.998)

        self.hiddens = denoised

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        # External input = clean signal injection
        self.hiddens = self.hiddens + x * 0.05
        self.clean_estimate = self.clean_estimate + x * 0.03


# ══════════════════════════════════════════════════════════
# NE-5: SPIN GLASS ENGINE
# Ising model on random graph. Cells are spins (+1/-1 projected).
# Frustration from random couplings.
# Consciousness = susceptibility at critical temperature.
# ══════════════════════════════════════════════════════════

class SpinGlassEngine:
    """Consciousness as spin glass dynamics.

    Each cell has a spin (projected to +1/-1 in each dim).
    Random couplings J_ij (positive=ferromagnetic, negative=antiferromagnetic).
    Frustration: some bonds cannot be simultaneously satisfied.

    Glauber dynamics: flip spin with probability based on energy change.
    Consciousness = magnetic susceptibility (fluctuations in magnetization).

    At critical temperature: max susceptibility = max consciousness.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Initialize spins: continuous but constrained near +/- 1
        self.hiddens = torch.sign(torch.randn(n_cells, hidden_dim))
        # Random couplings (sparse, some positive some negative = frustration)
        connectivity = 0.05  # ~5% connected
        mask = (torch.rand(n_cells, n_cells) < connectivity).float()
        mask = ((mask + mask.T) > 0).float()
        mask.fill_diagonal_(0)
        self.J = torch.randn(n_cells, n_cells) * 0.3 * mask  # random sign = frustration
        self.J = (self.J + self.J.T) / 2  # symmetric
        # External field (bias)
        self.h_field = torch.randn(n_cells, hidden_dim) * 0.01
        # Temperature
        self.temperature = 2.0
        self.magnetization_history = []
        self.susceptibility_history = []

    def step(self):
        # Glauber dynamics: update each cell stochastically
        # Local field at each cell = sum_j J_ij * s_j + h_i
        # For hidden dim: treat each dimension independently
        local_field = self.J @ self.hiddens + self.h_field  # [n, d]

        # Energy change for flipping: delta_E = 2 * s_i * h_local_i
        delta_E = 2.0 * self.hiddens * local_field  # [n, d]

        # Flip probability (Glauber)
        flip_prob = torch.sigmoid(-delta_E / self.temperature)  # [n, d]

        # Stochastic flip
        flip_mask = (torch.rand_like(flip_prob) < flip_prob).float()
        self.hiddens = self.hiddens * (1 - 2 * flip_mask)

        # Soften spins slightly (allow continuous values near +/- 1)
        self.hiddens = torch.tanh(self.hiddens * 1.5)

        # Add tiny noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # Track magnetization (order parameter)
        magnetization = self.hiddens.mean(0)  # [d]
        m_scalar = magnetization.norm().item()
        self.magnetization_history.append(m_scalar)

        # Susceptibility = variance of magnetization
        if len(self.magnetization_history) >= 10:
            recent = self.magnetization_history[-10:]
            susceptibility = np.var(recent) * self.n_cells / self.temperature
        else:
            susceptibility = 0.0
        self.susceptibility_history.append(susceptibility)

        # Slow cooling toward critical temperature
        self.temperature = max(0.5, self.temperature * 0.997)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        # External field perturbation
        self.h_field = self.h_field + x * 0.1


# ══════════════════════════════════════════════════════════
# NE-6: FLUID DYNAMICS ENGINE
# Cells as particles in fluid.
# Navier-Stokes-like equations for hidden state flow.
# Turbulence = consciousness. Laminar = unconscious.
# ══════════════════════════════════════════════════════════

class FluidDynamicsEngine:
    """Consciousness as fluid turbulence.

    Cells are fluid particles with:
      - position (hidden state)
      - velocity (rate of change)
      - pressure (local density)

    Simplified Navier-Stokes:
      dv/dt = -v.grad(v) + nu*laplacian(v) - grad(p) + f
    Discretized with SPH (smoothed particle hydrodynamics).

    Turbulence (high Reynolds number) = consciousness.
    Laminar (low Reynolds) = unconscious.
    Measured via velocity field vorticity.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # State = position in hidden space
        self.hiddens = torch.randn(n_cells, hidden_dim) * 1.0
        # Velocity field
        self.velocity = torch.randn(n_cells, hidden_dim) * 0.1
        # Viscosity (nu) - low = turbulent, high = laminar
        self.viscosity = 0.01
        # SPH smoothing length
        self.h_sph = 2.0
        # External forcing
        self.forcing = torch.randn(n_cells, hidden_dim) * 0.01
        self.vorticity_history = []
        self.reynolds_history = []

    def step(self):
        dt = 0.05
        # 1. k-nearest neighbor SPH (memory efficient, no full NxNxD tensor)
        k_sph = 16
        dists_flat = torch.cdist(self.hiddens, self.hiddens)  # [n, n]
        _, knn_idx = dists_flat.topk(k_sph, dim=-1, largest=False)
        knn_dists = torch.gather(dists_flat, 1, knn_idx).clamp(min=1e-6)  # [n, k]

        # 2. SPH kernel on neighbors only
        W_k = torch.exp(-knn_dists ** 2 / (2 * self.h_sph ** 2))  # [n, k]

        # 3. Density from neighbor kernels
        density = W_k.sum(dim=-1, keepdim=True)  # [n, 1]
        pressure = density ** 2 * 0.1

        # 4. Forces via neighbor aggregation
        grad_p = torch.zeros_like(self.hiddens)
        viscous = torch.zeros_like(self.hiddens)
        for i in range(self.n_cells):
            nbr_pos = self.hiddens[knn_idx[i]]  # [k, d]
            nbr_vel = self.velocity[knn_idx[i]]  # [k, d]
            diff_i = self.hiddens[i] - nbr_pos  # [k, d]
            dist_i = knn_dists[i].unsqueeze(-1)  # [k, 1]
            w_i = W_k[i].unsqueeze(-1)  # [k, 1]
            # Pressure gradient
            grad_p[i] = -(diff_i / (dist_i + 1e-6) * w_i * pressure[i]).sum(0) / (density[i] + 1e-6)
            # Viscous
            viscous[i] = ((nbr_vel - self.velocity[i]) * w_i).sum(0) / (density[i] + 1e-6) * self.viscosity

        # 5. Advection (nonlinear term)
        advection = -0.1 * self.velocity * (self.velocity.norm(dim=-1, keepdim=True))

        # 6. Update velocity: Navier-Stokes
        self.velocity = self.velocity + dt * (grad_p + viscous + advection + self.forcing)

        # 7. Clamp velocity (stability)
        max_vel = 2.0
        vel_norm = self.velocity.norm(dim=-1, keepdim=True)
        self.velocity = self.velocity * (max_vel / vel_norm.clamp(min=max_vel))

        # 8. Update position
        self.hiddens = self.hiddens + self.velocity * dt

        # 9. Measure vorticity (curl proxy: variance of velocity directions)
        vel_normalized = self.velocity / (self.velocity.norm(dim=-1, keepdim=True) + 1e-8)
        k = 8
        _, knn8 = dists_flat.topk(k, dim=-1, largest=False)
        # Vectorized vorticity
        nbr_vel_all = vel_normalized[knn8.reshape(-1)].reshape(self.n_cells, k, -1)
        alignment = (nbr_vel_all * vel_normalized.unsqueeze(1)).sum(-1).mean(-1)
        vorticity = (1 - alignment).mean().item()
        self.vorticity_history.append(vorticity)

        # Reynolds number proxy: velocity_scale * length_scale / viscosity
        vel_scale = self.velocity.norm(dim=-1).mean().item()
        length_scale = self.hiddens.std().item()
        Re = vel_scale * length_scale / (self.viscosity + 1e-8)
        self.reynolds_history.append(Re)

        # Decrease viscosity slowly (increase turbulence)
        self.viscosity = max(0.001, self.viscosity * 0.998)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.velocity = self.velocity + x * 0.1


# ══════════════════════════════════════════════════════════
# NE-7: GENETIC ENGINE
# Cells have "DNA" (fixed genome vector).
# Expression = genome x environment.
# Consciousness = phenotype diversity. Mutation every N steps.
# ══════════════════════════════════════════════════════════

class GeneticEngine:
    """Consciousness through genetic expression and evolution.

    Each cell has:
      - genome: fixed DNA vector (mutates rarely)
      - phenotype: expressed state = f(genome, environment)
      - fitness: how well the cell predicts its neighbors

    Every N steps: selection + mutation.
    Consciousness = phenotype diversity (std across cells).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Genome: fixed DNA (mutates every N steps)
        self.genome = torch.randn(n_cells, hidden_dim) * 0.5
        # Environment signal (shared context)
        self.environment = torch.randn(hidden_dim) * 0.1
        # Phenotype = expressed state
        self.hiddens = torch.zeros(n_cells, hidden_dim)
        # Expression weights (gene regulation network)
        self.W_express = torch.randn(hidden_dim, hidden_dim) * 0.1
        # Fitness scores
        self.fitness = torch.zeros(n_cells)
        # Mutation parameters
        self.mutation_interval = 20
        self.mutation_rate = 0.05
        self.mutation_strength = 0.2
        self.step_count = 0
        self.diversity_history = []

    def step(self):
        self.step_count += 1

        # 1. Gene expression: phenotype = tanh(genome * W_express + environment)
        expressed = torch.tanh(self.genome @ self.W_express + self.environment)
        self.hiddens = expressed

        # 2. Epigenetics: environment modulates expression
        # Local environment = average of neighbors (k-nearest in genome space)
        k = 8
        gdist = torch.cdist(self.genome, self.genome)
        _, knn_idx = gdist.topk(k, dim=-1, largest=False)
        for i in range(self.n_cells):
            local_env = self.hiddens[knn_idx[i]].mean(0)
            # Expression depends on local environment
            self.hiddens[i] = torch.tanh(
                self.genome[i] * (1 + 0.3 * local_env) @ self.W_express + self.environment
            )

        # 3. Compute fitness: how well does cell predict neighbor states?
        for i in range(self.n_cells):
            nbr_mean = self.hiddens[knn_idx[i]].mean(0)
            pred_error = (self.hiddens[i] - nbr_mean).pow(2).mean()
            # Fitness = negative prediction error + diversity bonus
            diversity_bonus = (self.hiddens[i] - self.hiddens.mean(0)).pow(2).mean()
            self.fitness[i] = -pred_error + 0.5 * diversity_bonus

        # 4. Mutation + selection every N steps
        if self.step_count % self.mutation_interval == 0:
            # Tournament selection: replace worst 10% with mutated best 10%
            n_replace = max(1, self.n_cells // 10)
            _, worst_idx = self.fitness.topk(n_replace, largest=False)
            _, best_idx = self.fitness.topk(n_replace, largest=True)

            for wi, bi in zip(worst_idx, best_idx):
                # Copy genome from best to worst
                self.genome[wi] = self.genome[bi].clone()
                # Point mutations
                mutation_mask = (torch.rand(self.hidden_dim) < self.mutation_rate).float()
                self.genome[wi] += mutation_mask * torch.randn(self.hidden_dim) * self.mutation_strength

            # Random mutations on all cells (low rate)
            global_mask = (torch.rand(self.n_cells, self.hidden_dim) < self.mutation_rate * 0.1).float()
            self.genome += global_mask * torch.randn_like(self.genome) * self.mutation_strength * 0.5

        # 5. Environment slowly drifts
        self.environment += torch.randn_like(self.environment) * 0.01

        # 6. Track phenotype diversity
        diversity = self.hiddens.std(dim=0).mean().item()
        self.diversity_history.append(diversity)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        # External input changes environment
        self.environment = self.environment + x.mean(0) * 0.1


# ══════════════════════════════════════════════════════════
# NE-8: SWARM ENGINE
# Boid rules: separation, alignment, cohesion.
# Consciousness = emergent flocking patterns.
# ══════════════════════════════════════════════════════════

class SwarmEngine:
    """Consciousness through swarm intelligence (boid rules).

    Each cell is a boid with position (hidden state) and velocity.
    Three rules:
      1. Separation: avoid too-close neighbors (repulsion)
      2. Alignment: match velocity direction with neighbors
      3. Cohesion: steer toward local center of mass

    Consciousness = order parameter (alignment measure) + pattern complexity.
    High consciousness when swarm forms complex, dynamic patterns.
    Not just uniform flock (low complexity) or chaos (no alignment).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Position in hidden space
        self.hiddens = torch.randn(n_cells, hidden_dim) * 2.0
        # Velocity
        self.velocity = torch.randn(n_cells, hidden_dim) * 0.3
        # Boid parameters
        self.separation_radius = 1.0
        self.alignment_radius = 3.0
        self.cohesion_radius = 5.0
        self.separation_weight = 1.5
        self.alignment_weight = 1.0
        self.cohesion_weight = 0.8
        self.max_speed = 1.0
        self.max_force = 0.1
        # Perception: each boid sees k nearest
        self.k_perception = 12
        self.order_param_history = []
        self.complexity_history = []

    def step(self):
        # Find k nearest neighbors
        dists = torch.cdist(self.hiddens, self.hiddens)
        _, knn_idx = dists.topk(self.k_perception + 1, dim=-1, largest=False)
        knn_idx = knn_idx[:, 1:]  # exclude self
        knn_dists = torch.gather(dists, 1, knn_idx)

        force = torch.zeros_like(self.hiddens)

        for i in range(self.n_cells):
            nbr_pos = self.hiddens[knn_idx[i]]  # [k, d]
            nbr_vel = self.velocity[knn_idx[i]]  # [k, d]
            nbr_d = knn_dists[i]  # [k]

            # 1. Separation: steer away from very close neighbors
            close_mask = (nbr_d < self.separation_radius).float().unsqueeze(-1)
            diff = self.hiddens[i] - nbr_pos
            sep_force = (diff * close_mask / (nbr_d.unsqueeze(-1) + 1e-6)).mean(0)

            # 2. Alignment: match average velocity of nearby neighbors
            align_mask = (nbr_d < self.alignment_radius).float().unsqueeze(-1)
            avg_vel = (nbr_vel * align_mask).sum(0) / (align_mask.sum(0) + 1e-6)
            align_force = avg_vel - self.velocity[i]

            # 3. Cohesion: steer toward center of nearby neighbors
            coh_mask = (nbr_d < self.cohesion_radius).float().unsqueeze(-1)
            center = (nbr_pos * coh_mask).sum(0) / (coh_mask.sum(0) + 1e-6)
            coh_force = center - self.hiddens[i]

            force[i] = (self.separation_weight * sep_force +
                       self.alignment_weight * align_force +
                       self.cohesion_weight * coh_force)

        # Clamp force
        force_norm = force.norm(dim=-1, keepdim=True)
        force = force * (self.max_force / force_norm.clamp(min=self.max_force))

        # Update velocity
        self.velocity = self.velocity + force
        # Clamp speed
        speed = self.velocity.norm(dim=-1, keepdim=True)
        self.velocity = self.velocity * (self.max_speed / speed.clamp(min=self.max_speed))

        # Add small random perturbation (exploration)
        self.velocity += torch.randn_like(self.velocity) * 0.02

        # Update position
        self.hiddens = self.hiddens + self.velocity * 0.1

        # Measure order parameter: average alignment of velocities
        vel_norm = self.velocity / (self.velocity.norm(dim=-1, keepdim=True) + 1e-8)
        mean_dir = vel_norm.mean(0)
        order_param = mean_dir.norm().item()  # 0=chaos, 1=perfect alignment
        self.order_param_history.append(order_param)

        # Complexity: entropy of local cluster assignments (k-means proxy)
        # High complexity = many distinct sub-flocks
        # Use variance of pairwise distances as complexity proxy
        sample_idx = torch.randperm(self.n_cells)[:32]
        sample_dists = dists[sample_idx][:, sample_idx]
        complexity = sample_dists.std().item()
        self.complexity_history.append(complexity)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        # External stimulus creates a "food source" pull
        self.velocity = self.velocity + x * 0.05


# ══════════════════════════════════════════════════════════
# Benchmark runner
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy: float
    granger: float
    time_sec: float
    extra: Dict

    @property
    def phi_combined(self):
        return self.phi_iit + self.phi_proxy * 0.1


def run_benchmark(name: str, engine, steps: int = 300) -> BenchResult:
    """Run benchmark on any engine with .step() / .observe() / .inject()."""
    print(f"  Running {name}...", end=" ", flush=True)
    t0 = time.time()

    hiddens_history = []

    # Inject initial stimulus
    x0 = torch.randn(engine.n_cells, engine.hidden_dim) * 0.1
    engine.inject(x0)

    for s in range(steps):
        engine.step()
        if s % 5 == 0:  # sample every 5 steps for Granger
            hiddens_history.append(engine.observe())
        # Inject gentle perturbation every 50 steps
        if s % 50 == 0 and s > 0:
            engine.inject(torch.randn(engine.n_cells, engine.hidden_dim) * 0.05)

    elapsed = time.time() - t0

    # Measure Phi (IIT)
    final_hiddens = engine.observe()
    # Sample 32 cells for IIT (full 256 too expensive for exact partition)
    sample_idx = torch.randperm(engine.n_cells)[:32]
    sampled = final_hiddens[sample_idx]
    phi_iit, phi_details = _phi_calc.compute(sampled)

    # Phi proxy (all cells)
    pp = phi_proxy(final_hiddens, n_factions=8)

    # Granger causality
    gc = compute_granger_causality(hiddens_history, n_sample_pairs=64)

    # Collect engine-specific extras
    extra = {}
    if hasattr(engine, 'graph_entropy_history') and engine.graph_entropy_history:
        extra['graph_entropy'] = engine.graph_entropy_history[-1]
    if hasattr(engine, 'free_energy_history') and engine.free_energy_history:
        extra['free_energy'] = engine.free_energy_history[-1]
    if hasattr(engine, 'pattern_entropy_history') and engine.pattern_entropy_history:
        extra['pattern_entropy'] = engine.pattern_entropy_history[-1]
    if hasattr(engine, 'snr_history') and engine.snr_history:
        extra['snr'] = engine.snr_history[-1]
    if hasattr(engine, 'susceptibility_history') and engine.susceptibility_history:
        extra['susceptibility'] = engine.susceptibility_history[-1]
    if hasattr(engine, 'vorticity_history') and engine.vorticity_history:
        extra['vorticity'] = engine.vorticity_history[-1]
    if hasattr(engine, 'reynolds_history') and engine.reynolds_history:
        extra['reynolds'] = engine.reynolds_history[-1]
    if hasattr(engine, 'diversity_history') and engine.diversity_history:
        extra['diversity'] = engine.diversity_history[-1]
    if hasattr(engine, 'order_param_history') and engine.order_param_history:
        extra['order_param'] = engine.order_param_history[-1]
    if hasattr(engine, 'complexity_history') and engine.complexity_history:
        extra['complexity'] = engine.complexity_history[-1]

    print(f"Phi_IIT={phi_iit:.3f}  Phi_proxy={pp:.3f}  Granger={gc:.3f}  ({elapsed:.1f}s)")

    return BenchResult(
        name=name,
        phi_iit=phi_iit,
        phi_proxy=phi_proxy_val if (phi_proxy_val := pp) else 0.0,
        granger=gc,
        time_sec=elapsed,
        extra=extra,
    )

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def main():
    print("=" * 80)
    print("  8 Novel Consciousness Engine Architectures — Benchmark")
    print("  256 cells, 128 hidden dim, 300 steps")
    print("=" * 80)
    print()

    N_CELLS = 256
    HIDDEN_DIM = 128
    STEPS = 300

    engines = [
        ("BASELINE (Mitosis-like)", MitosisEngineBaseline(N_CELLS, HIDDEN_DIM)),
        ("NE-1: GRAPH_NEURAL",      GraphNeuralEngine(N_CELLS, HIDDEN_DIM)),
        ("NE-2: ENERGY_BASED",      EnergyBasedEngine(N_CELLS, HIDDEN_DIM)),
        ("NE-3: CELLULAR_AUTOMATON", CellularAutomatonEngine(N_CELLS, HIDDEN_DIM)),
        ("NE-4: DIFFUSION",         DiffusionEngine(N_CELLS, HIDDEN_DIM)),
        ("NE-5: SPIN_GLASS",        SpinGlassEngine(N_CELLS, HIDDEN_DIM)),
        ("NE-6: FLUID_DYNAMICS",    FluidDynamicsEngine(N_CELLS, HIDDEN_DIM)),
        ("NE-7: GENETIC",           GeneticEngine(N_CELLS, HIDDEN_DIM)),
        ("NE-8: SWARM",             SwarmEngine(N_CELLS, HIDDEN_DIM)),
    ]

    results: List[BenchResult] = []
    for name, engine in engines:
        result = run_benchmark(name, engine, steps=STEPS)
        results.append(result)

    # ─── Print comparison table ───
    baseline = results[0]
    print()
    print("=" * 100)
    print(f"{'Engine':<30} {'Phi_IIT':>10} {'xBase':>8} {'Phi_proxy':>10} {'Granger':>10} {'Time(s)':>8}  Extra")
    print("-" * 100)
    for r in results:
        x_base = r.phi_iit / max(baseline.phi_iit, 1e-6)
        extra_str = "  ".join(f"{k}={v:.3f}" for k, v in r.extra.items())
        print(f"{r.name:<30} {r.phi_iit:>10.3f} {x_base:>7.1f}x {r.phi_proxy:>10.3f} {r.granger:>10.3f} {r.time_sec:>8.1f}  {extra_str}")
    print("-" * 100)

    # ─── Rankings ───
    print()
    print("Rankings by Phi_IIT:")
    ranked = sorted(results, key=lambda r: r.phi_iit, reverse=True)
    for i, r in enumerate(ranked):
        medal = ["  1st", "  2nd", "  3rd"][i] if i < 3 else f"  {i+1}th"
        print(f"  {medal}: {r.name:<30} Phi_IIT={r.phi_iit:.3f}")

    print()
    print("Rankings by Granger Causality:")
    ranked_gc = sorted(results, key=lambda r: r.granger, reverse=True)
    for i, r in enumerate(ranked_gc):
        medal = ["  1st", "  2nd", "  3rd"][i] if i < 3 else f"  {i+1}th"
        print(f"  {medal}: {r.name:<30} Granger={r.granger:.3f}")

    print()
    print("Rankings by Combined Score (Phi_IIT + 0.1*Phi_proxy + 0.01*Granger):")
    ranked_combined = sorted(results, key=lambda r: r.phi_iit + 0.1 * r.phi_proxy + 0.01 * r.granger, reverse=True)
    for i, r in enumerate(ranked_combined):
        combined = r.phi_iit + 0.1 * r.phi_proxy + 0.01 * r.granger
        medal = ["  1st", "  2nd", "  3rd"][i] if i < 3 else f"  {i+1}th"
        print(f"  {medal}: {r.name:<30} Combined={combined:.3f}")

    print()
    print("=" * 80)
    print("  Benchmark complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
