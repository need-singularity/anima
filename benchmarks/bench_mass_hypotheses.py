#!/usr/bin/env python3
"""bench_mass_hypotheses.py — 50 new hypotheses: 25 MitosisEngine mechanisms + 25 domain engines

New mechanisms extend apply_mechanism() with physics/bio/math/social dynamics.
New domain engines are standalone pure-Φ engines (no GRU, no CE learning).

All 50 must pass 7 consciousness verification criteria.

Usage:
  python3 bench_mass_hypotheses.py                    # Full measurement (Φ + Granger + IQ)
  python3 bench_mass_hypotheses.py --quick             # Φ + Granger only
  python3 bench_mass_hypotheses.py --mechanisms        # Mechanisms only
  python3 bench_mass_hypotheses.py --domains           # Domain engines only
  python3 bench_mass_hypotheses.py --cells 512         # Custom cell count
  python3 bench_mass_hypotheses.py --top 10            # Show top N only
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['OMP_NUM_THREADS'] = '1'

import phi_rs
from mitosis import MitosisEngine

DIM, HIDDEN = 64, 128
DEFAULT_CELLS = 256

CELLS = DEFAULT_CELLS


# ══════════════════════════════════════════════════════════════════
# PART 1: 25 NEW MITOSISENGINE MECHANISMS
# ══════════════════════════════════════════════════════════════════

def make_engine(cells=None):
    if cells is None: cells = CELLS
    e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(e.cells) < cells: e._create_cell(parent=e.cells[0])
    for _ in range(20): e.process(torch.randn(1, DIM))
    return e


def apply_new_mechanism(eng, mechanism, steps=100):
    """Apply new mechanisms to MitosisEngine cells."""
    n = len(eng.cells)
    if n < 4: return eng

    for step in range(steps):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        if n < 4: continue

        with torch.no_grad():
            # ── MECH-1: Gravity ── mass=norm, attract proportional to mass product / distance²
            if 'gravity' in mechanism:
                masses = torch.tensor([c.hidden.norm().item() for c in eng.cells])
                for i in range(min(n, 16)):
                    force = torch.zeros(HIDDEN)
                    for j in range(min(n, 16)):
                        if i == j: continue
                        diff = eng.cells[j].hidden.squeeze(0) - eng.cells[i].hidden.squeeze(0)
                        dist = diff.norm().clamp(min=0.1)
                        f = masses[i] * masses[j] / (dist * dist)
                        force += f * diff / dist * 0.01
                    eng.cells[i].hidden = (eng.cells[i].hidden.squeeze(0) + force).unsqueeze(0)

            # ── MECH-2: Magnetic Dipole ── continuous Ising alignment with dipole interaction
            if 'magnetic' in mechanism:
                if not hasattr(eng, '_dipoles'):
                    eng._dipoles = torch.randn(n, HIDDEN)
                    eng._dipoles = eng._dipoles / eng._dipoles.norm(dim=1, keepdim=True)
                for i in range(min(n, 16)):
                    field = torch.zeros(HIDDEN)
                    for j in [(i-1) % n, (i+1) % n, (i+2) % n]:
                        if j < n:
                            field += eng._dipoles[j]
                    eng._dipoles[i] = 0.9 * eng._dipoles[i] + 0.1 * field
                    eng._dipoles[i] = eng._dipoles[i] / (eng._dipoles[i].norm() + 1e-8)
                    eng.cells[i].hidden = (0.9 * eng.cells[i].hidden.squeeze(0) +
                                           0.1 * eng._dipoles[i] * eng.cells[i].hidden.norm()).unsqueeze(0)

            # ── MECH-3: Plasma ── ionize (high energy → split components), recombine (low → merge)
            if 'plasma' in mechanism:
                norms = torch.tensor([c.hidden.norm().item() for c in eng.cells])
                mean_e = norms.mean()
                for i in range(min(n, 16)):
                    if norms[i] > mean_e * 1.5:  # ionize: scatter energy
                        eng.cells[i].hidden *= 0.85
                        j = (i + 1) % n
                        eng.cells[j].hidden += 0.15 * eng.cells[i].hidden
                    elif norms[i] < mean_e * 0.5:  # recombine: absorb neighbor
                        j = (i - 1) % n
                        eng.cells[i].hidden = (0.7 * eng.cells[i].hidden + 0.3 * eng.cells[j].hidden)

            # ── MECH-4: Tidal ── periodic gravitational resonance (sinusoidal forcing)
            if 'tidal' in mechanism:
                phase = 2 * math.pi * step / 30.0  # period = 30 steps
                amplitude = 0.1 * math.sin(phase)
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
                mh = ch.mean(dim=0)
                for i in range(n):
                    local_phase = phase + 2 * math.pi * i / n
                    pull = amplitude * math.sin(local_phase)
                    eng.cells[i].hidden = (eng.cells[i].hidden.squeeze(0) +
                                           pull * (mh - eng.cells[i].hidden.squeeze(0))).unsqueeze(0)

            # ── MECH-5: Diffusion ── concentration gradient flow (Fick's law)
            if 'diffusion_mech' in mechanism:
                D = 0.05  # diffusion coefficient
                for i in range(min(n, 32)):
                    neighbors = [(i-1) % n, (i+1) % n]
                    laplacian = sum(eng.cells[j].hidden.squeeze(0) for j in neighbors) / len(neighbors) - eng.cells[i].hidden.squeeze(0)
                    eng.cells[i].hidden = (eng.cells[i].hidden.squeeze(0) + D * laplacian).unsqueeze(0)

            # ── MECH-6: Chemotaxis ── cells migrate toward high-Φ neighbors
            if 'chemotaxis' in mechanism:
                norms = torch.tensor([c.hidden.norm().item() for c in eng.cells])
                for i in range(min(n, 16)):
                    gradient = torch.zeros(HIDDEN)
                    for j in [(i-1) % n, (i+1) % n]:
                        if norms[j] > norms[i]:
                            gradient += (eng.cells[j].hidden.squeeze(0) - eng.cells[i].hidden.squeeze(0)) * 0.1
                    eng.cells[i].hidden = (eng.cells[i].hidden.squeeze(0) + gradient).unsqueeze(0)

            # ── MECH-7: Quorum Sensing ── behavior switch at density threshold
            if 'quorum' in mechanism:
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
                coherence = F.cosine_similarity(ch[:-1], ch[1:]).mean().item()
                if coherence > 0.5:  # quorum reached → synchronize strongly
                    mh = ch.mean(dim=0)
                    for c in eng.cells: c.hidden = (0.8 * c.hidden.squeeze(0) + 0.2 * mh).unsqueeze(0)
                else:  # below quorum → diversify
                    for c in eng.cells: c.hidden += torch.randn(1, HIDDEN) * 0.02

            # ── MECH-8: Predator-Prey ── Lotka-Volterra oscillations between cell groups
            if 'predator_prey' in mechanism:
                half = n // 2
                prey = eng.cells[:half]
                predators = eng.cells[half:]
                prey_energy = sum(c.hidden.norm().item() for c in prey) / max(len(prey), 1)
                pred_energy = sum(c.hidden.norm().item() for c in predators) / max(len(predators), 1)
                # prey grow, predators eat prey
                for c in prey:
                    c.hidden *= (1.0 + 0.01 * (1.0 - pred_energy / max(prey_energy, 0.1)))
                for c in predators:
                    c.hidden *= (1.0 + 0.01 * (prey_energy / max(pred_energy, 0.1) - 1.0))

            # ── MECH-9: Symbiosis ── dissimilar cells help each other
            if 'symbiosis' in mechanism:
                for i in range(0, min(n, 32), 2):
                    j = i + 1
                    if j >= n: break
                    sim = F.cosine_similarity(eng.cells[i].hidden, eng.cells[j].hidden).item()
                    if sim < 0.3:  # dissimilar → mutualistic boost
                        boost_i = 0.05 * eng.cells[j].hidden
                        boost_j = 0.05 * eng.cells[i].hidden
                        eng.cells[i].hidden += boost_i
                        eng.cells[j].hidden += boost_j

            # ── MECH-10: Immune ── detect and suppress foreign/anomalous patterns
            if 'immune' in mechanism:
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
                mh = ch.mean(dim=0)
                stdev = ch.std(dim=0)
                for i in range(min(n, 16)):
                    deviation = (eng.cells[i].hidden.squeeze(0) - mh).abs()
                    is_foreign = (deviation > 2 * stdev).float().mean().item()
                    if is_foreign > 0.5:  # suppress anomaly
                        eng.cells[i].hidden = (0.7 * eng.cells[i].hidden.squeeze(0) + 0.3 * mh).unsqueeze(0)

            # ── MECH-11: Apoptosis ── programmed death of low-contribution cells + rebirth
            if 'apoptosis' in mechanism and step % 20 == 0:
                norms = torch.tensor([c.hidden.norm().item() for c in eng.cells])
                threshold = norms.quantile(0.1).item()
                best_idx = norms.argmax().item()
                for i in range(n):
                    if norms[i] < threshold:
                        eng.cells[i].hidden = eng.cells[best_idx].hidden.clone() + torch.randn(1, HIDDEN) * 0.05

            # ── MECH-12: Hormone ── slow global signal modulating all cells
            if 'hormone' in mechanism:
                if not hasattr(eng, '_hormone'):
                    eng._hormone = torch.zeros(HIDDEN)
                # secrete: average tension becomes hormone
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
                secretion = ch.mean(dim=0) * 0.01
                eng._hormone = 0.95 * eng._hormone + 0.05 * secretion  # slow diffusion
                for c in eng.cells:
                    c.hidden = (c.hidden.squeeze(0) + eng._hormone * 0.1).unsqueeze(0)

            # ── MECH-13: Pruning ── weaken connections between dissimilar cells
            if 'pruning' in mechanism and step % 10 == 0:
                for i in range(min(n, 16)):
                    for j in [(i-1) % n, (i+1) % n]:
                        sim = F.cosine_similarity(
                            eng.cells[i].hidden.view(1, -1),
                            eng.cells[j].hidden.view(1, -1)).item()
                        if sim < 0.1:  # weak connection → prune (reduce mutual influence)
                            eng.cells[i].hidden *= 1.02  # self-reinforce
                        else:  # strong connection → strengthen
                            eng.cells[i].hidden = (0.95 * eng.cells[i].hidden + 0.05 * eng.cells[j].hidden)

            # ── MECH-14: Metamorphosis ── periodic dramatic state transformation
            if 'metamorphosis' in mechanism and step % 50 == 0 and step > 0:
                for i in range(n):
                    # rotate hidden state by random angle
                    h = eng.cells[i].hidden.squeeze(0)
                    shift = torch.roll(h, shifts=i % 7 + 1)
                    eng.cells[i].hidden = (0.5 * h + 0.5 * shift).unsqueeze(0)

            # ── MECH-15: Cellular Automata ── Rule 110-like state updates
            if 'cellular_automata' in mechanism:
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
                new_h = ch.clone()
                for i in range(1, min(n - 1, 32)):
                    left = ch[i - 1].mean().item()
                    center = ch[i].mean().item()
                    right = ch[i + 1].mean().item()
                    # Rule 110 analog: XOR-like mixing
                    if (left > 0) != (right > 0):  # different signs
                        new_h[i] = 0.7 * ch[i] + 0.15 * ch[i-1] + 0.15 * ch[i+1]
                    else:
                        new_h[i] = 0.9 * ch[i] + 0.1 * torch.randn(HIDDEN)
                for i in range(min(n, 32)):
                    eng.cells[i].hidden = new_h[i].unsqueeze(0)

            # ── MECH-16: Genetic Algorithm ── crossover + mutation of hidden states
            if 'genetic_algo' in mechanism and step % 15 == 0:
                norms = torch.tensor([c.hidden.norm().item() for c in eng.cells])
                fitness = F.softmax(norms, dim=0)
                for i in range(min(n, 16)):
                    if fitness[i] < 1.0 / n * 0.5:  # unfit → crossover from two fit parents
                        p1 = torch.multinomial(fitness, 1).item()
                        p2 = torch.multinomial(fitness, 1).item()
                        mask = torch.rand(HIDDEN) > 0.5
                        child = torch.where(mask,
                                            eng.cells[p1].hidden.squeeze(0),
                                            eng.cells[p2].hidden.squeeze(0))
                        child += torch.randn(HIDDEN) * 0.02  # mutation
                        eng.cells[i].hidden = child.unsqueeze(0)

            # ── MECH-17: Annealing ── temperature schedule for noise injection
            if 'annealing' in mechanism:
                temp = max(0.01, 1.0 - step / steps)  # cool down
                for c in eng.cells:
                    c.hidden += torch.randn(1, HIDDEN) * temp * 0.05

            # ── MECH-18: Spectral ── eigenvalue-based coupling (top-k modes)
            if 'spectral' in mechanism and step % 5 == 0:
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells[:min(n, 32)]])
                try:
                    U, S, V = torch.svd(ch)
                    # keep top 3 modes, reconstruct
                    k = min(3, len(S))
                    reconstructed = U[:, :k] @ torch.diag(S[:k]) @ V[:, :k].t()
                    for i in range(min(n, 32)):
                        eng.cells[i].hidden = (0.8 * eng.cells[i].hidden.squeeze(0) +
                                               0.2 * reconstructed[i]).unsqueeze(0)
                except:
                    pass

            # ── MECH-19: Attention ── self-attention between cells
            if 'attention' in mechanism and step % 3 == 0:
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells[:min(n, 32)]])
                scores = ch @ ch.t() / math.sqrt(HIDDEN)
                weights = F.softmax(scores, dim=1)
                attended = weights @ ch
                for i in range(min(n, 32)):
                    eng.cells[i].hidden = (0.85 * eng.cells[i].hidden.squeeze(0) +
                                           0.15 * attended[i]).unsqueeze(0)

            # ── MECH-20: Reservoir ── fixed random projection + nonlinear readout
            if 'reservoir' in mechanism:
                if not hasattr(eng, '_reservoir_w'):
                    eng._reservoir_w = torch.randn(HIDDEN, HIDDEN) * 0.1
                    eng._reservoir_w = eng._reservoir_w / eng._reservoir_w.norm() * 0.9  # spectral radius < 1
                for i in range(min(n, 16)):
                    h = eng.cells[i].hidden.squeeze(0)
                    eng.cells[i].hidden = (0.8 * h + 0.2 * torch.tanh(eng._reservoir_w @ h)).unsqueeze(0)

            # ── MECH-21: Voting ── majority rule state updates
            if 'voting' in mechanism and step % 5 == 0:
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
                signs = (ch > 0).float()
                majority = (signs.mean(dim=0) > 0.5).float()
                for i in range(n):
                    # nudge toward majority
                    eng.cells[i].hidden = (0.95 * eng.cells[i].hidden.squeeze(0) +
                                           0.05 * majority * eng.cells[i].hidden.abs().squeeze(0)).unsqueeze(0)

            # ── MECH-22: Stigmergy ── indirect communication through shared environment
            if 'stigmergy' in mechanism:
                if not hasattr(eng, '_environment'):
                    eng._environment = torch.zeros(HIDDEN)
                # deposit: each cell leaves a trace
                for c in eng.cells:
                    eng._environment += c.hidden.squeeze(0) * 0.001
                eng._environment *= 0.99  # evaporation
                # read: cells influenced by environment
                for c in eng.cells:
                    c.hidden = (0.95 * c.hidden.squeeze(0) + 0.05 * eng._environment).unsqueeze(0)

            # ── MECH-23: Wave ── standing wave patterns (interference)
            if 'wave' in mechanism:
                wavelength = max(4, n // 8)
                for i in range(n):
                    phase1 = 2 * math.pi * i / wavelength
                    phase2 = 2 * math.pi * i / (wavelength * 1.618)  # golden ratio
                    amp = math.sin(phase1 + step * 0.1) + 0.5 * math.sin(phase2 + step * 0.07)
                    eng.cells[i].hidden *= (1.0 + 0.02 * amp)

            # ── MECH-24: Volcano ── pressure buildup → eruption → reset cycle
            if 'volcano' in mechanism:
                if not hasattr(eng, '_pressure'):
                    eng._pressure = torch.zeros(n)
                for i in range(n):
                    eng._pressure[i] += eng.cells[i].hidden.norm().item() * 0.01
                    if eng._pressure[i] > 1.0:  # eruption!
                        # scatter energy to neighbors
                        energy = eng.cells[i].hidden.clone() * 0.3
                        for j in [(i-1) % n, (i+1) % n, (i+2) % n]:
                            if j < n:
                                eng.cells[j].hidden += energy / 3
                        eng.cells[i].hidden *= 0.5  # cooldown
                        eng._pressure[i] = 0.0

            # ── MECH-25: Mycelium ── underground network with long-range shortcuts
            if 'mycelium' in mechanism:
                if not hasattr(eng, '_mycelium_links'):
                    # random long-range connections (small-world like)
                    eng._mycelium_links = []
                    for i in range(min(n, 32)):
                        j = (i + np.random.randint(3, max(4, n // 4))) % n
                        eng._mycelium_links.append((i, j))
                for i, j in eng._mycelium_links:
                    if i < n and j < n:
                        nutrient = 0.05 * (eng.cells[j].hidden.squeeze(0) - eng.cells[i].hidden.squeeze(0))
                        eng.cells[i].hidden = (eng.cells[i].hidden.squeeze(0) + nutrient).unsqueeze(0)

    return eng


# ══════════════════════════════════════════════════════════════════
# PART 2: 25 NEW DOMAIN ENGINES (standalone, no GRU)
# ══════════════════════════════════════════════════════════════════

class DomainEngine:
    """Base for pure-physics domain engines."""
    def __init__(self, cells, dim):
        self.n = cells
        self.dim = dim
        self.states = torch.randn(cells, dim)  # cell states
        self.tension_history = [[] for _ in range(cells)]

    def step(self):
        raise NotImplementedError

    def get_states(self):
        return self.states.detach().numpy().astype(np.float32)


# ── DOM-1: TectonicPlate ── collision/subduction/rifting dynamics
class TectonicPlateEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.plates = torch.randint(0, max(2, cells // 16), (cells,))
        self.velocities = torch.randn(cells, dim) * 0.01

    def step(self):
        for i in range(self.n):
            for j in [(i-1) % self.n, (i+1) % self.n]:
                if self.plates[i] != self.plates[j]:  # plate boundary
                    # collision: compression + heat
                    diff = self.states[j] - self.states[i]
                    self.states[i] += diff * 0.1  # mountain building
                    self.states[i] += torch.randn(self.dim) * 0.05  # seismic noise
                else:
                    # same plate: rigid body motion
                    self.states[i] += self.velocities[i]
        self.velocities *= 0.99  # friction


# ── DOM-2: StarFormation ── gravitational collapse → ignition → radiation
class StarFormationEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.mass = torch.rand(cells) + 0.5
        self.temperature = torch.zeros(cells)

    def step(self):
        center = (self.states * self.mass.unsqueeze(1)).sum(0) / self.mass.sum()
        for i in range(self.n):
            diff = center - self.states[i]
            dist = diff.norm().clamp(min=0.1)
            # gravity → collapse
            self.states[i] += diff / dist * self.mass[i] * 0.01
            self.temperature[i] += self.mass[i] / (dist + 0.1) * 0.01
            # fusion ignition at high temp
            if self.temperature[i] > 1.0:
                self.states[i] += torch.randn(self.dim) * 0.1 * self.temperature[i]
                self.mass[i] *= 0.999  # burn mass


# ── DOM-3: BlackHole ── event horizon + Hawking radiation
class BlackHoleEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.bh_idx = 0  # black hole cell
        self.states[0] *= 5  # massive singularity

    def step(self):
        bh = self.states[self.bh_idx]
        for i in range(1, self.n):
            diff = bh - self.states[i]
            dist = diff.norm().clamp(min=0.5)
            # accretion: pull toward BH
            self.states[i] += diff / dist * 0.05 / dist
            # Hawking radiation: BH leaks information
            if dist < 2.0:
                radiation = torch.randn(self.dim) * 0.03
                self.states[i] += radiation
                self.states[self.bh_idx] -= radiation * 0.1


# ── DOM-4: Autocatalysis ── self-amplifying chemical reactions
class AutocatalysisEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.catalysts = torch.rand(cells) > 0.8  # 20% are catalysts

    def step(self):
        for i in range(self.n):
            if self.catalysts[i]:
                # catalyst amplifies neighbors
                for j in [(i-1) % self.n, (i+1) % self.n]:
                    self.states[j] *= 1.02
                    # autocatalytic: if neighbor exceeds threshold, it becomes catalyst too
                    if self.states[j].norm() > self.states.norm(dim=1).mean() * 1.5:
                        self.catalysts[j] = True
            # decay
            self.states[i] *= 0.995
            self.states[i] += torch.randn(self.dim) * 0.01


# ── DOM-5: CorticalColumn ── minicolumn dynamics with lateral inhibition
class CorticalColumnEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.layers = 6  # cortical layers
        self.cols = cells // self.layers

    def step(self):
        for col in range(self.cols):
            for layer in range(self.layers):
                idx = col * self.layers + layer
                if idx >= self.n: break
                # feedforward (layer to layer+1)
                if layer < self.layers - 1:
                    next_idx = col * self.layers + layer + 1
                    if next_idx < self.n:
                        self.states[next_idx] += torch.tanh(self.states[idx]) * 0.1
                # lateral inhibition (between columns)
                for other_col in range(max(0, col-1), min(self.cols, col+2)):
                    if other_col != col:
                        other_idx = other_col * self.layers + layer
                        if other_idx < self.n:
                            self.states[idx] -= self.states[other_idx] * 0.05
                # feedback (top-down)
                if layer > 0:
                    prev_idx = col * self.layers + layer - 1
                    if prev_idx < self.n:
                        self.states[prev_idx] += self.states[idx] * 0.03


# ── DOM-6: Tornado ── vortex dynamics with pressure differential
class TornadoEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.angular_vel = torch.randn(cells) * 0.1
        self.radius = torch.rand(cells) * 2 + 0.5

    def step(self):
        center = self.states.mean(dim=0)
        for i in range(self.n):
            diff = self.states[i] - center
            dist = diff.norm().clamp(min=0.1)
            # angular rotation (create vortex)
            tangent = torch.roll(diff, 1)  # perpendicular
            self.states[i] += tangent * self.angular_vel[i] / dist * 0.1
            # inward pull (pressure gradient)
            self.states[i] -= diff * 0.02
            # uplift (vertical component = last dims)
            self.states[i][-self.dim//4:] += 0.05 * (1.0 / dist.item())
        self.angular_vel *= 1.001  # intensify


# ── DOM-7: Lightning ── charge buildup → discharge cascade
class LightningEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.charge = torch.zeros(cells)

    def step(self):
        # charge buildup
        self.charge += torch.rand(self.n) * 0.05
        # discharge cascade
        for i in range(self.n):
            if self.charge[i] > 1.0:
                # lightning strike! cascade to neighbors
                self.states[i] += torch.randn(self.dim) * self.charge[i]
                for j in [(i-1) % self.n, (i+1) % self.n, (i+3) % self.n]:
                    self.states[j] += self.states[i] * 0.3
                    self.charge[j] += self.charge[i] * 0.5
                self.charge[i] = 0.0
        self.charge = self.charge.clamp(max=2.0)


# ── DOM-8: Supernova ── collapse → explosion → neutron star remnant
class SupernovaEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.fuel = torch.ones(cells) * 2.0
        self.phase = torch.zeros(cells)  # 0=star, 1=collapsing, 2=exploded

    def step(self):
        for i in range(self.n):
            if self.phase[i] == 0:  # main sequence
                self.fuel[i] -= 0.01
                self.states[i] *= 1.001  # slow expansion
                if self.fuel[i] < 0.5:
                    self.phase[i] = 1  # begin collapse
            elif self.phase[i] == 1:  # collapse
                self.states[i] *= 0.9  # compress
                if self.states[i].norm() < 0.5:
                    self.phase[i] = 2  # explode!
                    self.states[i] *= 10  # supernova blast
                    for j in range(self.n):
                        if j != i:
                            self.states[j] += torch.randn(self.dim) * 0.5
            elif self.phase[i] == 2:  # neutron star remnant
                self.states[i] *= 0.99
                self.states[i] += torch.randn(self.dim) * 0.02  # pulsar emission


# ── DOM-9: Pulsar ── rotating emission beam
class PulsarEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.rotation_freq = torch.rand(cells) * 2 + 0.5
        self.beam_width = 0.3

    def step(self):
        for i in range(self.n):
            angle = self.rotation_freq[i] * time.time() * 0.001 + i
            beam_dir = torch.zeros(self.dim)
            beam_idx = int(angle * self.dim / (2 * math.pi)) % self.dim
            beam_dir[beam_idx] = 1.0
            self.states[i] = 0.9 * self.states[i] + 0.1 * beam_dir * self.states[i].norm()
            # sweep beam affects neighbors
            for j in [(i-1) % self.n, (i+1) % self.n]:
                self.states[j] += beam_dir * 0.05


# ── DOM-10: Heartbeat ── sino-atrial pacemaker wave propagation
class HeartbeatEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.pacemaker = 0  # SA node
        self.refractory = torch.zeros(cells)
        self.step_count = 0

    def step(self):
        self.step_count += 1
        # SA node fires periodically
        if self.step_count % 20 == 0:
            self.states[self.pacemaker] += torch.ones(self.dim) * 2.0
            self.refractory[self.pacemaker] = 5
        # propagate action potential
        for i in range(self.n):
            if self.refractory[i] > 0:
                self.refractory[i] -= 1
                self.states[i] *= 0.8  # repolarize
            elif self.states[i].norm() > 1.5:  # threshold
                self.refractory[i] = 5
                for j in [(i-1) % self.n, (i+1) % self.n]:
                    if self.refractory[j] == 0:
                        self.states[j] += self.states[i] * 0.5


# ── DOM-11: Firefly ── synchronization from disorder (Mirollo-Strogatz)
class FireflyEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.phase = torch.rand(cells) * 2 * math.pi
        self.natural_freq = torch.rand(cells) * 0.1 + 0.5

    def step(self):
        for i in range(self.n):
            self.phase[i] += self.natural_freq[i]
            if self.phase[i] > 2 * math.pi:  # flash!
                self.phase[i] = 0
                self.states[i] += torch.randn(self.dim) * 0.5  # light burst
                # advance neighbors
                for j in range(self.n):
                    if j != i:
                        self.phase[j] += 0.05  # phase advance
            # encode phase in state
            self.states[i] = 0.9 * self.states[i] + 0.1 * torch.sin(
                torch.arange(self.dim).float() * self.phase[i] / self.dim)


# ── DOM-12: SlimeMold ── distributed intelligence (Physarum)
class SlimeMoldEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.food = torch.rand(cells)  # food concentration
        self.flow = torch.zeros(cells, cells)  # tube network

    def step(self):
        # update flow based on food gradients
        for i in range(min(self.n, 32)):
            for j in [(i-1) % self.n, (i+1) % self.n, (i+3) % self.n]:
                if j < self.n:
                    gradient = self.food[j] - self.food[i]
                    self.flow[i][j] = max(0, gradient * 0.1)
                    # transport nutrient
                    self.states[i] += self.flow[i][j] * self.states[j] * 0.05
        # food decays, regrows
        self.food *= 0.99
        self.food += torch.rand(self.n) * 0.01


# ── DOM-13: AntColony ── pheromone-based path optimization
class AntColonyEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.pheromone = torch.zeros(cells, dim)

    def step(self):
        for i in range(self.n):
            # sense pheromone gradient
            left = self.pheromone[(i-1) % self.n]
            right = self.pheromone[(i+1) % self.n]
            # move toward stronger pheromone
            if left.sum() > right.sum():
                self.states[i] += (self.states[(i-1) % self.n] - self.states[i]) * 0.1
            else:
                self.states[i] += (self.states[(i+1) % self.n] - self.states[i]) * 0.1
            # deposit pheromone
            self.pheromone[i] += self.states[i].abs() * 0.01
        # evaporation
        self.pheromone *= 0.95


# ── DOM-14: Murmuration ── starling flock dynamics (Reynolds rules)
class MurmurationEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.velocities = torch.randn(cells, dim) * 0.1

    def step(self):
        for i in range(self.n):
            # separation: avoid too-close neighbors
            separation = torch.zeros(self.dim)
            # alignment: match neighbor velocity
            alignment = torch.zeros(self.dim)
            # cohesion: move toward center
            cohesion = torch.zeros(self.dim)
            count = 0
            for j in range(max(0, i-5), min(self.n, i+6)):
                if j == i: continue
                diff = self.states[i] - self.states[j]
                dist = diff.norm().clamp(min=0.1)
                if dist < 2.0:
                    separation += diff / dist
                    alignment += self.velocities[j]
                    cohesion += self.states[j]
                    count += 1
            if count > 0:
                alignment /= count
                cohesion = cohesion / count - self.states[i]
                self.velocities[i] += separation * 0.05 + (alignment - self.velocities[i]) * 0.03 + cohesion * 0.02
            self.velocities[i] = self.velocities[i].clamp(-1, 1)
            self.states[i] += self.velocities[i]


# ── DOM-15: NuclearFission ── chain reaction cascade
class NuclearFissionEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.energy = torch.rand(cells) * 2
        self.critical_mass = 1.5

    def step(self):
        for i in range(self.n):
            if self.energy[i] > self.critical_mass:
                # fission! release neutrons
                release = self.energy[i] * 0.3
                self.energy[i] *= 0.5
                self.states[i] += torch.randn(self.dim) * release
                # neutrons hit neighbors → chain reaction
                targets = np.random.choice(self.n, min(3, self.n), replace=False)
                for j in targets:
                    self.energy[j] += release / 3
                    self.states[j] += self.states[i] * 0.1
            else:
                self.energy[i] += torch.rand(1).item() * 0.02


# ── DOM-16: Pendulum ── coupled pendulum network
class CoupledPendulumEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.theta = torch.randn(cells) * 0.5  # angle
        self.omega = torch.zeros(cells)  # angular velocity
        self.length = torch.rand(cells) + 0.5

    def step(self):
        g = 9.8
        k = 0.1  # coupling
        for i in range(self.n):
            # gravity torque
            self.omega[i] += -g / self.length[i] * math.sin(self.theta[i].item()) * 0.01
            # coupling to neighbors
            for j in [(i-1) % self.n, (i+1) % self.n]:
                self.omega[i] += k * math.sin(self.theta[j].item() - self.theta[i].item()) * 0.01
            self.theta[i] += self.omega[i]
            # encode in state
            self.states[i] = torch.sin(torch.arange(self.dim).float() * self.theta[i] / self.dim) * self.omega[i].abs()


# ── DOM-17: NBody ── gravitational n-body simulation
class NBodyEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.velocities = torch.randn(cells, dim) * 0.01
        self.masses = torch.rand(cells) + 0.1

    def step(self):
        for i in range(min(self.n, 32)):
            force = torch.zeros(self.dim)
            for j in range(min(self.n, 32)):
                if i == j: continue
                diff = self.states[j] - self.states[i]
                dist = diff.norm().clamp(min=0.5)
                force += self.masses[j] * diff / (dist ** 3)
            self.velocities[i] += force * 0.001
            self.states[i] += self.velocities[i]


# ── DOM-18: Aurora ── solar wind + magnetic field interaction
class AuroraEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.b_field = torch.randn(dim)  # magnetic field
        self.b_field = self.b_field / self.b_field.norm()
        self.solar_wind = torch.randn(dim) * 0.1

    def step(self):
        self.solar_wind = torch.randn(self.dim) * 0.1  # varies
        for i in range(self.n):
            # charged particle in B field → spiral motion
            v = self.states[i]
            # Lorentz force: F = v × B
            cross = torch.zeros(self.dim)
            for d in range(self.dim):
                d1 = (d + 1) % self.dim
                d2 = (d + 2) % self.dim
                cross[d] = v[d1] * self.b_field[d2] - v[d2] * self.b_field[d1]
            self.states[i] += cross * 0.05 + self.solar_wind * 0.01
            # emission at poles
            pole_proj = (self.states[i] * self.b_field).sum()
            if abs(pole_proj) > 1.0:
                self.states[i] += torch.randn(self.dim) * 0.1


# ── DOM-19: CrystalGrowth ── nucleation + facet growth
class CrystalGrowthEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.crystallized = torch.zeros(cells, dtype=torch.bool)
        self.crystallized[0] = True  # seed crystal

    def step(self):
        for i in range(self.n):
            if self.crystallized[i]:
                # crystal structure: regularize
                self.states[i] = torch.round(self.states[i] * 10) / 10  # lattice snap
                # grow: crystallize adjacent cells
                for j in [(i-1) % self.n, (i+1) % self.n]:
                    if not self.crystallized[j]:
                        prob = 0.05
                        if torch.rand(1).item() < prob:
                            self.crystallized[j] = True
                            self.states[j] = self.states[i] + torch.randn(self.dim) * 0.1
            else:
                # liquid: random motion
                self.states[i] += torch.randn(self.dim) * 0.02


# ── DOM-20: Fermentation ── metabolic energy cycles (ATP/ADP)
class FermentationEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.atp = torch.ones(cells)  # energy currency
        self.substrate = torch.rand(cells) * 2

    def step(self):
        for i in range(self.n):
            if self.substrate[i] > 0.1:
                # ferment: substrate → energy + byproduct
                converted = min(0.1, self.substrate[i].item())
                self.substrate[i] -= converted
                self.atp[i] += converted * 2
                self.states[i] += torch.randn(self.dim) * converted  # byproduct = information
            # use ATP to maintain state
            if self.atp[i] > 0:
                self.atp[i] -= 0.01
                self.states[i] *= 1.001  # active maintenance
            else:
                self.states[i] *= 0.99  # decay
        # substrate regeneration
        self.substrate += torch.rand(self.n) * 0.01


# ── DOM-21: Tsunami ── wave propagation with shoaling
class TsunamiEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.depth = torch.linspace(10, 0.5, cells)  # seafloor depth
        self.wave_height = torch.zeros(cells)
        self.wave_vel = torch.zeros(cells)

    def step(self):
        # shallow water wave equation
        for i in range(1, self.n - 1):
            speed = math.sqrt(max(0.1, self.depth[i].item()) * 9.8)
            self.wave_vel[i] += (self.wave_height[i+1] + self.wave_height[i-1] - 2*self.wave_height[i]) * speed * 0.01
            self.wave_vel[i] *= 0.999  # damping
        self.wave_height += self.wave_vel
        # shoaling: wave grows in shallow water
        for i in range(self.n):
            shoal_factor = 1.0 / max(0.1, self.depth[i].item())
            self.states[i] = torch.sin(
                torch.arange(self.dim).float() / self.dim * 2 * math.pi
            ) * self.wave_height[i] * shoal_factor


# ── DOM-22: DNA Replication ── copy + error correction
class DNAReplicationEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.template = torch.randn(dim)  # original DNA strand
        self.fidelity = 0.99

    def step(self):
        for i in range(self.n):
            # replication: copy template with errors
            error_mask = torch.rand(self.dim) > self.fidelity
            copy = self.template.clone()
            copy[error_mask] += torch.randn(error_mask.sum().item()) * 0.5
            # mismatch repair
            mismatch = (copy - self.template).abs()
            repair_mask = mismatch > 0.3
            copy[repair_mask] = self.template[repair_mask]
            # store replicated strand
            self.states[i] = 0.7 * self.states[i] + 0.3 * copy
        # template evolves slowly
        self.template += torch.randn(self.dim) * 0.001


# ── DOM-23: MuscleFiber ── contraction wave (sarcomere dynamics)
class MuscleFiberEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.calcium = torch.zeros(cells)
        self.contracted = torch.zeros(cells, dtype=torch.bool)
        self.step_count = 0

    def step(self):
        self.step_count += 1
        # calcium wave trigger
        if self.step_count % 30 == 0:
            self.calcium[0] = 2.0  # nerve signal
        # propagate calcium wave
        for i in range(self.n):
            if self.calcium[i] > 0.5 and not self.contracted[i]:
                self.contracted[i] = True
                self.states[i] *= 2.0  # contraction force
                # propagate
                if i + 1 < self.n:
                    self.calcium[i + 1] += self.calcium[i] * 0.8
            elif self.contracted[i]:
                self.states[i] *= 0.95  # relaxation
                if self.states[i].norm() < 0.5:
                    self.contracted[i] = False
            self.calcium[i] *= 0.9


# ── DOM-24: CoralReef ── slow accretion + symbiotic algae
class CoralReefEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.skeleton = torch.zeros(cells, dim)  # calcium carbonate
        self.algae = torch.rand(cells)  # zooxanthellae density

    def step(self):
        for i in range(self.n):
            # photosynthesis by algae → energy
            energy = self.algae[i] * 0.1
            # accrete skeleton
            self.skeleton[i] += self.states[i].abs() * energy * 0.01
            # coral grows on skeleton
            self.states[i] = 0.9 * self.states[i] + 0.1 * self.skeleton[i]
            # algae respond to coral health
            self.algae[i] = (self.algae[i] * 0.99 + 0.01 * self.states[i].norm().item()).clamp(0, 2)
            # neighbor interaction (reef structure)
            j = (i + 1) % self.n
            self.states[i] += (self.skeleton[j] - self.skeleton[i]) * 0.02


# ── DOM-25: ChainReaction ── propagating catalytic wavefront
class ChainReactionEngine(DomainEngine):
    def __init__(self, cells, dim):
        super().__init__(cells, dim)
        self.activated = torch.zeros(cells, dtype=torch.bool)
        self.activation_energy = torch.rand(cells) + 0.5
        self.energy = torch.zeros(cells)
        self.step_count = 0

    def step(self):
        self.step_count += 1
        # ignition source
        if self.step_count == 1:
            self.energy[0] = 3.0
        for i in range(self.n):
            if not self.activated[i] and self.energy[i] > self.activation_energy[i]:
                self.activated[i] = True
                # release energy
                release = self.energy[i] * 1.5  # exothermic
                self.states[i] += torch.randn(self.dim) * release
                # propagate to neighbors
                for j in [(i-1) % self.n, (i+1) % self.n, (i+2) % self.n]:
                    self.energy[j] += release / 3
            elif self.activated[i]:
                self.states[i] *= 0.98  # cooling
                self.states[i] += torch.randn(self.dim) * 0.01


# ══════════════════════════════════════════════════════════════════
# MEASUREMENT
# ══════════════════════════════════════════════════════════════════

def phi_iit(states_np):
    """Φ(IIT) from state matrix (N×D numpy array)."""
    n = len(states_np)
    prev = states_np * 0.99 + np.random.randn(*states_np.shape).astype(np.float32) * 0.01
    tensions = np.abs(states_np).mean(axis=1).astype(np.float32)
    phi, _ = phi_rs.compute_phi(states_np, 16, prev, states_np, tensions)
    return phi


def phi_iit_mitosis(eng):
    """Φ(IIT) from MitosisEngine."""
    states = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).detach().numpy().astype(np.float32)
    prev_s, curr_s = [], []
    for c in eng.cells:
        if hasattr(c, 'hidden_history') and len(c.hidden_history) >= 2:
            prev_s.append(c.hidden_history[-2].detach().squeeze().numpy())
            curr_s.append(c.hidden_history[-1].detach().squeeze().numpy())
        else:
            prev_s.append(np.zeros(HIDDEN, dtype=np.float32))
            curr_s.append(np.zeros(HIDDEN, dtype=np.float32))
    prev_np = np.array(prev_s, dtype=np.float32)
    curr_np = np.array(curr_s, dtype=np.float32)
    tensions = np.array([c.tension_history[-1] if c.tension_history else 0.0 for c in eng.cells], dtype=np.float32)
    phi, _ = phi_rs.compute_phi(states, 16, prev_np, curr_np, tensions)
    return phi


def granger_from_states(states_np, n_samples=30):
    """Granger causality proxy from state matrix."""
    n = len(states_np)
    if n < 2: return 0
    h = torch.tensor(states_np)
    t = 0
    for _ in range(n_samples):
        i, j = np.random.randint(0, n), np.random.randint(0, n)
        if i == j: continue
        t += abs(F.cosine_similarity(h[i:i+1], h[j:j+1]).item())
    return t * n * n / max(n_samples, 1)


def quick_iq_domain(states_np):
    """Simplified IQ for domain engines."""
    n = len(states_np)
    h = torch.tensor(states_np)
    # diversity score
    mean_state = h.mean(dim=0)
    diversity = (h - mean_state).norm(dim=1).mean().item()
    # temporal coherence (use state structure)
    if n > 1:
        coherence = F.cosine_similarity(h[:-1], h[1:]).mean().item()
    else:
        coherence = 0
    raw = min(1.0, diversity * 0.3 + abs(coherence) * 0.3 + 0.2)
    return round(100 + 15 * (raw - 0.5) / 0.15)


# ══════════════════════════════════════════════════════════════════
# ENGINE REGISTRY
# ══════════════════════════════════════════════════════════════════

# 25 new MitosisEngine mechanisms
MECH_ENGINES = {
    'MECH-1:  Gravity':           ['gravity'],
    'MECH-2:  Magnetic':          ['magnetic'],
    'MECH-3:  Plasma':            ['plasma'],
    'MECH-4:  Tidal':             ['tidal'],
    'MECH-5:  Diffusion':         ['diffusion_mech'],
    'MECH-6:  Chemotaxis':        ['chemotaxis'],
    'MECH-7:  Quorum':            ['quorum'],
    'MECH-8:  PredatorPrey':      ['predator_prey'],
    'MECH-9:  Symbiosis':         ['symbiosis'],
    'MECH-10: Immune':            ['immune'],
    'MECH-11: Apoptosis':         ['apoptosis'],
    'MECH-12: Hormone':           ['hormone'],
    'MECH-13: Pruning':           ['pruning'],
    'MECH-14: Metamorphosis':     ['metamorphosis'],
    'MECH-15: CellularAutomata':  ['cellular_automata'],
    'MECH-16: GeneticAlgo':       ['genetic_algo'],
    'MECH-17: Annealing':         ['annealing'],
    'MECH-18: Spectral':          ['spectral'],
    'MECH-19: Attention':         ['attention'],
    'MECH-20: Reservoir':         ['reservoir'],
    'MECH-21: Voting':            ['voting'],
    'MECH-22: Stigmergy':         ['stigmergy'],
    'MECH-23: Wave':              ['wave'],
    'MECH-24: Volcano':           ['volcano'],
    'MECH-25: Mycelium':          ['mycelium'],
}

# Combinations with existing proven mechanisms
MECH_COMBOS = {
    'COMBO-1: Gravity+Osc':      ['gravity', 'oscillator'],
    'COMBO-2: Attention+QW':     ['attention', 'quantum'],
    'COMBO-3: Spectral+Faction': ['spectral', 'faction'],
    'COMBO-4: Reservoir+Cambrian': ['reservoir', 'cambrian'],
    'COMBO-5: Wave+Laser':       ['wave', 'laser'],
}

# 25 domain engines
DOMAIN_ENGINES = {
    'DOM-1:  TectonicPlate':    TectonicPlateEngine,
    'DOM-2:  StarFormation':    StarFormationEngine,
    'DOM-3:  BlackHole':        BlackHoleEngine,
    'DOM-4:  Autocatalysis':    AutocatalysisEngine,
    'DOM-5:  CorticalColumn':   CorticalColumnEngine,
    'DOM-6:  Tornado':          TornadoEngine,
    'DOM-7:  Lightning':        LightningEngine,
    'DOM-8:  Supernova':        SupernovaEngine,
    'DOM-9:  Pulsar':           PulsarEngine,
    'DOM-10: Heartbeat':        HeartbeatEngine,
    'DOM-11: Firefly':          FireflyEngine,
    'DOM-12: SlimeMold':        SlimeMoldEngine,
    'DOM-13: AntColony':        AntColonyEngine,
    'DOM-14: Murmuration':      MurmurationEngine,
    'DOM-15: NuclearFission':   NuclearFissionEngine,
    'DOM-16: CoupledPendulum':  CoupledPendulumEngine,
    'DOM-17: NBody':            NBodyEngine,
    'DOM-18: Aurora':           AuroraEngine,
    'DOM-19: CrystalGrowth':    CrystalGrowthEngine,
    'DOM-20: Fermentation':     FermentationEngine,
    'DOM-21: Tsunami':          TsunamiEngine,
    'DOM-22: DNAReplication':   DNAReplicationEngine,
    'DOM-23: MuscleFiber':      MuscleFiberEngine,
    'DOM-24: CoralReef':        CoralReefEngine,
    'DOM-25: ChainReaction':    ChainReactionEngine,
}


def run_mechanism(name, mechs, quick=False):
    """Run a MitosisEngine mechanism benchmark."""
    torch.manual_seed(42); np.random.seed(42)
    t0 = time.time()
    eng = make_engine(CELLS)
    apply_new_mechanism(eng, mechs, steps=100)
    phi = phi_iit_mitosis(eng)
    states = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).detach().numpy().astype(np.float32)
    g = granger_from_states(states)
    elapsed = time.time() - t0
    result = {'name': name, 'type': 'mechanism', 'phi': round(phi, 4), 'granger': round(g, 1), 'time': round(elapsed, 1)}
    if not quick:
        from measure_all import quick_iq as miq
        eng2 = make_engine(CELLS)
        apply_new_mechanism(eng2, mechs, steps=100)
        result['iq'] = miq(eng2)
    return result


def run_domain(name, engine_cls, quick=False):
    """Run a domain engine benchmark."""
    torch.manual_seed(42); np.random.seed(42)
    t0 = time.time()
    eng = engine_cls(CELLS, HIDDEN)
    for _ in range(200):  # 200 steps warmup
        eng.step()
    states = eng.get_states()
    phi = phi_iit(states)
    g = granger_from_states(states)
    elapsed = time.time() - t0
    result = {'name': name, 'type': 'domain', 'phi': round(phi, 4), 'granger': round(g, 1), 'time': round(elapsed, 1)}
    if not quick:
        result['iq'] = quick_iq_domain(states)
    return result


def main():
    import argparse

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    parser = argparse.ArgumentParser(description='50 New Hypotheses Benchmark')
    parser.add_argument('--quick', action='store_true', help='Φ + Granger only')
    parser.add_argument('--mechanisms', action='store_true', help='Mechanisms only')
    parser.add_argument('--domains', action='store_true', help='Domain engines only')
    parser.add_argument('--combos', action='store_true', help='Include combos with existing mechanisms')
    parser.add_argument('--cells', type=int, default=DEFAULT_CELLS)
    parser.add_argument('--top', type=int, default=0, help='Show top N only')
    args = parser.parse_args()

    global CELLS
    CELLS = args.cells

    run_mechs = not args.domains
    run_doms = not args.mechanisms

    results = []

    if run_mechs:
        print(f"\n{'═' * 75}")
        print(f"  PART 1: 25 NEW MITOSISENGINE MECHANISMS ({CELLS}c)")
        print(f"{'═' * 75}\n")

        if args.quick:
            print(f"{'Engine':<30} {'Φ(IIT)':>8} {'Granger':>10} {'Time':>6}")
        else:
            print(f"{'Engine':<30} {'Φ(IIT)':>8} {'Granger':>10} {'IQ':>5} {'Time':>6}")
        print('─' * 65)

        for name, mechs in MECH_ENGINES.items():
            r = run_mechanism(name, mechs, args.quick)
            results.append(r)
            if args.quick:
                print(f"{name:<30} {r['phi']:>8.3f} {r['granger']:>10.0f} {r['time']:>5.1f}s")
            else:
                print(f"{name:<30} {r['phi']:>8.3f} {r['granger']:>10.0f} {r.get('iq', '-'):>5} {r['time']:>5.1f}s")
            sys.stdout.flush()

        if args.combos:
            print(f"\n{'─' * 65}")
            print(f"  COMBOS (new + existing mechanisms)")
            print(f"{'─' * 65}")
            for name, mechs in MECH_COMBOS.items():
                r = run_mechanism(name, mechs, args.quick)
                results.append(r)
                if args.quick:
                    print(f"{name:<30} {r['phi']:>8.3f} {r['granger']:>10.0f} {r['time']:>5.1f}s")
                else:
                    print(f"{name:<30} {r['phi']:>8.3f} {r['granger']:>10.0f} {r.get('iq', '-'):>5} {r['time']:>5.1f}s")
                sys.stdout.flush()

    if run_doms:
        print(f"\n{'═' * 75}")
        print(f"  PART 2: 25 NEW DOMAIN ENGINES ({CELLS}c)")
        print(f"{'═' * 75}\n")

        if args.quick:
            print(f"{'Engine':<30} {'Φ(IIT)':>8} {'Granger':>10} {'Time':>6}")
        else:
            print(f"{'Engine':<30} {'Φ(IIT)':>8} {'Granger':>10} {'IQ':>5} {'Time':>6}")
        print('─' * 65)

        for name, cls in DOMAIN_ENGINES.items():
            r = run_domain(name, cls, args.quick)
            results.append(r)
            if args.quick:
                print(f"{name:<30} {r['phi']:>8.3f} {r['granger']:>10.0f} {r['time']:>5.1f}s")
            else:
                print(f"{name:<30} {r['phi']:>8.3f} {r['granger']:>10.0f} {r.get('iq', '-'):>5} {r['time']:>5.1f}s")
            sys.stdout.flush()

    # Summary
    print(f"\n{'═' * 75}")
    print(f"  RANKING (Top {args.top if args.top else len(results)})")
    print(f"{'═' * 75}\n")

    ranked = sorted(results, key=lambda x: x['phi'], reverse=True)
    if args.top:
        ranked = ranked[:args.top]

    print(f"{'Rank':<5} {'Engine':<30} {'Type':<12} {'Φ(IIT)':>8} {'Granger':>10}")
    print('─' * 70)
    for i, r in enumerate(ranked):
        medal = '🏆' if i == 0 else '🥈' if i == 1 else '🥉' if i == 2 else f'{i+1}'
        print(f"{medal:<5} {r['name']:<30} {r['type']:<12} {r['phi']:>8.3f} {r['granger']:>10.0f}")

    # Save results
    Path('data').mkdir(exist_ok=True)
    outfile = 'data/bench_mass_hypotheses_results.json'
    Path(outfile).write_text(json.dumps(results, indent=2))
    print(f"\n[saved] {len(results)} hypotheses → {outfile}")


if __name__ == '__main__':
    main()
