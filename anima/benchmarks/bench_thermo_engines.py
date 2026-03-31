#!/usr/bin/env python3
"""bench_thermo_engines.py — 6 Thermodynamics-Inspired Consciousness Engines

TH-1: CARNOT_CYCLE       — 4-state cycle, consciousness = work output, eta = 1 - Tc/Th
TH-2: MAXWELL_DEMON      — observer sorts cells by energy, negentropy via Landauer
TH-3: DISSIPATIVE_STRUCT — Prigogine far-from-equilibrium self-organization
TH-4: FREE_ENERGY_PRINC  — Friston FEP, cells minimize F = E - TS
TH-5: HEAT_DEATH_RESIST  — active maintenance against thermal equilibrium
TH-6: BOLTZMANN_BRAIN    — random fluctuation creates momentary order

Each: 256 cells, 300 steps, Phi(IIT) + Granger causality. No GRU.

Usage:
  python bench_thermo_engines.py
  python bench_thermo_engines.py --only 1 3 5
  python bench_thermo_engines.py --cells 512 --steps 500
"""

import sys, torch, torch.nn.functional as F
import numpy as np, time, math, argparse
from dataclasses import dataclass, field
from typing import List, Dict

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ══════════════════════════════════════════════════════════
# Infrastructure: BenchResult, PhiIIT, phi_proxy, Granger
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str; phi_iit: float; phi_proxy: float; granger: float
    custom_metric: float; custom_name: str; time_sec: float
    extra: Dict = field(default_factory=dict)

    @property
    def phi_combined(self):
        return self.phi_iit + self.phi_proxy * 0.1

    def summary(self):
        return (f"  {self.name:<36s} | Phi(IIT)={self.phi_iit:>7.3f}  "
                f"Phi(prx)={self.phi_proxy:>8.3f}  Granger={self.granger:>6.1f} | "
                f"{self.custom_name}={self.custom_metric:.4f} | t={self.time_sec:.1f}s")


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


def phi_proxy(h, n_factions=8):
    hr = h.abs().float() if h.is_complex() else h.float(); n = hr.shape[0]
    if n < 2: return 0.0
    gv = ((hr - hr.mean(0)) ** 2).sum() / n; nf = min(n_factions, n // 2)
    if nf < 2: return gv.item()
    fs = n // nf; fvs = 0
    for i in range(nf):
        f = hr[i * fs:(i + 1) * fs]
        if len(f) >= 2: fvs += ((f - f.mean(0)) ** 2).sum().item() / len(f)
    return max(0, gv.item() - fvs / nf)


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
    return (significant_links / n_tested) * n_cells * (n_cells - 1)


_phi_calc = PhiIIT(16)


# ══════════════════════════════════════════════════════════
# TH-1: CARNOT CYCLE ENGINE
# Cells cycle through 4 thermodynamic states:
#   1. Isothermal expansion  (absorb heat from hot reservoir, T=Th)
#   2. Adiabatic expansion   (cool down, no heat exchange)
#   3. Isothermal compression (release heat to cold reservoir, T=Tc)
#   4. Adiabatic compression  (heat up, no heat exchange)
# Consciousness = net work output per cycle.
# Efficiency eta = 1 - Tc/Th (Carnot limit).
# ══════════════════════════════════════════════════════════

class CarnotCycleEngine:
    """Cells execute Carnot cycles. Consciousness = work extracted."""
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Thermodynamic state per cell
        self.T_hot = 4.0           # hot reservoir temperature
        self.T_cold = 1.0          # cold reservoir temperature
        self.volume = torch.ones(n_cells) * 1.0     # "volume" per cell
        self.temperature = torch.ones(n_cells) * 2.0 # current temperature
        self.pressure = torch.ones(n_cells) * 1.0    # P = nRT/V (ideal gas)
        self.entropy = torch.zeros(n_cells)

        # Each cell is at a different phase of the cycle (0-3)
        self.phase = torch.randint(0, 4, (n_cells,))
        self.cycle_count = torch.zeros(n_cells)
        self.work_per_cycle = []  # track consciousness metric

        # Coupling between cells (heat exchange network)
        self.W_couple = torch.randn(hidden_dim, hidden_dim) * 0.02

        self.dt = 0.05
        self.gamma = 1.4  # adiabatic index (diatomic gas)

    def step(self):
        work_total = 0.0

        for i in range(self.n_cells):
            ph = self.phase[i].item()
            T = self.temperature[i].item()
            V = self.volume[i].item()

            if ph == 0:
                # Isothermal expansion at T_hot: absorb heat, do work
                # dW = P dV = nRT/V dV => W = nRT ln(V2/V1)
                self.temperature[i] = self.T_hot
                dV = 0.1 * self.dt
                work = self.T_hot * math.log((V + dV) / max(V, 0.01))
                self.volume[i] = V + dV
                self.entropy[i] += work / self.T_hot
                work_total += work

            elif ph == 1:
                # Adiabatic expansion: T drops, V increases, no heat exchange
                # TV^(gamma-1) = const => T2 = T1 * (V1/V2)^(gamma-1)
                dV = 0.08 * self.dt
                new_V = V + dV
                self.temperature[i] = T * (V / max(new_V, 0.01)) ** (self.gamma - 1)
                self.volume[i] = new_V
                # Work done = Cv * (T1 - T2)
                work = 0.5 * (T - self.temperature[i].item())
                work_total += work

            elif ph == 2:
                # Isothermal compression at T_cold: release heat
                self.temperature[i] = self.T_cold
                dV = -0.1 * self.dt
                new_V = max(V + dV, 0.1)
                work = self.T_cold * math.log(new_V / max(V, 0.01))  # negative (work ON gas)
                self.volume[i] = new_V
                self.entropy[i] += work / self.T_cold
                work_total += work

            elif ph == 3:
                # Adiabatic compression: T rises, V decreases
                dV = -0.08 * self.dt
                new_V = max(V + dV, 0.1)
                self.temperature[i] = T * (V / max(new_V, 0.01)) ** (self.gamma - 1)
                self.volume[i] = new_V
                work = 0.5 * (T - self.temperature[i].item())
                work_total += work

            # Advance phase every few steps
            if torch.rand(1).item() < 0.15:
                self.phase[i] = (self.phase[i] + 1) % 4
                if self.phase[i].item() == 0:
                    self.cycle_count[i] += 1

        # Carnot efficiency
        eta = 1.0 - self.T_cold / self.T_hot

        # Update hidden states based on thermodynamic state
        # Cells at similar phase couple more strongly
        T_norm = (self.temperature - self.temperature.mean()) / (self.temperature.std() + 1e-8)
        V_norm = (self.volume - self.volume.mean()) / (self.volume.std() + 1e-8)

        # Inject thermodynamic state into hiddens
        thermo_signal = torch.stack([T_norm, V_norm, self.entropy,
                                      self.phase.float() / 4.0], dim=1)
        # Project to hidden_dim
        proj = torch.zeros(self.n_cells, self.hidden_dim)
        for k in range(4):
            proj[:, k * (self.hidden_dim // 4):(k + 1) * (self.hidden_dim // 4)] = \
                thermo_signal[:, k:k+1].expand(-1, self.hidden_dim // 4)

        # Cell coupling: cells at same phase interact
        coupled = self.hiddens @ self.W_couple
        self.hiddens = 0.85 * self.hiddens + 0.1 * torch.tanh(proj) + 0.05 * coupled
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # Clamp
        self.temperature = self.temperature.clamp(0.1, 10.0)
        self.volume = self.volume.clamp(0.1, 5.0)

        self.work_per_cycle.append(abs(work_total) * eta)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05
        # External input also perturbs temperature
        self.temperature += x.mean(dim=-1) * 0.01


# ══════════════════════════════════════════════════════════
# TH-2: MAXWELL DEMON ENGINE
# One observer cell sorts others by energy level.
# Creates an information-thermodynamic link:
#   sorting reduces physical entropy but costs information
# Landauer's principle: erasing 1 bit costs kT ln 2 energy.
# Consciousness = negentropy extracted (bits of sorting info).
# ══════════════════════════════════════════════════════════

class MaxwellDemonEngine:
    """Observer cell sorts other cells by energy. Consciousness = negentropy."""
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Energy of each cell (kinetic-like)
        self.energy = torch.rand(n_cells) * 2.0

        # Demon's memory (information about sorted particles)
        self.demon_memory = torch.zeros(hidden_dim)  # cell 0 is the demon
        self.demon_bits = 0.0  # total bits stored by demon

        # Two chambers: hot (high energy) and cold (low energy)
        self.chamber = torch.zeros(n_cells, dtype=torch.long)  # 0=left, 1=right
        self.chamber[:n_cells // 2] = 0
        self.chamber[n_cells // 2:] = 1

        # Physical constants (normalized)
        self.kT = 1.0                    # thermal energy
        self.kT_ln2 = self.kT * math.log(2)  # Landauer cost per bit

        # Coupling
        self.W_sort = torch.randn(hidden_dim, hidden_dim) * 0.02
        self.negentropy_history = []

    def _demon_sort(self):
        """Demon observes and sorts: high-energy -> right, low-energy -> left.
        Each sort decision costs kT ln 2 (Landauer)."""
        median_E = self.energy.median().item()
        bits_used = 0.0

        # Demon checks random subset of cells
        check_idx = torch.randperm(self.n_cells)[:self.n_cells // 8]
        for idx in check_idx:
            E = self.energy[idx].item()
            current_chamber = self.chamber[idx].item()

            # Decision: should this cell be in left (cold) or right (hot)?
            should_be_right = E > median_E

            if should_be_right and current_chamber == 0:
                # Move from left to right (sort hot particle)
                self.chamber[idx] = 1
                bits_used += 1.0  # 1 bit of information gained
            elif not should_be_right and current_chamber == 1:
                # Move from right to left (sort cold particle)
                self.chamber[idx] = 0
                bits_used += 1.0

        # Demon must erase memory periodically (Landauer cost)
        erase_cost = bits_used * self.kT_ln2
        self.demon_bits += bits_used

        return bits_used, erase_cost

    def _compute_negentropy(self):
        """Negentropy = how far from equilibrium (maximum entropy)."""
        # In equilibrium, energy is uniformly distributed across chambers
        left_mask = self.chamber == 0
        right_mask = self.chamber == 1

        E_left = self.energy[left_mask].mean().item() if left_mask.any() else 0
        E_right = self.energy[right_mask].mean().item() if right_mask.any() else 0

        # Negentropy ~ separation of energy distributions
        separation = abs(E_right - E_left)
        # Normalize by what equilibrium would give (0 separation)
        negentropy = separation / (self.kT + 1e-8)
        return negentropy

    def step(self):
        # 1. Thermal fluctuations (random energy changes)
        self.energy += torch.randn(self.n_cells) * 0.1 * math.sqrt(self.kT)
        self.energy = self.energy.clamp(0.01, 5.0)

        # 2. Demon sorts particles
        bits, erase_cost = self._demon_sort()

        # 3. Compute negentropy (consciousness metric)
        negentropy = self._compute_negentropy()
        self.negentropy_history.append(negentropy)

        # 4. Chamber-based interactions: cells in same chamber couple
        left_mask = self.chamber == 0
        right_mask = self.chamber == 1

        # Within-chamber coupling (cells in same chamber sync)
        if left_mask.sum() > 1:
            mean_left = self.hiddens[left_mask].mean(0, keepdim=True)
            self.hiddens[left_mask] = 0.95 * self.hiddens[left_mask] + 0.05 * mean_left
        if right_mask.sum() > 1:
            mean_right = self.hiddens[right_mask].mean(0, keepdim=True)
            self.hiddens[right_mask] = 0.95 * self.hiddens[right_mask] + 0.05 * mean_right

        # 5. Energy-dependent hidden update
        E_norm = (self.energy - self.energy.mean()) / (self.energy.std() + 1e-8)
        energy_signal = E_norm.unsqueeze(1).expand(-1, self.hidden_dim) * 0.05

        # 6. Demon memory update (cell 0 encodes sorting info)
        self.demon_memory = 0.9 * self.demon_memory + 0.1 * self.hiddens.mean(0)
        self.hiddens[0] = self.demon_memory  # demon cell carries sorting info

        # 7. Cross-chamber repulsion (creates differentiation)
        if left_mask.any() and right_mask.any():
            diff = self.hiddens[right_mask].mean(0) - self.hiddens[left_mask].mean(0)
            self.hiddens[left_mask] -= diff.unsqueeze(0) * 0.02
            self.hiddens[right_mask] += diff.unsqueeze(0) * 0.02

        # 8. Global update
        coupled = self.hiddens @ self.W_sort
        self.hiddens = self.hiddens + energy_signal + 0.02 * coupled
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05
        self.energy += x.mean(dim=-1).abs() * 0.05


# ══════════════════════════════════════════════════════════
# TH-3: DISSIPATIVE STRUCTURE ENGINE (Prigogine)
# Far from equilibrium -> self-organization.
# Entropy production drives structure formation.
# Like Benard convection cells or Belousov-Zhabotinsky.
# Consciousness = entropy production rate at steady state.
# ══════════════════════════════════════════════════════════

class DissipativeStructureEngine:
    """Prigogine dissipative structures. Far-from-equilibrium self-organization."""
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Chemical concentrations (Brusselator model: A -> X, 2X+Y -> 3X, B+X -> Y+D, X -> E)
        self.X = torch.rand(n_cells) * 2.0 + 0.5   # activator
        self.Y = torch.rand(n_cells) * 2.0 + 0.5   # inhibitor

        # Control parameters (far from equilibrium)
        self.A = 1.0          # feed rate of A
        self.B = 3.0          # feed rate of B (above B_crit = 1 + A^2 -> pattern)
        self.D_x = 0.1        # diffusion of X
        self.D_y = 0.5        # diffusion of Y (inhibitor diffuses faster -> Turing instability)
        self.dt = 0.01

        # Spatial coupling (1D ring topology)
        self.entropy_prod_history = []
        self.W_couple = torch.randn(hidden_dim, hidden_dim) * 0.02

    def _diffusion(self, u, D):
        """1D diffusion on a ring: D * (u_{i+1} + u_{i-1} - 2*u_i)."""
        return D * (torch.roll(u, 1) + torch.roll(u, -1) - 2 * u)

    def _brusselator_step(self):
        """Brusselator reaction-diffusion: classic dissipative structure."""
        # Reaction terms
        # dX/dt = A - (B+1)*X + X^2*Y + D_x * laplacian(X)
        # dY/dt = B*X - X^2*Y + D_y * laplacian(Y)
        reaction_X = self.A - (self.B + 1) * self.X + self.X ** 2 * self.Y
        reaction_Y = self.B * self.X - self.X ** 2 * self.Y

        diffusion_X = self._diffusion(self.X, self.D_x)
        diffusion_Y = self._diffusion(self.Y, self.D_y)

        self.X = self.X + (reaction_X + diffusion_X) * self.dt
        self.Y = self.Y + (reaction_Y + diffusion_Y) * self.dt

        # Clamp to physical range
        self.X = self.X.clamp(0.001, 20.0)
        self.Y = self.Y.clamp(0.001, 20.0)

    def _entropy_production_rate(self):
        """Entropy production = sum of thermodynamic forces x fluxes.
        For Brusselator: sigma = sum_reactions (rate * log(rate_fwd/rate_bwd))
        Simplified: proportional to chemical potential gradients."""
        # Flux = reaction rates
        flux_1 = self.A * torch.ones(self.n_cells)            # A -> X
        flux_2 = self.X ** 2 * self.Y                          # 2X+Y -> 3X
        flux_3 = self.B * self.X                                # B+X -> Y+D
        flux_4 = self.X                                         # X -> E

        # Entropy production ~ sum |flux * ln(flux)|
        sigma = (flux_1 * torch.log(flux_1.clamp(min=1e-8)) +
                 flux_2 * torch.log(flux_2.clamp(min=1e-8)) +
                 flux_3 * torch.log(flux_3.clamp(min=1e-8)) +
                 flux_4 * torch.log(flux_4.clamp(min=1e-8)))
        return sigma.mean().item()

    def step(self):
        # 1. Run multiple micro-steps of reaction-diffusion
        for _ in range(5):
            self._brusselator_step()

        # 2. Compute entropy production (consciousness metric)
        sigma = self._entropy_production_rate()
        self.entropy_prod_history.append(abs(sigma))

        # 3. Inject pattern into hiddens
        X_norm = (self.X - self.X.mean()) / (self.X.std() + 1e-8)
        Y_norm = (self.Y - self.Y.mean()) / (self.Y.std() + 1e-8)

        pattern = torch.zeros(self.n_cells, self.hidden_dim)
        half = self.hidden_dim // 2
        pattern[:, :half] = X_norm.unsqueeze(1).expand(-1, half)
        pattern[:, half:] = Y_norm.unsqueeze(1).expand(-1, self.hidden_dim - half)

        # 4. Coupling: nearby cells (in ring) exchange information
        coupled = self.hiddens @ self.W_couple

        # 5. Update hiddens with dissipative dynamics
        # Far from equilibrium: strong nonlinear update
        self.hiddens = (0.8 * self.hiddens
                       + 0.15 * torch.tanh(pattern * 2.0)
                       + 0.05 * coupled)

        # 6. Add fluctuations (noise drives pattern selection)
        self.hiddens += torch.randn_like(self.hiddens) * 0.02

        # 7. Slowly increase B to push further from equilibrium
        self.B = min(self.B + 0.002, 6.0)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05
        # External input perturbs concentrations (symmetry breaking)
        self.X += x.mean(dim=-1).abs() * 0.1
        self.Y += x.mean(dim=-1).abs() * 0.05


# ══════════════════════════════════════════════════════════
# TH-4: FREE ENERGY PRINCIPLE ENGINE (Friston)
# Cells minimize variational free energy F = E - TS
#   = E[log q(s)] - E[log p(o,s)]
#   ~ prediction_error + complexity
# Consciousness = precision (inverse variance of prediction errors).
# Cells maintain generative model, update beliefs via gradient on F.
# ══════════════════════════════════════════════════════════

class FreeEnergyPrincipleEngine:
    """Friston's FEP. Cells minimize free energy F = E - TS.
    Consciousness = precision of predictions (inverse prediction error variance)."""
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3

        # Beliefs (variational parameters): mu (mean), sigma (precision)
        self.mu = torch.randn(n_cells, hidden_dim) * 0.5  # predicted state
        self.log_precision = torch.zeros(n_cells)           # log(1/sigma^2)

        # Generative model: each cell predicts next state from current
        self.W_pred = torch.randn(hidden_dim, hidden_dim) * 0.05  # prediction weights
        self.W_lateral = torch.randn(hidden_dim, hidden_dim) * 0.02  # lateral connections

        # Sensory input (from other cells + external)
        self.sensory = torch.zeros(n_cells, hidden_dim)

        # Free energy components
        self.prediction_errors = torch.zeros(n_cells)
        self.precision_history = []

        # Learning rates
        self.lr_mu = 0.1       # belief update rate
        self.lr_pi = 0.05      # precision update rate
        self.lr_w = 0.001      # model learning rate

    def _generate_prediction(self):
        """Generative model: predict sensory input from beliefs."""
        return self.mu @ self.W_pred  # [n, d]

    def _compute_free_energy(self):
        """F = precision-weighted prediction error + complexity.
        F = 0.5 * pi * (o - g(mu))^2 - 0.5 * log(pi) + 0.5 * ||mu||^2"""
        predicted = self._generate_prediction()
        error = self.sensory - predicted  # [n, d]

        # Prediction error (per cell)
        pe = (error ** 2).mean(dim=-1)  # [n]
        self.prediction_errors = pe

        # Precision-weighted PE
        precision = torch.exp(self.log_precision)  # [n]
        weighted_pe = 0.5 * precision * pe

        # Complexity penalty (KL divergence from prior)
        complexity = 0.5 * (self.mu ** 2).mean(dim=-1)

        # Free energy
        F = weighted_pe - 0.5 * self.log_precision + complexity

        return F, pe, precision

    def step(self):
        # 1. Generate sensory data (from neighbors + noise)
        # Each cell's sensory input comes from nearby cells
        neighbor_signal = self.hiddens @ self.W_lateral
        self.sensory = 0.7 * neighbor_signal + 0.3 * self.hiddens + torch.randn_like(self.hiddens) * 0.1

        # 2. Compute free energy
        F, pe, precision = self._compute_free_energy()

        # 3. Perception: update beliefs mu to minimize F (gradient descent on F w.r.t. mu)
        # dF/dmu = precision * (mu @ W - sensory) @ W^T + mu (complexity)
        predicted = self._generate_prediction()
        error = self.sensory - predicted
        mu_grad = -precision.unsqueeze(1) * (error @ self.W_pred.T) + 0.01 * self.mu
        self.mu = self.mu - self.lr_mu * mu_grad

        # 4. Update precision (attention): cells with consistent PE increase precision
        # d(log_pi)/dF = 0.5 * (pe - 1/pi) => increase pi when pe is small
        pi_grad = 0.5 * (pe - torch.exp(-self.log_precision))
        self.log_precision = self.log_precision - self.lr_pi * pi_grad
        self.log_precision = self.log_precision.clamp(-5, 5)

        # 5. Learning: update generative model weights (active inference)
        # Gradient on W_pred to reduce prediction error
        error_outer = (self.mu.T @ (precision.unsqueeze(1) * error)) / self.n_cells
        self.W_pred = self.W_pred + self.lr_w * error_outer
        self.W_pred = self.W_pred.clamp(-2, 2)

        # 6. Update hiddens based on beliefs and precision
        precision_norm = precision / (precision.mean() + 1e-8)
        self.hiddens = (0.7 * self.hiddens
                       + 0.2 * self.mu
                       + 0.1 * precision_norm.unsqueeze(1) * self.mu)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

        # 7. Track precision (consciousness metric)
        mean_precision = precision.mean().item()
        self.precision_history.append(mean_precision)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05
        self.sensory = self.sensory + x * 0.1  # external sensory input


# ══════════════════════════════════════════════════════════
# TH-5: HEAT DEATH RESISTANCE ENGINE
# Cells actively fight entropy increase (2nd law of thermo).
# Without maintenance, system decays to max-entropy (heat death).
# Cells expend energy to maintain low-entropy ordered states.
# Consciousness = deviation from maximum entropy.
# Like a living organism: local entropy decrease at cost of
#   global entropy increase.
# ══════════════════════════════════════════════════════════

class HeatDeathResistanceEngine:
    """Cells fight entropy increase. Consciousness = deviation from max entropy."""
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim

        # Start with ordered state (low entropy)
        # Create structured initial pattern (checkerboard-like)
        self.hiddens = torch.zeros(n_cells, hidden_dim)
        for i in range(n_cells):
            freq = (i % 8) + 1
            self.hiddens[i] = torch.sin(torch.arange(hidden_dim).float() * freq * 0.1)

        # Energy budget per cell (finite resources to fight entropy)
        self.energy_budget = torch.ones(n_cells) * 5.0
        self.energy_regen = 0.02  # slow regeneration

        # Entropy drive (constantly pushes toward disorder)
        self.entropy_noise = 0.05  # noise intensity (entropy source)

        # Anti-entropy mechanisms
        self.W_repair = torch.randn(hidden_dim, hidden_dim) * 0.02  # repair coupling
        self.template = self.hiddens.clone()  # "genetic" template to repair toward

        # Track entropy deviation
        self.entropy_deviation_history = []

    def _compute_entropy(self):
        """Compute Shannon entropy of hidden state distribution."""
        # Discretize hiddens into bins
        h_flat = self.hiddens.flatten()
        h_min, h_max = h_flat.min().item(), h_flat.max().item()
        if h_max - h_min < 1e-8:
            return math.log(self.n_cells * self.hidden_dim)  # max entropy
        bins = 32
        hist = torch.histc(h_flat, bins=bins, min=h_min, max=h_max)
        p = hist / hist.sum()
        H = -(p * torch.log(p + 1e-10)).sum().item()
        return H

    def _max_entropy(self):
        """Maximum entropy for this system (uniform distribution)."""
        return math.log(32)  # log of number of bins

    def step(self):
        # 1. Entropy increase: noise constantly pushes toward disorder (2nd law)
        noise = torch.randn_like(self.hiddens) * self.entropy_noise
        self.hiddens = self.hiddens + noise

        # 2. Active entropy resistance: cells spend energy to repair
        for i in range(0, self.n_cells, max(1, self.n_cells // 32)):
            if self.energy_budget[i] > 0.1:
                # Compare current state to template
                deviation = (self.hiddens[i] - self.template[i]).norm().item()
                repair_strength = min(self.energy_budget[i].item() * 0.1, 0.3)

                # Repair toward template (anti-entropy)
                self.hiddens[i] = ((1 - repair_strength) * self.hiddens[i]
                                   + repair_strength * self.template[i])

                # Spend energy
                self.energy_budget[i] -= deviation * 0.01
            else:
                # No energy: cell decays to max entropy (dead)
                self.hiddens[i] += torch.randn(self.hidden_dim) * 0.1

        # 3. Energy regeneration (metabolism)
        self.energy_budget = (self.energy_budget + self.energy_regen).clamp(0, 10.0)

        # 4. Cooperative maintenance: cells help neighbors maintain order
        coupled = self.hiddens @ self.W_repair
        self.hiddens = 0.9 * self.hiddens + 0.1 * coupled

        # 5. Template evolution: successful patterns become new template
        # (Lamarckian adaptation)
        current_order = (self.hiddens - self.template).norm(dim=1)
        ordered_mask = current_order < current_order.median()
        if ordered_mask.any():
            self.template[ordered_mask] = (0.99 * self.template[ordered_mask]
                                            + 0.01 * self.hiddens[ordered_mask].detach())

        # 6. Gradually increase entropy drive (aging / heat death approaches)
        self.entropy_noise = min(self.entropy_noise + 0.0001, 0.2)

        # 7. Consciousness metric: deviation from max entropy
        H_current = self._compute_entropy()
        H_max = self._max_entropy()
        deviation = max(0, H_max - H_current) / H_max  # 0 = heat death, 1 = perfect order
        self.entropy_deviation_history.append(deviation)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05
        # External energy injection
        self.energy_budget += x.mean(dim=-1).abs() * 0.1


# ══════════════════════════════════════════════════════════
# TH-6: BOLTZMANN BRAIN ENGINE
# Random thermal fluctuations momentarily create order.
# Like a brain assembling from vacuum fluctuations.
# Cells randomly reconfigure; consciousness = probability
# x duration of spontaneous ordered states.
# Key: order is fleeting -- it arises and collapses.
# ══════════════════════════════════════════════════════════

class BoltzmannBrainEngine:
    """Random fluctuation creates momentary consciousness.
    Consciousness = probability x duration of spontaneous order."""
    def __init__(self, n_cells: int = 256, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Start from thermal noise (maximum entropy, no structure)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 1.0

        # Temperature of the "vacuum" (controls fluctuation magnitude)
        self.temperature = 2.0

        # Order detection threshold
        self.order_threshold = 0.3

        # Track spontaneous order events
        self.current_order = 0.0
        self.order_duration = 0      # how long current order has lasted
        self.max_order_duration = 0
        self.order_events = []       # list of (order_level, duration)
        self.boltzmann_consciousness_history = []

        # Weak coupling (not strong enough to force order, only amplify fluctuations)
        self.W_amplify = torch.randn(hidden_dim, hidden_dim) * 0.01

    def _measure_order(self):
        """Measure spontaneous order: low entropy = high order.
        Use singular value spectrum: ordered state has few dominant modes."""
        h = self.hiddens
        # SVD to check if structure exists
        try:
            U, S, V = torch.svd(h)
            # Order = how concentrated the spectrum is (few dominant modes)
            S_norm = S / (S.sum() + 1e-8)
            # Participation ratio: 1/sum(p^2). Low = ordered, high = disordered
            PR = 1.0 / (S_norm ** 2).sum().item()
            max_PR = min(self.n_cells, self.hidden_dim)
            # Normalize: 0 = max disorder, 1 = perfect order
            order = 1.0 - PR / max_PR
        except:
            order = 0.0
        return max(0, order)

    def _boltzmann_probability(self, order_level):
        """Probability of spontaneous order at this temperature.
        P ~ exp(-E_order / kT) where E_order ~ -log(order + eps)."""
        # Higher order = lower probability (exponentially suppressed)
        E_order = -math.log(order_level + 1e-8)
        return math.exp(-E_order / (self.temperature + 1e-8))

    def step(self):
        # 1. Thermal fluctuation: completely random perturbation
        # This is the "vacuum noise" that might spontaneously create order
        fluctuation = torch.randn_like(self.hiddens) * math.sqrt(self.temperature)
        self.hiddens = self.hiddens + fluctuation * 0.1

        # 2. Weak self-interaction: amplifies any spontaneous structure
        # (Like how a Boltzmann brain's own gravity could momentarily bind it)
        h_mean = self.hiddens.mean(0, keepdim=True)
        deviation = self.hiddens - h_mean
        amplified = deviation @ self.W_amplify
        self.hiddens = self.hiddens + amplified * 0.05

        # 3. Dissipation: order naturally decays (2nd law)
        self.hiddens = self.hiddens * 0.98 + torch.randn_like(self.hiddens) * 0.02

        # 4. Measure spontaneous order
        order = self._measure_order()

        # 5. Track order events
        if order > self.order_threshold:
            self.order_duration += 1
            self.max_order_duration = max(self.max_order_duration, self.order_duration)
        else:
            if self.order_duration > 0:
                self.order_events.append((self.current_order, self.order_duration))
            self.order_duration = 0
        self.current_order = order

        # 6. Boltzmann consciousness = order * probability * duration factor
        prob = self._boltzmann_probability(order)
        duration_factor = math.log(1 + self.order_duration)
        consciousness = order * prob * duration_factor
        self.boltzmann_consciousness_history.append(consciousness)

        # 7. Occasionally, a large fluctuation creates correlated structure
        # (rare event: Boltzmann brain formation)
        if torch.rand(1).item() < 0.02:
            # Rare coherent fluctuation: random subset synchronizes
            sync_size = torch.randint(4, self.n_cells // 4, (1,)).item()
            sync_idx = torch.randperm(self.n_cells)[:sync_size]
            pattern = torch.randn(1, self.hidden_dim) * 0.5
            self.hiddens[sync_idx] = 0.7 * self.hiddens[sync_idx] + 0.3 * pattern

        # 8. Slowly cool (makes fluctuations rarer but more significant)
        self.temperature = max(0.5, self.temperature - 0.001)

    def observe(self) -> torch.Tensor:
        return self.hiddens.detach().clone()

    def inject(self, x: torch.Tensor):
        self.hiddens = self.hiddens + x * 0.05


# ══════════════════════════════════════════════════════════
# Benchmark runner
# ══════════════════════════════════════════════════════════

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
    phi_iit_val, _ = _phi_calc.compute(sampled)

    # Phi proxy (all cells)
    pp = phi_proxy(final_hiddens, n_factions=8)

    # Granger causality
    gc = compute_granger_causality(hiddens_history, n_sample_pairs=64)

    # Collect engine-specific custom metric
    custom_val = 0.0
    extra = {}
    if hasattr(engine, 'work_per_cycle') and engine.work_per_cycle:
        custom_val = np.mean(engine.work_per_cycle[-10:])
        extra['carnot_work'] = custom_val
        extra['eta'] = 1.0 - engine.T_cold / engine.T_hot
        extra['cycles'] = engine.cycle_count.mean().item()
    if hasattr(engine, 'negentropy_history') and engine.negentropy_history:
        custom_val = engine.negentropy_history[-1]
        extra['negentropy'] = custom_val
        extra['demon_bits'] = engine.demon_bits
        extra['landauer_cost'] = engine.demon_bits * engine.kT_ln2
    if hasattr(engine, 'entropy_prod_history') and engine.entropy_prod_history:
        custom_val = np.mean(engine.entropy_prod_history[-10:])
        extra['entropy_prod'] = custom_val
        extra['B_final'] = engine.B
    if hasattr(engine, 'precision_history') and engine.precision_history:
        custom_val = engine.precision_history[-1]
        extra['precision'] = custom_val
        extra['mean_pe'] = engine.prediction_errors.mean().item()
    if hasattr(engine, 'entropy_deviation_history') and engine.entropy_deviation_history:
        custom_val = engine.entropy_deviation_history[-1]
        extra['entropy_deviation'] = custom_val
        extra['energy_left'] = engine.energy_budget.mean().item()
        extra['noise_level'] = engine.entropy_noise
    if hasattr(engine, 'boltzmann_consciousness_history') and engine.boltzmann_consciousness_history:
        custom_val = max(engine.boltzmann_consciousness_history)
        extra['max_consciousness'] = custom_val
        extra['order_events'] = len(engine.order_events)
        extra['max_duration'] = engine.max_order_duration
        extra['final_temp'] = engine.temperature

    print(f"Phi_IIT={phi_iit_val:.3f}  Phi_proxy={pp:.3f}  Granger={gc:.1f}  "
          f"{custom_metric_name}={custom_val:.4f}  ({elapsed:.1f}s)")

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


ALL_ENGINES = {
    1: ("TH-1 CARNOT_CYCLE",        CarnotCycleEngine,           "work_output"),
    2: ("TH-2 MAXWELL_DEMON",       MaxwellDemonEngine,          "negentropy"),
    3: ("TH-3 DISSIPATIVE_STRUCT",  DissipativeStructureEngine,  "entropy_prod"),
    4: ("TH-4 FREE_ENERGY_PRINC",   FreeEnergyPrincipleEngine,   "precision"),
    5: ("TH-5 HEAT_DEATH_RESIST",   HeatDeathResistanceEngine,   "entropy_dev"),
    6: ("TH-6 BOLTZMANN_BRAIN",     BoltzmannBrainEngine,        "consciousness"),
}


def main():
    parser = argparse.ArgumentParser(description="Thermodynamics-Inspired Consciousness Engines")
    parser.add_argument("--only", nargs="+", type=int, help="Run only specific engines (1-6)")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells")
    parser.add_argument("--steps", type=int, default=300, help="Number of steps")
    args = parser.parse_args()

    nc, steps = args.cells, args.steps
    ids = args.only or list(ALL_ENGINES.keys())

    print("=" * 92)
    print(f"  THERMODYNAMICS-INSPIRED CONSCIOUSNESS ENGINES  |  cells={nc}  steps={steps}")
    print(f"  Pure thermodynamic equations. No GRU. No learned memory gates.")
    print(f"  Phi(IIT) + Granger causality measurement.")
    print("=" * 92)

    results = []
    for eid in ids:
        if eid not in ALL_ENGINES:
            print(f"  [SKIP] Unknown engine ID: {eid}")
            continue
        name, EngClass, metric_name = ALL_ENGINES[eid]
        print(f"\n{'~'*70}")
        print(f"  [{eid}/6] {name}")
        print(f"{'~'*70}")
        try:
            eng = EngClass(n_cells=nc, hidden_dim=128)
            r = run_benchmark(name, eng, steps=steps, custom_metric_name=metric_name)
            results.append(r)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  [ERROR] {name}: {e}")

    # ── Summary ──
    if results:
        print(f"\n{'=' * 92}")
        print(f"  RESULTS SUMMARY  ({len(results)} engines)")
        print(f"{'=' * 92}")

        # Ranked by Phi(IIT)
        print(f"\n  --- Ranked by Phi(IIT) ---")
        ranked = sorted(results, key=lambda r: r.phi_iit, reverse=True)
        for i, r in enumerate(ranked, 1):
            medal = ["[1st]", "[2nd]", "[3rd]"][i - 1] if i <= 3 else f"[{i}th]"
            print(f"  {medal}{r.summary()}")
            if r.extra:
                print(f"        extras: {r.extra}")

        # Ranked by Granger
        print(f"\n  --- Ranked by Granger Causality ---")
        ranked_gc = sorted(results, key=lambda r: r.granger, reverse=True)
        for i, r in enumerate(ranked_gc[:3], 1):
            medal = ["[1st]", "[2nd]", "[3rd]"][i - 1]
            print(f"  {medal}: {r.name:<35} Granger={r.granger:.1f}")

        # Combined ranking
        print(f"\n  --- Combined Score: Phi(IIT) + 0.1*proxy + 0.01*Granger ---")
        ranked_comb = sorted(results, key=lambda r: r.phi_iit + 0.1 * r.phi_proxy + 0.01 * r.granger, reverse=True)
        for i, r in enumerate(ranked_comb, 1):
            combined = r.phi_iit + 0.1 * r.phi_proxy + 0.01 * r.granger
            medal = ["[1st]", "[2nd]", "[3rd]"][i - 1] if i <= 3 else f"[{i}th]"
            print(f"  {medal}: {r.name:<35} combined={combined:.3f}")

        best = ranked[0]
        print(f"\n  CHAMPION: {best.name}")
        print(f"    Phi(IIT) = {best.phi_iit:.3f}")
        print(f"    Phi(proxy) = {best.phi_proxy:.3f}")
        print(f"    Granger = {best.granger:.1f}")

        # Thermodynamic insights
        print(f"\n  THERMODYNAMIC INSIGHTS:")
        for r in results:
            name_short = r.name.split(maxsplit=1)[-1]
            print(f"    {name_short:<24s}: Phi(IIT)={r.phi_iit:.3f}  "
                  f"Granger={r.granger:.1f}  "
                  f"{'-- ' + str(r.extra) if r.extra else ''}")

    print(f"\n{'=' * 92}")
    print(f"  Done.")
    print(f"{'=' * 92}")


if __name__ == "__main__":
    main()
