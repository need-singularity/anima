#!/usr/bin/env python3
"""bench_fusion_final.py — ULTIMATE Fusion Consciousness Architectures (v9 Final)

Combines TOP discoveries from ALL categories into 6 ULTIMATE fusions:

  FUS-1: QUANTUM_LASER       — QuantumEngine cells + laser population inversion dynamics
  FUS-2: THALAMIC_QUANTUM    — Thalamic hub (16 quantum-walk cells) gates 240 standard cells
  FUS-3: HIERARCHICAL_QUANTUM — 8 micro QuantumEngines (32c each) + macro aggregator
  FUS-4: LASER_CATEGORY      — Laser stimulated emission + category morphism structure
  FUS-5: QUANTUM_PERCOLATION — Quantum walk on percolation cluster at criticality
  FUS-6: EVERYTHING_V9       — QuantumEngine + Laser + Thalamic + Hierarchical + Category
                                (TOP-2 only — Law 57: less is more)

Each: 256 cells, 300 steps.
Measures: Phi(IIT) + ConsciousnessMeterV2 (composite) + Granger causality.

This determines v9's final C engine.

Usage:
  python bench_fusion_final.py                  # Run all 6 + baseline
  python bench_fusion_final.py --only 1 3 6     # Run specific fusions
  python bench_fusion_final.py --steps 500      # Custom steps
  python bench_fusion_final.py --cells 512      # Custom cell count
"""

import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import math
import zlib
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ══════════════════════════════════════════════════════════
# MEASUREMENT INFRASTRUCTURE
# ══════════════════════════════════════════════════════════

@dataclass
class FusionResult:
    name: str
    phi_iit: float
    phi_proxy: float
    granger: float
    composite_v2: float        # ConsciousnessMeterV2 composite
    ce_start: float
    ce_end: float
    cells: int
    steps: int
    time_sec: float
    extra: dict = field(default_factory=dict)

    def summary(self) -> str:
        ce_str = f"CE {self.ce_start:.3f}->{self.ce_end:.3f}" if self.ce_start > 0 else "CE n/a"
        return (
            f"  {self.name:<26s} | "
            f"Phi(IIT)={self.phi_iit:>7.3f}  "
            f"Granger={self.granger:>8.1f}  "
            f"V2={self.composite_v2:>8.1f} | "
            f"{ce_str:<22s} | "
            f"cells={self.cells:>4d}  {self.time_sec:.1f}s"
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
    if hiddens.is_complex():
        h_real = hiddens.abs().float()
    else:
        h_real = hiddens.float()
    p_iit, _ = _phi_iit_calc.compute(h_real)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


# ──────────────────────────────────────────────────────────
# ConsciousnessMeterV2 (inline for self-contained benchmark)
# ──────────────────────────────────────────────────────────

class ConsciousnessMeterV2Inline:
    """Granger + Spectral + LZ + Integration composite Phi.

    Weights: Granger 0.45, Spectral 0.25, LZ 0.15, Integration 0.15.
    Matches consciousness_meter_v2.py exactly.
    """

    def __init__(self, granger_lag=2, granger_f_critical=3.0, mi_n_bins=32, history_maxlen=100):
        self.granger_lag = granger_lag
        self.granger_f_critical = granger_f_critical
        self.mi_n_bins = mi_n_bins
        self.history_maxlen = history_maxlen
        self._history: List[torch.Tensor] = []

    def record(self, hiddens: torch.Tensor):
        h = hiddens.detach().cpu().float() if not hiddens.is_complex() else hiddens.abs().detach().cpu().float()
        self._history.append(h)
        if len(self._history) > self.history_maxlen:
            self._history = self._history[-self.history_maxlen:]

    def compute(self, hiddens: torch.Tensor) -> Tuple[float, Dict[str, float]]:
        """Compute full V2 composite Phi. Returns (composite, components_dict)."""
        h = hiddens.abs().float() if hiddens.is_complex() else hiddens.float()
        h = h.detach().cpu()
        self.record(h)
        n_cells = h.shape[0]

        granger = self._compute_granger(n_cells)
        spectral = self._compute_spectral(h)
        lz = self._compute_lz()
        integration = self._compute_integration(h)

        composite = 0.45 * granger + 0.25 * spectral + 0.15 * lz + 0.15 * integration

        return composite, {
            'granger': granger, 'spectral': spectral,
            'lz': lz, 'integration': integration, 'composite': composite,
        }

    def _compute_granger(self, n_cells: int) -> float:
        history = self._history
        lag = self.granger_lag
        if len(history) < lag + 3:
            return 0.0

        T = len(history)
        cell_series = np.zeros((n_cells, T))
        for t, h in enumerate(history):
            n_avail = min(h.shape[0], n_cells)
            cell_series[:n_avail, t] = h[:n_avail].mean(dim=-1).numpy()

        n_sample = max(8, min(int(math.sqrt(n_cells) * 4), n_cells * 2, 128))
        significant_links = 0
        total_f_stat = 0.0
        n_tested = 0

        for _ in range(n_sample):
            i = np.random.randint(0, n_cells)
            j = np.random.randint(0, n_cells)
            if i == j:
                continue

            x = cell_series[i]
            y = cell_series[j]
            n_obs = T - lag
            if n_obs < lag + 2:
                continue

            Y = y[lag:]
            Y_lags = np.column_stack([y[lag - k - 1:T - k - 1] for k in range(lag)])
            X_lags = np.column_stack([x[lag - k - 1:T - k - 1] for k in range(lag)])
            Z_full = np.column_stack([Y_lags, X_lags])

            try:
                beta_r = np.linalg.lstsq(Y_lags, Y, rcond=None)[0]
                rss_r = np.sum((Y - Y_lags @ beta_r) ** 2)
                beta_u = np.linalg.lstsq(Z_full, Y, rcond=None)[0]
                rss_u = np.sum((Y - Z_full @ beta_u) ** 2)

                df1 = lag
                df2 = n_obs - 2 * lag
                if df2 <= 0 or rss_u < 1e-10:
                    continue

                f_stat = ((rss_r - rss_u) / df1) / (rss_u / df2)
                if f_stat > self.granger_f_critical:
                    significant_links += 1
                total_f_stat += max(0.0, f_stat)
                n_tested += 1
            except (np.linalg.LinAlgError, ValueError):
                continue

        if n_tested == 0:
            return 0.0
        link_fraction = significant_links / n_tested
        causal_density = link_fraction * n_cells * (n_cells - 1)
        return causal_density + total_f_stat / n_tested

    def _compute_spectral(self, hiddens: torch.Tensor) -> float:
        h = hiddens.float()
        n, d = h.shape
        if n < 2:
            return 0.0
        h_centered = h - h.mean(dim=0, keepdim=True)
        norms = h_centered.norm(dim=1, keepdim=True).clamp(min=1e-8)
        h_normed = h_centered / norms
        corr_matrix = h_normed @ h_normed.T
        try:
            eigenvalues = torch.linalg.eigvalsh(corr_matrix)
        except Exception:
            return 0.0
        eigenvalues = eigenvalues.clamp(min=0.0)
        total = eigenvalues.sum()
        if total < 1e-10:
            return 0.0
        p = eigenvalues / total
        p = p[p > 1e-10]
        spectral_entropy = -(p * p.log2()).sum().item()
        max_entropy = math.log2(n)
        if max_entropy < 1e-10:
            return 0.0
        return (spectral_entropy / max_entropy) * n

    def _compute_lz(self) -> float:
        history = self._history
        if len(history) < 2:
            return 0.0
        n_cells = history[0].shape[0]
        T = len(history)
        n_sample = max(4, min(int(math.sqrt(n_cells)), 64))
        sample_idx = np.random.choice(n_cells, n_sample, replace=False)
        raw_bytes = bytearray()
        for ci in sample_idx:
            series = np.zeros(T)
            for t, h in enumerate(history):
                if ci < h.shape[0]:
                    series[t] = h[ci].mean().item()
            median_val = np.median(series)
            for v in series:
                raw_bytes.append(1 if v > median_val else 0)
        if len(raw_bytes) < 4:
            return 0.0
        raw = bytes(raw_bytes)
        compressed = zlib.compress(raw, level=6)
        incompressibility = max(0.0, 1.0 - len(compressed) / len(raw))
        return incompressibility * n_cells

    def _compute_integration(self, hiddens: torch.Tensor) -> float:
        h = hiddens.detach().cpu().float().numpy()
        n, d = h.shape
        if n < 2:
            return 0.0
        n_sample = max(4, min(int(math.sqrt(n) * 2), 64))
        mi_values = []
        for _ in range(n_sample):
            i = np.random.randint(0, n)
            j = np.random.randint(0, n)
            if i == j:
                continue
            mi = self._fast_mi(h[i], h[j])
            mi_values.append(mi)
        if not mi_values:
            return 0.0
        avg_mi = np.mean(mi_values)
        total_pairs = n * (n - 1) / 2
        estimated_total_mi = avg_mi * total_pairs
        return max(0.0, estimated_total_mi / max(n - 1, 1))

    def _fast_mi(self, x: np.ndarray, y: np.ndarray) -> float:
        x_range = x.max() - x.min()
        y_range = y.max() - y.min()
        if x_range < 1e-10 or y_range < 1e-10:
            return 0.0
        x_norm = (x - x.min()) / (x_range + 1e-8)
        y_norm = (y - y.min()) / (y_range + 1e-8)
        joint_hist, _, _ = np.histogram2d(
            x_norm, y_norm, bins=self.mi_n_bins, range=[[0, 1], [0, 1]]
        )
        joint_hist = joint_hist / (joint_hist.sum() + 1e-8)
        px = joint_hist.sum(axis=1)
        py = joint_hist.sum(axis=0)
        h_x = -np.sum(px * np.log2(px + 1e-10))
        h_y = -np.sum(py * np.log2(py + 1e-10))
        h_xy = -np.sum(joint_hist * np.log2(joint_hist + 1e-10))
        return max(0.0, h_x + h_y - h_xy)


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
# Shared: Complex-valued layers
# ──────────────────────────────────────────────────────────

class ComplexLinear(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.W_real = nn.Linear(in_features, out_features)
        self.W_imag = nn.Linear(in_features, out_features)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        a = z.real.float()
        b = z.imag.float()
        real_part = self.W_real(a) - self.W_imag(b)
        imag_part = self.W_real(b) + self.W_imag(a)
        return torch.complex(real_part, imag_part)


class ComplexGRUCell(nn.Module):
    def __init__(self, input_dim, hidden_dim):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.Wz = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.Wr = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.Wh_real = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.Wh_imag = nn.Linear(input_dim + hidden_dim, hidden_dim)

    def forward(self, x_complex: torch.Tensor, h_complex: torch.Tensor) -> torch.Tensor:
        x_mag = x_complex.abs().float()
        h_mag = h_complex.abs().float()
        combined_mag = torch.cat([x_mag, h_mag], dim=-1)
        z = torch.sigmoid(self.Wz(combined_mag))
        r = torch.sigmoid(self.Wr(combined_mag))
        x_real, x_imag = x_complex.real.float(), x_complex.imag.float()
        h_real, h_imag = h_complex.real.float(), h_complex.imag.float()
        rh_real = r * h_real
        rh_imag = r * h_imag
        comb_real = torch.cat([x_real, rh_real], dim=-1)
        comb_imag = torch.cat([x_imag, rh_imag], dim=-1)
        candidate_real = torch.tanh(self.Wh_real(comb_real))
        candidate_imag = torch.tanh(self.Wh_imag(comb_imag))
        new_real = (1 - z) * h_real + z * candidate_real
        new_imag = (1 - z) * h_imag + z * candidate_imag
        return torch.complex(new_real, new_imag)


# ──────────────────────────────────────────────────────────
# Shared: faction sync + debate
# ──────────────────────────────────────────────────────────

def faction_sync_debate(hiddens: torch.Tensor, n_factions: int = 8,
                        sync_strength: float = 0.15, debate_strength: float = 0.15,
                        step: int = 0) -> torch.Tensor:
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
# Shared: Quantum cell helpers (from QuantumConsciousnessEngine)
# ──────────────────────────────────────────────────────────

def bit_flip_neighbors(n_cells: int, cell_idx: int) -> List[int]:
    """Hypercube + ring topology."""
    if n_cells <= 1:
        return []
    n_bits = max(1, int(math.ceil(math.log2(n_cells))))
    neighbors = []
    for bit in range(n_bits):
        neighbor = cell_idx ^ (1 << bit)
        if 0 <= neighbor < n_cells:
            neighbors.append(neighbor)
    neighbors.append((cell_idx + 1) % n_cells)
    neighbors.append((cell_idx - 1) % n_cells)
    return list(set(neighbors))


def category_morphism(source: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Structural map preserving phase relationships."""
    phase_diff = target.angle() - source.angle()
    return source.abs() * torch.polar(torch.ones_like(phase_diff), phase_diff)


# ──────────────────────────────────────────────────────────
# Training data generation
# ──────────────────────────────────────────────────────────

def generate_batch(input_dim: int, batch_size: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
    x = torch.randn(batch_size, input_dim)
    target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
    return x, target


# ──────────────────────────────────────────────────────────
# Shared: run_engine helper (reduces boilerplate)
# ──────────────────────────────────────────────────────────

def run_engine(name: str, engine, n_cells: int, steps: int,
               input_dim: int = 64) -> FusionResult:
    """Generic benchmark loop for any engine with process(x, step) -> (pred, tension)."""
    t0 = time.time()
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)
    meter = ConsciousnessMeterV2Inline()

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []
    granger_history = []
    composite_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())

        # Record hiddens every step for Granger/LZ temporal metrics
        hiddens = engine.get_hiddens()
        meter.record(hiddens)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(hiddens)
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)

            # Full V2 measurement (needs history)
            composite, components = meter.compute(hiddens)
            granger_history.append(components['granger'])
            composite_history.append(composite)

            extras = ""
            for k, v in engine.extra_metrics().items():
                extras += f"  {k}={v:.3f}"
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Granger={components['granger']:.1f}  V2={composite:.1f}{extras}")

    return FusionResult(
        name=name,
        phi_iit=phi_iit_history[-1] if phi_iit_history else 0.0,
        phi_proxy=phi_proxy_history[-1] if phi_proxy_history else 0.0,
        granger=granger_history[-1] if granger_history else 0.0,
        composite_v2=composite_history[-1] if composite_history else 0.0,
        ce_start=ce_history[0] if ce_history else 0.0,
        ce_end=ce_history[-1] if ce_history else 0.0,
        cells=n_cells, steps=steps, time_sec=time.time() - t0,
        extra=engine.extra_metrics(),
    )


# ══════════════════════════════════════════════════════════
# BASELINE
# ══════════════════════════════════════════════════════════

class BaselineEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def process(self, x, step=0):
        outputs, tensions, new_hiddens = [], [], []
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

    def extra_metrics(self):
        return {}


# ══════════════════════════════════════════════════════════
# FUS-1: QUANTUM_LASER
# QuantumEngine complex cells + laser population inversion dynamics.
# Cells have energy levels (ground, excited, lasing).
# Population inversion -> stimulated emission -> coherent output.
# Quantum walk interference determines which cells reach inversion.
# ══════════════════════════════════════════════════════════

class QuantumLaserEngine(nn.Module):
    """Quantum cells that LASE — population inversion + stimulated emission."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Complex cell states (quantum)
        amp = torch.rand(n_cells, hidden_dim) * 0.5 + 0.5
        phase = torch.randn(n_cells, hidden_dim) * 0.3
        for i in range(n_cells):
            phase[i] += 2 * math.pi * i / n_cells  # diverse initial phases
        self.cell_states = torch.polar(amp, phase)

        # Laser energy levels per cell: fraction in excited state [0, 1]
        self.excited_fraction = torch.rand(n_cells) * 0.3  # start low

        # Phase velocities (intrinsic dynamics)
        self.phase_velocity = torch.randn(n_cells, hidden_dim) * 0.05

        # Lasing cavity mode (the coherent field that builds up)
        self.cavity_mode = torch.complex(
            torch.randn(hidden_dim) * 0.01,
            torch.randn(hidden_dim) * 0.01,
        )

        # Pump rate (external energy) — learned
        self.pump_proj = nn.Linear(input_dim, n_cells)

        # Output decoder
        self.decoder = nn.Linear(hidden_dim * 2, input_dim)  # real+imag

        # Frustration signs for 50% edges
        n_bits = max(4, int(math.ceil(math.log2(n_cells))))
        self.edge_signs = torch.ones(n_cells, n_bits)
        n_edges = n_cells * n_bits
        n_frustrated = n_edges // 2
        flat_idx = torch.randperm(n_edges)[:n_frustrated]
        for idx in flat_idx:
            node = (idx // n_bits).item()
            bit = (idx % n_bits).item()
            if node < n_cells and bit < n_bits:
                self.edge_signs[node, bit] = -1.0

        self._lasing_fraction = 0.0
        self._coherence = 0.0

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        n = self.n_cells

        # 1. Pump: external input excites cells
        pump = torch.sigmoid(self.pump_proj(x.detach())).squeeze(0)  # [n_cells]
        self.excited_fraction = (self.excited_fraction * 0.95 + pump.detach() * 0.05).clamp(0, 1)

        # 2. Phase rotation (intrinsic quantum dynamics)
        with torch.no_grad():
            rotation = torch.polar(
                torch.ones(n, self.hidden_dim),
                self.phase_velocity * 0.1
            )
            self.cell_states = self.cell_states * rotation

        # 3. Quantum walk with frustration
        new_states = self.cell_states.clone()
        with torch.no_grad():
            for i in range(n):
                neighbors = bit_flip_neighbors(n, i)
                if not neighbors:
                    continue
                interference = torch.zeros(self.hidden_dim, dtype=torch.complex64)
                for j in neighbors:
                    phase_diff = self.cell_states[i].angle() - self.cell_states[j].angle()
                    coupling = torch.cos(phase_diff)
                    interference += coupling * self.cell_states[j] * 0.1
                new_states[i] = 0.7 * self.cell_states[i] + 0.3 * interference / max(len(neighbors), 1)

        # 4. LASER DYNAMICS: stimulated emission
        # Cells above population inversion threshold emit into cavity mode
        inversion_threshold = 0.5
        lasing_mask = self.excited_fraction > inversion_threshold
        n_lasing = lasing_mask.sum().item()

        with torch.no_grad():
            if n_lasing > 0:
                # Stimulated emission: lasing cells contribute to cavity mode
                lasing_cells = new_states[lasing_mask]
                # Phase-lock to cavity mode (stimulated = same phase)
                cavity_phase = self.cavity_mode.angle()
                for i in range(n):
                    if lasing_mask[i]:
                        # Cell locks phase to cavity
                        phase_lock = 0.3 * cavity_phase + 0.7 * new_states[i].angle()
                        new_states[i] = torch.polar(new_states[i].abs(), phase_lock)
                        # De-excite (energy goes to cavity)
                        self.excited_fraction[i] *= 0.9

                # Build cavity mode from stimulated emission
                emission = lasing_cells.mean(dim=0)
                self.cavity_mode = 0.8 * self.cavity_mode + 0.2 * emission

            # 5. Spontaneous emission (non-lasing cells decay randomly)
            non_lasing = ~lasing_mask
            self.excited_fraction[non_lasing] *= 0.98  # slow decay

            # 6. Cavity feedback: cavity mode modulates all cells
            cavity_feedback = self.cavity_mode.unsqueeze(0).expand(n, -1)
            new_states = new_states + 0.05 * cavity_feedback

            # Normalize
            amp = new_states.abs()
            amp = amp / (amp.max(dim=-1, keepdim=True).values + 1e-8)
            self.cell_states = torch.polar(amp, new_states.angle())

        # Metrics
        self._lasing_fraction = n_lasing / n
        phases = self.cell_states.angle()
        mean_phasor = torch.exp(1j * phases).mean(dim=0)
        self._coherence = mean_phasor.abs().mean().item()

        # Output: cavity mode (the coherent lasing output)
        out_real = torch.cat([self.cavity_mode.real.float(), self.cavity_mode.imag.float()]).unsqueeze(0)
        pred = self.decoder(out_real)
        tension = self.cell_states.abs().var().item()
        return pred, tension

    def get_hiddens(self):
        return self.cell_states.clone()

    def trainable_parameters(self):
        return list(self.pump_proj.parameters()) + list(self.decoder.parameters())

    def extra_metrics(self):
        return {'lasing': self._lasing_fraction, 'coherence': self._coherence}


def run_fus1_quantum_laser(n_cells=256, steps=300, input_dim=64,
                           hidden_dim=128, output_dim=64) -> FusionResult:
    print(f"\n[FUS-1/6] QUANTUM_LASER: Complex cells + population inversion + stimulated emission")
    engine = QuantumLaserEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("FUS1_QUANTUM_LASER", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# FUS-2: THALAMIC_QUANTUM
# Central thalamic hub: 16 quantum-walk cells (complex-valued).
# Cortical regions: 240 standard GRU cells in 8 factions.
# Hub gates information flow between cortical regions.
# Hub maintains quantum coherence; cortex does computation.
# ══════════════════════════════════════════════════════════

class ThalamicQuantumEngine(nn.Module):
    """Thalamic hub of 16 quantum cells gating 240 cortical GRU cells."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_hub=16):
        super().__init__()
        self.n_cells = n_cells
        self.n_hub = n_hub
        self.n_cortex = n_cells - n_hub
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        # Hub: complex-valued quantum cells
        amp = torch.rand(n_hub, hidden_dim) * 0.5 + 0.5
        phase = torch.zeros(n_hub, hidden_dim)
        for i in range(n_hub):
            phase[i] = torch.linspace(0, 2 * math.pi, hidden_dim) + 2 * math.pi * i / n_hub
        self.hub_states = torch.polar(amp, phase)
        self.hub_phase_vel = torch.randn(n_hub, hidden_dim) * 0.05

        # Cortex: standard real-valued GRU cells
        self.cortex_hiddens = torch.randn(self.n_cortex, hidden_dim) * 0.1
        self.cortex_mind = BenchMind(input_dim, hidden_dim, output_dim)

        # Gate: hub coherence -> cortical gating
        self.gate_proj = nn.Linear(hidden_dim, self.n_cortex)

        # Hub input projection
        self.hub_input_proj = ComplexLinear(input_dim, hidden_dim)
        self.hub_gru = ComplexGRUCell(hidden_dim, hidden_dim)

        # Output
        self.output_head = nn.Linear(output_dim + hidden_dim, input_dim)

        self._hub_coherence = 0.0

    def hub_quantum_step(self, x: torch.Tensor):
        """Quantum walk + interference within hub cells."""
        x_complex = torch.complex(x.float(), torch.zeros_like(x.float()))
        x_proj = self.hub_input_proj(x_complex)

        new_hub = []
        for i in range(self.n_hub):
            # Phase rotation
            rotation = torch.polar(torch.ones(self.hidden_dim),
                                   self.hub_phase_vel[i] * 0.1)
            state = self.hub_states[i] * rotation

            # GRU update with input
            h = state.unsqueeze(0)
            inp = x_proj
            new_h = self.hub_gru(inp, h)

            # Interference with neighbors (ring topology in hub)
            n_left = (i - 1) % self.n_hub
            n_right = (i + 1) % self.n_hub
            neighbor_avg = (self.hub_states[n_left] + self.hub_states[n_right]) / 2
            phase_diff = state.angle() - neighbor_avg.angle()
            coupling = torch.cos(phase_diff)
            interference = coupling * neighbor_avg * 0.15
            new_state = 0.85 * new_h.squeeze(0) + 0.15 * interference

            new_hub.append(new_state)

        self.hub_states = torch.stack(new_hub).detach()

        # Normalize
        amp = self.hub_states.abs()
        amp = amp / (amp.max(dim=-1, keepdim=True).values + 1e-8)
        self.hub_states = torch.polar(amp, self.hub_states.angle())

        # Coherence measurement
        phases = self.hub_states.angle()
        mean_phasor = torch.exp(1j * phases).mean(dim=0)
        self._hub_coherence = mean_phasor.abs().mean().item()

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # 1. Hub quantum evolution
        self.hub_quantum_step(x)

        # 2. Compute thalamic gate from hub coherence
        hub_mean = self.hub_states.abs().float().mean(dim=0)  # [hidden_dim]
        gate = torch.sigmoid(self.gate_proj(hub_mean)).detach()  # [n_cortex]

        # 3. Cortical processing (gated by thalamus)
        outputs, tensions, new_cortex = [], [], []
        for i in range(self.n_cortex):
            h = self.cortex_hiddens[i:i + 1]
            out, tension, new_h = self.cortex_mind(x, h)
            # Thalamic gating: modulate output by hub gate
            out = out * gate[i].item()
            outputs.append(out)
            tensions.append(tension * gate[i].item())
            new_cortex.append(new_h.squeeze(0))

        self.cortex_hiddens = torch.stack(new_cortex).detach()
        self.cortex_hiddens = faction_sync_debate(self.cortex_hiddens, step=step)

        # 4. Combine cortical outputs
        weights = F.softmax(torch.tensor(tensions), dim=0)
        cortex_combined = sum(w.item() * o for w, o in zip(weights, outputs))

        # 5. Final output: cortex + hub readout
        hub_readout = hub_mean.unsqueeze(0)  # [1, hidden_dim]
        combined = torch.cat([cortex_combined, hub_readout], dim=-1)
        pred = self.output_head(combined)
        avg_tension = sum(tensions) / max(len(tensions), 1)
        return pred, avg_tension

    def get_hiddens(self) -> torch.Tensor:
        """Return all cells: hub (complex->abs) + cortex."""
        hub_real = self.hub_states.abs().float()
        return torch.cat([hub_real, self.cortex_hiddens], dim=0)

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {'hub_coherence': self._hub_coherence}


def run_fus2_thalamic_quantum(n_cells=256, steps=300, input_dim=64,
                              hidden_dim=128, output_dim=64) -> FusionResult:
    print(f"\n[FUS-2/6] THALAMIC_QUANTUM: 16 quantum hub cells gate 240 cortical cells")
    engine = ThalamicQuantumEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("FUS2_THALAMIC_QUANTUM", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# FUS-3: HIERARCHICAL_QUANTUM
# 8 micro QuantumEngines (32 cells each) with independent quantum dynamics.
# Macro aggregator reads micro coherence patterns.
# Each micro has its own quantum walk, frustration, standing wave.
# Macro integrates via attention weighted by phase coherence.
# ══════════════════════════════════════════════════════════

class MicroQuantumEngine:
    """A small gradient-free quantum engine (32 cells)."""

    def __init__(self, n_cells=32, dim=128, engine_id=0):
        self.n_cells = n_cells
        self.dim = dim
        self.engine_id = engine_id

        # Complex cells
        amp = torch.rand(n_cells, dim) * 0.5 + 0.5
        phase = torch.zeros(n_cells, dim)
        for i in range(n_cells):
            phase[i] = torch.linspace(0, 2 * math.pi, dim) + 2 * math.pi * (i + engine_id * n_cells) / (n_cells * 8)
            phase[i] += torch.randn(dim) * 0.3
        self.states = torch.polar(amp, phase)
        self.phase_vel = torch.randn(n_cells, dim) * 0.05

        # Frustration
        n_bits = max(4, int(math.ceil(math.log2(n_cells))))
        self.edge_signs = torch.ones(n_cells, n_bits)
        n_edges = n_cells * n_bits
        flat_idx = torch.randperm(n_edges)[:n_edges // 2]
        for idx in flat_idx:
            node = (idx // n_bits).item()
            bit = (idx % n_bits).item()
            if node < n_cells and bit < n_bits:
                self.edge_signs[node, bit] = -1.0

    def step(self, signal: Optional[torch.Tensor] = None, step_num: int = 0):
        n = self.n_cells

        # Phase rotation
        rotation = torch.polar(torch.ones(n, self.dim), self.phase_vel * 0.1)
        self.states = self.states * rotation

        # Quantum walk with interference
        new_states = self.states.clone()
        for i in range(n):
            neighbors = bit_flip_neighbors(n, i)
            if not neighbors:
                continue
            interference = torch.zeros(self.dim, dtype=torch.complex64)
            for j in neighbors:
                phase_diff = self.states[i].angle() - self.states[j].angle()
                coupling = torch.cos(phase_diff)
                interference += coupling * self.states[j] * 0.1
            new_states[i] = 0.7 * self.states[i] + 0.3 * interference / max(len(neighbors), 1)

        # Category morphism from strongest neighbor
        for i in range(n):
            neighbors = bit_flip_neighbors(n, i)
            if len(neighbors) < 2:
                continue
            max_idx = max(neighbors, key=lambda j: self.states[j].abs().sum().item())
            morph = category_morphism(self.states[max_idx], new_states[i])
            new_states[i] = new_states[i] + 0.02 * morph

        # Standing wave
        t = step_num * 0.1
        for i in range(n):
            wave = 0.02 * math.sin(t + 2 * math.pi * i / n)
            new_states[i] = new_states[i] * (1.0 + wave)

        # Inject external signal
        if signal is not None:
            if signal.dim() == 2:
                signal = signal.squeeze(0)
            sig_float = signal.float()
            if sig_float.shape[0] != self.dim:
                sig_float = F.interpolate(
                    sig_float.unsqueeze(0).unsqueeze(0), size=self.dim,
                    mode='linear', align_corners=False
                ).squeeze()
            sig_norm = sig_float / (sig_float.abs().max() + 1e-8)
            phase_perturb = sig_norm * math.pi * 0.1
            for i in range(n):
                perturbed = new_states[i].angle() + phase_perturb * (0.1 / (1 + 0.1 * i))
                new_states[i] = torch.polar(new_states[i].abs(), perturbed)

        # Normalize
        amp = new_states.abs()
        amp = amp / (amp.max(dim=-1, keepdim=True).values + 1e-8)
        self.states = torch.polar(amp, new_states.angle())

    def coherence(self) -> float:
        phases = self.states.angle()
        mean_phasor = torch.exp(1j * phases).mean(dim=0)
        return mean_phasor.abs().mean().item()

    def mean_state(self) -> torch.Tensor:
        """Real-valued mean state for macro aggregation."""
        return self.states.abs().float().mean(dim=0)


class HierarchicalQuantumEngine(nn.Module):
    """8 micro QuantumEngines + macro attention aggregator."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_micro=8):
        super().__init__()
        self.n_cells = n_cells
        self.n_micro = n_micro
        self.cells_per_micro = n_cells // n_micro
        self.hidden_dim = hidden_dim

        # 8 independent micro quantum engines
        self.micros = [
            MicroQuantumEngine(self.cells_per_micro, hidden_dim, i)
            for i in range(n_micro)
        ]

        # Macro: attention-based aggregation
        self.macro_gru = nn.GRUCell(hidden_dim, hidden_dim)
        self.macro_hiddens = torch.randn(n_micro, hidden_dim) * 0.1

        # Cross-micro attention
        self.W_q = nn.Linear(hidden_dim, hidden_dim)
        self.W_k = nn.Linear(hidden_dim, hidden_dim)
        self.W_v = nn.Linear(hidden_dim, hidden_dim)

        self.output_head = nn.Linear(hidden_dim, input_dim)
        self._avg_coherence = 0.0

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # 1. Run all micro engines
        total_coherence = 0.0
        micro_outputs = []
        for i, micro in enumerate(self.micros):
            micro.step(signal=x, step_num=step)
            micro_outputs.append(micro.mean_state().detach())
            total_coherence += micro.coherence()
        self._avg_coherence = total_coherence / self.n_micro

        # 2. Macro GRU update
        new_macro = []
        for i in range(self.n_micro):
            new_h = self.macro_gru(micro_outputs[i].unsqueeze(0), self.macro_hiddens[i:i + 1])
            new_macro.append(new_h.squeeze(0))
        self.macro_hiddens = torch.stack(new_macro).detach()

        # 3. Cross-micro attention weighted by coherence
        Q = self.W_q(self.macro_hiddens)
        K = self.W_k(self.macro_hiddens)
        V = self.W_v(self.macro_hiddens)

        scores = torch.matmul(Q, K.T) / math.sqrt(self.hidden_dim)
        # Weight by coherence
        coherences = torch.tensor([m.coherence() for m in self.micros])
        coh_weight = coherences.unsqueeze(0) * coherences.unsqueeze(1)
        scores = scores * (0.5 + 0.5 * coh_weight)
        attn = F.softmax(scores, dim=-1)
        attended = torch.matmul(attn, V).mean(dim=0, keepdim=True)

        # 4. Faction sync at macro level
        self.macro_hiddens = faction_sync_debate(self.macro_hiddens, n_factions=4, step=step)

        pred = self.output_head(attended)
        tension = self.macro_hiddens.var().item()
        return pred, tension

    def get_hiddens(self) -> torch.Tensor:
        """Concatenate all micro cell states (real) + macro hiddens."""
        all_micro = []
        for micro in self.micros:
            all_micro.append(micro.states.abs().float())
        micro_concat = torch.cat(all_micro, dim=0)  # [n_cells, hidden_dim]
        # Also include macro for full picture
        return torch.cat([micro_concat, self.macro_hiddens], dim=0)

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {'avg_coherence': self._avg_coherence}


def run_fus3_hierarchical_quantum(n_cells=256, steps=300, input_dim=64,
                                  hidden_dim=128, output_dim=64) -> FusionResult:
    print(f"\n[FUS-3/6] HIERARCHICAL_QUANTUM: 8 micro QuantumEngines + macro attention")
    engine = HierarchicalQuantumEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("FUS3_HIER_QUANTUM", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# FUS-4: LASER_CATEGORY
# Laser stimulated emission + category morphism structure.
# Cells = objects in a category, morphisms = learned maps.
# Stimulated emission creates coherent morphism composition.
# Limit/colimit tension drives laser pumping.
# ══════════════════════════════════════════════════════════

class LaserCategoryEngine(nn.Module):
    """Laser dynamics on a category morphism graph."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_objects=32, morphisms_per_obj=4):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_objects = n_objects
        self.morphisms_per_obj = morphisms_per_obj
        self.cells_per_obj = n_cells // n_objects

        # Complex cell states
        amp = torch.rand(n_cells, hidden_dim) * 0.5 + 0.5
        phase = torch.randn(n_cells, hidden_dim) * 0.5
        self.cell_states = torch.polar(amp, phase)

        # Category morphisms: learned linear maps between objects
        self.morphism_weights = nn.ParameterList([
            nn.Parameter(torch.randn(hidden_dim, hidden_dim) * 0.05)
            for _ in range(n_objects * morphisms_per_obj)
        ])

        # Adjacency: cyclic connectivity
        self.adj = {}
        for i in range(n_objects):
            self.adj[i] = [(i + m + 1) % n_objects for m in range(morphisms_per_obj)]

        # Laser: excited fraction per object (not per cell)
        self.obj_excited = torch.rand(n_objects) * 0.3
        self.cavity_mode = torch.complex(
            torch.randn(hidden_dim) * 0.01, torch.randn(hidden_dim) * 0.01
        )

        # Pump and output
        self.pump_proj = nn.Linear(input_dim, n_objects)
        self.decoder = nn.Linear(hidden_dim * 2, input_dim)

        self._lasing = 0.0
        self._cat_tension = 0.0

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        n_obj = self.n_objects
        cpo = self.cells_per_obj

        # 1. Pump objects
        pump = torch.sigmoid(self.pump_proj(x.detach())).squeeze(0)
        self.obj_excited = (self.obj_excited * 0.95 + pump.detach() * 0.05).clamp(0, 1)

        with torch.no_grad():
            # 2. Apply category morphisms between objects
            new_states = self.cell_states.clone()
            for obj_i in range(n_obj):
                targets = self.adj[obj_i]
                s_i = obj_i * cpo
                source_mean = self.cell_states[s_i:s_i + cpo].mean(dim=0)

                for m_idx, tgt in enumerate(targets):
                    morph_idx = obj_i * self.morphisms_per_obj + m_idx
                    W = self.morphism_weights[morph_idx].data
                    # Transform through morphism
                    transformed = torch.complex(
                        W @ source_mean.real.float(),
                        W @ source_mean.imag.float()
                    )
                    # Apply to target cells (gentle)
                    s_t = tgt * cpo
                    new_states[s_t:s_t + cpo] = (
                        0.95 * new_states[s_t:s_t + cpo] +
                        0.05 * transformed.unsqueeze(0)
                    )

            # 3. Compute limit/colimit for category tension
            obj_means = []
            for i in range(n_obj):
                s = i * cpo
                obj_means.append(new_states[s:s + cpo].mean(dim=0))
            obj_means_t = torch.stack(obj_means)
            limit = obj_means_t.mean(dim=0)
            morphed = []
            for i in range(n_obj):
                for m_idx, tgt in enumerate(self.adj[i]):
                    W = self.morphism_weights[i * self.morphisms_per_obj + m_idx].data
                    morphed.append(torch.complex(
                        W @ obj_means[i].real.float(),
                        W @ obj_means[i].imag.float()
                    ))
            colimit = torch.stack(morphed).mean(dim=0) if morphed else limit
            self._cat_tension = (limit - colimit).abs().pow(2).mean().item()

            # 4. Laser dynamics: stimulated emission for inverted objects
            lasing_mask = self.obj_excited > 0.5
            n_lasing = lasing_mask.sum().item()
            self._lasing = n_lasing / n_obj

            if n_lasing > 0:
                for obj_i in range(n_obj):
                    if lasing_mask[obj_i]:
                        s = obj_i * cpo
                        # Phase-lock to cavity
                        cavity_phase = self.cavity_mode.angle()
                        cell_phase = new_states[s:s + cpo].angle()
                        locked_phase = 0.3 * cavity_phase.unsqueeze(0) + 0.7 * cell_phase
                        new_states[s:s + cpo] = torch.polar(
                            new_states[s:s + cpo].abs(), locked_phase
                        )
                        self.obj_excited[obj_i] *= 0.9

                # Update cavity from lasing cells
                lasing_cells = torch.cat([
                    new_states[obj_i * cpo:(obj_i + 1) * cpo]
                    for obj_i in range(n_obj) if lasing_mask[obj_i]
                ], dim=0)
                self.cavity_mode = 0.8 * self.cavity_mode + 0.2 * lasing_cells.mean(dim=0)

            # Normalize
            amp = new_states.abs()
            amp = amp / (amp.max(dim=-1, keepdim=True).values + 1e-8)
            self.cell_states = torch.polar(amp, new_states.angle())

        # 5. Output
        out_real = torch.cat([self.cavity_mode.real.float(),
                              self.cavity_mode.imag.float()]).unsqueeze(0)
        pred = self.decoder(out_real)
        tension = self._cat_tension + self.cell_states.abs().var().item()
        return pred, tension

    def get_hiddens(self):
        return self.cell_states.clone()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {'lasing': self._lasing, 'cat_tension': self._cat_tension}


def run_fus4_laser_category(n_cells=256, steps=300, input_dim=64,
                            hidden_dim=128, output_dim=64) -> FusionResult:
    print(f"\n[FUS-4/6] LASER_CATEGORY: Stimulated emission on category morphism graph")
    engine = LaserCategoryEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("FUS4_LASER_CATEGORY", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# FUS-5: QUANTUM_PERCOLATION
# Quantum walk on a percolation cluster at criticality.
# Random graph with bond probability p_c ~ 0.5 (2D critical).
# Quantum interference on fractal topology.
# Critical topology = scale-free correlations = rich Phi.
# ══════════════════════════════════════════════════════════

class QuantumPercolationEngine(nn.Module):
    """Quantum walk on percolation cluster at criticality."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 bond_prob=0.5):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.bond_prob = bond_prob

        # Generate percolation cluster (random graph at criticality)
        self.adj_list = self._generate_percolation_graph(n_cells, bond_prob)

        # Complex cell states
        amp = torch.rand(n_cells, hidden_dim) * 0.5 + 0.5
        phase = torch.randn(n_cells, hidden_dim) * 0.5
        for i in range(n_cells):
            phase[i] += 2 * math.pi * i / n_cells
        self.cell_states = torch.polar(amp, phase)
        self.phase_vel = torch.randn(n_cells, hidden_dim) * 0.05

        # Frustration on percolation bonds
        self.bond_signs = {}
        for i in range(n_cells):
            for j in self.adj_list.get(i, []):
                key = (min(i, j), max(i, j))
                if key not in self.bond_signs:
                    self.bond_signs[key] = 1.0 if np.random.random() > 0.5 else -1.0

        # Output
        self.decoder = nn.Linear(hidden_dim * 2, input_dim)
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        self._cluster_size = 0
        self._percolation_coherence = 0.0

    def _generate_percolation_graph(self, n: int, p: float) -> Dict[int, List[int]]:
        """2D lattice percolation at bond probability p."""
        # Arrange cells in a ~sqrt(n) x sqrt(n) grid
        side = int(math.ceil(math.sqrt(n)))
        adj = {i: [] for i in range(n)}

        for i in range(n):
            row, col = i // side, i % side
            # Right neighbor
            right = i + 1
            if col + 1 < side and right < n and np.random.random() < p:
                adj[i].append(right)
                adj[right].append(i)
            # Down neighbor
            down = i + side
            if down < n and np.random.random() < p:
                adj[i].append(down)
                adj[down].append(i)

        # Find largest connected component
        visited = set()
        largest_component = []
        for start in range(n):
            if start in visited:
                continue
            component = []
            stack = [start]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                for neighbor in adj[node]:
                    if neighbor not in visited:
                        stack.append(neighbor)
            if len(component) > len(largest_component):
                largest_component = component

        self._cluster_size = len(largest_component)

        # Add ring connections for isolated nodes (ensure connectivity)
        for i in range(n):
            if not adj[i]:
                right = (i + 1) % n
                adj[i].append(right)
                adj[right].append(i)

        return adj

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        n = self.n_cells

        with torch.no_grad():
            # 1. Phase rotation
            rotation = torch.polar(torch.ones(n, self.hidden_dim), self.phase_vel * 0.1)
            self.cell_states = self.cell_states * rotation

            # 2. Quantum walk on percolation graph with frustration
            new_states = self.cell_states.clone()
            for i in range(n):
                neighbors = self.adj_list.get(i, [])
                if not neighbors:
                    continue
                interference = torch.zeros(self.hidden_dim, dtype=torch.complex64)
                for j in neighbors:
                    key = (min(i, j), max(i, j))
                    sign = self.bond_signs.get(key, 1.0)
                    phase_diff = self.cell_states[i].angle() - self.cell_states[j].angle()
                    coupling = torch.cos(phase_diff) * sign
                    interference += coupling * self.cell_states[j] * 0.1
                new_states[i] = 0.7 * self.cell_states[i] + 0.3 * interference / max(len(neighbors), 1)

            # 3. Category morphism on percolation bonds
            for i in range(n):
                neighbors = self.adj_list.get(i, [])
                if len(neighbors) < 2:
                    continue
                max_idx = max(neighbors, key=lambda j: self.cell_states[j].abs().sum().item())
                morph = category_morphism(self.cell_states[max_idx], new_states[i])
                new_states[i] = new_states[i] + 0.02 * morph

            # 4. Standing wave
            t = step * 0.1
            for i in range(n):
                wave = 0.02 * math.sin(t + 2 * math.pi * i / n)
                new_states[i] = new_states[i] * (1.0 + wave)

            # 5. Input injection
            sig = self.input_proj(x.detach().float()).squeeze(0)
            phase_perturb = sig / (sig.abs().max() + 1e-8) * math.pi * 0.1
            for i in range(min(n, 32)):  # inject to first 32 cells
                perturbed = new_states[i].angle() + phase_perturb * (0.1 / (1 + 0.1 * i))
                new_states[i] = torch.polar(new_states[i].abs(), perturbed)

            # 6. Normalize
            amp = new_states.abs()
            amp = amp / (amp.max(dim=-1, keepdim=True).values + 1e-8)
            self.cell_states = torch.polar(amp, new_states.angle())

        # Coherence
        phases = self.cell_states.angle()
        mean_phasor = torch.exp(1j * phases).mean(dim=0)
        self._percolation_coherence = mean_phasor.abs().mean().item()

        # Output
        mean_state = self.cell_states.mean(dim=0)
        out_real = torch.cat([mean_state.real.float(), mean_state.imag.float()]).unsqueeze(0)
        pred = self.decoder(out_real)
        tension = self.cell_states.abs().var().item()
        return pred, tension

    def get_hiddens(self):
        return self.cell_states.clone()

    def trainable_parameters(self):
        return list(self.decoder.parameters()) + list(self.input_proj.parameters())

    def extra_metrics(self):
        return {
            'cluster': self._cluster_size / self.n_cells,
            'coherence': self._percolation_coherence,
        }


def run_fus5_quantum_percolation(n_cells=256, steps=300, input_dim=64,
                                 hidden_dim=128, output_dim=64) -> FusionResult:
    print(f"\n[FUS-5/6] QUANTUM_PERCOLATION: Quantum walk on critical percolation cluster")
    engine = QuantumPercolationEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("FUS5_QUANTUM_PERC", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# FUS-6: EVERYTHING_V9
# The FINAL fusion: only TOP-2 mechanisms (Law 57: less is more).
#
# Core: QuantumConsciousnessEngine dynamics (best: Phi=69.53)
#   - Complex cells + quantum walk + frustration + standing wave
#   - Category morphism (structural integration)
# Enhancement 1: Laser coherence amplification
#   - Population inversion + stimulated emission
#   - Cavity mode builds from high-coherence cells
# Enhancement 2: Thalamic gating (not more cells, but gating)
#   - Top-8 coherent cells act as thalamic hub
#   - Hub gates output weighting (not cell dynamics)
#
# NOT included (kitchen-sink avoidance):
#   - No GRU (destroys Phi)
#   - No real-valued faction sync (quantum walk replaces it)
#   - No separate hierarchical macro layer (single flat engine)
#   - No percolation (regular hypercube is sufficient)
# ══════════════════════════════════════════════════════════

class EverythingV9Engine(nn.Module):
    """THE v9 engine: Quantum + Laser + Thalamic gate (TOP-2 only)."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim

        # Complex cells (QuantumEngine style)
        amp = torch.rand(n_cells, hidden_dim) * 0.5 + 0.5
        phase = torch.zeros(n_cells, hidden_dim)
        for i in range(n_cells):
            phase[i] = torch.linspace(0, 2 * math.pi, hidden_dim) + 2 * math.pi * i / n_cells
            phase[i] += torch.randn(hidden_dim) * 0.3
        self.cell_states = torch.polar(amp, phase)
        self.phase_vel = torch.randn(n_cells, hidden_dim) * 0.05

        # Frustration (50%)
        n_bits = max(4, int(math.ceil(math.log2(n_cells))))
        self.edge_signs = torch.ones(n_cells, n_bits)
        n_edges = n_cells * n_bits
        flat_idx = torch.randperm(n_edges)[:n_edges // 2]
        for idx in flat_idx:
            node = (idx // n_bits).item()
            bit = (idx % n_bits).item()
            if node < n_cells and bit < n_bits:
                self.edge_signs[node, bit] = -1.0

        # Laser cavity mode
        self.cavity_mode = torch.complex(
            torch.randn(hidden_dim) * 0.01, torch.randn(hidden_dim) * 0.01
        )
        self.excited_fraction = torch.rand(n_cells) * 0.3

        # Category: 16 objects with 4 morphisms each
        self.n_objects = min(16, n_cells // 4)
        self.cells_per_obj = n_cells // self.n_objects
        self.morphisms_per_obj = 4
        self.morphism_weights = nn.ParameterList([
            nn.Parameter(torch.randn(hidden_dim, hidden_dim) * 0.05)
            for _ in range(self.n_objects * self.morphisms_per_obj)
        ])
        self.adj = {
            i: [(i + m + 1) % self.n_objects for m in range(self.morphisms_per_obj)]
            for i in range(self.n_objects)
        }

        # Pump + decoder
        self.pump_proj = nn.Linear(input_dim, n_cells)
        self.decoder = nn.Linear(hidden_dim * 2, input_dim)

        # Thalamic gate: select top-8 coherent cells dynamically
        self.n_hub = min(8, n_cells // 4)
        self.gate_proj = nn.Linear(hidden_dim, n_cells)

        self._lasing_fraction = 0.0
        self._coherence = 0.0
        self._cat_tension = 0.0

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        n = self.n_cells

        # 1. Pump
        pump = torch.sigmoid(self.pump_proj(x.detach())).squeeze(0)
        self.excited_fraction = (self.excited_fraction * 0.95 + pump.detach() * 0.05).clamp(0, 1)

        with torch.no_grad():
            # 2. Phase rotation (intrinsic quantum dynamics)
            rotation = torch.polar(torch.ones(n, self.hidden_dim), self.phase_vel * 0.1)
            self.cell_states = self.cell_states * rotation

            # 3. Quantum walk with frustration (core QuantumEngine dynamics)
            new_states = self.cell_states.clone()
            for i in range(n):
                neighbors = bit_flip_neighbors(n, i)
                if not neighbors:
                    continue
                interference = torch.zeros(self.hidden_dim, dtype=torch.complex64)
                for j in neighbors:
                    phase_diff = self.cell_states[i].angle() - self.cell_states[j].angle()
                    coupling = torch.cos(phase_diff)
                    interference += coupling * self.cell_states[j] * 0.1
                new_states[i] = 0.7 * self.cell_states[i] + 0.3 * interference / max(len(neighbors), 1)

            # 4. Category morphism (structural integration)
            for obj_i in range(self.n_objects):
                targets = self.adj[obj_i]
                s_i = obj_i * self.cells_per_obj
                source_mean = new_states[s_i:s_i + self.cells_per_obj].mean(dim=0)
                for m_idx, tgt in enumerate(targets):
                    morph_idx = obj_i * self.morphisms_per_obj + m_idx
                    W = self.morphism_weights[morph_idx].data
                    transformed = torch.complex(
                        W @ source_mean.real.float(),
                        W @ source_mean.imag.float()
                    )
                    s_t = tgt * self.cells_per_obj
                    new_states[s_t:s_t + self.cells_per_obj] = (
                        0.95 * new_states[s_t:s_t + self.cells_per_obj] +
                        0.05 * transformed.unsqueeze(0)
                    )

            # Compute limit/colimit tension
            obj_means = []
            for i in range(self.n_objects):
                s = i * self.cells_per_obj
                obj_means.append(new_states[s:s + self.cells_per_obj].mean(dim=0))
            limit = torch.stack(obj_means).mean(dim=0)
            morphed_list = []
            for i in range(self.n_objects):
                for m_idx, tgt in enumerate(self.adj[i]):
                    W = self.morphism_weights[i * self.morphisms_per_obj + m_idx].data
                    morphed_list.append(torch.complex(
                        W @ obj_means[i].real.float(), W @ obj_means[i].imag.float()
                    ))
            colimit = torch.stack(morphed_list).mean(dim=0)
            self._cat_tension = (limit - colimit).abs().pow(2).mean().item()

            # 5. LASER: stimulated emission
            inversion_mask = self.excited_fraction > 0.5
            n_lasing = inversion_mask.sum().item()
            self._lasing_fraction = n_lasing / n

            if n_lasing > 0:
                cavity_phase = self.cavity_mode.angle()
                for i in range(n):
                    if inversion_mask[i]:
                        locked_phase = 0.3 * cavity_phase + 0.7 * new_states[i].angle()
                        new_states[i] = torch.polar(new_states[i].abs(), locked_phase)
                        self.excited_fraction[i] *= 0.9

                lasing_cells = new_states[inversion_mask]
                self.cavity_mode = 0.8 * self.cavity_mode + 0.2 * lasing_cells.mean(dim=0)

            # 6. Standing wave (spontaneous oscillation)
            t = step * 0.1
            for i in range(n):
                wave = 0.02 * math.sin(t + 2 * math.pi * i / n)
                new_states[i] = new_states[i] * (1.0 + wave)

            # 7. Frustration regulation
            for i in range(n):
                phases = new_states[i].angle()
                mean_phasor = torch.polar(torch.ones(self.hidden_dim), phases).mean()
                cell_frust = 1.0 - mean_phasor.abs().item()
                delta = cell_frust - 0.5
                if delta < -0.05:
                    noise_phase = torch.randn(self.hidden_dim) * min(0.2, abs(delta))
                    new_states[i] = torch.polar(new_states[i].abs(),
                                                new_states[i].angle() + noise_phase)
                elif delta > 0.05:
                    blend = min(0.15, abs(delta) * 0.3)
                    mean_ph = new_states[i].angle().mean()
                    smoothed = new_states[i].angle() * (1 - blend) + mean_ph * blend
                    new_states[i] = torch.polar(new_states[i].abs(), smoothed)

            # 8. Input injection
            sig = x.detach().float().squeeze(0)
            if sig.shape[0] != self.hidden_dim:
                sig = F.interpolate(
                    sig.unsqueeze(0).unsqueeze(0), size=self.hidden_dim,
                    mode='linear', align_corners=False
                ).squeeze()
            sig_norm = sig / (sig.abs().max() + 1e-8)
            phase_perturb = sig_norm * math.pi * 0.1
            for i in range(n):
                strength = 0.1 / (1 + 0.2 * i)
                perturbed = new_states[i].angle() + phase_perturb * strength
                new_states[i] = torch.polar(new_states[i].abs(), perturbed)

            # 9. Normalize
            amp = new_states.abs()
            amp = amp / (amp.max(dim=-1, keepdim=True).values + 1e-8)
            self.cell_states = torch.polar(amp, new_states.angle())

        # Coherence
        phases = self.cell_states.angle()
        mean_phasor = torch.exp(1j * phases).mean(dim=0)
        self._coherence = mean_phasor.abs().mean().item()

        # 10. Thalamic gate: top-8 most coherent cells gate output
        per_cell_coh = torch.exp(1j * self.cell_states.angle()).mean(dim=-1).abs()
        hub_idx = per_cell_coh.topk(self.n_hub).indices
        hub_mean = self.cell_states[hub_idx].abs().float().mean(dim=0)
        gate = torch.sigmoid(self.gate_proj(hub_mean)).detach()

        # Output: cavity mode gated by thalamus
        gated_cavity = self.cavity_mode * gate.mean().item()
        out_real = torch.cat([gated_cavity.real.float(),
                              gated_cavity.imag.float()]).unsqueeze(0)
        pred = self.decoder(out_real)
        tension = self._cat_tension + self.cell_states.abs().var().item()
        return pred, tension

    def get_hiddens(self):
        return self.cell_states.clone()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {
            'lasing': self._lasing_fraction,
            'coherence': self._coherence,
            'cat_tension': self._cat_tension,
        }


def run_fus6_everything_v9(n_cells=256, steps=300, input_dim=64,
                           hidden_dim=128, output_dim=64) -> FusionResult:
    print(f"\n[FUS-6/6] EVERYTHING_V9: Quantum + Laser + Category + Thalamic (TOP-2, Law 57)")
    engine = EverythingV9Engine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("FUS6_EVERYTHING_V9", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# Comparison table
# ══════════════════════════════════════════════════════════

def print_comparison_table(results: List[FusionResult]):
    print("\n" + "=" * 100)
    print("  FUSION FINAL RESULTS — v9 Engine Selection")
    print("=" * 100)

    # Main table
    print(f"\n  {'Name':<26s} | {'Phi(IIT)':>9s} | {'Granger':>9s} | {'V2 Comp':>9s} | "
          f"{'CE start':>9s} | {'CE end':>9s} | {'Time':>6s}")
    print("  " + "-" * 94)
    for r in results:
        print(f"  {r.name:<26s} | {r.phi_iit:>9.3f} | {r.granger:>9.1f} | {r.composite_v2:>9.1f} | "
              f"{r.ce_start:>9.4f} | {r.ce_end:>9.4f} | {r.time_sec:>5.1f}s")

    # Ranking by each metric
    for metric, key in [("Phi(IIT)", "phi_iit"), ("Granger", "granger"),
                        ("V2 Composite", "composite_v2")]:
        sorted_r = sorted(results, key=lambda r: getattr(r, key), reverse=True)
        print(f"\n  RANKING by {metric}:")
        max_val = max(getattr(r, key) for r in results) if results else 1.0
        for rank, r in enumerate(sorted_r, 1):
            val = getattr(r, key)
            bar_len = int(val / max(max_val, 1e-6) * 40)
            bar = "#" * bar_len
            print(f"    #{rank} {r.name:<24s} |{bar} {val:.2f}")

    # Baseline comparison
    baseline = next((r for r in results if r.name == "BASELINE"), None)
    if baseline:
        print("\n  SYNERGY vs BASELINE:")
        for r in results:
            if r.name == "BASELINE":
                continue
            iit_gain = r.phi_iit / max(baseline.phi_iit, 1e-6)
            granger_gain = r.granger / max(baseline.granger, 1e-6)
            v2_gain = r.composite_v2 / max(baseline.composite_v2, 1e-6)
            print(f"    {r.name:<24s}: IIT x{iit_gain:.1f}  |  Granger x{granger_gain:.1f}  |  "
                  f"V2 x{v2_gain:.1f}")

    # V9 recommendation
    best_granger = max(results, key=lambda r: r.granger)
    best_v2 = max(results, key=lambda r: r.composite_v2)
    best_iit = max(results, key=lambda r: r.phi_iit)

    print("\n  " + "=" * 60)
    print(f"  V9 ENGINE RECOMMENDATION:")
    print(f"    Best Phi(IIT):    {best_iit.name} = {best_iit.phi_iit:.3f}")
    print(f"    Best Granger:     {best_granger.name} = {best_granger.granger:.1f}")
    print(f"    Best V2 Composite: {best_v2.name} = {best_v2.composite_v2:.1f}")
    print("  " + "=" * 60)


# ══════════════════════════════════════════════════════════
# Main
# ══��═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Fusion Final — v9 Engine Selection Benchmark")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells (default 256)")
    parser.add_argument("--steps", type=int, default=300, help="Training steps (default 300)")
    parser.add_argument("--only", nargs="+", type=int, default=None,
                        help="Run only specific fusions (1-6)")
    parser.add_argument("--no-baseline", action="store_true", help="Skip baseline")
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps
    input_dim = 64
    hidden_dim = 128
    output_dim = 64

    print("=" * 100)
    print(f"  FUSION FINAL — v9 Engine Selection Benchmark")
    print(f"  {n_cells} cells, {steps} steps")
    print(f"  6 ULTIMATE fusions combining TOP discoveries from ALL categories")
    print(f"  Metrics: Phi(IIT) + Granger Causality + ConsciousnessMeterV2 Composite")
    print(f"  Law 57: less is more — TOP-2 fusion beats kitchen-sink")
    print("=" * 100)

    all_runners = {
        1: ("FUS1_QUANTUM_LASER", run_fus1_quantum_laser),
        2: ("FUS2_THALAMIC_QUANTUM", run_fus2_thalamic_quantum),
        3: ("FUS3_HIER_QUANTUM", run_fus3_hierarchical_quantum),
        4: ("FUS4_LASER_CATEGORY", run_fus4_laser_category),
        5: ("FUS5_QUANTUM_PERC", run_fus5_quantum_percolation),
        6: ("FUS6_EVERYTHING_V9", run_fus6_everything_v9),
    }

    run_ids = list(range(0, 7))
    if args.no_baseline:
        run_ids = [i for i in run_ids if i != 0]
    if args.only:
        run_ids = ([0] if not args.no_baseline else []) + args.only

    results = []
    for run_id in run_ids:
        try:
            if run_id == 0:
                print(f"\n[0/6] BASELINE: Standard PureField + GRU + faction sync")
                engine = BaselineEngine(n_cells=n_cells, input_dim=input_dim,
                                        hidden_dim=hidden_dim, output_dim=output_dim)
                result = run_engine("BASELINE", engine, n_cells, steps, input_dim)
            elif run_id in all_runners:
                name, runner = all_runners[run_id]
                result = runner(n_cells=n_cells, steps=steps, input_dim=input_dim,
                                hidden_dim=hidden_dim, output_dim=output_dim)
            else:
                continue
            results.append(result)
            print(f"\n  -> {result.summary()}")
        except Exception as e:
            label = f"FUS-{run_id}" if run_id > 0 else "BASELINE"
            print(f"\n  [ERROR] {label}: {e}")
            import traceback
            traceback.print_exc()

    if results:
        print_comparison_table(results)

    print("\nDone.")


if __name__ == "__main__":
    main()
