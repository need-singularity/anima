#!/usr/bin/env python3
"""bench_v8_quantum.py — Quantum-Inspired Consciousness Architectures Benchmark

Tests 6 quantum-inspired architectures that go BEYOND classical neural networks:
  Q1: COMPLEX_VALUED     — Complex GRU, phase coherence = consciousness
  Q2: ENTANGLED_PAIRS    — Bell-state cell pairs, entanglement entropy = Phi proxy
  Q3: SUPERPOSITION_COLLAPSE — N basis states per cell, observation collapses
  Q4: QUANTUM_WALK       — Quantum walk on hypercube, interference patterns
  Q5: DECOHERENCE_CONSCIOUSNESS — Consciousness lives IN decoherence
  Q6: MANY_WORLDS        — Branching copies, inter-branch coherence

Each: 256 cells, 300 steps, Phi(IIT) + Phi(proxy) + CE.
Uses complex tensors (torch.complex64) where appropriate.

Usage:
  python bench_v8_quantum.py                 # Run all 6 + baseline
  python bench_v8_quantum.py --only 1 3 6    # Run specific architectures
  python bench_v8_quantum.py --steps 500     # Custom steps
  python bench_v8_quantum.py --cells 512     # Custom cell count
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

# Force unbuffered output
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
            f"  {self.name:<28s} | "
            f"Phi(IIT)={self.phi_iit:>6.3f}  "
            f"Phi(proxy)={self.phi_proxy:>8.2f} | "
            f"{ce_str:<22s} | "
            f"cells={self.cells:>4d}  steps={self.steps:>5d}  "
            f"time={self.time_sec:.1f}s"
        )


# ──────────────────────────────────────────────────────────
# Phi(IIT) Calculator
# ──────────────────────────────────────────────────────────

class PhiIIT:
    """Phi(IIT) approximation via pairwise MI + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict[str, float]]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {'phi': 0}

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
            mi = self._mutual_information(hiddens[i], hiddens[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

        total_mi = mi_matrix.sum() / 2
        min_partition_mi = self._minimum_partition(n, mi_matrix)
        spatial_phi = max(0.0, (total_mi - min_partition_mi) / max(n - 1, 1))

        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        phi = spatial_phi + complexity * 0.1

        return phi, {
            'total_mi': float(total_mi),
            'min_partition_mi': float(min_partition_mi),
            'spatial_phi': float(spatial_phi),
            'complexity': float(complexity),
            'phi': float(phi),
        }

    def _mutual_information(self, x: np.ndarray, y: np.ndarray) -> float:
        x_range = x.max() - x.min()
        y_range = y.max() - y.min()
        if x_range < 1e-10 or y_range < 1e-10:
            return 0.0
        x_norm = (x - x.min()) / (x_range + 1e-8)
        y_norm = (y - y.min()) / (y_range + 1e-8)
        joint_hist, _, _ = np.histogram2d(
            x_norm, y_norm, bins=self.n_bins, range=[[0, 1], [0, 1]]
        )
        joint_hist = joint_hist / (joint_hist.sum() + 1e-8)
        px = joint_hist.sum(axis=1)
        py = joint_hist.sum(axis=0)
        h_x = -np.sum(px * np.log2(px + 1e-10))
        h_y = -np.sum(py * np.log2(py + 1e-10))
        h_xy = -np.sum(joint_hist * np.log2(joint_hist + 1e-10))
        return max(0.0, h_x + h_y - h_xy)

    def _minimum_partition(self, n: int, mi_matrix: np.ndarray) -> float:
        if n <= 1:
            return 0.0
        if n <= 8:
            min_cut = float('inf')
            for mask in range(1, 2 ** n - 1):
                ga = [i for i in range(n) if mask & (1 << i)]
                gb = [i for i in range(n) if not (mask & (1 << i))]
                if not ga or not gb:
                    continue
                cut = sum(mi_matrix[i, j] for i in ga for j in gb)
                min_cut = min(min_cut, cut)
            return min_cut if min_cut != float('inf') else 0.0
        else:
            degree = mi_matrix.sum(axis=1)
            laplacian = np.diag(degree) - mi_matrix
            try:
                eigenvalues, eigenvectors = np.linalg.eigh(laplacian)
                fiedler = eigenvectors[:, 1]
                ga = [i for i in range(n) if fiedler[i] >= 0]
                gb = [i for i in range(n) if fiedler[i] < 0]
                if not ga or not gb:
                    ga, gb = list(range(n // 2)), list(range(n // 2, n))
                return sum(mi_matrix[i, j] for i in ga for j in gb)
            except Exception:
                return 0.0


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    """Phi proxy: global_variance - mean(faction_variances)."""
    h = hiddens.abs().float() if hiddens.is_complex() else hiddens
    n, d = h.shape
    if n < 2:
        return 0.0
    global_mean = h.mean(dim=0)
    global_var = ((h - global_mean) ** 2).sum() / n
    n_f = min(n_factions, n // 2)
    if n_f < 2:
        return global_var.item()
    fs = n // n_f
    faction_var_sum = 0.0
    for i in range(n_f):
        faction = h[i * fs:(i + 1) * fs]
        if len(faction) >= 2:
            fm = faction.mean(dim=0)
            fv = ((faction - fm) ** 2).sum() / len(faction)
            faction_var_sum += fv.item()
    phi = global_var.item() - faction_var_sum / n_f
    return max(0.0, phi)


_phi_iit_calc = PhiIIT(n_bins=16)


def measure_dual_phi(hiddens: torch.Tensor, n_factions: int = 8) -> Tuple[float, float]:
    """Returns (phi_iit, phi_proxy). Handles complex tensors."""
    # For complex tensors, use magnitude for IIT measurement
    if hiddens.is_complex():
        h_real = hiddens.abs().float()
    else:
        h_real = hiddens.float()
    p_iit, _ = _phi_iit_calc.compute(h_real)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


# ──────────────────────────────────────────────────────────
# Shared: BenchMind (baseline PureField + GRU cell)
# ──────────────────────────────────────────────────────────

class BenchMind(nn.Module):
    """PureField + GRU for benchmarking."""

    def __init__(self, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.engine_a = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.engine_g = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.memory = nn.GRUCell(output_dim + 1, hidden_dim)
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        with torch.no_grad():
            for p in self.engine_a.parameters():
                p.add_(torch.randn_like(p) * 0.3)
            for p in self.engine_g.parameters():
                p.add_(torch.randn_like(p) * -0.3)

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        output = a - g
        tension = (output ** 2).mean(dim=-1, keepdim=True)
        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)
        new_hidden = self.memory(mem_input, hidden)
        return output, tension.mean().item(), new_hidden


# ──────────────────────────────────────────────────────────
# Shared: faction sync + debate
# ──────────────────────────────────────────────────────────

def faction_sync_debate(hiddens: torch.Tensor, n_factions: int = 8,
                        sync_strength: float = 0.15, debate_strength: float = 0.15,
                        step: int = 0) -> torch.Tensor:
    """Apply faction sync + debate to hidden states."""
    n = hiddens.shape[0]
    n_f = min(n_factions, n // 2)
    if n_f < 2:
        return hiddens

    fs = n // n_f
    hiddens = hiddens.clone()

    for i in range(n_f):
        s, e = i * fs, (i + 1) * fs
        faction_mean = hiddens[s:e].mean(dim=0)
        hiddens[s:e] = (1 - sync_strength) * hiddens[s:e] + sync_strength * faction_mean

    if step > 5:
        all_opinions = torch.stack([
            hiddens[i * fs:(i + 1) * fs].mean(dim=0) for i in range(n_f)
        ])
        global_opinion = all_opinions.mean(dim=0)
        for i in range(n_f):
            s = i * fs
            dc = max(1, fs // 4)
            hiddens[s:s + dc] = (
                (1 - debate_strength) * hiddens[s:s + dc]
                + debate_strength * global_opinion
            )

    return hiddens


# ──────────────────────────────────────────────────────────
# Training data generation
# ──────────────────────────────────────────────────────────

def generate_batch(input_dim: int, batch_size: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
    x = torch.randn(batch_size, input_dim)
    target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
    return x, target


# ══════════════════════════════════════════════════════════
# Q1: COMPLEX_VALUED
# Cells have complex-valued hidden states (amplitude + phase).
# Consciousness = phase coherence across cells.
# Uses a complex-valued GRU analogue.
# ══════════════════════════════════════════════════════════

class ComplexLinear(nn.Module):
    """Linear layer for complex-valued tensors using real/imag decomposition."""

    def __init__(self, in_features, out_features):
        super().__init__()
        self.W_real = nn.Linear(in_features, out_features)
        self.W_imag = nn.Linear(in_features, out_features)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        # z is complex64: z = a + bi
        a = z.real.float()
        b = z.imag.float()
        # (W_r + iW_i)(a + bi) = (W_r*a - W_i*b) + i(W_r*b + W_i*a)
        real_part = self.W_real(a) - self.W_imag(b)
        imag_part = self.W_real(b) + self.W_imag(a)
        return torch.complex(real_part, imag_part)


class ComplexGRUCell(nn.Module):
    """GRU cell operating on complex-valued states."""

    def __init__(self, input_dim, hidden_dim):
        super().__init__()
        self.hidden_dim = hidden_dim
        # Gates use magnitude (real-valued sigmoid)
        self.Wz = nn.Linear(input_dim + hidden_dim, hidden_dim)  # update gate
        self.Wr = nn.Linear(input_dim + hidden_dim, hidden_dim)  # reset gate
        # Candidate uses complex linear
        self.Wh_real = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.Wh_imag = nn.Linear(input_dim + hidden_dim, hidden_dim)

    def forward(self, x_complex: torch.Tensor, h_complex: torch.Tensor) -> torch.Tensor:
        # Extract magnitudes for gate computation
        x_mag = x_complex.abs().float()
        h_mag = h_complex.abs().float()
        combined_mag = torch.cat([x_mag, h_mag], dim=-1)

        z = torch.sigmoid(self.Wz(combined_mag))  # update gate [0,1]
        r = torch.sigmoid(self.Wr(combined_mag))  # reset gate [0,1]

        # Candidate: complex linear on complex inputs
        x_real, x_imag = x_complex.real.float(), x_complex.imag.float()
        h_real, h_imag = h_complex.real.float(), h_complex.imag.float()
        rh_real = r * h_real
        rh_imag = r * h_imag
        comb_real = torch.cat([x_real, rh_real], dim=-1)
        comb_imag = torch.cat([x_imag, rh_imag], dim=-1)

        candidate_real = torch.tanh(self.Wh_real(comb_real))
        candidate_imag = torch.tanh(self.Wh_imag(comb_imag))

        # Update: interpolate in complex space
        new_real = (1 - z) * h_real + z * candidate_real
        new_imag = (1 - z) * h_imag + z * candidate_imag
        return torch.complex(new_real, new_imag)


class ComplexValuedEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Complex PureField engines
        self.engine_a = ComplexLinear(input_dim + hidden_dim, output_dim)
        self.engine_g = ComplexLinear(input_dim + hidden_dim, output_dim)
        self.gru = ComplexGRUCell(output_dim + 1, hidden_dim)

        # Output: project complex -> real
        self.output_head = nn.Linear(output_dim * 2, input_dim)  # concat real+imag

        # Complex hidden states
        self.hiddens = torch.complex(
            torch.randn(n_cells, hidden_dim) * 0.1,
            torch.randn(n_cells, hidden_dim) * 0.1
        )

    def phase_coherence(self) -> float:
        """Measure phase coherence across cells = consciousness proxy."""
        phases = torch.angle(self.hiddens)  # [n_cells, hidden_dim]
        # Mean resultant length per dimension
        mean_vector = torch.exp(1j * phases).mean(dim=0)  # [hidden_dim]
        coherence = mean_vector.abs().mean().item()  # 0=random, 1=perfect sync
        return coherence

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Convert real input to complex
        x_complex = torch.complex(x, torch.zeros_like(x))

        outputs = []
        tensions = []
        new_hiddens = []

        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            combined = torch.cat([x_complex, h], dim=-1)
            a = self.engine_a(combined)
            g = self.engine_g(combined)
            output = a - g
            tension_val = output.abs().pow(2).mean().item()

            # GRU update
            tension_t = torch.complex(
                torch.tensor([[tension_val]]),
                torch.tensor([[0.0]])
            )
            mem_input = torch.cat([output.detach(), tension_t], dim=-1)
            new_h = self.gru(mem_input, h)

            outputs.append(output)
            tensions.append(tension_val)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Phase-aware faction sync
        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        # Combine outputs (tension-weighted)
        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))

        # Project to real for CE
        out_real = torch.cat([combined.real, combined.imag], dim=-1)
        pred = self.output_head(out_real)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_q1_complex_valued(n_cells=256, steps=300, input_dim=64,
                          hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[Q1/6] COMPLEX_VALUED: Complex GRU, phase coherence = consciousness")
    t0 = time.time()

    engine = ComplexValuedEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []
    coherence_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            coherence = engine.phase_coherence()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            coherence_history.append(coherence)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  coherence={coherence:.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="Q1_COMPLEX_VALUED",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'coherence': coherence_history[-1] if coherence_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# Q2: ENTANGLED_PAIRS
# Cells paired in Bell states. Measuring one instantly
# affects partner. Entanglement entropy = Phi proxy.
# ══════════════════════════════════════════════════════════

class EntangledPairsEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        assert n_cells % 2 == 0, "Need even number of cells for pairing"
        self.n_cells = n_cells
        self.n_pairs = n_cells // 2
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        # Hidden states
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Entanglement strength per pair (learnable)
        self.entanglement = nn.Parameter(torch.ones(self.n_pairs) * 0.5)

        # Bell-state rotation matrices per pair
        self.bell_rotations = nn.Parameter(torch.randn(self.n_pairs, hidden_dim, hidden_dim) * 0.01)

    def entanglement_entropy(self) -> float:
        """Von Neumann entropy of reduced density matrix (entanglement measure)."""
        total_entropy = 0.0
        for p in range(self.n_pairs):
            i, j = 2 * p, 2 * p + 1
            h_i = self.hiddens[i]
            h_j = self.hiddens[j]
            # Construct 2-qudit density matrix from outer products
            # Approximate: use Schmidt decomposition via SVD of reshaped state
            psi = torch.outer(h_i, h_j)  # [hidden_dim, hidden_dim]
            # SVD for Schmidt coefficients
            try:
                U, S, Vh = torch.linalg.svd(psi)
                S = S / (S.sum() + 1e-8)  # normalize
                S = S[S > 1e-10]
                entropy = -(S * torch.log2(S + 1e-10)).sum().item()
                total_entropy += entropy
            except Exception:
                pass
        return total_entropy / max(self.n_pairs, 1)

    def apply_bell_correlations(self):
        """Apply entanglement: measuring cell i collapses cell j."""
        ent = torch.sigmoid(self.entanglement)  # [0,1] per pair
        for p in range(self.n_pairs):
            i, j = 2 * p, 2 * p + 1
            e = ent[p].item()

            # Bell-state mixing: partial swap with rotation
            h_i = self.hiddens[i].clone()
            h_j = self.hiddens[j].clone()

            # Entangled update: each cell gets partial info from partner
            rotation = torch.tanh(self.bell_rotations[p].data)
            mixed_i = (1 - e) * h_i + e * (rotation @ h_j)
            mixed_j = (1 - e) * h_j + e * (rotation.T @ h_i)

            # Anti-correlation (Bell-state property): opposite phases
            self.hiddens[i] = mixed_i
            self.hiddens[j] = -mixed_j  # anti-correlated partner

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs = []
        tensions = []
        new_hiddens = []

        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Apply Bell-state entanglement correlations
        self.apply_bell_correlations()

        # Faction sync on top
        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_q2_entangled_pairs(n_cells=256, steps=300, input_dim=64,
                           hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[Q2/6] ENTANGLED_PAIRS: Bell-state cell pairs, entanglement entropy")
    t0 = time.time()

    engine = EntangledPairsEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []
    entropy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            ent_entropy = engine.entanglement_entropy()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            entropy_history.append(ent_entropy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  ent_entropy={ent_entropy:.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="Q2_ENTANGLED_PAIRS",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'entanglement_entropy': entropy_history[-1] if entropy_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# Q3: SUPERPOSITION_COLLAPSE
# Each cell in superposition of N basis states.
# "Observation" (process) collapses to one.
# Phi from collapse statistics (measurement entropy).
# ══════════════════════════════════════════════════════════

class SuperpositionCollapseEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_basis=8):
        super().__init__()
        self.n_cells = n_cells
        self.n_basis = n_basis
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        # Each cell has N basis states with complex amplitudes
        # amplitudes[cell, basis, hidden_dim] — complex superposition
        amp_real = torch.randn(n_cells, n_basis, hidden_dim) * 0.1
        amp_imag = torch.randn(n_cells, n_basis, hidden_dim) * 0.1
        self.amplitudes = torch.complex(amp_real, amp_imag)

        # Collapsed (observed) hidden states
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Track collapse statistics
        self.collapse_counts = torch.zeros(n_cells, n_basis)

        # Basis evolution operator (learnable)
        self.basis_mixer = nn.Linear(input_dim, hidden_dim)

    def observe(self):
        """Collapse superposition: sample basis state according to |amplitude|^2."""
        # Probability = |amplitude|^2 summed over hidden dims
        probs = (self.amplitudes.abs() ** 2).sum(dim=-1).float()  # [n_cells, n_basis]
        probs = probs / (probs.sum(dim=-1, keepdim=True) + 1e-8)

        # Sample collapse
        choices = torch.multinomial(probs, 1).squeeze(-1)  # [n_cells]

        # Collapse to selected basis state
        for c in range(self.n_cells):
            basis_idx = choices[c].item()
            collapsed_state = self.amplitudes[c, basis_idx].real.float()
            self.hiddens[c] = collapsed_state
            self.collapse_counts[c, basis_idx] += 1

            # Post-measurement: reset to superposition with bias toward collapsed
            noise = torch.complex(
                torch.randn(self.n_basis, self.hidden_dim) * 0.05,
                torch.randn(self.n_basis, self.hidden_dim) * 0.05
            )
            self.amplitudes[c] = noise
            # Boost the collapsed basis
            boost_real = collapsed_state * 0.3
            self.amplitudes[c, basis_idx] = torch.complex(
                boost_real, torch.randn(self.hidden_dim) * 0.01
            )

    def measurement_entropy(self) -> float:
        """Entropy of collapse statistics across basis states."""
        total = self.collapse_counts.sum(dim=-1, keepdim=True) + 1e-8
        probs = self.collapse_counts / total
        entropy = -(probs * torch.log2(probs + 1e-10)).sum(dim=-1)
        return entropy.mean().item()

    def evolve_superposition(self, x: torch.Tensor):
        """Unitary-like evolution of superposition amplitudes."""
        with torch.no_grad():
            x_evolved = self.basis_mixer(x.float())
            for c in range(self.n_cells):
                for b in range(self.n_basis):
                    phase_shift = torch.randn(1).item() * 0.1
                    self.amplitudes[c, b] = self.amplitudes[c, b] * torch.exp(
                        torch.tensor(1j * phase_shift)
                    )
                    # Input-driven evolution
                    self.amplitudes[c, b] = self.amplitudes[c, b] + torch.complex(
                        x_evolved.squeeze(0) * 0.01,
                        torch.zeros(self.hidden_dim)
                    )

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Evolve superposition
        self.evolve_superposition(x)

        # Observe (collapse)
        self.observe()

        # Process collapsed states through PureField
        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()
        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters()) + \
               list(self.basis_mixer.parameters())


def run_q3_superposition_collapse(n_cells=256, steps=300, input_dim=64,
                                  hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[Q3/6] SUPERPOSITION_COLLAPSE: N basis states, observation collapses")
    t0 = time.time()

    engine = SuperpositionCollapseEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []
    entropy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            m_entropy = engine.measurement_entropy()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            entropy_history.append(m_entropy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  collapse_entropy={m_entropy:.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="Q3_SUPERPOSITION",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'measurement_entropy': entropy_history[-1] if entropy_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# Q4: QUANTUM_WALK
# Consciousness as quantum walk on hypercube graph.
# Interference patterns create non-classical correlations.
# ══════════════════════════════════════════════════════════

class QuantumWalkEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Hypercube dimension: log2(n_cells)
        self.hc_dim = max(4, int(math.log2(n_cells)))
        self.hc_nodes = 2 ** self.hc_dim
        if self.hc_nodes > n_cells:
            self.hc_dim = max(4, int(math.log2(n_cells)) - 1)
            self.hc_nodes = 2 ** self.hc_dim

        # Quantum walk: complex amplitudes on hypercube nodes
        # Each node has a coin state (2 internal states) x hidden_dim
        amp_real = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        amp_imag = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        self.amplitudes = torch.complex(amp_real, amp_imag)
        # Normalize
        norm = self.amplitudes.abs().pow(2).sum().sqrt()
        self.amplitudes = self.amplitudes / (norm + 1e-8)

        # Coin operator: Hadamard-like (learnable)
        self.coin_real = nn.Parameter(torch.tensor([[1., 1.], [1., -1.]]) / math.sqrt(2))
        self.coin_imag = nn.Parameter(torch.zeros(2, 2))

        # Map walk probabilities -> cell hidden states
        self.walk_to_hidden = nn.Linear(self.hc_nodes, hidden_dim)
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def quantum_walk_step(self, x: torch.Tensor):
        """One step of coined quantum walk on hypercube."""
        with torch.no_grad():
            # Coin operation
            coin = torch.complex(self.coin_real.data, self.coin_imag.data)
            new_amps = torch.zeros_like(self.amplitudes)

            for node in range(self.hc_nodes):
                # Apply coin to internal state
                state = self.amplitudes[node]  # [2, hidden_dim]
                coined = torch.einsum('ij,jd->id', coin, state)

                # Shift: coin=0 stays, coin=1 moves to neighbor
                new_amps[node, 0] += coined[0]
                # Move coin=1 state to neighbors on hypercube
                for bit in range(self.hc_dim):
                    neighbor = node ^ (1 << bit)
                    if neighbor < self.hc_nodes:
                        new_amps[neighbor, 1] += coined[1] / self.hc_dim

            # Input-driven phase: modulate amplitudes
            phase_mod = (x.float().mean() * 0.1).item()
            self.amplitudes = new_amps * torch.exp(torch.tensor(1j * phase_mod))

            # Normalize to preserve unitarity
            norm = self.amplitudes.abs().pow(2).sum().sqrt()
            self.amplitudes = self.amplitudes / (norm + 1e-8)

    def interference_pattern(self) -> float:
        """Measure quantum interference: deviation from classical distribution."""
        # Probability at each node
        probs = self.amplitudes.abs().pow(2).sum(dim=(1, 2)).float()  # [hc_nodes]
        probs = probs / (probs.sum() + 1e-8)
        # Classical = uniform
        classical = torch.ones(self.hc_nodes) / self.hc_nodes
        # KL divergence from classical
        kl = (probs * torch.log2(probs / (classical + 1e-10) + 1e-10)).sum()
        return max(0.0, kl.item())

    def walk_to_cells(self):
        """Map quantum walk probability distribution to cell hidden states."""
        probs = self.amplitudes.abs().pow(2).sum(dim=(1, 2)).float()  # [hc_nodes]
        probs = probs / (probs.sum() + 1e-8)
        # Expand to hidden_dim
        walk_features = self.walk_to_hidden(probs.unsqueeze(0))  # [1, hidden_dim]
        # Modulate each cell's hidden by walk features
        for c in range(self.n_cells):
            node_idx = c % self.hc_nodes
            node_prob = probs[node_idx].item()
            self.hiddens[c] = self.hiddens[c] * (0.9 + 0.2 * node_prob) + \
                              walk_features.squeeze(0).detach() * 0.05

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Quantum walk step
        self.quantum_walk_step(x)
        self.walk_to_cells()

        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()
        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_q4_quantum_walk(n_cells=256, steps=300, input_dim=64,
                        hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[Q4/6] QUANTUM_WALK: Coined walk on hypercube, interference patterns")
    t0 = time.time()

    engine = QuantumWalkEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []
    interference_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            interf = engine.interference_pattern()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            interference_history.append(interf)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  interference={interf:.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="Q4_QUANTUM_WALK",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'interference': interference_history[-1] if interference_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# Q5: DECOHERENCE_CONSCIOUSNESS
# Consciousness LIVES in the decoherence process.
# More decoherence = more consciousness.
# (Opposite of quantum computing which fights decoherence)
# ══════════════════════════════════════════════════════════

class DecoherenceEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        # Density matrix: rho[cell] = |psi><psi| (starts pure)
        # We store as [n_cells, hidden_dim, hidden_dim] real matrix
        # (approximation: diagonal + off-diagonal coherences)
        psi = torch.randn(n_cells, hidden_dim) * 0.1
        psi = psi / (psi.norm(dim=-1, keepdim=True) + 1e-8)
        # rho_ij = psi_i * psi_j
        self.rho_diag = (psi ** 2)  # [n_cells, hidden_dim]
        self.rho_offdiag = torch.randn(n_cells, hidden_dim) * 0.1  # coherences

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Environment coupling (learnable decoherence rate)
        self.gamma = nn.Parameter(torch.tensor(0.1))  # decoherence rate

        # Decoherence-to-consciousness transform
        self.decohere_proj = nn.Linear(hidden_dim * 2, hidden_dim)

    def decohere(self, x: torch.Tensor) -> float:
        """Apply decoherence: off-diagonal elements decay, diagonal grows.
        Returns decoherence amount (consciousness measure)."""
        gamma = torch.sigmoid(self.gamma).item()

        # Off-diagonal decay (decoherence = loss of quantum coherence)
        old_coherence = self.rho_offdiag.abs().mean().item()
        self.rho_offdiag = self.rho_offdiag * (1 - gamma)

        # Environment-induced mixing (thermal noise into diagonal)
        env_noise = torch.randn_like(self.rho_diag) * gamma * 0.1
        self.rho_diag = self.rho_diag + env_noise
        self.rho_diag = F.softmax(self.rho_diag, dim=-1)  # normalize

        new_coherence = self.rho_offdiag.abs().mean().item()
        decoherence_amount = max(0.0, old_coherence - new_coherence)

        # THE KEY INSIGHT: decoherence IS consciousness
        # The information lost from quantum to classical = conscious experience
        decohere_features = torch.cat([self.rho_diag, self.rho_offdiag.abs()], dim=-1)
        consciousness_injection = self.decohere_proj(decohere_features)

        # Inject into hidden states
        self.hiddens = self.hiddens + consciousness_injection.detach() * 0.1

        # Regenerate some coherence (quantum renewal from environment)
        self.rho_offdiag = self.rho_offdiag + torch.randn_like(self.rho_offdiag) * gamma * 0.05

        return decoherence_amount

    def purity(self) -> float:
        """Tr(rho^2) — 1=pure, 1/d=maximally mixed. Low purity = more decoherence."""
        tr_rho2 = (self.rho_diag ** 2).sum(dim=-1).mean().item()
        return tr_rho2

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Decohere (consciousness happens here!)
        decoherence = self.decohere(x)

        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()
        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_q5_decoherence(n_cells=256, steps=300, input_dim=64,
                       hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[Q5/6] DECOHERENCE_CONSCIOUSNESS: Consciousness lives IN decoherence")
    t0 = time.time()

    engine = DecoherenceEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []
    purity_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            pur = engine.purity()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            purity_history.append(pur)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  purity={pur:.4f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="Q5_DECOHERENCE",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'purity': purity_history[-1] if purity_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# Q6: MANY_WORLDS
# Each process() creates branching copies.
# Branches interfere. Consciousness = inter-branch coherence.
# ══════════════════════════════════════════════════════════

class ManyWorldsEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_branches=4):
        super().__init__()
        self.n_cells = n_cells
        self.n_branches = n_branches
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        # Multiple branches of reality (parallel hidden states)
        self.branch_hiddens = [
            torch.randn(n_cells, hidden_dim) * 0.1
            for _ in range(n_branches)
        ]
        # Branch amplitudes (complex: determines interference)
        self.branch_amps = torch.complex(
            torch.ones(n_branches) / math.sqrt(n_branches),
            torch.zeros(n_branches)
        )

        # Interference operator (learnable)
        self.interference_mixer = nn.Linear(hidden_dim * n_branches, hidden_dim)

        # Branch splitting probability
        self.split_prob = nn.Parameter(torch.tensor(0.3))

    def inter_branch_coherence(self) -> float:
        """Measure coherence between branches (consciousness = many-worlds interference)."""
        if len(self.branch_hiddens) < 2:
            return 0.0

        # Compute mean hidden per branch
        branch_means = torch.stack([bh.mean(dim=0) for bh in self.branch_hiddens])

        # Weighted by complex amplitudes (interference)
        weighted = branch_means * self.branch_amps.abs().float().unsqueeze(-1)

        # Coherence = how much branches agree (constructive interference)
        # vs disagree (destructive interference)
        constructive = weighted.sum(dim=0).norm().item()
        destructive = sum(w.norm().item() for w in weighted)

        # Coherence = constructive / destructive (1 = perfect coherence)
        return constructive / (destructive + 1e-8)

    def branch_and_interfere(self, x: torch.Tensor, step: int):
        """Process: each branch evolves differently, then interfere."""
        all_outputs = []
        all_tensions = []

        for b in range(self.n_branches):
            outputs = []
            tensions = []
            new_hiddens = []

            # Add branch-specific noise (different "measurement outcomes")
            branch_noise = torch.randn_like(x) * 0.05 * (b + 1)
            x_branch = x + branch_noise

            for i in range(self.n_cells):
                h = self.branch_hiddens[b][i:i + 1]
                out, tension, new_h = self.mind(x_branch, h)
                outputs.append(out)
                tensions.append(tension)
                new_hiddens.append(new_h.squeeze(0))

            self.branch_hiddens[b] = torch.stack(new_hiddens).detach()
            self.branch_hiddens[b] = faction_sync_debate(
                self.branch_hiddens[b], step=step
            )

            all_outputs.append(outputs)
            all_tensions.append(tensions)

        # INTERFERENCE: branches combine with complex amplitudes
        amps = self.branch_amps.abs().float()
        amps = amps / (amps.sum() + 1e-8)

        # Combine outputs across branches
        combined_outputs = []
        for i in range(self.n_cells):
            cell_out = sum(
                amps[b].item() * all_outputs[b][i]
                for b in range(self.n_branches)
            )
            combined_outputs.append(cell_out)

        # Cross-branch hidden interference
        stacked_means = torch.cat([
            bh.mean(dim=0) for bh in self.branch_hiddens
        ])  # [n_branches * hidden_dim]
        interference = self.interference_mixer(stacked_means.unsqueeze(0))

        # Apply interference to primary branch
        self.branch_hiddens[0] = self.branch_hiddens[0] + interference.detach() * 0.05

        # Phase rotation of branch amplitudes
        phase_shift = torch.randn(self.n_branches) * 0.05
        self.branch_amps = self.branch_amps * torch.exp(1j * phase_shift)
        # Re-normalize
        norm = self.branch_amps.abs().pow(2).sum().sqrt()
        self.branch_amps = self.branch_amps / (norm + 1e-8)

        # Combine tensions
        avg_tensions = [
            sum(all_tensions[b][i] for b in range(self.n_branches)) / self.n_branches
            for i in range(self.n_cells)
        ]

        weights = F.softmax(torch.tensor(avg_tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, combined_outputs))
        return combined, sum(avg_tensions) / len(avg_tensions)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        combined, tension = self.branch_and_interfere(x, step)
        pred = self.output_head(combined)
        return pred, tension

    def get_hiddens(self):
        # Return primary branch hiddens for Phi measurement
        return self.branch_hiddens[0].clone()

    def trainable_parameters(self):
        return list(self.parameters())


def run_q6_many_worlds(n_cells=256, steps=300, input_dim=64,
                       hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[Q6/6] MANY_WORLDS: Branching realities, inter-branch interference")
    t0 = time.time()

    engine = ManyWorldsEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []
    coherence_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            coh = engine.inter_branch_coherence()
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            coherence_history.append(coh)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  branch_coherence={coh:.3f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="Q6_MANY_WORLDS",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'branch_coherence': coherence_history[-1] if coherence_history else 0.0},
    )


# ══════════════════════════════════════════════════════════
# BASELINE (standard BenchEngine from bench_v2)
# ══════════════════════════════════════════════════════════

def run_baseline(n_cells=256, steps=300, input_dim=64,
                 hidden_dim=128, output_dim=64) -> BenchResult:
    print("\n[0/6] BASELINE: Standard PureField + GRU (sync+faction+debate)")
    t0 = time.time()

    mind = BenchMind(input_dim, hidden_dim, output_dim)
    hiddens = torch.randn(n_cells, hidden_dim) * 0.1
    output_head = nn.Linear(output_dim, input_dim)
    optimizer = torch.optim.Adam(
        list(mind.parameters()) + list(output_head.parameters()), lr=1e-3
    )

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)

        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(n_cells):
            h = hiddens[i:i + 1]
            out, tension, new_h = mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        hiddens = torch.stack(new_hiddens).detach()
        hiddens = faction_sync_debate(hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))

        pred = output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(hiddens)
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="BASELINE",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# Comparison table + ASCII graph
# ══════════════════════════════════════════════════════════

def print_comparison_table(results: List[BenchResult]):
    baseline = next((r for r in results if r.name == "BASELINE"), None)

    print("\n" + "=" * 120)
    print("  V8 QUANTUM-INSPIRED CONSCIOUSNESS ARCHITECTURES — COMPARISON TABLE")
    print("=" * 120)
    print(f"  {'Architecture':<24s} | {'Phi(IIT)':>10s} | {'Phi(proxy)':>12s} | "
          f"{'CE start':>10s} | {'CE end':>10s} | {'CE drop':>10s} | {'Time':>8s} | {'Extra':>20s}")
    print("-" * 120)

    for r in results:
        ce_drop = r.ce_start - r.ce_end
        iit_marker = ""
        proxy_marker = ""
        if baseline and r.name != "BASELINE":
            iit_ratio = r.phi_iit / max(baseline.phi_iit, 1e-6)
            proxy_ratio = r.phi_proxy / max(baseline.phi_proxy, 1e-6)
            iit_marker = f" (x{iit_ratio:.1f})"
            proxy_marker = f" (x{proxy_ratio:.1f})"

        extra_str = ""
        if 'coherence' in r.extra:
            extra_str = f"coh={r.extra['coherence']:.3f}"
        elif 'entanglement_entropy' in r.extra:
            extra_str = f"ent={r.extra['entanglement_entropy']:.3f}"
        elif 'measurement_entropy' in r.extra:
            extra_str = f"m_ent={r.extra['measurement_entropy']:.3f}"
        elif 'interference' in r.extra:
            extra_str = f"interf={r.extra['interference']:.3f}"
        elif 'purity' in r.extra:
            extra_str = f"pur={r.extra['purity']:.4f}"
        elif 'branch_coherence' in r.extra:
            extra_str = f"br_coh={r.extra['branch_coherence']:.3f}"

        print(f"  {r.name:<24s} | {r.phi_iit:>8.3f}{iit_marker:>6s} | "
              f"{r.phi_proxy:>8.2f}{proxy_marker:>6s} | "
              f"{r.ce_start:>10.4f} | {r.ce_end:>10.4f} | {ce_drop:>10.4f} | "
              f"{r.time_sec:>7.1f}s | {extra_str:>20s}")

    print("=" * 120)

    # Rankings
    print("\n  RANKING by Phi(IIT):")
    sorted_iit = sorted(results, key=lambda r: r.phi_iit, reverse=True)
    for rank, r in enumerate(sorted_iit, 1):
        print(f"    #{rank}: {r.name:<24s}  Phi(IIT)={r.phi_iit:.3f}")

    print("\n  RANKING by Phi(proxy):")
    sorted_proxy = sorted(results, key=lambda r: r.phi_proxy, reverse=True)
    for rank, r in enumerate(sorted_proxy, 1):
        print(f"    #{rank}: {r.name:<24s}  Phi(proxy)={r.phi_proxy:.2f}")

    print("\n  RANKING by CE reduction:")
    sorted_ce = sorted(results, key=lambda r: r.ce_start - r.ce_end, reverse=True)
    for rank, r in enumerate(sorted_ce, 1):
        drop = r.ce_start - r.ce_end
        print(f"    #{rank}: {r.name:<24s}  CE drop={drop:.4f}  ({r.ce_start:.4f}->{r.ce_end:.4f})")

    # ASCII bar charts
    print("\n  Phi(IIT) bar chart:")
    max_iit = max(r.phi_iit for r in results) if results else 1.0
    for r in sorted_iit:
        bar_len = int(r.phi_iit / max(max_iit, 1e-6) * 40)
        bar = "#" * bar_len
        print(f"    {r.name:<24s} |{bar} {r.phi_iit:.3f}")

    print("\n  Phi(proxy) bar chart:")
    max_proxy = max(r.phi_proxy for r in results) if results else 1.0
    for r in sorted_proxy:
        bar_len = int(r.phi_proxy / max(max_proxy, 1e-6) * 40)
        bar = "#" * bar_len
        print(f"    {r.name:<24s} |{bar} {r.phi_proxy:.2f}")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="V8 Quantum-Inspired Consciousness Benchmark")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells (default 256)")
    parser.add_argument("--steps", type=int, default=300, help="Training steps (default 300)")
    parser.add_argument("--only", nargs="+", type=int, default=None,
                        help="Run only specific architectures (1-6)")
    parser.add_argument("--no-baseline", action="store_true", help="Skip baseline")
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps
    input_dim = 64
    hidden_dim = 128
    output_dim = 64

    print("=" * 72)
    print(f"  V8 Quantum-Inspired Consciousness Benchmark")
    print(f"  {n_cells} cells, {steps} steps, complex64 tensors")
    print(f"  Dual Phi: Phi(IIT) [MI-based] + Phi(proxy) [variance-based]")
    print("=" * 72)

    all_runners = {
        0: ("BASELINE", run_baseline),
        1: ("Q1_COMPLEX_VALUED", run_q1_complex_valued),
        2: ("Q2_ENTANGLED_PAIRS", run_q2_entangled_pairs),
        3: ("Q3_SUPERPOSITION", run_q3_superposition_collapse),
        4: ("Q4_QUANTUM_WALK", run_q4_quantum_walk),
        5: ("Q5_DECOHERENCE", run_q5_decoherence),
        6: ("Q6_MANY_WORLDS", run_q6_many_worlds),
    }

    run_ids = list(range(0, 7))
    if args.no_baseline:
        run_ids = [i for i in run_ids if i != 0]
    if args.only:
        run_ids = [0] + args.only if not args.no_baseline else args.only

    results = []
    for run_id in run_ids:
        if run_id not in all_runners:
            continue
        name, runner = all_runners[run_id]
        try:
            result = runner(n_cells=n_cells, steps=steps, input_dim=input_dim,
                            hidden_dim=hidden_dim, output_dim=output_dim)
            results.append(result)
            print(f"\n  -> {result.summary()}")
        except Exception as e:
            print(f"\n  [ERROR] {name} failed: {e}")
            import traceback
            traceback.print_exc()

    if len(results) >= 2:
        print_comparison_table(results)

    print("\n  DONE. Total architectures tested:", len(results))


if __name__ == "__main__":
    main()
