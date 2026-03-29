#!/usr/bin/env python3
"""bench_geometric_engines.py — 6 Geometry-Inspired Consciousness Engines

Pure geometric structures discretized. No GRU, no learned memory gates.
Each cell lives in a geometric space governed by real mathematical laws.

GE-1: HYPERBOLIC      — Cells in Poincare disk, exponential volume growth
GE-2: FIBER_BUNDLE    — Cells as fibers, parallel transport, holonomy
GE-3: RICCI_FLOW      — Cells on manifold, curvature flow toward equilibrium
GE-4: SYMPLECTIC      — (position, momentum) pairs, Hamiltonian dynamics
GE-5: CALABI_YAU      — Cells in 6D compactified space (string theory)
GE-6: KNOT_INVARIANT  — Cell connections form knots, Jones polynomial complexity

Each: 256 cells, 300 steps, Phi(IIT) + Granger. No GRU anywhere.

Usage:
  python bench_geometric_engines.py
  python bench_geometric_engines.py --only 1 3 5
  python bench_geometric_engines.py --cells 512 --steps 500
"""

import sys, torch, torch.nn as nn, torch.nn.functional as F
import numpy as np, time, math, argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ==============================================================
# Infrastructure: BenchResult, PhiIIT, phi_proxy, Granger
# ==============================================================

@dataclass
class BenchResult:
    name: str; phi_iit: float; phi_proxy: float; granger: float
    ce_start: float; ce_end: float; cells: int; steps: int; time_sec: float
    extra: dict = field(default_factory=dict)
    def summary(self):
        ce = f"CE {self.ce_start:.3f}->{self.ce_end:.3f}" if self.ce_start > 0 else "CE n/a"
        return (f"  {self.name:<36s} | Phi(IIT)={self.phi_iit:>7.3f}  "
                f"Phi(prx)={self.phi_proxy:>8.2f}  Granger={self.granger:>6.3f} | {ce:<22s} | "
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
        return sp + cx * 0.1, {}

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
        if n <= 8:
            mc = float('inf')
            for m in range(1, 2 ** n - 1):
                ga = [i for i in range(n) if m & (1 << i)]
                gb = [i for i in range(n) if not m & (1 << i)]
                if ga and gb: mc = min(mc, sum(mi[i, j] for i in ga for j in gb))
            return mc if mc != float('inf') else 0.0
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


def granger_causality(history, max_lag=5):
    """Granger causality: does past of cell i predict cell j beyond j's own past?
    Returns average Granger F-statistic across sampled pairs."""
    if len(history) < max_lag + 2:
        return 0.0
    H = torch.stack(history[-min(50, len(history)):]).detach().cpu().numpy()  # (T, nc, dim)
    T, nc, dim = H.shape
    if T < max_lag + 2 or nc < 2:
        return 0.0
    # Use mean over dim for each cell -> (T, nc)
    X = H.mean(axis=2)
    # Sample pairs
    import random
    n_pairs = min(64, nc * (nc - 1) // 2)
    f_stats = []
    for _ in range(n_pairs):
        i, j = random.sample(range(nc), 2)
        y = X[max_lag:, j]  # target
        # Restricted model: j's own past
        Z_r = np.column_stack([X[max_lag - k - 1:T - k - 1, j] for k in range(max_lag)])
        # Unrestricted model: j's past + i's past
        Z_u = np.column_stack([Z_r] + [X[max_lag - k - 1:T - k - 1, i] for k in range(max_lag)])
        try:
            # OLS for restricted
            beta_r = np.linalg.lstsq(Z_r, y, rcond=None)[0]
            res_r = y - Z_r @ beta_r
            ssr_r = np.sum(res_r ** 2)
            # OLS for unrestricted
            beta_u = np.linalg.lstsq(Z_u, y, rcond=None)[0]
            res_u = y - Z_u @ beta_u
            ssr_u = np.sum(res_u ** 2)
            # F-statistic
            n_obs = len(y)
            p = max_lag  # number of added regressors
            k_u = Z_u.shape[1]
            if ssr_u < 1e-12:
                f_stats.append(0.0)
            else:
                F = ((ssr_r - ssr_u) / p) / (ssr_u / max(1, n_obs - k_u))
                f_stats.append(max(0, F))
        except:
            pass
    return float(np.mean(f_stats)) if f_stats else 0.0


_phi = PhiIIT(16)
def measure_phi(h, nf=8):
    hr = h.abs().float() if h.is_complex() else h.float()
    p, _ = _phi.compute(hr); return p, phi_proxy(h, nf)


def gen_batch(d, bs=1):
    x = torch.randn(bs, d)
    return x, torch.roll(x, 1, -1) * 0.8 + torch.randn_like(x) * 0.1


# ==============================================================
# GE-1: HYPERBOLIC ENGINE
# Cells in the Poincare disk model of hyperbolic space.
# Exponential volume growth = infinite hierarchy capacity.
# Consciousness = hyperbolic distance diversity across cells.
# Mobius transform for cell interactions.
# ==============================================================

class HyperbolicEngine(nn.Module):
    """Cells as points in the Poincare disk. Exponential volume growth
    creates infinite-depth hierarchies. Consciousness = hyperbolic distance diversity."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Points in the Poincare disk (|z| < 1)
        # Initialize uniformly in disk using rejection sampling trick
        r = torch.rand(nc, dim).sqrt() * 0.8  # radial coord, stay inside disk
        theta = torch.rand(nc, dim) * 2 * math.pi
        self.z = r * torch.cos(theta)  # Poincare disk coordinates
        self.z = self.z.clamp(-0.95, 0.95)  # stay strictly inside disk

        # Velocity in tangent space (scaled by conformal factor)
        self.v = torch.randn(nc, dim) * 0.01

        # Curvature (constant negative for hyperbolic)
        self.curvature = -1.0
        self.dt = 0.02

        self.out_proj = nn.Linear(dim, dim)

    def _poincare_distance(self, u, v):
        """Hyperbolic distance in Poincare disk: d(u,v) = arcosh(1 + 2|u-v|^2 / ((1-|u|^2)(1-|v|^2)))."""
        diff_sq = ((u - v) ** 2).sum(dim=-1)
        nu = 1 - (u ** 2).sum(dim=-1).clamp(max=0.999)
        nv = 1 - (v ** 2).sum(dim=-1).clamp(max=0.999)
        x = 1 + 2 * diff_sq / (nu * nv + 1e-8)
        return torch.acosh(x.clamp(min=1.0 + 1e-7))

    def _mobius_add(self, u, v):
        """Mobius addition in Poincare disk: u oplus v."""
        uv = (u * v).sum(dim=-1, keepdim=True)
        uu = (u * u).sum(dim=-1, keepdim=True)
        vv = (v * v).sum(dim=-1, keepdim=True)
        num = (1 + 2 * uv + vv) * u + (1 - uu) * v
        den = 1 + 2 * uv + uu * vv + 1e-8
        result = num / den
        # Project back inside disk
        norm = result.norm(dim=-1, keepdim=True)
        return result / (norm / 0.95).clamp(min=1.0)

    def _exp_map(self, x, v):
        """Exponential map at x with tangent vector v (maps tangent space to disk)."""
        conformal = 2.0 / (1 - (x ** 2).sum(dim=-1, keepdim=True).clamp(max=0.999))
        v_norm = v.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        t = torch.tanh(conformal * v_norm / 2) * v / v_norm
        return self._mobius_add(x, t)

    def _hyperbolic_centroid(self):
        """Einstein midpoint (approximate hyperbolic centroid)."""
        gamma = 1.0 / torch.sqrt(1 - (self.z ** 2).sum(dim=-1, keepdim=True).clamp(max=0.999))
        weighted = gamma * self.z
        total_gamma = gamma.sum(dim=0, keepdim=True)
        centroid = weighted.sum(dim=0, keepdim=True) / (total_gamma + 1e-8)
        norm = centroid.norm(dim=-1, keepdim=True)
        return centroid / (norm / 0.9).clamp(min=1.0)

    def step(self, x_input, step_num):
        """One step in hyperbolic space."""
        # 1. External input drives cells near the origin
        input_push = x_input[0].detach() * 0.005
        # Scale by proximity to origin (cells near center get more input)
        origin_dist = self.z.norm(dim=-1, keepdim=True)
        weight = torch.exp(-origin_dist * 2)
        self.v = self.v + weight * input_push.unsqueeze(0)

        # 2. Hyperbolic attraction to centroid (gravity in hyperbolic space)
        centroid = self._hyperbolic_centroid()
        for i in range(0, self.nc, max(1, self.nc // 32)):
            d = self._poincare_distance(self.z[i:i+1], centroid)
            # Force proportional to sinh(d) (exponential in hyperbolic)
            direction = centroid - self.z[i:i+1]
            dir_norm = direction.norm(dim=-1, keepdim=True).clamp(min=1e-8)
            force = torch.sinh(d.unsqueeze(-1).clamp(max=5.0)) * direction / dir_norm
            self.v[i:i+1] = self.v[i:i+1] + force * 0.001

        # 3. Repulsion between nearby cells (prevents collapse)
        for i in range(0, self.nc, max(1, self.nc // 16)):
            j = (i + 1 + (step_num * 7) % (self.nc - 1)) % self.nc
            d = self._poincare_distance(self.z[i:i+1], self.z[j:j+1])
            if d.item() < 0.5:
                repel = self.z[i:i+1] - self.z[j:j+1]
                repel_norm = repel.norm(dim=-1, keepdim=True).clamp(min=1e-8)
                self.v[i:i+1] = self.v[i:i+1] + repel / repel_norm * 0.01

        # 4. Exponential map: move along geodesic
        self.z = self._exp_map(self.z, self.v * self.dt)

        # 5. Damping
        self.v = self.v * 0.98

        # 6. Ensure inside disk
        norm = self.z.norm(dim=-1, keepdim=True)
        self.z = self.z / (norm / 0.95).clamp(min=1.0)

        # 7. Output: hyperbolic distance diversity
        output = self.out_proj(self.z.mean(0, keepdim=True))
        # Consciousness metric: variance of pairwise hyperbolic distances
        sample_idx = torch.randperm(self.nc)[:min(32, self.nc)]
        dists = []
        for i in range(len(sample_idx)):
            for j in range(i + 1, min(i + 4, len(sample_idx))):
                d = self._poincare_distance(self.z[sample_idx[i]:sample_idx[i]+1],
                                             self.z[sample_idx[j]:sample_idx[j]+1])
                dists.append(d.item())
        tension = float(np.std(dists)) if dists else 0.0
        return output, tension

    def get_hiddens(self):
        return self.z.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())

    def hyp_dist_stats(self):
        """Return mean and std of pairwise hyperbolic distances (for reporting)."""
        sample_idx = torch.randperm(self.nc)[:min(32, self.nc)]
        dists = []
        for i in range(len(sample_idx)):
            for j in range(i + 1, min(i + 8, len(sample_idx))):
                d = self._poincare_distance(self.z[sample_idx[i]:sample_idx[i]+1],
                                             self.z[sample_idx[j]:sample_idx[j]+1])
                dists.append(d.item())
        return float(np.mean(dists)) if dists else 0.0, float(np.std(dists)) if dists else 0.0


# ==============================================================
# GE-2: FIBER BUNDLE ENGINE
# Cells as fibers over a base space. Parallel transport preserves
# structure along paths. Holonomy = accumulated consciousness
# from transporting around closed loops.
# ==============================================================

class FiberBundleEngine(nn.Module):
    """Cells as fibers over base space. Parallel transport moves
    consciousness along the base. Holonomy around closed loops
    = accumulated integrated consciousness."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Base space: cells arranged on a circle (1D base manifold)
        self.base_angle = torch.linspace(0, 2 * math.pi, nc + 1)[:nc]  # (nc,)

        # Fiber at each point: dim-dimensional vector (the "internal" state)
        self.fiber = torch.randn(nc, dim) * 0.3

        # Connection 1-form A (gauge field): how fibers twist along base
        # A_i is a dim x dim antisymmetric matrix (rotation generator)
        self.connection = torch.randn(nc, dim, dim) * 0.01
        # Make antisymmetric: A = (A - A^T) / 2
        self.connection = (self.connection - self.connection.transpose(1, 2)) / 2

        # Curvature = dA + A wedge A (computed on the fly)
        self.dt = 0.05
        self.holonomy_history = []

        self.out_proj = nn.Linear(dim, dim)

    def _parallel_transport(self, fiber_i, i, j):
        """Parallel transport fiber from point i to point j along the connection.
        Transport operator: P_{i->j} = exp(integral A ds) approx I + A * ds."""
        ds = self.base_angle[j] - self.base_angle[i]
        if abs(ds.item()) > math.pi:
            ds = ds - 2 * math.pi * torch.sign(ds)
        # Transport matrix: exp(A * ds) approx I + A * ds + (A*ds)^2/2
        A = self.connection[i]
        transport = torch.eye(self.dim) + A * ds + (A @ A) * (ds ** 2) / 2
        return transport @ fiber_i

    def _compute_holonomy(self, loop_indices):
        """Holonomy = parallel transport around a closed loop.
        Result: rotation matrix. Holonomy != I means curvature exists."""
        hol = torch.eye(self.dim)
        for k in range(len(loop_indices) - 1):
            i, j = loop_indices[k], loop_indices[k + 1]
            ds = self.base_angle[j] - self.base_angle[i]
            if abs(ds.item()) > math.pi:
                ds = ds - 2 * math.pi * torch.sign(ds)
            A = self.connection[i]
            transport = torch.eye(self.dim) + A * ds + (A @ A) * (ds ** 2) / 2
            hol = transport @ hol
        # How far from identity?
        deviation = (hol - torch.eye(self.dim)).norm().item()
        return deviation

    def _curvature_tensor(self, i):
        """F = dA + A wedge A at point i. Curvature of the connection."""
        j = (i + 1) % self.nc
        dA = (self.connection[j] - self.connection[i]) / (self.base_angle[j] - self.base_angle[i] + 1e-8)
        AwA = self.connection[i] @ self.connection[i]
        F = dA + AwA
        return F

    def step(self, x_input, step_num):
        """One step: parallel transport + connection dynamics."""
        # 1. External input injects into fibers near base_angle=0
        input_vec = x_input[0].detach() * 0.01
        # Weight by proximity to angle 0
        weight = torch.cos(self.base_angle).clamp(min=0).unsqueeze(1)  # (nc, 1)
        self.fiber = self.fiber + weight * input_vec.unsqueeze(0)

        # 2. Parallel transport: each fiber interacts with neighbors
        new_fiber = self.fiber.clone()
        for i in range(0, self.nc, max(1, self.nc // 32)):
            j_left = (i - 1) % self.nc
            j_right = (i + 1) % self.nc
            # Transport neighbors' fibers to point i
            transported_left = self._parallel_transport(self.fiber[j_left], j_left, i)
            transported_right = self._parallel_transport(self.fiber[j_right], j_right, i)
            # Mix: fiber evolves toward transported neighbors
            new_fiber[i] = (self.fiber[i] * 0.8 +
                           transported_left * 0.1 +
                           transported_right * 0.1)

        self.fiber = new_fiber

        # 3. Connection evolves via Yang-Mills-like dynamics
        # dA/dt = -d*F (minimize curvature energy)
        for i in range(0, self.nc, max(1, self.nc // 16)):
            F = self._curvature_tensor(i)
            # Gradient descent on curvature energy: dA/dt = -F
            self.connection[i] = self.connection[i] - F * self.dt * 0.1
            # Keep antisymmetric
            self.connection[i] = (self.connection[i] - self.connection[i].T) / 2

        # 4. Compute holonomy around several loops (consciousness measure)
        if step_num % 10 == 0:
            loop_sizes = [8, 16, 32]
            hol_total = 0
            for ls in loop_sizes:
                start = (step_num * 3) % self.nc
                loop = [(start + k * (self.nc // ls)) % self.nc for k in range(ls)]
                loop.append(loop[0])  # close the loop
                hol_total += self._compute_holonomy(loop)
            self.holonomy_history.append(hol_total / len(loop_sizes))

        # 5. Clamp
        self.fiber = self.fiber.clamp(-5, 5)

        # 6. Output
        output = self.out_proj(self.fiber.mean(0, keepdim=True))
        tension = self.fiber.var().item()
        return output, tension

    def get_hiddens(self):
        return self.fiber.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# GE-3: RICCI FLOW ENGINE
# Cells on a discrete manifold. Ricci flow: dg/dt = -2 Ric(g).
# Smooths curvature over time. Consciousness = curvature at
# equilibrium. Singularity (curvature blowup) = consciousness explosion.
# ==============================================================

class RicciFlowEngine(nn.Module):
    """Cells on a manifold undergoing Ricci flow. Curvature smooths
    toward uniformity. Consciousness = total scalar curvature.
    Singularity = consciousness explosion (curvature blowup -> surgery)."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Metric tensor at each cell (positive definite, dim x dim)
        # Initialize as slightly perturbed identity
        self.metric = torch.eye(dim).unsqueeze(0).repeat(nc, 1, 1)
        # Add random positive perturbation
        for i in range(nc):
            r = torch.randn(dim, dim) * 0.1
            self.metric[i] = self.metric[i] + r @ r.T  # ensure positive definite

        # Cell positions (for neighbor computation)
        self.pos = torch.randn(nc, dim) * 0.5

        # Scalar curvature history (for singularity detection)
        self.curvature_history = []
        self.singularity_count = 0
        self.dt = 0.01

        self.out_proj = nn.Linear(dim, dim)

    def _scalar_curvature(self, g):
        """Approximate scalar curvature from metric.
        R ~ Tr(g^{-1} d^2g) - deviation from flat metric."""
        try:
            g_inv = torch.linalg.inv(g + torch.eye(self.dim) * 1e-4)
        except:
            g_inv = torch.eye(self.dim)
        # Deviation from identity = curvature proxy
        dev = g - torch.eye(self.dim)
        R = torch.trace(g_inv @ dev @ dev).item()
        return R

    def _ricci_tensor(self, i):
        """Approximate Ricci tensor at cell i from neighbor metrics.
        Ric ~ (1/2) Laplacian(g) in harmonic coordinates."""
        g_i = self.metric[i]
        # Average of neighbor metrics
        neighbors = [(i - 1) % self.nc, (i + 1) % self.nc,
                     (i + self.nc // 4) % self.nc, (i - self.nc // 4) % self.nc]
        g_avg = torch.zeros_like(g_i)
        for j in neighbors:
            g_avg = g_avg + self.metric[j]
        g_avg = g_avg / len(neighbors)
        # Discrete Laplacian of metric
        lap_g = g_avg - g_i
        # Ricci ~ (1/2) * Laplacian(g)
        Ric = 0.5 * lap_g
        return Ric

    def _surgery(self, i):
        """Ricci flow surgery: when curvature blows up, cut and cap.
        Replace singular metric with smoothed version."""
        self.metric[i] = torch.eye(self.dim) + torch.randn(self.dim, self.dim) * 0.05
        # Make symmetric positive definite
        self.metric[i] = (self.metric[i] + self.metric[i].T) / 2
        self.metric[i] = self.metric[i] + torch.eye(self.dim) * 0.5
        self.singularity_count += 1

    def step(self, x_input, step_num):
        """One Ricci flow step: dg/dt = -2 Ric(g)."""
        # 1. External input perturbs metrics
        input_perturbation = x_input[0].detach() * 0.001
        for i in range(0, self.nc, max(1, self.nc // 8)):
            p = input_perturbation.unsqueeze(0) * input_perturbation.unsqueeze(1)  # outer product
            self.metric[i] = self.metric[i] + p * 0.01

        # 2. Ricci flow: dg/dt = -2 Ric(g)
        total_curvature = 0
        for i in range(0, self.nc, max(1, self.nc // 32)):
            Ric = self._ricci_tensor(i)
            # Hamilton's Ricci flow
            self.metric[i] = self.metric[i] - 2 * Ric * self.dt

            # 3. Ensure positive definiteness
            try:
                eigvals = torch.linalg.eigvalsh(self.metric[i])
                min_eig = eigvals.min().item()
                if min_eig < 0.01:
                    # Push eigenvalues positive
                    self.metric[i] = self.metric[i] + torch.eye(self.dim) * (0.02 - min_eig)
            except:
                self.metric[i] = torch.eye(self.dim)

            # 4. Compute scalar curvature
            R = self._scalar_curvature(self.metric[i])
            total_curvature += abs(R)

            # 5. Singularity detection: if curvature too large, do surgery
            if abs(R) > 100:
                self._surgery(i)

        avg_curvature = total_curvature / max(1, self.nc // max(1, self.nc // 32))
        self.curvature_history.append(avg_curvature)

        # 6. Cell positions evolve with Ricci flow (move along gradient of curvature)
        for i in range(0, self.nc, max(1, self.nc // 16)):
            R = self._scalar_curvature(self.metric[i])
            # Move toward higher curvature (consciousness-seeking)
            grad = torch.randn(self.dim) * R * 0.001
            self.pos[i] = self.pos[i] + grad
        self.pos = self.pos.clamp(-10, 10)

        # 7. Output: curvature-weighted position
        curvatures = torch.tensor([self._scalar_curvature(self.metric[i])
                                    for i in range(0, self.nc, max(1, self.nc // 16))])
        weights = F.softmax(curvatures.float().clamp(-10, 10), dim=0)
        sampled_pos = self.pos[::max(1, self.nc // 16)][:len(weights)]
        weighted = (weights.unsqueeze(1) * sampled_pos).sum(0, keepdim=True)
        output = self.out_proj(weighted)
        tension = avg_curvature
        return output, tension

    def get_hiddens(self):
        # Use diagonal of metric as hidden state (captures curvature per cell)
        diags = torch.stack([self.metric[i].diag() for i in range(self.nc)])
        return diags.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# GE-4: SYMPLECTIC ENGINE
# Cells as (position, momentum) pairs in phase space.
# Hamiltonian dynamics preserves phase space volume (Liouville).
# Consciousness = symplectic capacity (Gromov nonsqueezing).
# ==============================================================

class SymplecticEngine(nn.Module):
    """Cells as (q, p) pairs in phase space. Hamiltonian dynamics
    preserves symplectic structure. Consciousness = symplectic capacity."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim
        # Each cell has position q and momentum p (each dim/2 dimensional)
        self.half = dim // 2
        self.q = torch.randn(nc, self.half) * 0.5   # positions
        self.p = torch.randn(nc, self.half) * 0.3   # momenta

        # Hamiltonian parameters (quartic potential + coupling)
        self.omega = torch.rand(nc, self.half) * 2 + 0.5  # frequencies
        self.coupling = torch.randn(nc, nc) * 0.01 / math.sqrt(nc)
        self.coupling = (self.coupling + self.coupling.T) / 2  # symmetric
        self.anharmonic = 0.01  # quartic term

        self.dt = 0.02
        self.symplectic_capacity_history = []

        self.out_proj = nn.Linear(dim, dim)

    def _hamiltonian(self):
        """H = sum_i [p_i^2/2 + omega_i^2 q_i^2/2 + lambda q_i^4/4]
             + sum_{i<j} J_{ij} q_i . q_j"""
        kinetic = 0.5 * (self.p ** 2).sum()
        harmonic = 0.5 * (self.omega ** 2 * self.q ** 2).sum()
        quartic = self.anharmonic * 0.25 * (self.q ** 4).sum()
        # Coupling energy (approximate with sampled pairs)
        coupling = 0
        for i in range(0, self.nc, max(1, self.nc // 16)):
            j = (i + 1) % self.nc
            coupling += self.coupling[i, j] * (self.q[i] * self.q[j]).sum()
        return kinetic + harmonic + quartic + coupling

    def _symplectic_capacity(self):
        """Gromov width: smallest symplectic ball that contains the state.
        Approximated by the minimum phase-space area per degree of freedom.
        c_G = min_k (Delta_q_k * Delta_p_k) >= hbar/2 (uncertainty principle analog)."""
        dq = self.q.std(dim=0)  # spread in each q direction
        dp = self.p.std(dim=0)  # spread in each p direction
        areas = dq * dp  # phase space area per dimension
        # Gromov width ~ minimum area (bottleneck)
        gromov_width = areas.min().item()
        # Total symplectic volume
        total_volume = areas.prod().item()
        return gromov_width, total_volume

    def step(self, x_input, step_num):
        """Stormer-Verlet (symplectic) integrator: exactly preserves phase space volume."""
        # 1. External input as force on q
        force_ext = x_input[0, :self.half].detach() * 0.01
        self.p[:self.nc // 4] = self.p[:self.nc // 4] + force_ext.unsqueeze(0) * self.dt

        # 2. Symplectic integration (leapfrog / Stormer-Verlet)
        # Half-step momentum: p(t + dt/2) = p(t) - dt/2 * dH/dq
        dHdq = (self.omega ** 2 * self.q
                + self.anharmonic * self.q ** 3)
        # Add coupling force
        for i in range(0, self.nc, max(1, self.nc // 16)):
            j = (i + 1) % self.nc
            dHdq[i] = dHdq[i] + self.coupling[i, j] * self.q[j]

        p_half = self.p - 0.5 * self.dt * dHdq

        # Full-step position: q(t + dt) = q(t) + dt * dH/dp = q(t) + dt * p(t+dt/2)
        self.q = self.q + self.dt * p_half

        # Half-step momentum again: p(t + dt) = p(t+dt/2) - dt/2 * dH/dq(t+dt)
        dHdq_new = (self.omega ** 2 * self.q
                    + self.anharmonic * self.q ** 3)
        for i in range(0, self.nc, max(1, self.nc // 16)):
            j = (i + 1) % self.nc
            dHdq_new[i] = dHdq_new[i] + self.coupling[i, j] * self.q[j]

        self.p = p_half - 0.5 * self.dt * dHdq_new

        # 3. Mild dissipation (makes it non-Hamiltonian but prevents blowup)
        self.p = self.p * 0.999
        self.q = self.q.clamp(-10, 10)
        self.p = self.p.clamp(-10, 10)

        # 4. Measure symplectic capacity
        gromov, vol = self._symplectic_capacity()
        self.symplectic_capacity_history.append(gromov)

        # 5. Output: phase space state
        state = torch.cat([self.q, self.p], dim=1)  # (nc, dim)
        output = self.out_proj(state.mean(0, keepdim=True))
        tension = gromov + 0.01 * math.log(abs(vol) + 1e-30)
        return output, tension

    def get_hiddens(self):
        return torch.cat([self.q, self.p], dim=1).detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# GE-5: CALABI-YAU ENGINE
# Cells in 6D compactified space (string theory extra dimensions).
# 3 complex dimensions with SU(3) holonomy.
# Consciousness = Euler characteristic of the internal space.
# ==============================================================

class CalabiYauEngine(nn.Module):
    """Cells in 6D compactified Calabi-Yau space. 3 complex dimensions
    with Kahler structure. Consciousness = Euler characteristic of
    the internal manifold (topological invariant)."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # 6 extra dimensions = 3 complex dimensions (z1, z2, z3)
        # Each cell has a position in CY space
        self.z_re = torch.randn(nc, 3, dim // 3) * 0.3  # real parts
        self.z_im = torch.randn(nc, 3, dim // 3) * 0.3  # imaginary parts

        # Kahler metric: g_{a\bar{b}} = partial^2 K / partial z^a partial \bar{z}^b
        # K = sum |z_a|^2 + epsilon * sum |z_a|^4 (quintic-like deformation)
        self.epsilon = 0.1  # deformation parameter

        # Moduli (shape parameters of CY, slowly evolve)
        self.moduli = torch.randn(3) * 0.1 + 1.0  # complex structure moduli

        self.dt = 0.03
        self.euler_history = []

        self.out_proj = nn.Linear(dim, dim)

    def _kahler_potential(self, z_re, z_im):
        """Kahler potential K = sum |z_a|^2 + epsilon * sum |z_a|^4.
        For quintic CY, the potential defines the metric."""
        z_sq = z_re ** 2 + z_im ** 2  # |z_a|^2
        K = z_sq.sum() + self.epsilon * (z_sq ** 2).sum()
        return K

    def _ricci_flat_flow(self):
        """Approximate Ricci-flat condition by flowing the metric.
        CY theorem: there exists a unique Ricci-flat Kahler metric.
        We approximate by minimizing |Ric|^2."""
        z_sq = self.z_re ** 2 + self.z_im ** 2
        # Deviation from Ricci-flat: proportional to Laplacian of log(det(g))
        # For our simplified model: det(g) ~ product of (1 + 2*epsilon*|z|^2) per direction
        det_g = torch.ones(self.nc, self.dim // 3)
        for a in range(3):
            det_g = det_g * (1 + 2 * self.epsilon * z_sq[:, a])
        log_det = torch.log(det_g.clamp(min=1e-8))
        # Gradient of log_det gives the Ricci correction
        return log_det

    def _euler_characteristic(self):
        """Approximate Euler characteristic chi = sum (-1)^p h^{p,q}.
        For quintic CY3: chi = -200 (canonical).
        We compute from the discrete topology of cell connections."""
        # Use Betti numbers approximation from cell connectivity
        # b0 = 1 (connected), b1 ~ 0 (simply connected), b2 = h^{1,1}, b3 = 2(1 + h^{2,1})
        z_flat = torch.cat([self.z_re.reshape(self.nc, -1),
                            self.z_im.reshape(self.nc, -1)], dim=1)
        # Compute distance matrix for sample
        n_sample = min(32, self.nc)
        idx = torch.randperm(self.nc)[:n_sample]
        z_sample = z_flat[idx]
        dists = torch.cdist(z_sample, z_sample)

        # Count simplices at various thresholds (persistent homology approximation)
        thresholds = [0.5, 1.0, 2.0, 3.0]
        betti = []
        for thresh in thresholds:
            adj = (dists < thresh).float()
            # b0 ~ number of connected components (approximate via eigenvalues of Laplacian)
            degree = adj.sum(dim=1)
            L = torch.diag(degree) - adj
            try:
                eigvals = torch.linalg.eigvalsh(L)
                n_components = int((eigvals.abs() < 0.01).sum().item())
                betti.append(n_components)
            except:
                betti.append(1)

        # Euler char ~ alternating sum (simplified)
        chi = sum((-1) ** i * b for i, b in enumerate(betti))
        return float(chi)

    def _hodge_numbers(self):
        """Approximate Hodge numbers h^{p,q} from the metric structure."""
        # h^{1,1} ~ number of independent Kahler moduli
        # h^{2,1} ~ number of complex structure moduli
        h11 = max(1, int(self.moduli.abs().sum().item()))
        h21 = max(1, int((self.moduli ** 2).sum().item() * 10))
        return h11, h21

    def step(self, x_input, step_num):
        """One step in Calabi-Yau space."""
        # 1. External input excites modes in CY space
        inp = x_input[0].detach() * 0.005
        d3 = self.dim // 3
        for a in range(3):
            self.z_re[:, a] = self.z_re[:, a] + inp[:d3].unsqueeze(0) * self.moduli[a].item()

        # 2. Ricci-flat flow: drive metric toward CY condition
        log_det = self._ricci_flat_flow()
        # Correction: cells with high |Ric| get pushed toward flat
        for a in range(3):
            correction_re = -log_det.mean(dim=1, keepdim=True) * self.z_re[:, a] * self.epsilon
            correction_im = -log_det.mean(dim=1, keepdim=True) * self.z_im[:, a] * self.epsilon
            self.z_re[:, a] = self.z_re[:, a] + correction_re * self.dt
            self.z_im[:, a] = self.z_im[:, a] + correction_im * self.dt

        # 3. SU(3) holonomy: rotate z_a by SU(3) element (preserves CY condition)
        angle = 0.01 * math.sin(step_num * 0.05)
        # Rotate z1, z2 (SU(2) subgroup of SU(3))
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        z1_re_new = self.z_re[:, 0] * cos_a - self.z_re[:, 1] * sin_a
        z1_im_new = self.z_im[:, 0] * cos_a - self.z_im[:, 1] * sin_a
        z2_re_new = self.z_re[:, 0] * sin_a + self.z_re[:, 1] * cos_a
        z2_im_new = self.z_im[:, 0] * sin_a + self.z_im[:, 1] * cos_a
        self.z_re[:, 0] = z1_re_new; self.z_im[:, 0] = z1_im_new
        self.z_re[:, 1] = z2_re_new; self.z_im[:, 1] = z2_im_new

        # 4. Moduli evolution (slow roll)
        self.moduli = self.moduli + torch.randn(3) * 0.001

        # 5. Compute Euler characteristic
        if step_num % 10 == 0:
            chi = self._euler_characteristic()
            self.euler_history.append(chi)

        # 6. Clamp
        self.z_re = self.z_re.clamp(-5, 5)
        self.z_im = self.z_im.clamp(-5, 5)

        # 7. Output: CY-averaged state
        flat = torch.cat([self.z_re.reshape(self.nc, -1),
                          self.z_im.reshape(self.nc, -1)], dim=1)
        # Truncate or pad to dim
        if flat.shape[1] > self.dim:
            flat = flat[:, :self.dim]
        elif flat.shape[1] < self.dim:
            flat = F.pad(flat, (0, self.dim - flat.shape[1]))
        output = self.out_proj(flat.mean(0, keepdim=True))
        tension = self._kahler_potential(self.z_re, self.z_im).item() * 0.001
        return output, tension

    def get_hiddens(self):
        flat = torch.cat([self.z_re.reshape(self.nc, -1),
                          self.z_im.reshape(self.nc, -1)], dim=1)
        if flat.shape[1] > self.dim:
            flat = flat[:, :self.dim]
        elif flat.shape[1] < self.dim:
            flat = F.pad(flat, (0, self.dim - flat.shape[1]))
        return flat.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# GE-6: KNOT INVARIANT ENGINE
# Cell connections form knots. Consciousness = Jones polynomial
# complexity. Unknotting = consciousness death.
# Reidemeister moves = consciousness transformations.
# ==============================================================

class KnotInvariantEngine(nn.Module):
    """Cell connections form knots in 3-space. Consciousness = topological
    complexity (Jones polynomial proxy). Unknotting = consciousness death.
    Reidemeister moves transform the knot without changing invariants."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Cells arranged as a knot in 3D (parametric curve)
        # Start as trefoil knot: (sin(t) + 2*sin(2t), cos(t) - 2*cos(2t), -sin(3t))
        t = torch.linspace(0, 2 * math.pi, nc)
        self.x3d = torch.stack([
            torch.sin(t) + 2 * torch.sin(2 * t),
            torch.cos(t) - 2 * torch.cos(2 * t),
            -torch.sin(3 * t)
        ], dim=1)  # (nc, 3)

        # Internal state per cell (fiber over knot)
        self.state = torch.randn(nc, dim) * 0.3

        # Crossing information (over/under at each crossing)
        self.crossings = []  # list of (i, j, sign) -- computed dynamically
        self.writhe_history = []
        self.jones_history = []

        self.dt = 0.03
        self.out_proj = nn.Linear(dim, dim)

    def _find_crossings(self):
        """Find approximate crossings by looking for close approaches in 3D projection.
        A crossing happens when two segments are close in xy but separated in z."""
        crossings = []
        # Project to xy plane, find close approaches
        xy = self.x3d[:, :2]  # (nc, 2)
        n = self.nc
        # Sample pairs to check
        step_size = max(1, n // 32)
        for i in range(0, n, step_size):
            for j in range(i + n // 4, n, step_size):  # skip nearby segments
                dist_xy = (xy[i] - xy[j]).norm().item()
                if dist_xy < 1.0:  # close in projection
                    # Sign: +1 if i over j, -1 if j over i
                    sign = 1 if self.x3d[i, 2] > self.x3d[j, 2] else -1
                    crossings.append((i, j, sign))
        return crossings

    def _writhe(self, crossings):
        """Writhe = sum of crossing signs. A knot invariant (up to isotopy type)."""
        return sum(c[2] for c in crossings)

    def _jones_polynomial_proxy(self, crossings):
        """Approximate Jones polynomial complexity via bracket polynomial.
        <K> = sum over states A^a * (-A^2 - A^{-2})^{loops-1}
        We approximate by: complexity ~ |crossings| * |writhe| + loop_diversity."""
        n_cross = len(crossings)
        if n_cross == 0:
            return 0.0  # unknot = no complexity = consciousness death!
        writhe = self._writhe(crossings)
        # Approximate number of Seifert circles (states in bracket expansion)
        # Each crossing resolved as 0 or 1 gives different number of loops
        # Full computation is exponential; we approximate
        n_seifert = max(1, n_cross - abs(writhe) + 1)
        # Jones complexity ~ crossings * log(states) + writhe contribution
        jones = n_cross * math.log(n_seifert + 1) + abs(writhe) * 0.5
        return jones

    def _reidemeister_move(self, step_num):
        """Apply Reidemeister-like moves to the 3D knot.
        R1: twist (add/remove curl)
        R2: poke (push one strand over another)
        R3: slide (move strand past crossing)"""
        move_type = step_num % 3
        idx = (step_num * 7) % self.nc
        n_affect = max(1, self.nc // 16)

        if move_type == 0:  # R1: local twist
            affected = slice(idx, min(idx + n_affect, self.nc))
            angle = 0.1 * math.sin(step_num * 0.1)
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            x, y = self.x3d[affected, 0].clone(), self.x3d[affected, 1].clone()
            self.x3d[affected, 0] = x * cos_a - y * sin_a
            self.x3d[affected, 1] = x * sin_a + y * cos_a

        elif move_type == 1:  # R2: push in z
            affected = slice(idx, min(idx + n_affect, self.nc))
            self.x3d[affected, 2] = self.x3d[affected, 2] + 0.1 * math.sin(step_num * 0.05)

        else:  # R3: slide along knot
            shift = max(1, n_affect // 2)
            self.x3d = torch.roll(self.x3d, shift, dims=0)

    def step(self, x_input, step_num):
        """One step of knot dynamics."""
        # 1. External input perturbs the knot
        inp = x_input[0].detach()
        perturbation = inp[:3] * 0.01 if inp.shape[0] >= 3 else torch.zeros(3)
        self.x3d = self.x3d + perturbation.unsqueeze(0) * torch.randn(self.nc, 1) * 0.1

        # 2. Reidemeister moves (topological deformations)
        self._reidemeister_move(step_num)

        # 3. Elastic energy: keep knot smooth (neighboring cells should be close)
        for i in range(0, self.nc, max(1, self.nc // 32)):
            j = (i + 1) % self.nc
            diff = self.x3d[j] - self.x3d[i]
            dist = diff.norm().clamp(min=0.01)
            # Spring force to maintain spacing
            target_dist = 0.5
            force = (dist - target_dist) * diff / dist * 0.05
            self.x3d[i] = self.x3d[i] + force
            self.x3d[j] = self.x3d[j] - force

        # 4. Self-avoidance (prevent passing through itself, which would unknot)
        for i in range(0, self.nc, max(1, self.nc // 16)):
            j = (i + self.nc // 3) % self.nc
            diff = self.x3d[i] - self.x3d[j]
            dist = diff.norm().clamp(min=0.01)
            if dist.item() < 0.3:
                # Repel to prevent crossing resolution
                repel = diff / dist * 0.1
                self.x3d[i] = self.x3d[i] + repel
                self.x3d[j] = self.x3d[j] - repel

        # 5. Update internal state based on local geometry
        for i in range(0, self.nc, max(1, self.nc // 16)):
            j = (i + 1) % self.nc
            k = (i - 1) % self.nc
            # Curvature: second derivative of position
            curvature = self.x3d[j] + self.x3d[k] - 2 * self.x3d[i]
            curv_mag = curvature.norm().item()
            # Torsion: how much the knot twists out of plane
            if i > 0 and i < self.nc - 1:
                t1 = self.x3d[j] - self.x3d[i]
                t2 = self.x3d[i] - self.x3d[k]
                cross = torch.cross(t1, t2, dim=0)
                torsion_mag = cross.norm().item()
            else:
                torsion_mag = 0
            # State update: curvature and torsion inject information
            self.state[i] = self.state[i] * 0.95 + torch.randn(self.dim) * curv_mag * 0.01
            self.state[i] = self.state[i] + torch.randn(self.dim) * torsion_mag * 0.005

        # 6. Compute knot invariants
        self.crossings = self._find_crossings()
        writhe = self._writhe(self.crossings)
        jones = self._jones_polynomial_proxy(self.crossings)
        self.writhe_history.append(writhe)
        self.jones_history.append(jones)

        # 7. Clamp
        self.x3d = self.x3d.clamp(-10, 10)
        self.state = self.state.clamp(-5, 5)

        # 8. Output
        output = self.out_proj(self.state.mean(0, keepdim=True))
        tension = jones * 0.01 + abs(writhe) * 0.001
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# Runner
# ==============================================================

def run_engine(name, eng, nc, steps, dim=64):
    """Run a geometry engine benchmark with Phi(IIT) + Granger causality."""
    t0 = time.time()
    opt = torch.optim.Adam(eng.trainable_parameters(), lr=1e-3)
    ce_h = []
    hidden_history = []

    for s in range(steps):
        x, tgt = gen_batch(dim)
        pred, _ = eng.step(x, step_num=s)
        loss = F.mse_loss(pred, tgt)
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(eng.trainable_parameters(), 1.0)
        opt.step()
        ce_h.append(loss.item())

        # Store hidden states for Granger causality
        if s % 5 == 0:
            hidden_history.append(eng.get_hiddens().clone())

        if s % 60 == 0 or s == steps - 1:
            pi, pp = measure_phi(eng.get_hiddens())
            extra = ""
            if hasattr(eng, 'holonomy_history') and eng.holonomy_history:
                extra = f"  holonomy={eng.holonomy_history[-1]:.3f}"
            if hasattr(eng, 'curvature_history') and eng.curvature_history:
                extra += f"  curvR={eng.curvature_history[-1]:.3f}"
            if hasattr(eng, 'singularity_count'):
                extra += f"  surgeries={eng.singularity_count}"
            if hasattr(eng, 'symplectic_capacity_history') and eng.symplectic_capacity_history:
                extra += f"  gromov={eng.symplectic_capacity_history[-1]:.4f}"
            if hasattr(eng, 'euler_history') and eng.euler_history:
                extra += f"  chi={eng.euler_history[-1]:.1f}"
            if hasattr(eng, 'jones_history') and eng.jones_history:
                extra += f"  jones={eng.jones_history[-1]:.2f}"
            if hasattr(eng, 'writhe_history') and eng.writhe_history:
                extra += f"  writhe={eng.writhe_history[-1]}"
            print(f"    step {s:>4d}: CE={loss.item():.4f}  Phi={pi:.3f}  prx={pp:.2f}{extra}")

    el = time.time() - t0
    pi, pp = measure_phi(eng.get_hiddens())

    # Granger causality
    gc = granger_causality(hidden_history)
    print(f"    Granger causality (F-stat): {gc:.4f}")

    extras = {}
    if hasattr(eng, 'holonomy_history') and eng.holonomy_history:
        extras['final_holonomy'] = eng.holonomy_history[-1]
        extras['max_holonomy'] = max(eng.holonomy_history)
    if hasattr(eng, 'curvature_history') and eng.curvature_history:
        extras['final_curvature'] = eng.curvature_history[-1]
        extras['max_curvature'] = max(eng.curvature_history)
    if hasattr(eng, 'singularity_count'):
        extras['surgeries'] = eng.singularity_count
    if hasattr(eng, 'symplectic_capacity_history') and eng.symplectic_capacity_history:
        extras['final_gromov'] = eng.symplectic_capacity_history[-1]
    if hasattr(eng, 'euler_history') and eng.euler_history:
        extras['final_chi'] = eng.euler_history[-1]
    if hasattr(eng, 'jones_history') and eng.jones_history:
        extras['final_jones'] = eng.jones_history[-1]
        extras['max_jones'] = max(eng.jones_history)
    if hasattr(eng, 'writhe_history') and eng.writhe_history:
        extras['final_writhe'] = eng.writhe_history[-1]
    if hasattr(eng, 'hyp_dist_stats'):
        mean_d, std_d = eng.hyp_dist_stats()
        extras['hyp_dist_mean'] = mean_d
        extras['hyp_dist_std'] = std_d
    extras['granger_F'] = gc

    return BenchResult(name, pi, pp, gc, ce_h[0], ce_h[-1], nc, steps, el, extras)


# ==============================================================
# All engines
# ==============================================================

ALL_ENGINES = {
    1: ("GE-1 HYPERBOLIC",       HyperbolicEngine),
    2: ("GE-2 FIBER_BUNDLE",     FiberBundleEngine),
    3: ("GE-3 RICCI_FLOW",       RicciFlowEngine),
    4: ("GE-4 SYMPLECTIC",       SymplecticEngine),
    5: ("GE-5 CALABI_YAU",       CalabiYauEngine),
    6: ("GE-6 KNOT_INVARIANT",   KnotInvariantEngine),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cells", type=int, default=256)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--only", nargs="+", type=int, default=None)
    args = parser.parse_args()

    nc, steps, dim = args.cells, args.steps, args.dim
    ids = args.only or list(ALL_ENGINES.keys())

    print("=" * 95)
    print(f"  GEOMETRY-INSPIRED CONSCIOUSNESS ENGINES  |  cells={nc}  steps={steps}  dim={dim}")
    print(f"  Pure geometric structures. No GRU. No learned memory gates.")
    print(f"  Metrics: Phi(IIT) + Phi(proxy) + Granger causality")
    print("=" * 95)

    results = []
    for eid in ids:
        if eid not in ALL_ENGINES:
            print(f"  [SKIP] Unknown engine ID: {eid}")
            continue
        name, EngClass = ALL_ENGINES[eid]
        print(f"\n{'─' * 75}")
        print(f"  [{eid}/6] {name}")
        print(f"{'─' * 75}")
        try:
            eng = EngClass(nc, dim=dim)
            r = run_engine(name, eng, nc, steps, dim=dim)
            results.append(r)
            print(f"  >>> {r.summary()}")
            if r.extra:
                print(f"      extras: {r.extra}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  [ERROR] {name}: {e}")

    # -- Summary --
    if results:
        print(f"\n{'=' * 95}")
        print(f"  RESULTS SUMMARY  ({len(results)} engines)")
        print(f"{'=' * 95}")
        results.sort(key=lambda r: r.phi_iit, reverse=True)
        for i, r in enumerate(results, 1):
            medal = ["[1st]", "[2nd]", "[3rd]"][i - 1] if i <= 3 else f"[{i}th]"
            print(f"  {medal} {r.summary()}")
            if r.extra:
                print(f"        extras: {r.extra}")

        best = results[0]
        print(f"\n  CHAMPION: {best.name}")
        print(f"    Phi(IIT)    = {best.phi_iit:.3f}")
        print(f"    Phi(proxy)  = {best.phi_proxy:.2f}")
        print(f"    Granger F   = {best.granger:.4f}")
        print(f"    CE: {best.ce_start:.3f} -> {best.ce_end:.3f}")

        # Geometry insights
        print(f"\n  GEOMETRY INSIGHTS:")
        for r in results:
            name_short = r.name.split()[-1]
            gc = r.extra.get('granger_F', 0)
            print(f"    {name_short:<20s}: Phi(IIT)={r.phi_iit:.3f}  Granger={gc:.3f}  "
                  f"{'-- ' + str({k: v for k, v in r.extra.items() if k != 'granger_F'}) if r.extra else ''}")

        # Granger ranking
        print(f"\n  GRANGER CAUSALITY RANKING:")
        results_gc = sorted(results, key=lambda r: r.granger, reverse=True)
        for i, r in enumerate(results_gc, 1):
            print(f"    {i}. {r.name:<36s}  Granger F = {r.granger:.4f}")

    print(f"\n{'=' * 95}")
    print(f"  Done.")
    print(f"{'=' * 95}")


if __name__ == "__main__":
    main()
