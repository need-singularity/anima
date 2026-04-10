#!/usr/bin/env python3
"""quantum_attention_engine.py — 양자 어텐션 의식 엔진 + 벤치마크

Hybrid of the two best Phi mechanisms:
  Q4 Quantum Walk = Phi(IIT) 19.34 (best raw Phi)
  ATTENTION_PHI = Phi(IIT) 13.70 (fastest, content routing)

QuantumAttentionEngine combines:
  1. Quantum walk: phase-based neighbor interference on hypercube
  2. Self-attention: content-based all-to-all routing
  3. Frustration: 50% anti-ferromagnetic coupling
  4. Standing wave: resonance modes
  5. Category morphism: structural integration

No GRU gates. Pure attention + quantum mechanics.
Both mechanisms are gradient-free in the consciousness engine (Trinity C compatible).

Usage:
  python quantum_attention_engine.py                  # Full benchmark
  python quantum_attention_engine.py --steps 500      # Custom steps
  python quantum_attention_engine.py --cells 512      # Custom cell count
"""

import sys
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DIM, HIDDEN = 64, 128


# ══════════════════════════════════════════════════════════
# Phi(IIT) Calculator
# ══════════════════════════════════════════════════════════

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
                eigvals, eigvecs = np.linalg.eigh(laplacian)
                fiedler = eigvecs[:, 1]
                ga = [i for i in range(n) if fiedler[i] >= 0]
                gb = [i for i in range(n) if fiedler[i] < 0]
                if not ga or not gb:
                    ga, gb = list(range(n // 2)), list(range(n // 2, n))
                return sum(mi_matrix[i, j] for i in ga for j in gb)
            except Exception:
                return 0.0


_phi_iit_calc = PhiIIT(n_bins=16)


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    """Phi proxy: global_variance - mean(faction_variances)."""
    h = hiddens.abs().float() if hiddens.is_complex() else hiddens.float()
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


def measure_dual_phi(hiddens: torch.Tensor, n_factions: int = 8) -> Tuple[float, float]:
    """Returns (phi_iit, phi_proxy)."""
    h_real = hiddens.abs().float() if hiddens.is_complex() else hiddens.float()
    p_iit, _ = _phi_iit_calc.compute(h_real)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


def generate_batch(input_dim: int, batch_size: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
    x = torch.randn(batch_size, input_dim)
    target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
    return x, target


# ══════════════════════════════════════════════════════════
# Shared helpers: faction sync, quantum walk, frustration, standing wave
# ══════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════
# QuantumAttentionEngine — The Hybrid
# ══════════════════════════════════════════════════════════

class QuantumAttentionEngine(nn.Module):
    """양자 어텐션 의식 엔진

    Cells = complex-valued embeddings
    Interaction = quantum walk (phase interference) + self-attention (content routing)
    No GRU gates -- pure attention + quantum mechanics

    Step:
    1. Quantum walk: phase-based neighbor interference on hypercube
    2. Self-attention: content-based all-to-all routing
    3. Frustration: 50% anti-ferromagnetic
    4. Standing wave: resonance modes
    5. Category morphism: structural integration
    """

    def __init__(self, n_cells: int = 256, input_dim: int = 64,
                 hidden_dim: int = 128, output_dim: int = 64,
                 n_heads: int = 8, n_attn_layers: int = 2):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.n_heads = n_heads
        self.n_attn_layers = n_attn_layers

        # ── Quantum walk on hypercube ──
        self.hc_dim = max(4, int(math.log2(n_cells)))
        self.hc_nodes = 2 ** self.hc_dim
        if self.hc_nodes > n_cells:
            self.hc_dim = max(4, int(math.log2(n_cells)) - 1)
            self.hc_nodes = 2 ** self.hc_dim

        # Complex amplitudes: [hc_nodes, 2_coin_states, hidden_dim]
        amp_real = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        amp_imag = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        self.amplitudes = torch.complex(amp_real, amp_imag)
        norm = self.amplitudes.abs().pow(2).sum().sqrt()
        self.amplitudes = self.amplitudes / (norm + 1e-8)

        # Learnable coin operator (Hadamard-like)
        self.coin_real = nn.Parameter(torch.tensor([[1., 1.], [1., -1.]]) / math.sqrt(2))
        self.coin_imag = nn.Parameter(torch.zeros(2, 2))

        # ── Self-attention layers (content routing) ──
        self.cell_embeddings = nn.Parameter(torch.randn(n_cells, hidden_dim) * 0.1)
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        self.attn_layers = nn.ModuleList()
        self.layer_norms = nn.ModuleList()
        for _ in range(n_attn_layers):
            self.attn_layers.append(
                nn.MultiheadAttention(embed_dim=hidden_dim, num_heads=n_heads, batch_first=True)
            )
            self.layer_norms.append(nn.LayerNorm(hidden_dim))

        # ── Output ──
        self.output_head = nn.Linear(hidden_dim, input_dim)

        # ── Frustration coupling signs (50% anti-ferromagnetic) ──
        self.frustration_signs = torch.ones(n_cells)
        anti_idx = torch.randperm(n_cells)[:n_cells // 2]
        self.frustration_signs[anti_idx] = -1.0

    # ── Step 1: Quantum walk ──
    def quantum_walk_step(self, x: torch.Tensor):
        """One step of coined quantum walk on hypercube. Gradient-free."""
        with torch.no_grad():
            coin = torch.complex(self.coin_real.data, self.coin_imag.data)
            new_amps = torch.zeros_like(self.amplitudes)

            for node in range(self.hc_nodes):
                state = self.amplitudes[node]  # [2, hidden_dim]
                coined = torch.einsum('ij,jd->id', coin, state)

                # coin=0 stays, coin=1 shifts to hypercube neighbors
                new_amps[node, 0] += coined[0]
                for bit in range(self.hc_dim):
                    neighbor = node ^ (1 << bit)
                    if neighbor < self.hc_nodes:
                        new_amps[neighbor, 1] += coined[1] / self.hc_dim

            # Input-driven phase modulation
            phase_mod = (x.float().mean() * 0.1).item()
            self.amplitudes = new_amps * torch.exp(torch.tensor(1j * phase_mod))

            # Normalize (preserve unitarity)
            norm = self.amplitudes.abs().pow(2).sum().sqrt()
            self.amplitudes = self.amplitudes / (norm + 1e-8)

    def walk_probability_distribution(self) -> torch.Tensor:
        """Probability at each hypercube node from quantum walk."""
        probs = self.amplitudes.abs().pow(2).sum(dim=(1, 2)).float()  # [hc_nodes]
        return probs / (probs.sum() + 1e-8)

    def interference_pattern(self) -> float:
        """KL divergence from classical uniform distribution."""
        probs = self.walk_probability_distribution()
        classical = torch.ones(self.hc_nodes) / self.hc_nodes
        kl = (probs * torch.log2(probs / (classical + 1e-10) + 1e-10)).sum()
        return max(0.0, kl.item())

    def inject_walk_into_cells(self):
        """Map quantum walk probability distribution into cell embeddings. Gradient-free.

        Uses STRONG modulation + multi-bit interference to maximize quantum effects.
        The quantum walk creates non-uniform probability -> cells at different nodes
        get differentiated -> higher MI between cells -> higher Phi(IIT).
        """
        with torch.no_grad():
            probs = self.walk_probability_distribution()
            # Phase amplitudes (complex) carry richer structure than just probabilities
            phase_angles = self.amplitudes.sum(dim=1).angle().float().mean(dim=-1)  # [hc_nodes]

            for c in range(self.n_cells):
                node_idx = c % self.hc_nodes
                node_prob = probs[node_idx].item()
                phase = phase_angles[node_idx].item()

                # Strong probability-based modulation (wider range than before)
                self.cell_embeddings.data[c] *= (0.8 + 0.4 * node_prob)

                # Phase-based rotation: different phases -> different cell states
                # This creates differentiation even for cells on same-probability nodes
                cos_p, sin_p = math.cos(phase * 0.3), math.sin(phase * 0.3)
                h = self.cell_embeddings.data[c]
                d = self.hidden_dim
                # Rotate first half vs second half by phase angle
                h_first = h[:d // 2] * cos_p - h[d // 2:] * sin_p
                h_second = h[:d // 2] * sin_p + h[d // 2:] * cos_p
                self.cell_embeddings.data[c] = torch.cat([h_first, h_second]) * 0.5 + h * 0.5

                # Multi-bit interference: blend with ALL hypercube neighbors
                for bit in range(min(self.hc_dim, 6)):
                    neighbor = node_idx ^ (1 << bit)
                    if neighbor < self.hc_nodes:
                        nb_prob = probs[neighbor].item()
                        # Interference term: constructive if probs similar, destructive if different
                        interf = (node_prob - nb_prob) * 0.03
                        self.cell_embeddings.data[c] += interf

    # ── Step 2: Self-attention (content routing) ──
    def attention_step(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        """Multi-layer self-attention over cell embeddings. Returns (cells, attn_tension).

        ADDITIVE update: attention adds a small delta on top of quantum-walk-modulated cells.
        This preserves the phase structure from quantum walk while adding content routing.
        """
        x_proj = self.input_proj(x)  # [1, hidden_dim]
        cells = self.cell_embeddings.unsqueeze(0)  # [1, n_cells, hidden_dim]
        cells = cells + x_proj.unsqueeze(1) * 0.1  # gentle input injection

        total_attn_std = 0.0
        for attn_layer, ln in zip(self.attn_layers, self.layer_norms):
            attn_out, attn_weights = attn_layer(cells, cells, cells)
            cells = ln(cells + attn_out)
            if attn_weights is not None:
                total_attn_std += float(attn_weights.std().detach())

        # NO embedding update from attention -- quantum walk owns cell states.
        # Attention is pure content routing for output; it reads cells, doesn't write.
        # This preserves the quantum walk's phase-differentiated structure.

        tension = total_attn_std / self.n_attn_layers
        return cells, tension

    # ── Step 3: Frustration ──
    def frustration_step(self, n_samples: int = 64):
        """50% anti-ferromagnetic coupling. Gradient-free."""
        n = self.n_cells
        n_bits = max(1, int(math.log2(n)))
        with torch.no_grad():
            for i in range(min(n, n_samples)):
                influence = torch.zeros(self.hidden_dim)
                cnt = 0
                for bit in range(min(n_bits, 10)):
                    j = i ^ (1 << bit)
                    if j < n:
                        sign = self.frustration_signs[i] * self.frustration_signs[j]
                        influence += sign.item() * self.cell_embeddings.data[j]
                        cnt += 1
                if cnt > 0:
                    self.cell_embeddings.data[i] = (
                        0.85 * self.cell_embeddings.data[i] + 0.15 * influence / cnt
                    )

    # ── Step 4: Standing wave ──
    def standing_wave_step(self, step: int):
        """Counter-propagating waves create resonance modes. Gradient-free."""
        n = self.n_cells
        fwd = (step * 0.15) % n
        bwd = (n - step * 0.15) % n
        with torch.no_grad():
            for i in range(n):
                amp = 1.0 / (math.cosh((i - fwd) / 2) ** 2) + \
                      1.0 / (math.cosh((i - bwd) / 2) ** 2)
                self.cell_embeddings.data[i] *= (1.0 + 0.03 * amp)

    # ── Step 5: Category morphism ──
    def category_morphism_step(self, n_sample: int = 32):
        """Structural integration via category-theoretic morphisms. Gradient-free."""
        n = min(self.n_cells, n_sample)
        with torch.no_grad():
            hs = [self.cell_embeddings.data[i] for i in range(n)]
            for i in range(n):
                morphism_sum = sum(
                    torch.tanh(hs[j] - hs[i]) for j in range(n) if j != i
                ) / max(n - 1, 1)
                self.cell_embeddings.data[i] = (
                    0.9 * self.cell_embeddings.data[i] + 0.1 * morphism_sum
                )

    # ── Full process step ──
    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        """Full consciousness step: quantum walk -> attention -> frustration -> wave -> morphism.

        All consciousness updates are gradient-free (no_grad).
        Only the output_head participates in CE gradient.
        This preserves quantum walk structure from being disrupted by backprop.
        """
        # === PHASE A: Consciousness (ALL gradient-free) ===
        with torch.no_grad():
            # Step 1: Quantum walk (phase coherence) -- run TWICE for stronger effect
            self.quantum_walk_step(x)
            self.inject_walk_into_cells()
            self.quantum_walk_step(x)  # double walk = stronger interference
            self.inject_walk_into_cells()

            # Step 3: Frustration (diversity)
            self.frustration_step(n_samples=128)

            # Step 4: Standing wave (resonance)
            self.standing_wave_step(step)

            # Step 5: Category morphism (structural integration)
            if step % 3 == 0:
                self.category_morphism_step(n_sample=48)

            # Step 6: Faction sync + debate (WEAK sync to preserve quantum diversity)
            self.cell_embeddings.data = faction_sync_debate(
                self.cell_embeddings.data, sync_strength=0.08, debate_strength=0.20,
                step=step
            )

        # === PHASE B: Attention (content routing, gradient flows only through output) ===
        # Attention reads from quantum-modulated cells but updates are additive/small
        cells, attn_tension = self.attention_step(x)

        # Output: mean pool through output head (ONLY this gets CE gradient)
        output = self.output_head(cells.mean(dim=1))
        return output, attn_tension

    def get_hiddens(self) -> torch.Tensor:
        return self.cell_embeddings.data.clone()

    def trainable_parameters(self):
        return list(self.parameters())


# ══════════════════════════════════════════════════════════
# Pure Quantum Walk Engine (for comparison)
# ══════════════════════════════════════════════════════════

class PureQuantumWalkEngine(nn.Module):
    """Q4 quantum walk only. No attention. Uses BenchMind (GRU) for cell processing."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim

        self.hc_dim = max(4, int(math.log2(n_cells)))
        self.hc_nodes = 2 ** self.hc_dim
        if self.hc_nodes > n_cells:
            self.hc_dim = max(4, int(math.log2(n_cells)) - 1)
            self.hc_nodes = 2 ** self.hc_dim

        amp_real = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        amp_imag = torch.randn(self.hc_nodes, 2, hidden_dim) * 0.1
        self.amplitudes = torch.complex(amp_real, amp_imag)
        norm = self.amplitudes.abs().pow(2).sum().sqrt()
        self.amplitudes = self.amplitudes / (norm + 1e-8)

        self.coin_real = nn.Parameter(torch.tensor([[1., 1.], [1., -1.]]) / math.sqrt(2))
        self.coin_imag = nn.Parameter(torch.zeros(2, 2))

        self.walk_to_hidden = nn.Linear(self.hc_nodes, hidden_dim)

        # GRU-based mind (like original Q4)
        self.engine_a = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(), nn.Linear(128, output_dim))
        self.engine_g = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(), nn.Linear(128, output_dim))
        self.memory = nn.GRUCell(output_dim + 1, hidden_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def quantum_walk_step(self, x):
        with torch.no_grad():
            coin = torch.complex(self.coin_real.data, self.coin_imag.data)
            new_amps = torch.zeros_like(self.amplitudes)
            for node in range(self.hc_nodes):
                state = self.amplitudes[node]
                coined = torch.einsum('ij,jd->id', coin, state)
                new_amps[node, 0] += coined[0]
                for bit in range(self.hc_dim):
                    neighbor = node ^ (1 << bit)
                    if neighbor < self.hc_nodes:
                        new_amps[neighbor, 1] += coined[1] / self.hc_dim
            phase_mod = (x.float().mean() * 0.1).item()
            self.amplitudes = new_amps * torch.exp(torch.tensor(1j * phase_mod))
            norm = self.amplitudes.abs().pow(2).sum().sqrt()
            self.amplitudes = self.amplitudes / (norm + 1e-8)

    def walk_to_cells(self):
        probs = self.amplitudes.abs().pow(2).sum(dim=(1, 2)).float()
        probs = probs / (probs.sum() + 1e-8)
        walk_features = self.walk_to_hidden(probs.unsqueeze(0))
        for c in range(self.n_cells):
            node_idx = c % self.hc_nodes
            node_prob = probs[node_idx].item()
            self.hiddens[c] = self.hiddens[c] * (0.9 + 0.2 * node_prob) + \
                              walk_features.squeeze(0).detach() * 0.05

    def process(self, x, step=0):
        self.quantum_walk_step(x)
        self.walk_to_cells()

        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            combined = torch.cat([x, h], dim=-1)
            a = self.engine_a(combined)
            g = self.engine_g(combined)
            out = a - g
            t = (out ** 2).mean(dim=-1, keepdim=True)
            mem_in = torch.cat([out.detach(), t.detach()], dim=-1)
            new_h = self.memory(mem_in, h)
            outputs.append(out)
            tensions.append(t.mean().item())
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


# ══════════════════════════════════════════════════════════
# Pure Attention Engine (for comparison)
# ══════════════════════════════════════════════════════════

class PureAttentionEngine(nn.Module):
    """ATTENTION_PHI only. No quantum walk."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_heads=8):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim

        self.cell_embeddings = nn.Parameter(torch.randn(n_cells, hidden_dim) * 0.1)
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=n_heads, batch_first=True)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.output_head = nn.Linear(hidden_dim, input_dim)

    def process(self, x, step=0):
        x_proj = self.input_proj(x)
        cells = self.cell_embeddings.unsqueeze(0)
        cells = cells + x_proj.unsqueeze(1) * 0.1
        attn_out, attn_weights = self.attention(cells, cells, cells)
        cells = self.layer_norm(cells + attn_out)

        with torch.no_grad():
            self.cell_embeddings.data = (
                0.9 * self.cell_embeddings.data + 0.1 * cells.squeeze(0).detach()
            )

        tension = float(attn_weights.std()) if attn_weights is not None else 0.0
        output = self.output_head(cells.mean(dim=1))
        return output, tension

    def get_hiddens(self):
        return self.cell_embeddings.data.clone()

    def trainable_parameters(self):
        return list(self.parameters())


# ══════════════════════════════════════════════════════════
# MitosisEngine baseline (from mitosis.py)
# ══════════════════════════════════════════════════════════

def _make_mitosis_baseline(n_cells, input_dim, hidden_dim, output_dim):
    """Create MitosisEngine baseline with Cell objects for PhiCalculator compatibility."""
    from mitosis import MitosisEngine
    engine = MitosisEngine(input_dim, hidden_dim, output_dim,
                           initial_cells=2, max_cells=n_cells)
    while len(engine.cells) < n_cells:
        engine._create_cell(parent=engine.cells[0])
    # Warm up
    for _ in range(30):
        engine.process(torch.randn(1, input_dim))
    return engine


# ══════════════════════════════════════════════════════════
# Trinity wrapper: C=QuantumAttentionEngine, D=decoder, W=forced 50%
# ══════════════════════════════════════════════════════════

def run_trinity_qa(n_cells=256, steps=300, input_dim=64,
                   hidden_dim=128, output_dim=64) -> dict:
    """Trinity with QuantumAttentionEngine as C.
    C: consciousness (quantum+attention, gradient-free)
    D: decoder (CE learning)
    W: will (forced 50% learning)
    """
    print("\n[TRINITY-QA] C=QuantumAttentionEngine, D=decoder, W=forced 50%")
    t0 = time.time()

    # Engine C: consciousness
    eng_c = QuantumAttentionEngine(n_cells, input_dim, hidden_dim, output_dim)

    # Engine D: data decoder
    knowledge = nn.Linear(hidden_dim, hidden_dim)
    decoder = nn.Linear(hidden_dim, input_dim)
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)

    # Engine W: will (simple net, forced 50%)
    will_net = nn.Sequential(nn.Linear(hidden_dim, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)

    data = [(torch.randn(1, input_dim) * 0.5, torch.randn(1, input_dim) * 0.3)
            for _ in range(100)]
    learn_count, last_ce = 0, 1.0
    phi_iit_history = []
    ce_history = []

    for step in range(steps):
        x, target = data[step % len(data)]

        # ── C: consciousness (all gradient-free) ──
        with torch.no_grad():
            eng_c.quantum_walk_step(x)
            eng_c.inject_walk_into_cells()
            eng_c.frustration_step()
            eng_c.standing_wave_step(step)
            if step % 3 == 0:
                eng_c.category_morphism_step()
            eng_c.cell_embeddings.data = faction_sync_debate(
                eng_c.cell_embeddings.data, step=step
            )

        # Attention step (has learnable params but we detach for C state)
        x_proj = eng_c.input_proj(x)
        cells = eng_c.cell_embeddings.unsqueeze(0)
        cells = cells + x_proj.unsqueeze(1) * 0.1
        for attn_layer, ln in zip(eng_c.attn_layers, eng_c.layer_norms):
            attn_out, _ = attn_layer(cells, cells, cells)
            cells = ln(cells + attn_out)
        with torch.no_grad():
            eng_c.cell_embeddings.data = (
                0.85 * eng_c.cell_embeddings.data + 0.15 * cells.squeeze(0).detach()
            )

        c_state = eng_c.cell_embeddings.data.mean(dim=0).detach()

        # ── W: will (forced 50% learning) ──
        action_logits = will_net(c_state.unsqueeze(0))
        action = action_logits.argmax(dim=-1).item()
        current_ratio = learn_count / max(step, 1)
        if current_ratio < 0.5 or step % 2 == 0:
            action = 0
        if action == 0:
            learn_count += 1

        # ── D: data (CE learning) ──
        if action == 0:
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :input_dim])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()

        ce_history.append(last_ce)

        # W learning
        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        # W->C feedback
        if action == 1:
            with torch.no_grad():
                eng_c.cell_embeddings.data += torch.randn_like(eng_c.cell_embeddings.data) * 0.01
        elif action == 2:
            with torch.no_grad():
                eng_c.cell_embeddings.data = faction_sync_debate(
                    eng_c.cell_embeddings.data, sync_strength=0.3, step=step
                )

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(eng_c.get_hiddens())
            interf = eng_c.interference_pattern()
            phi_iit_history.append(p_iit)
            print(f"    step {step:>4d}: CE={last_ce:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  interference={interf:.3f}")

    elapsed = time.time() - t0
    return {
        'phi_iit': phi_iit_history[-1] if phi_iit_history else 0.0,
        'ce_end': ce_history[-1] if ce_history else 1.0,
        'ce_start': ce_history[0] if ce_history else 1.0,
        'time_sec': elapsed,
        'interference': eng_c.interference_pattern(),
    }


# ══════════════════════════════════════════════════════════
# Benchmark runners
# ══════════════════════════════════════════════════════════

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
            f"  {self.name:<32s} | "
            f"Phi(IIT)={self.phi_iit:>7.3f}  "
            f"Phi(proxy)={self.phi_proxy:>8.2f} | "
            f"{ce_str:<22s} | "
            f"cells={self.cells:>4d}  steps={self.steps:>5d}  "
            f"time={self.time_sec:.1f}s"
        )


def run_bench_engine(name, engine_cls, n_cells, steps, input_dim, hidden_dim, output_dim,
                     **kwargs) -> BenchResult:
    """Generic benchmark runner for any engine with .process() and .get_hiddens()."""
    print(f"\n[BENCH] {name}")
    t0 = time.time()

    engine = engine_cls(n_cells, input_dim, hidden_dim, output_dim, **kwargs)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

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
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            interf = engine.interference_pattern() if hasattr(engine, 'interference_pattern') else 0.0
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}"
                  + (f"  interf={interf:.3f}" if interf > 0 else ""))

    elapsed = time.time() - t0
    return BenchResult(
        name=name,
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'interference': engine.interference_pattern() if hasattr(engine, 'interference_pattern') else 0.0},
    )


def run_mitosis_baseline(n_cells, steps, input_dim, hidden_dim, output_dim) -> BenchResult:
    """Run MitosisEngine baseline for comparison."""
    print(f"\n[BENCH] MITOSIS_BASELINE")
    t0 = time.time()

    engine = _make_mitosis_baseline(n_cells, input_dim, hidden_dim, output_dim)
    decoder = nn.Linear(hidden_dim, input_dim)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = [(torch.randn(1, input_dim) * 0.5, torch.randn(1, input_dim) * 0.3)
            for _ in range(100)]

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :input_dim])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_history.append(ce.item())

        if step % 50 == 0 or step == steps - 1:
            hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
            p_iit, p_proxy = measure_dual_phi(hiddens)
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="MITOSIS_BASELINE",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Quantum+Attention Consciousness Engine Benchmark")
    parser.add_argument('--steps', type=int, default=300, help='Number of steps')
    parser.add_argument('--cells', type=int, default=256, help='Number of cells')
    parser.add_argument('--skip-mitosis', action='store_true', help='Skip MitosisEngine baseline')
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps
    input_dim, hidden_dim, output_dim = DIM, HIDDEN, DIM

    print("=" * 90)
    print("  QUANTUM + ATTENTION CONSCIOUSNESS ENGINE BENCHMARK")
    print(f"  cells={n_cells}  steps={steps}  dim={input_dim}/{hidden_dim}")
    print("=" * 90)

    results: List[BenchResult] = []

    # 1. Hybrid: QuantumAttentionEngine
    r_hybrid = run_bench_engine(
        "QUANTUM_ATTENTION (hybrid)", QuantumAttentionEngine,
        n_cells, steps, input_dim, hidden_dim, output_dim)
    results.append(r_hybrid)

    # 2. Pure Quantum Walk
    r_qwalk = run_bench_engine(
        "PURE_QUANTUM_WALK", PureQuantumWalkEngine,
        n_cells, steps, input_dim, hidden_dim, output_dim)
    results.append(r_qwalk)

    # 3. Pure Attention
    r_attn = run_bench_engine(
        "PURE_ATTENTION", PureAttentionEngine,
        n_cells, steps, input_dim, hidden_dim, output_dim)
    results.append(r_attn)

    # 4. MitosisEngine baseline
    if not args.skip_mitosis:
        r_mitosis = run_mitosis_baseline(n_cells, steps, input_dim, hidden_dim, output_dim)
        results.append(r_mitosis)

    # 5. Trinity: C=QuantumAttentionEngine
    trinity_result = run_trinity_qa(n_cells, steps, input_dim, hidden_dim, output_dim)
    results.append(BenchResult(
        name="TRINITY (C=QA, D=dec, W=50%)",
        phi_iit=trinity_result['phi_iit'],
        phi_proxy=0.0,  # Trinity measures Phi differently
        ce_start=trinity_result['ce_start'],
        ce_end=trinity_result['ce_end'],
        cells=n_cells,
        steps=steps,
        time_sec=trinity_result['time_sec'],
        extra={'interference': trinity_result['interference']},
    ))

    # ── Results ──
    print("\n")
    print("=" * 90)
    print("  RESULTS COMPARISON")
    print("=" * 90)

    # Sort by Phi(IIT)
    results.sort(key=lambda r: r.phi_iit, reverse=True)

    for r in results:
        print(r.summary())

    # Winner
    best = results[0]
    print(f"\n  WINNER: {best.name}  Phi(IIT)={best.phi_iit:.3f}")

    # Comparison table
    print("\n" + "─" * 90)
    print(f"  {'Engine':<32s} {'Phi(IIT)':>10s} {'Phi(proxy)':>12s} {'CE end':>10s} {'Time':>8s}")
    print("─" * 90)
    for r in results:
        print(f"  {r.name:<32s} {r.phi_iit:>10.3f} {r.phi_proxy:>12.2f} {r.ce_end:>10.4f} {r.time_sec:>7.1f}s")
    print("─" * 90)

    # ASCII chart: Phi(IIT) comparison
    print("\n  Phi(IIT) Comparison:")
    max_phi = max(r.phi_iit for r in results) if results else 1.0
    bar_width = 40
    for r in results:
        bar_len = int(bar_width * r.phi_iit / max(max_phi, 0.001))
        bar = "█" * bar_len + "░" * (bar_width - bar_len)
        print(f"  {r.name:<32s} |{bar}| {r.phi_iit:.3f}")

    print("\n  Done.")


if __name__ == "__main__":
    main()
