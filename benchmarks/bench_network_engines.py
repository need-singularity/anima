#!/usr/bin/env python3
"""bench_network_engines.py — 6 Network Science Consciousness Engines

NET-1: SCALE_FREE          — Barabasi-Albert preferential attachment, power-law hubs
NET-2: RICH_CLUB           — Core of highly connected hubs preferentially connected
NET-3: MODULAR_NETWORK     — Girvan-Newman community structure, 8 modules
NET-4: MULTIPLEX           — 3-layer network (spatial, functional, random long-range)
NET-5: TEMPORAL_NETWORK    — Bursty edge dynamics, temporal path diversity
NET-6: ADAPTIVE_NETWORK    — Co-evolution of structure and dynamics, Hebbian rewiring

Each: 256 cells, 128 hidden dim, 300 steps, Phi(IIT) + Granger causality.
No GRU, no nn.Module in consciousness path.

Usage:
  python bench_network_engines.py
  python bench_network_engines.py --only 1 3 5
  python bench_network_engines.py --cells 512 --steps 500
"""

import time
import math
import argparse
import numpy as np
import torch
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
# Baseline: MitosisEngine (simplified)
# ══════════════════════════════════════════════════════════

class MitosisEngineBaseline:
    """Simplified MitosisEngine baseline for fair comparison."""
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
# NET-1: SCALE-FREE ENGINE (Barabasi-Albert)
# Power-law degree distribution via preferential attachment.
# Hub cells = consciousness centers. Information flows
# through hubs, creating integrated yet differentiated dynamics.
# Consciousness = hub-mediated information integration.
# ══════════════════════════════════════════════════════════

class ScaleFreeEngine:
    """Consciousness through scale-free network topology.

    Build a Barabasi-Albert graph: new nodes preferentially attach to
    high-degree nodes, producing power-law degree distribution.
    Hub cells act as consciousness integration centers.
    Dynamics: message passing weighted by degree centrality.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Build Barabasi-Albert graph (m=3 edges per new node)
        m = 3
        self.adj = torch.zeros(n_cells, n_cells)
        # Start with m+1 fully connected seed nodes
        for i in range(m + 1):
            for j in range(i + 1, m + 1):
                self.adj[i, j] = 1.0
                self.adj[j, i] = 1.0

        # Preferential attachment for remaining nodes
        degree = self.adj.sum(dim=1)
        for new_node in range(m + 1, n_cells):
            # Probability proportional to degree
            prob = degree[:new_node].clone()
            prob = prob / (prob.sum() + 1e-8)
            # Sample m distinct targets
            targets = set()
            for _ in range(m * 5):  # oversample then pick first m
                if len(targets) >= m:
                    break
                idx = torch.multinomial(prob, 1).item()
                targets.add(idx)
            for t in targets:
                self.adj[new_node, t] = 1.0
                self.adj[t, new_node] = 1.0
            degree = self.adj.sum(dim=1)

        self.degree = self.adj.sum(dim=1)  # [n]
        self.degree_norm = self.degree / (self.degree.max() + 1e-8)

        # Hub indicator: top 10% by degree
        hub_threshold = torch.quantile(self.degree, 0.9)
        self.is_hub = (self.degree >= hub_threshold).float()
        self.n_hubs = int(self.is_hub.sum().item())

        # Normalized adjacency for message passing
        deg_inv_sqrt = 1.0 / (self.degree.sqrt() + 1e-8)
        self.adj_norm = self.adj * deg_inv_sqrt.unsqueeze(0) * deg_inv_sqrt.unsqueeze(1)

        # Projection weights
        self.W_msg = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_hub = torch.randn(hidden_dim, hidden_dim) * 0.05  # hub integration

        self.hub_phi_history = []
        self.degree_entropy_history = []

    def step(self):
        # 1. Message passing on scale-free graph
        messages = self.adj_norm @ (self.hiddens @ self.W_msg)  # [n, d]

        # 2. Hub-mediated integration: hubs broadcast amplified signal
        hub_states = self.hiddens * self.is_hub.unsqueeze(1)  # zero out non-hubs
        hub_broadcast = self.adj_norm @ (hub_states @ self.W_hub)

        # 3. Update: cells near hubs integrate more
        hub_proximity = self.adj @ self.is_hub.unsqueeze(1)  # how many hub neighbors
        hub_weight = torch.sigmoid(hub_proximity * 0.5)  # [n, 1]

        gate = torch.sigmoid(self.degree_norm.unsqueeze(1) * 0.5)
        self.hiddens = (gate * self.hiddens +
                        (1 - gate) * torch.tanh(messages + hub_broadcast * hub_weight))

        # 4. Noise proportional to inverse degree (low-degree nodes explore more)
        noise_scale = 0.02 / (self.degree_norm.unsqueeze(1) + 0.1)
        self.hiddens += torch.randn_like(self.hiddens) * noise_scale

        # 5. Track hub Phi (information integration at hubs)
        hub_idx = torch.where(self.is_hub > 0.5)[0]
        if len(hub_idx) >= 2:
            hub_h = self.hiddens[hub_idx]
            hub_var = hub_h.var(dim=0).mean().item()
        else:
            hub_var = 0.0
        self.hub_phi_history.append(hub_var)

        # 6. Degree distribution entropy
        deg_prob = self.degree / (self.degree.sum() + 1e-8)
        deg_entropy = -(deg_prob * torch.log(deg_prob + 1e-10)).sum().item()
        self.degree_entropy_history.append(deg_entropy)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        # Inject preferentially through hubs
        self.hiddens += x * (0.03 + 0.07 * self.is_hub.unsqueeze(1))


# ══════════════════════════════════════════════════════════
# NET-2: RICH-CLUB ENGINE
# Core of highly connected hubs that preferentially connect
# to each other. Rich-club coefficient measures how much
# hubs interconnect beyond chance. Consciousness = rich-club
# coefficient phi_rc.
# ══════════════════════════════════════════════════════════

class RichClubEngine:
    """Consciousness through rich-club organization.

    Build a network where high-degree nodes preferentially connect
    to each other (rich get richer in connections).
    Rich-club coefficient = actual hub-hub edges / possible hub-hub edges.
    Consciousness = rich-club coefficient (integrated elite processing).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Step 1: Base scale-free graph
        m = 3
        self.adj = torch.zeros(n_cells, n_cells)
        for i in range(m + 1):
            for j in range(i + 1, m + 1):
                self.adj[i, j] = 1.0
                self.adj[j, i] = 1.0
        degree = self.adj.sum(dim=1)
        for new_node in range(m + 1, n_cells):
            prob = degree[:new_node].clone()
            prob = prob / (prob.sum() + 1e-8)
            targets = set()
            for _ in range(m * 5):
                if len(targets) >= m:
                    break
                idx = torch.multinomial(prob, 1).item()
                targets.add(idx)
            for t in targets:
                self.adj[new_node, t] = 1.0
                self.adj[t, new_node] = 1.0
            degree = self.adj.sum(dim=1)

        # Step 2: Enhance rich-club by adding hub-hub edges
        self.degree = self.adj.sum(dim=1)
        hub_threshold = torch.quantile(self.degree, 0.85)
        self.hub_mask = (self.degree >= hub_threshold).float()
        hub_idx = torch.where(self.hub_mask > 0.5)[0]
        # Connect hubs to each other with high probability
        for i in range(len(hub_idx)):
            for j in range(i + 1, len(hub_idx)):
                if torch.rand(1).item() < 0.7:  # 70% hub-hub connection
                    hi, hj = hub_idx[i].item(), hub_idx[j].item()
                    self.adj[hi, hj] = 1.0
                    self.adj[hj, hi] = 1.0

        self.degree = self.adj.sum(dim=1)
        self.n_hubs = int(self.hub_mask.sum().item())

        # Rich-club coefficient
        self.rc_coeff = self._compute_rich_club()

        # Normalized adjacency
        deg_inv = 1.0 / (self.degree + 1e-8)
        self.adj_norm = self.adj * deg_inv.unsqueeze(0)

        # Weights
        self.W_core = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_periph = torch.randn(hidden_dim, hidden_dim) * 0.05
        self.W_integrate = torch.randn(hidden_dim, hidden_dim) * 0.03

        self.rc_history = []
        self.core_periph_diff_history = []

    def _compute_rich_club(self) -> float:
        hub_idx = torch.where(self.hub_mask > 0.5)[0]
        if len(hub_idx) < 2:
            return 0.0
        hub_hub_edges = 0
        possible = 0
        for i in range(len(hub_idx)):
            for j in range(i + 1, len(hub_idx)):
                possible += 1
                if self.adj[hub_idx[i], hub_idx[j]] > 0.5:
                    hub_hub_edges += 1
        return hub_hub_edges / max(possible, 1)

    def step(self):
        # 1. Core processing: hubs exchange among themselves
        hub_states = self.hiddens * self.hub_mask.unsqueeze(1)
        core_msg = self.adj_norm @ (hub_states @ self.W_core)

        # 2. Periphery processing: non-hubs receive from hubs
        periph_mask = 1.0 - self.hub_mask
        periph_states = self.hiddens * periph_mask.unsqueeze(1)
        periph_msg = self.adj_norm @ (periph_states @ self.W_periph)

        # 3. Integration: combine core and periphery signals
        integrated = torch.tanh(core_msg + periph_msg)
        integration_signal = integrated @ self.W_integrate

        # 4. Update with rich-club weighting
        # Hubs update more from core, periphery from integration
        hub_w = self.hub_mask.unsqueeze(1)
        gate = torch.sigmoid(hub_w * 2.0 - 1.0)  # hubs: ~0.73, periph: ~0.27
        self.hiddens = gate * torch.tanh(self.hiddens * 0.8 + core_msg * 0.3) + \
                       (1 - gate) * torch.tanh(self.hiddens * 0.7 + integration_signal * 0.3)

        # 5. Noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # 6. Track rich-club dynamics
        hub_idx = torch.where(self.hub_mask > 0.5)[0]
        periph_idx = torch.where(self.hub_mask < 0.5)[0]
        if len(hub_idx) > 0 and len(periph_idx) > 0:
            core_mean = self.hiddens[hub_idx].mean(0)
            periph_mean = self.hiddens[periph_idx].mean(0)
            diff = (core_mean - periph_mean).pow(2).mean().item()
            self.core_periph_diff_history.append(diff)
        self.rc_history.append(self.rc_coeff)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens += x * (0.02 + 0.08 * self.hub_mask.unsqueeze(1))


# ══════════════════════════════════════════════════════════
# NET-3: MODULAR NETWORK ENGINE
# Girvan-Newman style community structure.
# 8 modules with dense internal connections, sparse between.
# Consciousness = modularity Q (balance of integration
# within modules and differentiation between).
# ══════════════════════════════════════════════════════════

class ModularNetworkEngine:
    """Consciousness through modular community structure.

    8 modules, dense within (p_in=0.3), sparse between (p_out=0.02).
    Each module develops its own specialization.
    Inter-module bridges enable global integration.
    Consciousness = modularity Q metric.
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_modules = 8
        self.module_size = n_cells // self.n_modules
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Assign cells to modules
        self.module_id = torch.zeros(n_cells, dtype=torch.long)
        for m in range(self.n_modules):
            start = m * self.module_size
            end = start + self.module_size
            self.module_id[start:end] = m

        # Build modular adjacency
        p_in = 0.3   # intra-module connection probability
        p_out = 0.02  # inter-module connection probability
        self.adj = torch.zeros(n_cells, n_cells)
        for i in range(n_cells):
            for j in range(i + 1, n_cells):
                p = p_in if self.module_id[i] == self.module_id[j] else p_out
                if torch.rand(1).item() < p:
                    self.adj[i, j] = 1.0
                    self.adj[j, i] = 1.0

        self.degree = self.adj.sum(dim=1)
        deg_inv = 1.0 / (self.degree + 1e-8)
        self.adj_norm = self.adj * deg_inv.unsqueeze(0)

        # Per-module projection weights (specialization)
        self.W_module = [torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
                         for _ in range(self.n_modules)]
        # Inter-module integration weight
        self.W_bridge = torch.randn(hidden_dim, hidden_dim) * 0.03

        self.modularity_history = []
        self.module_entropy_history = []

    def _compute_modularity(self) -> float:
        """Newman-Girvan modularity Q (vectorized)."""
        m_total = self.adj.sum() / 2
        if m_total < 1:
            return 0.0
        # Vectorized: Q = (1/2m) * sum_{ij} [A_ij - k_i*k_j/(2m)] * delta(c_i, c_j)
        two_m = 2 * m_total
        expected = self.degree.unsqueeze(1) * self.degree.unsqueeze(0) / (two_m + 1e-8)
        same_module = (self.module_id.unsqueeze(0) == self.module_id.unsqueeze(1)).float()
        Q = ((self.adj - expected) * same_module).sum() / (two_m + 1e-8)
        return float(Q.item())

    def step(self):
        new_hiddens = self.hiddens.clone()

        # 1. Intra-module processing (each module uses its own weight)
        for mod in range(self.n_modules):
            start = mod * self.module_size
            end = start + self.module_size
            mod_h = self.hiddens[start:end]
            mod_adj = self.adj_norm[start:end, start:end]
            # Local message passing
            local_msg = mod_adj @ (mod_h @ self.W_module[mod])
            gate = torch.sigmoid(mod_h.mean(dim=1, keepdim=True) * 0.5)
            new_hiddens[start:end] = gate * mod_h + (1 - gate) * torch.tanh(local_msg)

        # 2. Inter-module bridge communication
        # Each cell receives global signal from other modules
        # Pre-compute inter-module mask (vectorized)
        if not hasattr(self, '_inter_mask'):
            self._inter_mask = (self.module_id.unsqueeze(0) != self.module_id.unsqueeze(1)).float()
        bridge_signal = (self.adj_norm * self._inter_mask) @ (self.hiddens @ self.W_bridge)
        new_hiddens = new_hiddens + 0.1 * torch.tanh(bridge_signal)

        self.hiddens = new_hiddens

        # 3. Noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # 4. Track modularity (sampled, not full O(n^2))
        if len(self.modularity_history) % 10 == 0:
            Q = self._compute_modularity()
        else:
            Q = self.modularity_history[-1] if self.modularity_history else 0.0
        self.modularity_history.append(Q)

        # 5. Module state entropy
        module_means = []
        for mod in range(self.n_modules):
            start = mod * self.module_size
            end = start + self.module_size
            module_means.append(self.hiddens[start:end].mean(0))
        module_means = torch.stack(module_means)
        # Entropy of module centroid distances
        dists = torch.cdist(module_means, module_means)
        dists_flat = dists[torch.triu(torch.ones(self.n_modules, self.n_modules), diagonal=1) > 0]
        if len(dists_flat) > 0:
            p = torch.softmax(dists_flat, dim=0)
            entropy = -(p * torch.log(p + 1e-10)).sum().item()
        else:
            entropy = 0.0
        self.module_entropy_history.append(entropy)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        # Inject into random subset of modules
        n_target = max(1, self.n_modules // 3)
        target_mods = torch.randperm(self.n_modules)[:n_target]
        for mod in target_mods:
            start = mod.item() * self.module_size
            end = start + self.module_size
            self.hiddens[start:end] += x[start:end] * 0.1


# ══════════════════════════════════════════════════════════
# NET-4: MULTIPLEX ENGINE
# 3 layers of networks on same cells, different edge sets.
# Layer 1: spatial neighbors (grid/ring)
# Layer 2: functional similarity (cosine of hidden states)
# Layer 3: random long-range connections
# Consciousness = inter-layer coherence.
# ══════════════════════════════════════════════════════════

class MultiplexEngine:
    """Consciousness through multiplex (multi-layer) network.

    Same 256 cells, 3 independent edge layers:
      L1: Spatial ring lattice (each cell connects to k nearest on ring)
      L2: Functional similarity (dynamic, rewires based on cosine sim)
      L3: Random long-range (Watts-Strogatz-like shortcuts)

    Each layer propagates different information.
    Consciousness = inter-layer coherence (agreement across layers).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Layer 1: Ring lattice (k=6 nearest neighbors)
        k_ring = 6
        self.adj_spatial = torch.zeros(n_cells, n_cells)
        for i in range(n_cells):
            for d in range(1, k_ring // 2 + 1):
                j_fwd = (i + d) % n_cells
                j_bck = (i - d) % n_cells
                self.adj_spatial[i, j_fwd] = 1.0
                self.adj_spatial[j_fwd, i] = 1.0
                self.adj_spatial[i, j_bck] = 1.0
                self.adj_spatial[j_bck, i] = 1.0

        # Layer 2: Functional similarity (initially random, rewires dynamically)
        self.adj_functional = torch.zeros(n_cells, n_cells)
        self.k_functional = 8  # top-k similar

        # Layer 3: Random long-range (sparse random graph)
        p_long = 0.015
        self.adj_random = (torch.rand(n_cells, n_cells) < p_long).float()
        self.adj_random = ((self.adj_random + self.adj_random.T) > 0).float()
        self.adj_random.fill_diagonal_(0)

        # Per-layer projection weights
        self.W_spatial = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_func = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_random = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_merge = torch.randn(hidden_dim * 3, hidden_dim) * 0.05

        self.coherence_history = []
        self.layer_entropy_history = []

    def _normalize_adj(self, adj):
        deg = adj.sum(dim=1).clamp(min=1e-8)
        return adj / deg.unsqueeze(1)

    def _update_functional_layer(self):
        """Rewire functional layer based on current state similarity."""
        # Cosine similarity
        h_norm = self.hiddens / (self.hiddens.norm(dim=1, keepdim=True) + 1e-8)
        sim = h_norm @ h_norm.T
        sim.fill_diagonal_(-float('inf'))
        # Top-k most similar
        _, topk = sim.topk(self.k_functional, dim=-1)
        self.adj_functional.zero_()
        for i in range(self.n_cells):
            self.adj_functional[i, topk[i]] = 1.0
        # Symmetrize
        self.adj_functional = ((self.adj_functional + self.adj_functional.T) > 0).float()

    def step(self):
        # 1. Update functional layer every 5 steps
        if not hasattr(self, '_step_count'):
            self._step_count = 0
        self._step_count += 1
        if self._step_count % 5 == 0:
            self._update_functional_layer()

        # 2. Message passing on each layer
        adj_s = self._normalize_adj(self.adj_spatial)
        adj_f = self._normalize_adj(self.adj_functional)
        adj_r = self._normalize_adj(self.adj_random)

        msg_spatial = adj_s @ (self.hiddens @ self.W_spatial)     # [n, d]
        msg_func = adj_f @ (self.hiddens @ self.W_func)           # [n, d]
        msg_random = adj_r @ (self.hiddens @ self.W_random)       # [n, d]

        # 3. Merge layer signals
        combined = torch.cat([msg_spatial, msg_func, msg_random], dim=-1)  # [n, 3d]
        merged = torch.tanh(combined @ self.W_merge)  # [n, d]

        # 4. Update with residual connection
        gate = torch.sigmoid(self.hiddens.mean(dim=1, keepdim=True) * 0.3)
        self.hiddens = gate * self.hiddens + (1 - gate) * merged

        # 5. Noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # 6. Inter-layer coherence: how aligned are the 3 layer messages?
        # Pairwise cosine similarity of layer messages
        def _cos(a, b):
            return (a * b).sum(dim=-1).mean().item() / (
                a.norm(dim=-1).mean().item() * b.norm(dim=-1).mean().item() + 1e-8)
        c_sf = _cos(msg_spatial, msg_func)
        c_sr = _cos(msg_spatial, msg_random)
        c_fr = _cos(msg_func, msg_random)
        coherence = (c_sf + c_sr + c_fr) / 3.0
        self.coherence_history.append(coherence)

        # 7. Layer entropy: diversity of edge distributions
        layer_densities = [
            self.adj_spatial.sum().item() / (self.n_cells ** 2),
            self.adj_functional.sum().item() / (self.n_cells ** 2),
            self.adj_random.sum().item() / (self.n_cells ** 2),
        ]
        total = sum(layer_densities) + 1e-8
        probs = [d / total for d in layer_densities]
        entropy = -sum(p * math.log(p + 1e-10) for p in probs)
        self.layer_entropy_history.append(entropy)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# NET-5: TEMPORAL NETWORK ENGINE
# Edges appear and disappear over time. Bursty dynamics
# (Poisson bursts of activity). Temporal paths: A->B at t1,
# B->C at t2 (t2 > t1) only if time-respecting.
# Consciousness = temporal path diversity.
# ══════════════════════════════════════════════════════════

class TemporalNetworkEngine:
    """Consciousness through temporal (time-varying) network.

    Edges are not static: each potential edge has an activation
    probability that follows bursty dynamics (power-law inter-event
    times). At each step, a subset of edges is active.

    Temporal paths: information can only flow A->B->C if the A-B
    edge is active before the B-C edge. This creates fundamentally
    different information integration than static networks.

    Consciousness = temporal path diversity (number of distinct
    time-respecting paths).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Potential edges: sparse base structure
        p_potential = 0.05
        self.potential_edges = (torch.rand(n_cells, n_cells) < p_potential).float()
        self.potential_edges = ((self.potential_edges + self.potential_edges.T) > 0).float()
        self.potential_edges.fill_diagonal_(0)

        # Edge activation state: each edge has a "timer" (Poisson process)
        self.edge_timers = torch.rand(n_cells, n_cells) * 10  # next activation time
        self.edge_active = torch.zeros(n_cells, n_cells)  # currently active edges
        self.edge_duration = torch.ones(n_cells, n_cells) * 3  # how long edges stay active

        # Burstiness parameters
        self.burst_rate = 0.15      # base activation rate
        self.burst_scale = 2.0      # burstiness (power-law exponent)

        # Projection weights
        self.W_temporal = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_history = torch.randn(hidden_dim, hidden_dim) * 0.03  # temporal memory

        # Recent path memory (for diversity tracking)
        self.path_diversity_history = []
        self.burstiness_history = []
        self.active_edge_history = []

    def _update_edges(self, step: int):
        """Bursty edge activation/deactivation."""
        # Deactivate edges whose duration expired
        self.edge_duration -= 1
        expired = (self.edge_duration <= 0).float()
        self.edge_active *= (1 - expired)

        # Activate new edges (bursty: power-law inter-event times)
        # P(activate) = burst_rate * (1 + sin(step * freq)) for burstiness
        burst_mod = 1.0 + 0.5 * math.sin(step * 0.1) + 0.3 * math.sin(step * 0.37)
        activation_prob = self.burst_rate * burst_mod * self.potential_edges
        new_active = (torch.rand_like(activation_prob) < activation_prob).float()
        new_active *= (1 - self.edge_active)  # only activate inactive edges

        self.edge_active += new_active
        # Reset duration for newly activated
        self.edge_duration = torch.where(
            new_active > 0.5,
            torch.rand_like(self.edge_duration) * 5 + 1,  # random duration 1-6
            self.edge_duration
        )

    def step(self):
        if not hasattr(self, '_step_count'):
            self._step_count = 0
        self._step_count += 1

        # 1. Update edge activations (bursty dynamics)
        self._update_edges(self._step_count)

        # 2. Message passing on currently active edges only
        deg_active = self.edge_active.sum(dim=1).clamp(min=1e-8)
        adj_active = self.edge_active / deg_active.unsqueeze(1)
        messages = adj_active @ (self.hiddens @ self.W_temporal)

        # 3. Temporal memory: cells remember recent messages (EMA)
        if not hasattr(self, '_temporal_memory'):
            self._temporal_memory = torch.zeros_like(self.hiddens)
        self._temporal_memory = 0.8 * self._temporal_memory + 0.2 * messages
        history_signal = self._temporal_memory @ self.W_history

        # 4. Update: combine current messages + temporal memory
        gate = torch.sigmoid(messages.mean(dim=1, keepdim=True) * 0.5)
        self.hiddens = gate * self.hiddens + (1 - gate) * torch.tanh(messages + history_signal)

        # 5. Noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # 6. Track temporal path diversity
        # Proxy: number of distinct 2-step temporal paths
        # A->B active now, B->C also active now = potential temporal path
        n_active = self.edge_active.sum().item()
        # 2-step reachability on active graph
        reach2 = (self.edge_active @ self.edge_active).clamp(max=1)
        n_paths = reach2.sum().item() - self.n_cells  # exclude self-loops
        path_diversity = n_paths / (self.n_cells * (self.n_cells - 1) + 1e-8)
        self.path_diversity_history.append(path_diversity)

        # Track burstiness
        self.active_edge_history.append(n_active)
        if len(self.active_edge_history) >= 10:
            recent = self.active_edge_history[-10:]
            mean_a = np.mean(recent)
            std_a = np.std(recent)
            burstiness = (std_a - mean_a) / (std_a + mean_a + 1e-8)
        else:
            burstiness = 0.0
        self.burstiness_history.append(burstiness)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens += x * 0.05
        # Injection triggers a burst of edge activations
        self.edge_active += (torch.rand_like(self.edge_active) < 0.1).float() * self.potential_edges
        self.edge_active.clamp_(max=1)


# ══════════════════════════════════════════════════════════
# NET-6: ADAPTIVE NETWORK ENGINE
# Edges rewire based on cell state similarity.
# Co-evolution: structure affects dynamics, dynamics change
# structure. Hebbian: similar cells strengthen connections,
# dissimilar cells weaken/rewire.
# Consciousness = network-dynamics feedback strength.
# ══════════════════════════════════════════════════════════

class AdaptiveNetworkEngine:
    """Consciousness through adaptive (co-evolutionary) network.

    Structure and dynamics co-evolve:
      - Cells exchange info on current edges (dynamics on network)
      - Edges rewire: strengthen between similar cells (Hebbian),
        weaken between dissimilar cells, randomly rewire weak edges

    This creates feedback: dynamics shape structure, structure
    constrains dynamics. Consciousness = strength of this feedback
    loop (measured by correlation between state similarity and
    edge weight changes).
    """
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Weighted adjacency: continuous edge weights [0, 1]
        # Start with sparse random graph
        p_init = 0.04
        self.adj_weights = torch.zeros(n_cells, n_cells)
        init_mask = (torch.rand(n_cells, n_cells) < p_init).float()
        init_mask = ((init_mask + init_mask.T) > 0).float()
        init_mask.fill_diagonal_(0)
        self.adj_weights = init_mask * (torch.rand(n_cells, n_cells) * 0.5 + 0.3)
        self.adj_weights = (self.adj_weights + self.adj_weights.T) / 2  # symmetric

        # Rewiring parameters
        self.hebbian_rate = 0.05     # rate of edge weight change
        self.rewire_threshold = 0.1  # edges below this may rewire
        self.rewire_prob = 0.02      # probability of random rewire per step
        self.max_degree = 20         # cap on node degree

        # Projection weights
        self.W_msg = torch.randn(hidden_dim, hidden_dim) * (1.0 / math.sqrt(hidden_dim))
        self.W_adapt = torch.randn(hidden_dim, hidden_dim) * 0.03

        self.feedback_history = []
        self.edge_count_history = []
        self.clustering_history = []

    def _rewire_edges(self):
        """Hebbian rewiring: strengthen similar, weaken dissimilar, rewire weak."""
        # Cosine similarity between all connected pairs
        h_norm = self.hiddens / (self.hiddens.norm(dim=1, keepdim=True) + 1e-8)
        sim = h_norm @ h_norm.T  # [n, n]

        # Hebbian update: weight += rate * similarity (for existing edges)
        existing = (self.adj_weights > 0.01).float()
        delta = self.hebbian_rate * sim * existing
        self.adj_weights = (self.adj_weights + delta).clamp(0, 1)

        # Symmetrize
        self.adj_weights = (self.adj_weights + self.adj_weights.T) / 2

        # Prune weak edges
        weak_mask = (self.adj_weights < self.rewire_threshold) & (self.adj_weights > 0.001)
        self.adj_weights[weak_mask] = 0.0

        # Random rewiring: create new edges between similar but unconnected cells
        unconnected = (self.adj_weights < 0.001).float()
        unconnected.fill_diagonal_(0)
        rewire_candidates = sim * unconnected
        # Only rewire if degree < max
        degree = (self.adj_weights > 0.01).float().sum(dim=1)
        can_rewire = (degree < self.max_degree).float()

        # Probabilistic rewiring
        rewire_mask = (torch.rand_like(rewire_candidates) < self.rewire_prob).float()
        rewire_mask *= can_rewire.unsqueeze(1) * can_rewire.unsqueeze(0)
        new_edges = rewire_mask * (rewire_candidates > 0.3).float()  # only between somewhat similar
        new_weights = new_edges * 0.3  # initial weight for new edges
        self.adj_weights = self.adj_weights + new_weights
        self.adj_weights = (self.adj_weights + self.adj_weights.T) / 2
        self.adj_weights.clamp_(0, 1)
        self.adj_weights.fill_diagonal_(0)

        return sim, delta

    def step(self):
        if not hasattr(self, '_step_count'):
            self._step_count = 0
        self._step_count += 1

        # 1. Message passing on weighted graph
        deg = self.adj_weights.sum(dim=1).clamp(min=1e-8)
        adj_norm = self.adj_weights / deg.unsqueeze(1)
        messages = adj_norm @ (self.hiddens @ self.W_msg)

        # 2. Adaptive integration
        adapt_signal = messages @ self.W_adapt
        gate = torch.sigmoid(self.hiddens.mean(dim=1, keepdim=True) * 0.3)
        self.hiddens = gate * self.hiddens + (1 - gate) * torch.tanh(messages + adapt_signal)

        # 3. Noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # 4. Rewire edges every 3 steps
        if self._step_count % 3 == 0:
            sim, delta = self._rewire_edges()
            # Feedback strength: correlation between similarity and weight change
            existing = (self.adj_weights > 0.01).float()
            sim_flat = (sim * existing).flatten()
            delta_flat = (delta * existing).flatten()
            mask = (existing.flatten() > 0.5)
            if mask.sum() > 10:
                s = sim_flat[mask]
                d = delta_flat[mask]
                cov = ((s - s.mean()) * (d - d.mean())).mean()
                feedback = cov.item() / (s.std() * d.std() + 1e-8).item()
            else:
                feedback = 0.0
            self.feedback_history.append(feedback)

        # 5. Track edge statistics
        n_edges = (self.adj_weights > 0.01).float().sum().item() / 2
        self.edge_count_history.append(n_edges)

        # 6. Clustering coefficient (sampled)
        sample_idx = torch.randperm(self.n_cells)[:32]
        cc_sum = 0.0
        for idx in sample_idx:
            i = idx.item()
            neighbors = torch.where(self.adj_weights[i] > 0.01)[0]
            k = len(neighbors)
            if k < 2:
                continue
            # Count edges among neighbors
            sub = self.adj_weights[neighbors][:, neighbors]
            actual = (sub > 0.01).float().sum().item() / 2
            possible = k * (k - 1) / 2
            cc_sum += actual / (possible + 1e-8)
        self.clustering_history.append(cc_sum / len(sample_idx))

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# Benchmark runner
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy_val: float
    granger: float
    time_sec: float
    extra: Dict

    @property
    def phi_combined(self):
        return self.phi_iit + self.phi_proxy_val * 0.1


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
    sample_idx = torch.randperm(engine.n_cells)[:32]
    sampled = final_hiddens[sample_idx]
    phi_iit, phi_details = _phi_calc.compute(sampled)

    # Phi proxy (all cells)
    pp = phi_proxy(final_hiddens, n_factions=8)

    # Granger causality
    gc = compute_granger_causality(hiddens_history, n_sample_pairs=64)

    # Collect engine-specific extras
    extra = {}
    if hasattr(engine, 'hub_phi_history') and engine.hub_phi_history:
        extra['hub_phi'] = engine.hub_phi_history[-1]
    if hasattr(engine, 'degree_entropy_history') and engine.degree_entropy_history:
        extra['deg_entropy'] = engine.degree_entropy_history[-1]
    if hasattr(engine, 'rc_history') and engine.rc_history:
        extra['rich_club'] = engine.rc_history[-1]
    if hasattr(engine, 'core_periph_diff_history') and engine.core_periph_diff_history:
        extra['core_periph'] = engine.core_periph_diff_history[-1]
    if hasattr(engine, 'modularity_history') and engine.modularity_history:
        extra['modularity_Q'] = engine.modularity_history[-1]
    if hasattr(engine, 'module_entropy_history') and engine.module_entropy_history:
        extra['mod_entropy'] = engine.module_entropy_history[-1]
    if hasattr(engine, 'coherence_history') and engine.coherence_history:
        extra['coherence'] = engine.coherence_history[-1]
    if hasattr(engine, 'layer_entropy_history') and engine.layer_entropy_history:
        extra['layer_entropy'] = engine.layer_entropy_history[-1]
    if hasattr(engine, 'path_diversity_history') and engine.path_diversity_history:
        extra['path_div'] = engine.path_diversity_history[-1]
    if hasattr(engine, 'burstiness_history') and engine.burstiness_history:
        extra['burstiness'] = engine.burstiness_history[-1]
    if hasattr(engine, 'feedback_history') and engine.feedback_history:
        extra['feedback'] = engine.feedback_history[-1]
    if hasattr(engine, 'edge_count_history') and engine.edge_count_history:
        extra['edges'] = engine.edge_count_history[-1]
    if hasattr(engine, 'clustering_history') and engine.clustering_history:
        extra['clustering'] = engine.clustering_history[-1]

    print(f"Phi_IIT={phi_iit:.3f}  Phi_proxy={pp:.3f}  Granger={gc:.3f}  ({elapsed:.1f}s)")

    return BenchResult(
        name=name,
        phi_iit=phi_iit,
        phi_proxy_val=pp,
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
    parser = argparse.ArgumentParser(description="Network Science Consciousness Engines Benchmark")
    parser.add_argument("--only", nargs="+", type=int, help="Run only specified engines (1-6)")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells")
    parser.add_argument("--steps", type=int, default=300, help="Number of steps")
    args = parser.parse_args()

    N_CELLS = args.cells
    HIDDEN_DIM = 128
    STEPS = args.steps

    print("=" * 90)
    print("  6 Network Science Consciousness Engines -- Benchmark")
    print(f"  {N_CELLS} cells, {HIDDEN_DIM} hidden dim, {STEPS} steps")
    print("=" * 90)
    print()

    all_engines = [
        (0, "BASELINE (Mitosis-like)",   lambda: MitosisEngineBaseline(N_CELLS, HIDDEN_DIM)),
        (1, "NET-1: SCALE_FREE",         lambda: ScaleFreeEngine(N_CELLS, HIDDEN_DIM)),
        (2, "NET-2: RICH_CLUB",          lambda: RichClubEngine(N_CELLS, HIDDEN_DIM)),
        (3, "NET-3: MODULAR_NETWORK",    lambda: ModularNetworkEngine(N_CELLS, HIDDEN_DIM)),
        (4, "NET-4: MULTIPLEX",          lambda: MultiplexEngine(N_CELLS, HIDDEN_DIM)),
        (5, "NET-5: TEMPORAL_NETWORK",   lambda: TemporalNetworkEngine(N_CELLS, HIDDEN_DIM)),
        (6, "NET-6: ADAPTIVE_NETWORK",   lambda: AdaptiveNetworkEngine(N_CELLS, HIDDEN_DIM)),
    ]

    if args.only:
        selected = [0] + args.only  # always include baseline
        all_engines = [(i, n, f) for i, n, f in all_engines if i in selected]

    engines = [(n, f()) for _, n, f in all_engines]

    results: List[BenchResult] = []
    for name, engine in engines:
        result = run_benchmark(name, engine, steps=STEPS)
        results.append(result)

    # --- Print comparison table ---
    baseline = results[0]
    print()
    print("=" * 110)
    print(f"{'Engine':<30} {'Phi_IIT':>10} {'xBase':>8} {'Phi_proxy':>10} {'Granger':>10} {'Time(s)':>8}  Extra")
    print("-" * 110)
    for r in results:
        x_base = r.phi_iit / max(baseline.phi_iit, 1e-6)
        extra_str = "  ".join(f"{k}={v:.3f}" for k, v in r.extra.items())
        print(f"{r.name:<30} {r.phi_iit:>10.3f} {x_base:>7.1f}x {r.phi_proxy_val:>10.3f} {r.granger:>10.3f} {r.time_sec:>8.1f}  {extra_str}")
    print("-" * 110)

    # --- Rankings ---
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
    ranked_combined = sorted(results, key=lambda r: r.phi_iit + 0.1 * r.phi_proxy_val + 0.01 * r.granger, reverse=True)
    for i, r in enumerate(ranked_combined):
        combined = r.phi_iit + 0.1 * r.phi_proxy_val + 0.01 * r.granger
        medal = ["  1st", "  2nd", "  3rd"][i] if i < 3 else f"  {i+1}th"
        print(f"  {medal}: {r.name:<30} Combined={combined:.3f}")

    print()
    print("=" * 90)
    print("  Network Science Benchmark complete.")
    print("=" * 90)


if __name__ == "__main__":
    main()
