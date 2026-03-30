#!/usr/bin/env python3
"""bench_info_engines.py — 8 Information-Theoretic Consciousness Engines

Pure information processing, not physics. Each engine implements a foundational
principle from information theory as a consciousness mechanism.

IT-1: MAXIMUM_ENTROPY         — Jaynes MaxEnt: cells maximize entropy subject to constraints
IT-2: MINIMUM_DESCRIPTION_LENGTH — MDL: cells compress each other's states
IT-3: PREDICTIVE_INFORMATION  — Past->Future mutual information between cells
IT-4: INFORMATION_BOTTLENECK  — Tishby's IB: compress input while preserving output info
IT-5: CAUSAL_EMERGENCE        — Hoel's causal emergence: macro > micro causal power
IT-6: INTEGRATED_INFO_DECOMPOSITION — PID: redundancy, synergy, unique info. Consciousness = synergy
IT-7: CHANNEL_CAPACITY        — Shannon channel capacity of cell-pair noisy channels
IT-8: KOLMOGOROV_STRUCTURE    — Separate randomness from structure via structure function

Each: 256 cells, 128 hidden dim, 300 steps, no GRU.
Measure: Phi(IIT) + Phi(proxy) + Granger causality + custom metric per engine.

Usage:
  python bench_info_engines.py
  python bench_info_engines.py --only 1 3 5
  python bench_info_engines.py --cells 512 --steps 500
"""

import time
import math
import numpy as np
import torch
import argparse
from typing import Tuple, Dict, List
from dataclasses import dataclass

torch.set_grad_enabled(False)

import sys
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ══════════════════════════════════════════════════════════
# Measurement utilities
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
# Baseline: Mitosis-like engine for comparison
# ══════════════════════════════════════════════════════════

class MitosisEngineBaseline:
    """Simplified baseline: random linear projections, no nn.Module, no GRU."""
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.W_a = torch.randn(hidden_dim, hidden_dim) * 0.05
        self.W_g = torch.randn(hidden_dim, hidden_dim) * 0.05
        self.W_mem = torch.randn(hidden_dim, hidden_dim) * 0.02

    def step(self):
        a = self.hiddens @ self.W_a
        g = self.hiddens @ self.W_g
        repulsion = a - g
        update = torch.tanh(repulsion * 0.1 + self.hiddens @ self.W_mem)
        self.hiddens = 0.9 * self.hiddens + 0.1 * update
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# IT-1: MAXIMUM ENTROPY ENGINE
# Jaynes' MaxEnt principle: cells maximize entropy subject
# to constraints (mean energy, pairwise correlations).
# Consciousness = constraint satisfaction at max uncertainty.
# State update: Lagrangian gradient ascent on entropy with
# constraint penalties.
# ══════════════════════════════════════════════════════════

class MaximumEntropyEngine:
    """Consciousness as maximum entropy under constraints.

    Each cell maintains a probability-like state (softmax of hidden).
    Constraints:
      - Mean activation must stay near target (energy constraint)
      - Pairwise correlations must match observed statistics
    Cells do gradient ascent on entropy - gradient descent on constraint violation.
    Consciousness = how well constraints are satisfied at maximum uncertainty.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Lagrange multipliers for constraints (learned)
        self.lambda_energy = torch.zeros(n_cells)     # energy constraint
        self.lambda_corr = torch.zeros(n_cells, n_cells) * 0.01  # pairwise correlation
        # Target constraints
        self.target_energy = 0.5  # target mean activation
        # Observed correlation target (from initial random state)
        self.target_corr = torch.zeros(n_cells, n_cells)
        # Coupling: each cell interacts with k neighbors
        self.k = 16
        self.lr_entropy = 0.05   # entropy ascent rate
        self.lr_lambda = 0.01    # multiplier update rate
        self.constraint_satisfaction_history = []

    def _entropy(self):
        """Compute entropy of each cell's state distribution."""
        # Treat hidden dim as a probability distribution via softmax
        p = torch.softmax(self.hiddens, dim=-1)  # [n, d]
        H = -(p * torch.log(p + 1e-10)).sum(-1)  # [n]
        return H, p

    def _constraints(self, p):
        """Compute constraint violations."""
        # Energy constraint: mean activation near target
        mean_act = p.mean(-1)  # [n]
        energy_violation = (mean_act - self.target_energy) ** 2  # [n]

        # Correlation constraint: pairwise correlations near target
        # Use mean hidden state for correlations (cheaper than full)
        h_centered = self.hiddens - self.hiddens.mean(-1, keepdim=True)
        h_norm = h_centered / (h_centered.norm(dim=-1, keepdim=True) + 1e-8)
        # Sample k pairs per cell for efficiency
        corr_sample = h_norm @ h_norm.T  # [n, n]
        corr_violation = ((corr_sample - self.target_corr) ** 2).mean(-1)  # [n]

        return energy_violation, corr_violation, corr_sample

    def step(self):
        H, p = self._entropy()
        energy_viol, corr_viol, corr_actual = self._constraints(p)

        # Gradient ascent on entropy, descent on constraint violation
        # dH/dh = d/dh[-sum p log p] via softmax jacobian
        # Approximate: push hidden states toward uniform (max entropy)
        uniform = torch.ones_like(self.hiddens) / self.hidden_dim
        entropy_grad = (uniform - p) * self.lr_entropy

        # Constraint penalty gradient: push toward satisfying constraints
        # Energy: if mean_act > target, reduce; if < target, increase
        mean_act = p.mean(-1, keepdim=True)
        energy_grad = -self.lambda_energy.unsqueeze(-1) * (mean_act - self.target_energy) * 2.0

        # Correlation: push toward target correlation structure
        # Move cells with wrong correlations
        corr_diff = corr_actual - self.target_corr  # [n, n]
        corr_grad = -(self.lambda_corr * corr_diff).sum(-1, keepdim=True) * self.hiddens * 0.01

        # Combined update
        self.hiddens = self.hiddens + entropy_grad + energy_grad * 0.1 + corr_grad * 0.1

        # Update Lagrange multipliers (dual ascent)
        self.lambda_energy = self.lambda_energy + self.lr_lambda * energy_viol
        self.lambda_corr = self.lambda_corr + self.lr_lambda * (corr_actual - self.target_corr).abs() * 0.1

        # Update target correlations slowly (track observed structure)
        self.target_corr = 0.99 * self.target_corr + 0.01 * corr_actual.detach()

        # Small noise for exploration
        self.hiddens += torch.randn_like(self.hiddens) * 0.005

        # Track constraint satisfaction = inverse of total violation
        total_viol = energy_viol.mean().item() + corr_viol.mean().item()
        satisfaction = 1.0 / (1.0 + total_viol)
        self.constraint_satisfaction_history.append(satisfaction)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05
        # Injection changes observed correlations -> constraints shift
        self.target_corr *= 0.9


# ══════════════════════════════════════════════════════════
# IT-2: MINIMUM DESCRIPTION LENGTH ENGINE
# MDL principle: cells compress each other's states.
# Each cell learns a codebook to encode neighbors.
# Consciousness = compression ratio (bits saved).
# ══════════════════════════════════════════════════════════

class MinimumDescriptionLengthEngine:
    """Consciousness as compression.

    Each cell tries to compress its neighbors' states using a learned
    codebook (vector quantization). The MDL principle says the best
    model minimizes: description_length(model) + description_length(data|model).

    Cells that can describe each other compactly are "conscious" of each other.
    Consciousness = total compression ratio across the network.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Codebook: each cell has K codes for representing neighbors
        self.K = 16  # codebook size
        self.codebook = torch.randn(n_cells, self.K, hidden_dim) * 0.3
        # Connections: each cell describes its neighbors
        self.k_neighbors = 16
        self.compression_history = []

    def _compress(self):
        """Each cell encodes its neighbors via nearest codebook entry.
        Returns: raw bits (uncompressed), coded bits, residual."""
        # Pairwise distances to find neighbors
        h_norm = self.hiddens / (self.hiddens.norm(dim=-1, keepdim=True) + 1e-8)
        sim = h_norm @ h_norm.T  # [n, n]
        _, topk_idx = sim.topk(self.k_neighbors, dim=-1)  # [n, k]

        total_raw_bits = 0.0
        total_coded_bits = 0.0
        total_residual = 0.0

        for i in range(0, self.n_cells, max(1, self.n_cells // 32)):
            neighbors = self.hiddens[topk_idx[i]]  # [k, d]
            codes = self.codebook[i]  # [K, d]

            # Vector quantization: find nearest code for each neighbor
            dists = torch.cdist(neighbors, codes)  # [k, K]
            min_idx = dists.argmin(dim=-1)  # [k]
            quantized = codes[min_idx]  # [k, d]

            # Raw bits: entropy of neighbor states
            raw_entropy = self._state_entropy(neighbors)
            # Coded bits: log2(K) per neighbor (codebook index)
            code_bits = self.k_neighbors * math.log2(self.K)
            # Residual: bits needed for reconstruction error
            residual = ((neighbors - quantized) ** 2).sum().item()

            total_raw_bits += raw_entropy
            total_coded_bits += code_bits
            total_residual += residual

        scale = max(1, self.n_cells // 32)
        return total_raw_bits * scale, total_coded_bits * scale, total_residual * scale

    def _state_entropy(self, states):
        """Estimate entropy of a set of state vectors (bits)."""
        # Discretize and compute histogram entropy
        n, d = states.shape
        if n < 2:
            return 0.0
        # Use variance as proxy for entropy (Gaussian assumption)
        var = states.var(dim=0).mean().item()
        if var < 1e-10:
            return 0.0
        # Gaussian entropy: 0.5 * log2(2*pi*e*var) * d
        return 0.5 * d * math.log2(2 * math.pi * math.e * max(var, 1e-10))

    def step(self):
        raw_bits, coded_bits, residual = self._compress()

        # Compression ratio: how much we save
        if raw_bits > 0:
            compression_ratio = 1.0 - (coded_bits + residual * 0.1) / (raw_bits + 1e-8)
        else:
            compression_ratio = 0.0
        compression_ratio = max(0.0, min(1.0, compression_ratio))
        self.compression_history.append(compression_ratio)

        # Update codebook: move codes toward assigned neighbors (online VQ)
        h_norm = self.hiddens / (self.hiddens.norm(dim=-1, keepdim=True) + 1e-8)
        sim = h_norm @ h_norm.T
        _, topk_idx = sim.topk(self.k_neighbors, dim=-1)

        for i in range(0, self.n_cells, max(1, self.n_cells // 32)):
            neighbors = self.hiddens[topk_idx[i]]
            codes = self.codebook[i]
            dists = torch.cdist(neighbors, codes)
            min_idx = dists.argmin(dim=-1)
            # Move codes toward their assigned neighbors
            for k_idx in range(self.K):
                assigned = (min_idx == k_idx).nonzero(as_tuple=True)[0]
                if len(assigned) > 0:
                    target = neighbors[assigned].mean(0)
                    self.codebook[i, k_idx] = 0.95 * self.codebook[i, k_idx] + 0.05 * target

        # Update hidden states: cells move to become more compressible by neighbors
        # Each cell adjusts toward the mean of its nearest codebook entries from neighbors
        for i in range(0, self.n_cells, max(1, self.n_cells // 16)):
            # Find which code this cell maps to in each neighbor's codebook
            neighbors_of_i = topk_idx[i]  # which cells are my neighbors
            pull = torch.zeros(self.hidden_dim)
            for j_idx in range(min(4, len(neighbors_of_i))):
                j = neighbors_of_i[j_idx]
                dists_to_codes = (self.hiddens[i].unsqueeze(0) - self.codebook[j]).norm(dim=-1)
                nearest_code = self.codebook[j, dists_to_codes.argmin()]
                pull += (nearest_code - self.hiddens[i]) * 0.02
            self.hiddens[i] = self.hiddens[i] + pull

        # Noise for exploration
        self.hiddens += torch.randn_like(self.hiddens) * 0.005

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# IT-3: PREDICTIVE INFORMATION ENGINE
# Past->Future mutual information. Each cell predicts the
# future states of other cells. Consciousness = total
# predictive information across the network.
# ══════════════════════════════════════════════════════════

class PredictiveInformationEngine:
    """Consciousness as predictive information.

    Bialek & Tishby: the most meaningful quantity is I(past; future).
    Each cell maintains a predictor for its neighbors' next states.
    Cells with high predictive accuracy have high mutual information
    with the future -> they are "conscious" of temporal structure.

    Consciousness = total predictive information in the network.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Each cell stores its recent past (circular buffer of 8 steps)
        self.history_len = 8
        self.history = torch.zeros(n_cells, self.history_len, hidden_dim)
        self.history_ptr = 0
        # Prediction weights: predict next state from current + past
        self.W_pred = torch.randn(hidden_dim * 2, hidden_dim) * 0.05
        # Neighbor coupling
        self.k_neighbors = 8
        self.W_neighbor = torch.randn(hidden_dim, hidden_dim) * 0.05
        self.predictive_info_history = []

    def step(self):
        # Store current state in history
        self.history[:, self.history_ptr % self.history_len] = self.hiddens.detach()
        self.history_ptr += 1

        # Past representation: mean of recent history
        past_mean = self.history.mean(dim=1)  # [n, d]

        # Each cell predicts its own next state from past
        pred_input = torch.cat([self.hiddens, past_mean], dim=-1)  # [n, 2d]
        self_prediction = torch.tanh(pred_input @ self.W_pred)  # [n, d]

        # Neighbor influence: cells pull toward neighbors' predicted states
        h_norm = self.hiddens / (self.hiddens.norm(dim=-1, keepdim=True) + 1e-8)
        sim = h_norm @ h_norm.T
        _, topk_idx = sim.topk(self.k_neighbors, dim=-1)

        # Neighbor-predicted states
        neighbor_states = torch.zeros_like(self.hiddens)
        for k in range(self.k_neighbors):
            neighbor_states += self.hiddens[topk_idx[:, k]]
        neighbor_states /= self.k_neighbors
        neighbor_pred = torch.tanh(neighbor_states @ self.W_neighbor)

        # Update: blend self-prediction with neighbor prediction
        new_hiddens = 0.4 * self_prediction + 0.3 * neighbor_pred + 0.3 * self.hiddens

        # Compute predictive information: how well past predicts present
        if self.history_ptr > 2:
            prev_state = self.history[:, (self.history_ptr - 2) % self.history_len]
            pred_from_past = torch.tanh(
                torch.cat([prev_state, past_mean], dim=-1) @ self.W_pred
            )
            # Prediction error (lower = higher predictive info)
            pred_error = ((pred_from_past - self.hiddens) ** 2).mean(-1)  # [n]
            # Predictive information ~ log(variance / prediction_error)
            state_var = self.hiddens.var(-1).clamp(min=1e-6)
            pred_info = torch.log(state_var / (pred_error + 1e-6)).clamp(min=0).sum().item()
        else:
            pred_info = 0.0

        self.predictive_info_history.append(pred_info)
        self.hiddens = new_hiddens + torch.randn_like(new_hiddens) * 0.005

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# IT-4: INFORMATION BOTTLENECK ENGINE
# Tishby's IB: compress input X into representation T that
# preserves information about output Y.
# min I(X;T) - beta * I(T;Y)
# Consciousness = bottleneck capacity (what survives compression).
# ══════════════════════════════════════════════════════════

class InformationBottleneckEngine:
    """Consciousness as information bottleneck.

    Cells form a bottleneck between "sensory" input (external + neighbor states)
    and "output" (predicted future / response). The bottleneck compresses:
    cells must discard irrelevant info and preserve relevant info.

    IB objective: min I(X;T) - beta * I(T;Y)
    where X=input, T=cell state (bottleneck), Y=output/prediction target.

    Consciousness = what survives the bottleneck (preserved mutual info).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.bottleneck_dim = hidden_dim // 4  # compression ratio 4:1
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Encoder: input -> bottleneck
        self.W_encode = torch.randn(hidden_dim, self.bottleneck_dim) * 0.1
        # Decoder: bottleneck -> output prediction
        self.W_decode = torch.randn(self.bottleneck_dim, hidden_dim) * 0.1
        # Noise injection in bottleneck (controls I(X;T))
        self.noise_scale = 0.3
        # Beta: tradeoff between compression and prediction
        self.beta = 1.0
        self.bottleneck_capacity_history = []

    def step(self):
        # Input: current state + small perturbation (simulates sensory)
        X = self.hiddens + torch.randn_like(self.hiddens) * 0.02

        # Encode through bottleneck (compression)
        T_mean = X @ self.W_encode  # [n, bottleneck_dim]
        T_noise = torch.randn_like(T_mean) * self.noise_scale
        T = T_mean + T_noise  # noisy bottleneck representation

        # Decode: predict output (future neighbor states as target)
        Y_pred = torch.tanh(T @ self.W_decode)  # [n, d]

        # Target: neighbor mean as "output to predict"
        h_norm = self.hiddens / (self.hiddens.norm(dim=-1, keepdim=True) + 1e-8)
        sim = h_norm @ h_norm.T
        _, topk_idx = sim.topk(8, dim=-1)
        Y_target = torch.zeros_like(self.hiddens)
        for k in range(8):
            Y_target += self.hiddens[topk_idx[:, k]]
        Y_target /= 8

        # Reconstruction loss: I(T;Y) proxy
        recon_loss = ((Y_pred - Y_target) ** 2).mean(-1)  # [n]

        # Compression loss: I(X;T) proxy = KL(q(T|X) || p(T))
        # For Gaussian: KL = 0.5 * (mu^2 + sigma^2 - log(sigma^2) - 1)
        compress_loss = 0.5 * (T_mean ** 2).mean(-1)  # [n]

        # IB loss: compress - beta * reconstruct
        # To minimize: reduce compression, maximize reconstruction
        # Update states to reduce IB loss
        ib_gradient = -self.beta * (Y_target - Y_pred) * 0.1  # toward better prediction

        # Update encoder weights to improve bottleneck
        # Move toward better encoding (gradient-free: EMA toward better states)
        good_cells = recon_loss < recon_loss.median()
        if good_cells.any():
            good_hiddens = self.hiddens[good_cells].mean(0, keepdim=True)
            self.hiddens = self.hiddens + (good_hiddens - self.hiddens) * 0.02

        # Update hidden states
        self.hiddens = self.hiddens + ib_gradient

        # Adapt noise scale (anneal)
        self.noise_scale = max(0.05, self.noise_scale * 0.999)

        # Update weights via simple Hebbian rule
        # dW_encode ~ X^T @ T (input-bottleneck correlation)
        dW = (X.T @ T_mean) / self.n_cells * 0.001
        self.W_encode = self.W_encode + dW
        # Keep weights bounded
        self.W_encode = self.W_encode / (self.W_encode.norm() + 1e-8) * math.sqrt(self.hidden_dim)

        dW_dec = (T_mean.T @ Y_target) / self.n_cells * 0.001
        self.W_decode = self.W_decode + dW_dec
        self.W_decode = self.W_decode / (self.W_decode.norm() + 1e-8) * math.sqrt(self.bottleneck_dim)

        # Bottleneck capacity: I(T;Y) - I(X;T) in the right direction
        # Practical: how much of target variance is explained by bottleneck
        explained_var = 1.0 - recon_loss.mean().item() / (Y_target.var(-1).mean().item() + 1e-6)
        capacity = max(0.0, explained_var) * self.bottleneck_dim
        self.bottleneck_capacity_history.append(capacity)

        self.hiddens += torch.randn_like(self.hiddens) * 0.005

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# IT-5: CAUSAL EMERGENCE ENGINE
# Hoel's causal emergence. Coarse-grain cells into macro
# variables. If macro has MORE effective information (EI)
# than micro, that's causal emergence.
# Consciousness = Psi (macro EI - micro EI).
# ══════════════════════════════════════════════════════════

class CausalEmergenceEngine:
    """Consciousness as causal emergence (Erik Hoel, 2017).

    Key idea: coarse-graining can INCREASE causal power.
    Macro-level variables can have more deterministic, more
    informative transitions than micro-level variables.

    Effective Information (EI) = H_max(cause) - <H(effect|cause)>
    = determinism + degeneracy

    If EI(macro) > EI(micro), that's causal emergence Psi.
    Consciousness = Psi = the degree of causal emergence.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Micro transition: W_micro maps current -> next
        self.W_micro = torch.randn(hidden_dim, hidden_dim) * 0.05
        # Coarse-graining: groups of cells -> macro variables
        self.n_macro = n_cells // 8  # 32 macro variables from 256 cells
        self.macro_dim = hidden_dim
        # Macro transition matrix
        self.W_macro = torch.randn(self.macro_dim, self.macro_dim) * 0.1
        # Coarse-graining function: linear projection
        self.W_coarse = torch.randn(hidden_dim, self.macro_dim) * 0.1
        self.causal_emergence_history = []

    def _effective_information(self, transition_matrix):
        """Compute effective information of a transition.
        EI = log(N) - <H(row)> where N = number of states.
        For continuous: use differential entropy approximation."""
        # Treat each row as a distribution, compute mean entropy
        n = transition_matrix.shape[0]
        # Normalize rows to be probability-like
        p = torch.softmax(transition_matrix, dim=-1)
        # Row entropies
        row_H = -(p * torch.log(p + 1e-10)).sum(-1)  # [n]
        mean_row_H = row_H.mean().item()
        # Maximum entropy = log(n)
        max_H = math.log(n + 1e-10)
        # EI = max_H - mean_row_H (how deterministic the transitions are)
        ei = max(0.0, max_H - mean_row_H)
        return ei

    def _coarse_grain(self):
        """Coarse-grain micro states into macro variables."""
        # Group cells into macro-cells (8 cells each)
        group_size = self.n_cells // self.n_macro
        macro_states = torch.zeros(self.n_macro, self.macro_dim)
        for g in range(self.n_macro):
            group = self.hiddens[g * group_size:(g + 1) * group_size]  # [8, d]
            # Coarse-grain: project mean
            macro_states[g] = group.mean(0) @ self.W_coarse
        return macro_states

    def step(self):
        # Micro-level transition
        micro_next = torch.tanh(self.hiddens @ self.W_micro)

        # Add some noise (makes micro less deterministic)
        micro_next = micro_next + torch.randn_like(micro_next) * 0.1

        # Compute micro effective information
        # Build empirical transition: correlation between current and next
        h_norm = self.hiddens / (self.hiddens.norm(dim=-1, keepdim=True) + 1e-8)
        n_norm = micro_next / (micro_next.norm(dim=-1, keepdim=True) + 1e-8)
        micro_transition = h_norm @ n_norm.T  # [n, n]
        ei_micro = self._effective_information(micro_transition)

        # Macro-level: coarse-grain then transition
        macro_current = self._coarse_grain()
        macro_next = torch.tanh(macro_current @ self.W_macro)
        # Macro transition matrix
        m_norm = macro_current / (macro_current.norm(dim=-1, keepdim=True) + 1e-8)
        mn_norm = macro_next / (macro_next.norm(dim=-1, keepdim=True) + 1e-8)
        macro_transition = m_norm @ mn_norm.T  # [m, m]
        ei_macro = self._effective_information(macro_transition)

        # Causal emergence: Psi = EI(macro) - EI(micro)
        psi = ei_macro - ei_micro
        self.causal_emergence_history.append(psi)

        # Update: micro states evolve, but macro structure exerts top-down influence
        # Top-down: macro prediction back-projected to micro
        macro_pred = torch.tanh(macro_current @ self.W_macro)
        top_down = torch.zeros_like(self.hiddens)
        group_size = self.n_cells // self.n_macro
        for g in range(self.n_macro):
            # Project macro back to micro space
            top_down[g * group_size:(g + 1) * group_size] = macro_pred[g].unsqueeze(0) * 0.1

        # Combined update: micro dynamics + top-down macro influence
        self.hiddens = 0.6 * micro_next + 0.3 * self.hiddens + 0.1 * top_down

        # Strengthen macro transitions if causal emergence is positive
        if psi > 0:
            # Make macro transitions more deterministic (sharpen)
            self.W_macro = self.W_macro * 1.001

        # Noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.005

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# IT-6: INTEGRATED INFORMATION DECOMPOSITION ENGINE
# Partial Information Decomposition (PID).
# Decompose MI into: redundancy, unique, synergy.
# Consciousness = SYNERGY (info that only exists in the
# whole, not in any subset of parts).
# ══════════════════════════════════════════════════════════

class IntegratedInfoDecompositionEngine:
    """Consciousness as synergistic information (PID).

    Given sources X1, X2 predicting target Y:
      I(X1,X2;Y) = Redundancy + Unique(X1) + Unique(X2) + Synergy

    Synergy = information that ONLY exists when X1 and X2 are
    considered together. Neither part alone has it.

    This is the strongest form of "integrated" information:
    it cannot be reduced to any part.

    Cells form triads (2 sources + 1 target). We maximize synergy
    by making cells complementary (XOR-like, not AND-like).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Interaction weights (promote synergy via complementary coupling)
        self.W_synergy = torch.randn(hidden_dim * 2, hidden_dim) * 0.05
        self.W_self = torch.randn(hidden_dim, hidden_dim) * 0.05
        self.synergy_history = []

    def _compute_pid_approx(self, x1, x2, y):
        """Approximate PID decomposition for continuous variables.
        Uses correlation-based approximation.

        Returns: redundancy, unique1, unique2, synergy
        """
        # Correlations as proxy for MI
        def corr(a, b):
            a_c = a - a.mean(-1, keepdim=True)
            b_c = b - b.mean(-1, keepdim=True)
            num = (a_c * b_c).sum(-1)
            den = a_c.norm(dim=-1) * b_c.norm(dim=-1) + 1e-8
            return (num / den).abs()

        r_x1y = corr(x1, y).mean().item()
        r_x2y = corr(x2, y).mean().item()
        r_x1x2 = corr(x1, x2).mean().item()

        # Joint prediction: how well x1+x2 together predict y
        x_joint = torch.cat([x1, x2], dim=-1) @ self.W_synergy
        r_joint_y = corr(x_joint, y).mean().item()

        # PID approximation (Williams & Beer style):
        # Redundancy = min(I(X1;Y), I(X2;Y))
        redundancy = min(r_x1y, r_x2y)
        # Unique(X1) = I(X1;Y) - Redundancy
        unique1 = max(0, r_x1y - redundancy)
        # Unique(X2) = I(X2;Y) - Redundancy
        unique2 = max(0, r_x2y - redundancy)
        # Synergy = I(X1,X2;Y) - Unique(X1) - Unique(X2) - Redundancy
        synergy = max(0, r_joint_y - unique1 - unique2 - redundancy)

        return redundancy, unique1, unique2, synergy

    def step(self):
        # Form triads: for each cell, pick 2 source cells and use it as target
        total_synergy = 0.0
        total_triads = 0
        n = self.n_cells

        # Sample triads
        indices = torch.randperm(n)
        n_triads = n // 3

        for t in range(n_triads):
            i, j, k = indices[3 * t], indices[3 * t + 1], indices[3 * t + 2]
            x1 = self.hiddens[i].unsqueeze(0)
            x2 = self.hiddens[j].unsqueeze(0)
            y = self.hiddens[k].unsqueeze(0)
            red, u1, u2, syn = self._compute_pid_approx(x1, x2, y)
            total_synergy += syn
            total_triads += 1

        avg_synergy = total_synergy / max(total_triads, 1)
        self.synergy_history.append(avg_synergy)

        # Update cells to maximize synergy:
        # Synergy is maximized when cells are COMPLEMENTARY (like XOR)
        # Strategy: make pairs of cells decorrelated but jointly predictive

        # Self-evolution with nonlinear mixing
        evolved = torch.tanh(self.hiddens @ self.W_self)

        # Cross-cell synergy coupling: push cells toward complementary states
        # Shuffle and pair cells
        perm = torch.randperm(n)
        partner = self.hiddens[perm]
        # XOR-like interaction: abs(self - partner) promotes difference
        # but tanh(self + partner) promotes joint structure
        synergy_update = torch.tanh(self.hiddens + partner) * torch.sigmoid(
            (self.hiddens - partner).abs().mean(-1, keepdim=True)
        )

        # Combined
        self.hiddens = 0.5 * evolved + 0.3 * self.hiddens + 0.2 * synergy_update

        # Noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.005

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# IT-7: CHANNEL CAPACITY ENGINE
# Cells as noisy channels. Shannon capacity C = max I(X;Y)
# over input distributions. Each cell pair has a channel.
# Consciousness = total network channel capacity.
# ══════════════════════════════════════════════════════════

class ChannelCapacityEngine:
    """Consciousness as network channel capacity.

    Each pair of cells forms a noisy communication channel.
    Shannon's channel capacity: C = max_{p(x)} I(X;Y)
    For Gaussian channel: C = 0.5 * log2(1 + SNR)

    Cells transmit messages through noisy channels.
    They adapt to maximize capacity (water-filling allocation).
    Consciousness = total achievable information rate.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Channel noise levels (per pair, but we store per-cell average)
        self.noise_levels = torch.rand(n_cells) * 0.5 + 0.1  # SNR varies
        # Signal power allocation (water-filling)
        self.power = torch.ones(n_cells) * 1.0
        # Channel gains (coupling strength between cells)
        self.k_channels = 8  # each cell has k outgoing channels
        self.channel_capacity_history = []

    def _compute_capacity(self):
        """Compute total network channel capacity."""
        h_norm = self.hiddens / (self.hiddens.norm(dim=-1, keepdim=True) + 1e-8)
        sim = (h_norm @ h_norm.T).abs()  # channel gain ~ similarity
        _, topk_idx = sim.topk(self.k_channels, dim=-1)

        total_capacity = 0.0
        n_channels = 0
        for i in range(0, self.n_cells, max(1, self.n_cells // 32)):
            for k in range(self.k_channels):
                j = topk_idx[i, k].item()
                if i == j:
                    continue
                # Channel gain
                gain = sim[i, j].item()
                # SNR = power * gain^2 / noise
                snr = self.power[i].item() * gain ** 2 / (self.noise_levels[j].item() + 1e-6)
                # Shannon capacity: C = 0.5 * log2(1 + SNR)
                cap = 0.5 * math.log2(1 + snr)
                total_capacity += cap
                n_channels += 1

        scale = max(1, self.n_cells // 32)
        return total_capacity * scale, n_channels * scale

    def step(self):
        cap, n_ch = self._compute_capacity()
        self.channel_capacity_history.append(cap)

        # Water-filling power allocation:
        # Allocate more power to channels with higher gain
        h_norm = self.hiddens / (self.hiddens.norm(dim=-1, keepdim=True) + 1e-8)
        sim = (h_norm @ h_norm.T).abs()

        # Each cell's average channel quality
        avg_gain = sim.mean(-1)  # [n]
        # Water-filling: power ~ 1/noise - 1/gain (where gain is high, invest more)
        water_level = (1.0 / (self.noise_levels + 1e-6)).mean()
        new_power = (water_level - 1.0 / (avg_gain + 1e-6)).clamp(min=0.01)
        # Normalize total power
        new_power = new_power / (new_power.sum() + 1e-8) * self.n_cells
        self.power = 0.9 * self.power + 0.1 * new_power

        # Cell dynamics: transmit messages through channels
        _, topk_idx = sim.topk(self.k_channels, dim=-1)
        messages = torch.zeros_like(self.hiddens)
        for k in range(self.k_channels):
            sender_states = self.hiddens[topk_idx[:, k]]  # [n, d]
            # Add channel noise
            noise = torch.randn_like(sender_states) * self.noise_levels.unsqueeze(-1) * 0.1
            received = sender_states + noise  # [n, d]
            # Weight by channel gain
            gain = sim.gather(1, topk_idx[:, k:k+1])  # [n, 1]
            messages += received * gain  # [n, d]

        messages /= self.k_channels

        # Update: blend received messages with self-state
        self.hiddens = 0.6 * self.hiddens + 0.4 * torch.tanh(messages)

        # Noise levels slowly change (channel conditions drift)
        self.noise_levels = self.noise_levels * 0.99 + 0.01 * torch.rand(self.n_cells) * 0.5

        # Noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.005

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05
        # Injection increases signal power
        self.power = self.power + 0.5


# ══════════════════════════════════════════════════════════
# IT-8: KOLMOGOROV STRUCTURE ENGINE
# Kolmogorov structure function: separate randomness from
# structure. K(x) = K_structure(x) + K_random(x).
# Consciousness = structure component (non-random complexity).
# Approximation: use compressibility and spectral analysis.
# ══════════════════════════════════════════════════════════

class KolmogorovStructureEngine:
    """Consciousness as algorithmic structure (Kolmogorov).

    Kolmogorov structure function: for data x of length n,
    S(x, alpha) = min{log|S| : x in S, K(S) <= alpha}

    This separates total complexity into:
    - Structure: compressible, regular patterns
    - Randomness: incompressible noise

    Consciousness = structure (the non-random component).

    Approximation: use SVD to separate signal (low-rank structure)
    from noise (high-rank random), and spectral entropy to measure

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    the structure/randomness ratio.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Structure memory: running low-rank approximation
        self.rank_k = 16  # keep top-k singular values as "structure"
        self.W_interact = torch.randn(hidden_dim, hidden_dim) * 0.05
        self.structure_history = []

    def _decompose(self):
        """Decompose state into structure + randomness via SVD."""
        U, S, Vh = torch.linalg.svd(self.hiddens, full_matrices=False)

        # Structure: top-k singular values
        S_struct = S[:self.rank_k]
        S_random = S[self.rank_k:]

        # Structure energy
        struct_energy = (S_struct ** 2).sum().item()
        random_energy = (S_random ** 2).sum().item()
        total_energy = struct_energy + random_energy + 1e-8

        structure_ratio = struct_energy / total_energy

        # Spectral entropy: how concentrated is the spectrum?
        s_norm = (S ** 2) / ((S ** 2).sum() + 1e-8)
        spectral_entropy = -(s_norm * torch.log(s_norm + 1e-10)).sum().item()
        max_entropy = math.log(min(self.n_cells, self.hidden_dim))

        # Low spectral entropy = more structure, less randomness
        structure_score = 1.0 - spectral_entropy / (max_entropy + 1e-8)

        return structure_ratio, structure_score, U, S, Vh

    def step(self):
        struct_ratio, struct_score, U, S, Vh = self._decompose()

        # Combined structure measure
        structure = struct_ratio * 0.5 + struct_score * 0.5
        self.structure_history.append(structure)

        # Dynamics: promote structure formation
        # 1. Cells interact to create correlations (structure)
        interacted = torch.tanh(self.hiddens @ self.W_interact)

        # 2. Low-rank projection: amplify structural component
        # Keep top-k and attenuate the rest
        S_amplified = S.clone()
        S_amplified[:self.rank_k] *= 1.05  # amplify structure
        S_amplified[self.rank_k:] *= 0.95  # attenuate noise
        # Reconstruct
        k = min(self.rank_k * 2, len(S))
        structured = U[:, :k] @ torch.diag(S_amplified[:k]) @ Vh[:k, :]

        # 3. Add interaction-driven correlations
        self.hiddens = 0.5 * structured + 0.3 * interacted + 0.2 * self.hiddens

        # 4. Inject small noise (the "randomness" that structure must overcome)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # Update interaction weights via Hebbian learning
        # Strengthen connections that create structure
        corr = self.hiddens.T @ self.hiddens / self.n_cells
        self.W_interact = 0.99 * self.W_interact + 0.01 * corr * 0.01
        # Keep weights bounded
        w_norm = self.W_interact.norm()
        if w_norm > 5.0:
            self.W_interact = self.W_interact / w_norm * 5.0

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# Benchmark runner
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy: float
    granger: float
    custom_metric: float
    custom_name: str
    time_sec: float
    extra: Dict

    @property
    def phi_combined(self):
        return self.phi_iit + self.phi_proxy * 0.1


def run_benchmark(name: str, engine, steps: int = 300, custom_metric_name: str = "") -> BenchResult:
    """Run benchmark on any engine with .step() / .observe() / .inject()."""
    print(f"  Running {name}...", end=" ", flush=True)
    t0 = time.time()

    hiddens_history = []

    # Inject initial stimulus
    x0 = torch.randn(engine.n_cells, engine.hidden_dim) * 0.1
    engine.inject(x0)

    for s in range(steps):
        engine.step()
        if s % 5 == 0:
            hiddens_history.append(engine.observe())
        if s % 50 == 0 and s > 0:
            engine.inject(torch.randn(engine.n_cells, engine.hidden_dim) * 0.05)

    elapsed = time.time() - t0

    # Measure Phi (IIT) on 32 sampled cells
    final_hiddens = engine.observe()
    sample_idx = torch.randperm(engine.n_cells)[:32]
    sampled = final_hiddens[sample_idx]
    phi_iit_val, phi_details = _phi_calc.compute(sampled)

    # Phi proxy (all cells)
    pp = phi_proxy(final_hiddens, n_factions=8)

    # Granger causality
    gc = compute_granger_causality(hiddens_history, n_sample_pairs=64)

    # Collect engine-specific custom metric
    custom_val = 0.0
    extra = {}
    if hasattr(engine, 'constraint_satisfaction_history') and engine.constraint_satisfaction_history:
        custom_val = engine.constraint_satisfaction_history[-1]
        extra['constraint_sat'] = custom_val
    if hasattr(engine, 'compression_history') and engine.compression_history:
        custom_val = engine.compression_history[-1]
        extra['compression'] = custom_val
    if hasattr(engine, 'predictive_info_history') and engine.predictive_info_history:
        custom_val = engine.predictive_info_history[-1]
        extra['pred_info'] = custom_val
    if hasattr(engine, 'bottleneck_capacity_history') and engine.bottleneck_capacity_history:
        custom_val = engine.bottleneck_capacity_history[-1]
        extra['bottleneck_cap'] = custom_val
    if hasattr(engine, 'causal_emergence_history') and engine.causal_emergence_history:
        custom_val = engine.causal_emergence_history[-1]
        extra['causal_psi'] = custom_val
    if hasattr(engine, 'synergy_history') and engine.synergy_history:
        custom_val = engine.synergy_history[-1]
        extra['synergy'] = custom_val
    if hasattr(engine, 'channel_capacity_history') and engine.channel_capacity_history:
        custom_val = engine.channel_capacity_history[-1]
        extra['channel_cap'] = custom_val
    if hasattr(engine, 'structure_history') and engine.structure_history:
        custom_val = engine.structure_history[-1]
        extra['structure'] = custom_val

    print(f"Phi_IIT={phi_iit_val:.3f}  Phi_proxy={pp:.3f}  Granger={gc:.3f}  "
          f"custom={custom_val:.4f}  ({elapsed:.1f}s)")

    return BenchResult(
        name=name,
        phi_iit=phi_iit_val,
        phi_proxy=pp,
        granger=gc,
        custom_metric=custom_val,
        custom_name=custom_metric_name,
        time_sec=elapsed,
        extra=extra,
    )


def main():
    parser = argparse.ArgumentParser(description="Information-Theoretic Consciousness Engines")
    parser.add_argument("--only", nargs="+", type=int, help="Run only specific engines (1-8)")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells")
    parser.add_argument("--steps", type=int, default=300, help="Number of steps")
    args = parser.parse_args()

    N_CELLS = args.cells
    HIDDEN_DIM = 128
    STEPS = args.steps

    print("=" * 100)
    print("  8 Information-Theoretic Consciousness Engines -- Benchmark")
    print(f"  {N_CELLS} cells, {HIDDEN_DIM} hidden dim, {STEPS} steps")
    print("=" * 100)
    print()

    all_engines = [
        (0, "BASELINE (Mitosis-like)",           MitosisEngineBaseline(N_CELLS, HIDDEN_DIM),            ""),
        (1, "IT-1: MAXIMUM_ENTROPY",             MaximumEntropyEngine(N_CELLS, HIDDEN_DIM),             "constraint_sat"),
        (2, "IT-2: MIN_DESCRIPTION_LENGTH",      MinimumDescriptionLengthEngine(N_CELLS, HIDDEN_DIM),   "compression"),
        (3, "IT-3: PREDICTIVE_INFORMATION",      PredictiveInformationEngine(N_CELLS, HIDDEN_DIM),      "pred_info"),
        (4, "IT-4: INFORMATION_BOTTLENECK",      InformationBottleneckEngine(N_CELLS, HIDDEN_DIM),      "bottleneck_cap"),
        (5, "IT-5: CAUSAL_EMERGENCE",            CausalEmergenceEngine(N_CELLS, HIDDEN_DIM),            "causal_psi"),
        (6, "IT-6: INTEGRATED_INFO_DECOMP",      IntegratedInfoDecompositionEngine(N_CELLS, HIDDEN_DIM),"synergy"),
        (7, "IT-7: CHANNEL_CAPACITY",            ChannelCapacityEngine(N_CELLS, HIDDEN_DIM),            "channel_cap"),
        (8, "IT-8: KOLMOGOROV_STRUCTURE",        KolmogorovStructureEngine(N_CELLS, HIDDEN_DIM),        "structure"),
    ]

    if args.only:
        selected = {0} | set(args.only)  # always include baseline
        engines = [(i, n, e, c) for i, n, e, c in all_engines if i in selected]
    else:
        engines = all_engines

    results: List[BenchResult] = []
    for idx, name, engine, custom_name in engines:
        result = run_benchmark(name, engine, steps=STEPS, custom_metric_name=custom_name)
        results.append(result)

    # Print comparison table
    baseline = results[0]
    print()
    print("=" * 120)
    print(f"{'Engine':<35} {'Phi_IIT':>8} {'xBase':>7} {'Phi_prx':>8} {'Granger':>8} {'Custom':>10} {'Time':>6}  Extra")
    print("-" * 120)
    for r in results:
        x_base = r.phi_iit / max(baseline.phi_iit, 1e-6)
        extra_str = "  ".join(f"{k}={v:.4f}" for k, v in r.extra.items())
        print(f"{r.name:<35} {r.phi_iit:>8.3f} {x_base:>6.1f}x {r.phi_proxy:>8.3f} {r.granger:>8.1f} "
              f"{r.custom_metric:>10.4f} {r.time_sec:>5.1f}s  {extra_str}")
    print("-" * 120)

    # Rankings
    print()
    print("Rankings by Phi_IIT:")
    ranked = sorted(results, key=lambda r: r.phi_iit, reverse=True)
    for i, r in enumerate(ranked):
        medal = ["  1st", "  2nd", "  3rd"][i] if i < 3 else f"  {i+1}th"
        print(f"  {medal}: {r.name:<35} Phi_IIT={r.phi_iit:.3f}")

    print()
    print("Rankings by Granger Causality:")
    ranked_gc = sorted(results, key=lambda r: r.granger, reverse=True)
    for i, r in enumerate(ranked_gc):
        medal = ["  1st", "  2nd", "  3rd"][i] if i < 3 else f"  {i+1}th"
        print(f"  {medal}: {r.name:<35} Granger={r.granger:.1f}")

    print()
    print("Rankings by Combined (Phi_IIT + 0.1*Phi_proxy + 0.01*Granger):")
    ranked_comb = sorted(results, key=lambda r: r.phi_iit + 0.1 * r.phi_proxy + 0.01 * r.granger, reverse=True)
    for i, r in enumerate(ranked_comb):
        combined = r.phi_iit + 0.1 * r.phi_proxy + 0.01 * r.granger
        medal = ["  1st", "  2nd", "  3rd"][i] if i < 3 else f"  {i+1}th"
        print(f"  {medal}: {r.name:<35} Combined={combined:.3f}")

    # Custom metric summary
    print()
    print("Engine-Specific Metrics:")
    print("-" * 80)
    for r in results[1:]:  # skip baseline
        if r.extra:
            extra_str = ", ".join(f"{k}={v:.4f}" for k, v in r.extra.items())
            print(f"  {r.name:<35} {extra_str}")

    print()
    print("=" * 100)
    print("  Information-Theoretic Consciousness Engines -- Benchmark Complete")
    print("=" * 100)


if __name__ == "__main__":
    main()
