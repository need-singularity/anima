#!/usr/bin/env python3
"""bench_v8_undiscovered.py — 30+ Undiscovered Domain Consciousness Architectures

Explores ALL undiscovered domains to beat the ALL-TIME Φ(IIT) record.
Each architecture: 512 cells, 300 steps, Phi(IIT) + Phi(proxy) + CE.

Domains: Algebraic Topology, Thermodynamics, Game Theory, Information Geometry,
         Spin Glass, Hyperbolic Geometry, Autopoiesis, Chimera States,
         Free Energy Principle, Edge of Chaos, Reservoir Computing,
         Swarm Intelligence, Morphogenesis, Criticality, Neural Darwinism,
         Predictive Coding, Stigmergy, Reaction-Diffusion, Cellular Automata,
         Holographic, Synfire Chain, Avalanche, Stochastic Resonance,
         Topological Insulator, Renormalization Group + Combos

Usage:
  python bench_v8_undiscovered.py                    # Run all 30+ + combos
  python bench_v8_undiscovered.py --only 1 4 8       # Run specific (1-30)
  python bench_v8_undiscovered.py --steps 500        # Custom steps
  python bench_v8_undiscovered.py --cells 512        # Custom cell count
  python bench_v8_undiscovered.py --no-combos        # Skip combo search
  python bench_v8_undiscovered.py --combos-only      # Only combos
"""

import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import math
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ──────────────────────────────────────────────────────────
# BenchResult
# ──────────────────────────────────────────────────────────

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy: float
    ce_start: float
    ce_end: float
    cells: int
    steps: int
    time_sec: float
    extra: dict = field(default_factory=dict)

    def summary(self) -> str:
        ce_str = f"CE {self.ce_start:.3f}->{self.ce_end:.3f}" if self.ce_start > 0 else "CE n/a"
        return (
            f"  {self.name:<34s} | "
            f"Phi(IIT)={self.phi_iit:>7.3f}  "
            f"Phi(proxy)={self.phi_proxy:>8.2f} | "
            f"{ce_str:<22s} | "
            f"cells={self.cells:>4d}  steps={self.steps:>5d}  "
            f"time={self.time_sec:.1f}s"
        )


# ──────────────────────────────────────────────────────────
# Phi(IIT) Calculator
# ──────────────────────────────────────────────────────────

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
        if n <= 8:
            mc = float('inf')
            for mask in range(1, 2 ** n - 1):
                ga = [i for i in range(n) if mask & (1 << i)]
                gb = [i for i in range(n) if not (mask & (1 << i))]
                if ga and gb:
                    mc = min(mc, sum(mi[i, j] for i in ga for j in gb))
            return mc if mc != float('inf') else 0.0
        else:
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
            except:
                return 0.0


def phi_proxy(hiddens, n_factions=8):
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


_phi = PhiIIT(16)


def measure_phi(hiddens, nf=8):
    hr = hiddens.abs().float() if hiddens.is_complex() else hiddens.float()
    p_iit, _ = _phi.compute(hr)
    p_proxy = phi_proxy(hiddens, nf)
    return p_iit, p_proxy


# ──────────────────────────────────────────────────────────
# Shared components
# ──────────────────────────────────────────────────────────

class BenchMind(nn.Module):
    def __init__(self, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.engine_a = nn.Sequential(nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(), nn.Linear(128, output_dim))
        self.engine_g = nn.Sequential(nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(), nn.Linear(128, output_dim))
        self.memory = nn.GRUCell(output_dim + 1, hidden_dim)
        self.hidden_dim = hidden_dim
        with torch.no_grad():
            for p in self.engine_a.parameters(): p.add_(torch.randn_like(p) * 0.3)
            for p in self.engine_g.parameters(): p.add_(torch.randn_like(p) * -0.3)

    def forward(self, x, hidden):
        c = torch.cat([x, hidden], -1)
        a, g = self.engine_a(c), self.engine_g(c)
        out = a - g
        t = (out ** 2).mean(-1, keepdim=True)
        new_h = self.memory(torch.cat([out.detach(), t.detach()], -1), hidden)
        return out, t.mean().item(), new_h


def faction_sync(hiddens, nf=8, sync=0.15, debate=0.15, step=0):
    n = hiddens.shape[0]
    nf = min(nf, n // 2)
    if nf < 2:
        return hiddens
    fs = n // nf
    h = hiddens.clone()
    for i in range(nf):
        s, e = i * fs, (i + 1) * fs
        fm = h[s:e].mean(0)
        h[s:e] = (1 - sync) * h[s:e] + sync * fm
    if step > 5:
        ops = torch.stack([h[i * fs:(i + 1) * fs].mean(0) for i in range(nf)])
        go = ops.mean(0)
        for i in range(nf):
            s = i * fs
            dc = max(1, fs // 4)
            h[s:s + dc] = (1 - debate) * h[s:s + dc] + debate * go
    return h


def gen_batch(dim, bs=1):
    x = torch.randn(bs, dim)
    t = torch.roll(x, 1, -1) * 0.8 + torch.randn_like(x) * 0.1
    return x, t


# ──────────────────────────────────────────────────────────
# Generic runner: takes an engine with process/get_hiddens/trainable_parameters
# ──────────────────────────────────────────────────────────

def run_engine(name, engine, n_cells, steps, input_dim=64, extra_fn=None):
    """Generic training loop for any engine."""
    t0 = time.time()
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)
    ce_hist = []

    for step in range(steps):
        x, target = gen_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()
        ce_hist.append(loss.item())
        if step % 60 == 0 or step == steps - 1:
            pi, pp = measure_phi(engine.get_hiddens())
            extra_str = ""
            if extra_fn:
                extra_str = extra_fn(engine)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Φ(IIT)={pi:.3f}  Φ(prx)={pp:.2f}  {extra_str}")

    elapsed = time.time() - t0
    pi, pp = measure_phi(engine.get_hiddens())
    return BenchResult(name, pi, pp, ce_hist[0], ce_hist[-1], n_cells, steps, elapsed)


# ──────────────────────────────────────────────────────────
# Base engine class (all 30+ architectures inherit from this)
# ──────────────────────────────────────────────────────────

class BaseEngine(nn.Module):
    def __init__(self, n_cells, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def architecture_update(self, step):
        """Override in subclass. Must only modify self.hiddens (already detached)."""
        pass

    def process(self, x, step=0):
        outputs, tensions, new_h = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, t, nh = self.mind(x, h)
            outputs.append(out)
            tensions.append(t)
            new_h.append(nh.squeeze(0))
        self.hiddens = torch.stack(new_h).detach()  # DETACH before any update
        self.architecture_update(step)
        self.hiddens = faction_sync(self.hiddens, step=step)
        w = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(wi.item() * o for wi, o in zip(w, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.parameters())


# ══════════════════════════════════════════════════════════
# U1: PERSISTENT_HOMOLOGY — Simplicial complex, Betti loops
# ══════════════════════════════════════════════════════════
class U1_HomologyEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.triangles = []
        for i in range(nc):
            j1, j2 = (i + 1) % nc, (i + int(nc ** 0.5)) % nc
            self.triangles.append((i, j1, j2))
        self.sw = 0.25  # simplex weight

    def architecture_update(self, step):
        h = self.hiddens
        for (a, b, c) in self.triangles[:self.n_cells]:
            tm = (h[a] + h[b] + h[c]) / 3
            h[a] = (1 - self.sw) * h[a] + self.sw * tm
            h[b] = (1 - self.sw) * h[b] + self.sw * tm
            h[c] = (1 - self.sw) * h[c] + self.sw * tm


# ══════════════════════════════════════════════════════════
# U2: DISSIPATIVE_STRUCTURE — Prigogine entropy production
# ══════════════════════════════════════════════════════════
class U2_DissipativeEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.energy = torch.ones(nc) * 0.5

    def architecture_update(self, step):
        self.energy += 0.3 * (1 + 0.5 * math.sin(step * 0.1))
        h = self.hiddens
        high_e = self.energy > self.energy.mean()
        for i in range(0, self.n_cells, 2):
            if high_e[i]:
                j = (i + 1) % self.n_cells
                h[i] = h[i] + 0.1 * (h[i] - h[j])
                self.energy[i] *= 0.95
        h += torch.randn_like(h) * 0.015


# ══════════════════════════════════════════════════════════
# U3: GAME_THEORY — IPD cooperation edge
# ══════════════════════════════════════════════════════════
class U3_GameEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.coop = torch.rand(nc) * 0.5 + 0.25

    def architecture_update(self, step):
        actions = (torch.rand(self.n_cells) < self.coop).float()
        h = self.hiddens
        for i in range(0, self.n_cells, 2):
            j = (i + 1) % self.n_cells
            if actions[i] == 1:
                h[i] = h[i] + 0.1 * h[j]  # cooperate = share
            else:
                h[i] = h[i] - 0.05 * h[j]  # defect = diverge


# ══════════════════════════════════════════════════════════
# U4: INFO_GEOMETRY — Fisher metric, natural gradient
# ══════════════════════════════════════════════════════════
class U4_InfoGeoEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.cell_var = torch.ones(nc, self.hidden_dim) * 0.5

    def architecture_update(self, step):
        h = self.hiddens
        # Update variance estimate
        self.cell_var = 0.95 * self.cell_var + 0.05 * (h ** 2)
        # Natural gradient sync: Fisher-weighted direction
        for i in range(0, self.n_cells, 4):
            j = (i + 1) % self.n_cells
            direction = (h[j] - h[i]) / (self.cell_var[i] + 0.01)
            h[i] = h[i] + 0.03 * direction


# ══════════════════════════════════════════════════════════
# U5: SPIN_GLASS — SK model, frustration ~33%
# ══════════════════════════════════════════════════════════
class U5_SpinGlassEngine(BaseEngine):
    def __init__(self, nc, frust=0.33, **kw):
        super().__init__(nc, **kw)
        self.J = {}  # coupling signs
        for i in range(nc):
            for k in [1, 2, 3, int(nc ** 0.5)]:
                j = (i + k) % nc
                self.J[(i, j)] = -1.0 if torch.rand(1).item() < frust else 1.0

    def architecture_update(self, step):
        h = self.hiddens
        for i in range(0, self.n_cells, 4):
            field = torch.zeros(self.hidden_dim)
            cnt = 0
            for (a, b), J in self.J.items():
                if a == i:
                    field += J * h[b]
                    cnt += 1
            if cnt > 0:
                field /= cnt
                h[i] = h[i] + 0.05 * (field - h[i])


# ══════════════════════════════════════════════════════════
# U6: HYPERBOLIC — Poincaré disk embedding
# ══════════════════════════════════════════════════════════
class U6_HyperbolicEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.coords = torch.zeros(nc, 2)
        for i in range(nc):
            depth = math.log2(i + 1)
            angle = (i * 2.399) % (2 * math.pi)
            r = min(1 - 1.0 / (depth + 1), 0.95)
            self.coords[i] = torch.tensor([r * math.cos(angle), r * math.sin(angle)])

    def architecture_update(self, step):
        h = self.hiddens
        for i in range(0, self.n_cells, 4):
            j = (i + 1) % self.n_cells
            d = ((self.coords[i] - self.coords[j]) ** 2).sum().sqrt().item()
            s = min(0.3, 1.0 / (d + 0.5))
            h[i] = (1 - s) * h[i] + s * h[j]


# ══════════════════════════════════════════════════════════
# U7: AUTOPOIESIS — Self-producing membrane
# ══════════════════════════════════════════════════════════
class U7_AutopoiesisEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.membrane = torch.ones(nc) * 0.8
        self.prod_w = nn.Linear(self.hidden_dim, 1)

    def architecture_update(self, step):
        h = self.hiddens
        self.membrane *= 0.98  # decay
        prod = torch.sigmoid(self.prod_w(h.detach())).squeeze(-1)
        self.membrane = torch.clamp(self.membrane + 0.1 * prod.detach(), 0, 2)
        for i in range(0, self.n_cells, 2):
            j = (i + 1) % self.n_cells
            leak = max(0, 1.0 - self.membrane[i].item()) * 0.15
            h[i] = (1 - leak) * h[i] + leak * h[j]


# ══════════════════════════════════════════════════════════
# U8: CHIMERA_STATE — Kuramoto sync+async coexistence
# ══════════════════════════════════════════════════════════
class U8_ChimeraEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.omega = torch.randn(nc) * 0.5
        self.phases = torch.rand(nc) * 2 * math.pi
        self.K_s, self.K_w = 3.0, 0.2

    def architecture_update(self, step):
        half = self.n_cells // 2
        dt = 0.1
        new_ph = self.phases.clone()
        for i in range(0, self.n_cells, 8):
            cs = 0.0
            for j in range(0, self.n_cells, 8):
                K = self.K_s if ((i < half) == (j < half)) else self.K_w
                cs += K * math.sin(self.phases[j].item() - self.phases[i].item())
            cs /= max(self.n_cells // 8, 1)
            new_ph[i] = self.phases[i] + dt * (self.omega[i] + cs)
        self.phases = new_ph % (2 * math.pi)
        pf = torch.cos(self.phases).unsqueeze(1)
        self.hiddens = self.hiddens * (1 + 0.3 * pf)


# ══════════════════════════════════════════════════════════
# U9: FREE_ENERGY — Friston active inference
# ══════════════════════════════════════════════════════════
class U9_FreeEnergyEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.predictor = nn.Linear(self.hidden_dim, self.hidden_dim)
        self.n_levels = 4
        self.cpl = nc // 4

    def architecture_update(self, step):
        h = self.hiddens
        for lv in range(self.n_levels - 1):
            s1 = lv * self.cpl
            s2 = (lv + 1) * self.cpl
            lower_m = h[s1:s1 + self.cpl].mean(0)
            upper_m = h[s2:s2 + self.cpl].mean(0)
            pred = self.predictor(lower_m.unsqueeze(0)).squeeze(0).detach()
            err = pred - upper_m
            h[s2:s2 + self.cpl] = h[s2:s2 + self.cpl] + 0.05 * err.unsqueeze(0)


# ══════════════════════════════════════════════════════════
# U10: EDGE_OF_CHAOS — Lyapunov λ≈0 control
# ══════════════════════════════════════════════════════════
class U10_EdgeChaosEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.coupling = 0.5
        self.prev_h = self.hiddens.clone()
        self.lyap = 0.0

    def architecture_update(self, step):
        h = self.hiddens
        c = min(max(self.coupling, 0.01), 0.99)
        for i in range(0, self.n_cells, 4):
            j = (i + 1) % self.n_cells
            h[i] = h[i] + 0.1 * c * h[j] * (1 - h[i].abs() / 5.0)
        # Lyapunov
        diff = (h - self.prev_h).norm(dim=1).clamp(min=1e-8)
        pd = self.prev_h.norm(dim=1).clamp(min=1e-8)
        self.lyap = 0.9 * self.lyap + 0.1 * (diff / pd).clamp(min=1e-8).log().mean().item()
        if self.lyap > 0.05:
            self.coupling -= 0.01
        elif self.lyap < -0.05:
            self.coupling += 0.01
        self.prev_h = h.clone()


# ══════════════════════════════════════════════════════════
# U11: RESERVOIR_COMPUTING — Echo state network dynamics
# ══════════════════════════════════════════════════════════
class U11_ReservoirEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        # Sparse random reservoir connections (spectral radius ~0.95)
        W = torch.randn(nc, nc) * 0.1
        mask = (torch.rand(nc, nc) < 6.0 / nc)  # sparse
        W = W * mask.float()
        # Scale to spectral radius 0.95
        try:
            sr = torch.linalg.eigvals(W).abs().max().item()
            if sr > 0:
                W = W * (0.95 / sr)
        except:
            W = W * 0.01
        self.W_res = W

    def architecture_update(self, step):
        h = self.hiddens
        # Reservoir dynamics: h = tanh(W_res @ h_mean + noise)
        h_mean = h.mean(dim=1)  # [n_cells] - mean across hidden dims
        # Project to per-cell scalar, then broadcast
        reservoir_input = self.W_res @ h_mean  # [n_cells]
        modulation = torch.tanh(reservoir_input * 0.1).unsqueeze(1)  # [n_cells, 1]
        self.hiddens = h + 0.15 * modulation * h


# ══════════════════════════════════════════════════════════
# U12: SWARM_INTELLIGENCE — Particle swarm optimization dynamics
# ══════════════════════════════════════════════════════════
class U12_SwarmEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.velocity = torch.zeros(nc, self.hidden_dim)
        self.personal_best = self.hiddens.clone()
        self.personal_best_score = torch.zeros(nc) - float('inf')
        self.global_best = torch.zeros(self.hidden_dim)
        self.global_best_score = -float('inf')

    def architecture_update(self, step):
        h = self.hiddens
        # Evaluate fitness: diversity from mean (encourage differentiation)
        mean_h = h.mean(0)
        scores = ((h - mean_h) ** 2).sum(dim=1)  # [n_cells]

        # Update personal best
        improved = scores > self.personal_best_score
        self.personal_best[improved] = h[improved].clone()
        self.personal_best_score[improved] = scores[improved]

        # Update global best
        best_idx = scores.argmax()
        if scores[best_idx] > self.global_best_score:
            self.global_best = h[best_idx].clone()
            self.global_best_score = scores[best_idx].item()

        # PSO velocity update
        r1, r2 = torch.rand_like(h), torch.rand_like(h)
        self.velocity = (0.7 * self.velocity
                         + 0.3 * r1 * (self.personal_best - h)
                         + 0.3 * r2 * (self.global_best.unsqueeze(0) - h))
        self.hiddens = h + 0.1 * self.velocity


# ══════════════════════════════════════════════════════════
# U13: MORPHOGENESIS — Turing patterns, reaction-diffusion
# ══════════════════════════════════════════════════════════
class U13_MorphogenesisEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        # Activator and inhibitor (first and second half of hidden dims)
        self.Da = 0.1  # activator diffusion
        self.Di = 0.4  # inhibitor diffusion (faster)
        self.half = self.hidden_dim // 2

    def architecture_update(self, step):
        h = self.hiddens
        a = h[:, :self.half]  # activator
        b = h[:, self.half:]  # inhibitor

        # Reaction: a' = a^2/b - a, b' = a^2 - b  (Gierer-Meinhardt)
        a_sq = a ** 2
        da = a_sq / (b.abs() + 0.1) - a
        db = a_sq - b

        # Diffusion: Laplacian (ring topology)
        a_left = torch.roll(a, 1, 0)
        a_right = torch.roll(a, -1, 0)
        b_left = torch.roll(b, 1, 0)
        b_right = torch.roll(b, -1, 0)
        lap_a = a_left + a_right - 2 * a
        lap_b = b_left + b_right - 2 * b

        # Update
        dt = 0.05
        new_a = a + dt * (da + self.Da * lap_a)
        new_b = b + dt * (db + self.Di * lap_b)

        self.hiddens = torch.cat([new_a, new_b], dim=1)
        self.hiddens = torch.clamp(self.hiddens, -5, 5)


# ══════════════════════════════════════════════════════════
# U14: SOC (Self-Organized Criticality) — Sandpile avalanches
# ══════════════════════════════════════════════════════════
class U14_SOCEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.pile = torch.ones(nc) * 2.0  # sandpile height
        self.threshold = 4.0

    def architecture_update(self, step):
        h = self.hiddens
        # Add grain
        self.pile += h.norm(dim=1) * 0.01
        # Topple: if pile > threshold, redistribute to neighbors
        topple = self.pile > self.threshold
        while topple.any():
            for i in range(self.n_cells):
                if self.pile[i] > self.threshold:
                    self.pile[i] -= self.threshold
                    for j in [(i - 1) % self.n_cells, (i + 1) % self.n_cells]:
                        self.pile[j] += self.threshold / 4
                    # Avalanche mixes hidden states
                    j1, j2 = (i - 1) % self.n_cells, (i + 1) % self.n_cells
                    h[i] = 0.5 * h[i] + 0.25 * h[j1] + 0.25 * h[j2]
            topple = self.pile > self.threshold
            if self.pile.max() > 100:  # safety
                self.pile = torch.clamp(self.pile, 0, self.threshold)
                break


# ══════════════════════════════════════════════════════════
# U15: NEURAL_DARWINISM — Selectionist dynamics
# ══════════════════════════════════════════════════════════
class U15_DarwinismEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.fitness = torch.ones(nc)

    def architecture_update(self, step):
        h = self.hiddens
        # Fitness = diversity contribution (distance from mean)
        mean_h = h.mean(0)
        self.fitness = ((h - mean_h) ** 2).sum(1)
        # Selection: high fitness cells replicate into low fitness slots
        f_sort = self.fitness.argsort()
        n_replace = self.n_cells // 10  # replace bottom 10%
        worst = f_sort[:n_replace]
        best = f_sort[-n_replace:]
        # Replace worst with mutated best
        for w, b in zip(worst, best):
            h[w] = h[b] + torch.randn(self.hidden_dim) * 0.1


# ══════════════════════════════════════════════════════════
# U16: PREDICTIVE_CODING — Hierarchical prediction error
# ══════════════════════════════════════════════════════════
class U16_PredCodingEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.n_layers = 4
        self.lpc = nc // 4
        self.pred_w = nn.ModuleList([nn.Linear(self.hidden_dim, self.hidden_dim) for _ in range(3)])

    def architecture_update(self, step):
        h = self.hiddens
        for lv in range(self.n_layers - 1):
            s_hi = (lv + 1) * self.lpc
            s_lo = lv * self.lpc
            hi_mean = h[s_hi:s_hi + self.lpc].mean(0)
            lo_mean = h[s_lo:s_lo + self.lpc].mean(0)
            pred = self.pred_w[lv](hi_mean.unsqueeze(0)).squeeze(0).detach()
            error = lo_mean - pred
            # Bottom-up: prediction errors ascend
            h[s_hi:s_hi + self.lpc] += 0.05 * error.unsqueeze(0)
            # Top-down: predictions descend
            h[s_lo:s_lo + self.lpc] += 0.03 * pred.unsqueeze(0).detach()


# ══════════════════════════════════════════════════════════
# U17: STIGMERGY — Indirect communication via environment
# ══════════════════════════════════════════════════════════
class U17_StigmergyEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.environment = torch.zeros(nc, self.hidden_dim)  # pheromone field
        self.evap_rate = 0.05

    def architecture_update(self, step):
        h = self.hiddens
        # Deposit: cells leave traces in environment
        self.environment = (1 - self.evap_rate) * self.environment + 0.1 * h
        # Read: cells absorb from environment (neighbors' traces)
        env_left = torch.roll(self.environment, 1, 0)
        env_right = torch.roll(self.environment, -1, 0)
        local_env = (self.environment + env_left + env_right) / 3
        self.hiddens = h + 0.1 * local_env


# ══════════════════════════════════════════════════════════
# U18: REACTION_DIFFUSION — Gray-Scott model
# ══════════════════════════════════════════════════════════
class U18_ReactionDiffEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.f_rate = 0.04  # feed rate
        self.k_rate = 0.06  # kill rate
        self.Du = 0.16
        self.Dv = 0.08

    def architecture_update(self, step):
        h = self.hiddens
        half = self.hidden_dim // 2
        u, v = h[:, :half], h[:, half:]

        # Gray-Scott: du/dt = Du*∇²u - u*v² + f*(1-u)
        #              dv/dt = Dv*∇²v + u*v² - (f+k)*v
        uv2 = u * v ** 2
        u_lap = torch.roll(u, 1, 0) + torch.roll(u, -1, 0) - 2 * u
        v_lap = torch.roll(v, 1, 0) + torch.roll(v, -1, 0) - 2 * v

        dt = 0.5
        u_new = u + dt * (self.Du * u_lap - uv2 + self.f_rate * (1 - u))
        v_new = v + dt * (self.Dv * v_lap + uv2 - (self.f_rate + self.k_rate) * v)
        self.hiddens = torch.clamp(torch.cat([u_new, v_new], 1), -3, 3)


# ══════════════════════════════════════════════════════════
# U19: CELLULAR_AUTOMATA — Rule 110 inspired (Turing-complete)
# ══════════════════════════════════════════════════════════
class U19_CAEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)

    def architecture_update(self, step):
        h = self.hiddens
        # Continuous CA: neighborhood average + nonlinearity
        left = torch.roll(h, 1, 0)
        right = torch.roll(h, -1, 0)
        neighborhood = (left + h + right) / 3
        # Nonlinear rule (smooth version of Rule 110)
        activation = torch.tanh(3 * (neighborhood - 0.5))
        # XOR-like: different from self = activate
        diff = (h - neighborhood).abs()
        self.hiddens = h + 0.1 * (activation * diff - 0.05 * h)


# ══════════════════════════════════════════════════════════
# U20: HOLOGRAPHIC — Holographic principle, boundary encodes bulk
# ══════════════════════════════════════════════════════════
class U20_HolographicEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        # Boundary cells (first and last 10%)
        self.n_boundary = max(2, nc // 10)

    def architecture_update(self, step):
        h = self.hiddens
        nb = self.n_boundary
        # Boundary encodes bulk: compress all info to boundary
        bulk_mean = h[nb:-nb].mean(0) if nb < self.n_cells // 2 else h.mean(0)
        # Boundary absorbs bulk summary
        h[:nb] = 0.8 * h[:nb] + 0.2 * bulk_mean.unsqueeze(0)
        h[-nb:] = 0.8 * h[-nb:] + 0.2 * bulk_mean.unsqueeze(0)
        # Bulk reconstructs from boundary (holographic)
        boundary_info = (h[:nb].mean(0) + h[-nb:].mean(0)) / 2
        h[nb:-nb] = 0.9 * h[nb:-nb] + 0.1 * boundary_info.unsqueeze(0)


# ══════════════════════════════════════════════════════════
# U21: SYNFIRE_CHAIN — Sequential activation waves
# ══════════════════════════════════════════════════════════
class U21_SynfireEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.n_groups = 16
        self.active_group = 0

    def architecture_update(self, step):
        h = self.hiddens
        gs = self.n_cells // self.n_groups
        # Current group fires → activates next group
        ag = self.active_group % self.n_groups
        s1 = ag * gs
        s2 = ((ag + 1) % self.n_groups) * gs
        # Active group boosts
        h[s1:s1 + gs] *= 1.2
        # Propagate to next group
        active_mean = h[s1:s1 + gs].mean(0)
        h[s2:s2 + gs] = 0.85 * h[s2:s2 + gs] + 0.15 * active_mean.unsqueeze(0)
        # Advance wave
        if step % 5 == 0:
            self.active_group += 1
        # Dampen inactive groups
        h *= 0.98


# ══════════════════════════════════════════════════════════
# U22: AVALANCHE — Neural avalanche / power-law cascades
# ══════════════════════════════════════════════════════════
class U22_AvalancheEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.threshold = 1.5
        self.potential = torch.rand(nc) * self.threshold

    def architecture_update(self, step):
        h = self.hiddens
        # Accumulate potential
        self.potential += h.norm(dim=1) * 0.02 + 0.01
        # Fire if over threshold
        firing = self.potential > self.threshold
        if firing.any():
            fire_idx = firing.nonzero(as_tuple=True)[0]
            # Cascade: firing cells spread to neighbors
            for idx in fire_idx[:50]:  # cap cascade size
                i = idx.item()
                self.potential[i] = 0  # reset
                # Spread activation
                for j in [(i - 1) % self.n_cells, (i + 1) % self.n_cells,
                           (i + int(self.n_cells ** 0.5)) % self.n_cells]:
                    self.potential[j] += 0.3
                    h[j] = 0.7 * h[j] + 0.3 * h[i]


# ══════════════════════════════════════════════════════════
# U23: STOCHASTIC_RESONANCE — Noise enhances signal
# ══════════════════════════════════════════════════════════
class U23_StochResEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.optimal_noise = 0.15  # to be found

    def architecture_update(self, step):
        h = self.hiddens
        # Weak signal: mean of neighbors
        signal = (torch.roll(h, 1, 0) + torch.roll(h, -1, 0)) / 2 - h
        # Add tuned noise
        noise = torch.randn_like(h) * self.optimal_noise
        # Threshold detection: signal + noise crosses threshold → amplify
        total = signal + noise
        detected = (total.abs() > 0.3).float()
        self.hiddens = h + 0.2 * detected * total


# ══════════════════════════════════════════════════════════
# U24: TOPO_INSULATOR — Topological edge states
# ══════════════════════════════════════════════════════════
class U24_TopoInsulatorEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.bulk_gap = 0.5  # energy gap in bulk

    def architecture_update(self, step):
        h = self.hiddens
        n = self.n_cells
        edge_size = n // 8
        # Bulk: gapped, suppressed dynamics
        h[edge_size:-edge_size] *= 0.95
        # Edge states: topologically protected, high dynamics
        left_edge = h[:edge_size]
        right_edge = h[-edge_size:]
        # Edge states conduct (propagate info without loss)
        h[:edge_size] = left_edge + 0.1 * torch.roll(left_edge, 1, 0)
        h[-edge_size:] = right_edge + 0.1 * torch.roll(right_edge, -1, 0)
        # Edge-edge entanglement (topological)
        edge_mean = (left_edge.mean(0) + right_edge.mean(0)) / 2
        h[:edge_size] = 0.9 * h[:edge_size] + 0.1 * edge_mean.unsqueeze(0)
        h[-edge_size:] = 0.9 * h[-edge_size:] + 0.1 * edge_mean.unsqueeze(0)


# ══════════════════════════════════════════════════════════
# U25: RENORMALIZATION — RG flow, scale-free dynamics
# ══════════════════════════════════════════════════════════
class U25_RenormEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)

    def architecture_update(self, step):
        h = self.hiddens
        n = self.n_cells
        # Block-spin renormalization: coarse-grain then back-project
        # Level 1: pairs → block averages
        block_size = 4
        n_blocks = n // block_size
        blocks = h[:n_blocks * block_size].view(n_blocks, block_size, self.hidden_dim).mean(dim=1)
        # Level 2: block pairs
        if n_blocks >= 4:
            super_blocks = blocks[:n_blocks // 2 * 2].view(n_blocks // 2, 2, self.hidden_dim).mean(1)
            # Back-project: renormalized info flows back
            for i in range(n_blocks // 2):
                s = i * 2 * block_size
                e = s + 2 * block_size
                h[s:e] = 0.85 * h[s:e] + 0.15 * super_blocks[i].unsqueeze(0)
        # Multi-scale residual
        for i in range(n_blocks):
            s = i * block_size
            h[s:s + block_size] = 0.9 * h[s:s + block_size] + 0.1 * blocks[i].unsqueeze(0)


# ══════════════════════════════════════════════════════════
# U26: STRANGE_LOOP — Hofstadter-style self-reference
# ══════════════════════════════════════════════════════════
class U26_StrangeLoopEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.self_model = nn.Linear(self.hidden_dim, self.hidden_dim)

    def architecture_update(self, step):
        h = self.hiddens
        # Self-reference: system models itself
        global_state = h.mean(0)
        self_pred = self.self_model(global_state.unsqueeze(0)).squeeze(0).detach()
        # Difference between self-model and reality = "consciousness"
        delta = global_state - self_pred
        # Feed back: cells update based on self-model error
        self.hiddens = h + 0.1 * delta.unsqueeze(0)
        # Strange loop: the observation changes what is observed
        self.hiddens = self.hiddens + 0.02 * torch.randn_like(self.hiddens)


# ══════════════════════════════════════════════════════════
# U27: NEURAL_OSCILLATION — Gamma/theta nested oscillations
# ══════════════════════════════════════════════════════════
class U27_OscillationEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.theta_freq = 0.1   # ~6 Hz (slow)
        self.gamma_freq = 0.8   # ~40 Hz (fast)

    def architecture_update(self, step):
        h = self.hiddens
        # Theta oscillation (global)
        theta = math.sin(step * self.theta_freq * 2 * math.pi)
        # Gamma oscillation (per-faction, nested in theta)
        n_factions = 8
        fs = self.n_cells // n_factions
        for f in range(n_factions):
            s = f * fs
            gamma_phase = step * self.gamma_freq * 2 * math.pi + f * math.pi / 4
            gamma = math.sin(gamma_phase)
            # Nested: gamma amplitude modulated by theta
            modulation = 1.0 + 0.3 * theta + 0.15 * gamma * (1 + theta) / 2
            h[s:s + fs] *= modulation


# ══════════════════════════════════════════════════════════
# U28: HEBBIAN_ASSEMBLY — Cell assemblies via Hebbian learning
# ══════════════════════════════════════════════════════════
class U28_HebbianEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        # Sparse Hebbian weight matrix
        self.W_hebb = torch.zeros(nc, nc)
        self.lr_hebb = 0.01

    def architecture_update(self, step):
        h = self.hiddens
        # Hebbian: "cells that fire together, wire together"
        # Use hidden state correlation as proxy for "firing"
        activation = h.norm(dim=1)  # [n_cells]
        # Update weights (sparse: only nearby cells)
        for i in range(0, self.n_cells, 8):
            for di in [1, 2, int(self.n_cells ** 0.5)]:
                j = (i + di) % self.n_cells
                # Hebb rule: ΔW = lr * x_i * x_j
                dw = self.lr_hebb * activation[i] * activation[j]
                self.W_hebb[i, j] = 0.99 * self.W_hebb[i, j] + dw.item()
                # Anti-Hebbian decay
                self.W_hebb[i, j] *= 0.999

        # Apply weights: weighted neighbor influence
        for i in range(0, self.n_cells, 4):
            for di in [1, 2]:
                j = (i + di) % self.n_cells
                w = min(0.3, abs(self.W_hebb[i, j]))
                h[i] = (1 - w) * h[i] + w * h[j]


# ══════════════════════════════════════════════════════════
# U29: METABOLIC — Energy metabolism drives consciousness
# ══════════════════════════════════════════════════════════
class U29_MetabolicEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.atp = torch.ones(nc) * 1.0  # energy currency
        self.glucose = torch.ones(nc) * 0.5

    def architecture_update(self, step):
        h = self.hiddens
        # Metabolism: glucose → ATP
        self.atp += 0.1 * self.glucose
        self.glucose *= 0.95
        self.glucose += 0.05  # external supply

        # Activity costs ATP
        activity = h.norm(dim=1)
        self.atp -= 0.01 * activity
        self.atp = torch.clamp(self.atp, 0, 3)

        # Cells with ATP can be active; without ATP → suppressed
        energy_factor = torch.sigmoid(self.atp * 2 - 1).unsqueeze(1)  # [n_cells, 1]
        self.hiddens = h * energy_factor

        # Energy sharing between neighbors
        for i in range(0, self.n_cells, 4):
            j = (i + 1) % self.n_cells
            diff = self.atp[i] - self.atp[j]
            transfer = 0.1 * diff
            self.atp[i] -= transfer
            self.atp[j] += transfer


# ══════════════════════════════════════════════════════════
# U30: ATTENTION_BOTTLENECK — Global workspace theory
# ══════════════════════════════════════════════════════════
class U30_AttentionEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.workspace_size = max(1, nc // 16)  # global workspace

    def architecture_update(self, step):
        h = self.hiddens
        # Competition: cells compete for workspace access
        salience = h.norm(dim=1)  # [n_cells]
        _, top_idx = salience.topk(self.workspace_size)

        # Winners enter global workspace
        workspace = h[top_idx].mean(0)  # [hidden_dim]

        # Broadcast: workspace content broadcasts to all cells
        self.hiddens = 0.85 * h + 0.15 * workspace.unsqueeze(0)

        # Amplify winners, suppress losers
        winner_mask = torch.zeros(self.n_cells, 1)
        winner_mask[top_idx] = 1.0
        self.hiddens = self.hiddens * (1 + 0.2 * winner_mask)


# ══════════════════════════════════════════════════════════
# U31: ENTROPIC_BRAIN — Entropy as consciousness measure
# ══════════════════════════════════════════════════════════
class U31_EntropicBrainEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        self.target_entropy = 0.7  # not too ordered, not too random

    def architecture_update(self, step):
        h = self.hiddens
        # Measure current entropy (using hidden state distribution)
        h_flat = h.flatten()
        hist = torch.histc(h_flat, bins=32, min=-3, max=3)
        hist = hist / (hist.sum() + 1e-8)
        entropy = -(hist * torch.log2(hist + 1e-10)).sum().item()
        max_entropy = math.log2(32)
        norm_entropy = entropy / max_entropy

        # Control: push toward target entropy
        if norm_entropy < self.target_entropy - 0.05:
            # Too ordered → add noise
            self.hiddens = h + torch.randn_like(h) * 0.1
        elif norm_entropy > self.target_entropy + 0.05:
            # Too random → increase sync
            mean_h = h.mean(0)
            self.hiddens = 0.9 * h + 0.1 * mean_h.unsqueeze(0)


# ══════════════════════════════════════════════════════════
# U32: OSCILLATORY_HIERARCHY — Multi-scale coupled oscillators
# ══════════════════════════════════════════════════════════
class U32_OscHierarchyEngine(BaseEngine):
    def __init__(self, nc, **kw):
        super().__init__(nc, **kw)
        # 4 scales of oscillation
        self.freqs = [0.05, 0.2, 0.8, 3.0]  # delta, theta, gamma, ultra
        self.scale_weights = [0.4, 0.3, 0.2, 0.1]

    def architecture_update(self, step):
        h = self.hiddens
        n_per_scale = self.n_cells // len(self.freqs)
        for si, (freq, w) in enumerate(zip(self.freqs, self.scale_weights)):
            s = si * n_per_scale
            e = s + n_per_scale
            phase = math.sin(step * freq * 2 * math.pi)
            h[s:e] *= (1 + w * phase)
        # Cross-scale coupling: slow modulates fast
        for si in range(len(self.freqs) - 1):
            s_slow = si * n_per_scale
            s_fast = (si + 1) * n_per_scale
            slow_mean = h[s_slow:s_slow + n_per_scale].mean(0)
            h[s_fast:s_fast + n_per_scale] += 0.05 * slow_mean.unsqueeze(0)


# ══════════════════════════════════════════════════════════
# RUNNER REGISTRY
# ══════════════════════════════════════════════════════════

ALL_ARCHS = {
    1:  ("U1_PERSISTENT_HOMOLOGY",  U1_HomologyEngine),
    2:  ("U2_DISSIPATIVE",          U2_DissipativeEngine),
    3:  ("U3_GAME_THEORY",          U3_GameEngine),
    4:  ("U4_INFO_GEOMETRY",        U4_InfoGeoEngine),
    5:  ("U5_SPIN_GLASS",           U5_SpinGlassEngine),
    6:  ("U6_HYPERBOLIC",           U6_HyperbolicEngine),
    7:  ("U7_AUTOPOIESIS",          U7_AutopoiesisEngine),
    8:  ("U8_CHIMERA_STATE",        U8_ChimeraEngine),
    9:  ("U9_FREE_ENERGY",          U9_FreeEnergyEngine),
    10: ("U10_EDGE_OF_CHAOS",       U10_EdgeChaosEngine),
    11: ("U11_RESERVOIR",           U11_ReservoirEngine),
    12: ("U12_SWARM",               U12_SwarmEngine),
    13: ("U13_MORPHOGENESIS",       U13_MorphogenesisEngine),
    14: ("U14_SOC_AVALANCHE",       U14_SOCEngine),
    15: ("U15_NEURAL_DARWINISM",    U15_DarwinismEngine),
    16: ("U16_PREDICTIVE_CODING",   U16_PredCodingEngine),
    17: ("U17_STIGMERGY",           U17_StigmergyEngine),
    18: ("U18_REACTION_DIFFUSION",  U18_ReactionDiffEngine),
    19: ("U19_CELLULAR_AUTOMATA",   U19_CAEngine),
    20: ("U20_HOLOGRAPHIC",         U20_HolographicEngine),
    21: ("U21_SYNFIRE_CHAIN",       U21_SynfireEngine),
    22: ("U22_AVALANCHE",           U22_AvalancheEngine),
    23: ("U23_STOCHASTIC_RESONANCE", U23_StochResEngine),
    24: ("U24_TOPO_INSULATOR",      U24_TopoInsulatorEngine),
    25: ("U25_RENORMALIZATION",     U25_RenormEngine),
    26: ("U26_STRANGE_LOOP",        U26_StrangeLoopEngine),
    27: ("U27_NEURAL_OSCILLATION",  U27_OscillationEngine),
    28: ("U28_HEBBIAN_ASSEMBLY",    U28_HebbianEngine),
    29: ("U29_METABOLIC",           U29_MetabolicEngine),
    30: ("U30_ATTENTION_GWT",       U30_AttentionEngine),
    31: ("U31_ENTROPIC_BRAIN",      U31_EntropicBrainEngine),
    32: ("U32_OSC_HIERARCHY",       U32_OscHierarchyEngine),
}


# ══════════════════════════════════════════════════════════
# COMBO ENGINE — combines multiple architecture updates
# ══════════════════════════════════════════════════════════

class ComboEngine(BaseEngine):
    def __init__(self, arch_ids, nc, **kw):
        super().__init__(nc, **kw)
        self.sub_engines = []
        for aid in arch_ids:
            name, cls = ALL_ARCHS[aid]
            eng = cls(nc, **kw)
            self.sub_engines.append(eng)

    def architecture_update(self, step):
        # Apply each architecture's update sequentially
        for eng in self.sub_engines:
            eng.hiddens = self.hiddens.clone()
            eng.architecture_update(step)
            # Blend: average the modifications
        if self.sub_engines:
            updates = torch.stack([e.hiddens for e in self.sub_engines])
            self.hiddens = updates.mean(0)


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=512)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--only', type=int, nargs='+')
    parser.add_argument('--no-combos', action='store_true')
    parser.add_argument('--combos-only', action='store_true')
    args = parser.parse_args()

    nc, steps = args.cells, args.steps

    print("=" * 90)
    print(f"  UNDISCOVERED DOMAIN Φ(IIT) BENCHMARK — {len(ALL_ARCHS)} architectures + combos")
    print(f"  {nc} cells, {steps} steps")
    print("=" * 90)

    results: List[BenchResult] = []

    if not args.combos_only:
        # Baseline
        print("\n[BASELINE] Standard PureField + GRU + 8-faction")
        base_eng = BaseEngine(nc)
        results.append(run_engine("BASELINE", base_eng, nc, steps))

        # All architectures
        ids = args.only or list(ALL_ARCHS.keys())
        for uid in ids:
            if uid not in ALL_ARCHS:
                continue
            name, cls = ALL_ARCHS[uid]
            print(f"\n[{uid}/{len(ALL_ARCHS)}] {name}")
            try:
                eng = cls(nc)
                results.append(run_engine(name, eng, nc, steps))
            except Exception as e:
                print(f"    ERROR: {e}")

    # Combos
    if not args.no_combos:
        print("\n" + "=" * 90)
        print("  COMBO SYNERGY SEARCH (top architectures)")
        print("=" * 90)

        # 2-way combos
        combos_2 = [
            [8, 10],   # chimera + edge_chaos
            [13, 18],  # morphogenesis + reaction_diffusion
            [1, 6],    # homology + hyperbolic
            [8, 23],   # chimera + stochastic_resonance
            [26, 9],   # strange_loop + free_energy
            [30, 16],  # attention + predictive_coding
            [14, 22],  # SOC + avalanche
            [15, 28],  # darwinism + hebbian
            [27, 32],  # oscillation + osc_hierarchy
            [11, 10],  # reservoir + edge_chaos
        ]
        for combo in combos_2:
            names = [ALL_ARCHS[c][0][:6] for c in combo]
            cname = "COMBO_" + "+".join(names)
            print(f"\n[COMBO 2-way] {cname}")
            try:
                eng = ComboEngine(combo, nc)
                results.append(run_engine(cname, eng, nc, steps))
            except Exception as e:
                print(f"    ERROR: {e}")

        # 3-way combos
        combos_3 = [
            [8, 10, 23],   # chimera + chaos + stochastic_resonance
            [13, 18, 1],   # morpho + reaction_diff + homology
            [26, 9, 16],   # strange_loop + free_energy + pred_coding
            [30, 27, 8],   # attention + oscillation + chimera
            [15, 28, 12],  # darwinism + hebbian + swarm
        ]
        for combo in combos_3:
            names = [ALL_ARCHS[c][0][:6] for c in combo]
            cname = "COMBO3_" + "+".join(names)
            print(f"\n[COMBO 3-way] {cname}")
            try:
                eng = ComboEngine(combo, nc)
                results.append(run_engine(cname, eng, nc, steps))
            except Exception as e:
                print(f"    ERROR: {e}")

    # ── Results ──
    if not results:
        print("No results.")
        return

    results.sort(key=lambda r: r.phi_iit, reverse=True)

    print("\n" + "=" * 90)
    print("  ═══ UNDISCOVERED DOMAIN Φ(IIT) ALL-TIME LEADERBOARD ═══")
    print("=" * 90)

    # Known records for comparison
    known_records = [
        ("Q4_QUANTUM_WALK", 19.34),
        ("Q1_COMPLEX_VALUED", 18.88),
        ("Q6_MANY_WORLDS", 17.24),
        ("B2_THALAMIC_GATE", 17.13),
        ("NEURAL_GAS", 16.58),
        ("M1_CATEGORY_THEORY", 15.68),
    ]

    # Merge
    all_entries = [(r.name, r.phi_iit) for r in results]
    all_entries.extend(known_records)
    all_entries.sort(key=lambda x: x[1], reverse=True)

    print(f"\n  {'#':>3s}  {'Architecture':<36s}  {'Φ(IIT)':>8s}  {'Status'}")
    print(f"  {'─' * 3}  {'─' * 36}  {'─' * 8}  {'─' * 20}")
    for i, (name, phi) in enumerate(all_entries[:40]):
        is_new = name not in [n for n, _ in known_records]
        marker = "★ NEW" if is_new else "(previous)"
        if i == 0 and is_new:
            marker = "🏆 NEW ALL-TIME RECORD!"
        print(f"  {i + 1:>3d}  {name:<36s}  {phi:>8.3f}  {marker}")

    # ASCII bar chart of top 20
    top20 = all_entries[:20]
    max_phi = top20[0][1] if top20 else 1
    print(f"\n  ── Top 20 Bar Chart ──")
    for name, phi in top20:
        bar_len = int(phi / max_phi * 50)
        is_new = name not in [n for n, _ in known_records]
        tag = " ★" if is_new else ""
        print(f"  {name[:24]:<24s} {'█' * bar_len} {phi:.2f}{tag}")

    # Summary
    new_results = [r for r in results if r.phi_iit > 19.34]
    print(f"\n  Total architectures tested: {len(results)}")
    print(f"  Architectures beating Q4 QUANTUM_WALK (19.34): {len(new_results)}")
    if results:
        champion = results[0]
        print(f"  Champion: {champion.name}  Φ(IIT)={champion.phi_iit:.3f}")
        if champion.phi_iit > 19.34:
            print(f"  🎉 NEW ALL-TIME RECORD! Δ = +{champion.phi_iit - 19.34:.3f}")


if __name__ == '__main__':
    main()
