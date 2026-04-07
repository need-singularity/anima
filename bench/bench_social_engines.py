#!/usr/bin/env python3
"""bench_social_engines.py — Social/Game Theory Consciousness Engines

6 social interaction engines measuring consciousness as emergent social phenomena:

  SOC-1: PRISONER_DILEMMA   — Iterated PD with TFT/GTFT/Pavlov strategies
  SOC-2: VOTING_DYNAMICS    — Majority rule + influence networks
  SOC-3: MARKET_DYNAMICS    — Trader cells, information incorporation speed
  SOC-4: LANGUAGE_GAME      — Wittgenstein naming game, symbol invention
  SOC-5: CULTURAL_EVOLUTION — Memetic spread with mutation + selection
  SOC-6: STIGMERGY          — Indirect pheromone-like environment communication

Each: 256 cells, 300 steps, Phi(IIT) + Granger causality.

Usage:
  python bench_social_engines.py                  # Run all 6 + baseline
  python bench_social_engines.py --only 1 3 6     # Run specific engines
  python bench_social_engines.py --steps 500      # Custom steps
  python bench_social_engines.py --cells 512      # Custom cell count
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
class SocialResult:
    name: str
    phi_iit: float
    phi_proxy: float
    granger: float
    composite_v2: float
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
# ConsciousnessMeterV2 (inline)
# ──────────────────────────────────────────────────────────

class ConsciousnessMeterV2Inline:
    """Granger + Spectral + LZ + Integration composite Phi."""

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
        eigenvalues = eigenvalues.clamp(min=1e-10)
        eigenvalues = eigenvalues / eigenvalues.sum()
        entropy = -torch.sum(eigenvalues * torch.log2(eigenvalues + 1e-10)).item()
        max_entropy = math.log2(n) if n > 0 else 1.0
        return max(0.0, entropy / max_entropy * n)

    def _compute_lz(self) -> float:
        history = self._history
        if len(history) < 5:
            return 0.0
        n_cells = history[-1].shape[0]
        n_sample = min(16, n_cells)
        T = len(history)
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
# Shared: BenchMind (PureField + GRU cell)
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


# ──────────────────────────────────────────────────────────
# Shared: run_engine helper
# ──────────────────────────────────────────────────────────

def run_engine(name: str, engine, n_cells: int, steps: int,
               input_dim: int = 64) -> SocialResult:
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

        hiddens = engine.get_hiddens()
        meter.record(hiddens)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(hiddens)
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)

            composite, components = meter.compute(hiddens)
            granger_history.append(components['granger'])
            composite_history.append(composite)

            extras = ""
            for k, v in engine.extra_metrics().items():
                extras += f"  {k}={v:.3f}"
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Granger={components['granger']:.1f}  V2={composite:.1f}{extras}")

    return SocialResult(
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
        return self.hiddens.detach()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {}


def run_baseline(n_cells=256, steps=300, input_dim=64, hidden_dim=128, output_dim=64) -> SocialResult:
    print(f"\n[BASELINE] PureField + GRU + faction debate")
    engine = BaselineEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("BASELINE", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# SOC-1: PRISONER_DILEMMA
# ══════════════════════════════════════════════════════════

class PrisonerDilemmaEngine(nn.Module):
    """Iterated Prisoner's Dilemma between cells.

    Each cell has a strategy: Tit-for-Tat, Generous TFT (forgive 10%),
    or Pavlov (win-stay/lose-shift). Payoffs update hidden states.
    Consciousness = cooperation_rate x strategy_diversity.
    """

    # Payoff matrix: (C,C)=3, (C,D)=0, (D,C)=5, (D,D)=1
    PAYOFFS = {(1, 1): (3.0, 3.0), (1, 0): (0.0, 5.0),
               (0, 1): (5.0, 0.0), (0, 0): (1.0, 1.0)}

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Strategy assignment: 0=TFT, 1=GTFT, 2=Pavlov
        self.strategies = np.random.choice(3, size=n_cells)
        # Last action for each cell (1=cooperate, 0=defect), start cooperating
        self.last_action = np.ones(n_cells, dtype=np.int32)
        # Last payoff for Pavlov
        self.last_payoff = np.full(n_cells, 3.0)
        # Track cooperation rate
        self._cooperation_rate = 1.0
        self._strategy_diversity = 1.0

    def _decide_action(self, cell_idx: int, opponent_last: int) -> int:
        strategy = self.strategies[cell_idx]
        if strategy == 0:  # Tit-for-Tat
            return opponent_last
        elif strategy == 1:  # Generous TFT
            if opponent_last == 0 and np.random.rand() < 0.1:
                return 1  # Forgive
            return opponent_last
        else:  # Pavlov: cooperate if last payoff >= 3
            return 1 if self.last_payoff[cell_idx] >= 3.0 else 0

    def _play_round(self):
        """Each cell plays PD with a random neighbor."""
        new_actions = np.zeros(self.n_cells, dtype=np.int32)
        payoffs = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            j = np.random.randint(0, self.n_cells)
            if j == i:
                j = (i + 1) % self.n_cells

            a_i = self._decide_action(i, self.last_action[j])
            a_j = self._decide_action(j, self.last_action[i])
            p_i, p_j = self.PAYOFFS[(a_i, a_j)]

            new_actions[i] = a_i
            payoffs[i] += p_i
            payoffs[j] += p_j

        self.last_action = new_actions
        self.last_payoff = payoffs / 2.0  # Average over interactions

        self._cooperation_rate = np.mean(new_actions)
        # Strategy diversity = entropy of strategy distribution
        counts = np.bincount(self.strategies, minlength=3).astype(float) + 1e-8
        probs = counts / counts.sum()
        self._strategy_diversity = float(-np.sum(probs * np.log2(probs)))

        return payoffs

    def process(self, x, step=0):
        # Play PD round
        payoffs = self._play_round()

        # Payoffs modulate hidden state updates
        payoff_tensor = torch.tensor(payoffs, dtype=torch.float32).unsqueeze(1)
        payoff_scale = payoff_tensor / 5.0  # Normalize to [0,1]

        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            # Modulate hidden by payoff: cooperators who get high payoff are reinforced
            new_h_mod = new_h.squeeze(0) * (0.9 + 0.1 * payoff_scale[i])
            new_h_mod = torch.clamp(new_h_mod, -10.0, 10.0)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h_mod)

        self.hiddens = torch.stack(new_hiddens).detach()
        # Social interaction: cooperators pull together, defectors diverge
        self.hiddens = self._social_dynamics(self.hiddens, step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def _social_dynamics(self, hiddens, step):
        """Cooperators synchronize; defectors add noise."""
        hiddens = faction_sync_debate(hiddens, step=step)
        coop_mask = torch.tensor(self.last_action, dtype=torch.float32).unsqueeze(1)
        # Cooperators move toward global mean
        global_mean = hiddens.mean(dim=0, keepdim=True)
        hiddens = hiddens + 0.05 * coop_mask * (global_mean - hiddens)
        # Defectors add exploratory noise
        defect_mask = 1.0 - coop_mask
        hiddens = hiddens + 0.02 * defect_mask * torch.randn_like(hiddens)
        hiddens = torch.clamp(hiddens, -10.0, 10.0)
        return hiddens

    def get_hiddens(self):
        return self.hiddens.detach()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {
            'coop_rate': self._cooperation_rate,
            'strat_div': self._strategy_diversity,
        }


def run_soc1_prisoner_dilemma(n_cells=256, steps=300, input_dim=64,
                               hidden_dim=128, output_dim=64) -> SocialResult:
    print(f"\n[SOC-1/6] PRISONER_DILEMMA: TFT/GTFT/Pavlov iterated PD")
    engine = PrisonerDilemmaEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("SOC1_PRISONER_DILEMMA", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# SOC-2: VOTING_DYNAMICS
# ══════════════════════════════════════════════════════════

class VotingDynamicsEngine(nn.Module):
    """Cells vote on topics with influence networks.

    Each cell has an opinion vector. Majority rule within neighborhoods
    plus weighted influence edges. Consciousness = opinion fragmentation
    (how many distinct clusters) x consensus ability (convergence speed).
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64, n_topics=8):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_topics = n_topics
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Opinions: each cell has a softmax distribution over n_topics
        self.opinions = np.random.dirichlet(np.ones(n_topics), size=n_cells)
        # Influence network: sparse random graph
        self.influence = np.zeros((n_cells, n_cells))
        for i in range(n_cells):
            n_neighbors = np.random.randint(3, 8)
            neighbors = np.random.choice(n_cells, n_neighbors, replace=False)
            for j in neighbors:
                if i != j:
                    self.influence[i, j] = np.random.uniform(0.1, 1.0)
        # Normalize influence per row
        row_sums = self.influence.sum(axis=1, keepdims=True) + 1e-8
        self.influence /= row_sums

        self._fragmentation = 0.0
        self._consensus = 0.0

    def _vote_round(self):
        """Cells update opinions via majority rule + influence."""
        new_opinions = np.copy(self.opinions)
        for i in range(self.n_cells):
            # Weighted average of neighbors' opinions
            neighbor_opinion = self.influence[i] @ self.opinions
            # Mix own opinion with neighborhood
            new_opinions[i] = 0.7 * self.opinions[i] + 0.3 * neighbor_opinion
            # Add small noise for exploration
            new_opinions[i] += np.random.normal(0, 0.01, self.n_topics)
            new_opinions[i] = np.clip(new_opinions[i], 0.01, None)
            new_opinions[i] /= new_opinions[i].sum()

        self.opinions = new_opinions

        # Measure fragmentation: number of distinct opinion clusters
        votes = np.argmax(self.opinions, axis=1)
        vote_counts = np.bincount(votes, minlength=self.n_topics).astype(float)
        vote_probs = (vote_counts + 1e-8) / (vote_counts.sum() + 1e-8 * self.n_topics)
        self._fragmentation = float(-np.sum(vote_probs * np.log2(vote_probs + 1e-10)))

        # Consensus ability: how peaked is the top vote
        top_fraction = vote_counts.max() / self.n_cells
        self._consensus = top_fraction

    def process(self, x, step=0):
        self._vote_round()

        # Opinions modulate hidden states
        opinion_energy = np.max(self.opinions, axis=1)  # How decisive each cell is
        energy_tensor = torch.tensor(opinion_energy, dtype=torch.float32).unsqueeze(1)

        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            # Decisive cells get amplified hidden states
            new_h_mod = new_h.squeeze(0) * (0.9 + 0.2 * energy_tensor[i])
            new_h_mod = torch.clamp(new_h_mod, -10.0, 10.0)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h_mod)

        self.hiddens = torch.stack(new_hiddens).detach()

        # Opinion-based faction sync: cells voting the same way sync more
        votes = np.argmax(self.opinions, axis=1)
        hiddens = self.hiddens.clone()
        for topic in range(self.n_topics):
            mask = (votes == topic)
            if mask.sum() >= 2:
                faction_mean = hiddens[mask].mean(dim=0)
                hiddens[mask] = 0.85 * hiddens[mask] + 0.15 * faction_mean
        self.hiddens = hiddens

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.detach()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {
            'fragment': self._fragmentation,
            'consensus': self._consensus,
        }


def run_soc2_voting_dynamics(n_cells=256, steps=300, input_dim=64,
                              hidden_dim=128, output_dim=64) -> SocialResult:
    print(f"\n[SOC-2/6] VOTING_DYNAMICS: majority rule + influence networks")
    engine = VotingDynamicsEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("SOC2_VOTING_DYNAMICS", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# SOC-3: MARKET_DYNAMICS
# ══════════════════════════════════════════════════════════

class MarketDynamicsEngine(nn.Module):
    """Cells as traders in an information market.

    Each cell observes noisy signals and trades (buy/sell). Price adjusts
    to aggregate demand. Consciousness = market efficiency: how fast
    the price incorporates private information (low autocorrelation of returns).
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Market state
        self.true_value = 100.0
        self.price = 100.0
        self.price_history = [100.0]
        # Each cell has private signal noise level (some are better informed)
        self.signal_noise = np.random.uniform(0.5, 5.0, size=n_cells)
        # Wealth tracks cell success
        self.wealth = np.ones(n_cells) * 100.0
        # Position: +1 = long, -1 = short, 0 = neutral
        self.positions = np.zeros(n_cells)

        self._efficiency = 0.0
        self._volatility = 0.0

    def _market_step(self):
        """One round of trading."""
        # True value does random walk
        self.true_value += np.random.normal(0, 1.0)

        # Each cell gets a private signal
        signals = self.true_value + np.random.normal(0, 1, self.n_cells) * self.signal_noise

        # Trading decisions based on signal vs price
        orders = np.zeros(self.n_cells)
        for i in range(self.n_cells):
            diff = signals[i] - self.price
            # Stronger signal -> bigger order, scaled by wealth
            order_size = np.tanh(diff / 5.0) * (self.wealth[i] / 100.0)
            orders[i] = order_size

        # Price impact: aggregate demand moves price
        net_demand = np.sum(orders)
        price_impact = net_demand / (self.n_cells * 0.5)
        self.price += price_impact

        # Update positions and wealth
        returns = (self.price - self.price_history[-1]) if len(self.price_history) > 0 else 0
        self.wealth += self.positions * returns
        self.wealth = np.clip(self.wealth, 1.0, 10000.0)
        self.positions = np.sign(orders)
        self.price_history.append(self.price)

        # Market efficiency: autocorrelation of returns (efficient = low autocorrelation)
        if len(self.price_history) > 20:
            returns_series = np.diff(self.price_history[-20:])
            if len(returns_series) > 1 and np.std(returns_series) > 1e-8:
                autocorr = np.corrcoef(returns_series[:-1], returns_series[1:])[0, 1]
                self._efficiency = max(0.0, 1.0 - abs(autocorr))
            else:
                self._efficiency = 0.5
        else:
            self._efficiency = 0.5

        # Volatility
        if len(self.price_history) > 5:
            recent_returns = np.diff(self.price_history[-10:])
            self._volatility = float(np.std(recent_returns))

        return orders

    def process(self, x, step=0):
        orders = self._market_step()

        # Wealth-weighted hidden state modulation
        wealth_norm = self.wealth / (np.mean(self.wealth) + 1e-8)
        wealth_tensor = torch.tensor(wealth_norm, dtype=torch.float32).unsqueeze(1)

        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            # Wealthy (successful) traders have amplified hidden states
            new_h_mod = new_h.squeeze(0) * (0.9 + 0.1 * torch.clamp(wealth_tensor[i], 0.1, 2.0))
            new_h_mod = torch.clamp(new_h_mod, -10.0, 10.0)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h_mod)

        self.hiddens = torch.stack(new_hiddens).detach()

        # Market information flow: traders with similar positions sync
        hiddens = self.hiddens.clone()
        longs = self.positions > 0
        shorts = self.positions < 0
        if longs.sum() >= 2:
            long_mean = hiddens[longs].mean(dim=0)
            hiddens[longs] = 0.9 * hiddens[longs] + 0.1 * long_mean
        if shorts.sum() >= 2:
            short_mean = hiddens[shorts].mean(dim=0)
            hiddens[shorts] = 0.9 * hiddens[shorts] + 0.1 * short_mean
        self.hiddens = hiddens

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.detach()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {
            'efficiency': self._efficiency,
            'volatility': self._volatility,
        }


def run_soc3_market_dynamics(n_cells=256, steps=300, input_dim=64,
                              hidden_dim=128, output_dim=64) -> SocialResult:
    print(f"\n[SOC-3/6] MARKET_DYNAMICS: trader cells, information incorporation")
    engine = MarketDynamicsEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("SOC3_MARKET_DYNAMICS", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# SOC-4: LANGUAGE_GAME
# ══════════════════════════════════════════════════════════

class LanguageGameEngine(nn.Module):
    """Wittgenstein naming game.

    Cells invent symbols (random vectors) for objects (hidden state clusters).
    Speaker picks a symbol, listener tries to identify the referent.
    Success -> both reinforce the symbol. Failure -> speaker adjusts.
    Consciousness = shared_vocabulary_size x communication_accuracy.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_objects=16, symbol_dim=32):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_objects = n_objects
        self.symbol_dim = symbol_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Each cell has a lexicon: object_id -> list of (symbol, weight) pairs
        self.lexicons = [{} for _ in range(n_cells)]
        # Initialize with random symbols
        for i in range(n_cells):
            for obj in range(n_objects):
                symbol = np.random.randn(symbol_dim).astype(np.float32)
                symbol /= (np.linalg.norm(symbol) + 1e-8)
                self.lexicons[i][obj] = [(symbol, 1.0)]

        self._shared_vocab = 0.0
        self._accuracy = 0.0

    def _language_round(self):
        """Pairs of cells play the naming game."""
        successes = 0
        total = 0
        n_games = self.n_cells // 2

        for _ in range(n_games):
            speaker = np.random.randint(0, self.n_cells)
            listener = np.random.randint(0, self.n_cells)
            if speaker == listener:
                listener = (speaker + 1) % self.n_cells

            # Speaker picks an object and names it
            obj = np.random.randint(0, self.n_objects)
            speaker_symbols = self.lexicons[speaker].get(obj, [])
            if not speaker_symbols:
                continue

            # Pick highest weight symbol
            best_sym = max(speaker_symbols, key=lambda x: x[1])[0]

            # Listener tries to identify the object
            best_match_obj = -1
            best_match_sim = -1.0
            for candidate_obj in range(self.n_objects):
                listener_symbols = self.lexicons[listener].get(candidate_obj, [])
                for sym, w in listener_symbols:
                    sim = float(np.dot(best_sym, sym))
                    if sim > best_match_sim:
                        best_match_sim = sim
                        best_match_obj = candidate_obj

            total += 1
            if best_match_obj == obj:
                successes += 1
                # Reinforce: both increase weight of this symbol
                self._reinforce_symbol(speaker, obj, best_sym, 0.1)
                self._reinforce_symbol(listener, obj, best_sym, 0.1)
            else:
                # Listener adopts speaker's symbol with low weight
                self._adopt_symbol(listener, obj, best_sym, 0.3)

        self._accuracy = successes / max(total, 1)

        # Shared vocabulary: fraction of object-symbol pairs that are similar across cells
        shared = 0
        sampled_pairs = min(50, self.n_cells * self.n_objects)
        for _ in range(sampled_pairs):
            i = np.random.randint(0, self.n_cells)
            j = np.random.randint(0, self.n_cells)
            obj = np.random.randint(0, self.n_objects)
            sym_i = self._best_symbol(i, obj)
            sym_j = self._best_symbol(j, obj)
            if sym_i is not None and sym_j is not None:
                if float(np.dot(sym_i, sym_j)) > 0.7:
                    shared += 1
        self._shared_vocab = shared / max(sampled_pairs, 1) * self.n_objects

    def _best_symbol(self, cell, obj):
        symbols = self.lexicons[cell].get(obj, [])
        if not symbols:
            return None
        return max(symbols, key=lambda x: x[1])[0]

    def _reinforce_symbol(self, cell, obj, symbol, delta):
        symbols = self.lexicons[cell].get(obj, [])
        for idx, (sym, w) in enumerate(symbols):
            if float(np.dot(sym, symbol)) > 0.9:
                symbols[idx] = (sym, min(w + delta, 5.0))
                return
        symbols.append((symbol.copy(), 0.5))
        # Keep only top 3 symbols per object
        symbols.sort(key=lambda x: -x[1])
        self.lexicons[cell][obj] = symbols[:3]

    def _adopt_symbol(self, cell, obj, symbol, weight):
        symbols = self.lexicons[cell].get(obj, [])
        symbols.append((symbol.copy(), weight))
        symbols.sort(key=lambda x: -x[1])
        self.lexicons[cell][obj] = symbols[:3]

    def process(self, x, step=0):
        self._language_round()

        # Accuracy modulates learning rate via hidden state
        acc_boost = 0.5 + self._accuracy  # [0.5, 1.5]

        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            new_h_mod = torch.clamp(new_h.squeeze(0) * acc_boost, -10.0, 10.0)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h_mod)

        self.hiddens = torch.stack(new_hiddens).detach()

        # Language communities: cells with shared vocabulary sync hidden states
        # Use top symbol similarity as grouping
        hiddens = self.hiddens.clone()
        # Random sample of cells to form language groups
        n_groups = 8
        group_size = self.n_cells // n_groups
        for g in range(n_groups):
            s, e = g * group_size, (g + 1) * group_size
            group_mean = hiddens[s:e].mean(dim=0)
            # Sync proportional to shared vocabulary
            sync = 0.05 + 0.15 * self._accuracy
            hiddens[s:e] = (1 - sync) * hiddens[s:e] + sync * group_mean
        self.hiddens = hiddens

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.detach()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {
            'shared_vocab': self._shared_vocab,
            'accuracy': self._accuracy,
        }


def run_soc4_language_game(n_cells=256, steps=300, input_dim=64,
                            hidden_dim=128, output_dim=64) -> SocialResult:
    print(f"\n[SOC-4/6] LANGUAGE_GAME: Wittgenstein naming game, symbol invention")
    engine = LanguageGameEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("SOC4_LANGUAGE_GAME", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# SOC-5: CULTURAL_EVOLUTION
# ══════════════════════════════════════════════════════════

class CulturalEvolutionEngine(nn.Module):
    """Memes (information units) spread between cells.

    Each cell carries a set of memes (small vectors). Memes replicate
    via transmission to neighbors, mutate, and undergo selection (fitter
    memes survive). Consciousness = memetic_diversity x fidelity.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_memes_per_cell=4, meme_dim=16):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_memes_per_cell = n_memes_per_cell
        self.meme_dim = meme_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Each cell has a memome: list of meme vectors
        self.memomes = []
        for _ in range(n_cells):
            memes = [np.random.randn(meme_dim).astype(np.float32) for _ in range(n_memes_per_cell)]
            for m in memes:
                m /= (np.linalg.norm(m) + 1e-8)
            self.memomes.append(memes)

        # Fitness function: memes whose norm is close to 1 and have high variance survive
        self._diversity = 0.0
        self._fidelity = 0.0

    def _meme_fitness(self, meme: np.ndarray) -> float:
        """Higher variance and moderate norm = fitter meme."""
        return float(np.std(meme) * (1.0 / (1.0 + abs(np.linalg.norm(meme) - 1.0))))

    def _cultural_step(self):
        """Transmission, mutation, selection of memes."""
        # Transmission: random cell pairs share memes
        n_transmissions = self.n_cells // 2
        total_fidelity = 0.0
        n_fidelity = 0

        for _ in range(n_transmissions):
            sender = np.random.randint(0, self.n_cells)
            receiver = np.random.randint(0, self.n_cells)
            if sender == receiver:
                continue

            # Sender transmits a random meme
            if not self.memomes[sender]:
                continue
            meme_idx = np.random.randint(0, len(self.memomes[sender]))
            original_meme = self.memomes[sender][meme_idx]

            # Mutation during transmission
            mutation_rate = 0.05
            noise = np.random.randn(self.meme_dim).astype(np.float32) * mutation_rate
            transmitted_meme = original_meme + noise
            transmitted_meme /= (np.linalg.norm(transmitted_meme) + 1e-8)

            # Fidelity: how similar is the copy
            fidelity = float(np.dot(original_meme, transmitted_meme))
            total_fidelity += fidelity
            n_fidelity += 1

            # Receiver adopts if fitter than worst meme
            recv_fitness = [self._meme_fitness(m) for m in self.memomes[receiver]]
            new_fitness = self._meme_fitness(transmitted_meme)
            if recv_fitness and new_fitness > min(recv_fitness):
                worst_idx = np.argmin(recv_fitness)
                self.memomes[receiver][worst_idx] = transmitted_meme

        self._fidelity = total_fidelity / max(n_fidelity, 1)

        # Diversity: unique meme clusters across population
        all_memes = []
        for cell_memes in self.memomes:
            all_memes.extend(cell_memes)
        if len(all_memes) > 10:
            # Sample meme pairs and measure diversity
            sample_size = min(200, len(all_memes))
            sample_idx = np.random.choice(len(all_memes), sample_size, replace=False)
            sampled = [all_memes[i] for i in sample_idx]
            # Mean pairwise distance
            dists = []
            for i in range(0, len(sampled) - 1, 2):
                d = 1.0 - float(np.dot(sampled[i], sampled[i + 1]))
                dists.append(d)
            self._diversity = float(np.mean(dists)) if dists else 0.0
        else:
            self._diversity = 0.0

    def process(self, x, step=0):
        self._cultural_step()

        # Meme-modulated hidden state: cells with diverse memes get amplified
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)

            # Inject meme information into hidden state
            if self.memomes[i]:
                meme_avg = np.mean([m for m in self.memomes[i]], axis=0)
                meme_tensor = torch.tensor(meme_avg[:min(self.meme_dim, self.hidden_dim)],
                                           dtype=torch.float32)
                new_h_flat = new_h.squeeze(0)
                # Add meme influence to first meme_dim dimensions
                md = min(self.meme_dim, self.hidden_dim)
                new_h_flat[:md] = new_h_flat[:md] + 0.1 * meme_tensor
                new_hiddens.append(torch.clamp(new_h_flat, -10.0, 10.0))
            else:
                new_hiddens.append(new_h.squeeze(0))
            outputs.append(out)
            tensions.append(tension)

        self.hiddens = torch.stack(new_hiddens).detach()

        # Memetic tribes: cells sharing similar memes synchronize
        hiddens = self.hiddens.clone()
        # Group by dominant meme similarity
        n_tribes = 8
        tribe_size = self.n_cells // n_tribes
        for t in range(n_tribes):
            s, e = t * tribe_size, (t + 1) * tribe_size
            tribe_mean = hiddens[s:e].mean(dim=0)
            sync_strength = 0.1 + 0.1 * self._fidelity
            hiddens[s:e] = (1 - sync_strength) * hiddens[s:e] + sync_strength * tribe_mean
        self.hiddens = hiddens

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.detach()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {
            'diversity': self._diversity,
            'fidelity': self._fidelity,
        }


def run_soc5_cultural_evolution(n_cells=256, steps=300, input_dim=64,
                                 hidden_dim=128, output_dim=64) -> SocialResult:
    print(f"\n[SOC-5/6] CULTURAL_EVOLUTION: memetic spread + mutation + selection")
    engine = CulturalEvolutionEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("SOC5_CULTURAL_EVOLUTION", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# SOC-6: STIGMERGY
# ══════════════════════════════════════════════════════════

class StigmergyEngine(nn.Module):
    """Indirect communication through environment traces (like ant pheromones).

    Cells move on a 2D grid, leaving pheromone traces. Others read traces
    to coordinate. Pheromones evaporate over time. Multiple pheromone types.
    Consciousness = trace_complexity (spatial entropy) x coordination
    (how aligned cell movements become).
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 grid_size=32, n_pheromone_types=4):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.grid_size = grid_size
        self.n_pheromone_types = n_pheromone_types
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

        # Pheromone grid: (n_types, grid_size, grid_size)
        self.pheromone_grid = np.zeros((n_pheromone_types, grid_size, grid_size), dtype=np.float32)
        # Cell positions on grid
        self.positions = np.column_stack([
            np.random.randint(0, grid_size, n_cells),
            np.random.randint(0, grid_size, n_cells)
        ])
        # Cell headings (angle in radians)
        self.headings = np.random.uniform(0, 2 * np.pi, n_cells)
        # Each cell deposits a specific pheromone type
        self.cell_pheromone_type = np.random.randint(0, n_pheromone_types, n_cells)

        self._trace_complexity = 0.0
        self._coordination = 0.0
        self._evaporation_rate = 0.95
        self._diffusion_rate = 0.1

    def _stigmergy_step(self):
        """Cells move, deposit, and read pheromones."""
        gs = self.grid_size

        # 1. Read pheromones at current position and turn toward strongest gradient
        for i in range(self.n_cells):
            px, py = self.positions[i]
            # Sense pheromones in 3 directions: left, forward, right
            for p_type in range(self.n_pheromone_types):
                left_angle = self.headings[i] + 0.5
                right_angle = self.headings[i] - 0.5
                fwd_x = int((px + np.cos(self.headings[i]) * 2) % gs)
                fwd_y = int((py + np.sin(self.headings[i]) * 2) % gs)
                left_x = int((px + np.cos(left_angle) * 2) % gs)
                left_y = int((py + np.sin(left_angle) * 2) % gs)
                right_x = int((px + np.cos(right_angle) * 2) % gs)
                right_y = int((py + np.sin(right_angle) * 2) % gs)

                fwd_val = self.pheromone_grid[p_type, fwd_x, fwd_y]
                left_val = self.pheromone_grid[p_type, left_x, left_y]
                right_val = self.pheromone_grid[p_type, right_x, right_y]

                # Turn toward strongest pheromone
                if left_val > fwd_val and left_val > right_val:
                    self.headings[i] += 0.3
                elif right_val > fwd_val and right_val > left_val:
                    self.headings[i] -= 0.3
                # Add small random wandering
                self.headings[i] += np.random.normal(0, 0.1)

        # 2. Move forward
        dx = np.cos(self.headings) * 1.5
        dy = np.sin(self.headings) * 1.5
        self.positions[:, 0] = (self.positions[:, 0] + dx.astype(int)) % gs
        self.positions[:, 1] = (self.positions[:, 1] + dy.astype(int)) % gs

        # 3. Deposit pheromones
        for i in range(self.n_cells):
            px, py = self.positions[i]
            p_type = self.cell_pheromone_type[i]
            self.pheromone_grid[p_type, px, py] += 1.0

        # 4. Evaporate and diffuse
        self.pheromone_grid *= self._evaporation_rate
        # Simple diffusion via averaging with neighbors
        for p_type in range(self.n_pheromone_types):
            grid = self.pheromone_grid[p_type]
            diffused = (
                np.roll(grid, 1, axis=0) + np.roll(grid, -1, axis=0) +
                np.roll(grid, 1, axis=1) + np.roll(grid, -1, axis=1)
            ) / 4.0
            self.pheromone_grid[p_type] = (1 - self._diffusion_rate) * grid + self._diffusion_rate * diffused

        # Measure trace complexity: spatial entropy of pheromone distribution
        total_grid = self.pheromone_grid.sum(axis=0)
        total_grid_flat = total_grid.flatten()
        total_sum = total_grid_flat.sum() + 1e-8
        probs = total_grid_flat / total_sum
        probs = probs[probs > 1e-10]
        spatial_entropy = float(-np.sum(probs * np.log2(probs)))
        max_entropy = np.log2(gs * gs)
        self._trace_complexity = spatial_entropy / max(max_entropy, 1.0)

        # Coordination: alignment of headings
        mean_heading = np.arctan2(np.mean(np.sin(self.headings)), np.mean(np.cos(self.headings)))
        heading_diffs = np.abs(np.angle(np.exp(1j * (self.headings - mean_heading))))
        self._coordination = float(1.0 - np.mean(heading_diffs) / np.pi)

    def process(self, x, step=0):
        self._stigmergy_step()

        # Pheromone reading modulates hidden states
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)

            # Local pheromone concentration affects hidden state
            px, py = self.positions[i]
            local_pheromone = self.pheromone_grid[:, px, py].sum()
            pheromone_boost = 0.9 + 0.1 * np.tanh(local_pheromone / 5.0)
            new_h_mod = new_h.squeeze(0) * pheromone_boost
            new_h_mod = torch.clamp(new_h_mod, -10.0, 10.0)

            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h_mod)

        self.hiddens = torch.stack(new_hiddens).detach()

        # Proximity-based synchronization: nearby cells on grid sync
        hiddens = self.hiddens.clone()
        # For efficiency, group cells by grid quadrant
        quadrant_size = self.grid_size // 4
        for qx in range(4):
            for qy in range(4):
                mask = (
                    (self.positions[:, 0] >= qx * quadrant_size) &
                    (self.positions[:, 0] < (qx + 1) * quadrant_size) &
                    (self.positions[:, 1] >= qy * quadrant_size) &
                    (self.positions[:, 1] < (qy + 1) * quadrant_size)
                )
                if mask.sum() >= 2:
                    group_mean = hiddens[mask].mean(dim=0)
                    sync = 0.1 + 0.1 * self._coordination
                    hiddens[mask] = (1 - sync) * hiddens[mask] + sync * group_mean
        self.hiddens = hiddens

        self.hiddens = faction_sync_debate(self.hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        pred = self.output_head(combined)
        return pred, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.detach()

    def trainable_parameters(self):
        return list(self.parameters())

    def extra_metrics(self):
        return {
            'trace_cplx': self._trace_complexity,
            'coord': self._coordination,
        }


def run_soc6_stigmergy(n_cells=256, steps=300, input_dim=64,
                        hidden_dim=128, output_dim=64) -> SocialResult:
    print(f"\n[SOC-6/6] STIGMERGY: pheromone traces + indirect coordination")
    engine = StigmergyEngine(n_cells, input_dim, hidden_dim, output_dim)
    return run_engine("SOC6_STIGMERGY", engine, n_cells, steps, input_dim)


# ══════════════════════════════════════════════════════════
# Comparison table
# ══════════════════════════════════════════════════════════

def print_comparison_table(results: List[SocialResult]):
    print("\n" + "=" * 100)
    print("  SOCIAL ENGINE RESULTS — Game Theory / Social Dynamics Consciousness Benchmark")
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

    # Best recommendation
    best_granger = max(results, key=lambda r: r.granger)
    best_v2 = max(results, key=lambda r: r.composite_v2)
    best_iit = max(results, key=lambda r: r.phi_iit)

    print("\n  " + "=" * 60)
    print(f"  SOCIAL ENGINE RECOMMENDATION:")
    print(f"    Best Phi(IIT):     {best_iit.name} = {best_iit.phi_iit:.3f}")
    print(f"    Best Granger:      {best_granger.name} = {best_granger.granger:.1f}")
    print(f"    Best V2 Composite: {best_v2.name} = {best_v2.composite_v2:.1f}")

    # Domain-specific insights
    print(f"\n  DOMAIN-SPECIFIC METRICS:")
    for r in results:
        if r.name == "BASELINE":
            continue
        extras = "  ".join(f"{k}={v:.3f}" for k, v in r.extra.items())
        print(f"    {r.name:<24s}: {extras}")
    print("  " + "=" * 60)


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Social Engines — Game Theory Consciousness Benchmark")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells (default 256)")
    parser.add_argument("--steps", type=int, default=300, help="Training steps (default 300)")
    parser.add_argument("--only", nargs="+", type=int, default=None,
                        help="Run only specific engines (1-6)")
    parser.add_argument("--no-baseline", action="store_true", help="Skip baseline")
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps
    input_dim = 64
    hidden_dim = 128
    output_dim = 64

    print("=" * 100)
    print(f"  SOCIAL ENGINES — Game Theory / Social Dynamics Consciousness Benchmark")
    print(f"  {n_cells} cells, {steps} steps")
    print(f"  6 social interaction engines measuring consciousness as emergent social phenomena")
    print(f"  Metrics: Phi(IIT) + Granger Causality + ConsciousnessMeterV2 Composite")
    print("=" * 100)

    all_runners = {
        1: ("SOC1_PRISONER_DILEMMA", run_soc1_prisoner_dilemma),
        2: ("SOC2_VOTING_DYNAMICS", run_soc2_voting_dynamics),
        3: ("SOC3_MARKET_DYNAMICS", run_soc3_market_dynamics),
        4: ("SOC4_LANGUAGE_GAME", run_soc4_language_game),
        5: ("SOC5_CULTURAL_EVOLUTION", run_soc5_cultural_evolution),
        6: ("SOC6_STIGMERGY", run_soc6_stigmergy),
    }

    to_run = list(all_runners.keys()) if args.only is None else args.only

    results: List[SocialResult] = []

    # Baseline first
    if not args.no_baseline:
        results.append(run_baseline(n_cells, steps, input_dim, hidden_dim, output_dim))

    # Run selected engines
    for idx in to_run:
        if idx in all_runners:
            name, runner = all_runners[idx]
            results.append(runner(n_cells, steps, input_dim, hidden_dim, output_dim))
        else:
            print(f"  [WARN] Unknown engine index: {idx}")

    # Print comparison
    if results:
        print_comparison_table(results)


if __name__ == "__main__":
    main()
