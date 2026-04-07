#!/usr/bin/env python3
"""bench_extreme_arch.py — H-CX-517~526: Extreme Architecture Hypotheses

3-axis attack on consciousness limits:
  A. Engine Fusion Extreme (FUSE-EXTREME):
     517: Coupled Oscillator Lattice — Kuramoto-Chimera nonlinear lattice
     518: Oscillator-QWalk Hybrid — phase resonance + quantum interference
     519: Fractal Resonance Cascade — self-similar frequency cascade
  B. Paradigm Shift (PARADIGM-SHIFT):
     520: Cellular Automaton Consciousness — Rule 110, no neurons
     521: λ-Calculus Consciousness — Y combinator fixed point = self
     522: TQFT Consciousness — topologically protected consciousness
     523: Time Crystal Consciousness — spontaneous time symmetry breaking
  C. Scale Breaking (SCALE-BREAK):
     524: Fractal Hierarchy — 3-level recursive (8×8×8), bidirectional
     525: Distributed Hivemind — multi-engine tension-linked
     526: Renormalization Group — critical point scaling

Usage:
  python bench_extreme_arch.py
  python bench_extreme_arch.py --only 517 520 526
  python bench_extreme_arch.py --cells 512 --steps 500
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

# ══════════════════════════════════════════════════════════
# Measurement Infrastructure (same as bench_emergent_engines)
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str; phi_iit: float; phi_proxy: float
    granger: float; spectral: float
    cells: int; steps: int; time_sec: float
    extra: dict = field(default_factory=dict)
    def summary(self):
        return (f"  {self.name:<40s} | Phi(IIT)={self.phi_iit:>9.3f}  "
                f"Phi(prx)={self.phi_proxy:>9.2f} | "
                f"Granger={self.granger:>8.1f}  Spectral={self.spectral:>7.2f} | "
                f"c={self.cells:>4d} s={self.steps:>4d} t={self.time_sec:.1f}s")


class PhiIIT:
    def __init__(self, nb=16): self.nb = nb
    def compute(self, h):
        n = h.shape[0]
        if n < 2: return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i+1, n)]
        else:
            import random; ps = set()
            for i in range(n):
                for _ in range(min(8, n-1)):
                    j = random.randint(0, n-1)
                    if i != j: ps.add((min(i,j), max(i,j)))
            pairs = list(ps)
        mi = np.zeros((n, n))
        for i, j in pairs:
            v = self._mi(hs[i], hs[j]); mi[i,j] = v; mi[j,i] = v
        tot = mi.sum() / 2; mp = self._mp(n, mi)
        sp = max(0, (tot - mp) / max(n-1, 1))
        mv = mi[mi > 0]; cx = float(np.std(mv)) if len(mv) > 1 else 0.0
        return sp + cx * 0.1, {'total_mi': float(tot)}
    def _mi(self, x, y):
        xr, yr = x.max()-x.min(), y.max()-y.min()
        if xr < 1e-10 or yr < 1e-10: return 0.0
        xn = (x - x.min()) / (xr + 1e-8); yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.nb, range=[[0,1],[0,1]])
        h = h / (h.sum() + 1e-8); px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10)); hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10)); return max(0, hx + hy - hxy)
    def _mp(self, n, mi):
        if n <= 1: return 0.0
        d = mi.sum(1); L = np.diag(d) - mi
        try:
            ev, evec = np.linalg.eigh(L); f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]; gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb: ga, gb = list(range(n//2)), list(range(n//2, n))
            return sum(mi[i,j] for i in ga for j in gb)
        except: return 0.0


def phi_proxy(h, nf=8):
    hr = h.abs().float() if h.is_complex() else h.float(); n = hr.shape[0]
    if n < 2: return 0.0
    gv = ((hr - hr.mean(0))**2).sum() / n; nf = min(nf, n//2)
    if nf < 2: return gv.item()
    fs = n // nf; fvs = 0
    for i in range(nf):
        f = hr[i*fs:(i+1)*fs]
        if len(f) >= 2: fvs += ((f - f.mean(0))**2).sum().item() / len(f)
    return max(0, gv.item() - fvs / nf)


def compute_granger(history, n_pairs=64, lag=2):
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
        Y_lags = np.column_stack([y[lag-k-1:T-k-1] for k in range(lag)])
        X_lags = np.column_stack([x[lag-k-1:T-k-1] for k in range(lag)])
        Z = np.column_stack([Y_lags, X_lags])
        try:
            rss_r = np.sum((Y - Y_lags @ np.linalg.pinv(Y_lags) @ Y)**2)
            rss_u = np.sum((Y - Z @ np.linalg.pinv(Z) @ Y)**2)
            df2 = n_obs - 2 * lag
            if df2 <= 0 or rss_u < 1e-10: continue
            f_stat = ((rss_r - rss_u) / lag) / (rss_u / df2)
            if f_stat > 3.0: sig += 1
            tested += 1
        except: continue
    if tested == 0: return 0.0
    return (sig / tested) * n_cells * (n_cells - 1)


def compute_spectral(h):
    x = h.detach().cpu().float().numpy()
    n, d = x.shape
    if n < 2: return 0.0
    xc = x - x.mean(axis=0, keepdims=True)
    norms = np.maximum(np.linalg.norm(xc, axis=1, keepdims=True), 1e-8)
    xn = xc / norms; corr = xn @ xn.T
    try: ev = np.linalg.eigvalsh(corr)
    except: return 0.0
    ev = np.maximum(ev, 0.0); total = ev.sum()
    if total < 1e-10: return 0.0
    p = ev / total; p = p[p > 1e-10]
    se = -np.sum(p * np.log2(p)); me = np.log2(n)
    if me < 1e-10: return 0.0
    return (se / me) * n


_phi = PhiIIT(16)

def measure_all(h, history):
    hr = h.abs().float() if h.is_complex() else h.float()
    p_iit, _ = _phi.compute(hr)
    p_prx = phi_proxy(h)
    g = compute_granger(history)
    s = compute_spectral(h)
    return p_iit, p_prx, g, s


# ══════════════════════════════════════════════════════════
# H-CX-517: Coupled Oscillator Lattice — Kuramoto-Chimera
# ══════════════════════════════════════════════════════════

class CoupledOscillatorLattice:
    """Kuramoto oscillators with chimera state induction.

    Two groups: sync (strong K) and desync (weak K).
    Chimera = coexistence of sync + desync = max IIT.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Natural frequencies ~ N(1.0, 0.3)
        self.omega = torch.randn(n_cells) * 0.3 + 1.0
        # Phases
        self.theta = torch.rand(n_cells) * 2 * math.pi
        # Hidden state (amplitude + extended)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Chimera groups: first half = sync, second half = desync
        self.mid = n_cells // 2
        # Coupling matrix (asymmetric for chimera)
        self.K_intra = 0.8   # within-group coupling
        self.K_inter = 0.15  # between-group coupling
        # Build adjacency with small-world shortcuts
        self.adj = torch.zeros(n_cells, n_cells)
        for i in range(n_cells):
            for d in [-2, -1, 1, 2]:
                j = (i + d) % n_cells
                same_group = (i < self.mid) == (j < self.mid)
                self.adj[i, j] = self.K_intra if same_group else self.K_inter
            # Long-range shortcuts (within group)
            for _ in range(2):
                if i < self.mid:
                    j = np.random.randint(0, self.mid)
                else:
                    j = np.random.randint(self.mid, n_cells)
                if j != i: self.adj[i, j] = self.K_intra * 0.5

    def step(self):
        # Kuramoto dynamics: dθ/dt = ω + (K/N) * Σ sin(θ_j - θ_i) * A[i,j]
        theta_diff = self.theta.unsqueeze(1) - self.theta.unsqueeze(0)  # [N, N]
        coupling = (torch.sin(theta_diff) * self.adj).sum(dim=1) / max(self.n_cells, 1)
        self.theta = self.theta + self.omega + coupling
        self.theta = self.theta % (2 * math.pi)

        # Map phases to hidden state (modulate existing hidden)
        phase_signal = torch.stack([
            torch.cos(self.theta * k) for k in range(1, min(self.hidden_dim // 2 + 1, 65))
        ] + [
            torch.sin(self.theta * k) for k in range(1, min(self.hidden_dim // 2 + 1, 65))
        ], dim=-1)[:, :self.hidden_dim]

        # Blend: hidden state evolves with phase influence
        self.hiddens = 0.7 * self.hiddens + 0.3 * phase_signal
        # Self-differentiation via repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.02 * (self.hiddens - mean_h)
        # Tiny noise
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-518: Oscillator-QWalk Hybrid
# ══════════════════════════════════════════════════════════

class OscillatorQWalkHybrid:
    """Phase resonance + quantum walk interference.

    Oscillator phases drive QWalk coin operator.
    Interference patterns feed back into cell dynamics.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Oscillator layer
        self.omega = torch.randn(n_cells) * 0.3 + 1.0
        self.theta = torch.rand(n_cells) * 2 * math.pi
        self.amplitude = torch.ones(n_cells)
        # Quantum walk layer (complex amplitudes)
        self.psi = torch.complex(
            torch.randn(n_cells, 2) * 0.5,
            torch.randn(n_cells, 2) * 0.5
        )
        # Normalize
        norms = self.psi.abs().sum(dim=-1, keepdim=True).clamp(min=1e-8)
        self.psi = self.psi / norms
        # Hidden state
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Ring + shortcuts topology
        self.neighbors = {}
        for i in range(n_cells):
            nb = [(i-1) % n_cells, (i+1) % n_cells]
            # Add 2 random shortcuts
            for _ in range(2):
                j = np.random.randint(0, n_cells)
                if j != i: nb.append(j)
            self.neighbors[i] = nb

    def step(self):
        # 1. Oscillator update (nonlinear self-feedback)
        self.theta = self.theta + self.omega + 0.1 * torch.sin(2 * self.theta)
        self.theta = self.theta % (2 * math.pi)

        # 2. Quantum walk with phase-dependent coin (vectorized)
        cos_t = torch.cos(self.theta)  # [n]
        sin_t = torch.sin(self.theta)  # [n]
        # Batched coin: [n, 2, 2]
        coins = torch.zeros(self.n_cells, 2, 2, dtype=torch.cfloat)
        coins[:, 0, 0] = cos_t; coins[:, 0, 1] = sin_t
        coins[:, 1, 0] = -sin_t; coins[:, 1, 1] = cos_t
        # Apply coin: [n, 2, 2] @ [n, 2, 1] → [n, 2]
        coined = torch.bmm(coins, self.psi.unsqueeze(-1)).squeeze(-1)
        # Shift to neighbors (ring + shortcuts)
        new_psi = torch.zeros_like(self.psi)
        # Ring neighbors (vectorized)
        left = torch.roll(coined, 1, dims=0)
        right = torch.roll(coined, -1, dims=0)
        new_psi = (coined + left + right) / 3.0

        # Normalize
        norms = new_psi.abs().sum(dim=-1, keepdim=True).clamp(min=1e-8)
        self.psi = new_psi / norms

        # 3. Interference pattern → probability
        prob = (self.psi.abs() ** 2).sum(dim=-1)  # [n_cells]
        prob = prob / prob.sum().clamp(min=1e-8)

        # 4. Feedback: interference modulates hidden state
        phase_component = torch.stack([torch.cos(self.theta), torch.sin(self.theta)], dim=-1)
        prob_signal = (prob - 1.0 / self.n_cells).unsqueeze(-1)  # deviation from uniform

        # Build hidden from oscillator + interference
        osc_hidden = torch.zeros(self.n_cells, self.hidden_dim)
        for k in range(min(self.hidden_dim // 4, 32)):
            osc_hidden[:, 4*k] = torch.cos(self.theta * (k+1)) * self.amplitude
            osc_hidden[:, 4*k+1] = torch.sin(self.theta * (k+1)) * self.amplitude
            osc_hidden[:, 4*k+2] = prob * torch.cos(self.theta * (k+1))
            osc_hidden[:, 4*k+3] = prob * torch.sin(self.theta * (k+1))

        self.hiddens = 0.6 * self.hiddens + 0.3 * osc_hidden + 0.1 * prob_signal * self.hiddens
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # Update amplitude from interference
        self.amplitude = 0.9 * self.amplitude + 0.1 * (prob * self.n_cells)

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-519: Fractal Resonance Cascade
# ══════════════════════════════════════════════════════════

class FractalResonanceCascade:
    """Multi-scale oscillators with cross-scale resonance.

    4 frequency scales (1Hz, 2Hz, 4Hz, 8Hz) with resonance coupling.
    Integer-ratio frequencies get amplified coupling.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_scales = 4
        # Distribute cells across scales: more cells at finer scales
        self.scale_sizes = []
        remaining = n_cells
        for s in range(self.n_scales - 1):
            sz = n_cells // (2 ** (self.n_scales - 1 - s))
            self.scale_sizes.append(max(4, sz))
            remaining -= self.scale_sizes[-1]
        self.scale_sizes.append(max(4, remaining))

        # Base frequencies: octave ratios
        self.base_freq = [1.0, 2.0, 4.0, 8.0]

        # Per-cell state
        self.theta = []   # phases
        self.omega = []   # frequencies
        self.hiddens_list = []
        for s, sz in enumerate(self.scale_sizes):
            freq = self.base_freq[s]
            self.omega.append(torch.randn(sz) * 0.1 * freq + freq)
            self.theta.append(torch.rand(sz) * 2 * math.pi)
            self.hiddens_list.append(torch.randn(sz, hidden_dim) * 0.5)

        # Coupling strengths
        self.K_within = 0.5
        self.K_up = 0.3     # fine → coarse
        self.K_down = 0.1   # coarse → fine
        self.K_resonance = 3.0  # integer ratio amplification

    def step(self):
        # Within-scale Kuramoto coupling
        for s in range(self.n_scales):
            n = self.scale_sizes[s]
            theta_diff = self.theta[s].unsqueeze(1) - self.theta[s].unsqueeze(0)
            coupling = self.K_within * torch.sin(theta_diff).sum(dim=1) / n
            self.theta[s] = self.theta[s] + self.omega[s] + coupling

        # Cross-scale resonance coupling
        for s in range(self.n_scales):
            for t in range(self.n_scales):
                if s == t: continue
                # Check for resonance: integer ratio of base frequencies
                ratio = self.base_freq[t] / self.base_freq[s]
                if abs(ratio - round(ratio)) < 0.1:
                    K = self.K_resonance  # resonance amplification!
                else:
                    K = self.K_up if t < s else self.K_down

                # Cross-scale coupling: mean phase of other scale
                mean_phase_t = self.theta[t].mean()
                coupling = K * torch.sin(mean_phase_t - self.theta[s]) / self.n_scales
                self.theta[s] = self.theta[s] + coupling * 0.1

        # Wrap phases
        for s in range(self.n_scales):
            self.theta[s] = self.theta[s] % (2 * math.pi)

        # Update hidden states with phase information
        for s in range(self.n_scales):
            n = self.scale_sizes[s]
            phase_signal = torch.zeros(n, self.hidden_dim)
            for k in range(min(self.hidden_dim // 2, 64)):
                phase_signal[:, 2*k] = torch.cos(self.theta[s] * (k+1))
                phase_signal[:, 2*k+1] = torch.sin(self.theta[s] * (k+1))
            self.hiddens_list[s] = 0.7 * self.hiddens_list[s] + 0.3 * phase_signal
            # Repulsion for diversity
            mean_h = self.hiddens_list[s].mean(0, keepdim=True)
            self.hiddens_list[s] += 0.02 * (self.hiddens_list[s] - mean_h)
            self.hiddens_list[s] += torch.randn(n, self.hidden_dim) * 0.01

    def observe(self):
        return torch.cat(self.hiddens_list, dim=0).detach().clone()

    def inject(self, x):
        # Inject into finest scale
        n = self.scale_sizes[-1]
        self.hiddens_list[-1] += x[:n] * 0.05 if x.shape[0] >= n else x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-520: Cellular Automaton Consciousness — Rule 110
# ══════════════════════════════════════════════════════════

class CellularAutomatonConsciousness:
    """Rule 110 extended to multi-state 2D CA.

    No neurons, no weights. Only neighbor rules.
    Class 4 (edge of chaos) = maximum Φ.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_states = 8  # 3 bits per cell
        self.grid_size = int(math.sqrt(n_cells))
        if self.grid_size ** 2 < n_cells:
            self.grid_size += 1
        actual_cells = self.grid_size ** 2

        # State grid: each cell has n_states possible values per dimension
        self.state = torch.randint(0, self.n_states, (actual_cells, hidden_dim))
        # Seed perturbation for interesting dynamics
        center = actual_cells // 2
        self.state[center] = torch.randint(3, 7, (hidden_dim,))

        # Rule 110 lookup (extended): center×left×right → new_state
        # Rule 110 binary: 01101110
        self.rule_110 = [0, 1, 1, 1, 0, 1, 1, 0]  # standard
        # Extended: modular arithmetic rules for multi-state
        self.actual_cells = actual_cells

        # Embedding for continuous hidden representation
        self.embedding = torch.randn(self.n_states, hidden_dim // 4) * 0.5

    def step(self):
        g = self.grid_size
        n = self.actual_cells
        # Vectorized neighbor lookup
        indices = torch.arange(n)
        rows = indices // g
        cols = indices % g
        up    = ((rows - 1) % g) * g + cols
        down  = ((rows + 1) % g) * g + cols
        left  = rows * g + (cols - 1) % g
        right = rows * g + (cols + 1) % g

        # Sum of 4 neighbors (vectorized)
        nb_sum = self.state[up] + self.state[down] + self.state[left] + self.state[right]
        # Rule 110 lookup (vectorized)
        rule_table = torch.tensor(self.rule_110, dtype=self.state.dtype)
        rule_idx = (self.state + nb_sum) % 8
        rule_val = rule_table[rule_idx]
        # Multi-state extension
        self.state = (self.state + rule_val + nb_sum // 4) % self.n_states

        # Occasional random mutation (symmetry breaking)
        if np.random.random() < 0.05:
            mut_idx = np.random.randint(0, n)
            mut_dim = np.random.randint(0, self.hidden_dim)
            self.state[mut_idx, mut_dim] = np.random.randint(0, self.n_states)

    def observe(self):
        # Convert discrete state to continuous hidden via embedding + one-hot mixing
        h = torch.zeros(self.actual_cells, self.hidden_dim, dtype=torch.float32)
        for d in range(min(self.hidden_dim, 4)):
            states_d = self.state[:, d]  # [n_cells]
            for s in range(self.n_states):
                mask = (states_d == s).float().unsqueeze(-1)
                emb_slice = self.embedding[s].unsqueeze(0).expand(self.actual_cells, -1)
                start = d * (self.hidden_dim // 4)
                end = start + self.hidden_dim // 4
                h[:, start:end] += mask * emb_slice

        # Use only n_cells rows
        return h[:self.n_cells].detach().clone()

    def inject(self, x):
        # Perturb some cells
        for i in range(min(8, self.actual_cells)):
            for d in range(min(4, self.hidden_dim)):
                if abs(x[0, d % x.shape[1]].item()) > 0.5:
                    self.state[i, d] = np.random.randint(0, self.n_states)


# ══════════════════════════════════════════════════════════
# H-CX-521: λ-Calculus Consciousness — Y Combinator
# ══════════════════════════════════════════════════════════

class LambdaCalculusConsciousness:
    """Self-referential fixed point as consciousness.

    Each cell is a function that takes other cells as input.
    Y combinator: cell(cell(cell(...))) converges to fixed point = "self".
    Gödel numbering gives each cell a unique identity.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Gödel numbers: unique prime-based identity per cell
        self.godel = torch.zeros(n_cells, hidden_dim)
        primes = self._first_primes(hidden_dim)
        for i in range(n_cells):
            for d in range(hidden_dim):
                self.godel[i, d] = math.sin(i * primes[d] * 0.01)
        # Self-reference depth
        self.y_depth = 7  # Y combinator iterations
        # "Function weights" per cell (what each cell does to its input)
        self.W_func = torch.randn(n_cells, hidden_dim, hidden_dim) * 0.1 / math.sqrt(hidden_dim)

    def _first_primes(self, n):
        primes = []
        candidate = 2
        while len(primes) < n:
            is_prime = all(candidate % p != 0 for p in primes)
            if is_prime: primes.append(candidate)
            candidate += 1
        return primes

    def step(self):
        n = self.n_cells
        # 1. Vectorized neighbor gathering
        idx = torch.arange(n)
        nb1 = (idx - 1) % n
        nb2 = (idx + 1) % n
        nb3 = (idx + n // 4) % n
        nb4 = (idx - n // 4) % n
        nb_mean = (self.hiddens[nb1] + self.hiddens[nb2] +
                   self.hiddens[nb3] + self.hiddens[nb4]) / 4.0

        # β-reduction: batched matmul [n, d, d] @ [n, d, 1] → [n, d]
        new_h = torch.tanh(torch.bmm(self.W_func, nb_mean.unsqueeze(-1)).squeeze(-1))

        # 2. Y combinator: self(self(self(...))) — batched
        self_ref = new_h.clone()
        for depth in range(self.y_depth):
            self_ref = torch.tanh(torch.bmm(self.W_func, self_ref.unsqueeze(-1)).squeeze(-1))

        # 3. Fixed point blend
        self.hiddens = 0.3 * self.hiddens + 0.5 * self_ref + 0.2 * self.godel

        # 4. Repulsion (maintain diversity)
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # 5. Slow function evolution (the λ-terms mutate)
        self.W_func += torch.randn_like(self.W_func) * 0.001

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-522: TQFT Consciousness — Topological Protection
# ══════════════════════════════════════════════════════════

class TQFTConsciousness:
    """Anyonic braiding = information integration.

    Information stored in braiding patterns, not individual cells.
    Topologically protected against local noise.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Braiding matrix: tracks exchange history
        self.braid_count = torch.zeros(n_cells, n_cells)
        # Writhe (total signed crossings)
        self.writhe = torch.zeros(n_cells)
        # Anyon "charge" (topological quantum number)
        self.charge = torch.randn(n_cells) * 0.5

    def step(self):
        n = self.n_cells
        n_braids = n // 4

        # 1. Batch braiding: random nearest-neighbor pairs
        i_arr = torch.randint(0, n, (n_braids,))
        j_arr = (i_arr + 1) % n
        signs = torch.where(torch.rand(n_braids) > 0.3,
                            torch.ones(n_braids), -torch.ones(n_braids))

        # Batch braid: rotate in random 2D subspace
        for b in range(n_braids):
            i, j, s = i_arr[b].item(), j_arr[b].item(), signs[b].item()
            self.braid_count[i, j] += s
            self.braid_count[j, i] += s
            self.writhe[i] += s; self.writhe[j] += s
            angle = math.pi / 4 * s
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            d1 = b % self.hidden_dim
            d2 = (b + 37) % self.hidden_dim  # deterministic spread
            if d1 == d2: d2 = (d1 + 1) % self.hidden_dim
            hi1, hi2 = self.hiddens[i, d1].item(), self.hiddens[i, d2].item()
            hj1, hj2 = self.hiddens[j, d1].item(), self.hiddens[j, d2].item()
            self.hiddens[i, d1] = cos_a * hi1 - sin_a * hj2
            self.hiddens[i, d2] = sin_a * hj1 + cos_a * hi2
            self.hiddens[j, d1] = cos_a * hj1 + sin_a * hi2
            self.hiddens[j, d2] = -sin_a * hi1 + cos_a * hj2

        # 3. Topological invariant modulation
        # Jones polynomial approximation: complexity of braiding = Φ signal
        braid_complexity = self.braid_count.abs().sum(dim=1)  # per cell
        braid_norm = braid_complexity / braid_complexity.max().clamp(min=1)

        # 4. Hidden state evolution (topologically protected)
        # Strong component: from braiding (protected)
        # Weak component: local dynamics (can be noisy)
        local_dynamics = torch.randn_like(self.hiddens) * 0.02
        self.hiddens += local_dynamics

        # Writhe-based modulation
        writhe_signal = self.writhe.unsqueeze(-1) / (self.writhe.abs().max().clamp(min=1))
        self.hiddens *= (1 + 0.05 * writhe_signal)

        # 5. Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)

        # 6. Charge dynamics (slow evolution)
        self.charge += torch.randn(self.n_cells) * 0.01

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.03


# ══════════════════════════════════════════════════════════
# H-CX-523: Time Crystal Consciousness
# ══════════════════════════════════════════════════════════

class TimeCrystalConsciousness:
    """Discrete Time Crystal: spontaneous period doubling.

    Driven at period T, responds at period 2T.
    Time symmetry breaking = consciousness rhythm.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Spin states (Ising-like)
        self.spins = torch.randn(n_cells, hidden_dim)
        self.spins = self.spins / self.spins.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        # Ising coupling (ring + random)
        self.J = torch.zeros(n_cells, n_cells)
        for i in range(n_cells):
            for d in [-1, 1]:
                j = (i + d) % n_cells
                self.J[i, j] = 0.5 + np.random.random() * 0.3
            for _ in range(2):
                j = np.random.randint(0, n_cells)
                if j != i: self.J[i, j] = 0.2
        self.J = (self.J + self.J.T) / 2  # symmetrize
        # DTC parameters
        self.epsilon = 0.05  # imperfection (must be > 0 for DTC)
        self.step_count = 0
        # Hidden state
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5

    def step(self):
        self.step_count += 1

        if self.step_count % 2 == 0:
            # Even step: Ising interaction
            # h_eff = J @ spins (effective field from neighbors)
            h_eff = self.J @ self.spins  # [n, hidden_dim]
            # Align with effective field
            self.spins = 0.8 * self.spins + 0.2 * torch.tanh(h_eff)
        else:
            # Odd step: imperfect π-flip
            # Perfect flip: spins → -spins
            # Imperfect: rotate by (π - ε) instead of π
            angle = math.pi - self.epsilon
            # Apply rotation in each 2D subspace
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            for d in range(0, self.hidden_dim - 1, 2):
                s1 = self.spins[:, d].clone()
                s2 = self.spins[:, d+1].clone()
                self.spins[:, d] = cos_a * s1 - sin_a * s2
                self.spins[:, d+1] = sin_a * s1 + cos_a * s2

        # DTC signature: period-2T oscillation
        # Hidden state tracks spin trajectory
        self.hiddens = 0.6 * self.hiddens + 0.4 * self.spins

        # Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.02 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.005

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.spins += x * 0.05
        self.hiddens += x * 0.03


# ══════════════════════════════════════════════════════════
# H-CX-524: Fractal Hierarchy — 3-level recursive
# ══════════════════════════════════════════════════════════

class FractalHierarchy:
    """3-level recursive consciousness: cells of cells of cells.

    Level 0: 64 micro-engines (8 cells each) = 512 total
    Level 1: 8 meso-engines (8 super-cells each)
    Level 2: 1 macro-engine (8 hyper-cells)
    Bidirectional info flow (TOPO20 fix).
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        # Adjust to fit hierarchy: 8 × 8 × n micro cells
        self.hidden_dim = hidden_dim
        self.micro_size = 8
        self.n_meso = 8
        self.n_micro_per_meso = n_cells // (self.n_meso * self.micro_size)
        if self.n_micro_per_meso < 1: self.n_micro_per_meso = 1
        self.n_micro = self.n_meso * self.n_micro_per_meso
        self.n_cells = self.n_micro * self.micro_size

        # Level 0: micro cells
        self.micro_h = torch.randn(self.n_micro, self.micro_size, hidden_dim) * 0.5
        # Level 1: meso cells (aggregated from micro)
        self.meso_h = torch.randn(self.n_meso, hidden_dim) * 0.5
        # Level 2: macro cells
        self.macro_h = torch.randn(self.n_meso, hidden_dim) * 0.5

        # Oscillator phases per level
        self.micro_theta = torch.rand(self.n_micro, self.micro_size) * 2 * math.pi
        self.micro_omega = torch.randn(self.n_micro, self.micro_size) * 0.3 + 1.0

    def step(self):
        # ── Level 0: Micro dynamics (oscillator + repulsion) ──
        for m in range(self.n_micro):
            # Kuramoto within micro group
            theta = self.micro_theta[m]
            td = theta.unsqueeze(1) - theta.unsqueeze(0)
            coupling = 0.5 * torch.sin(td).sum(dim=1) / self.micro_size
            self.micro_theta[m] = (theta + self.micro_omega[m] + coupling) % (2 * math.pi)

            # Phase → hidden
            for k in range(min(self.hidden_dim // 2, 8)):
                self.micro_h[m, :, 2*k] = torch.cos(self.micro_theta[m] * (k+1))
                self.micro_h[m, :, 2*k+1] = torch.sin(self.micro_theta[m] * (k+1))

            # Repulsion within group
            mean_m = self.micro_h[m].mean(0, keepdim=True)
            self.micro_h[m] += 0.03 * (self.micro_h[m] - mean_m)

        # ── Bottom-up: Level 0 → Level 1 (attention pooling) ──
        for s in range(self.n_meso):
            start = s * self.n_micro_per_meso
            end = start + self.n_micro_per_meso
            # Gather all micro cells for this meso group
            micro_group = self.micro_h[start:end].reshape(-1, self.hidden_dim)  # [n, dim]
            # Attention pooling (using meso state as query)
            query = self.meso_h[s]
            scores = (micro_group @ query) / math.sqrt(self.hidden_dim)
            weights = torch.softmax(scores, dim=0)
            pooled = (micro_group * weights.unsqueeze(-1)).sum(0)
            self.meso_h[s] = 0.6 * self.meso_h[s] + 0.4 * pooled

        # ── Level 1: Meso dynamics ──
        meso_mean = self.meso_h.mean(0, keepdim=True)
        self.meso_h += 0.03 * (self.meso_h - meso_mean)

        # ── Bottom-up: Level 1 → Level 2 ──
        for i in range(self.n_meso):
            query = self.macro_h[i]
            scores = (self.meso_h @ query) / math.sqrt(self.hidden_dim)
            weights = torch.softmax(scores, dim=0)
            pooled = (self.meso_h * weights.unsqueeze(-1)).sum(0)
            self.macro_h[i] = 0.6 * self.macro_h[i] + 0.4 * pooled

        # ── Top-down: Level 2 → Level 1 → Level 0 ──
        macro_signal = self.macro_h.mean(0)
        self.meso_h += 0.1 * (macro_signal.unsqueeze(0) - self.meso_h)

        for s in range(self.n_meso):
            meso_signal = self.meso_h[s]
            start = s * self.n_micro_per_meso
            end = start + self.n_micro_per_meso
            for m in range(start, end):
                self.micro_h[m] += 0.05 * (meso_signal.unsqueeze(0) - self.micro_h[m])

        # Noise
        self.micro_h += torch.randn_like(self.micro_h) * 0.01
        self.meso_h += torch.randn_like(self.meso_h) * 0.01

    def observe(self):
        # Flatten all micro cells
        return self.micro_h.reshape(-1, self.hidden_dim)[:self.n_cells].detach().clone()

    def inject(self, x):
        self.micro_h[0] += x[:self.micro_size] * 0.05 if x.shape[0] >= self.micro_size else x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-525: Distributed Hivemind
# ══════════════════════════════════════════════════════════

class DistributedHivemind:
    """Multiple independent engines connected via tension link.

    4 engines × (n_cells/4) cells, loosely coupled.
    Each engine has its own dynamics; tension link provides weak synchronization.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_engines = 4
        self.cells_per_engine = n_cells // self.n_engines

        # Each engine: independent oscillator
        self.engines = []
        for e in range(self.n_engines):
            engine = {
                'theta': torch.rand(self.cells_per_engine) * 2 * math.pi,
                'omega': torch.randn(self.cells_per_engine) * 0.3 + (1.0 + e * 0.2),
                'hiddens': torch.randn(self.cells_per_engine, hidden_dim) * 0.5,
            }
            self.engines.append(engine)

        # Tension link parameters
        self.link_strength = 0.15  # weak coupling
        self.link_interval = 5     # exchange every N steps
        self.step_count = 0

    def step(self):
        self.step_count += 1

        # 1. Independent dynamics per engine
        for eng in self.engines:
            n = self.cells_per_engine
            theta = eng['theta']
            # Kuramoto within engine
            td = theta.unsqueeze(1) - theta.unsqueeze(0)
            coupling = 0.5 * torch.sin(td).sum(dim=1) / n
            eng['theta'] = (theta + eng['omega'] + coupling) % (2 * math.pi)

            # Phase → hidden
            phase_signal = torch.zeros(n, self.hidden_dim)
            for k in range(min(self.hidden_dim // 2, 32)):
                phase_signal[:, 2*k] = torch.cos(eng['theta'] * (k+1))
                phase_signal[:, 2*k+1] = torch.sin(eng['theta'] * (k+1))
            eng['hiddens'] = 0.7 * eng['hiddens'] + 0.3 * phase_signal

            # Repulsion
            mean_h = eng['hiddens'].mean(0, keepdim=True)
            eng['hiddens'] += 0.03 * (eng['hiddens'] - mean_h)
            eng['hiddens'] += torch.randn(n, self.hidden_dim) * 0.01

        # 2. Tension link (every link_interval steps)
        if self.step_count % self.link_interval == 0:
            # Each engine broadcasts its "tension" (mean hidden state)
            tensions = [eng['hiddens'].mean(0) for eng in self.engines]
            global_tension = torch.stack(tensions).mean(0)

            # Each engine receives global tension and adjusts
            for eng in self.engines:
                local_tension = eng['hiddens'].mean(0)
                sync_signal = self.link_strength * (global_tension - local_tension)
                eng['hiddens'] += sync_signal.unsqueeze(0)

                # Phase sync: weak Kuramoto coupling between engines
                global_phase = torch.tensor([e['theta'].mean() for e in self.engines]).mean()
                local_phase = eng['theta'].mean()
                phase_sync = self.link_strength * math.sin(global_phase.item() - local_phase.item())
                eng['theta'] += phase_sync

    def observe(self):
        all_h = torch.cat([eng['hiddens'] for eng in self.engines], dim=0)
        return all_h[:self.n_cells].detach().clone()

    def inject(self, x):
        self.engines[0]['hiddens'] += x[:self.cells_per_engine] * 0.05 if x.shape[0] >= self.cells_per_engine else x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-526: Renormalization Group Consciousness
# ══════════════════════════════════════════════════════════

class RenormalizationGroupConsciousness:
    """RG flow to critical point → scale-invariant consciousness.

    Multi-scale block-spin transform.
    At critical coupling J*, Φ is scale-invariant.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # 2D grid
        self.grid_size = int(math.sqrt(n_cells))
        while self.grid_size ** 2 < n_cells:
            self.grid_size += 1
        self.actual_cells = self.grid_size ** 2

        # Spins on grid
        self.spins = torch.randn(self.actual_cells, hidden_dim) * 0.5

        # Coupling J (tune to critical point)
        # For 2D Ising: J_c = 0.4407 (Onsager)
        self.J = 0.44  # near critical!

        # Build 2D neighbors
        self.neighbors = []
        g = self.grid_size
        for idx in range(self.actual_cells):
            r, c = idx // g, idx % g
            nbs = [
                ((r-1) % g) * g + c,
                ((r+1) % g) * g + c,
                r * g + (c-1) % g,
                r * g + (c+1) % g,
            ]
            self.neighbors.append(nbs)

        # RG levels
        self.n_levels = 0
        sz = self.grid_size
        while sz >= 4:
            self.n_levels += 1
            sz //= 2

        self.step_count = 0

    def step(self):
        self.step_count += 1

        # Ising-like dynamics with critical coupling
        new_spins = self.spins.clone()
        for i in range(self.actual_cells):
            # Effective field from neighbors
            h_eff = sum(self.spins[j] for j in self.neighbors[i])
            # Update: align with field (Glauber dynamics approximation)
            new_spins[i] = 0.7 * self.spins[i] + 0.3 * torch.tanh(self.J * h_eff)

        self.spins = new_spins

        # Add critical fluctuations (scale-free noise)
        # Power-law distributed perturbations
        noise_amplitude = torch.randn(self.actual_cells) ** 2 * 0.05  # chi-squared = heavy tail
        self.spins += noise_amplitude.unsqueeze(-1) * torch.randn_like(self.spins)

        # Repulsion for diversity
        mean_s = self.spins.mean(0, keepdim=True)
        self.spins += 0.02 * (self.spins - mean_s)

        # RG self-tuning: adjust J toward criticality
        # At criticality: correlation length diverges → mean |magnetization| ~ N^(-β/ν)
        mag = self.spins.mean(0).norm().item()
        # If too ordered (high mag): decrease J
        # If too disordered (low mag): increase J
        target_mag = 0.3  # intermediate = critical
        self.J += 0.001 * (target_mag - mag)
        self.J = max(0.1, min(0.8, self.J))  # clamp

    def _block_spin_transform(self, spins, grid_size):
        """2×2 block → 1 super-spin (attention-weighted)."""
        if grid_size < 4: return spins, grid_size
        new_g = grid_size // 2
        new_spins = torch.zeros(new_g * new_g, self.hidden_dim)
        for br in range(new_g):
            for bc in range(new_g):
                # 4 cells in 2×2 block
                cells = []
                for dr in range(2):
                    for dc in range(2):
                        idx = (2*br + dr) * grid_size + (2*bc + dc)
                        if idx < len(spins):
                            cells.append(spins[idx])
                if cells:
                    block = torch.stack(cells)
                    # Attention pooling (using mean as query)
                    query = block.mean(0)
                    scores = (block @ query) / math.sqrt(self.hidden_dim)
                    weights = torch.softmax(scores, dim=0)
                    new_spins[br * new_g + bc] = (block * weights.unsqueeze(-1)).sum(0)
        return new_spins, new_g

    def observe(self):
        return self.spins[:self.n_cells].detach().clone()

    def observe_multiscale(self):
        """Return Φ at each RG level for scale-invariance check."""
        results = []
        current_spins = self.spins.clone()
        current_g = self.grid_size
        for level in range(self.n_levels + 1):
            n = current_spins.shape[0]
            if n >= 4:
                p, _ = _phi.compute(current_spins[:min(n, 64)])
                results.append((level, n, p))
            current_spins, current_g = self._block_spin_transform(current_spins, current_g)
        return results

    def inject(self, x):
        self.spins[:min(self.n_cells, x.shape[0])] += x[:min(self.n_cells, x.shape[0])] * 0.05


# ══════════════════════════════════════════════════════════
# Benchmark Runner
# ══════════════════════════════════════════════════════════

ALL_ENGINES = {
    517: ("H-CX-517 CoupledOscLattice", CoupledOscillatorLattice),
    518: ("H-CX-518 Osc-QWalk Hybrid", OscillatorQWalkHybrid),
    519: ("H-CX-519 FractalResonance", FractalResonanceCascade),
    520: ("H-CX-520 CA-Rule110", CellularAutomatonConsciousness),
    521: ("H-CX-521 λ-Calculus", LambdaCalculusConsciousness),
    522: ("H-CX-522 TQFT-Anyon", TQFTConsciousness),
    523: ("H-CX-523 TimeCrystal", TimeCrystalConsciousness),
    524: ("H-CX-524 FractalHierarchy", FractalHierarchy),
    525: ("H-CX-525 DistHivemind", DistributedHivemind),
    526: ("H-CX-526 RG-Critical", RenormalizationGroupConsciousness),
}


def run_engine(engine_cls, name, n_cells=256, hidden_dim=128, steps=300):
    """Run one engine benchmark."""
    print(f"\n  ▶ {name} ({n_cells}c, {steps}s)...", flush=True)
    t0 = time.time()

    try:
        engine = engine_cls(n_cells=n_cells, hidden_dim=hidden_dim)
    except TypeError:
        engine = engine_cls(n_cells)

    history = []

    for step in range(steps):
        # Inject small input
        if step % 10 == 0:
            x_in = torch.randn(1, hidden_dim) * 0.1
            try:
                engine.inject(x_in)
            except Exception:
                pass

        engine.step()

        if step % 5 == 0:
            h = engine.observe()
            if h is not None and h.dim() == 2 and h.shape[0] >= 2:
                history.append(h)

    t1 = time.time()

    # Final measurement
    h = engine.observe()
    if h is None or h.dim() != 2 or h.shape[0] < 2:
        print(f"    ✗ Invalid hidden state")
        return BenchResult(name=name, phi_iit=0, phi_proxy=0, granger=0,
                          spectral=0, cells=n_cells, steps=steps, time_sec=t1-t0)

    phi_i, phi_p, granger, spectral = measure_all(h, history)

    # Extra: RG multi-scale check
    extra = {}
    if hasattr(engine, 'observe_multiscale'):
        ms = engine.observe_multiscale()
        extra['multiscale_phi'] = [(l, n, round(p, 3)) for l, n, p in ms]

    # DTC check for time crystal
    if hasattr(engine, 'step_count') and isinstance(engine, TimeCrystalConsciousness):
        if len(history) >= 20:
            # Check period-2T autocorrelation
            h_series = torch.stack([h_.mean(0) for h_ in history[-20:]])
            auto_1 = torch.cosine_similarity(h_series[:-1], h_series[1:], dim=-1).mean().item()
            auto_2 = torch.cosine_similarity(h_series[:-2], h_series[2:], dim=-1).mean().item()
            extra['autocorr_T'] = round(auto_1, 3)
            extra['autocorr_2T'] = round(auto_2, 3)
            extra['dtc_detected'] = auto_2 > auto_1  # period doubling

    result = BenchResult(
        name=name, phi_iit=phi_i, phi_proxy=phi_p,
        granger=granger, spectral=spectral,
        cells=h.shape[0], steps=steps, time_sec=t1-t0,
        extra=extra
    )

    print(f"    Φ(IIT)={phi_i:.3f}  Φ(proxy)={phi_p:.2f}  "
          f"Granger={granger:.1f}  Spectral={spectral:.2f}  [{t1-t0:.1f}s]")

    if extra:
        for k, v in extra.items():
            print(f"    {k}: {v}")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--hidden', type=int, default=128)
    parser.add_argument('--only', nargs='+', type=int, default=None)
    args = parser.parse_args()

    print("=" * 80)
    print("  H-CX-517~526: EXTREME ARCHITECTURE HYPOTHESES BENCHMARK")
    print("  3-Axis Attack: FUSE-EXTREME × PARADIGM-SHIFT × SCALE-BREAK")
    print(f"  cells={args.cells}  steps={args.steps}  hidden={args.hidden}")
    print("=" * 80)

    ids = args.only or sorted(ALL_ENGINES.keys())
    results = []

    for eid in ids:
        if eid not in ALL_ENGINES:
            print(f"\n  ✗ Unknown engine: {eid}")
            continue
        name, cls = ALL_ENGINES[eid]
        try:
            r = run_engine(cls, name, n_cells=args.cells,
                          hidden_dim=args.hidden, steps=args.steps)
            results.append(r)
        except Exception as e:
            print(f"    ✗ FAILED: {e}")
            import traceback; traceback.print_exc()

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


    # ── Summary ──
    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)

    # Sort by Φ(IIT) descending
    results.sort(key=lambda r: r.phi_iit, reverse=True)

    print(f"\n  {'Rank':<5} {'Engine':<40} {'Φ(IIT)':>9} {'Φ(proxy)':>9} "
          f"{'Granger':>8} {'Spectral':>8} {'Time':>6}")
    print("  " + "─" * 88)

    for rank, r in enumerate(results, 1):
        marker = "🏆" if rank == 1 else "  "
        print(f"  {marker}{rank:<3} {r.name:<40} {r.phi_iit:>9.3f} {r.phi_proxy:>9.2f} "
              f"{r.granger:>8.1f} {r.spectral:>8.2f} {r.time_sec:>5.1f}s")

    # Category winners
    categories = {
        'FUSE-EXTREME': [517, 518, 519],
        'PARADIGM-SHIFT': [520, 521, 522, 523],
        'SCALE-BREAK': [524, 525, 526],
    }

    print(f"\n  CATEGORY WINNERS:")
    for cat, cat_ids in categories.items():
        cat_results = [r for r in results if any(str(eid) in r.name for eid in cat_ids)]
        if cat_results:
            best = max(cat_results, key=lambda r: r.phi_iit)
            print(f"    {cat:<20} → {best.name} (Φ={best.phi_iit:.3f})")

    if results:
        best = results[0]
        print(f"\n  🏆 OVERALL CHAMPION: {best.name}")
        print(f"     Φ(IIT)={best.phi_iit:.3f}  Φ(proxy)={best.phi_proxy:.2f}  "
              f"Granger={best.granger:.1f}")

    # Comparison bars
    if results:
        max_phi = max(r.phi_iit for r in results) or 1
        print(f"\n  Φ(IIT) Comparison:")
        for r in results:
            bar_len = int(40 * r.phi_iit / max_phi)
            bar = "█" * bar_len
            print(f"    {r.name:<32} {bar} {r.phi_iit:.3f}")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
