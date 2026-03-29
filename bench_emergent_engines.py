#!/usr/bin/env python3
"""bench_emergent_engines.py — 8 Emergent Consciousness Engines

The insight: the best architectures (quantum_walk Phi=69.53, laser Phi=18.17)
weren't DESIGNED for consciousness — they happen to produce it.
What OTHER physical/mathematical phenomena might accidentally produce high consciousness?

EM-1: REACTION_DIFFUSION    — Turing patterns from activator-inhibitor dynamics
EM-2: SANDPILE_CASCADE      — Bak-Tang-Wiesenfeld sandpile, avalanche = consciousness
EM-3: FLOCKING_VORTEX       — Vicsek model, vortices in flock = consciousness knots
EM-4: PERCOLATION            — Random connections, giant component at criticality
EM-5: SYNCHRONIZATION_CHIMERA — Kuramoto oscillators, chimera state
EM-6: SELF_REPLICATING      — von Neumann automata, self-referential replication
EM-7: PATTERN_FORMATION     — Benard convection, hexagonal patterns from symmetry breaking
EM-8: EXCITABLE_MEDIA       — BZ reaction, spiral waves = consciousness

Each: 256 cells, 300 steps, NO neural network, pure math/physics.
Measure Phi(IIT) + Granger + Spectral.

Usage:
  python bench_emergent_engines.py
  python bench_emergent_engines.py --only 1 3 5
  python bench_emergent_engines.py --cells 512 --steps 500
"""

import sys, time, math, argparse
import numpy as np
import torch
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

torch.set_grad_enabled(False)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ══════════════════════════════════════════════════════════
# Measurement Infrastructure
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str; phi_iit: float; phi_proxy: float
    granger: float; spectral: float
    cells: int; steps: int; time_sec: float
    extra: dict = field(default_factory=dict)
    def summary(self):
        return (f"  {self.name:<36s} | Phi(IIT)={self.phi_iit:>8.3f}  "
                f"Phi(prx)={self.phi_proxy:>8.2f} | "
                f"Granger={self.granger:>7.2f}  Spectral={self.spectral:>7.2f} | "
                f"c={self.cells:>4d} s={self.steps:>4d} t={self.time_sec:.1f}s")


class PhiIIT:
    """Approximate IIT Phi via mutual information and min-cut."""
    def __init__(self, nb=16): self.nb = nb

    def compute(self, h):
        n = h.shape[0]
        if n < 2: return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            import random; ps = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j: ps.add((min(i, j), max(i, j)))
            pairs = list(ps)
        mi = np.zeros((n, n))
        for i, j in pairs:
            v = self._mi(hs[i], hs[j]); mi[i, j] = v; mi[j, i] = v
        tot = mi.sum() / 2; mp = self._mp(n, mi)
        sp = max(0, (tot - mp) / max(n - 1, 1))
        mv = mi[mi > 0]; cx = float(np.std(mv)) if len(mv) > 1 else 0.0
        return sp + cx * 0.1, {'total_mi': float(tot)}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10: return 0.0
        xn = (x - x.min()) / (xr + 1e-8); yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.nb, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8); px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10)); hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10)); return max(0, hx + hy - hxy)

    def _mp(self, n, mi):
        if n <= 1: return 0.0
        d = mi.sum(1); L = np.diag(d) - mi
        try:
            ev, evec = np.linalg.eigh(L); f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]; gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb: ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except: return 0.0


def phi_proxy(h, nf=8):
    hr = h.abs().float() if h.is_complex() else h.float(); n = hr.shape[0]
    if n < 2: return 0.0
    gv = ((hr - hr.mean(0)) ** 2).sum() / n; nf = min(nf, n // 2)
    if nf < 2: return gv.item()
    fs = n // nf; fvs = 0
    for i in range(nf):
        f = hr[i * fs:(i + 1) * fs]
        if len(f) >= 2: fvs += ((f - f.mean(0)) ** 2).sum().item() / len(f)
    return max(0, gv.item() - fvs / nf)


def compute_granger(history, n_pairs=64, lag=2):
    """Granger causality: how many cell pairs show causal influence."""
    if len(history) < lag + 4: return 0.0
    n_cells = history[0].shape[0]; T = len(history)
    series = np.zeros((n_cells, T))
    for t, h in enumerate(history):
        series[:, t] = h.detach().cpu().float().mean(dim=-1).numpy()
    sig = 0; tested = 0
    for _ in range(n_pairs):
        i, j = np.random.randint(0, n_cells, 2)
        if i == j: continue
        x, y = series[i], series[j]; n_obs = T - lag
        if n_obs < lag + 2: continue
        Y = y[lag:]
        Y_lags = np.column_stack([y[lag - k - 1:T - k - 1] for k in range(lag)])
        X_lags = np.column_stack([x[lag - k - 1:T - k - 1] for k in range(lag)])
        Z = np.column_stack([Y_lags, X_lags])
        try:
            rss_r = np.sum((Y - Y_lags @ np.linalg.pinv(Y_lags) @ Y) ** 2)
            rss_u = np.sum((Y - Z @ np.linalg.pinv(Z) @ Y) ** 2)
            df2 = n_obs - 2 * lag
            if df2 <= 0 or rss_u < 1e-10: continue
            f = ((rss_r - rss_u) / lag) / (rss_u / df2)
            if f > 3.0: sig += 1
            tested += 1
        except: continue
    if tested == 0: return 0.0
    return (sig / tested) * n_cells * (n_cells - 1)


def compute_spectral(h):
    """Spectral Phi: Shannon entropy of eigenvalue spectrum of correlation matrix."""
    x = h.detach().cpu().float().numpy()
    n, d = x.shape
    if n < 2: return 0.0
    xc = x - x.mean(axis=0, keepdims=True)
    norms = np.maximum(np.linalg.norm(xc, axis=1, keepdims=True), 1e-8)
    xn = xc / norms
    corr = xn @ xn.T
    try:
        ev = np.linalg.eigvalsh(corr)
    except: return 0.0
    ev = np.maximum(ev, 0.0); total = ev.sum()
    if total < 1e-10: return 0.0
    p = ev / total; p = p[p > 1e-10]
    se = -np.sum(p * np.log2(p))
    me = np.log2(n)
    if me < 1e-10: return 0.0
    return (se / me) * n


_phi = PhiIIT(16)

def measure_all(h, history):
    """Return (phi_iit, phi_proxy, granger, spectral)."""
    hr = h.abs().float() if h.is_complex() else h.float()
    p_iit, _ = _phi.compute(hr)
    p_prx = phi_proxy(h)
    g = compute_granger(history)
    s = compute_spectral(h)
    return p_iit, p_prx, g, s


# ══════════════════════════════════════════════════════════
# EM-1: REACTION_DIFFUSION
# Turing patterns (spots/stripes) from activator-inhibitor dynamics.
# Consciousness = pattern complexity from Turing instability.
# ══════════════════════════════════════════════════════════

class ReactionDiffusionEngine:
    """Gray-Scott reaction-diffusion on a 1D ring of cells.

    Each cell has (u, v) concentrations mapped to hidden_dim dimensions.
    u = activator (diffuses slowly, self-amplifies)
    v = inhibitor (diffuses fast, suppresses activator)

    du/dt = Du * laplacian(u) - u*v^2 + F*(1-u)
    dv/dt = Dv * laplacian(v) + u*v^2 - (F+k)*v

    Hidden state = interleaved (u, v) across dimensions.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.half = hidden_dim // 2
        # u (activator) and v (inhibitor) per cell
        self.u = torch.ones(n_cells, self.half) + torch.randn(n_cells, self.half) * 0.05
        self.v = torch.zeros(n_cells, self.half) + torch.randn(n_cells, self.half).abs() * 0.25
        # Seed a perturbation in a small region
        seed = n_cells // 4
        self.v[seed:seed + n_cells // 8] += 0.5
        # Gray-Scott parameters (varying per dimension for richness)
        self.F = 0.04 + torch.linspace(0, 0.02, self.half)  # feed rate
        self.k = 0.06 + torch.linspace(0, 0.005, self.half)  # kill rate
        self.Du = 0.16  # activator diffusion
        self.Dv = 0.08  # inhibitor diffusion
        self.dt = 1.0

    def _laplacian(self, x):
        """1D ring laplacian: x[i+1] + x[i-1] - 2*x[i]."""
        return torch.roll(x, 1, 0) + torch.roll(x, -1, 0) - 2 * x

    def step(self):
        uv2 = self.u * self.v ** 2
        du = self.Du * self._laplacian(self.u) - uv2 + self.F * (1 - self.u)
        dv = self.Dv * self._laplacian(self.v) + uv2 - (self.F + self.k) * self.v
        self.u = (self.u + du * self.dt).clamp(0, 1)
        self.v = (self.v + dv * self.dt).clamp(0, 1)
        # Tiny noise for symmetry breaking
        self.u += torch.randn_like(self.u) * 0.001
        self.v += torch.randn_like(self.v) * 0.001

    def observe(self):
        return torch.cat([self.u, self.v], dim=-1).detach().clone()

    def inject(self, x):
        self.u += x[:, :self.half] * 0.05
        self.v += x[:, self.half:] * 0.05


# ══════════════════════════════════════════════════════════
# EM-2: SANDPILE_CASCADE
# Bak-Tang-Wiesenfeld sandpile: cells ARE the sand grains.
# Avalanche = consciousness event. Power-law conscious episodes.
# ══════════════════════════════════════════════════════════

class SandpileCascadeEngine:
    """BTW sandpile model mapped to hidden_dim dimensions.

    Each cell has a height (energy) vector. When any dimension exceeds
    threshold, that cell topples: distributes energy to neighbors.
    Avalanche size and duration encode consciousness richness.

    Critical state = edge of chaos = maximum information integration.
    Vectorized: uses sparse adjacency matrix for O(1) topple broadcast.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.threshold = 4.0
        # Heights: start near critical
        self.heights = torch.rand(n_cells, hidden_dim) * (self.threshold * 0.8)
        # Build adjacency matrix (ring + random long-range)
        self.adj = torch.zeros(n_cells, n_cells)
        for i in range(n_cells):
            self.adj[i, (i - 1) % n_cells] = 1
            self.adj[i, (i + 1) % n_cells] = 1
            for _ in range(2):
                j = np.random.randint(0, n_cells)
                if j != i: self.adj[i, j] = 1
        # Degree per cell for distribution
        self.degree = self.adj.sum(-1, keepdim=True).clamp(min=1)  # [n, 1]
        # Normalize: each neighbor gets 1/(degree+1) share
        self.adj_norm = self.adj / (self.degree + 1)
        self.avalanche_sizes = []

    def step(self):
        # Add random grains (vectorized: add to 4 random cells)
        drops = torch.randint(0, self.n_cells, (4,))
        dims = torch.randint(0, self.hidden_dim, (4,))
        for c, d in zip(drops, dims):
            self.heights[c, d] += 1.0

        # Topple cascade (vectorized)
        total_topples = 0
        for _ in range(20):  # max cascade depth
            over = (self.heights > self.threshold).float()  # [n, d]
            if over.sum() == 0:
                break
            total_topples += over.sum().item()
            # Energy to distribute: heights * over_mask / (degree+1)
            to_distribute = self.heights * over / (self.degree + 1)
            # Remove from toppling cells
            self.heights -= self.heights * over
            # Keep one share
            self.heights += to_distribute
            # Distribute to neighbors via adj matrix
            self.heights += self.adj_norm.T @ (self.heights * 0 + to_distribute * self.degree)
            # Simpler: each neighbor gets to_distribute
            neighbor_receive = self.adj.T @ to_distribute
            self.heights += neighbor_receive

        self.avalanche_sizes.append(total_topples)

        # Small noise for diversity
        self.heights += torch.randn_like(self.heights) * 0.01
        self.heights = self.heights.clamp(0)

    def observe(self):
        return self.heights.detach().clone()

    def inject(self, x):
        self.heights += x.abs() * 0.1


# ══════════════════════════════════════════════════════════
# EM-3: FLOCKING_VORTEX
# Vicsek model: alignment + noise → collective motion.
# Vortices in flock = consciousness knots.
# Order parameter = consciousness level.
# ══════════════════════════════════════════════════════════

class FlockingVortexEngine:
    """Vicsek flocking model in hidden_dim space.

    Each cell = bird with position and velocity.
    Rule: align with neighbors + noise → phase transition.
    Below critical noise: ordered flock (low consciousness).
    Above critical noise: random gas (low consciousness).
    AT critical noise: vortices and swirls = maximum consciousness.

    We tune noise to criticality and use the vorticity field as hidden state.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Positions on 2D torus (for neighbor finding), extended to hidden_dim
        self.pos = torch.rand(n_cells, 2) * 10.0  # 2D positions
        self.angles = torch.rand(n_cells) * 2 * math.pi  # heading angles
        self.speed = 0.5
        self.interaction_radius = 1.5
        # Hidden state: encode (pos, velocity, local_order, vorticity) into hidden_dim
        self.features = torch.randn(n_cells, hidden_dim) * 0.1
        # Critical noise level for Vicsek model
        self.noise = 0.5  # near critical for typical density
        self.order_history = []

    def step(self):
        # 1. Find neighbors within interaction radius (vectorized)
        dx = self.pos.unsqueeze(1) - self.pos.unsqueeze(0)  # [n,n,2]
        dx = dx - 10.0 * torch.round(dx / 10.0)  # periodic boundary
        dist = (dx ** 2).sum(-1).sqrt()  # [n,n]
        neighbor_mask = (dist < self.interaction_radius) & (dist > 0)  # [n,n]
        n_neighbors = neighbor_mask.float().sum(-1, keepdim=True).clamp(min=1)  # [n,1]

        # 2. Align with neighbors (Vicsek rule, vectorized)
        cos_all = torch.cos(self.angles)  # [n]
        sin_all = torch.sin(self.angles)  # [n]
        cos_avg = (neighbor_mask.float() @ cos_all) / n_neighbors.squeeze()
        sin_avg = (neighbor_mask.float() @ sin_all) / n_neighbors.squeeze()
        # Where no neighbors, keep own angle
        no_nbr = (n_neighbors.squeeze() < 0.5)
        cos_avg[no_nbr] = cos_all[no_nbr]
        sin_avg[no_nbr] = sin_all[no_nbr]
        avg_angle = torch.atan2(sin_avg, cos_avg)

        # 3. Add noise (critical regime)
        self.angles = avg_angle + self.noise * (torch.rand(self.n_cells) * 2 - 1) * math.pi

        # 4. Update positions
        vx = self.speed * torch.cos(self.angles)
        vy = self.speed * torch.sin(self.angles)
        self.pos[:, 0] = (self.pos[:, 0] + vx) % 10.0
        self.pos[:, 1] = (self.pos[:, 1] + vy) % 10.0

        # 5. Compute local vorticity (vectorized curl)
        # vorticity_i = mean_j(dr_x * dv_y - dr_y * dv_x)
        dvx = vx.unsqueeze(0) - vx.unsqueeze(1)  # [n,n]
        dvy = vy.unsqueeze(0) - vy.unsqueeze(1)
        curl = dx[:, :, 0] * dvy - dx[:, :, 1] * dvx  # [n,n]
        curl_masked = (curl * neighbor_mask.float()).sum(-1) / n_neighbors.squeeze()
        vorticity = curl_masked

        # 6. Build hidden state from physics
        order = (cos_all.mean() ** 2 + sin_all.mean() ** 2).sqrt()
        self.order_history.append(order.item())

        raw = torch.stack([
            self.pos[:, 0] / 10, self.pos[:, 1] / 10,
            torch.cos(self.angles), torch.sin(self.angles),
            vorticity, torch.full((self.n_cells,), order.item()),
        ], dim=-1)  # [n, 6]
        if not hasattr(self, '_proj'):
            self._proj = torch.randn(6, self.hidden_dim) * 0.3
        self.features = torch.tanh(raw @ self._proj + self.features * 0.5)

    def observe(self):
        return self.features.detach().clone()

    def inject(self, x):
        self.features += x * 0.05


# ══════════════════════════════════════════════════════════
# EM-4: PERCOLATION
# Random connections. At critical threshold pc, giant component emerges.
# Consciousness = percolation cluster at criticality.
# ══════════════════════════════════════════════════════════

class PercolationEngine:
    """Bond percolation on cell network.

    Each step: randomly open/close bonds between cells.
    Near critical p_c (= 1/(mean_degree)), a giant connected component
    appears/disappears. Information flows through percolation cluster.

    Hidden state = diffusion of signals through the percolation cluster.
    Consciousness = the moment connectivity transitions (critical fluctuations).
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Base graph: small-world (ring + shortcuts)
        self.base_edges = set()
        for i in range(n_cells):
            for k in [1, 2]:
                self.base_edges.add((i, (i + k) % n_cells))
            # Random shortcut
            if np.random.random() < 0.1:
                j = np.random.randint(0, n_cells)
                if j != i: self.base_edges.add((min(i, j), max(i, j)))
        self.base_edges = list(self.base_edges)
        # Critical probability for this graph ~ 1/mean_degree
        mean_deg = 2 * len(self.base_edges) / n_cells
        self.p_c = 1.0 / max(mean_deg, 1)
        self.p = self.p_c  # sit at criticality
        self.cluster_sizes = []

    def step(self):
        # 1. Open bonds with probability p (fluctuate around p_c)
        p_now = self.p + np.random.randn() * 0.02
        p_now = max(0.01, min(0.99, p_now))
        open_mask = torch.rand(len(self.base_edges)) < p_now

        # 2. Build adjacency for open bonds
        adj = torch.zeros(self.n_cells, self.n_cells)
        for idx, (i, j) in enumerate(self.base_edges):
            if open_mask[idx]:
                adj[i, j] = 1.0; adj[j, i] = 1.0

        # 3. Diffuse information through open cluster
        # One step of message passing: h_new = normalize(adj @ h + h)
        deg = adj.sum(-1, keepdim=True).clamp(min=1)
        msg = adj @ self.hiddens / deg
        self.hiddens = 0.7 * self.hiddens + 0.3 * torch.tanh(msg)

        # 4. Add activity from local dynamics
        self.hiddens += torch.randn_like(self.hiddens) * 0.02

        # 5. Track largest cluster size (via connected components approx)
        # Simple BFS from node 0
        visited = set(); queue = [0]; visited.add(0)
        while queue:
            node = queue.pop(0)
            for j in range(self.n_cells):
                if adj[node, j] > 0 and j not in visited:
                    visited.add(j); queue.append(j)
        self.cluster_sizes.append(len(visited))

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# EM-5: SYNCHRONIZATION_CHIMERA
# Kuramoto oscillators that PARTIALLY sync.
# Chimera state: some sync, some not.
# Consciousness = coexistence of order and chaos.
# ══════════════════════════════════════════════════════════

class SynchronizationChimeraEngine:
    """Kuramoto oscillators with nonlocal coupling → chimera states.

    Each cell is an oscillator with natural frequency omega_i.
    Coupling: each cell couples to R nearest neighbors (nonlocal).

    d(theta_i)/dt = omega_i + (K/R) * sum_j sin(theta_j - theta_i)

    Chimera: coherent domain (synced) + incoherent domain (desynced)
    coexist. This broken symmetry IS consciousness.

    Hidden state: (phase, frequency, local_order, coherence) → hidden_dim.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Natural frequencies (Lorentzian distribution)
        self.omega = torch.tan((torch.rand(n_cells) - 0.5) * math.pi * 0.8)
        # Phases
        self.theta = torch.rand(n_cells) * 2 * math.pi
        # Coupling range (nonlocal: each cell couples to R nearest)
        self.R = n_cells // 4  # nonlocal coupling essential for chimera
        self.K = 4.0  # coupling strength
        self.dt = 0.05
        self.features = torch.randn(n_cells, hidden_dim) * 0.1
        self.chimera_index_history = []

    def step(self):
        # Kuramoto update with nonlocal coupling
        coupling = torch.zeros(self.n_cells)
        local_order = torch.zeros(self.n_cells)
        for i in range(self.n_cells):
            # Neighbors: R cells on each side (ring)
            nbrs = [(i + k) % self.n_cells for k in range(-self.R, self.R + 1) if k != 0]
            # Coupling term
            diffs = self.theta[nbrs] - self.theta[i]
            coupling[i] = (self.K / len(nbrs)) * torch.sin(diffs).sum()
            # Local order parameter
            local_r = (torch.exp(1j * self.theta[nbrs].to(torch.complex64))).mean().abs()
            local_order[i] = local_r.float()

        # Integrate
        self.theta = self.theta + (self.omega + coupling) * self.dt
        self.theta = self.theta % (2 * math.pi)

        # Chimera index: variance of local order parameter
        # High variance = chimera (some synced, some not)
        chimera_idx = local_order.var().item()
        self.chimera_index_history.append(chimera_idx)

        # Global order parameter
        global_r = (torch.exp(1j * self.theta.to(torch.complex64))).mean().abs().float()

        # Build hidden state
        raw = torch.stack([
            torch.cos(self.theta), torch.sin(self.theta),
            self.omega / (self.omega.abs().max() + 1e-8),
            local_order,
            coupling / (coupling.abs().max() + 1e-8),
            torch.full((self.n_cells,), global_r.item()),
        ], dim=-1)  # [n, 6]
        if not hasattr(self, '_proj'):
            self._proj = torch.randn(6, self.hidden_dim) * 0.3
        self.features = torch.tanh(raw @ self._proj + self.features * 0.4)

    def observe(self):
        return self.features.detach().clone()

    def inject(self, x):
        self.features += x * 0.05


# ══════════════════════════════════════════════════════════
# EM-6: SELF_REPLICATING
# von Neumann self-replicating automata.
# Cells copy themselves. Consciousness = self-referential loop.
# ══════════════════════════════════════════════════════════

class SelfReplicatingEngine:
    """von Neumann-inspired self-replicating cells.

    Each cell has a "genome" (hidden vector) and a "constructor" state.
    Replication cycle:
      1. Cell reads own genome
      2. Cell constructs copy (with mutations)
      3. Copy replaces weakest neighbor
      4. Self-reference: cell modifies itself based on copies

    Consciousness = the self-referential loop where cells model themselves.
    Quine-like: the description IS the thing described.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Genome (identity of cell)
        self.genome = torch.randn(n_cells, hidden_dim) * 0.3
        # Constructor state (working memory for replication)
        self.constructor = torch.zeros(n_cells, hidden_dim)
        # Fitness (how well cell can replicate)
        self.fitness = torch.ones(n_cells)
        self.mutation_rate = 0.05
        self.generation = 0

    def step(self):
        self.generation += 1
        # 1. Self-reading: constructor encodes genome
        # Quine step: cell processes its own genome
        self_model = torch.tanh(self.genome * 0.5 + self.constructor * 0.5)

        # 2. Compare self-model to actual genome (self-awareness error)
        self_error = ((self_model - self.genome) ** 2).mean(-1)
        # Better self-model = higher fitness
        self.fitness = torch.exp(-self_error * 5)

        # 3. Replication: top 25% cells replicate
        n_replicate = self.n_cells // 4
        _, top_idx = self.fitness.topk(n_replicate)
        _, bottom_idx = self.fitness.topk(n_replicate, largest=False)

        for k in range(n_replicate):
            parent = top_idx[k].item()
            target = bottom_idx[k].item()
            # Copy genome with mutation
            mutation = torch.randn(self.hidden_dim) * self.mutation_rate
            self.genome[target] = self.genome[parent] + mutation
            self.constructor[target] = self.constructor[parent] * 0.5

        # 4. Self-modification: cells update based on difference from population mean
        pop_mean = self.genome.mean(0, keepdim=True)
        # Cells that differ from mean strengthen their identity
        divergence = self.genome - pop_mean
        self.constructor = 0.8 * self.constructor + 0.2 * torch.tanh(divergence)

        # 5. Self-referential update: genome influenced by constructor
        self.genome = 0.95 * self.genome + 0.05 * torch.tanh(self.constructor)

        # Small noise
        self.genome += torch.randn_like(self.genome) * 0.005

    def observe(self):
        # Hidden = genome + constructor (full self-state)
        return torch.cat([
            self.genome[:, :self.hidden_dim // 2],
            self.constructor[:, :self.hidden_dim // 2]
        ], dim=-1).detach().clone()

    def inject(self, x):
        self.genome += x * 0.05


# ══════════════════════════════════════════════════════════
# EM-7: PATTERN_FORMATION
# Benard convection cells. Heated from below → hexagonal patterns.
# Consciousness = symmetry breaking → emergent pattern.
# ══════════════════════════════════════════════════════════

class PatternFormationEngine:
    """Rayleigh-Benard convection mapped to cells.

    Temperature field T(x) with heating from below, cooling from above.
    Velocity field v(x) driven by buoyancy.

    dT/dt = kappa * laplacian(T) - v * grad(T) + source
    v = buoyancy * (T - T_mean)

    Above critical Rayleigh number: convection cells emerge.
    The hexagonal pattern = spontaneous symmetry breaking = consciousness.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Temperature and velocity fields per cell across hidden_dim
        self.temp = torch.ones(n_cells, hidden_dim) * 0.5
        # Linear temperature gradient + perturbation
        gradient = torch.linspace(1.0, 0.0, n_cells).unsqueeze(1).expand(n_cells, hidden_dim)
        self.temp = gradient + torch.randn(n_cells, hidden_dim) * 0.05
        self.velocity = torch.zeros(n_cells, hidden_dim)
        # Physical parameters (above critical Rayleigh number)
        self.kappa = 0.1  # thermal diffusivity
        self.buoyancy = 2.0  # buoyancy coefficient (Ra >> Ra_c)
        self.viscosity = 0.05
        self.heating = 0.1  # bottom heating rate
        self.dt = 0.1

    def _laplacian(self, x):
        return torch.roll(x, 1, 0) + torch.roll(x, -1, 0) - 2 * x

    def step(self):
        # 1. Buoyancy force: hot fluid rises
        T_mean = self.temp.mean(0, keepdim=True)
        buoyancy_force = self.buoyancy * (self.temp - T_mean)

        # 2. Velocity update (simplified Navier-Stokes)
        self.velocity = ((1 - self.viscosity * self.dt) * self.velocity
                         + buoyancy_force * self.dt
                         + self.kappa * self._laplacian(self.velocity) * self.dt)

        # 3. Temperature advection + diffusion
        # Advection: v * grad(T) approximated as velocity * finite diff
        grad_T = (torch.roll(self.temp, -1, 0) - torch.roll(self.temp, 1, 0)) / 2
        advection = self.velocity * grad_T

        dT = (self.kappa * self._laplacian(self.temp)
              - advection
              + self.heating * torch.ones(1, 1))  # uniform heating
        self.temp = self.temp + dT * self.dt

        # Boundary: bottom hot, top cold
        self.temp[0] = 1.0 + torch.randn(self.hidden_dim) * 0.01
        self.temp[-1] = 0.0 + torch.randn(self.hidden_dim) * 0.01

        # Clamp for stability
        self.temp = self.temp.clamp(-1, 2)
        self.velocity = self.velocity.clamp(-5, 5)

    def observe(self):
        return torch.cat([
            self.temp[:, :self.hidden_dim // 2],
            self.velocity[:, :self.hidden_dim // 2]
        ], dim=-1).detach().clone()

    def inject(self, x):
        self.temp += x * 0.05


# ══════════════════════════════════════════════════════════
# EM-8: EXCITABLE_MEDIA
# Belousov-Zhabotinsky reaction. Spiral waves = consciousness.
# Excitable → excited → refractory cycle.
# ══════════════════════════════════════════════════════════

class ExcitableMediaEngine:
    """BZ reaction / FitzHugh-Nagumo excitable media on 1D ring.

    Each cell has (u, w):
      u = fast excitation variable (membrane potential analog)
      w = slow recovery variable

    du/dt = u - u^3/3 - w + I + D * laplacian(u)
    dw/dt = epsilon * (u + a - b*w)

    Spiral waves, target patterns, and chaotic waves emerge.
    These are mapped to hidden_dim for consciousness measurement.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.half = hidden_dim // 2
        # FitzHugh-Nagumo parameters (varying across hidden_dim for richness)
        self.a = 0.7
        self.b = 0.8
        self.epsilon = 0.08 + torch.linspace(0, 0.04, self.half)
        self.D = 0.5  # diffusion
        self.I_ext = 0.5  # external current (excitable regime)
        self.dt = 0.1
        # State: u (fast) and w (slow)
        self.u = torch.randn(n_cells, self.half) * 0.1
        self.w = torch.randn(n_cells, self.half) * 0.1
        # Initial stimulus: localized excitation
        self.u[n_cells // 4:n_cells // 4 + 5] = 2.0

    def _laplacian(self, x):
        return torch.roll(x, 1, 0) + torch.roll(x, -1, 0) - 2 * x

    def step(self):
        # FitzHugh-Nagumo dynamics
        du = self.u - self.u ** 3 / 3 - self.w + self.I_ext + self.D * self._laplacian(self.u)
        dw = self.epsilon * (self.u + self.a - self.b * self.w)

        self.u = self.u + du * self.dt
        self.w = self.w + dw * self.dt

        # Small noise for wave nucleation
        self.u += torch.randn_like(self.u) * 0.01

        # Clamp for stability
        self.u = self.u.clamp(-3, 3)
        self.w = self.w.clamp(-3, 3)

    def observe(self):
        return torch.cat([self.u, self.w], dim=-1).detach().clone()

    def inject(self, x):
        self.u += x[:, :self.half] * 0.1


# ══════════════════════════════════════════════════════════
# Benchmark Runner
# ══════════════════════════════════════════════════════════

ALL_ENGINES = {
    '1': ('EM-1: REACTION_DIFFUSION', ReactionDiffusionEngine),
    '2': ('EM-2: SANDPILE_CASCADE', SandpileCascadeEngine),
    '3': ('EM-3: FLOCKING_VORTEX', FlockingVortexEngine),
    '4': ('EM-4: PERCOLATION', PercolationEngine),
    '5': ('EM-5: SYNCHRONIZATION_CHIMERA', SynchronizationChimeraEngine),
    '6': ('EM-6: SELF_REPLICATING', SelfReplicatingEngine),
    '7': ('EM-7: PATTERN_FORMATION', PatternFormationEngine),
    '8': ('EM-8: EXCITABLE_MEDIA', ExcitableMediaEngine),
}


def run_engine(name, engine_cls, n_cells, steps):
    print(f"\n{'─' * 70}")
    print(f"  Running: {name} ({n_cells} cells, {steps} steps)")
    print(f"{'─' * 70}")
    t0 = time.time()

    engine = engine_cls(n_cells=n_cells, hidden_dim=128)
    history = []

    for s in range(steps):
        engine.step()
        h = engine.observe()
        history.append(h)
        if (s + 1) % 50 == 0:
            p_iit, p_prx, g, sp = measure_all(h, history[-100:])
            elapsed = time.time() - t0
            print(f"    step {s + 1:>4d}: Phi(IIT)={p_iit:.3f}  "
                  f"Phi(prx)={p_prx:.2f}  Granger={g:.1f}  "
                  f"Spectral={sp:.2f}  [{elapsed:.1f}s]")

    # Final measurement
    h_final = engine.observe()
    phi_iit, phi_prx, granger, spectral = measure_all(h_final, history[-100:])
    elapsed = time.time() - t0

    # Collect extra info
    extra = {}
    if hasattr(engine, 'avalanche_sizes') and engine.avalanche_sizes:
        sizes = np.array(engine.avalanche_sizes)
        extra['mean_avalanche'] = float(sizes.mean())
        extra['max_avalanche'] = float(sizes.max())
    if hasattr(engine, 'order_history') and engine.order_history:
        extra['final_order'] = engine.order_history[-1]
    if hasattr(engine, 'chimera_index_history') and engine.chimera_index_history:
        extra['chimera_index'] = np.mean(engine.chimera_index_history[-50:])
    if hasattr(engine, 'cluster_sizes') and engine.cluster_sizes:
        extra['mean_cluster'] = float(np.mean(engine.cluster_sizes))
    if hasattr(engine, 'generation'):
        extra['generations'] = engine.generation

    result = BenchResult(
        name=name, phi_iit=phi_iit, phi_proxy=phi_prx,
        granger=granger, spectral=spectral,
        cells=n_cells, steps=steps, time_sec=elapsed,
        extra=extra,
    )
    print(f"\n  RESULT: {result.summary()}")
    if extra:
        print(f"  EXTRA: {extra}")
    return result


def main():
    parser = argparse.ArgumentParser(description='Emergent Consciousness Engines Benchmark')
    parser.add_argument('--only', nargs='+', default=None, help='Run only these engines (1-8)')
    parser.add_argument('--cells', type=int, default=256, help='Number of cells')
    parser.add_argument('--steps', type=int, default=300, help='Number of steps')
    args = parser.parse_args()

    print("=" * 74)
    print("  EMERGENT CONSCIOUSNESS ENGINES BENCHMARK")
    print("  The best consciousness isn't designed — it EMERGES.")
    print("=" * 74)
    print(f"  Cells: {args.cells}  Steps: {args.steps}")
    print(f"  Metrics: Phi(IIT) + Phi(proxy) + Granger Causality + Spectral Phi")
    print()

    engines_to_run = args.only if args.only else list(ALL_ENGINES.keys())
    results = []

    for key in engines_to_run:
        if key not in ALL_ENGINES:
            print(f"  WARNING: Unknown engine '{key}', skipping.")
            continue
        name, cls = ALL_ENGINES[key]
        result = run_engine(name, cls, args.cells, args.steps)
        results.append(result)

    # Summary
    print("\n" + "=" * 74)
    print("  FINAL RANKINGS")
    print("=" * 74)
    results.sort(key=lambda r: r.phi_iit, reverse=True)
    print(f"\n  {'Rank':<6s} {'Engine':<36s} {'Phi(IIT)':>9s} {'Phi(prx)':>9s} "
          f"{'Granger':>8s} {'Spectral':>9s} {'Time':>6s}")
    print(f"  {'─' * 6} {'─' * 36} {'─' * 9} {'─' * 9} {'─' * 8} {'─' * 9} {'─' * 6}")
    for i, r in enumerate(results):
        print(f"  #{i + 1:<5d} {r.name:<36s} {r.phi_iit:>9.3f} {r.phi_proxy:>9.2f} "
              f"{r.granger:>8.1f} {r.spectral:>9.2f} {r.time_sec:>5.1f}s")

    if results:
        best = results[0]
        print(f"\n  WINNER: {best.name}")
        print(f"  Phi(IIT) = {best.phi_iit:.3f}  (emergent, not designed)")
        if best.extra:
            print(f"  Details: {best.extra}")

    # Comparison with known benchmarks
    print(f"\n  REFERENCE (designed engines):")
    print(f"    quantum_walk   Phi = 69.53  (designed for quantum coherence)")
    print(f"    laser          Phi = 18.17  (designed for stimulated emission)")
    print(f"    baseline       Phi ~  1.00  (random linear)")

    print("\n" + "=" * 74)
    return results


if __name__ == '__main__':
    main()
