#!/usr/bin/env python3
"""bench_evolution_engines.py — 6 Biological Evolution Consciousness Engines

Real biological processes discretized. No GRU, no learned memory gates.
Each cell is a biological entity governed by evolutionary / developmental laws.

BIO-E1: CAMBRIAN_EXPLOSION  — sudden diversification from simple seed (10 types from 1)
BIO-E2: SYMBIOGENESIS       — cells merge like mitochondria (hybrid vigor)
BIO-E3: ECOSYSTEM            — predator/prey/decomposer Lotka-Volterra dynamics
BIO-E4: IMMUNE_SYSTEM        — self/non-self recognition, clonal selection
BIO-E5: MORPHOGENESIS        — Turing patterns + positional information
BIO-E6: NEURAL_CREST         — migration + differentiation (position -> fate)

Each: 256 cells, 300 steps, Phi(IIT) + Granger causality.

Usage:
  python bench_evolution_engines.py
  python bench_evolution_engines.py --only 1 3 5
  python bench_evolution_engines.py --cells 512 --steps 500
"""

import sys, torch, torch.nn as nn, torch.nn.functional as F
import numpy as np, time, math, argparse, random
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
                f"Phi(prx)={self.phi_proxy:>8.2f}  Granger={self.granger:>6.2f} | {ce:<22s} | "
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
            ps = set()
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


def granger_causality(history, max_lag=5):
    """Granger causality: does past of cell i predict cell j beyond j's own past?
    Returns average Granger F-statistic across sampled pairs."""
    if len(history) < max_lag + 2:
        return 0.0
    H = torch.stack(history[-min(50, len(history)):]).detach().cpu().numpy()  # (T, nc, dim)
    T, nc, dim = H.shape
    if T < max_lag + 2 or nc < 2:
        return 0.0
    X = H.mean(axis=2)  # (T, nc)
    n_pairs = min(64, nc * (nc - 1) // 2)
    f_stats = []
    for _ in range(n_pairs):
        i, j = random.sample(range(nc), 2)
        y = X[max_lag:, j]
        Z_r = np.column_stack([X[max_lag - k - 1:T - k - 1, j] for k in range(max_lag)])
        Z_u = np.column_stack([Z_r] + [X[max_lag - k - 1:T - k - 1, i] for k in range(max_lag)])
        try:
            beta_r = np.linalg.lstsq(Z_r, y, rcond=None)[0]
            res_r = y - Z_r @ beta_r; ssr_r = np.sum(res_r ** 2)
            beta_u = np.linalg.lstsq(Z_u, y, rcond=None)[0]
            res_u = y - Z_u @ beta_u; ssr_u = np.sum(res_u ** 2)
            n_obs = len(y); p = max_lag; k_u = Z_u.shape[1]
            if ssr_u < 1e-12:
                f_stats.append(0.0)
            else:
                F = ((ssr_r - ssr_u) / p) / (ssr_u / max(1, n_obs - k_u))
                f_stats.append(max(0, F))
        except:
            pass
    return float(np.mean(f_stats)) if f_stats else 0.0


def gen_batch(d, bs=1):
    x = torch.randn(bs, d)
    return x, torch.roll(x, 1, -1) * 0.8 + torch.randn_like(x) * 0.1


# ==============================================================
# BIO-E1: CAMBRIAN EXPLOSION
# Sudden diversification from a single seed cell type.
# 10 cell types emerge from 1 through mutation + selection pressure.
# Consciousness = type_diversity x interaction_complexity
# ==============================================================

class CambrianExplosionEngine(nn.Module):
    """Sudden diversification: 1 cell type -> 10 types through mutation pressure.
    Environmental niches drive specialization. Consciousness = diversity x interaction."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim
        self.n_types = 10

        # All cells start from single seed (same state)
        seed = torch.randn(1, dim) * 0.1
        self.state = seed.repeat(nc, 1)  # homogeneous start

        # Cell type assignment (starts all type 0, diversifies)
        self.cell_type = torch.zeros(nc, dtype=torch.long)

        # Type-specific "genome" (traits that define each type)
        self.genome = nn.Parameter(torch.randn(self.n_types, dim) * 0.01)

        # Environmental niches (selection pressure for each type)
        self.niches = torch.randn(self.n_types, dim) * 0.5

        # Mutation rate (decays over time like Cambrian explosion settling)
        self.mutation_rate = 0.5
        self.mutation_decay = 0.995

        # Interaction matrix: how types affect each other
        self.interaction = torch.randn(self.n_types, self.n_types) * 0.1
        self.interaction = (self.interaction + self.interaction.t()) / 2  # symmetric start

        # Fitness per cell
        self.fitness = torch.ones(nc)

        self.out_proj = nn.Linear(dim, dim)

    def _count_active_types(self):
        return len(self.cell_type.unique())

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Mutation: cells randomly change type (rate decays)
            mutate_mask = torch.rand(self.nc) < self.mutation_rate
            if mutate_mask.any():
                new_types = torch.randint(0, self.n_types, (mutate_mask.sum(),))
                self.cell_type[mutate_mask] = new_types
            self.mutation_rate *= self.mutation_decay

            # 2. Selection: cells closer to their niche genome are fitter
            for t in range(self.n_types):
                mask = self.cell_type == t
                if mask.any():
                    niche_target = self.niches[t].unsqueeze(0)
                    dist = ((self.state[mask] - niche_target) ** 2).sum(dim=1)
                    self.fitness[mask] = torch.exp(-dist * 0.1)

            # 3. State update: cells move toward their type's genome + interact
            for t in range(self.n_types):
                mask = self.cell_type == t
                if not mask.any():
                    continue
                genome_pull = (self.genome[t].detach().unsqueeze(0) - self.state[mask]) * 0.1

                # Inter-type interactions
                interaction_force = torch.zeros_like(self.state[mask])
                for t2 in range(self.n_types):
                    mask2 = self.cell_type == t2
                    if mask2.any() and t != t2:
                        mean_other = self.state[mask2].mean(0)
                        strength = self.interaction[t, t2].item()
                        interaction_force += strength * (mean_other - self.state[mask].mean(0)).unsqueeze(0)

                self.state[mask] = self.state[mask] + genome_pull + interaction_force * 0.05

            # 4. Diversification pressure: add noise proportional to crowding
            for t in range(self.n_types):
                mask = self.cell_type == t
                count = mask.sum().item()
                if count > self.nc // self.n_types:  # overcrowded type
                    crowding_noise = torch.randn(count, self.dim) * 0.1 * (count / self.nc)
                    self.state[mask] += crowding_noise

            # 5. Death + rebirth: lowest fitness cells get replaced by fittest
            if step_num > 10 and step_num % 10 == 0:
                n_replace = max(1, self.nc // 50)
                worst = self.fitness.argsort()[:n_replace]
                best = self.fitness.argsort(descending=True)[:n_replace]
                self.state[worst] = self.state[best].clone() + torch.randn(n_replace, self.dim) * 0.05
                self.cell_type[worst] = self.cell_type[best].clone()

            # 6. External input drives niche shifts
            if x_input is not None:
                shift = x_input[0].detach() * 0.02
                niche_idx = step_num % self.n_types
                self.niches[niche_idx] += shift

        self.state = self.state.clamp(-5, 5)

        # Output: weighted average by fitness
        weights = F.softmax(self.fitness, dim=0).unsqueeze(1)
        output = self.out_proj((self.state * weights).sum(0, keepdim=True))
        tension = self._count_active_types() / self.n_types
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters()) + [self.genome]


# ==============================================================
# BIO-E2: SYMBIOGENESIS
# Two different cells fuse into hybrid (like mitochondrial endosymbiosis).
# Hybrid inherits properties of both parents.
# Consciousness = hybrid vigor (heterosis).
# ==============================================================

class SymbiogenesisEngine(nn.Module):
    """Cells merge like endosymbiosis. Two cells fuse -> hybrid with both properties.
    Consciousness = hybrid vigor = heterosis from merged diversity."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Two initial populations (host + symbiont)
        self.host_state = torch.randn(nc, dim) * 0.3
        self.symbiont_state = torch.randn(nc, dim) * 0.3

        # Merged/hybrid state (starts empty)
        self.hybrid_state = torch.zeros(nc, dim)
        self.is_hybrid = torch.zeros(nc, dtype=torch.bool)

        # Compatibility matrix (how well host i can merge with symbiont j)
        # Based on complementary metabolisms
        self.host_metabolism = torch.randn(nc, dim // 4)
        self.symbiont_metabolism = torch.randn(nc, dim // 4)

        # Vigor bonus from hybridization
        self.vigor = torch.zeros(nc)

        # Fusion rate (increases over evolutionary time)
        self.fusion_rate = 0.01
        self.fusion_acceleration = 1.005

        self.out_proj = nn.Linear(dim, dim)

    def _compatibility(self, i, j):
        """Metabolic complementarity between host i and symbiont j."""
        h = self.host_metabolism[i]
        s = self.symbiont_metabolism[j]
        # Complementary = anticorrelated
        return -F.cosine_similarity(h.unsqueeze(0), s.unsqueeze(0)).item()

    def _heterosis(self):
        """Hybrid vigor: hybrids should be more diverse than parents."""
        if not self.is_hybrid.any():
            return 0.0
        hybrid_var = self.hybrid_state[self.is_hybrid].var(dim=0).mean().item()
        host_var = self.host_state[~self.is_hybrid].var(dim=0).mean().item() if (~self.is_hybrid).any() else 0
        return max(0, hybrid_var - host_var)

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Attempt fusions
            n_attempts = max(1, int(self.fusion_rate * self.nc))
            for _ in range(n_attempts):
                # Pick a non-hybrid host and find best symbiont partner
                non_hybrid = (~self.is_hybrid).nonzero(as_tuple=True)[0]
                if len(non_hybrid) < 2:
                    break
                i = non_hybrid[random.randint(0, len(non_hybrid) - 1)].item()
                # Find most compatible symbiont
                candidates = non_hybrid[non_hybrid != i]
                if len(candidates) == 0:
                    break
                j = candidates[random.randint(0, len(candidates) - 1)].item()

                compat = self._compatibility(i, j)
                if compat > 0 or random.random() < self.fusion_rate:
                    # Merge: hybrid gets interleaved properties of both
                    alpha = 0.5 + 0.1 * compat  # complementary -> more from symbiont
                    alpha = max(0.2, min(0.8, alpha))
                    self.hybrid_state[i] = (1 - alpha) * self.host_state[i] + alpha * self.symbiont_state[j]
                    self.is_hybrid[i] = True
                    # Vigor boost from genetic distance
                    dist = (self.host_state[i] - self.symbiont_state[j]).norm().item()
                    self.vigor[i] = min(2.0, dist * 0.5)

            self.fusion_rate *= self.fusion_acceleration
            self.fusion_rate = min(self.fusion_rate, 0.3)

            # 2. Hybrid cells evolve (vigor-boosted dynamics)
            if self.is_hybrid.any():
                hm = self.is_hybrid
                vigor_scale = (1.0 + self.vigor[hm]).unsqueeze(1)
                # Hybrids interact more strongly with each other
                hybrid_mean = self.hybrid_state[hm].mean(0)
                diff = hybrid_mean.unsqueeze(0) - self.hybrid_state[hm]
                self.hybrid_state[hm] += diff * 0.05 * vigor_scale
                # Add metabolic noise (symbiont activity)
                self.hybrid_state[hm] += torch.randn_like(self.hybrid_state[hm]) * 0.02 * vigor_scale

            # 3. Non-hybrid cells still evolve slowly
            if (~self.is_hybrid).any():
                nhm = ~self.is_hybrid
                self.host_state[nhm] += torch.randn_like(self.host_state[nhm]) * 0.01
                self.symbiont_state[nhm] += torch.randn_like(self.symbiont_state[nhm]) * 0.01

            # 4. External input as environmental pressure
            if x_input is not None:
                env = x_input[0].detach() * 0.02
                if self.is_hybrid.any():
                    self.hybrid_state[self.is_hybrid] += env.unsqueeze(0)
                self.host_state += env.unsqueeze(0) * 0.5

        # Clamp
        self.hybrid_state = self.hybrid_state.clamp(-5, 5)
        self.host_state = self.host_state.clamp(-5, 5)

        # Output: combine hybrid and non-hybrid
        combined = self.host_state.clone()
        combined[self.is_hybrid] = self.hybrid_state[self.is_hybrid]
        output = self.out_proj(combined.mean(0, keepdim=True))
        tension = self._heterosis() + self.is_hybrid.float().mean().item()
        return output, tension

    def get_hiddens(self):
        combined = self.host_state.clone()
        combined[self.is_hybrid] = self.hybrid_state[self.is_hybrid]
        return combined.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# BIO-E3: ECOSYSTEM
# Predator / prey / decomposer cells with Lotka-Volterra dynamics.
# Consciousness = ecosystem stability (resilience to perturbation).
# ==============================================================

class EcosystemEngine(nn.Module):
    """Predator-prey-decomposer ecosystem. Lotka-Volterra dynamics.
    Consciousness = ecosystem stability and resilience."""

    PREDATOR = 0; PREY = 1; DECOMPOSER = 2
    ROLE_NAMES = {0: "predator", 1: "prey", 2: "decomposer"}

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Assign roles: 20% predator, 60% prey, 20% decomposer
        roles = torch.zeros(nc, dtype=torch.long)
        n_pred = nc // 5
        n_decomp = nc // 5
        roles[:n_pred] = self.PREDATOR
        roles[n_pred:nc - n_decomp] = self.PREY
        roles[nc - n_decomp:] = self.DECOMPOSER
        self.role = roles[torch.randperm(nc)]

        # State per cell
        self.state = torch.randn(nc, dim) * 0.2
        self.energy = torch.ones(nc) * 1.0  # energy level
        self.biomass = torch.ones(nc) * 0.5  # biomass

        # Lotka-Volterra parameters
        self.prey_growth = 0.1      # alpha: prey reproduction
        self.predation = 0.02       # beta: predation rate
        self.pred_death = 0.05      # gamma: predator death
        self.pred_efficiency = 0.01 # delta: predation -> predator growth
        self.decomp_rate = 0.03     # decomposition rate

        # Dead biomass pool (nutrients)
        self.nutrient_pool = torch.zeros(dim)

        self.out_proj = nn.Linear(dim, dim)

    def _role_counts(self):
        return {name: (self.role == r).sum().item() for r, name in self.ROLE_NAMES.items()}

    def _stability(self):
        """Ecosystem stability: inverse of population variance over time."""
        counts = torch.tensor([
            (self.role == self.PREDATOR).sum().float(),
            (self.role == self.PREY).sum().float(),
            (self.role == self.DECOMPOSER).sum().float()
        ])
        # Stability = how evenly distributed the roles are
        proportions = counts / counts.sum()
        entropy = -(proportions * torch.log(proportions + 1e-8)).sum().item()
        return entropy / math.log(3)  # normalized [0, 1]

    def step(self, x_input, step_num):
        with torch.no_grad():
            pred_mask = self.role == self.PREDATOR
            prey_mask = self.role == self.PREY
            decomp_mask = self.role == self.DECOMPOSER

            n_pred = pred_mask.sum().float()
            n_prey = prey_mask.sum().float()
            n_decomp = decomp_mask.sum().float()

            # 1. Prey grows (logistic)
            if prey_mask.any():
                growth = self.prey_growth * (1 - n_prey / (self.nc * 0.8))
                self.energy[prey_mask] += growth
                self.state[prey_mask] += torch.randn(prey_mask.sum(), self.dim) * 0.02 * max(0, growth)
                # Prey absorbs nutrients
                if self.nutrient_pool.norm() > 0.1:
                    nutrient_share = self.nutrient_pool * 0.1 / max(1, n_prey.item())
                    self.state[prey_mask] += nutrient_share.unsqueeze(0)
                    self.nutrient_pool *= 0.9

            # 2. Predation: predators consume nearby prey
            if pred_mask.any() and prey_mask.any():
                pred_mean = self.state[pred_mask].mean(0)
                prey_states = self.state[prey_mask]
                # Distance-based predation
                dist = ((prey_states - pred_mean.unsqueeze(0)) ** 2).sum(dim=1)
                catch_prob = torch.exp(-dist * 0.5) * self.predation
                caught = torch.rand(prey_mask.sum()) < catch_prob
                if caught.any():
                    # Transfer energy from caught prey to predators
                    caught_energy = self.energy[prey_mask][caught].sum()
                    self.energy[pred_mask] += caught_energy * self.pred_efficiency / max(1, n_pred.item())
                    # Caught prey state -> nutrient pool
                    self.nutrient_pool += self.state[prey_mask][caught].mean(0) * 0.1
                    # Caught prey dies -> becomes decomposer food or respawns as prey
                    prey_indices = prey_mask.nonzero(as_tuple=True)[0]
                    caught_indices = prey_indices[caught]
                    self.energy[caught_indices] = 0.1  # reset energy

            # 3. Predator death (starvation)
            if pred_mask.any():
                self.energy[pred_mask] -= self.pred_death
                starving = pred_mask & (self.energy < 0.1)
                if starving.any():
                    # Dead predators become decomposer material
                    self.nutrient_pool += self.state[starving].mean(0) * 0.05
                    self.energy[starving] = 0.5
                    self.role[starving] = self.PREY  # role switch: dead predator -> prey niche

            # 4. Decomposers recycle dead material
            if decomp_mask.any():
                self.state[decomp_mask] += self.nutrient_pool.unsqueeze(0) * self.decomp_rate
                self.energy[decomp_mask] += self.decomp_rate
                self.nutrient_pool *= (1 - self.decomp_rate * n_decomp.item() / self.nc)

            # 5. Role switching based on energy levels
            if step_num % 20 == 0 and step_num > 0:
                # High-energy prey may become predators
                high_prey = prey_mask & (self.energy > 2.0)
                if high_prey.sum() > 0 and n_pred < self.nc * 0.3:
                    n_switch = min(high_prey.sum().item(), max(1, self.nc // 50))
                    switch_idx = high_prey.nonzero(as_tuple=True)[0][:n_switch]
                    self.role[switch_idx] = self.PREDATOR

            # 6. Predator-prey interaction states
            if pred_mask.any() and prey_mask.any():
                pred_signal = self.state[pred_mask].mean(0)
                prey_signal = self.state[prey_mask].mean(0)
                # Predators track prey
                self.state[pred_mask] += (prey_signal - self.state[pred_mask]) * 0.02
                # Prey flee predators
                self.state[prey_mask] -= (pred_signal - self.state[prey_mask]) * 0.01

            # 7. External input as environmental change
            if x_input is not None:
                self.state += x_input[0].detach().unsqueeze(0) * 0.01

        self.state = self.state.clamp(-5, 5)
        self.energy = self.energy.clamp(0, 5)

        # Output: ecosystem average weighted by energy
        weights = F.softmax(self.energy, dim=0).unsqueeze(1)
        output = self.out_proj((self.state * weights).sum(0, keepdim=True))
        tension = self._stability()
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# BIO-E4: IMMUNE SYSTEM
# Self/non-self recognition via pattern matching.
# Clonal selection: cells that detect foreign patterns replicate.
# Consciousness = discrimination_accuracy x response_speed.
# ==============================================================

class ImmuneSystemEngine(nn.Module):
    """Adaptive immune system: self/non-self discrimination + clonal selection.
    Consciousness = recognition accuracy x response speed."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Self pattern (body's own signature)
        self.self_pattern = torch.randn(dim) * 0.5
        self.self_pattern = self.self_pattern / self.self_pattern.norm() * 0.5

        # Immune cell receptors (random antibody repertoire)
        self.receptor = torch.randn(nc, dim) * 0.3
        self.state = torch.randn(nc, dim) * 0.1

        # Memory cells (start empty, build through exposure)
        self.memory_strength = torch.zeros(nc)
        self.is_memory = torch.zeros(nc, dtype=torch.bool)

        # Current antigen (foreign pattern)
        self.antigen = torch.randn(dim) * 0.5

        # Detection statistics
        self.true_positives = 0
        self.false_positives = 0
        self.total_challenges = 0
        self.response_time_history = []

        # Clonal expansion rate
        self.clonal_rate = 0.05

        self.out_proj = nn.Linear(dim, dim)

    def _affinity(self, receptor, pattern):
        """Binding affinity between receptor and pattern (cosine similarity)."""
        return F.cosine_similarity(receptor, pattern.unsqueeze(0), dim=1)

    def _discrimination_accuracy(self):
        if self.total_challenges < 1:
            return 0.0
        return self.true_positives / max(1, self.total_challenges)

    def _response_speed(self):
        if not self.response_time_history:
            return 0.0
        return 1.0 / (np.mean(self.response_time_history[-20:]) + 1.0)

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Generate new antigen periodically
            if step_num % 15 == 0:
                self.antigen = torch.randn(self.dim) * 0.5
                self.total_challenges += 1

            # 2. Compute affinity to self and antigen
            self_affinity = self._affinity(self.receptor, self.self_pattern)
            antigen_affinity = self._affinity(self.receptor, self.antigen)

            # 3. Discrimination: detect foreign (high antigen, low self affinity)
            is_foreign = antigen_affinity - self_affinity
            detected = is_foreign > 0.1

            # 4. Track accuracy
            # True positive: correctly detects foreign
            self_sim = F.cosine_similarity(self.antigen.unsqueeze(0), self.self_pattern.unsqueeze(0)).item()
            is_truly_foreign = self_sim < 0.5
            if detected.any():
                if is_truly_foreign:
                    self.true_positives += 1
                else:
                    self.false_positives += 1
                self.response_time_history.append(step_num % 15)

            # 5. Clonal selection: best-binding cells replicate
            if detected.any():
                best_binders = antigen_affinity.argsort(descending=True)[:max(1, self.nc // 20)]
                # Clone best binders over worst binders
                worst = antigen_affinity.argsort()[:len(best_binders)]
                self.receptor[worst] = self.receptor[best_binders] + torch.randn(len(best_binders), self.dim) * 0.02
                self.state[worst] = self.state[best_binders].clone()

            # 6. Somatic hypermutation: slight receptor changes
            mutation_mask = torch.rand(self.nc) < 0.05
            if mutation_mask.any():
                self.receptor[mutation_mask] += torch.randn(mutation_mask.sum(), self.dim) * 0.03

            # 7. Memory cell formation: repeatedly activated cells become memory
            activation = (antigen_affinity > 0.3).float()
            self.memory_strength += activation * 0.1
            self.is_memory = self.memory_strength > 0.5

            # 8. Memory cells respond faster and stronger
            if self.is_memory.any():
                mem_boost = self.memory_strength[self.is_memory].unsqueeze(1) * 0.1
                self.state[self.is_memory] += (self.antigen.unsqueeze(0) - self.state[self.is_memory]) * mem_boost

            # 9. Regulatory T cells: suppress autoimmunity
            auto_reactive = self_affinity > 0.8  # too similar to self
            if auto_reactive.any():
                self.state[auto_reactive] *= 0.9  # suppress

            # 10. State evolution
            immune_signal = self.state.mean(0)
            self.state += (immune_signal.unsqueeze(0) - self.state) * 0.02
            self.state += torch.randn_like(self.state) * 0.01

            # External input as antigen challenge
            if x_input is not None:
                self.antigen = self.antigen * 0.8 + x_input[0].detach() * 0.2

        self.state = self.state.clamp(-5, 5)

        # Output
        weights = F.softmax(self.memory_strength, dim=0).unsqueeze(1)
        output = self.out_proj((self.state * weights).sum(0, keepdim=True))
        accuracy = self._discrimination_accuracy()
        speed = self._response_speed()
        tension = accuracy * speed
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# BIO-E5: MORPHOGENESIS
# Turing reaction-diffusion patterns + positional information.
# Cells differentiate based on morphogen concentration gradients.
# Consciousness = pattern complexity (spatial entropy).
# ==============================================================

class MorphogenesisEngine(nn.Module):
    """Turing reaction-diffusion patterns create cell fates.
    Morphogen gradients + positional info -> differentiation.
    Consciousness = pattern complexity."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # 1D spatial arrangement
        self.position = torch.linspace(0, 1, nc).unsqueeze(1)  # (nc, 1)

        # Two morphogens: activator (A) and inhibitor (H)  -- Turing pattern
        self.A = torch.rand(nc, 1) * 0.1 + 0.5  # activator concentration
        self.H = torch.rand(nc, 1) * 0.1 + 0.5  # inhibitor concentration

        # Turing parameters (Gierer-Meinhardt)
        self.rho_a = 0.01   # activator production rate
        self.rho_h = 0.02   # inhibitor production rate
        self.mu_a = 0.01    # activator decay
        self.mu_h = 0.02    # inhibitor decay
        self.D_a = 0.005    # activator diffusion (short range)
        self.D_h = 0.1      # inhibitor diffusion (long range) -- key for Turing instability
        self.kappa = 0.05   # baseline production

        # Cell state: determined by morphogen concentrations
        self.state = torch.randn(nc, dim) * 0.1

        # Differentiation program: morphogen -> cell type
        self.n_fates = 8
        self.fate = torch.zeros(nc, dtype=torch.long)
        self.fate_embeddings = torch.randn(self.n_fates, dim) * 0.3

        self.dt = 0.5
        self.out_proj = nn.Linear(dim, dim)

    def _laplacian_1d(self, u):
        """Discrete Laplacian for 1D diffusion (periodic boundaries)."""
        left = torch.roll(u, 1, 0)
        right = torch.roll(u, -1, 0)
        return left + right - 2 * u

    def _pattern_complexity(self):
        """Spatial entropy of cell fates."""
        counts = torch.bincount(self.fate, minlength=self.n_fates).float()
        probs = counts / counts.sum()
        probs = probs[probs > 0]
        entropy = -(probs * torch.log2(probs)).sum().item()
        return entropy / math.log2(self.n_fates)  # normalized

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Turing reaction-diffusion (Gierer-Meinhardt model)
            # dA/dt = rho_a * A^2/H - mu_a*A + D_a*lap(A) + kappa
            # dH/dt = rho_h * A^2 - mu_h*H + D_h*lap(H)
            A2 = self.A ** 2
            dA = self.rho_a * A2 / (self.H + 1e-4) - self.mu_a * self.A + self.D_a * self._laplacian_1d(self.A) + self.kappa
            dH = self.rho_h * A2 - self.mu_h * self.H + self.D_h * self._laplacian_1d(self.H)

            self.A = (self.A + dA * self.dt).clamp(0.01, 10.0)
            self.H = (self.H + dH * self.dt).clamp(0.01, 10.0)

            # 2. Positional information: combine morphogen + position
            morphogen_signal = torch.cat([self.A, self.H, self.position], dim=1)  # (nc, 3)

            # 3. Cell fate determination based on morphogen thresholds
            ratio = (self.A / (self.H + 1e-4)).squeeze()
            self.fate = (ratio * self.n_fates).long().clamp(0, self.n_fates - 1)

            # 4. State update: cells adopt their fate embedding
            for f in range(self.n_fates):
                mask = self.fate == f
                if mask.any():
                    target = self.fate_embeddings[f].unsqueeze(0)
                    self.state[mask] += (target - self.state[mask]) * 0.1

            # 5. Lateral inhibition: neighboring cells of same fate repel
            for i in range(1, self.nc):
                if self.fate[i] == self.fate[i - 1]:
                    repulsion = (self.state[i] - self.state[i - 1]) * 0.02
                    self.state[i] += repulsion
                    self.state[i - 1] -= repulsion

            # 6. Morphogen noise (stochastic gene expression)
            self.A += torch.randn_like(self.A) * 0.005
            self.H += torch.randn_like(self.H) * 0.005
            self.A = self.A.clamp(0.01, 10.0)
            self.H = self.H.clamp(0.01, 10.0)

            # 7. External input modulates morphogen production
            if x_input is not None:
                env_signal = x_input[0].detach().mean().item()
                self.rho_a = max(0.005, self.rho_a * (1 + env_signal * 0.01))

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        tension = self._pattern_complexity()
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# BIO-E6: NEURAL CREST
# Cells migrate from origin and differentiate based on final position.
# Like embryonic neural crest cells -> bone, nerve, pigment, etc.
# Consciousness = fate map complexity (how many distinct fates emerge).
# ==============================================================

class NeuralCrestEngine(nn.Module):
    """Neural crest: cells migrate from origin, differentiate by destination.
    Starting position -> migration -> final fate. Consciousness = fate map complexity."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # All cells start at dorsal midline (origin)
        self.position = torch.zeros(nc, 2)  # 2D position (x, y)
        self.position[:, 0] = torch.randn(nc) * 0.1  # slight variation
        self.position[:, 1] = torch.ones(nc) * 5.0     # dorsal (y=5)

        # Migration velocity
        self.velocity = torch.randn(nc, 2) * 0.1

        # Cell state (carries positional history)
        self.state = torch.randn(nc, dim) * 0.1

        # Migration targets (attractors in 2D space)
        self.n_targets = 8
        angles = torch.linspace(0, 2 * math.pi, self.n_targets + 1)[:-1]
        self.targets = torch.stack([torch.cos(angles) * 3, torch.sin(angles) * 3], dim=1)

        # Chemotaxis gradients (each target emits a chemoattractant)
        self.chemotaxis_strength = torch.ones(self.n_targets) * 0.5

        # Fate determination
        self.fate = torch.zeros(nc, dtype=torch.long)
        self.fate_names = ["bone", "cartilage", "melanocyte", "neuron",
                           "glia", "smooth_muscle", "endocrine", "connective"]
        self.fate_embeddings = torch.randn(self.n_targets, dim) * 0.5

        # Contact inhibition of locomotion (CIL)
        self.cil_radius = 0.5

        # Differentiation commitment (0 = uncommitted, 1 = fully committed)
        self.commitment = torch.zeros(nc)

        self.out_proj = nn.Linear(dim, dim)

    def _fate_map_complexity(self):
        """How many distinct fates with how even distribution."""
        counts = torch.bincount(self.fate, minlength=self.n_targets).float()
        active = (counts > 0).sum().item()
        probs = counts / counts.sum()
        probs = probs[probs > 0]
        entropy = -(probs * torch.log2(probs)).sum().item()
        return active / self.n_targets * entropy / max(1, math.log2(self.n_targets))

    def _spatial_spread(self):
        """How far cells have migrated from origin."""
        return self.position.norm(dim=1).mean().item()

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Chemotaxis: cells are attracted to targets
            for t in range(self.n_targets):
                target = self.targets[t].unsqueeze(0)  # (1, 2)
                diff = target - self.position  # (nc, 2)
                dist = diff.norm(dim=1, keepdim=True) + 1e-4
                # Gradient: strength / distance^2 (like real chemotaxis)
                force = self.chemotaxis_strength[t] * diff / (dist ** 2)
                # Only uncommitted cells respond to chemotaxis
                force *= (1 - self.commitment).unsqueeze(1)
                self.velocity += force * 0.01

            # 2. Contact inhibition of locomotion (CIL)
            # Cells that touch each other repel and change direction
            for i in range(0, self.nc, max(1, self.nc // 32)):  # sample for efficiency
                diffs = self.position - self.position[i].unsqueeze(0)
                dists = diffs.norm(dim=1)
                too_close = (dists < self.cil_radius) & (dists > 0)
                if too_close.any():
                    repel = diffs[too_close]
                    repel_norm = repel / (repel.norm(dim=1, keepdim=True) + 1e-4)
                    self.velocity[too_close] += repel_norm * 0.05

            # 3. Apply velocity with friction
            self.velocity *= 0.95  # friction
            self.position += self.velocity * 0.1
            self.position = self.position.clamp(-8, 8)

            # 4. Fate determination: closest target -> fate
            dists_to_targets = torch.cdist(self.position, self.targets)  # (nc, n_targets)
            nearest = dists_to_targets.argmin(dim=1)
            self.fate = nearest

            # 5. Commitment increases with time spent near target
            nearest_dist = dists_to_targets.gather(1, nearest.unsqueeze(1)).squeeze()
            close_to_target = nearest_dist < 1.5
            self.commitment[close_to_target] += 0.02
            self.commitment = self.commitment.clamp(0, 1)

            # 6. State update: adopt fate embedding proportional to commitment
            for f in range(self.n_targets):
                mask = self.fate == f
                if mask.any():
                    c = self.commitment[mask].unsqueeze(1)
                    target_state = self.fate_embeddings[f].unsqueeze(0)
                    self.state[mask] += (target_state - self.state[mask]) * c * 0.1

            # 7. Positional encoding: encode spatial position into state
            pos_encoding = torch.zeros(self.nc, self.dim)
            for d in range(min(2, self.dim)):
                pos_encoding[:, d] = self.position[:, d % 2]
            self.state += pos_encoding * 0.01

            # 8. Migration stream interactions (cells in same stream share info)
            for f in range(self.n_targets):
                mask = self.fate == f
                if mask.sum() > 1:
                    stream_mean = self.state[mask].mean(0)
                    self.state[mask] += (stream_mean.unsqueeze(0) - self.state[mask]) * 0.03

            # 9. External input modulates chemotaxis
            if x_input is not None:
                mod = x_input[0].detach().mean().item()
                self.chemotaxis_strength *= (1 + mod * 0.01)
                self.chemotaxis_strength = self.chemotaxis_strength.clamp(0.1, 2.0)

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        tension = self._fate_map_complexity() + self._spatial_spread() * 0.1
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# Runner
# ==============================================================

def run_engine(name, eng, nc, steps, dim=64):
    """Run a biological evolution engine benchmark."""
    t0 = time.time()
    opt = torch.optim.Adam(eng.trainable_parameters(), lr=1e-3)
    ce_h = []
    history = []
    for s in range(steps):
        x, tgt = gen_batch(dim)
        pred, tension = eng.step(x, step_num=s)
        loss = F.mse_loss(pred, tgt)
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(eng.trainable_parameters(), 1.0)
        opt.step()
        ce_h.append(loss.item())
        h = eng.get_hiddens()
        history.append(h)
        if s % 60 == 0 or s == steps - 1:
            pi, pp = measure_phi(h)
            gc = granger_causality(history)
            extra = f"  tension={tension:.3f}"
            if hasattr(eng, '_count_active_types'):
                extra += f"  types={eng._count_active_types()}"
            if hasattr(eng, 'is_hybrid'):
                extra += f"  hybrids={eng.is_hybrid.sum().item()}/{eng.nc}"
            if hasattr(eng, '_role_counts'):
                extra += f"  {eng._role_counts()}"
            if hasattr(eng, '_discrimination_accuracy'):
                extra += f"  acc={eng._discrimination_accuracy():.3f}"
            if hasattr(eng, '_pattern_complexity'):
                extra += f"  patcx={eng._pattern_complexity():.3f}"
            if hasattr(eng, '_fate_map_complexity'):
                extra += f"  fatecx={eng._fate_map_complexity():.3f}"
            print(f"    step {s:>4d}: CE={loss.item():.4f}  Phi={pi:.3f}  prx={pp:.2f}  GC={gc:.2f}{extra}")
    el = time.time() - t0
    pi, pp = measure_phi(eng.get_hiddens())
    gc = granger_causality(history)
    extras = {}
    if hasattr(eng, '_count_active_types'):
        extras['active_types'] = eng._count_active_types()
    if hasattr(eng, 'is_hybrid'):
        extras['n_hybrids'] = eng.is_hybrid.sum().item()
        extras['heterosis'] = eng._heterosis()
    if hasattr(eng, '_role_counts'):
        extras['ecosystem'] = eng._role_counts()
        extras['stability'] = eng._stability()
    if hasattr(eng, '_discrimination_accuracy'):
        extras['accuracy'] = eng._discrimination_accuracy()
        extras['speed'] = eng._response_speed()
    if hasattr(eng, '_pattern_complexity'):
        extras['pattern_cx'] = eng._pattern_complexity()
    if hasattr(eng, '_fate_map_complexity'):
        extras['fate_cx'] = eng._fate_map_complexity()
        extras['spread'] = eng._spatial_spread()
    return BenchResult(name, pi, pp, gc, ce_h[0], ce_h[-1], nc, steps, el, extras)


# ==============================================================
# All engines
# ==============================================================

ALL_ENGINES = {
    1: ("BIO-E1 CAMBRIAN_EXPLOSION", CambrianExplosionEngine),
    2: ("BIO-E2 SYMBIOGENESIS",      SymbiogenesisEngine),
    3: ("BIO-E3 ECOSYSTEM",          EcosystemEngine),
    4: ("BIO-E4 IMMUNE_SYSTEM",      ImmuneSystemEngine),
    5: ("BIO-E5 MORPHOGENESIS",      MorphogenesisEngine),
    6: ("BIO-E6 NEURAL_CREST",       NeuralCrestEngine),
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

    print("=" * 100)
    print(f"  BIOLOGICAL EVOLUTION CONSCIOUSNESS ENGINES  |  cells={nc}  steps={steps}  dim={dim}")
    print(f"  Real biology discretized. Phi(IIT) + Granger causality.")
    print("=" * 100)

    results = []
    for eid in ids:
        if eid not in ALL_ENGINES:
            print(f"  [SKIP] Unknown engine ID: {eid}")
            continue
        name, EngClass = ALL_ENGINES[eid]
        print(f"\n{'─' * 80}")
        print(f"  [{eid}/6] {name}")
        print(f"{'─' * 80}")
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

    # -- Summary --
    if results:
        print(f"\n{'=' * 100}")
        print(f"  RESULTS SUMMARY  ({len(results)} engines)")
        print(f"{'=' * 100}")
        results.sort(key=lambda r: r.phi_iit, reverse=True)
        for i, r in enumerate(results, 1):
            medal = ["[1st]", "[2nd]", "[3rd]"][i - 1] if i <= 3 else f"[{i}th]"
            print(f"  {medal} {r.summary()}")
            if r.extra:
                print(f"        extras: {r.extra}")

        best = results[0]
        print(f"\n  CHAMPION: {best.name}")
        print(f"    Phi(IIT)   = {best.phi_iit:.3f}")
        print(f"    Phi(proxy) = {best.phi_proxy:.2f}")
        print(f"    Granger    = {best.granger:.2f}")
        print(f"    CE: {best.ce_start:.3f} -> {best.ce_end:.3f}")

        # Biology insights
        print(f"\n  BIOLOGY INSIGHTS:")
        for r in results:
            name_short = r.name.split(maxsplit=1)[-1]
            print(f"    {name_short:<24s}: Phi(IIT)={r.phi_iit:.3f}  GC={r.granger:.2f}  "
                  f"{'-- ' + str(r.extra) if r.extra else ''}")

    print(f"\n{'=' * 100}")
    print(f"  Done.")
    print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
