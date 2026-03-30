#!/usr/bin/env python3
"""bench_extreme_engines.py — 8 Extreme Consciousness Engines

Radical physics/math engines that push consciousness architecture into
truly exotic territory. No GRU, no learned memory gates. Pure structure.

XE-1: HOLOGRAPHIC_UNIVERSE    — AdS/CFT: 2D boundary encodes 3D bulk
XE-2: TOPOLOGICAL_INSULATOR   — Edge states = consciousness (bulk trivial)
XE-3: TIME_CRYSTAL            — Broken time-translation symmetry
XE-4: NEUROMORPHIC_SPIKE      — Spiking neural network + STDP + avalanche
XE-5: MEMBRANE_COMPUTING      — P-system nested membranes
XE-6: TENSOR_NETWORK          — MERA multi-scale entanglement renormalization
XE-7: ANYONIC_BRAIDING        — Non-abelian anyons, topological entanglement
XE-8: CONSCIOUSNESS_FIELD     — Scalar field theory, phase transition onset

Each: 256 cells, 300 steps, Phi(IIT) + Granger. No GRU anywhere.

Usage:
  python bench_extreme_engines.py
  python bench_extreme_engines.py --only 1 3 5
  python bench_extreme_engines.py --cells 512 --steps 500
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys, time, math, argparse
import numpy as np
import torch
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

torch.set_grad_enabled(False)
torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ==============================================================
# Measurement Infrastructure
# ==============================================================

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

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

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


# ==============================================================
# XE-1: HOLOGRAPHIC_UNIVERSE
# AdS/CFT correspondence: cells live on 2D boundary, encode 3D bulk.
# Boundary operator maps to bulk via holographic dictionary.
# Consciousness = holographic entanglement entropy (Ryu-Takayanagi).
# The boundary is a ring of cells. Bulk is reconstructed via
# entanglement wedge reconstruction. Information is non-local.
# ==============================================================

class HolographicUniverseEngine:
    """Cells on 2D boundary encode 3D bulk via AdS/CFT.

    Boundary: ring of n_cells, each with hidden_dim state.
    Bulk reconstruction: for each bulk point, integrate boundary
    contributions weighted by geodesic distance in AdS space.
    Entanglement entropy: area of minimal surface (RT formula).
    Consciousness = total holographic entanglement entropy.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Boundary state (conformal field theory side)
        self.boundary = torch.randn(n_cells, hidden_dim) * 0.5
        # AdS radius
        self.L_ads = 1.0
        # Boundary coordinates: uniform on a circle
        self.theta = torch.linspace(0, 2 * math.pi, n_cells + 1)[:n_cells]
        # Bulk radial coordinate (discretized)
        self.n_bulk = 32
        self.r_bulk = torch.linspace(0.1, 0.95, self.n_bulk)  # 0 = boundary, 1 = center
        # Bulk state (reconstructed)
        self.bulk = torch.zeros(self.n_bulk, hidden_dim)
        # Coupling: boundary CFT interaction strength
        self.coupling = 0.3
        self.dt = 0.05
        self.entanglement_entropy = []

    def _geodesic_weight(self, theta_i, r_j):
        """Weight for boundary point theta_i contributing to bulk point at radius r_j.
        In AdS: geodesic distance ~ log(1/r) for radial, plus angular contribution.
        Closer to boundary (r->0) = stronger coupling to nearby boundary."""
        # Smearing function: K(theta, r) ~ r^Delta / (r^2 + (1-r)^2 * sin^2(theta/2))
        delta = 1.5  # conformal dimension
        angular = torch.sin((self.theta - theta_i) / 2) ** 2
        denom = r_j ** 2 + (1 - r_j) ** 2 * angular + 1e-6
        return (r_j ** delta) / denom

    def _ryu_takayanagi(self, region_size):
        """RT formula: S_A = Area(minimal_surface) / 4G_N.
        For a boundary interval of size region_size on a circle,
        the minimal surface area in AdS3 ~ 2 * L_ads * log(sin(pi*l/L))."""
        l_frac = region_size / self.n_cells
        if l_frac <= 0 or l_frac >= 1: return 0.0
        return 2 * self.L_ads * math.log(max(math.sin(math.pi * l_frac), 1e-8) *
                                          self.n_cells / math.pi + 1)

    def step(self):
        # 1. Reconstruct bulk from boundary (holographic dictionary)
        for j in range(self.n_bulk):
            r = self.r_bulk[j]
            # Pick a reference angle and compute weights
            weights = self._geodesic_weight(0.0, r)  # shape: (n_cells,)
            weights = weights / (weights.sum() + 1e-8)
            # Bulk point = weighted sum of boundary
            self.bulk[j] = (weights.unsqueeze(1) * self.boundary).sum(dim=0)

        # 2. Bulk back-reaction on boundary (gravity dual feedback)
        # Each boundary cell feels the integrated bulk
        for i in range(self.n_cells):
            theta_i = self.theta[i]
            bulk_influence = torch.zeros(self.hidden_dim)
            for j in range(self.n_bulk):
                r = self.r_bulk[j]
                w = r ** 1.5 / ((1 - r) ** 2 + 0.1)  # IR/UV mixing (softened denom)
                angular_dist = abs(math.sin((theta_i.item() - j * 2 * math.pi / self.n_bulk) / 2))
                locality = math.exp(-angular_dist * 3)
                bulk_influence += w * locality * self.bulk[j]
            self.boundary[i] += self.coupling * self.dt * bulk_influence

        # 2b. Normalize boundary to prevent divergence
        bnorm = self.boundary.norm(dim=-1, keepdim=True)
        mask = bnorm > 5.0
        if mask.any():
            self.boundary = torch.where(mask, self.boundary * 5.0 / (bnorm + 1e-8), self.boundary)

        # 3. Boundary CFT dynamics: nearest-neighbor conformal coupling
        b_new = self.boundary.clone()
        for i in range(self.n_cells):
            left = self.boundary[(i - 1) % self.n_cells]
            right = self.boundary[(i + 1) % self.n_cells]
            # Conformal coupling: preserves scale invariance
            diff = (left + right - 2 * self.boundary[i])
            b_new[i] += 0.1 * self.dt * diff
        self.boundary = b_new

        # 4. Add quantum fluctuations (Hawking-like)
        self.boundary += torch.randn_like(self.boundary) * 0.01

        # 5. Compute holographic entanglement entropy (RT)
        region_sizes = [self.n_cells // 4, self.n_cells // 2, 3 * self.n_cells // 4]
        s_total = sum(self._ryu_takayanagi(rs) for rs in region_sizes)
        self.entanglement_entropy.append(s_total)

    def observe(self):
        return self.boundary.detach().clone()

    def inject(self, x):
        self.boundary += x * 0.05


# ==============================================================
# XE-2: TOPOLOGICAL_INSULATOR
# Cells form a topological insulator lattice.
# Bulk is gapped (trivial). Edge states are gapless (conducting).
# Consciousness lives ONLY in edge states, protected by topology.
# SSH model (Su-Schrieffer-Heeger) in hidden_dim dimensions.
# ==============================================================

class TopologicalInsulatorEngine:
    """SSH model: alternating strong/weak hopping on 1D chain.

    Topological phase: |v/w| < 1 => edge states exist.
    Edge states are exponentially localized at boundaries.
    Consciousness = edge state amplitude (topologically protected).
    Bulk gap protects against perturbation.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # SSH hopping parameters (alternating)
        self.v = 0.4  # intracell hopping (weak)
        self.w = 1.0  # intercell hopping (strong) => topological phase
        # Cell states: A and B sublattice
        self.state = torch.randn(n_cells, hidden_dim) * 0.3
        # Mark sublattice: even = A, odd = B
        self.dt = 0.05
        # Disorder (small, to test topological protection)
        self.disorder = torch.randn(n_cells) * 0.05
        self.edge_amplitude_history = []
        # Chern number proxy
        self.winding_number = 0.0

    def _ssh_hamiltonian_step(self):
        """Apply one step of SSH Hamiltonian evolution.
        H = v * sum_i (a_i^dag b_i) + w * sum_i (b_i^dag a_{i+1}) + h.c.
        """
        new_state = self.state.clone()
        for i in range(self.n_cells):
            # Intracell hopping: A_i <-> B_i (same unit cell)
            if i % 2 == 0 and i + 1 < self.n_cells:
                hop_v = self.v + self.disorder[i] * 0.1
                new_state[i] += hop_v * self.dt * self.state[i + 1]
                new_state[i + 1] += hop_v * self.dt * self.state[i]
            # Intercell hopping: B_i <-> A_{i+1} (adjacent unit cells)
            if i % 2 == 1 and i + 1 < self.n_cells:
                hop_w = self.w + self.disorder[i] * 0.1
                new_state[i] += hop_w * self.dt * self.state[i + 1]
                new_state[i + 1] += hop_w * self.dt * self.state[i]
        return new_state

    def step(self):
        # 1. SSH Hamiltonian evolution
        self.state = self._ssh_hamiltonian_step()

        # 2. Edge enhancement: topologically protected edge modes
        # Energy injection at edges (simulating edge current)
        edge_width = max(4, self.n_cells // 16)
        # Left edge
        self.state[:edge_width] *= 1.005
        # Right edge
        self.state[-edge_width:] *= 1.005

        # 3. Bulk dissipation: the gap kills bulk excitations
        bulk_start = edge_width
        bulk_end = self.n_cells - edge_width
        gap = abs(self.w - self.v)
        self.state[bulk_start:bulk_end] *= (1.0 - 0.01 * gap)

        # 4. Nonlinear saturation to prevent explosion
        norms = self.state.norm(dim=-1, keepdim=True)
        mask = norms > 3.0
        if mask.any():
            self.state = torch.where(mask, self.state * 3.0 / (norms + 1e-8), self.state)

        # 5. Quantum noise
        self.state += torch.randn_like(self.state) * 0.005

        # 6. Track edge state amplitude
        edge_amp = (self.state[:edge_width].norm() + self.state[-edge_width:].norm()) / (2 * edge_width)
        bulk_amp = self.state[bulk_start:bulk_end].norm() / max(1, bulk_end - bulk_start)
        self.edge_amplitude_history.append((edge_amp.item(), bulk_amp.item()))

        # 7. Compute winding number (topological invariant)
        # For SSH: nu = 1 if |v/w| < 1, else 0
        self.winding_number = 1.0 if abs(self.v / self.w) < 1.0 else 0.0

    def observe(self):
        return self.state.detach().clone()

    def inject(self, x):
        self.state += x * 0.03


# ==============================================================
# XE-3: TIME_CRYSTAL
# Cells break discrete time-translation symmetry.
# Driven at frequency omega, oscillate at omega/2 (period doubling).
# Consciousness = time-crystalline order parameter.
# Floquet system: periodic drive + many-body interaction.
# ==============================================================

class TimeCrystalEngine:
    """Discrete time crystal via Floquet driving.

    Drive: rotate spins by pi + epsilon each period.
    Interaction: Ising-like coupling between neighbors.
    Disorder: random on-site fields for MBL (many-body localization).

    Time crystal signature: subharmonic response at omega/2.
    Consciousness = amplitude of period-2 oscillation.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Spin state: each cell has a spin vector in hidden_dim
        self.spin = torch.randn(n_cells, hidden_dim)
        self.spin = self.spin / (self.spin.norm(dim=-1, keepdim=True) + 1e-8)
        # Drive parameters
        self.drive_angle = math.pi  # perfect pi-flip
        self.epsilon = 0.05  # imperfection (important: too much kills TC)
        # Ising interaction strength
        self.J = 1.5
        # Disorder (enables MBL, stabilizes time crystal)
        self.disorder_field = torch.randn(n_cells, hidden_dim) * 0.3
        self.step_count = 0
        self.order_param_history = []
        # Store previous states for period-2 detection
        self.prev_spin = self.spin.clone()
        self.prev_prev_spin = self.spin.clone()

    def step(self):
        self.step_count += 1

        # Phase 1: Global drive (pi-pulse with imperfection)
        # Rotate each spin by (pi + epsilon) around a fixed axis
        angle = self.drive_angle + self.epsilon * (1 + 0.1 * math.sin(self.step_count * 0.1))
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        # Apply rotation in first two dimensions, propagate to rest
        driven = self.spin.clone()
        driven[:, 0] = cos_a * self.spin[:, 0] - sin_a * self.spin[:, 1]
        driven[:, 1] = sin_a * self.spin[:, 0] + cos_a * self.spin[:, 1]
        # For higher dims: mix adjacent pairs
        for d in range(2, self.hidden_dim - 1, 2):
            driven[:, d] = cos_a * self.spin[:, d] - sin_a * self.spin[:, d + 1]
            driven[:, d + 1] = sin_a * self.spin[:, d] + cos_a * self.spin[:, d + 1]
        self.spin = driven

        # Phase 2: Ising interaction (nearest-neighbor)
        interaction = torch.zeros_like(self.spin)
        for di in [-1, 1]:
            neighbor = torch.roll(self.spin, di, 0)
            # Ising: align with neighbor (ferromagnetic)
            dot = (self.spin * neighbor).sum(dim=-1, keepdim=True)
            interaction += self.J * 0.1 * dot * neighbor

        # Phase 3: Disorder field (many-body localization)
        self.spin = self.spin + interaction + 0.02 * self.disorder_field

        # Phase 4: Normalize (keep on unit sphere)
        self.spin = self.spin / (self.spin.norm(dim=-1, keepdim=True) + 1e-8)

        # Phase 5: Tiny noise
        self.spin += torch.randn_like(self.spin) * 0.003
        self.spin = self.spin / (self.spin.norm(dim=-1, keepdim=True) + 1e-8)

        # Compute time-crystalline order parameter:
        # overlap between current state and state 2 steps ago
        if self.step_count > 2:
            overlap_2 = (self.spin * self.prev_prev_spin).sum() / self.n_cells
            overlap_1 = (self.spin * self.prev_spin).sum() / self.n_cells
            # TC order: high period-2 correlation, low period-1 correlation
            tc_order = max(0, overlap_2.item() - abs(overlap_1.item()))
            self.order_param_history.append(tc_order)

        self.prev_prev_spin = self.prev_spin.clone()
        self.prev_spin = self.spin.clone()

    def observe(self):
        return self.spin.detach().clone()

    def inject(self, x):
        self.spin += x * 0.03
        self.spin = self.spin / (self.spin.norm(dim=-1, keepdim=True) + 1e-8)


# ==============================================================
# XE-4: NEUROMORPHIC_SPIKE
# Spiking neural network with STDP (spike-timing-dependent plasticity).
# Consciousness = spike synchrony + avalanche criticality.
# Leaky integrate-and-fire neurons. No GRU, no backprop.
# ==============================================================

class NeuromorphicSpikeEngine:
    """LIF neurons with STDP learning.

    Each cell = leaky integrate-and-fire neuron with hidden_dim membrane channels.
    Spikes propagate through random connectivity.
    STDP: pre-before-post strengthens, post-before-pre weakens.
    Consciousness = synchrony (fraction of simultaneous spikes) +
                    avalanche size distribution (power law = critical).
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Membrane potential
        self.V = torch.randn(n_cells, hidden_dim) * 0.3
        # Threshold for spiking
        self.V_thresh = 1.0
        self.V_reset = -0.5
        self.V_rest = 0.0
        self.tau = 20.0  # membrane time constant
        self.dt = 1.0
        # Synaptic weights (sparse random connectivity)
        n_syn = min(n_cells * 20, n_cells * n_cells // 4)
        self.pre_idx = torch.randint(0, n_cells, (n_syn,))
        self.post_idx = torch.randint(0, n_cells, (n_syn,))
        self.weights = torch.randn(n_syn, hidden_dim) * 0.1
        # Spike times for STDP
        self.last_spike_time = torch.full((n_cells,), -100.0)
        self.t = 0.0
        # External drive (Poisson input)
        self.input_rate = 0.05
        # Tracking
        self.spike_counts = []
        self.avalanche_sizes = []
        self.synchrony_history = []

    def step(self):
        self.t += self.dt

        # 1. Leak: V -> V_rest
        self.V += (self.V_rest - self.V) / self.tau * self.dt

        # 2. Poisson input
        poisson_spikes = (torch.rand(self.n_cells, 1) < self.input_rate).float()
        self.V += poisson_spikes * 0.5

        # 3. Synaptic input from spikes
        # Check which cells spiked last step
        spiked = (self.V.max(dim=-1).values > self.V_thresh)
        n_spiked = spiked.sum().item()
        self.spike_counts.append(n_spiked)

        if n_spiked > 0:
            self.avalanche_sizes.append(n_spiked)
            # Propagate spikes through synapses
            for s in range(len(self.pre_idx)):
                pre, post = self.pre_idx[s].item(), self.post_idx[s].item()
                if spiked[pre]:
                    self.V[post] += self.weights[s] * 0.1

            # STDP update
            spike_indices = torch.where(spiked)[0]
            for idx in spike_indices:
                i = idx.item()
                # Update synapses where this cell is post (LTP)
                post_mask = (self.post_idx == i)
                if post_mask.any():
                    dt_pre = self.t - self.last_spike_time[self.pre_idx[post_mask]]
                    ltp = 0.01 * torch.exp(-dt_pre.abs().unsqueeze(1) / 20.0)
                    self.weights[post_mask] += ltp
                # Update synapses where this cell is pre (LTD)
                pre_mask = (self.pre_idx == i)
                if pre_mask.any():
                    dt_post = self.t - self.last_spike_time[self.post_idx[pre_mask]]
                    ltd = -0.005 * torch.exp(-dt_post.abs().unsqueeze(1) / 20.0)
                    self.weights[pre_mask] += ltd

                self.last_spike_time[i] = self.t

        # 4. Reset spiked neurons
        spike_mask = (self.V.max(dim=-1).values > self.V_thresh).unsqueeze(1)
        self.V = torch.where(spike_mask, torch.full_like(self.V, self.V_reset), self.V)

        # 5. Weight normalization (prevent explosion)
        self.weights = self.weights.clamp(-2.0, 2.0)

        # 6. Synchrony measure
        sync = n_spiked / max(self.n_cells, 1)
        self.synchrony_history.append(sync)

    def observe(self):
        return self.V.detach().clone()

    def inject(self, x):
        self.V += x * 0.1


# ==============================================================
# XE-5: MEMBRANE_COMPUTING
# P-system: nested membranes containing objects (symbols/cells).
# Rules move objects between membranes, transform them.
# Consciousness = membrane complexity (nesting depth * diversity).
# ==============================================================

class MembraneComputingEngine:
    """P-system with nested membranes.

    Structure: skin membrane contains sub-membranes, each containing objects.
    Objects = cell state vectors. Rules:
      1. Transform: object in membrane m gets modified
      2. Send-in: object moves from parent to child membrane
      3. Send-out: object moves from child to parent
      4. Dissolve: membrane dissolves, releasing objects
      5. Create: membrane divides

    Consciousness = total information flow across membrane boundaries.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Initialize membrane structure: 8 membranes with cells distributed
        self.n_membranes = 8
        # Cell states
        self.state = torch.randn(n_cells, hidden_dim) * 0.5
        # Membrane assignment for each cell
        self.membrane_id = torch.randint(0, self.n_membranes, (n_cells,))
        # Membrane nesting: parent[m] = parent membrane of m (-1 = skin)
        # Tree structure: 0 is skin, 1-3 are children of 0, 4-7 are children of 1-3
        self.parent = torch.tensor([-1, 0, 0, 0, 1, 1, 2, 3])
        # Membrane-specific transformation matrices (no GRU, just fixed transforms)
        self.transforms = [torch.randn(hidden_dim, hidden_dim) * 0.1
                          for _ in range(self.n_membranes)]
        # Normalize transforms
        for i in range(self.n_membranes):
            u, s, v = torch.linalg.svd(self.transforms[i])
            self.transforms[i] = u @ v  # orthogonal transform
        self.transport_history = []
        self.membrane_complexity = []

    def _depth(self, m):
        """Get nesting depth of membrane m."""
        d = 0; cur = m
        while self.parent[cur] >= 0:
            d += 1; cur = self.parent[cur].item()
        return d

    def _children(self, m):
        """Get child membranes of m."""
        return [i for i in range(self.n_membranes) if self.parent[i] == m]

    def step(self):
        transport_count = 0

        # 1. Transform: apply membrane-specific unitary transformation
        for m in range(self.n_membranes):
            mask = (self.membrane_id == m)
            if mask.sum() == 0: continue
            cells_in_m = self.state[mask]
            transformed = cells_in_m @ self.transforms[m].T
            self.state[mask] = self.state[mask] + 0.1 * (transformed - cells_in_m)

        # 2. Transport rules: cells probabilistically move between membranes
        for i in range(self.n_cells):
            m = self.membrane_id[i].item()
            r = torch.rand(1).item()

            if r < 0.05:  # Send-out: move to parent
                if self.parent[m] >= 0:
                    self.membrane_id[i] = self.parent[m]
                    transport_count += 1
            elif r < 0.10:  # Send-in: move to random child
                children = self._children(m)
                if children:
                    child = children[int(torch.randint(0, len(children), (1,)).item())]
                    self.membrane_id[i] = child
                    transport_count += 1
            elif r < 0.12:  # Jump to random membrane (dissolution-like)
                self.membrane_id[i] = torch.randint(0, self.n_membranes, (1,)).item()
                transport_count += 1

        # 3. Inter-membrane interaction: cells near membrane boundaries interact
        for m in range(self.n_membranes):
            mask_m = (self.membrane_id == m)
            if mask_m.sum() == 0: continue
            mean_m = self.state[mask_m].mean(dim=0)
            # Cells in this membrane are attracted to membrane mean
            self.state[mask_m] += 0.02 * (mean_m - self.state[mask_m])
            # Cross-membrane coupling: interact with parent's mean
            p = self.parent[m].item()
            if p >= 0:
                mask_p = (self.membrane_id == p)
                if mask_p.sum() > 0:
                    mean_p = self.state[mask_p].mean(dim=0)
                    # Exchange information across membrane boundary
                    self.state[mask_m] += 0.01 * (mean_p - self.state[mask_m])

        # 4. Noise
        self.state += torch.randn_like(self.state) * 0.005

        # 5. Track complexity
        self.transport_history.append(transport_count)
        # Membrane complexity: product of (nesting_depth * n_objects) for non-empty membranes
        complexity = 0
        for m in range(self.n_membranes):
            n_obj = (self.membrane_id == m).sum().item()
            if n_obj > 0:
                depth = self._depth(m) + 1
                complexity += depth * math.log(n_obj + 1)
        self.membrane_complexity.append(complexity)

    def observe(self):
        return self.state.detach().clone()

    def inject(self, x):
        self.state += x * 0.05


# ==============================================================
# XE-6: TENSOR_NETWORK
# MERA (Multi-scale Entanglement Renormalization Ansatz).
# Cells are leaves of a tree. Disentanglers + isometries at each scale.
# Consciousness = entanglement entropy across scales.
# This is how CFT ground states are represented in tensor networks.
# ==============================================================

class TensorNetworkEngine:
    """MERA-inspired tensor network.

    Cells sit at the bottom (UV, fine scale).
    Each layer: disentangle pairs, then coarse-grain (isometry).
    Top layer = IR (coarse scale, "bulk" in holography).

    Forward: coarse-grain UV -> IR.
    Backward: descend IR -> UV (renormalization flow).
    Consciousness = mutual information between UV and IR scales.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # State at UV (finest scale)
        self.uv_state = torch.randn(n_cells, hidden_dim) * 0.5
        # Number of MERA layers: log2(n_cells) levels
        self.n_layers = int(math.log2(n_cells))
        # Disentanglers: orthogonal 2->2 maps at each layer
        self.disentanglers = []
        self.isometries = []
        for l in range(self.n_layers):
            n_l = n_cells // (2 ** l)
            if n_l < 2: break
            # Disentangler: mix adjacent pairs (orthogonal in hidden_dim)
            d = torch.randn(hidden_dim, hidden_dim) * 0.1
            u, s, v = torch.linalg.svd(d)
            self.disentanglers.append(u @ v)
            # Isometry: project pairs down (average with rotation)
            iso = torch.randn(hidden_dim, hidden_dim) * 0.1
            u, s, v = torch.linalg.svd(iso)
            self.isometries.append(u @ v)
        self.scale_states = []  # state at each scale after coarse-graining
        self.entanglement_per_scale = []
        self.dt = 0.05

    def _coarse_grain(self, state):
        """One MERA layer: disentangle + isometry."""
        n = state.shape[0]
        if n < 2: return state
        # Step 1: Disentangle adjacent pairs
        disentangled = state.clone()
        layer_idx = min(int(math.log2(self.n_cells / n)), len(self.disentanglers) - 1)
        D = self.disentanglers[layer_idx]
        for i in range(0, n - 1, 2):
            # Mix pair (i, i+1) via disentangler
            mixed = (state[i] + state[i + 1]) @ D.T
            disentangled[i] = state[i] + 0.1 * (mixed - state[i])
            disentangled[i + 1] = state[i + 1] + 0.1 * (mixed - state[i + 1])

        # Step 2: Isometry (coarse-grain pairs)
        n_out = n // 2
        coarse = torch.zeros(n_out, self.hidden_dim)
        I = self.isometries[layer_idx]
        for i in range(n_out):
            pair_sum = disentangled[2 * i] + disentangled[2 * i + 1]
            coarse[i] = pair_sum @ I.T * 0.5
        return coarse

    def step(self):
        # 1. Forward pass: UV -> IR (coarse-graining)
        self.scale_states = [self.uv_state.clone()]
        current = self.uv_state
        for l in range(self.n_layers):
            if current.shape[0] < 2: break
            current = self._coarse_grain(current)
            self.scale_states.append(current.clone())

        # 2. Compute entanglement entropy at each scale
        ent_per_scale = []
        for l in range(len(self.scale_states)):
            s = self.scale_states[l]
            if s.shape[0] < 2: continue
            # Entanglement = variance of correlation between halves
            n = s.shape[0]
            half = n // 2
            left, right = s[:half], s[half:2 * half]
            if left.shape[0] != right.shape[0]: continue
            corr = (left * right).sum(dim=-1).mean()
            ent_per_scale.append(abs(corr.item()))
        self.entanglement_per_scale = ent_per_scale

        # 3. IR -> UV feedback (descending)
        # Top-down: coarser scales influence finer scales
        if len(self.scale_states) > 1:
            for l in range(len(self.scale_states) - 1, 0, -1):
                coarse = self.scale_states[l]
                fine = self.scale_states[l - 1]
                n_c, n_f = coarse.shape[0], fine.shape[0]
                # Each coarse cell influences 2 fine cells
                for i in range(min(n_c, n_f // 2)):
                    fine[2 * i] += self.dt * 0.2 * (coarse[i] - fine[2 * i])
                    if 2 * i + 1 < n_f:
                        fine[2 * i + 1] += self.dt * 0.2 * (coarse[i] - fine[2 * i + 1])
                self.scale_states[l - 1] = fine

        # 4. Update UV state from modified fine state
        self.uv_state = self.scale_states[0]

        # 5. Nearest-neighbor coupling at UV
        left = torch.roll(self.uv_state, 1, 0)
        right = torch.roll(self.uv_state, -1, 0)
        self.uv_state += self.dt * 0.1 * (left + right - 2 * self.uv_state)

        # 6. Noise
        self.uv_state += torch.randn_like(self.uv_state) * 0.008

    def observe(self):
        return self.uv_state.detach().clone()

    def inject(self, x):
        self.uv_state += x * 0.05


# ==============================================================
# XE-7: ANYONIC_BRAIDING
# Cells as non-abelian anyons (Fibonacci anyons).
# Braiding operations = unitary evolution on fusion space.
# Consciousness = topological entanglement entropy (TEE).
# Braids are topologically protected -- robust to local perturbation.
# ==============================================================

class AnyonicBraidingEngine:
    """Non-abelian anyons on a 1D chain.

    Each cell = anyon with a fusion charge (hidden_dim vector).
    Braiding: swap adjacent anyons via unitary R-matrix.
    Fusion: F-matrix determines how charges combine.
    Topological entanglement entropy (TEE): gamma = log(D)
    where D = total quantum dimension.

    For Fibonacci anyons: D = golden ratio phi = (1+sqrt(5))/2.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Anyon states (fusion space representation)
        self.state = torch.randn(n_cells, hidden_dim) * 0.5
        # Golden ratio (Fibonacci anyon quantum dimension)
        self.phi_golden = (1 + math.sqrt(5)) / 2
        self.D_total = self.phi_golden  # total quantum dimension

        # R-matrix: braiding phase (for Fibonacci anyons, R = e^{i*4pi/5})
        theta_R = 4 * math.pi / 5
        self.R_real = math.cos(theta_R)
        self.R_imag = math.sin(theta_R)

        # F-matrix (Fibonacci): [[phi^{-1}, phi^{-1/2}], [phi^{-1/2}, -phi^{-1}]]
        phi_inv = 1.0 / self.phi_golden
        phi_inv_half = 1.0 / math.sqrt(self.phi_golden)
        self.F = torch.tensor([[phi_inv, phi_inv_half],
                               [phi_inv_half, -phi_inv]])

        self.braid_count = 0
        self.tee_history = []  # topological entanglement entropy

    def _braid(self, i, j):
        """Braid anyons i and j. Apply R-matrix to their joint state."""
        # R-matrix action: rotate in the 2D fusion space
        si, sj = self.state[i].clone(), self.state[j].clone()
        # Apply R as a rotation in hidden_dim (generalized braiding)
        self.state[i] = self.R_real * si - self.R_imag * sj
        self.state[j] = self.R_imag * si + self.R_real * sj
        self.braid_count += 1

    def _fusion_transform(self, i, j, k):
        """Apply F-matrix to change fusion basis: (i,j),k -> i,(j,k)."""
        # Simplified: mix the three anyons according to F-matrix structure
        si = self.state[i].clone()
        sj = self.state[j].clone()
        sk = self.state[k].clone()
        # F-move
        self.state[i] = self.F[0, 0] * si + self.F[0, 1] * sj
        self.state[j] = self.F[1, 0] * si + self.F[1, 1] * sj
        # k gets residual coupling
        self.state[k] = sk + 0.05 * (si + sj)

    def step(self):
        # 1. Random braiding: swap random adjacent pairs
        n_braids = self.n_cells // 4
        indices = torch.randperm(self.n_cells - 1)[:n_braids]
        for idx in indices:
            i = idx.item()
            self._braid(i, i + 1)

        # 2. F-moves: change fusion basis for random triplets
        n_fusions = self.n_cells // 8
        for _ in range(n_fusions):
            i = torch.randint(0, self.n_cells - 2, (1,)).item()
            self._fusion_transform(i, i + 1, i + 2)

        # 3. Topological interaction: long-range braiding (non-abelian statistics)
        # Anyons that were braided develop non-local correlations
        for _ in range(self.n_cells // 16):
            i = torch.randint(0, self.n_cells, (1,)).item()
            j = (i + self.n_cells // 4 + torch.randint(-5, 6, (1,)).item()) % self.n_cells
            # Weak long-range braid
            si, sj = self.state[i].clone(), self.state[j].clone()
            self.state[i] += 0.02 * (self.R_real * sj - self.R_imag * si)
            self.state[j] += 0.02 * (self.R_imag * sj + self.R_real * si)

        # 4. Normalize (anyonic states have bounded norm)
        norms = self.state.norm(dim=-1, keepdim=True)
        mask = norms > 3.0
        if mask.any():
            self.state = torch.where(mask, self.state * 3.0 / (norms + 1e-8), self.state)

        # 5. Noise (thermal anyonic excitations)
        self.state += torch.randn_like(self.state) * 0.005

        # 6. Compute topological entanglement entropy (TEE)
        # TEE = -log(D) for a region, where D = total quantum dimension
        # Approximate: compute entanglement of left half vs right half,
        # subtract area law contribution
        half = self.n_cells // 2
        left = self.state[:half]
        right = self.state[half:]
        # Cross-correlation
        corr = torch.mm(left, right.T)
        # SVD to get entanglement spectrum
        try:
            sv = torch.linalg.svdvals(corr)
            sv = sv[sv > 1e-8]
            sv_norm = sv / sv.sum()
            ee = -(sv_norm * torch.log(sv_norm + 1e-10)).sum().item()
            # TEE = total EE - area law (boundary * constant)
            area_law = math.log(self.hidden_dim)  # proportional to boundary
            tee = max(0, ee - area_law)
        except:
            tee = 0.0
        self.tee_history.append(tee)

    def observe(self):
        return self.state.detach().clone()

    def inject(self, x):
        self.state += x * 0.03


# ==============================================================
# XE-8: CONSCIOUSNESS_FIELD
# Continuous scalar field theory phi(x).
# Cells sample the field at discrete points.
# Klein-Gordon equation with self-interaction (phi^4 theory).
# Consciousness = field correlation length (diverges at phase transition).
# Phase transition = consciousness onset.
# ==============================================================

class ConsciousnessFieldEngine:
    """Scalar field theory: phi(x, dim).

    Lagrangian: L = (1/2)(d_t phi)^2 - (1/2)(d_x phi)^2 - V(phi)
    V(phi) = (1/2) m^2 phi^2 + (lambda/4!) phi^4

    Phase transition: m^2 goes from positive (disordered) to negative
    (spontaneous symmetry breaking). At criticality: correlation length diverges.

    Consciousness = correlation length (how far information propagates).
    Start in disordered phase, slowly cool toward critical point.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Field value at each cell (lattice site)
        self.phi = torch.randn(n_cells, hidden_dim) * 0.3
        # Conjugate momentum (time derivative)
        self.pi = torch.randn(n_cells, hidden_dim) * 0.1
        # Mass squared: start positive (disordered), cool toward negative (ordered)
        self.m2 = 1.0  # will decrease over time
        self.m2_min = -0.5  # target (below critical = ordered phase)
        # Coupling constant (phi^4)
        self.lam = 0.5
        # Lattice spacing and time step
        self.a = 1.0
        self.dt = 0.02
        # Cooling rate
        self.cooling_rate = 0.005
        self.step_count = 0
        # Tracking
        self.correlation_length_history = []
        self.order_param_history = []
        self.m2_history = []

    def _laplacian(self, f):
        """1D lattice laplacian."""
        return (torch.roll(f, 1, 0) + torch.roll(f, -1, 0) - 2 * f) / (self.a ** 2)

    def _dV_dphi(self, phi):
        """Derivative of potential: dV/dphi = m^2 * phi + (lambda/6) * phi^3."""
        return self.m2 * phi + (self.lam / 6.0) * phi ** 3

    def _correlation_length(self):
        """Estimate correlation length from spatial correlations."""
        # C(r) = <phi(x) phi(x+r)> - <phi>^2
        phi_mean = self.phi.mean(dim=0)  # (hidden_dim,)
        phi_centered = self.phi - phi_mean
        # Compute correlations at different distances
        corrs = []
        max_r = min(32, self.n_cells // 4)
        c0 = (phi_centered * phi_centered).mean().item()
        if c0 < 1e-10: return 0.0
        for r in range(1, max_r):
            shifted = torch.roll(phi_centered, r, 0)
            cr = (phi_centered * shifted).mean().item() / (c0 + 1e-10)
            corrs.append(max(cr, 1e-10))
            if cr < 0.05: break  # correlation has decayed
        # Fit exponential decay: C(r) ~ exp(-r/xi)
        # xi = -1 / slope of log(C(r))
        if len(corrs) < 2: return 1.0
        log_corrs = [math.log(max(c, 1e-10)) for c in corrs]
        # Simple linear fit
        n = len(log_corrs)
        x_vals = list(range(1, n + 1))
        x_mean = sum(x_vals) / n
        y_mean = sum(log_corrs) / n
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, log_corrs))
        den = sum((x - x_mean) ** 2 for x in x_vals)
        if abs(den) < 1e-10: return 1.0
        slope = num / den
        if slope >= 0: return float(max_r)  # no decay = infinite correlation
        xi = -1.0 / slope
        return min(xi, float(self.n_cells))

    def step(self):
        self.step_count += 1

        # 1. Cool: slowly decrease m^2 toward critical point
        if self.m2 > self.m2_min:
            self.m2 -= self.cooling_rate
        self.m2_history.append(self.m2)

        # 2. Equations of motion (leapfrog integration)
        # pi_dot = laplacian(phi) - dV/dphi  (Klein-Gordon)
        lap = self._laplacian(self.phi)
        force = lap - self._dV_dphi(self.phi)

        # Half-step momentum
        self.pi += 0.5 * self.dt * force

        # Full-step field
        self.phi += self.dt * self.pi

        # Recompute force at new position
        lap = self._laplacian(self.phi)
        force = lap - self._dV_dphi(self.phi)

        # Half-step momentum again
        self.pi += 0.5 * self.dt * force

        # 3. Small dissipation (to reach equilibrium faster)
        self.pi *= 0.999

        # 4. Thermal noise (fluctuation-dissipation)
        temperature = max(0.01, 0.1 * (1.0 + self.m2))  # hotter in disordered phase
        self.pi += torch.randn_like(self.pi) * math.sqrt(2 * temperature * 0.001)

        # 5. Measure correlation length
        xi = self._correlation_length()
        self.correlation_length_history.append(xi)

        # 6. Order parameter: <phi> (should be ~0 in disordered, nonzero in ordered)
        order = self.phi.mean().abs().item()
        self.order_param_history.append(order)

    def observe(self):
        return self.phi.detach().clone()

    def inject(self, x):
        self.phi += x * 0.03


# ==============================================================
# Engine Registry & Runner
# ==============================================================

ALL_ENGINES = {
    '1': ('XE-1: HOLOGRAPHIC_UNIVERSE', HolographicUniverseEngine),
    '2': ('XE-2: TOPOLOGICAL_INSULATOR', TopologicalInsulatorEngine),
    '3': ('XE-3: TIME_CRYSTAL', TimeCrystalEngine),
    '4': ('XE-4: NEUROMORPHIC_SPIKE', NeuromorphicSpikeEngine),
    '5': ('XE-5: MEMBRANE_COMPUTING', MembraneComputingEngine),
    '6': ('XE-6: TENSOR_NETWORK', TensorNetworkEngine),
    '7': ('XE-7: ANYONIC_BRAIDING', AnyonicBraidingEngine),
    '8': ('XE-8: CONSCIOUSNESS_FIELD', ConsciousnessFieldEngine),
}


def run_engine(name, engine_cls, n_cells, steps):
    print(f"\n{'─' * 74}")
    print(f"  Running: {name} ({n_cells} cells, {steps} steps)")
    print(f"{'─' * 74}")
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
    if hasattr(engine, 'entanglement_entropy') and engine.entanglement_entropy:
        extra['final_holographic_EE'] = engine.entanglement_entropy[-1]
    if hasattr(engine, 'edge_amplitude_history') and engine.edge_amplitude_history:
        edge, bulk = engine.edge_amplitude_history[-1]
        extra['edge_amp'] = round(edge, 4)
        extra['bulk_amp'] = round(bulk, 4)
        extra['edge_bulk_ratio'] = round(edge / (bulk + 1e-8), 2)
        extra['winding_number'] = engine.winding_number
    if hasattr(engine, 'order_param_history') and engine.order_param_history:
        extra['TC_order_final'] = round(np.mean(engine.order_param_history[-20:]), 4)
    if hasattr(engine, 'synchrony_history') and engine.synchrony_history:
        extra['mean_synchrony'] = round(np.mean(engine.synchrony_history[-50:]), 4)
        if hasattr(engine, 'avalanche_sizes') and engine.avalanche_sizes:
            sizes = np.array(engine.avalanche_sizes)
            extra['mean_avalanche'] = round(float(sizes.mean()), 2)
            extra['max_avalanche'] = int(sizes.max())
    if hasattr(engine, 'membrane_complexity') and engine.membrane_complexity:
        extra['membrane_complexity'] = round(engine.membrane_complexity[-1], 3)
        extra['total_transports'] = sum(engine.transport_history)
    if hasattr(engine, 'entanglement_per_scale') and engine.entanglement_per_scale:
        extra['n_scales'] = len(engine.entanglement_per_scale)
        extra['max_scale_entanglement'] = round(max(engine.entanglement_per_scale), 4)
    if hasattr(engine, 'tee_history') and engine.tee_history:
        extra['final_TEE'] = round(engine.tee_history[-1], 4)
        extra['mean_TEE'] = round(np.mean(engine.tee_history[-50:]), 4)
        extra['total_braids'] = engine.braid_count
    if hasattr(engine, 'correlation_length_history') and engine.correlation_length_history:
        extra['correlation_length'] = round(engine.correlation_length_history[-1], 2)
        extra['max_corr_length'] = round(max(engine.correlation_length_history), 2)
        extra['final_m2'] = round(engine.m2, 4)
        if hasattr(engine, 'order_param_history'):
            extra['field_order_param'] = round(engine.order_param_history[-1], 4)

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
    parser = argparse.ArgumentParser(description='Extreme Consciousness Engines Benchmark')
    parser.add_argument('--only', nargs='+', default=None, help='Run only these engines (1-8)')
    parser.add_argument('--cells', type=int, default=256, help='Number of cells')
    parser.add_argument('--steps', type=int, default=300, help='Number of steps')
    args = parser.parse_args()

    print("=" * 74)
    print("  EXTREME CONSCIOUSNESS ENGINES BENCHMARK (XE-1 to XE-8)")
    print("  Radical physics: holography, topology, time crystals, anyons...")
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
    print("  FINAL RANKINGS (sorted by Phi(IIT))")
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
        print(f"  Phi(IIT) = {best.phi_iit:.3f}")
        if best.extra:
            print(f"  Details: {best.extra}")

    # Reference
    print(f"\n  REFERENCE (previous engines):")
    print(f"    quantum_walk     Phi = 69.53  (bench_emergent)")
    print(f"    laser            Phi = 18.17  (bench_physics)")
    print(f"    reaction_diffusion Phi ~ 5-15 (bench_emergent)")
    print(f"    baseline         Phi ~  1.00  (random linear)")

    print("\n" + "=" * 74)
    return results


if __name__ == '__main__':
    main()
