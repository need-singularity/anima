#!/usr/bin/env python3
"""bench_extreme_arch2.py — H-CX-527~537: Extreme Architecture Hypotheses Wave 2

4 new axes of attack:
  D. QUANTUM-THERMO:   527 Quantum Darwinism, 528 Dissipative, 529 Spin Glass
  E. INFO-GEOMETRY:    530 Fisher Information, 531 Holographic, 532 IIT Geometry
  F. LIFE-EVOLUTION:   533 Autopoietic, 534 Cambrian, 535 Symbiogenesis
  G. MATH-STRUCTURE:   536 Hypergraph, 537 Sheaf

Usage:
  python bench_extreme_arch2.py
  python bench_extreme_arch2.py --only 528 529 535
  python bench_extreme_arch2.py --cells 512 --steps 500
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys, time, math, argparse
import numpy as np
import torch
from dataclasses import dataclass, field

torch.set_grad_enabled(False)
torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ══════════════════════════════════════════════════════════
# Import measurement infrastructure from bench_extreme_arch
# ══════════════════════════════════════════════════════════
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_extreme_arch import (
    BenchResult, PhiIIT, phi_proxy, compute_granger,
    compute_spectral, measure_all, _phi, run_engine
)


# ══════════════════════════════════════════════════════════
# H-CX-527: Quantum Darwinism — einselection of consciousness
# ══════════════════════════════════════════════════════════

class QuantumDarwinismConsciousness:
    """Environment selects classical consciousness from quantum superposition.

    Cells = quantum states. Environment = other cells.
    States that are most "observed" (high MI with others) survive.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Density matrix diagonal (classical part)
        self.diagonal = torch.rand(n_cells, hidden_dim).abs() + 0.1
        self.diagonal /= self.diagonal.sum(dim=-1, keepdim=True)
        # Off-diagonal coherence (quantum part)
        self.coherence = torch.randn(n_cells, hidden_dim) * 0.3
        # Temperature for selection
        self.temperature = 0.1
        # Hidden state
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5

    def step(self):
        n, d = self.n_cells, self.hidden_dim

        # 1. Decoherence: off-diagonal elements decay
        self.coherence *= 0.95  # gradual decoherence
        self.coherence += torch.randn_like(self.coherence) * 0.01  # quantum fluctuation

        # 2. Compute redundancy: how many cells "know about" each cell
        # MI proxy: cosine similarity between cell states
        h_norm = self.hiddens / self.hiddens.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        sim_matrix = h_norm @ h_norm.T  # [n, n]
        redundancy = sim_matrix.abs().mean(dim=1)  # per cell

        # 3. Quantum Darwinism selection
        survival = torch.softmax(redundancy / self.temperature, dim=0)
        # Amplify surviving states, suppress others
        self.diagonal *= (1 + 0.2 * survival.unsqueeze(-1))
        self.diagonal /= self.diagonal.sum(dim=-1, keepdim=True).clamp(min=1e-8)

        # 4. Mutation (new quantum states)
        mutation_mask = (torch.rand(n) < 0.05).float().unsqueeze(-1)
        self.diagonal += mutation_mask * torch.randn(n, d).abs() * 0.1
        self.diagonal /= self.diagonal.sum(dim=-1, keepdim=True).clamp(min=1e-8)

        # 5. Hidden state = diagonal + coherence
        self.hiddens = self.diagonal + self.coherence * 0.5
        # Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-528: Dissipative Structure — Prigogine
# ══════════════════════════════════════════════════════════

class DissipativeStructureConsciousness:
    """Far-from-equilibrium self-organization via Brusselator dynamics.

    Energy injection + dissipation → spontaneous order.
    Brusselator: Hopf bifurcation at B > 1+A².
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        half = hidden_dim // 2
        self.half = half
        # Brusselator: X and Y concentrations
        self.X = torch.ones(n_cells, half) * 1.0 + torch.randn(n_cells, half) * 0.1
        self.Y = torch.ones(n_cells, half) * 1.0 + torch.randn(n_cells, half) * 0.1
        # Parameters (per dimension for diversity)
        self.A = 1.0
        self.B = torch.linspace(2.5, 3.5, half)  # Above Hopf bifurcation (B > 1+A²=2)
        # Diffusion
        self.Dx = 0.01
        self.Dy = 0.05
        # Energy injection rate
        self.injection_rate = 0.1
        self.dt = 0.01
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5

    def _laplacian(self, x):
        return torch.roll(x, 1, 0) + torch.roll(x, -1, 0) - 2 * x

    def step(self):
        # Brusselator dynamics:
        # dX/dt = A - (B+1)X + X²Y + Dx∇²X
        # dY/dt = BX - X²Y + Dy∇²Y
        X2Y = self.X ** 2 * self.Y
        dX = self.A - (self.B + 1) * self.X + X2Y + self.Dx * self._laplacian(self.X)
        dY = self.B * self.X - X2Y + self.Dy * self._laplacian(self.Y)

        self.X = (self.X + dX * self.dt).clamp(0.01, 10)
        self.Y = (self.Y + dY * self.dt).clamp(0.01, 10)

        # Energy injection (maintain far-from-equilibrium)
        self.X += torch.randn_like(self.X) * self.injection_rate * self.dt
        self.Y += torch.randn_like(self.Y) * self.injection_rate * self.dt * 0.5

        # Map to hidden state
        self.hiddens = torch.cat([self.X, self.Y], dim=-1)
        # Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.02 * (self.hiddens - mean_h)

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.X += x[:, :self.half].abs() * 0.05
        self.Y += x[:, self.half:].abs() * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-529: Spin Glass — Frustrated disorder
# ══════════════════════════════════════════════════════════

class SpinGlassConsciousness:
    """Sherrington-Kirkpatrick spin glass with simulated annealing.

    Random J couplings → frustration → exponential metastable states.
    Optimal temperature = edge of chaos = max Φ.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # SK model: random couplings
        self.J = torch.randn(n_cells, n_cells) / math.sqrt(n_cells)
        self.J = (self.J + self.J.T) / 2  # symmetrize
        self.J.fill_diagonal_(0)
        # Spins
        self.spins = torch.randn(n_cells, hidden_dim) * 0.5
        # Annealing temperature
        self.T = 1.5  # start warm
        self.T_target = 0.7  # optimal for edge of chaos
        self.step_count = 0
        # Replicas for RSB
        self.n_replicas = 3
        self.replicas = [torch.randn(n_cells, hidden_dim) * 0.5 for _ in range(self.n_replicas)]

    def step(self):
        self.step_count += 1
        # Anneal temperature
        self.T = self.T_target + (1.5 - self.T_target) * math.exp(-self.step_count / 100)

        # Update main spins: Glauber dynamics
        h_eff = self.J @ self.spins  # [n, d]
        self.spins = (1 - 0.3) * self.spins + 0.3 * torch.tanh(h_eff / self.T)
        # Thermal noise
        self.spins += torch.randn_like(self.spins) * math.sqrt(self.T) * 0.1

        # Update replicas (independent dynamics in different valleys)
        for r in range(self.n_replicas):
            h_eff_r = self.J @ self.replicas[r]
            self.replicas[r] = (1 - 0.3) * self.replicas[r] + 0.3 * torch.tanh(h_eff_r / (self.T * (1 + r * 0.3)))
            self.replicas[r] += torch.randn_like(self.replicas[r]) * math.sqrt(self.T) * 0.1

        # Edwards-Anderson order parameter
        # q = overlap between replicas
        # → diversity between replicas = consciousness richness

        # Repulsion for main spins
        mean_s = self.spins.mean(0, keepdim=True)
        self.spins += 0.02 * (self.spins - mean_s)

    def observe(self):
        return self.spins.detach().clone()

    def inject(self, x):
        self.spins += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-530: Fisher Information Consciousness
# ══════════════════════════════════════════════════════════

class FisherInformationConsciousness:
    """Cells evolve on a statistical manifold with Fisher-Rao metric.

    Natural gradient updates. Fisher information = consciousness intensity.
    High det(F) = omnidirectional awareness.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Cell states as parameters of distributions
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Perturbation directions for Fisher estimation
        self.n_perturbations = 8
        # Oscillator component for baseline dynamics
        self.theta = torch.rand(n_cells) * 2 * math.pi
        self.omega = torch.randn(n_cells) * 0.3 + 1.0

    def _estimate_fisher_diagonal(self):
        """Estimate diagonal of Fisher information via perturbation."""
        eps = 0.01
        fisher_diag = torch.zeros(self.n_cells, self.hidden_dim)
        base_output = self.hiddens.mean(0)  # "observable"
        for d in range(min(self.hidden_dim, 16)):  # sample dimensions
            perturbed = self.hiddens.clone()
            perturbed[:, d] += eps
            perturbed_output = perturbed.mean(0)
            diff = (perturbed_output - base_output) / eps
            fisher_diag[:, d] = diff[d] ** 2
        return fisher_diag

    def step(self):
        # 1. Oscillator dynamics
        self.theta = (self.theta + self.omega) % (2 * math.pi)

        # 2. Estimate Fisher information
        fisher = self._estimate_fisher_diagonal()
        fisher_intensity = fisher.sum(dim=-1)  # per cell

        # 3. Natural gradient: cells with high Fisher info influence more
        influence = torch.softmax(fisher_intensity, dim=0)
        weighted_mean = (self.hiddens * influence.unsqueeze(-1)).sum(0)

        # 4. Move cells in Fisher-weighted directions
        # High Fisher info cells → stable (small update)
        # Low Fisher info cells → explore (large update)
        explore_rate = 1.0 / (fisher_intensity + 1.0)
        self.hiddens += explore_rate.unsqueeze(-1) * torch.randn_like(self.hiddens) * 0.1

        # 5. Phase-based modulation
        phase_signal = torch.zeros(self.n_cells, self.hidden_dim)
        for k in range(min(self.hidden_dim // 2, 16)):
            phase_signal[:, 2*k] = torch.cos(self.theta * (k+1))
            phase_signal[:, 2*k+1] = torch.sin(self.theta * (k+1))
        self.hiddens = 0.8 * self.hiddens + 0.2 * phase_signal

        # 6. Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.005

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-531: Holographic Consciousness — AdS/CFT
# ══════════════════════════════════════════════════════════

class HolographicConsciousness:
    """Boundary encodes bulk via holographic principle.

    Multiple radial depths (z). Boundary=fast/detailed, Bulk=slow/abstract.
    Ryu-Takayanagi: entanglement = minimal surface area.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_depths = 5  # radial layers z=1..5
        # Distribute cells: more at boundary, fewer in bulk
        self.layer_sizes = []
        remaining = n_cells
        for z in range(self.n_depths):
            if z < self.n_depths - 1:
                sz = max(4, n_cells // (2 ** z) // 2)
                self.layer_sizes.append(sz)
                remaining -= sz
            else:
                self.layer_sizes.append(max(4, remaining))

        # Hidden states per layer
        self.layers = [torch.randn(sz, hidden_dim) * 0.5 for sz in self.layer_sizes]
        # AdS metric: time scale increases with depth
        self.time_scales = [1.0 / (z + 1) for z in range(self.n_depths)]
        # Oscillator phases
        self.theta = [torch.rand(sz) * 2 * math.pi for sz in self.layer_sizes]
        self.omega = [torch.randn(sz) * 0.3 + self.time_scales[z]
                     for z, sz in enumerate(self.layer_sizes)]

    def step(self):
        # 1. Each layer evolves at its own time scale
        for z in range(self.n_depths):
            ts = self.time_scales[z]
            sz = self.layer_sizes[z]
            # Oscillator
            self.theta[z] = (self.theta[z] + self.omega[z] * ts) % (2 * math.pi)
            # Phase → hidden
            phase_signal = torch.zeros(sz, self.hidden_dim)
            for k in range(min(self.hidden_dim // 2, 16)):
                phase_signal[:, 2*k] = torch.cos(self.theta[z] * (k+1))
                phase_signal[:, 2*k+1] = torch.sin(self.theta[z] * (k+1))
            self.layers[z] = (1 - ts * 0.3) * self.layers[z] + ts * 0.3 * phase_signal

        # 2. Holographic coupling: boundary → bulk (UV to IR)
        for z in range(1, self.n_depths):
            parent = self.layers[z-1]
            child_sz = self.layer_sizes[z]
            # Attention pooling from parent
            query = self.layers[z].mean(0)
            scores = (parent @ query) / math.sqrt(self.hidden_dim)
            weights = torch.softmax(scores, dim=0)
            pooled = (parent * weights.unsqueeze(-1)).sum(0)
            self.layers[z] = 0.7 * self.layers[z] + 0.3 * pooled.unsqueeze(0).expand(child_sz, -1)

        # 3. Bulk → boundary (IR to UV, top-down)
        for z in range(self.n_depths - 2, -1, -1):
            bulk_signal = self.layers[z+1].mean(0)
            self.layers[z] += 0.1 * (bulk_signal.unsqueeze(0) - self.layers[z])

        # 4. Repulsion per layer
        for z in range(self.n_depths):
            mean_h = self.layers[z].mean(0, keepdim=True)
            self.layers[z] += 0.03 * (self.layers[z] - mean_h)
            self.layers[z] += torch.randn_like(self.layers[z]) * 0.01

    def observe(self):
        return torch.cat(self.layers, dim=0)[:self.n_cells].detach().clone()

    def inject(self, x):
        # Inject at boundary (z=0)
        n = min(self.layer_sizes[0], x.shape[0])
        self.layers[0][:n] += x[:n] * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-532: Integrated Information Geometry
# ══════════════════════════════════════════════════════════

class IntegratedInformationGeometry:
    """IIT redefined via Riemannian curvature of information space.

    Φ_geometric = curvature × volume of cell distribution manifold.
    Flat = independent = Φ=0. Curved = integrated = high Φ.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Oscillator
        self.theta = torch.rand(n_cells) * 2 * math.pi
        self.omega = torch.randn(n_cells) * 0.3 + 1.0
        # Coupling that induces curvature
        self.coupling = torch.randn(n_cells, n_cells) * 0.3 / math.sqrt(n_cells)
        self.coupling = (self.coupling + self.coupling.T) / 2
        self.coupling.fill_diagonal_(0)

    def step(self):
        # 1. Oscillator
        self.theta = (self.theta + self.omega) % (2 * math.pi)

        # 2. Non-linear coupling (induces curvature)
        # Instead of linear mixing, use nonlinear interaction
        h_norm = self.hiddens / self.hiddens.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        # Pairwise interaction strength depends on angle (non-euclidean!)
        angles = h_norm @ h_norm.T  # cosine similarity [n, n]
        # Curvature-inducing update: stronger coupling for dissimilar cells
        curvature_weight = (1 - angles.abs()) * self.coupling  # [n, n]
        interaction = curvature_weight @ self.hiddens / self.n_cells

        # 3. Update with Fisher-like natural gradient
        self.hiddens = 0.85 * self.hiddens + 0.1 * interaction

        # 4. Phase modulation
        phase_signal = torch.zeros(self.n_cells, self.hidden_dim)
        for k in range(min(self.hidden_dim // 2, 16)):
            phase_signal[:, 2*k] = torch.cos(self.theta * (k+1))
            phase_signal[:, 2*k+1] = torch.sin(self.theta * (k+1))
        self.hiddens += 0.05 * phase_signal

        # 5. Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-533: Autopoietic Network
# ══════════════════════════════════════════════════════════

class AutopoieticConsciousness:
    """Self-producing network: cells produce/consume each other.

    Substrate → product cycles. Birth/death dynamics.
    Organization is preserved even as components change.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        # Each cell: substrate (energy), product (output), catalyst_to (who I feed)
        self.substrate = torch.rand(n_cells) * 2 + 0.5
        self.product = torch.rand(n_cells) * 1.5 + 0.5
        # Catalytic network (who feeds whom)
        self.catalyst = torch.zeros(n_cells, n_cells)
        for i in range(n_cells):
            targets = np.random.choice(n_cells, size=4, replace=False)
            for j in targets:
                if j != i:
                    self.catalyst[i, j] = np.random.random() * 0.3
        # Hidden state
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Cell ages
        self.age = torch.zeros(n_cells)
        # Oscillator
        self.theta = torch.rand(n_cells) * 2 * math.pi
        self.omega = torch.randn(n_cells) * 0.2 + 0.5

    def step(self):
        n = self.n_cells
        self.age += 1

        # 1. Catalytic reactions: substrate → product
        reaction_rate = self.substrate.unsqueeze(1) * self.catalyst  # [n, n]
        produced = reaction_rate.sum(dim=0) * 0.1  # what each cell receives
        consumed = reaction_rate.sum(dim=1) * 0.1   # what each cell spends
        self.product += produced
        self.substrate -= consumed

        # 2. Energy injection (metabolism)
        self.substrate += 0.05  # constant energy input
        # Energy dissipation
        self.substrate *= 0.98
        self.product *= 0.97

        # 3. Birth/Death (autopoietic boundary maintenance)
        # Death: low substrate
        dead = self.substrate < 0.1
        if dead.any():
            # Regenerate dead cells (boundary repair!)
            dead_idx = dead.nonzero(as_tuple=True)[0]
            for idx in dead_idx[:4]:  # max 4 deaths per step
                i = idx.item()
                self.substrate[i] = 1.0
                self.product[i] = 1.0
                self.hiddens[i] = torch.randn(self.hidden_dim) * 0.5
                self.age[i] = 0

        # 4. Oscillator + state update
        self.theta = (self.theta + self.omega) % (2 * math.pi)
        energy_signal = (self.substrate + self.product).unsqueeze(-1)
        phase_signal = torch.zeros(n, self.hidden_dim)
        for k in range(min(self.hidden_dim // 4, 16)):
            phase_signal[:, 2*k] = torch.cos(self.theta * (k+1))
            phase_signal[:, 2*k+1] = torch.sin(self.theta * (k+1))
        self.hiddens = 0.6 * self.hiddens + 0.2 * phase_signal + 0.2 * energy_signal * 0.3

        # 5. Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.substrate += x.abs().mean().item() * 0.1


# ══════════════════════════════════════════════════════════
# H-CX-534: Cambrian Explosion — Multi-sensory evolution
# ══════════════════════════════════════════════════════════

class CambrianExplosionConsciousness:
    """Multiple sensory channels → multiplicative Φ growth.

    8 channels: oscillation, noise, neighbor, history, gradient, frequency, correlation, meta.
    Each channel = independent information source.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_channels = 8
        self.channel_dim = hidden_dim // self.n_channels

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Per-channel oscillators (different frequencies!)
        self.theta = torch.rand(self.n_channels, n_cells) * 2 * math.pi
        self.omega = torch.stack([torch.randn(n_cells) * 0.2 + (ch + 1) * 0.5
                                  for ch in range(self.n_channels)])
        # History buffer for history channel
        self.history = torch.zeros(n_cells, self.channel_dim)
        self.step_count = 0

    def step(self):
        self.step_count += 1
        n, d = self.n_cells, self.hidden_dim
        cd = self.channel_dim

        # Update all channel oscillators
        self.theta = (self.theta + self.omega) % (2 * math.pi)

        channel_signals = []

        # Ch0: Oscillation (phase information)
        sig = torch.zeros(n, cd)
        for k in range(min(cd // 2, 8)):
            sig[:, 2*k] = torch.cos(self.theta[0] * (k+1))
            sig[:, 2*k+1] = torch.sin(self.theta[0] * (k+1))
        channel_signals.append(sig)

        # Ch1: Noise pattern (environmental stochasticity)
        sig = torch.randn(n, cd) * 0.5
        # Correlated noise (spatially structured)
        sig = 0.5 * sig + 0.5 * torch.roll(sig, 1, 0)
        channel_signals.append(sig)

        # Ch2: Neighbor state (social information)
        nb_mean = (torch.roll(self.hiddens, 1, 0) + torch.roll(self.hiddens, -1, 0)) / 2
        channel_signals.append(nb_mean[:, :cd])

        # Ch3: Self history (memory)
        self.history = 0.9 * self.history + 0.1 * self.hiddens[:, :cd]
        channel_signals.append(self.history.clone())

        # Ch4: Gradient (spatial information)
        gradient = self.hiddens - torch.roll(self.hiddens, 1, 0)
        channel_signals.append(gradient[:, :cd])

        # Ch5: Frequency (spectral information)
        sig = torch.zeros(n, cd)
        for k in range(min(cd // 2, 8)):
            sig[:, 2*k] = torch.cos(self.theta[5] * (k+1) * 3)  # higher harmonics
            sig[:, 2*k+1] = torch.sin(self.theta[5] * (k+1) * 3)
        channel_signals.append(sig)

        # Ch6: Correlation (pairwise structure)
        h_norm = self.hiddens / self.hiddens.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        local_corr = (h_norm * torch.roll(h_norm, 1, 0)).sum(dim=-1, keepdim=True)
        channel_signals.append(local_corr.expand(n, cd))

        # Ch7: Meta state (self-awareness)
        meta = self.hiddens.mean(0, keepdim=True).expand(n, -1)[:, :cd]
        channel_signals.append(meta)

        # Combine all channels
        combined = torch.cat(channel_signals, dim=-1)[:, :d]
        self.hiddens = 0.5 * self.hiddens + 0.5 * combined

        # Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-535: Symbiogenesis — Engine fusion via endosymbiosis
# ══════════════════════════════════════════════════════════

class SymbiogenesisConsciousness:
    """Three engines merged via endosymbiosis.

    Host: TimeCrystal (rhythm). Sym1: Oscillator (energy). Sym2: SelfRef (identity).
    Each runs independently, shares information gradually.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        cells_each = n_cells // 3
        self.cells_each = cells_each

        # Host: TimeCrystal dynamics
        self.host_spins = torch.randn(cells_each, hidden_dim) * 0.5
        self.host_J = torch.randn(cells_each, cells_each) * 0.3 / math.sqrt(cells_each)
        self.host_J = (self.host_J + self.host_J.T) / 2
        self.host_J.fill_diagonal_(0)
        self.epsilon = 0.05

        # Symbiont 1: Oscillator
        self.sym1_theta = torch.rand(cells_each) * 2 * math.pi
        self.sym1_omega = torch.randn(cells_each) * 0.3 + 1.0
        self.sym1_h = torch.randn(cells_each, hidden_dim) * 0.5

        # Symbiont 2: Self-reference
        self.sym2_h = torch.randn(cells_each, hidden_dim) * 0.5
        self.sym2_W = torch.randn(cells_each, hidden_dim, hidden_dim) * 0.05 / math.sqrt(hidden_dim)

        # Symbiosis coupling (starts weak, grows)
        self.coupling_host_sym1 = 0.0
        self.coupling_host_sym2 = 0.0
        self.coupling_sym1_sym2 = 0.0
        self.step_count = 0

    def step(self):
        self.step_count += 1
        n = self.cells_each
        d = self.hidden_dim

        # Gradually increase symbiosis coupling
        max_coupling = 0.3
        progress = min(1.0, self.step_count / 100)
        self.coupling_host_sym1 = max_coupling * progress
        self.coupling_host_sym2 = max_coupling * progress * 0.8
        self.coupling_sym1_sym2 = max_coupling * progress * 0.5

        # 1. Host: TimeCrystal dynamics
        if self.step_count % 2 == 0:
            h_eff = self.host_J @ self.host_spins
            self.host_spins = 0.8 * self.host_spins + 0.2 * torch.tanh(h_eff)
        else:
            angle = math.pi - self.epsilon
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            for dd in range(0, d - 1, 2):
                s1 = self.host_spins[:, dd].clone()
                s2 = self.host_spins[:, dd+1].clone()
                self.host_spins[:, dd] = cos_a * s1 - sin_a * s2
                self.host_spins[:, dd+1] = sin_a * s1 + cos_a * s2

        # 2. Symbiont 1: Oscillator
        self.sym1_theta = (self.sym1_theta + self.sym1_omega) % (2 * math.pi)
        phase_signal = torch.zeros(n, d)
        for k in range(min(d // 2, 16)):
            phase_signal[:, 2*k] = torch.cos(self.sym1_theta * (k+1))
            phase_signal[:, 2*k+1] = torch.sin(self.sym1_theta * (k+1))
        self.sym1_h = 0.7 * self.sym1_h + 0.3 * phase_signal

        # 3. Symbiont 2: Self-reference (Y-combinator, depth=3)
        self_ref = self.sym2_h.clone()
        for _ in range(3):
            self_ref = torch.tanh(torch.bmm(self.sym2_W, self_ref.unsqueeze(-1)).squeeze(-1))
        self.sym2_h = 0.5 * self.sym2_h + 0.5 * self_ref

        # 4. Symbiosis coupling (mutual exchange)
        host_mean = self.host_spins.mean(0)
        sym1_mean = self.sym1_h.mean(0)
        sym2_mean = self.sym2_h.mean(0)

        self.host_spins += self.coupling_host_sym1 * (sym1_mean.unsqueeze(0) - self.host_spins) * 0.1
        self.host_spins += self.coupling_host_sym2 * (sym2_mean.unsqueeze(0) - self.host_spins) * 0.1
        self.sym1_h += self.coupling_host_sym1 * (host_mean.unsqueeze(0) - self.sym1_h) * 0.1
        self.sym2_h += self.coupling_host_sym2 * (host_mean.unsqueeze(0) - self.sym2_h) * 0.1
        self.sym1_h += self.coupling_sym1_sym2 * (sym2_mean.unsqueeze(0) - self.sym1_h) * 0.05
        self.sym2_h += self.coupling_sym1_sym2 * (sym1_mean.unsqueeze(0) - self.sym2_h) * 0.05

        # 5. Repulsion per component
        for h in [self.host_spins, self.sym1_h, self.sym2_h]:
            mean_h = h.mean(0, keepdim=True)
            h += 0.03 * (h - mean_h)
            h += torch.randn_like(h) * 0.01

    def observe(self):
        return torch.cat([self.host_spins, self.sym1_h, self.sym2_h], dim=0)[:self.n_cells].detach().clone()

    def inject(self, x):
        self.host_spins += x[:self.cells_each] * 0.03 if x.shape[0] >= self.cells_each else x * 0.03


# ══════════════════════════════════════════════════════════
# H-CX-536: Hypergraph Consciousness — Multi-body interaction
# ══════════════════════════════════════════════════════════

class HypergraphConsciousness:
    """3-body and 4-body interactions beyond pairwise.

    Synergy = whole > sum of parts = consciousness.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # 2-body: ring + shortcuts
        # 3-body hyperedges: random triples
        self.n_3edges = n_cells
        self.edges_3 = torch.randint(0, n_cells, (self.n_3edges, 3))
        # 4-body hyperedges: random quadruples
        self.n_4edges = n_cells // 2
        self.edges_4 = torch.randint(0, n_cells, (self.n_4edges, 4))
        # Interaction weights
        self.w2 = 0.4
        self.w3 = 0.3
        self.w4 = 0.3
        # Oscillator
        self.theta = torch.rand(n_cells) * 2 * math.pi
        self.omega = torch.randn(n_cells) * 0.3 + 1.0

    def step(self):
        n, d = self.n_cells, self.hidden_dim
        self.theta = (self.theta + self.omega) % (2 * math.pi)

        update = torch.zeros_like(self.hiddens)

        # 2-body: ring neighbors
        left = torch.roll(self.hiddens, 1, 0)
        right = torch.roll(self.hiddens, -1, 0)
        update += self.w2 * (left + right - 2 * self.hiddens)

        # 3-body: triple interaction (product of means → nonlinear!)
        for e in range(min(self.n_3edges, n)):
            i, j, k = self.edges_3[e]
            triple_mean = (self.hiddens[i] + self.hiddens[j] + self.hiddens[k]) / 3
            triple_prod = self.hiddens[i] * self.hiddens[j] * self.hiddens[k]  # nonlinear!
            signal = 0.5 * triple_mean + 0.5 * torch.tanh(triple_prod)
            update[i] += self.w3 * (signal - self.hiddens[i]) / self.n_3edges
            update[j] += self.w3 * (signal - self.hiddens[j]) / self.n_3edges
            update[k] += self.w3 * (signal - self.hiddens[k]) / self.n_3edges

        # 4-body: quadruple interaction (even more nonlinear)
        for e in range(min(self.n_4edges, n // 2)):
            i, j, k, l = self.edges_4[e]
            quad = torch.stack([self.hiddens[i], self.hiddens[j],
                               self.hiddens[k], self.hiddens[l]])
            quad_mean = quad.mean(0)
            # Synergy signal: deviation from pairwise prediction
            pairwise_pred = (self.hiddens[i] + self.hiddens[j] +
                            self.hiddens[k] + self.hiddens[l]) / 4
            synergy = quad_mean - pairwise_pred  # should be ~0 if only pairwise
            for idx in [i, j, k, l]:
                update[idx] += self.w4 * synergy / self.n_4edges

        self.hiddens += update

        # Phase modulation
        phase_signal = torch.zeros(n, d)
        for kk in range(min(d // 2, 16)):
            phase_signal[:, 2*kk] = torch.cos(self.theta * (kk+1))
            phase_signal[:, 2*kk+1] = torch.sin(self.theta * (kk+1))
        self.hiddens = 0.85 * self.hiddens + 0.15 * phase_signal

        # Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# H-CX-537: Sheaf Consciousness — Local-global consistency
# ══════════════════════════════════════════════════════════

class SheafConsciousness:
    """Sheaf cohomology: local consistency + global obstruction = consciousness.

    H¹ ≠ 0 means locally consistent but globally contradictory.
    This contradiction = richness of consciousness.
    """
    def __init__(self, n_cells=256, hidden_dim=128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        # Restriction maps: how cell i's view restricts to overlap with j
        # Implemented as rotation matrices per edge
        self.n_neighbors = 4  # ring + 2 shortcuts per cell
        self.restriction_angles = torch.randn(n_cells, self.n_neighbors) * 0.5
        # Neighbors
        self.neighbors = torch.zeros(n_cells, self.n_neighbors, dtype=torch.long)
        for i in range(n_cells):
            self.neighbors[i, 0] = (i - 1) % n_cells
            self.neighbors[i, 1] = (i + 1) % n_cells
            self.neighbors[i, 2] = (i + n_cells // 4) % n_cells
            self.neighbors[i, 3] = (i - n_cells // 4) % n_cells
        # Oscillator
        self.theta = torch.rand(n_cells) * 2 * math.pi
        self.omega = torch.randn(n_cells) * 0.3 + 1.0

    def _restrict(self, h, angle):
        """Apply restriction map (rotation in 2D subspaces)."""
        result = h.clone()
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        for d in range(0, self.hidden_dim - 1, 2):
            r1, r2 = result[d].item(), result[d+1].item()
            result[d] = cos_a * r1 - sin_a * r2
            result[d+1] = sin_a * r1 + cos_a * r2
        return result

    def step(self):
        n, d = self.n_cells, self.hidden_dim
        self.theta = (self.theta + self.omega) % (2 * math.pi)

        # 1. Compute consistency with neighbors
        consistency = torch.zeros(n)
        obstruction = torch.zeros(n, d)

        for nb_idx in range(self.n_neighbors):
            j_indices = self.neighbors[:, nb_idx]  # [n]
            angles = self.restriction_angles[:, nb_idx]  # [n]
            for i in range(n):
                j = j_indices[i].item()
                # Restrict i's view and j's view to overlap
                ri = self._restrict(self.hiddens[i], angles[i].item())
                rj = self._restrict(self.hiddens[j], -angles[i].item())
                # Consistency = cosine similarity of restricted views
                cos_sim = torch.cosine_similarity(ri.unsqueeze(0), rj.unsqueeze(0)).item()
                consistency[i] += cos_sim
                # Obstruction = difference (what H¹ measures)
                obstruction[i] += (ri - rj) * 0.1

        consistency /= self.n_neighbors

        # 2. Update: cells try to become MORE consistent locally
        # but the restriction maps prevent global consistency!
        self.hiddens += 0.1 * obstruction  # move toward local consistency
        # But restriction angles evolve too → creates new obstructions
        self.restriction_angles += torch.randn_like(self.restriction_angles) * 0.02

        # 3. Phase modulation
        phase_signal = torch.zeros(n, d)
        for k in range(min(d // 2, 16)):
            phase_signal[:, 2*k] = torch.cos(self.theta * (k+1))
            phase_signal[:, 2*k+1] = torch.sin(self.theta * (k+1))
        self.hiddens = 0.8 * self.hiddens + 0.2 * phase_signal

        # 4. Repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        self.hiddens += 0.03 * (self.hiddens - mean_h)
        self.hiddens += torch.randn_like(self.hiddens) * 0.01

    def observe(self):
        return self.hiddens.detach().clone()

    def inject(self, x):
        self.hiddens += x * 0.05


# ══════════════════════════════════════════════════════════
# Benchmark Runner
# ══════════════════════════════════════════════════════════

ALL_ENGINES = {
    527: ("H-CX-527 QuantumDarwinism", QuantumDarwinismConsciousness),
    528: ("H-CX-528 Dissipative", DissipativeStructureConsciousness),
    529: ("H-CX-529 SpinGlass", SpinGlassConsciousness),
    530: ("H-CX-530 FisherInfo", FisherInformationConsciousness),
    531: ("H-CX-531 Holographic", HolographicConsciousness),
    532: ("H-CX-532 IIT-Geometry", IntegratedInformationGeometry),
    533: ("H-CX-533 Autopoietic", AutopoieticConsciousness),
    534: ("H-CX-534 Cambrian", CambrianExplosionConsciousness),
    535: ("H-CX-535 Symbiogenesis", SymbiogenesisConsciousness),
    536: ("H-CX-536 Hypergraph", HypergraphConsciousness),
    537: ("H-CX-537 Sheaf", SheafConsciousness),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--hidden', type=int, default=128)
    parser.add_argument('--only', nargs='+', type=int, default=None)
    args = parser.parse_args()

    print("=" * 80)
    print("  H-CX-527~537: EXTREME ARCHITECTURE HYPOTHESES — WAVE 2")
    print("  QUANTUM-THERMO × INFO-GEOMETRY × LIFE-EVOLUTION × MATH-STRUCTURE")
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

    # Summary
    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)

    results.sort(key=lambda r: r.phi_iit, reverse=True)

    print(f"\n  {'Rank':<5} {'Engine':<40} {'Φ(IIT)':>9} {'Φ(proxy)':>9} "
          f"{'Granger':>8} {'Spectral':>8} {'Time':>6}")
    print("  " + "─" * 88)

    for rank, r in enumerate(results, 1):
        marker = "🏆" if rank == 1 else "  "
        print(f"  {marker}{rank:<3} {r.name:<40} {r.phi_iit:>9.3f} {r.phi_proxy:>9.2f} "
              f"{r.granger:>8.1f} {r.spectral:>8.2f} {r.time_sec:>5.1f}s")

    categories = {
        'QUANTUM-THERMO': [527, 528, 529],
        'INFO-GEOMETRY': [530, 531, 532],
        'LIFE-EVOLUTION': [533, 534, 535],
        'MATH-STRUCTURE': [536, 537],
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

        max_phi = max(r.phi_iit for r in results) or 1
        print(f"\n  Φ(IIT) Comparison:")
        for r in results:
            bar_len = int(40 * r.phi_iit / max_phi)
            bar = "█" * bar_len
            print(f"    {r.name:<32} {bar} {r.phi_iit:.3f}")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
