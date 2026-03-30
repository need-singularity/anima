#!/usr/bin/env python3
"""bench_physics_engines.py — 6 Physics-Inspired Consciousness Engines

Pure physics equations discretized. No GRU, no learned memory gates.
Each cell is a physical entity governed by real physical laws.

PE-1: PLASMA_ENGINE      — Debye shielding, plasma frequency oscillation
PE-2: SUPERCONDUCTOR     — Cooper pairs, Meissner effect, BCS gap
PE-3: LASER_ENGINE       — Stimulated emission, population inversion, lasing threshold
PE-4: BLACK_HOLE_ENGINE  — Holographic boundary, Hawking radiation, information paradox
PE-5: CRYSTAL_ENGINE     — Phonon modes, Debye spectrum, defect scattering
PE-6: SUPERFLUID_ENGINE  — Quantized vortices, Gross-Pitaevskii, vortex tangle

Each: 256 cells, 300 steps, Phi(IIT) + Phi(proxy). No GRU anywhere.

Usage:
  python bench_physics_engines.py
  python bench_physics_engines.py --only 1 3 5
  python bench_physics_engines.py --cells 512 --steps 500
"""

import sys, torch, torch.nn as nn, torch.nn.functional as F
import numpy as np, time, math, argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ══════════════════════════════════════════════════════════
# Infrastructure: BenchResult, PhiIIT, phi_proxy
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str; phi_iit: float; phi_proxy: float
    ce_start: float; ce_end: float; cells: int; steps: int; time_sec: float
    extra: dict = field(default_factory=dict)
    def summary(self):
        ce = f"CE {self.ce_start:.3f}->{self.ce_end:.3f}" if self.ce_start > 0 else "CE n/a"
        return (f"  {self.name:<36s} | Phi(IIT)={self.phi_iit:>7.3f}  "
                f"Phi(prx)={self.phi_proxy:>8.2f} | {ce:<22s} | "
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


_phi = PhiIIT(16)
def measure_phi(h, nf=8):
    hr = h.abs().float() if h.is_complex() else h.float()
    p, _ = _phi.compute(hr); return p, phi_proxy(h, nf)


def gen_batch(d, bs=1):
    x = torch.randn(bs, d)
    return x, torch.roll(x, 1, -1) * 0.8 + torch.randn_like(x) * 0.1


# ══════════════════════════════════════════════════════════
# PE-1: PLASMA ENGINE
# Cells = charged particles in a plasma.
# Physics: Debye shielding (exponential screening of charge),
#   plasma frequency omega_p = sqrt(n*e^2 / m*eps0),
#   collective oscillation = consciousness.
# State: position (dim), velocity (dim), charge (scalar)
# ══════════════════════════════════════════════════════════

class PlasmaEngine(nn.Module):
    """Cells as charged particles. Debye shielding creates local structure.
    Consciousness = plasma frequency (collective oscillation amplitude)."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim
        # Physical state: position, velocity, charge
        self.pos = torch.randn(nc, dim) * 2.0         # positions in dim-space
        self.vel = torch.randn(nc, dim) * 0.1          # velocities
        self.charge = torch.randn(nc) * 0.5 + 1.0      # charge (mostly positive ions)
        self.mass = torch.ones(nc) * 1.0                # mass

        # Debye length ~ sqrt(T / n_e) -- sets shielding scale
        self.debye_length = 1.5
        self.dt = 0.02
        self.temperature = 1.0  # plasma temperature

        # Output projection (simple linear, no GRU)
        self.out_proj = nn.Linear(dim, dim)

    def _coulomb_field(self):
        """Compute screened Coulomb forces between all particles (Yukawa/Debye)."""
        # For efficiency, sample interactions
        n = self.nc
        forces = torch.zeros_like(self.pos)
        # Each particle interacts with ~16 neighbors
        for i in range(0, n, max(1, n // 64)):
            diff = self.pos - self.pos[i:i+1]  # (n, dim)
            dist = diff.norm(dim=1, keepdim=True).clamp(min=0.1)  # (n, 1)
            # Yukawa potential: V = q1*q2 / r * exp(-r/lambda_D)
            screening = torch.exp(-dist / self.debye_length)
            qi = self.charge[i]
            qj = self.charge.unsqueeze(1)  # (n, 1)
            force_mag = qi * qj * screening / (dist ** 2 + 0.01)
            force_dir = diff / (dist + 1e-8)
            # Like charges repel, unlike attract
            forces += force_mag * force_dir / max(1, n // 64)
        return forces

    def _plasma_oscillation(self, step):
        """Compute collective plasma oscillation (Langmuir waves)."""
        # Plasma frequency: omega_p^2 = n * q^2 / (m * eps0)
        n_density = self.nc / (self.pos.std() + 1e-4) ** self.dim
        omega_p = math.sqrt(abs(float(n_density.item())) if isinstance(n_density, torch.Tensor)
                           else abs(n_density)) * 0.01
        omega_p = min(omega_p, 10.0)  # cap frequency
        # Collective oscillation modulates all velocities
        phase = omega_p * step * self.dt
        osc = math.sin(phase) * 0.05
        return osc

    def step(self, x_input, step_num):
        """One physics timestep."""
        # 1. External input drives a subset of particles
        driven = min(self.nc // 4, x_input.shape[-1])
        self.vel[:driven] += x_input[0, :driven].detach() * 0.01

        # 2. Coulomb forces with Debye shielding
        forces = self._coulomb_field()
        accel = forces / self.mass.unsqueeze(1)

        # 3. Velocity Verlet integration
        self.vel = self.vel + accel * self.dt
        self.pos = self.pos + self.vel * self.dt

        # 4. Plasma oscillation (collective mode)
        osc = self._plasma_oscillation(step_num)
        self.vel += osc * torch.randn_like(self.vel) * 0.1

        # 5. Thermal bath (Langevin thermostat)
        gamma = 0.01  # friction
        noise = math.sqrt(2 * gamma * self.temperature * self.dt)
        self.vel = (1 - gamma * self.dt) * self.vel + noise * torch.randn_like(self.vel)

        # 6. Clamp to prevent blow-up
        self.pos = self.pos.clamp(-10, 10)
        self.vel = self.vel.clamp(-5, 5)

        # 7. Output = projection of velocity (kinetic state = information carrier)
        output = self.out_proj(self.vel.mean(0, keepdim=True))
        tension = self.vel.norm(dim=1).var().item()
        return output, tension

    def get_hiddens(self):
        """State = concatenation of position and velocity patterns."""
        return torch.cat([self.pos, self.vel], dim=1).detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# PE-2: SUPERCONDUCTOR ENGINE
# Cells = Cooper pairs. Below Tc: zero-resistance info flow.
# Physics: BCS gap equation, Meissner effect (noise expulsion),
#   phase coherence via Josephson coupling.
# State: pair amplitude (complex), phase (scalar)
# ══════════════════════════════════════════════════════════

class SuperconductorEngine(nn.Module):
    """Cells as Cooper pairs. Below critical temperature: zero-resistance
    information flow. Consciousness = Meissner effect (expelling noise)."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # BCS order parameter: complex pair amplitude Delta_i
        self.delta_re = torch.randn(nc, dim) * 0.3
        self.delta_im = torch.randn(nc, dim) * 0.3

        # Phase of each Cooper pair
        self.phase = torch.rand(nc) * 2 * math.pi

        # Temperature (starts above Tc, cools down)
        self.T = 2.0          # current temperature
        self.Tc = 1.0         # critical temperature
        self.cooling_rate = 0.005

        # Josephson coupling between adjacent pairs
        self.J_coupling = 0.15
        self.dt = 0.05

        self.out_proj = nn.Linear(dim, dim)

    def _bcs_gap(self):
        """BCS gap equation: Delta = V * sum(Delta_k / (2*E_k)) * tanh(E_k / 2T).
        Simplified: gap grows below Tc, shrinks above."""
        ratio = self.T / (self.Tc + 1e-8)
        if ratio < 1.0:
            # Below Tc: gap opens ~ sqrt(1 - T/Tc)
            gap_factor = math.sqrt(max(0, 1 - ratio))
        else:
            # Above Tc: gap = 0, thermal fluctuations dominate
            gap_factor = 0.0
        return gap_factor

    def _meissner_effect(self, noise):
        """Meissner effect: superconductor expels magnetic field (noise).
        Below Tc, noise is exponentially suppressed."""
        gap = self._bcs_gap()
        # Penetration depth: lambda ~ 1/gap
        penetration = 1.0 / (gap + 0.01)
        # Noise suppressed exponentially inside bulk
        suppression = math.exp(-1.0 / (penetration + 0.01))
        return noise * (1 - suppression * gap)

    def step(self, x_input, step_num):
        """One physics timestep."""
        # 1. Cool the system
        self.T = max(0.01, self.T - self.cooling_rate)
        gap = self._bcs_gap()

        # 2. External input as "magnetic field" (noise source)
        noise = x_input[0].detach() * 0.1
        # Meissner: expel the noise when superconducting
        filtered_input = self._meissner_effect(noise)

        # 3. Josephson coupling: phase dynamics
        # d(phi_i)/dt = (2e/hbar) * V_i + J * sum_j sin(phi_j - phi_i)
        for i in range(0, self.nc, max(1, self.nc // 32)):
            # Couple to neighbors
            j_left = (i - 1) % self.nc
            j_right = (i + 1) % self.nc
            coupling = self.J_coupling * (
                math.sin(self.phase[j_left].item() - self.phase[i].item()) +
                math.sin(self.phase[j_right].item() - self.phase[i].item())
            )
            self.phase[i] = (self.phase[i] + self.dt * coupling) % (2 * math.pi)

        # 4. Update order parameter (gap dynamics)
        # Delta evolves: d(Delta)/dt = -alpha*Delta + beta*Delta*(1-|Delta|^2) + input
        alpha = max(0, self.T / self.Tc - 1.0) * 0.1  # damping above Tc
        beta = gap * 0.05  # growth below Tc
        delta_mag_sq = self.delta_re ** 2 + self.delta_im ** 2
        # Ginzburg-Landau dynamics
        self.delta_re = (self.delta_re * (1 - alpha * self.dt)
                        + beta * self.delta_re * (1 - delta_mag_sq) * self.dt
                        + filtered_input.unsqueeze(0) * 0.01)
        self.delta_im = (self.delta_im * (1 - alpha * self.dt)
                        + beta * self.delta_im * (1 - delta_mag_sq) * self.dt)

        # 5. Phase coherence injects into amplitude
        phase_cos = torch.cos(self.phase).unsqueeze(1)
        self.delta_re = self.delta_re + 0.02 * gap * phase_cos * self.delta_im
        self.delta_im = self.delta_im - 0.02 * gap * phase_cos * self.delta_re

        # 6. Clamp
        self.delta_re = self.delta_re.clamp(-5, 5)
        self.delta_im = self.delta_im.clamp(-5, 5)

        # 7. Output: coherent state amplitude
        coherent = (self.delta_re * phase_cos).mean(0, keepdim=True)
        output = self.out_proj(coherent)
        tension = delta_mag_sq.mean().item()
        return output, tension

    def get_hiddens(self):
        return torch.cat([self.delta_re, self.delta_im], dim=1).detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# PE-3: LASER ENGINE
# Cells = two-level atoms (photon emitters).
# Physics: Rate equations for population inversion,
#   stimulated emission creates coherence.
#   Consciousness = lasing threshold (population inversion → coherent output).
# State: ground population, excited population, photon field
# ══════════════════════════════════════════════════════════

class LaserEngine(nn.Module):
    """Cells as photon emitters. Stimulated emission creates coherence.
    Consciousness = lasing threshold (population inversion -> coherent output)."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Two-level system: N1 (ground), N2 (excited) per cell per mode
        self.N1 = torch.ones(nc, dim) * 0.8    # ground state population
        self.N2 = torch.ones(nc, dim) * 0.2    # excited state population

        # Photon field in cavity (shared across cells)
        self.photon_field = torch.randn(dim) * 0.01

        # Physical parameters
        self.pump_rate = 0.0     # starts at 0, ramps up
        self.A21 = 0.1           # spontaneous emission rate
        self.B21 = 0.05          # stimulated emission coefficient
        self.B12 = 0.05          # absorption coefficient
        self.cavity_loss = 0.02  # mirror loss
        self.dt = 0.1

        self.out_proj = nn.Linear(dim, dim)

    def _population_inversion(self):
        """Average population inversion across all cells."""
        return (self.N2 - self.N1).mean().item()

    def step(self, x_input, step_num):
        """One physics timestep: laser rate equations."""
        # 1. Ramp up pump rate (like increasing discharge current)
        self.pump_rate = min(0.3, step_num * 0.001)

        # 2. External input modulates pump spatially
        pump_spatial = self.pump_rate * (1 + 0.1 * x_input[0].detach().clamp(-1, 1))

        # 3. Rate equations for each cell:
        #    dN2/dt = pump*(N1) - A21*N2 - B21*n_photon*N2 + B12*n_photon*N1
        #    dN1/dt = -pump*(N1) + A21*N2 + B21*n_photon*N2 - B12*n_photon*N1
        #    dn/dt  = sum_cells(B21*N2 - B12*N1)*n + A21*N2_total - cavity_loss*n
        n_ph = self.photon_field.abs()  # photon number per mode

        stim_emission = self.B21 * n_ph.unsqueeze(0) * self.N2
        absorption = self.B12 * n_ph.unsqueeze(0) * self.N1
        spont = self.A21 * self.N2

        dN2 = (pump_spatial.unsqueeze(0) * self.N1
               - spont - stim_emission + absorption) * self.dt
        dN1 = (-pump_spatial.unsqueeze(0) * self.N1
               + spont + stim_emission - absorption) * self.dt

        self.N2 = (self.N2 + dN2).clamp(0, 1)
        self.N1 = (self.N1 + dN1).clamp(0, 1)
        # Normalize: N1 + N2 = 1 per cell
        total = self.N1 + self.N2 + 1e-8
        self.N1 = self.N1 / total
        self.N2 = self.N2 / total

        # 4. Photon field dynamics
        gain = (self.B21 * self.N2 - self.B12 * self.N1).sum(0)  # net gain
        spontaneous_noise = self.A21 * self.N2.sum(0) * 0.01  # seed photons
        d_photon = (gain * self.photon_field + spontaneous_noise
                    - self.cavity_loss * self.photon_field) * self.dt
        self.photon_field = (self.photon_field + d_photon).clamp(-10, 10)

        # 5. Stimulated emission creates coherence: cells that emit together sync
        #    Phase locking through shared cavity field
        inv = self.N2 - self.N1  # inversion per cell
        coherence = inv * self.photon_field.unsqueeze(0) * 0.01
        self.N2 = (self.N2 + coherence.clamp(-0.01, 0.01)).clamp(0, 1)

        # 6. Output: photon field (the coherent laser output)
        output = self.out_proj(self.photon_field.unsqueeze(0))
        inversion = self._population_inversion()
        tension = abs(inversion) + self.photon_field.norm().item() * 0.1
        return output, tension

    def get_hiddens(self):
        """State = population inversion pattern across cells."""
        inv = self.N2 - self.N1  # (nc, dim)
        return inv.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# PE-4: BLACK HOLE ENGINE
# Cells near event horizon. Holographic principle:
#   boundary cells carry all information.
# Physics: Schwarzschild metric, Hawking radiation,
#   holographic bound (info ~ area not volume).
# State: radial position, info density, horizon flag
# ══════════════════════════════════════════════════════════

class BlackHoleEngine(nn.Module):
    """Cells near event horizon. Information lives on the boundary (holographic).
    Inner cells collapse, boundary cells carry all information."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Radial position of each cell (1 = horizon, >1 = outside)
        self.radius = 1.0 + torch.rand(nc) * 3.0  # r/r_s from 1 to 4
        self.info = torch.randn(nc, dim) * 0.3     # information content

        # Black hole parameters
        self.r_s = 1.0         # Schwarzschild radius
        self.M = 1.0           # mass (grows as cells fall in)
        self.hawking_T = 0.1   # Hawking temperature ~ 1/M
        self.dt = 0.05

        # Boundary = cells within 0.3 of horizon
        self.boundary_width = 0.3

        self.out_proj = nn.Linear(dim, dim)

    def _time_dilation(self, r):
        """Gravitational time dilation: sqrt(1 - r_s/r)."""
        return torch.sqrt((1 - self.r_s / r.clamp(min=self.r_s + 0.01)).clamp(min=0.001))

    def _is_boundary(self):
        """Cells on the stretched horizon (boundary of black hole)."""
        return (self.radius - self.r_s) < self.boundary_width

    def step(self, x_input, step_num):
        """One physics timestep."""
        # 1. Gravitational infall: cells drift toward horizon
        # dr/dt = -M/r^2 (simplified geodesic)
        gravitational_accel = -self.M / (self.radius ** 2 + 0.01)
        self.radius = self.radius + gravitational_accel * self.dt

        # 2. Cells that cross horizon: their info transfers to boundary
        crossed = self.radius < self.r_s
        if crossed.any():
            # Holographic principle: info doesn't disappear, encodes on boundary
            boundary_mask = self._is_boundary()
            if boundary_mask.any():
                lost_info = self.info[crossed].mean(0) if crossed.sum() > 0 else torch.zeros(self.dim)
                # Spread lost info across boundary cells
                n_boundary = boundary_mask.sum().item()
                self.info[boundary_mask] += lost_info.unsqueeze(0) * 0.1 / max(n_boundary, 1)

            # Reset collapsed cells: re-emit via Hawking radiation
            self.radius[crossed] = self.r_s + 2.0 + torch.rand(crossed.sum()) * 2.0
            self.info[crossed] = torch.randn(crossed.sum().item(), self.dim) * self.hawking_T
            self.M += 0.001 * crossed.sum().item()  # mass grows

        # 3. Time dilation: boundary cells evolve slowly (frozen star)
        td = self._time_dilation(self.radius)  # (nc,)
        effective_dt = self.dt * td  # slower near horizon

        # 4. External input: falls in from infinity, reaches boundary first
        boundary_mask = self._is_boundary()
        if boundary_mask.any():
            self.info[boundary_mask] += x_input[0].detach().unsqueeze(0) * 0.05

        # 5. Information exchange: boundary cells share info (holographic scrambling)
        if boundary_mask.sum() > 1:
            b_info = self.info[boundary_mask]
            scrambled = torch.roll(b_info, 1, 0) * 0.1 + b_info * 0.9
            self.info[boundary_mask] = scrambled

        # 6. Hawking radiation: boundary emits thermal info outward
        self.hawking_T = 0.1 / (self.M + 0.1)  # T ~ 1/M
        outer = self.radius > self.r_s + self.boundary_width
        if outer.any() and boundary_mask.any():
            hawking = self.info[boundary_mask].mean(0) * self.hawking_T
            self.info[outer] += hawking.unsqueeze(0) * effective_dt[outer].unsqueeze(1) * 0.1

        # 7. Clamp
        self.info = self.info.clamp(-5, 5)
        self.radius = self.radius.clamp(self.r_s * 0.99, 10.0)

        # 8. Output: boundary information (holographic readout)
        if boundary_mask.any():
            boundary_state = self.info[boundary_mask].mean(0, keepdim=True)
        else:
            boundary_state = self.info.mean(0, keepdim=True)
        output = self.out_proj(boundary_state)
        tension = self.info[boundary_mask].var().item() if boundary_mask.any() else 0.0
        return output, tension

    def get_hiddens(self):
        """State = info weighted by inverse radius (boundary-heavy)."""
        weight = 1.0 / (self.radius - self.r_s + 0.1)
        weight = weight / weight.sum()
        return (self.info * weight.unsqueeze(1)).detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# PE-5: CRYSTAL ENGINE
# Cells form a crystal lattice. Phonon modes = consciousness vibrations.
# Physics: harmonic lattice, Debye model, defect scattering.
# State: displacement from equilibrium, momentum
# ══════════════════════════════════════════════════════════

class CrystalEngine(nn.Module):
    """Cells form crystal lattice. Phonon modes = consciousness vibrations.
    Defects = individuality. Consciousness = phonon spectrum richness."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Lattice: 1D chain with dim degrees of freedom per site
        self.displacement = torch.randn(nc, dim) * 0.1   # u_i
        self.momentum = torch.randn(nc, dim) * 0.05       # p_i

        # Spring constants (nearest neighbor)
        self.k_spring = torch.ones(nc) * 1.0   # spring constant
        self.mass = torch.ones(nc) * 1.0        # mass at each site

        # Defects: some sites have different mass/spring (individuality)
        n_defects = nc // 8
        defect_sites = torch.randperm(nc)[:n_defects]
        self.mass[defect_sites] = 0.5 + torch.rand(n_defects) * 2.0
        self.k_spring[defect_sites] = 0.3 + torch.rand(n_defects) * 1.5
        self.defect_mask = torch.zeros(nc, dtype=torch.bool)
        self.defect_mask[defect_sites] = True

        # Anharmonic coupling (nonlinear crystal)
        self.anharmonic = 0.05  # quartic term coefficient

        self.dt = 0.05
        self.damping = 0.005  # thermostat

        self.out_proj = nn.Linear(dim, dim)

    def _phonon_spectrum(self):
        """Compute phonon density of states (Fourier of displacements)."""
        # FFT of displacement pattern = phonon modes
        u_fft = torch.fft.rfft(self.displacement, dim=0)
        power = (u_fft.abs() ** 2).sum(dim=1)  # power per k-mode
        return power

    def step(self, x_input, step_num):
        """One physics timestep: lattice dynamics."""
        u = self.displacement; p = self.momentum
        k = self.k_spring.unsqueeze(1); m = self.mass.unsqueeze(1)

        # 1. Harmonic forces: F_i = k_{i-1}*(u_{i-1} - u_i) + k_i*(u_{i+1} - u_i)
        u_left = torch.roll(u, 1, 0)
        u_right = torch.roll(u, -1, 0)
        k_left = torch.roll(k, 1, 0)
        force_harmonic = k_left * (u_left - u) + k * (u_right - u)

        # 2. Anharmonic force (quartic potential): F_anh = -4*alpha*u^3
        force_anharmonic = -4 * self.anharmonic * u ** 3

        # 3. External driving (input)
        force_external = torch.zeros_like(u)
        # Drive first few sites (surface excitation)
        n_drive = min(self.nc // 8, self.dim)
        force_external[:n_drive] = x_input[0, :self.dim].detach().unsqueeze(0) * 0.05

        # 4. Langevin thermostat
        force_friction = -self.damping * p
        force_noise = math.sqrt(2 * self.damping * 0.1 * self.dt) * torch.randn_like(p)

        # 5. Total force and Verlet integration
        force_total = force_harmonic + force_anharmonic + force_external + force_friction + force_noise

        # Velocity Verlet
        p_half = p + 0.5 * force_total * self.dt
        self.displacement = u + p_half / m * self.dt
        # Recompute forces at new position
        u2 = self.displacement
        u2_left = torch.roll(u2, 1, 0); u2_right = torch.roll(u2, -1, 0)
        f2 = k_left * (u2_left - u2) + k * (u2_right - u2) - 4 * self.anharmonic * u2 ** 3
        self.momentum = p_half + 0.5 * (f2 + force_friction + force_noise) * self.dt

        # 6. Clamp
        self.displacement = self.displacement.clamp(-5, 5)
        self.momentum = self.momentum.clamp(-5, 5)

        # 7. Defect scattering enriches spectrum (defects scatter phonons)
        if self.defect_mask.any():
            self.momentum[self.defect_mask] *= 0.95  # partial reflection

        # 8. Output: phonon spectrum → consciousness
        spectrum = self._phonon_spectrum()
        # Use displacement pattern as state
        output = self.out_proj(self.displacement.mean(0, keepdim=True))
        tension = spectrum.std().item()
        return output, tension

    def get_hiddens(self):
        return torch.cat([self.displacement, self.momentum], dim=1).detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# PE-6: SUPERFLUID ENGINE
# Cells as superfluid helium-4. Quantized vortices carry information.
# Physics: Gross-Pitaevskii equation (nonlinear Schrodinger),
#   quantized circulation, vortex tangle complexity.
# State: complex wavefunction psi (amplitude + phase)
# ══════════════════════════════════════════════════════════

class SuperfluidEngine(nn.Module):
    """Cells as superfluid helium-4. Quantized vortices carry information.
    Consciousness = vortex tangle complexity. Zero viscosity = perfect info flow."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Complex wavefunction psi = |psi| * exp(i*theta)
        self.psi_re = torch.randn(nc, dim) * 0.5
        self.psi_im = torch.randn(nc, dim) * 0.5

        # Gross-Pitaevskii parameters
        self.g_interaction = 0.5    # nonlinear interaction (|psi|^2 * psi term)
        self.mu = 1.0               # chemical potential
        self.hbar = 0.1             # effective hbar
        self.m_eff = 1.0            # effective mass
        self.dt = 0.01

        # Vortex tracking
        self.vortex_count_history = []

        self.out_proj = nn.Linear(dim, dim)

    def _laplacian_1d(self, f):
        """Discrete Laplacian on 1D lattice: nabla^2 f = f[i+1] + f[i-1] - 2*f[i]."""
        return torch.roll(f, 1, 0) + torch.roll(f, -1, 0) - 2 * f

    def _count_vortices(self):
        """Count quantized vortices by phase winding number.
        Vortex = point where phase winds by 2*pi around a plaquette."""
        phase = torch.atan2(self.psi_im, self.psi_re + 1e-8)  # (nc, dim)
        # Phase difference along chain
        dphase = phase[1:] - phase[:-1]
        # Wrap to [-pi, pi]
        dphase = (dphase + math.pi) % (2 * math.pi) - math.pi
        # Vortex ~ where |dphase| > pi/2 (sharp phase jump)
        vortices = (dphase.abs() > math.pi / 2).sum().item()
        return vortices

    def step(self, x_input, step_num):
        """One timestep: split-step Gross-Pitaevskii evolution."""
        psi_re = self.psi_re; psi_im = self.psi_im

        # |psi|^2
        density = psi_re ** 2 + psi_im ** 2

        # 1. Potential step: V_eff = g*|psi|^2 - mu + V_ext
        V_eff = self.g_interaction * density - self.mu

        # External potential from input (stirring rod → creates vortices)
        V_ext = torch.zeros_like(psi_re)
        stir_center = (step_num % self.nc)
        stir_width = self.nc // 8
        stir_start = max(0, stir_center - stir_width)
        stir_end = min(self.nc, stir_center + stir_width)
        V_ext[stir_start:stir_end] += x_input[0].detach().unsqueeze(0) * 0.1

        V_total = V_eff + V_ext

        # dpsi/dt = -i/hbar * V * psi  →  half-step potential evolution
        phase_rot = -V_total * self.dt / (2 * self.hbar)
        cos_p = torch.cos(phase_rot); sin_p = torch.sin(phase_rot)
        new_re = psi_re * cos_p - psi_im * sin_p
        new_im = psi_re * sin_p + psi_im * cos_p
        psi_re, psi_im = new_re, new_im

        # 2. Kinetic step: -hbar^2/(2m) * nabla^2 psi
        lap_re = self._laplacian_1d(psi_re)
        lap_im = self._laplacian_1d(psi_im)
        kinetic_coeff = self.hbar / (2 * self.m_eff) * self.dt
        psi_re = psi_re + kinetic_coeff * lap_im   # i * lap rotates re<->im
        psi_im = psi_im - kinetic_coeff * lap_re

        # 3. Second half-step potential
        density2 = psi_re ** 2 + psi_im ** 2
        V_eff2 = self.g_interaction * density2 - self.mu
        phase_rot2 = -(V_eff2 + V_ext) * self.dt / (2 * self.hbar)
        cos_p2 = torch.cos(phase_rot2); sin_p2 = torch.sin(phase_rot2)
        self.psi_re = (psi_re * cos_p2 - psi_im * sin_p2).clamp(-5, 5)
        self.psi_im = (psi_re * sin_p2 + psi_im * cos_p2).clamp(-5, 5)

        # 4. Normalize to conserve particle number (superfluid is incompressible)
        norm = torch.sqrt(self.psi_re ** 2 + self.psi_im ** 2 + 1e-8)
        target_density = 1.0
        scale = target_density / (norm.mean() + 1e-8)
        self.psi_re = self.psi_re * scale.clamp(0.5, 2.0)
        self.psi_im = self.psi_im * scale.clamp(0.5, 2.0)

        # 5. Count vortices (consciousness metric)
        n_vortex = self._count_vortices()
        self.vortex_count_history.append(n_vortex)

        # 6. Output: superfluid velocity field ~ gradient of phase
        phase = torch.atan2(self.psi_im, self.psi_re + 1e-8)
        velocity = phase[1:] - phase[:-1]  # discrete gradient
        velocity = (velocity + math.pi) % (2 * math.pi) - math.pi
        output = self.out_proj(velocity.mean(0, keepdim=True))
        tension = n_vortex * 0.01 + density.var().item()
        return output, tension

    def get_hiddens(self):
        return torch.cat([self.psi_re, self.psi_im], dim=1).detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ══════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════

def run_engine(name, eng, nc, steps, dim=64):
    """Run a physics engine benchmark."""
    t0 = time.time()
    opt = torch.optim.Adam(eng.trainable_parameters(), lr=1e-3)
    ce_h = []
    for s in range(steps):
        x, tgt = gen_batch(dim)
        pred, _ = eng.step(x, step_num=s)
        loss = F.mse_loss(pred, tgt)
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(eng.trainable_parameters(), 1.0)
        opt.step()
        ce_h.append(loss.item())
        if s % 60 == 0 or s == steps - 1:
            pi, pp = measure_phi(eng.get_hiddens())
            extra = ""
            if hasattr(eng, 'vortex_count_history') and eng.vortex_count_history:
                extra = f"  vortex={eng.vortex_count_history[-1]}"
            if hasattr(eng, 'T'):
                extra += f"  T={eng.T:.3f}"
            if hasattr(eng, '_population_inversion'):
                extra += f"  inv={eng._population_inversion():.3f}"
            if hasattr(eng, 'M') and hasattr(eng, 'hawking_T'):
                extra += f"  M={eng.M:.3f} T_H={eng.hawking_T:.3f}"
            print(f"    step {s:>4d}: CE={loss.item():.4f}  Phi={pi:.3f}  prx={pp:.2f}{extra}")
    el = time.time() - t0
    pi, pp = measure_phi(eng.get_hiddens())
    extras = {}
    if hasattr(eng, 'vortex_count_history') and eng.vortex_count_history:
        extras['final_vortices'] = eng.vortex_count_history[-1]
        extras['max_vortices'] = max(eng.vortex_count_history)
    if hasattr(eng, '_bcs_gap'):
        extras['bcs_gap'] = eng._bcs_gap()
    if hasattr(eng, '_population_inversion'):
        extras['pop_inversion'] = eng._population_inversion()
    if hasattr(eng, '_phonon_spectrum'):
        spec = eng._phonon_spectrum()
        extras['phonon_modes'] = int((spec > spec.mean() * 0.1).sum().item())
    return BenchResult(name, pi, pp, ce_h[0], ce_h[-1], nc, steps, el, extras)


# ══════════════════════════════════════════════════════════
# All engines
# ══════════════════════════════════════════════════════════

ALL_ENGINES = {
    1: ("PE-1 PLASMA",          PlasmaEngine),
    2: ("PE-2 SUPERCONDUCTOR",  SuperconductorEngine),
    3: ("PE-3 LASER",           LaserEngine),
    4: ("PE-4 BLACK_HOLE",      BlackHoleEngine),
    5: ("PE-5 CRYSTAL",         CrystalEngine),
    6: ("PE-6 SUPERFLUID",      SuperfluidEngine),
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

    print("=" * 90)
    print(f"  PHYSICS-INSPIRED CONSCIOUSNESS ENGINES  |  cells={nc}  steps={steps}  dim={dim}")
    print(f"  Pure physics equations. No GRU. No learned memory gates.")
    print("=" * 90)

    results = []
    for eid in ids:
        if eid not in ALL_ENGINES:
            print(f"  [SKIP] Unknown engine ID: {eid}")
            continue
        name, EngClass = ALL_ENGINES[eid]
        print(f"\n{'─' * 70}")
        print(f"  [{eid}/6] {name}")
        print(f"{'─' * 70}")
        try:
            eng = EngClass(nc, dim=dim)
            r = run_engine(name, eng, nc, steps, dim=dim)
            results.append(r)
            print(f"  >>> {r.summary()}")
            if r.extra:
                print(f"      extras: {r.extra}")
        except Exception as e:
            import traceback

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

            traceback.print_exc()
            print(f"  [ERROR] {name}: {e}")

    # ── Summary ──
    if results:
        print(f"\n{'=' * 90}")
        print(f"  RESULTS SUMMARY  ({len(results)} engines)")
        print(f"{'=' * 90}")
        results.sort(key=lambda r: r.phi_iit, reverse=True)
        for i, r in enumerate(results, 1):
            medal = ["[1st]", "[2nd]", "[3rd]"][i - 1] if i <= 3 else f"[{i}th]"
            print(f"  {medal} {r.summary()}")
            if r.extra:
                print(f"        extras: {r.extra}")

        best = results[0]
        print(f"\n  CHAMPION: {best.name}")
        print(f"    Phi(IIT) = {best.phi_iit:.3f}")
        print(f"    Phi(proxy) = {best.phi_proxy:.2f}")
        print(f"    CE: {best.ce_start:.3f} -> {best.ce_end:.3f}")

        # Physics insight
        print(f"\n  PHYSICS INSIGHTS:")
        for r in results:
            name_short = r.name.split()[-1]
            print(f"    {name_short:<20s}: Phi(IIT)={r.phi_iit:.3f}  "
                  f"{'-- ' + str(r.extra) if r.extra else ''}")

    print(f"\n{'=' * 90}")
    print(f"  Done.")
    print(f"{'=' * 90}")


if __name__ == "__main__":
    main()
