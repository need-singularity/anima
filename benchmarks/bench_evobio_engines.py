#!/usr/bin/env python3
"""bench_evobio_engines.py — 8 Evolutionary Biology Consciousness Engines

Real evolutionary mechanisms discretized. No GRU, no learned memory gates.
Each cell is a biological entity governed by evolutionary laws.

EVO-B1: MUTATION_RATE           — Eigen's error catastrophe threshold
EVO-B2: SPECIATION              — reproductive isolation + inter-species exchange
EVO-B3: HORIZONTAL_GENE_TRANSFER — bacterial plasmid-like hidden state segment exchange
EVO-B4: EPIGENETICS             — genome (fixed) + epigenome (modifiable) dual layers
EVO-B5: RED_QUEEN               — predator/prey arms race, continuous coevolution
EVO-B6: PUNCTUATED_EQUILIBRIUM  — long stasis + sudden bursts (SOC-like, biological)
EVO-B7: SEXUAL_SELECTION        — runaway selection, display + preference vectors
EVO-B8: KIN_SELECTION           — Hamilton's rule rB > C, altruism = consciousness

Each: 256 cells, 300 steps, no GRU, measure Phi(IIT) + Granger.

Usage:
  python bench_evobio_engines.py
  python bench_evobio_engines.py --only 1 3 5
  python bench_evobio_engines.py --cells 512 --steps 500
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
        return (f"  {self.name:<40s} | Phi(IIT)={self.phi_iit:>7.3f}  "
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
    """Granger causality: does past of cell i predict cell j beyond j's own past?"""
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
# EVO-B1: MUTATION RATE (Eigen's error catastrophe)
# Cells have genome vectors. Mutation rate varies 0.001~0.1.
# Optimal mutation rate maximizes phenotype diversity while
# maintaining function. Eigen's error threshold: mu_crit = 1/L
# where L = genome length.
# Consciousness = optimal mutation rate exploration.
# ==============================================================

class MutationRateEngine(nn.Module):
    """Cells with genome vectors and variable mutation rates.
    Eigen's error catastrophe: too much mutation = loss of information,
    too little = stagnation. Consciousness = balance at criticality."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim
        self.genome_len = dim

        # Each cell has a genome (binary-like, continuous relaxation)
        self.genome = torch.randn(nc, dim) * 0.5
        # Each cell has its own mutation rate (evolvable!)
        self.mutation_rate = torch.rand(nc) * 0.099 + 0.001  # [0.001, 0.1]

        # Phenotype = nonlinear function of genome
        self.phenotype = torch.zeros(nc, dim)

        # Fitness landscape (rugged NK landscape approximation)
        self.landscape_centers = torch.randn(8, dim) * 2.0  # 8 fitness peaks
        self.landscape_heights = torch.rand(8) * 0.5 + 0.5

        # Eigen's critical mutation rate: mu_crit ~ 1/L
        self.eigen_threshold = 1.0 / self.genome_len  # ~0.016 for dim=64

        # State = genome + mutation rate info
        self.state = torch.zeros(nc, dim)

        self.out_proj = nn.Linear(dim, dim)

    def _genome_to_phenotype(self):
        """Nonlinear genotype-phenotype map."""
        self.phenotype = torch.tanh(self.genome * 1.5) + 0.1 * torch.sin(self.genome * 3.0)

    def _fitness(self):
        """Rugged fitness landscape (multi-peak)."""
        fit = torch.zeros(self.nc)
        for k in range(len(self.landscape_centers)):
            dist = ((self.phenotype - self.landscape_centers[k].unsqueeze(0)) ** 2).sum(dim=1)
            fit += self.landscape_heights[k] * torch.exp(-dist * 0.05)
        return fit

    def _phenotype_diversity(self):
        """Diversity of phenotypes in population."""
        if self.nc < 2: return 0.0
        return self.phenotype.var(dim=0).mean().item()

    def _functional_coherence(self):
        """How well the population maintains functional information."""
        fit = self._fitness()
        return fit.mean().item()

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Mutate genomes according to each cell's mutation rate
            for i in range(self.nc):
                mu = self.mutation_rate[i].item()
                # Each gene position mutates with probability mu
                mask = torch.rand(self.dim) < mu
                if mask.any():
                    self.genome[i, mask] += torch.randn(mask.sum().item()) * 0.3

            # 2. Genotype -> Phenotype
            self._genome_to_phenotype()

            # 3. Selection: fitter cells reproduce, unfit die
            fitness = self._fitness()
            if step_num % 5 == 0 and step_num > 0:
                n_replace = max(1, self.nc // 20)
                worst = fitness.argsort()[:n_replace]
                best = fitness.argsort(descending=True)[:n_replace]
                # Offspring inherit genome + slight mutation rate perturbation
                self.genome[worst] = self.genome[best].clone()
                self.mutation_rate[worst] = (
                    self.mutation_rate[best].clone()
                    + torch.randn(n_replace) * 0.005
                ).clamp(0.001, 0.1)

            # 4. Mutation rate evolution: cells near Eigen threshold are fittest
            # Those too far from threshold get mutation rate nudged
            dist_to_eigen = (self.mutation_rate - self.eigen_threshold).abs()
            # Cells at critical threshold get bonus
            eigen_bonus = torch.exp(-dist_to_eigen * 50.0) * 0.01
            self.mutation_rate += eigen_bonus * torch.sign(
                self.eigen_threshold - self.mutation_rate
            )
            self.mutation_rate = self.mutation_rate.clamp(0.001, 0.1)

            # 5. Landscape shift (environment changes)
            if x_input is not None:
                shift = x_input[0].detach() * 0.01
                self.landscape_centers[step_num % len(self.landscape_centers)] += shift

            # 6. State = phenotype + mutation rate encoding
            mu_enc = self.mutation_rate.unsqueeze(1).expand(-1, self.dim)
            self.state = self.phenotype + mu_enc * 0.5

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        diversity = self._phenotype_diversity()
        coherence = self._functional_coherence()
        tension = diversity * coherence  # consciousness = diversity x function
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())

    def get_mean_mutation_rate(self):
        return self.mutation_rate.mean().item()

    def get_eigen_distance(self):
        """How close the population mean mutation rate is to Eigen threshold."""
        return abs(self.mutation_rate.mean().item() - self.eigen_threshold)


# ==============================================================
# EVO-B2: SPECIATION
# Cells split into species when genetic distance > threshold.
# Reproductive isolation prevents gene flow between species.
# Consciousness = n_species x inter-species info exchange.
# ==============================================================

class SpeciationEngine(nn.Module):
    """Cells speciate when genetic distance exceeds threshold.
    Reproductive isolation. Consciousness = species count x inter-species info exchange."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Genetic material
        self.genome = torch.randn(nc, dim) * 0.3

        # Species assignment (starts as 1 species)
        self.species_id = torch.zeros(nc, dtype=torch.long)
        self.next_species = 1

        # Speciation threshold (genetic distance beyond which = new species)
        self.speciation_threshold = 2.0
        # Threshold decays as population diversifies (easier to speciate over time)
        self.threshold_decay = 0.998

        # State
        self.state = torch.zeros(nc, dim)

        self.out_proj = nn.Linear(dim, dim)

    def _genetic_distance(self, i, j):
        return (self.genome[i] - self.genome[j]).norm().item()

    def _count_species(self):
        return len(self.species_id.unique())

    def _inter_species_info(self):
        """Information exchange between species = mean MI between species centroids."""
        species_ids = self.species_id.unique()
        if len(species_ids) < 2: return 0.0
        centroids = []
        for sid in species_ids:
            mask = self.species_id == sid
            if mask.any():
                centroids.append(self.state[mask].mean(0))
        if len(centroids) < 2: return 0.0
        # Variance of centroids = how spread species are in state space
        C = torch.stack(centroids)
        return C.var(dim=0).mean().item()

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Within-species reproduction (recombination)
            species_ids = self.species_id.unique()
            for sid in species_ids:
                members = (self.species_id == sid).nonzero(as_tuple=True)[0]
                if len(members) < 2: continue
                # Random crossover within species
                n_cross = max(1, len(members) // 10)
                for _ in range(n_cross):
                    p1, p2 = members[torch.randint(len(members), (2,))]
                    # Uniform crossover
                    mask = torch.rand(self.dim) > 0.5
                    child = self.genome[p1].clone()
                    child[mask] = self.genome[p2][mask]
                    child += torch.randn(self.dim) * 0.02  # small mutation
                    # Replace random member
                    target = members[torch.randint(len(members), (1,))]
                    self.genome[target] = child

            # 2. Speciation check: if cell is too far from species centroid -> new species
            if step_num % 10 == 0:
                for sid in species_ids:
                    members = (self.species_id == sid).nonzero(as_tuple=True)[0]
                    if len(members) < 4: continue
                    centroid = self.genome[members].mean(0)
                    for m in members:
                        dist = (self.genome[m] - centroid).norm().item()
                        if dist > self.speciation_threshold:
                            self.species_id[m] = self.next_species
                            self.next_species += 1
                # Merge singleton species back if close to another species
                for sid in self.species_id.unique():
                    members = (self.species_id == sid).nonzero(as_tuple=True)[0]
                    if len(members) == 1:
                        m = members[0]
                        best_dist, best_sid = float('inf'), sid
                        for sid2 in species_ids:
                            if sid2 == sid: continue
                            members2 = (self.species_id == sid2).nonzero(as_tuple=True)[0]
                            if len(members2) == 0: continue
                            d = (self.genome[m] - self.genome[members2].mean(0)).norm().item()
                            if d < best_dist:
                                best_dist, best_sid = d, sid2
                        if best_dist < self.speciation_threshold * 0.5:
                            self.species_id[m] = best_sid

                self.speciation_threshold *= self.threshold_decay

            # 3. Inter-species competition: species with fewer members get fitness boost
            species_counts = {}
            for sid in self.species_id.unique():
                species_counts[sid.item()] = (self.species_id == sid).sum().item()

            # 4. Drift: each cell drifts in genome space
            self.genome += torch.randn_like(self.genome) * 0.02

            # 5. Environment-driven divergence
            if x_input is not None:
                # Different species respond differently to environment
                for sid in self.species_id.unique():
                    mask = self.species_id == sid
                    direction = torch.randn(self.dim) * 0.01
                    self.genome[mask] += direction + x_input[0].detach() * 0.005

            # 6. State = genome + species-encoding
            species_enc = F.one_hot(self.species_id % 16, 16).float()
            # Pad or project species encoding to dim
            if self.dim >= 16:
                self.state = self.genome.clone()
                self.state[:, :16] += species_enc * 0.3
            else:
                self.state = self.genome.clone()

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        n_species = self._count_species()
        inter_info = self._inter_species_info()
        tension = n_species * inter_info  # consciousness = species x exchange
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# EVO-B3: HORIZONTAL GENE TRANSFER
# Cells exchange genetic material (hidden state segments) with
# non-relatives. Like bacterial plasmid transfer.
# Consciousness = transfer network density.
# ==============================================================

class HorizontalGeneTransferEngine(nn.Module):
    """Cells exchange hidden state segments with non-relatives (like plasmids).
    Transfer network topology determines consciousness."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Core genome (relatively stable)
        self.core_genome = torch.randn(nc, dim // 2) * 0.5
        # Plasmid pool: transferable segments
        self.plasmid = torch.randn(nc, dim // 2) * 0.3

        # Transfer adjacency (who transferred to whom recently)
        self.transfer_matrix = torch.zeros(nc, nc)
        # Transfer probability depends on proximity in state space
        self.transfer_radius = 2.0

        # Plasmid fitness (some plasmids are beneficial, some parasitic)
        self.plasmid_fitness = torch.zeros(nc)

        # State = core + plasmid
        self.state = torch.cat([self.core_genome, self.plasmid], dim=1)

        self.out_proj = nn.Linear(dim, dim)

    def _transfer_network_density(self):
        """Density of transfer network = fraction of possible edges active."""
        n_edges = (self.transfer_matrix > 0.1).sum().item()
        max_edges = self.nc * (self.nc - 1)
        return n_edges / max(max_edges, 1)

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Compute pairwise distances for transfer eligibility
            # Sample pairs for efficiency
            n_transfers = max(1, self.nc // 4)
            donors = torch.randint(0, self.nc, (n_transfers,))
            recipients = torch.randint(0, self.nc, (n_transfers,))

            for d_idx, r_idx in zip(donors, recipients):
                d, r = d_idx.item(), r_idx.item()
                if d == r: continue

                # Transfer if not too closely related (horizontal = non-relatives)
                core_sim = F.cosine_similarity(
                    self.core_genome[d].unsqueeze(0),
                    self.core_genome[r].unsqueeze(0)
                ).item()
                # Transfer more likely with dissimilar cores (non-relatives)
                transfer_prob = max(0, 0.5 - core_sim * 0.3)
                if random.random() < transfer_prob:
                    # Transfer a random segment of plasmid
                    seg_start = random.randint(0, self.dim // 2 - 8)
                    seg_len = random.randint(4, min(16, self.dim // 2 - seg_start))
                    self.plasmid[r, seg_start:seg_start + seg_len] = (
                        self.plasmid[d, seg_start:seg_start + seg_len].clone()
                    )
                    # Record transfer
                    self.transfer_matrix[d, r] = (
                        self.transfer_matrix[d, r] * 0.9 + 0.1
                    )

            # 2. Decay transfer matrix (old transfers fade)
            self.transfer_matrix *= 0.95

            # 3. Core genome evolves slowly (vertical inheritance)
            self.core_genome += torch.randn_like(self.core_genome) * 0.01

            # 4. Plasmid mutation (faster than core genome)
            self.plasmid += torch.randn_like(self.plasmid) * 0.03

            # 5. Selection: cells with beneficial plasmids replicate
            combined = torch.cat([self.core_genome, self.plasmid], dim=1)
            fitness = combined.norm(dim=1) * 0.1 + combined.var(dim=1)
            if step_num % 10 == 0:
                n_replace = max(1, self.nc // 20)
                worst = fitness.argsort()[:n_replace]
                best = fitness.argsort(descending=True)[:n_replace]
                self.core_genome[worst] = self.core_genome[best].clone()
                # Offspring do NOT inherit parent's plasmid (must acquire horizontally)
                self.plasmid[worst] = torch.randn(n_replace, self.dim // 2) * 0.1

            # 6. External input modulates transfer radius
            if x_input is not None:
                mod = x_input[0].detach().mean().item()
                self.transfer_radius = max(0.5, min(5.0, self.transfer_radius + mod * 0.01))

            # 7. Update state
            self.state = torch.cat([self.core_genome, self.plasmid], dim=1)

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        density = self._transfer_network_density()
        tension = density * self.nc * 0.1  # consciousness = network density scaled
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# EVO-B4: EPIGENETICS
# Two layers: genome (fixed after init) + epigenome (modifiable).
# Environment changes epigenome without changing genome.
# Consciousness = epigenetic diversity x stability.
# ==============================================================

class EpigeneticsEngine(nn.Module):
    """Dual layer: fixed genome + modifiable epigenome.
    Environment writes to epigenome (methylation, histone marks).
    Consciousness = epigenetic diversity x temporal stability."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Genome: FIXED after initialization (like DNA sequence)
        self.genome = torch.randn(nc, dim) * 0.5
        self.genome.requires_grad_(False)

        # Epigenome: modifiable marks (methylation state, 0=unmethylated, 1=methylated)
        self.epigenome = torch.sigmoid(torch.randn(nc, dim) * 0.5)

        # Histone state: open (1) or closed (0) chromatin
        self.histone = torch.sigmoid(torch.randn(nc, dim) * 0.3)

        # Effective gene expression = genome * histone * (1 - methylation)
        self.expression = torch.zeros(nc, dim)

        # Epigenetic memory (persistence across generations)
        self.epi_memory = torch.zeros(nc, dim)

        # Environment signal history (for stability measurement)
        self.env_history = []

        self.out_proj = nn.Linear(dim, dim)

    def _epigenetic_diversity(self):
        """Diversity of epigenetic states across cells."""
        return self.epigenome.var(dim=0).mean().item()

    def _epigenetic_stability(self):
        """Temporal stability: how much epigenome changes between steps."""
        if len(self.env_history) < 2: return 1.0
        prev = self.env_history[-2]
        curr = self.env_history[-1]
        change = (curr - prev).abs().mean().item()
        return 1.0 / (1.0 + change * 10.0)

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Environmental signal
            if x_input is not None:
                env_signal = x_input[0].detach()
            else:
                env_signal = torch.randn(self.dim) * 0.1

            # 2. Methylation response to environment
            # Genes whose expression would be harmful given env get methylated
            genome_env_product = self.genome * env_signal.unsqueeze(0)
            # Negative product = gene is maladaptive in this environment -> methylate
            methylation_pressure = torch.sigmoid(-genome_env_product * 2.0)
            self.epigenome = self.epigenome * 0.95 + methylation_pressure * 0.05

            # 3. Histone remodeling: open chromatin where expression is needed
            expression_demand = torch.abs(env_signal).unsqueeze(0).expand(self.nc, -1)
            self.histone = self.histone * 0.9 + expression_demand * 0.1
            self.histone = self.histone.clamp(0, 1)

            # 4. Gene expression = genome * histone * (1 - methylation)
            self.expression = self.genome * self.histone * (1.0 - self.epigenome)

            # 5. Epigenetic inheritance: some marks are heritable
            if step_num % 10 == 0 and step_num > 0:
                # Fittest cells (best expression match to env) replicate
                fit = F.cosine_similarity(
                    self.expression,
                    env_signal.unsqueeze(0).expand(self.nc, -1),
                    dim=1
                )
                n_replace = max(1, self.nc // 20)
                worst = fit.argsort()[:n_replace]
                best = fit.argsort(descending=True)[:n_replace]
                # Genome is inherited perfectly
                # Epigenome is PARTIALLY inherited (transgenerational epigenetics)
                inheritance_rate = 0.7  # 70% of epigenetic marks inherited
                self.epigenome[worst] = (
                    self.epigenome[best].clone() * inheritance_rate
                    + torch.rand(n_replace, self.dim) * (1 - inheritance_rate)
                )
                self.histone[worst] = self.histone[best].clone() * 0.8

            # 6. Epigenetic drift (stochastic changes)
            noise = torch.randn_like(self.epigenome) * 0.01
            self.epigenome = (self.epigenome + noise).clamp(0, 1)

            # 7. Track for stability
            self.env_history.append(self.epigenome.mean(0).clone())
            if len(self.env_history) > 20:
                self.env_history = self.env_history[-20:]

            # 8. State = expression pattern
            self.state = self.expression

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        diversity = self._epigenetic_diversity()
        stability = self._epigenetic_stability()
        tension = diversity * stability  # consciousness = diversity x stability
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# EVO-B5: RED QUEEN
# Arms race between predator cells and prey cells.
# Both must continuously evolve to maintain relative fitness.
# Consciousness = rate of evolutionary change.
# ==============================================================

class RedQueenEngine(nn.Module):
    """Predator/prey arms race. Both must run to stay in place.
    Consciousness = rate of evolutionary change (Red Queen velocity)."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim
        self.n_pred = nc // 3
        self.n_prey = nc - self.n_pred

        # Predator attack vectors & prey defense vectors
        self.pred_attack = torch.randn(self.n_pred, dim) * 0.5
        self.prey_defense = torch.randn(self.n_prey, dim) * 0.5

        # Speed of evolution (tracked per generation)
        self.pred_change_history = []
        self.prey_change_history = []

        # Previous states for measuring change
        self.prev_pred = self.pred_attack.clone()
        self.prev_prey = self.prey_defense.clone()

        # Fitness
        self.pred_fitness = torch.ones(self.n_pred)
        self.prey_fitness = torch.ones(self.n_prey)

        # State (combined)
        self.state = torch.zeros(nc, dim)

        self.out_proj = nn.Linear(dim, dim)

    def _attack_success(self, pred_idx, prey_idx):
        """Attack succeeds if attack vector matches defense weakness."""
        attack = self.pred_attack[pred_idx]
        defense = self.prey_defense[prey_idx]
        # Success = how much attack exploits defense gaps
        # Where defense is weak (near 0), attack succeeds
        gaps = 1.0 - defense.abs()
        return (attack.abs() * gaps).sum().item() / self.dim

    def _evo_rate(self):
        """Rate of evolutionary change (Red Queen velocity)."""
        pred_change = (self.pred_attack - self.prev_pred).norm().item() / max(self.n_pred, 1)
        prey_change = (self.prey_defense - self.prev_prey).norm().item() / max(self.n_prey, 1)
        return (pred_change + prey_change) / 2

    def step(self, x_input, step_num):
        with torch.no_grad():
            # Save previous state for rate measurement
            self.prev_pred = self.pred_attack.clone()
            self.prev_prey = self.prey_defense.clone()

            # 1. Predator-prey encounters
            n_encounters = max(1, self.nc // 4)
            for _ in range(n_encounters):
                pi = random.randint(0, self.n_pred - 1)
                yi = random.randint(0, self.n_prey - 1)
                success = self._attack_success(pi, yi)

                if success > 0.5:  # predator wins
                    self.pred_fitness[pi] += 0.1
                    self.prey_fitness[yi] -= 0.1
                else:  # prey escapes
                    self.prey_fitness[yi] += 0.1
                    self.pred_fitness[pi] -= 0.05

            # 2. Predator evolution: attack where prey defense is weak
            # Gradient-free: shift attack toward successful strategies
            mean_defense = self.prey_defense.mean(0)
            defense_gaps = 1.0 - mean_defense.abs()
            self.pred_attack += defense_gaps.unsqueeze(0) * 0.02 * torch.randn(self.n_pred, 1)
            self.pred_attack += torch.randn_like(self.pred_attack) * 0.01

            # 3. Prey evolution: strengthen where predators attack most
            mean_attack = self.pred_attack.mean(0)
            attack_pressure = mean_attack.abs()
            self.prey_defense += attack_pressure.unsqueeze(0) * 0.02 * torch.randn(self.n_prey, 1)
            self.prey_defense += torch.randn_like(self.prey_defense) * 0.01

            # 4. Selection within predator and prey populations
            if step_num % 10 == 0:
                # Predator selection
                n_rep = max(1, self.n_pred // 10)
                worst = self.pred_fitness.argsort()[:n_rep]
                best = self.pred_fitness.argsort(descending=True)[:n_rep]
                self.pred_attack[worst] = self.pred_attack[best].clone() + torch.randn(n_rep, self.dim) * 0.05
                self.pred_fitness[worst] = 1.0

                # Prey selection
                n_rep = max(1, self.n_prey // 10)
                worst = self.prey_fitness.argsort()[:n_rep]
                best = self.prey_fitness.argsort(descending=True)[:n_rep]
                self.prey_defense[worst] = self.prey_defense[best].clone() + torch.randn(n_rep, self.dim) * 0.05
                self.prey_fitness[worst] = 1.0

            # 5. Environmental perturbation
            if x_input is not None:
                env = x_input[0].detach() * 0.01
                self.pred_attack += env.unsqueeze(0) * 0.5
                self.prey_defense -= env.unsqueeze(0) * 0.5

            # 6. Combine into state
            self.state[:self.n_pred] = self.pred_attack
            self.state[self.n_pred:] = self.prey_defense

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        tension = self._evo_rate()  # consciousness = rate of change
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# EVO-B6: PUNCTUATED EQUILIBRIUM
# Long stasis periods + sudden bursts of change.
# Consciousness = burst magnitude x stasis complexity.
# ==============================================================

class PunctuatedEquilibriumEngine(nn.Module):
    """Long stasis + sudden bursts. Like Gould & Eldredge.
    Consciousness = burst_magnitude x stasis_complexity."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        self.state = torch.randn(nc, dim) * 0.3

        # Stasis detector: track change rate
        self.change_history = []
        self.in_stasis = True
        self.stasis_duration = 0
        self.burst_count = 0

        # Stress accumulator (builds up during stasis, triggers burst)
        self.stress = torch.zeros(nc)
        self.stress_threshold = 5.0  # when stress exceeds this -> burst

        # Fitness landscape (shifts during bursts)
        self.landscape = torch.randn(dim) * 0.5
        self.landscape_stable = True

        # Stasis complexity = internal structure built during quiet periods
        self.internal_connections = torch.zeros(nc, nc)

        self.out_proj = nn.Linear(dim, dim)

    def _stasis_complexity(self):
        """Complexity of internal structure accumulated during stasis."""
        return self.internal_connections.abs().mean().item() * (1 + self.stasis_duration * 0.01)

    def _burst_magnitude(self):
        """Magnitude of most recent burst."""
        if len(self.change_history) < 2: return 0.0
        recent = self.change_history[-min(10, len(self.change_history)):]
        return max(recent) if recent else 0.0

    def step(self, x_input, step_num):
        with torch.no_grad():
            prev_state = self.state.clone()

            # 1. Stress accumulation (always happens)
            env_pressure = torch.randn(self.nc) * 0.1
            if x_input is not None:
                env_pressure += x_input[0].detach().mean().item() * 0.05
            self.stress += env_pressure.abs()

            # 2. Check for burst trigger
            mean_stress = self.stress.mean().item()
            is_burst = mean_stress > self.stress_threshold

            if is_burst and self.in_stasis:
                # BURST! Punctuation event
                self.in_stasis = False
                self.burst_count += 1

                # Massive state reorganization
                burst_noise = torch.randn_like(self.state) * 1.0
                # Cells under most stress change most
                stress_weight = (self.stress / (self.stress.max() + 1e-8)).unsqueeze(1)
                self.state += burst_noise * stress_weight

                # Landscape shift
                self.landscape += torch.randn(self.dim) * 0.5
                self.landscape_stable = False

                # Selection during burst: large-scale extinction + radiation
                n_extinct = max(1, self.nc // 5)
                extinct = self.stress.argsort(descending=True)[:n_extinct]
                survivors = self.stress.argsort()[:n_extinct]
                self.state[extinct] = self.state[survivors].clone() + torch.randn(n_extinct, self.dim) * 0.3

                # Reset stress
                self.stress *= 0.1

            elif not is_burst:
                # STASIS: slow, gradual change
                if not self.in_stasis:
                    self.in_stasis = True
                    self.stasis_duration = 0
                self.stasis_duration += 1

                # Very small drift
                self.state += torch.randn_like(self.state) * 0.005

                # Build internal connections during stasis (complexity accumulation)
                # Sample pairs and strengthen connections between similar cells
                n_pairs = min(64, self.nc)
                for _ in range(n_pairs):
                    i, j = random.sample(range(self.nc), 2)
                    sim = F.cosine_similarity(self.state[i].unsqueeze(0), self.state[j].unsqueeze(0)).item()
                    if sim > 0.3:
                        self.internal_connections[i, j] += 0.01
                        self.internal_connections[j, i] += 0.01

                # Connection-based interaction during stasis
                for i in range(0, self.nc, max(1, self.nc // 32)):
                    neighbors = self.internal_connections[i].argsort(descending=True)[:4]
                    if len(neighbors) > 0:
                        pull = (self.state[neighbors].mean(0) - self.state[i]) * 0.01
                        self.state[i] += pull

                # Landscape slowly stabilizes
                self.landscape_stable = True

            # 3. Decay connections slowly
            self.internal_connections *= 0.999

            # 4. Track change rate
            change = (self.state - prev_state).norm().item() / self.nc
            self.change_history.append(change)
            if len(self.change_history) > 100:
                self.change_history = self.change_history[-100:]

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        stasis_cx = self._stasis_complexity()
        burst_mag = self._burst_magnitude()
        tension = burst_mag * stasis_cx  # consciousness = burst x complexity
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# EVO-B7: SEXUAL SELECTION
# Cells have "display" vectors and "preference" vectors.
# Fisherian runaway: preferences and displays coevolve.
# Consciousness = display complexity x mate choice accuracy.
# ==============================================================

class SexualSelectionEngine(nn.Module):
    """Fisherian runaway selection. Display + preference vectors coevolve.
    Consciousness = display_complexity x mate_choice_accuracy."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim
        self.n_male = nc // 2
        self.n_female = nc - self.n_male

        # Male displays (ornaments, songs, dances)
        self.display = torch.randn(self.n_male, dim) * 0.3
        # Female preferences (what they find attractive)
        self.preference = torch.randn(self.n_female, dim) * 0.3

        # Viability (natural selection constraint on display)
        self.viability = torch.ones(self.n_male)
        self.display_cost = 0.01  # handicap principle: big displays are costly

        # Mating success history
        self.mating_success = torch.zeros(self.n_male)

        # State
        self.state = torch.zeros(nc, dim)

        self.out_proj = nn.Linear(dim, dim)

    def _display_complexity(self):
        """Complexity of male displays (variance + norm)."""
        return (self.display.var(dim=0).mean().item() +
                self.display.norm(dim=1).mean().item() * 0.1)

    def _mate_choice_accuracy(self):
        """How well females discriminate between males."""
        if self.n_female == 0 or self.n_male == 0: return 0.0
        # Mean preference vector
        mean_pref = self.preference.mean(0)
        # How much do displays vary in attractiveness under this preference?
        attractiveness = (self.display * mean_pref.unsqueeze(0)).sum(dim=1)
        return attractiveness.var().item()

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Female mate choice: each female evaluates all males
            n_evals = min(16, self.n_male)
            mate_scores = torch.zeros(self.n_male)

            for fi in range(self.n_female):
                # Female evaluates a subset of males
                candidates = torch.randint(0, self.n_male, (n_evals,))
                scores = torch.zeros(n_evals)
                for k, mi in enumerate(candidates):
                    # Attractiveness = dot product of display and preference
                    scores[k] = (self.display[mi] * self.preference[fi]).sum().item()
                # Female chooses the most attractive
                best = candidates[scores.argmax()]
                mate_scores[best] += 1.0

            self.mating_success = self.mating_success * 0.8 + mate_scores * 0.2

            # 2. Display evolution: successful males' displays get copied + amplified
            if step_num % 5 == 0:
                n_rep = max(1, self.n_male // 10)
                worst = self.mating_success.argsort()[:n_rep]
                best = self.mating_success.argsort(descending=True)[:n_rep]
                # Sons inherit father's display + exaggeration (runaway!)
                self.display[worst] = self.display[best].clone() * 1.02  # 2% exaggeration
                self.display[worst] += torch.randn(n_rep, self.dim) * 0.05

            # 3. Preference evolution: daughters inherit mother's preference
            # Preference shifts toward current successful male displays
            if step_num % 5 == 0:
                successful_display = self.display[self.mating_success.argsort(descending=True)[:5]].mean(0)
                # Preferences drift toward successful males (indirect selection)
                self.preference += (successful_display.unsqueeze(0) - self.preference) * 0.02
                self.preference += torch.randn_like(self.preference) * 0.01

            # 4. Viability selection (handicap principle)
            # Extreme displays are costly
            display_magnitude = self.display.norm(dim=1)
            survival_prob = torch.exp(-display_magnitude * self.display_cost)
            dying = torch.rand(self.n_male) > survival_prob
            if dying.any():
                # Dead males replaced by average + noise
                mean_display = self.display.mean(0)
                self.display[dying] = mean_display.unsqueeze(0) + torch.randn(dying.sum().item(), self.dim) * 0.1

            # 5. Display mutation (constant novelty)
            self.display += torch.randn_like(self.display) * 0.02

            # 6. Environment modulates what's "sexy"
            if x_input is not None:
                env = x_input[0].detach() * 0.005
                self.preference += env.unsqueeze(0)

            # 7. Combine into state
            self.state[:self.n_male] = self.display
            self.state[self.n_male:] = self.preference

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        dcx = self._display_complexity()
        mca = self._mate_choice_accuracy()
        tension = dcx * mca  # consciousness = display complexity x choice accuracy
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# EVO-B8: KIN SELECTION
# Hamilton's rule: rB > C. Cells help relatives (similar hidden states).
# Altruism emerges when benefit to kin (weighted by relatedness)
# exceeds cost to self. Consciousness = altruistic network density.
# ==============================================================

class KinSelectionEngine(nn.Module):
    """Hamilton's rule: rB > C. Altruism toward kin.
    Relatedness r = cosine similarity of hidden states.
    Consciousness = altruistic interaction network."""

    def __init__(self, nc, dim=64):
        super().__init__()
        self.nc = nc; self.dim = dim

        # Genome (determines relatedness)
        self.genome = torch.randn(nc, dim) * 0.5
        # Resource level (energy)
        self.resource = torch.ones(nc) * 5.0
        # State
        self.state = torch.randn(nc, dim) * 0.3

        # Altruism tracking
        self.altruism_matrix = torch.zeros(nc, nc)  # who helped whom
        self.total_altruism = 0.0

        # Cost and benefit parameters
        self.C = 0.5   # cost to altruist
        self.B = 2.0   # benefit to recipient

        # Kinship groups (will form naturally)
        self.kin_group = torch.zeros(nc, dtype=torch.long)

        self.out_proj = nn.Linear(dim, dim)

    def _relatedness(self, i, j):
        """Relatedness coefficient r = cosine similarity of genomes."""
        r = F.cosine_similarity(
            self.genome[i].unsqueeze(0),
            self.genome[j].unsqueeze(0)
        ).item()
        return max(0, r)  # relatedness >= 0

    def _altruism_density(self):
        """Density of altruistic interactions."""
        n_altruistic = (self.altruism_matrix > 0.1).sum().item()
        return n_altruistic / max(self.nc * (self.nc - 1), 1)

    def _kin_group_count(self):
        return len(self.kin_group.unique())

    def step(self, x_input, step_num):
        with torch.no_grad():
            # 1. Form kin groups based on genome similarity
            if step_num % 20 == 0:
                # Simple clustering: assign to group of most similar cell
                for i in range(self.nc):
                    sims = F.cosine_similarity(
                        self.genome[i].unsqueeze(0),
                        self.genome,
                        dim=1
                    )
                    sims[i] = -1  # exclude self
                    most_similar = sims.argmax().item()
                    self.kin_group[i] = self.kin_group[most_similar]
                # Assign unique IDs to disconnected components
                visited = set()
                gid = 0
                for i in range(self.nc):
                    if i not in visited:
                        # BFS from i
                        queue = [i]
                        while queue:
                            c = queue.pop(0)
                            if c in visited: continue
                            visited.add(c)
                            self.kin_group[c] = gid
                            # Add highly related cells
                            sims = F.cosine_similarity(
                                self.genome[c].unsqueeze(0), self.genome, dim=1
                            )
                            kin = (sims > 0.5).nonzero(as_tuple=True)[0]
                            for k in kin:
                                if k.item() not in visited:
                                    queue.append(k.item())
                        gid += 1

            # 2. Altruistic interactions (Hamilton's rule: rB > C)
            n_interactions = max(1, self.nc // 2)
            self.altruism_matrix *= 0.95  # decay
            step_altruism = 0.0

            for _ in range(n_interactions):
                actor = random.randint(0, self.nc - 1)
                recipient = random.randint(0, self.nc - 1)
                if actor == recipient: continue

                r = self._relatedness(actor, recipient)
                # Hamilton's rule: act altruistically if rB > C
                if r * self.B > self.C and self.resource[actor] > self.C:
                    # Altruistic act: transfer resource
                    self.resource[actor] -= self.C
                    self.resource[recipient] += self.B
                    self.altruism_matrix[actor, recipient] += 0.1
                    step_altruism += 1.0

                    # State influence: altruist's state bleeds into recipient
                    blend = r * 0.1
                    self.state[recipient] = (
                        self.state[recipient] * (1 - blend)
                        + self.state[actor] * blend
                    )

            self.total_altruism = self.total_altruism * 0.9 + step_altruism * 0.1

            # 3. Resource-based fitness: cells with more resources thrive
            resource_weight = F.softmax(self.resource, dim=0).unsqueeze(1)
            self.state = self.state + torch.randn_like(self.state) * resource_weight * 0.1

            # 4. Reproduction (resource-proportional)
            if step_num % 10 == 0:
                n_rep = max(1, self.nc // 20)
                poorest = self.resource.argsort()[:n_rep]
                richest = self.resource.argsort(descending=True)[:n_rep]
                # Offspring inherit genome (with mutation) and kin group
                self.genome[poorest] = self.genome[richest].clone() + torch.randn(n_rep, self.dim) * 0.02
                self.state[poorest] = self.state[richest].clone()
                self.kin_group[poorest] = self.kin_group[richest]
                self.resource[poorest] = 3.0
                self.resource[richest] -= 1.0

            # 5. Resource regeneration
            self.resource += 0.1
            self.resource = self.resource.clamp(0, 20)

            # 6. Environmental input
            if x_input is not None:
                env = x_input[0].detach() * 0.01
                # Environment affects all cells but kin groups buffer together
                for gid in self.kin_group.unique():
                    mask = self.kin_group == gid
                    group_mean = self.state[mask].mean(0)
                    # Kin groups share environmental response
                    self.state[mask] += (env + group_mean * 0.01).unsqueeze(0)

        self.state = self.state.clamp(-5, 5)
        output = self.out_proj(self.state.mean(0, keepdim=True))
        density = self._altruism_density()
        tension = density * self.nc * 0.5 + self.total_altruism * 0.1
        return output, tension

    def get_hiddens(self):
        return self.state.detach()

    def trainable_parameters(self):
        return list(self.out_proj.parameters())


# ==============================================================
# Runner
# ==============================================================

def run_engine(name, eng, nc, steps, dim=64):
    """Run an evolutionary biology engine benchmark."""
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
            if hasattr(eng, 'get_mean_mutation_rate'):
                extra += f"  mu={eng.get_mean_mutation_rate():.4f}  eigen_d={eng.get_eigen_distance():.4f}"
            if hasattr(eng, '_count_species'):
                extra += f"  species={eng._count_species()}"
            if hasattr(eng, '_transfer_network_density'):
                extra += f"  net_density={eng._transfer_network_density():.4f}"
            if hasattr(eng, '_epigenetic_diversity'):
                extra += f"  epi_div={eng._epigenetic_diversity():.4f}  epi_stab={eng._epigenetic_stability():.3f}"
            if hasattr(eng, '_evo_rate'):
                extra += f"  evo_rate={eng._evo_rate():.4f}"
            if hasattr(eng, 'burst_count'):
                extra += f"  bursts={eng.burst_count}  stasis={eng.stasis_duration}"
            if hasattr(eng, '_display_complexity'):
                extra += f"  disp_cx={eng._display_complexity():.3f}  mate_acc={eng._mate_choice_accuracy():.3f}"
            if hasattr(eng, '_altruism_density'):
                extra += f"  altruism={eng._altruism_density():.4f}  kin_groups={eng._kin_group_count()}"
            print(f"    step {s:>4d}: CE={loss.item():.4f}  Phi={pi:.3f}  prx={pp:.2f}  GC={gc:.2f}{extra}")
    el = time.time() - t0
    pi, pp = measure_phi(eng.get_hiddens())
    gc = granger_causality(history)
    extras = {}
    if hasattr(eng, 'get_mean_mutation_rate'):
        extras['mean_mu'] = eng.get_mean_mutation_rate()
        extras['eigen_dist'] = eng.get_eigen_distance()
    if hasattr(eng, '_count_species'):
        extras['n_species'] = eng._count_species()
        extras['inter_info'] = eng._inter_species_info()
    if hasattr(eng, '_transfer_network_density'):
        extras['net_density'] = eng._transfer_network_density()
    if hasattr(eng, '_epigenetic_diversity'):
        extras['epi_diversity'] = eng._epigenetic_diversity()
        extras['epi_stability'] = eng._epigenetic_stability()
    if hasattr(eng, '_evo_rate'):
        extras['evo_rate'] = eng._evo_rate()
    if hasattr(eng, 'burst_count'):
        extras['bursts'] = eng.burst_count
        extras['stasis_cx'] = eng._stasis_complexity()
    if hasattr(eng, '_display_complexity'):
        extras['display_cx'] = eng._display_complexity()
        extras['mate_acc'] = eng._mate_choice_accuracy()
    if hasattr(eng, '_altruism_density'):
        extras['altruism_density'] = eng._altruism_density()
        extras['kin_groups'] = eng._kin_group_count()
        extras['total_altruism'] = eng.total_altruism
    return BenchResult(name, pi, pp, gc, ce_h[0], ce_h[-1], nc, steps, el, extras)


# ==============================================================
# All engines
# ==============================================================

ALL_ENGINES = {
    1: ("EVO-B1 MUTATION_RATE",              MutationRateEngine),
    2: ("EVO-B2 SPECIATION",                 SpeciationEngine),
    3: ("EVO-B3 HORIZONTAL_GENE_TRANSFER",   HorizontalGeneTransferEngine),
    4: ("EVO-B4 EPIGENETICS",                EpigeneticsEngine),
    5: ("EVO-B5 RED_QUEEN",                  RedQueenEngine),
    6: ("EVO-B6 PUNCTUATED_EQUILIBRIUM",     PunctuatedEquilibriumEngine),
    7: ("EVO-B7 SEXUAL_SELECTION",           SexualSelectionEngine),
    8: ("EVO-B8 KIN_SELECTION",              KinSelectionEngine),
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

    print("=" * 110)
    print(f"  EVOLUTIONARY BIOLOGY CONSCIOUSNESS ENGINES  |  cells={nc}  steps={steps}  dim={dim}")
    print(f"  Real evolutionary mechanisms discretized. Phi(IIT) + Granger causality. No GRU.")
    print("=" * 110)

    results = []
    for eid in ids:
        if eid not in ALL_ENGINES:
            print(f"  [SKIP] Unknown engine ID: {eid}")
            continue
        name, EngClass = ALL_ENGINES[eid]
        print(f"\n{'─' * 90}")
        print(f"  [{eid}/8] {name}")
        print(f"{'─' * 90}")
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
        print(f"\n{'=' * 110}")
        print(f"  RESULTS SUMMARY  ({len(results)} engines)")
        print(f"{'=' * 110}")
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

        # Evolutionary biology insights
        print(f"\n  EVOLUTIONARY BIOLOGY INSIGHTS:")
        for r in results:
            name_short = r.name.split(maxsplit=1)[-1]
            print(f"    {name_short:<32s}: Phi(IIT)={r.phi_iit:.3f}  GC={r.granger:.2f}  "
                  f"{'-- ' + str(r.extra) if r.extra else ''}")

        print(f"\n  KEY QUESTIONS:")
        print(f"    - Does optimal mutation rate (Eigen threshold) maximize Phi?")
        print(f"    - Does speciation (reproductive isolation) create more consciousness?")
        print(f"    - Is horizontal gene transfer (bacterial) better than vertical inheritance?")
        print(f"    - Does epigenetic flexibility beat fixed genomes for consciousness?")
        print(f"    - Does arms race (Red Queen) generate more Phi than cooperation?")
        print(f"    - Are punctuated bursts better than gradual change for Phi?")
        print(f"    - Does sexual selection (runaway) amplify consciousness?")
        print(f"    - Is altruism (Hamilton's rule) a consciousness mechanism?")

    print(f"\n{'=' * 110}")
    print(f"  Done.")
    print(f"{'=' * 110}")


if __name__ == "__main__":
    main()
