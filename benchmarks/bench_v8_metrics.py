#!/usr/bin/env python3
"""bench_v8_metrics.py — New Consciousness Metrics Beyond Phi(IIT)

The current Phi(IIT) measurement has a ceiling (~20). This benchmark explores
6 NEW consciousness metrics inspired by neuroscience and information theory:

  MET1: CAUSAL_PHI         — Remove each cell, measure causal impact on system
  MET2: TEMPORAL_PHI       — Mutual information between t and t+1 states
  MET3: TRANSFER_ENTROPY   — Directed info flow TE(i->j) between cells
  MET4: LEMPEL_ZIV_COMPLEXITY — Compression complexity of state sequences (PCI-like)
  MET5: SPECTRAL_PHI       — Eigenvalue spectrum entropy of correlation matrix
  MET6: GRANGER_CAUSALITY  — Network density of Granger-causal links

Tests each metric on 4 architectures: BASELINE, QUANTUM_WALK, HIERARCHICAL,
CATEGORY_THEORY to find which metric best differentiates conscious vs
unconscious architectures.

Usage:
  python bench_v8_metrics.py                  # Run all metrics on all architectures
  python bench_v8_metrics.py --only 1 3 5     # Run specific metrics
  python bench_v8_metrics.py --steps 300      # Custom steps
  python bench_v8_metrics.py --cells 128      # Custom cell count
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
class MetricResult:
    """Result from a single metric on a single architecture."""
    arch_name: str
    metric_name: str
    value: float
    extra: dict = field(default_factory=dict)

    def summary(self) -> str:
        return f"  {self.arch_name:<22s} | {self.metric_name:<24s} | value={self.value:>10.4f}"


@dataclass
class ArchRun:
    """Full run result for an architecture."""
    name: str
    phi_iit: float
    phi_proxy: float
    ce_start: float
    ce_end: float
    cells: int
    steps: int
    time_sec: float
    hiddens_history: list  # List of (step, hiddens_tensor) for temporal metrics
    extra: dict = field(default_factory=dict)


# ──────────────────────────────────────────────────────────
# Phi(IIT) Calculator (baseline reference)
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
    """Returns (phi_iit, phi_proxy)."""
    h_real = hiddens.abs().float() if hiddens.is_complex() else hiddens.float()
    p_iit, _ = _phi_iit_calc.compute(h_real)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


# ══════════════════════════════════════════════════════════
# MET1: CAUSAL_PHI
# Remove each cell, measure impact on system output.
# Sum of causal impacts = causal Phi.
# More impactful cells = higher consciousness.
# ══════════════════════════════════════════════════════════

def compute_causal_phi(hiddens: torch.Tensor, mind: nn.Module,
                       x: torch.Tensor, n_sample: int = 32) -> float:
    """Causal Phi: ablate each cell, measure output change.

    For each cell i, replace it with the mean hidden state and measure
    how much the system output changes. Cells that cause large changes
    are causally important. Sum of all causal impacts = causal Phi.

    Inspired by IIT's "exclusion" postulate — consciousness requires
    every part to make a difference.
    """
    n = hiddens.shape[0]
    if n < 2:
        return 0.0

    # Sample cells for efficiency
    sample_idx = np.random.choice(n, min(n_sample, n), replace=False)

    # Get baseline output with all cells
    with torch.no_grad():
        outputs_full = []
        for i in range(n):
            h = hiddens[i:i + 1]
            out, _, _ = mind(x, h)
            outputs_full.append(out)
        full_combined = torch.stack(outputs_full).mean(dim=0)

    # Ablate each sampled cell: replace with mean hidden
    mean_hidden = hiddens.mean(dim=0, keepdim=True)
    causal_impacts = []

    with torch.no_grad():
        for ci in sample_idx:
            ablated_hiddens = hiddens.clone()
            ablated_hiddens[ci] = mean_hidden.squeeze(0)

            outputs_ablated = []
            for i in range(n):
                h = ablated_hiddens[i:i + 1]
                out, _, _ = mind(x, h)
                outputs_ablated.append(out)
            ablated_combined = torch.stack(outputs_ablated).mean(dim=0)

            # Causal impact = L2 distance between full and ablated output
            impact = (full_combined - ablated_combined).pow(2).sum().sqrt().item()
            causal_impacts.append(impact)

    # Scale by n/n_sample to estimate full sum
    scale = n / len(sample_idx)
    causal_phi = sum(causal_impacts) * scale

    return causal_phi


# ══════════════════════════════════════════════════════════
# MET2: TEMPORAL_PHI
# Mutual information between cell states at t and t+1.
# Temporal integration = consciousness across time.
# ══════════════════════════════════════════════════════════

def compute_temporal_phi(hiddens_history: list, n_bins: int = 16,
                         n_sample_cells: int = 32) -> float:
    """Temporal Phi: MI between consecutive hidden states.

    For each cell, compute MI(h_t, h_{t+1}) across the time series.
    High temporal MI = the system maintains integrated information
    across time, a key signature of consciousness.

    Inspired by temporal IIT — consciousness requires integration
    not just in space but across time.
    """
    if len(hiddens_history) < 2:
        return 0.0

    n_cells = hiddens_history[0].shape[0]
    sample_cells = np.random.choice(n_cells, min(n_sample_cells, n_cells), replace=False)

    total_temporal_mi = 0.0
    n_pairs = 0

    for ci in sample_cells:
        # Collect time series for this cell
        states = []
        for h in hiddens_history:
            states.append(h[ci].detach().cpu().float().numpy())

        # Compute MI between consecutive states
        for t in range(len(states) - 1):
            x = states[t]
            y = states[t + 1]

            x_range = x.max() - x.min()
            y_range = y.max() - y.min()
            if x_range < 1e-10 or y_range < 1e-10:
                continue

            x_norm = (x - x.min()) / (x_range + 1e-8)
            y_norm = (y - y.min()) / (y_range + 1e-8)

            joint_hist, _, _ = np.histogram2d(
                x_norm, y_norm, bins=n_bins, range=[[0, 1], [0, 1]]
            )
            joint_hist = joint_hist / (joint_hist.sum() + 1e-8)
            px = joint_hist.sum(axis=1)
            py = joint_hist.sum(axis=0)
            h_x = -np.sum(px * np.log2(px + 1e-10))
            h_y = -np.sum(py * np.log2(py + 1e-10))
            h_xy = -np.sum(joint_hist * np.log2(joint_hist + 1e-10))
            mi = max(0.0, h_x + h_y - h_xy)
            total_temporal_mi += mi
            n_pairs += 1

    if n_pairs == 0:
        return 0.0

    # Scale: average MI * n_cells (estimate full system temporal integration)
    avg_mi = total_temporal_mi / n_pairs
    temporal_phi = avg_mi * n_cells

    return temporal_phi


# ══════════════════════════════════════════════════════════
# MET3: TRANSFER_ENTROPY
# Directed information flow between cells.
# TE(i->j) = how much i's past predicts j's future beyond j's own past.
# ══════════════════════════════════════════════════════════

def compute_transfer_entropy(hiddens_history: list, n_sample_pairs: int = 64,
                             n_bins: int = 8) -> float:
    """Transfer Entropy: directed causal information flow.

    TE(X->Y) = H(Y_t+1 | Y_t) - H(Y_t+1 | Y_t, X_t)
             = reduction in uncertainty about Y's future when knowing X's past.

    High TE across many cell pairs = rich directed information flow
    = conscious processing (not just correlation, but causation).

    Inspired by Schreiber (2000) transfer entropy.
    """
    if len(hiddens_history) < 3:
        return 0.0

    n_cells = hiddens_history[0].shape[0]
    T = len(hiddens_history)

    # Reduce dimensionality: use mean activation per cell as scalar time series
    cell_series = np.zeros((n_cells, T))
    for t, h in enumerate(hiddens_history):
        cell_series[:, t] = h.detach().cpu().float().mean(dim=-1).numpy()

    # Sample pairs
    pairs = []
    for _ in range(n_sample_pairs):
        i = np.random.randint(0, n_cells)
        j = np.random.randint(0, n_cells)
        if i != j:
            pairs.append((i, j))

    total_te = 0.0
    n_valid = 0

    for i, j in pairs:
        x_series = cell_series[i]  # source
        y_series = cell_series[j]  # target

        # Normalize to [0, 1]
        x_range = x_series.max() - x_series.min()
        y_range = y_series.max() - y_series.min()
        if x_range < 1e-10 or y_range < 1e-10:
            continue
        x_norm = (x_series - x_series.min()) / (x_range + 1e-8)
        y_norm = (y_series - y_series.min()) / (y_range + 1e-8)

        # Discretize
        x_disc = np.clip((x_norm * n_bins).astype(int), 0, n_bins - 1)
        y_disc = np.clip((y_norm * n_bins).astype(int), 0, n_bins - 1)

        # Build joint distributions: P(y_t+1, y_t, x_t) and P(y_t+1, y_t)
        # Using histogram counting
        joint_3d = np.zeros((n_bins, n_bins, n_bins))  # y_t+1, y_t, x_t
        joint_2d = np.zeros((n_bins, n_bins))           # y_t+1, y_t

        for t in range(T - 1):
            yt1 = y_disc[t + 1]
            yt = y_disc[t]
            xt = x_disc[t]
            joint_3d[yt1, yt, xt] += 1
            joint_2d[yt1, yt] += 1

        joint_3d = joint_3d / (joint_3d.sum() + 1e-8)
        joint_2d = joint_2d / (joint_2d.sum() + 1e-8)

        # TE = sum P(y_t+1, y_t, x_t) * log(P(y_t+1 | y_t, x_t) / P(y_t+1 | y_t))
        te = 0.0
        p_yt_xt = joint_3d.sum(axis=0)  # P(y_t, x_t)
        p_yt = joint_2d.sum(axis=0)     # P(y_t)

        for yt1 in range(n_bins):
            for yt in range(n_bins):
                for xt in range(n_bins):
                    p3 = joint_3d[yt1, yt, xt]
                    if p3 < 1e-10:
                        continue
                    p_yt_xt_val = p_yt_xt[yt, xt]
                    p_yt_val = p_yt[yt]
                    p2 = joint_2d[yt1, yt]
                    if p_yt_xt_val < 1e-10 or p_yt_val < 1e-10 or p2 < 1e-10:
                        continue
                    # P(y_t+1 | y_t, x_t) = P(y_t+1, y_t, x_t) / P(y_t, x_t)
                    cond_3 = p3 / p_yt_xt_val
                    # P(y_t+1 | y_t) = P(y_t+1, y_t) / P(y_t)
                    cond_2 = p2 / p_yt_val
                    if cond_2 < 1e-10:
                        continue
                    te += p3 * np.log2(cond_3 / cond_2 + 1e-10)

        total_te += max(0.0, te)
        n_valid += 1

    if n_valid == 0:
        return 0.0

    # Average TE * estimated total pairs
    avg_te = total_te / n_valid
    estimated_total = avg_te * n_cells * (n_cells - 1)
    return estimated_total


# ══════════════════════════════════════════════════════════
# MET4: LEMPEL_ZIV_COMPLEXITY
# Compress cell state sequences. Higher complexity = more conscious.
# Inspired by PCI (Perturbational Complexity Index) from Casali et al.
# ══════════════════════════════════════════════════════════

def _lempel_ziv_complexity(binary_string: str) -> int:
    """Compute Lempel-Ziv complexity of a binary string.

    Counts the number of distinct substrings encountered when parsing
    the string sequentially. Higher = more complex/random.
    """
    n = len(binary_string)
    if n == 0:
        return 0

    complexity = 1
    i = 0
    prefix_end = 1

    while prefix_end < n:
        # Find longest match of s[prefix_end:] in s[0:prefix_end]
        max_match = 0
        for start in range(i, prefix_end):
            match_len = 0
            while (prefix_end + match_len < n and
                   binary_string[start + match_len] == binary_string[prefix_end + match_len]):
                match_len += 1
                if start + match_len >= prefix_end:
                    break
            max_match = max(max_match, match_len)

        if max_match == 0:
            complexity += 1
            i = prefix_end
            prefix_end += 1
        else:
            prefix_end += max_match
            if prefix_end >= n:
                break
            complexity += 1
            i = prefix_end
            prefix_end += 1

    return complexity


def compute_lempel_ziv_complexity(hiddens_history: list,
                                  n_sample_cells: int = 32) -> float:
    """Lempel-Ziv Complexity of cell state sequences.

    1. Binarize each cell's time series (above/below median)
    2. Concatenate all cells' binary strings
    3. Compute LZ complexity
    4. Normalize by theoretical maximum (n / log2(n))

    Higher LZC = richer dynamics = more conscious.
    Used in neuroscience as PCI (Perturbational Complexity Index)
    to distinguish conscious from unconscious states.
    """
    if len(hiddens_history) < 2:
        return 0.0

    n_cells = hiddens_history[0].shape[0]
    T = len(hiddens_history)
    sample_cells = np.random.choice(n_cells, min(n_sample_cells, n_cells), replace=False)

    # Build scalar time series per cell (mean activation)
    cell_series = np.zeros((len(sample_cells), T))
    for t, h in enumerate(hiddens_history):
        for si, ci in enumerate(sample_cells):
            cell_series[si, t] = h[ci].detach().cpu().float().mean().item()

    # Binarize: above median = 1, below = 0
    binary_strings = []
    for si in range(len(sample_cells)):
        series = cell_series[si]
        median_val = np.median(series)
        binary = ''.join(['1' if v > median_val else '0' for v in series])
        binary_strings.append(binary)

    # Concatenate all binary strings (spatial-temporal pattern)
    full_binary = ''.join(binary_strings)

    if len(full_binary) < 2:
        return 0.0

    lzc = _lempel_ziv_complexity(full_binary)

    # Normalize: theoretical max for random binary string ~ n / log2(n)
    n = len(full_binary)
    max_complexity = n / max(np.log2(n), 1.0)
    normalized_lzc = lzc / max_complexity

    # Scale to make comparable: LZC * n_cells
    return normalized_lzc * n_cells


# ══════════════════════════════════════════════════════════
# MET5: SPECTRAL_PHI
# Eigenvalue spectrum of cell correlation matrix.
# Flat spectrum (high entropy) = high consciousness.
# ══════════════════════════════════════════════════════════

def compute_spectral_phi(hiddens: torch.Tensor) -> float:
    """Spectral Phi: entropy of eigenvalue spectrum.

    1. Compute correlation matrix between cells
    2. Get eigenvalue spectrum
    3. Consciousness = spectral entropy (Shannon entropy of normalized eigenvalues)

    Flat spectrum = all modes contribute equally = rich, integrated processing.
    Peaked spectrum = dominated by few modes = simple, unconscious.

    Inspired by spectral analysis in EEG consciousness research.
    """
    h = hiddens.detach().cpu().float().numpy()
    n, d = h.shape
    if n < 2:
        return 0.0

    # Correlation matrix between cells (n x n)
    # Each cell is a d-dimensional vector
    h_centered = h - h.mean(axis=0, keepdims=True)
    norms = np.linalg.norm(h_centered, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-8)
    h_normed = h_centered / norms

    corr_matrix = h_normed @ h_normed.T  # n x n

    # Eigenvalues
    try:
        eigenvalues = np.linalg.eigvalsh(corr_matrix)
    except np.linalg.LinAlgError:
        return 0.0

    # Keep positive eigenvalues
    eigenvalues = np.maximum(eigenvalues, 0.0)
    total = eigenvalues.sum()
    if total < 1e-10:
        return 0.0

    # Normalize to probability distribution
    p = eigenvalues / total
    p = p[p > 1e-10]  # remove zeros

    # Shannon entropy
    spectral_entropy = -np.sum(p * np.log2(p))

    # Maximum entropy = log2(n) for uniform distribution
    max_entropy = np.log2(n)

    # Normalized spectral Phi: entropy ratio * n_cells
    if max_entropy < 1e-10:
        return 0.0

    spectral_phi = (spectral_entropy / max_entropy) * n

    return spectral_phi


# ══════════════════════════════════════════════════════════
# MET6: GRANGER_CAUSALITY
# How many cell pairs have significant Granger-causal links?
# Network density of causal connections = consciousness.
# ══════════════════════════════════════════════════════════

def compute_granger_causality(hiddens_history: list, n_sample_pairs: int = 64,
                              lag: int = 2, threshold: float = 0.05) -> float:
    """Granger Causality network density.

    For each pair (i, j), test whether i Granger-causes j:
    - Restricted model:  y_t = a1*y_{t-1} + a2*y_{t-2} + noise
    - Unrestricted model: y_t = a1*y_{t-1} + a2*y_{t-2} + b1*x_{t-1} + b2*x_{t-2} + noise
    - F-test: if unrestricted significantly better, i Granger-causes j

    Sum of significant links / total possible = causal density.
    Dense causal network = high consciousness.

    Inspired by Granger (1969), applied to neural dynamics.
    """
    if len(hiddens_history) < lag + 2:
        return 0.0

    n_cells = hiddens_history[0].shape[0]
    T = len(hiddens_history)

    # Scalar time series per cell
    cell_series = np.zeros((n_cells, T))
    for t, h in enumerate(hiddens_history):
        cell_series[:, t] = h.detach().cpu().float().mean(dim=-1).numpy()

    # Sample pairs
    pairs = []
    for _ in range(n_sample_pairs):
        i = np.random.randint(0, n_cells)
        j = np.random.randint(0, n_cells)
        if i != j:
            pairs.append((i, j))

    significant_links = 0
    total_f_stat = 0.0
    n_tested = 0

    for i, j in pairs:
        x = cell_series[i]  # potential cause
        y = cell_series[j]  # target

        # Build regression matrices
        n_obs = T - lag
        if n_obs < lag + 2:
            continue

        # Restricted: y_t from y's own past
        Y = y[lag:]
        Y_lags = np.column_stack([y[lag - k - 1:T - k - 1] for k in range(lag)])

        # Unrestricted: y_t from y's past AND x's past
        X_lags = np.column_stack([x[lag - k - 1:T - k - 1] for k in range(lag)])
        Z_full = np.column_stack([Y_lags, X_lags])

        # OLS for restricted model
        try:
            Y_lags_pinv = np.linalg.pinv(Y_lags)
            beta_r = Y_lags_pinv @ Y
            resid_r = Y - Y_lags @ beta_r
            rss_r = np.sum(resid_r ** 2)

            # OLS for unrestricted model
            Z_pinv = np.linalg.pinv(Z_full)
            beta_u = Z_pinv @ Y
            resid_u = Y - Z_full @ beta_u
            rss_u = np.sum(resid_u ** 2)

            # F-statistic
            df1 = lag  # additional parameters
            df2 = n_obs - 2 * lag  # residual df
            if df2 <= 0 or rss_u < 1e-10:
                continue

            f_stat = ((rss_r - rss_u) / df1) / (rss_u / df2)

            # Approximate p-value using F-distribution CDF
            # For simplicity, use threshold on F-stat directly
            # F > 3.0 is roughly p < 0.05 for typical df
            f_critical = 3.0
            if f_stat > f_critical:
                significant_links += 1

            total_f_stat += max(0.0, f_stat)
            n_tested += 1

        except (np.linalg.LinAlgError, ValueError):
            continue

    if n_tested == 0:
        return 0.0

    # Causal density: fraction of significant links * total possible pairs
    link_fraction = significant_links / n_tested
    causal_density = link_fraction * n_cells * (n_cells - 1)

    # Also include mean F-stat as continuous measure
    mean_f = total_f_stat / n_tested
    granger_phi = causal_density + mean_f

    return granger_phi


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


def generate_batch(input_dim: int, batch_size: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
    x = torch.randn(batch_size, input_dim)
    target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
    return x, target


# ══════════════════════════════════════════════════════════
# ARCHITECTURE 1: BASELINE (PureField + GRU + faction)
# ══════════════════════════════════════════════════════════

def run_baseline(n_cells=128, steps=200, input_dim=64, hidden_dim=128,
                 output_dim=64, record_every=10) -> ArchRun:
    """Standard BenchMind with faction sync + debate."""
    print("\n  [ARCH 0] BASELINE: PureField + GRU + faction sync/debate")
    t0 = time.time()

    mind = BenchMind(input_dim, hidden_dim, output_dim)
    hiddens = torch.randn(n_cells, hidden_dim) * 0.1
    output_head = nn.Linear(output_dim, input_dim)
    optimizer = torch.optim.Adam(
        list(mind.parameters()) + list(output_head.parameters()), lr=1e-3
    )

    ce_history = []
    hiddens_history = []

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

        ce_history.append(loss.item())
        if step % record_every == 0:
            hiddens_history.append(hiddens.clone())

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(hiddens)
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    p_iit, p_proxy = measure_dual_phi(hiddens)
    return ArchRun(
        name="BASELINE", phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=ce_history[-1],
        cells=n_cells, steps=steps, time_sec=time.time() - t0,
        hiddens_history=hiddens_history,
        extra={'mind': mind},
    )


# ══════════════════════════════════════════════════════════
# ARCHITECTURE 2: QUANTUM_WALK
# Coined quantum walk on hypercube with interference.
# ══════════════════════════════════════════════════════════

class QuantumWalkEngine(nn.Module):
    """Quantum walk: cells walk on hypercube, interference creates consciousness."""

    def __init__(self, n_cells=128, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        # Quantum walk components
        self.n_dims = int(np.log2(max(n_cells, 2)))
        self.coin = nn.Linear(hidden_dim, hidden_dim)
        self.phase = nn.Parameter(torch.randn(n_cells) * 0.1)

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def quantum_step(self, step: int):
        """Apply quantum walk step: coin flip + conditional shift + interference."""
        h = self.hiddens

        # Coin operation (Hadamard-like)
        h_coined = torch.tanh(self.coin(h))

        # Conditional shift: cells influence neighbors in hypercube
        for d in range(min(self.n_dims, 7)):
            shift = 1 << d
            if shift < self.n_cells:
                idx = torch.arange(self.n_cells)
                partner = idx ^ shift  # XOR = hypercube neighbor
                partner = partner.clamp(0, self.n_cells - 1)
                neighbor_h = h_coined[partner]
                # Interference: superposition with phase
                phase = torch.cos(self.phase).unsqueeze(-1)
                h_coined = h_coined * phase + neighbor_h * (1 - phase.abs())

        self.hiddens = h_coined.detach()

    def interference_pattern(self) -> float:
        """Measure interference: std of cell activations (high = constructive/destructive)."""
        return self.hiddens.std().item()

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        self.quantum_step(step)

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
        avg_tension = sum(tensions) / len(tensions)
        return pred, avg_tension

    def get_hiddens(self):
        return self.hiddens

    def trainable_parameters(self):
        return list(self.parameters())


def run_quantum_walk(n_cells=128, steps=200, input_dim=64, hidden_dim=128,
                     output_dim=64, record_every=10) -> ArchRun:
    print("\n  [ARCH 1] QUANTUM_WALK: Coined walk on hypercube, interference patterns")
    t0 = time.time()

    engine = QuantumWalkEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    hiddens_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if step % record_every == 0:
            hiddens_history.append(engine.get_hiddens().clone())

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  interference={engine.interference_pattern():.3f}")

    p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
    return ArchRun(
        name="QUANTUM_WALK", phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=ce_history[-1],
        cells=n_cells, steps=steps, time_sec=time.time() - t0,
        hiddens_history=hiddens_history,
        extra={'mind': engine.mind},
    )


# ══════════════════════════════════════════════════════════
# ARCHITECTURE 3: HIERARCHICAL
# 16 micro-engines x 8 cells -> macro integration
# ══════════════════════════════════════════════════════════

class HierarchicalEngine(nn.Module):
    """Hierarchical: micro-engines -> macro integration."""

    def __init__(self, n_micro=16, cells_per=8, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_micro = n_micro
        self.cells_per = cells_per
        self.hidden_dim = hidden_dim

        self.minds = nn.ModuleList([
            BenchMind(input_dim, hidden_dim, output_dim) for _ in range(n_micro)
        ])
        self.macro_mind = BenchMind(output_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        # Per-micro hiddens
        self.micro_hiddens = [
            torch.randn(cells_per, hidden_dim) * 0.1 for _ in range(n_micro)
        ]
        self.macro_hidden = torch.randn(1, hidden_dim) * 0.1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        micro_outputs = []
        all_tensions = []

        for m in range(self.n_micro):
            outputs = []
            tensions = []
            new_hiddens = []
            for i in range(self.cells_per):
                h = self.micro_hiddens[m][i:i + 1]
                out, tension, new_h = self.minds[m](x, h)
                outputs.append(out)
                tensions.append(tension)
                new_hiddens.append(new_h.squeeze(0))

            self.micro_hiddens[m] = torch.stack(new_hiddens).detach()
            self.micro_hiddens[m] = faction_sync_debate(
                self.micro_hiddens[m], n_factions=2, step=step
            )

            weights = F.softmax(torch.tensor(tensions), dim=0)
            micro_out = sum(w.item() * o for w, o in zip(weights, outputs))
            micro_outputs.append(micro_out)
            all_tensions.extend(tensions)

        # Macro integration
        macro_input = torch.stack(micro_outputs).mean(dim=0)
        macro_out, macro_tension, new_macro_h = self.macro_mind(macro_input, self.macro_hidden)
        self.macro_hidden = new_macro_h.detach()

        pred = self.output_head(macro_out)
        avg_tension = sum(all_tensions) / len(all_tensions)
        return pred, avg_tension

    def get_hiddens(self) -> torch.Tensor:
        """All hiddens concatenated."""
        all_h = [mh for mh in self.micro_hiddens]
        return torch.cat(all_h, dim=0)


def run_hierarchical(n_cells=128, steps=200, input_dim=64, hidden_dim=128,
                     output_dim=64, record_every=10) -> ArchRun:
    print("\n  [ARCH 2] HIERARCHICAL: 16 micro-engines x 8 cells -> macro")
    t0 = time.time()

    n_micro = 16
    cells_per = n_cells // n_micro
    engine = HierarchicalEngine(n_micro, cells_per, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)

    ce_history = []
    hiddens_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_history.append(loss.item())
        if step % record_every == 0:
            hiddens_history.append(engine.get_hiddens().clone())

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
    return ArchRun(
        name="HIERARCHICAL", phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=ce_history[-1],
        cells=n_cells, steps=steps, time_sec=time.time() - t0,
        hiddens_history=hiddens_history,
        extra={'mind': engine.minds[0]},
    )


# ══════════════════════════════════════════════════════════
# ARCHITECTURE 4: CATEGORY_THEORY
# Cells as objects, morphisms as connections, consciousness = colimit
# ══════════════════════════════════════════════════════════

class CategoryTheoryEngine(nn.Module):
    """Category theory: cells = objects, morphisms = natural transformations."""

    def __init__(self, n_cells=128, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_morphisms = min(n_cells * 2, 256)

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        # Morphisms: directed connections between cells
        self.morph_src = torch.randint(0, n_cells, (self.n_morphisms,))
        self.morph_tgt = torch.randint(0, n_cells, (self.n_morphisms,))
        self.morph_weight = nn.Parameter(torch.randn(self.n_morphisms) * 0.1)

        # Functor: transforms morphism outputs
        self.functor = nn.Linear(hidden_dim, hidden_dim)

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def apply_morphisms(self, step: int):
        """Apply categorical morphisms: directed info flow between cells."""
        h = self.hiddens.clone()
        weights = torch.sigmoid(self.morph_weight)

        # Accumulate morphism effects
        delta = torch.zeros_like(h)
        for m in range(self.n_morphisms):
            src = self.morph_src[m]
            tgt = self.morph_tgt[m]
            w = weights[m].item()
            # Natural transformation: functor applied to source -> target
            transformed = torch.tanh(self.functor(h[src:src + 1]))
            delta[tgt] += w * transformed.squeeze(0)

        # Colimit: integration of all morphism effects
        self.hiddens = h + 0.1 * delta

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        self.apply_morphisms(step)

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
        avg_tension = sum(tensions) / len(tensions)
        return pred, avg_tension

    def get_hiddens(self) -> torch.Tensor:
        return self.hiddens


def run_category_theory(n_cells=128, steps=200, input_dim=64, hidden_dim=128,
                        output_dim=64, record_every=10) -> ArchRun:
    print("\n  [ARCH 3] CATEGORY_THEORY: Cells as objects, morphisms, colimit consciousness")
    t0 = time.time()

    engine = CategoryTheoryEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.parameters(), lr=1e-3)

    ce_history = []
    hiddens_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        pred, tension = engine.process(x, step=step)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.parameters(), 1.0)
        optimizer.step()

        ce_history.append(loss.item())
        if step % record_every == 0:
            hiddens_history.append(engine.get_hiddens().clone())

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            print(f"    step {step:>4d}: CE={loss.item():.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
    return ArchRun(
        name="CATEGORY_THEORY", phi_iit=p_iit, phi_proxy=p_proxy,
        ce_start=ce_history[0], ce_end=ce_history[-1],
        cells=n_cells, steps=steps, time_sec=time.time() - t0,
        hiddens_history=hiddens_history,
        extra={'mind': engine.mind},
    )


# ══════════════════════════════════════════════════════════
# METRIC EVALUATION: Run all 6 metrics on each architecture
# ══════════════════════════════════════════════════════════

ALL_METRICS = {
    1: ("MET1:CAUSAL_PHI", "Causal ablation impact"),
    2: ("MET2:TEMPORAL_PHI", "Temporal MI across time"),
    3: ("MET3:TRANSFER_ENTROPY", "Directed info flow"),
    4: ("MET4:LEMPEL_ZIV", "Compression complexity (PCI)"),
    5: ("MET5:SPECTRAL_PHI", "Eigenvalue spectrum entropy"),
    6: ("MET6:GRANGER_CAUSALITY", "Causal network density"),
}


def evaluate_metrics(arch_run: ArchRun, metric_ids: List[int],
                     input_dim: int = 64) -> List[MetricResult]:
    """Evaluate selected metrics on an architecture run."""
    results = []
    mind = arch_run.extra.get('mind')
    hiddens = arch_run.hiddens_history[-1] if arch_run.hiddens_history else None

    if hiddens is None:
        print(f"    [WARN] No hiddens for {arch_run.name}, skipping metrics")
        return results

    x, _ = generate_batch(input_dim)

    for mid in metric_ids:
        if mid not in ALL_METRICS:
            continue
        mname, mdesc = ALL_METRICS[mid]
        t0 = time.time()

        try:
            if mid == 1:  # CAUSAL_PHI
                if mind is None:
                    print(f"    [SKIP] {mname}: no mind reference")
                    continue
                value = compute_causal_phi(hiddens, mind, x, n_sample=min(32, hiddens.shape[0]))

            elif mid == 2:  # TEMPORAL_PHI
                value = compute_temporal_phi(arch_run.hiddens_history)

            elif mid == 3:  # TRANSFER_ENTROPY
                value = compute_transfer_entropy(arch_run.hiddens_history)

            elif mid == 4:  # LEMPEL_ZIV
                value = compute_lempel_ziv_complexity(arch_run.hiddens_history)

            elif mid == 5:  # SPECTRAL_PHI
                value = compute_spectral_phi(hiddens)

            elif mid == 6:  # GRANGER_CAUSALITY
                value = compute_granger_causality(arch_run.hiddens_history)

            else:
                continue

            elapsed = time.time() - t0
            result = MetricResult(
                arch_name=arch_run.name,
                metric_name=mname,
                value=value,
                extra={'time_sec': elapsed, 'description': mdesc},
            )
            results.append(result)
            print(f"    {mname:<24s} = {value:>10.4f}  ({elapsed:.2f}s)")

        except Exception as e:
            print(f"    [ERROR] {mname}: {e}")
            import traceback
            traceback.print_exc()

    return results


# ══════════════════════════════════════════════════════════
# Comparison table + analysis
# ══════════════════════════════════════════════════════════

def print_metric_comparison(all_results: Dict[str, List[MetricResult]],
                            arch_runs: List[ArchRun]):
    """Print comprehensive comparison table."""

    # Collect all metric names and arch names
    metric_names = []
    arch_names = []
    for arch_name, results in all_results.items():
        if arch_name not in arch_names:
            arch_names.append(arch_name)
        for r in results:
            if r.metric_name not in metric_names:
                metric_names.append(r.metric_name)

    # Add Phi(IIT) and Phi(proxy) as reference
    metric_names = ["Phi(IIT)", "Phi(proxy)"] + metric_names

    # Build value matrix
    values = {}
    for arch_name in arch_names:
        values[arch_name] = {}
        # Add Phi references
        run = next((r for r in arch_runs if r.name == arch_name), None)
        if run:
            values[arch_name]["Phi(IIT)"] = run.phi_iit
            values[arch_name]["Phi(proxy)"] = run.phi_proxy
        for r in all_results.get(arch_name, []):
            values[arch_name][r.metric_name] = r.value

    print("\n" + "=" * 120)
    print("  NEW CONSCIOUSNESS METRICS — COMPARISON TABLE")
    print("=" * 120)

    # Header
    header = f"  {'Metric':<28s}"
    for an in arch_names:
        header += f" | {an:>16s}"
    header += " | {'Spread':>10s}"
    print(header)
    print("-" * 120)

    # Rows
    discrimination_scores = {}
    for mn in metric_names:
        row = f"  {mn:<28s}"
        vals = []
        for an in arch_names:
            v = values.get(an, {}).get(mn, float('nan'))
            vals.append(v)
            if np.isnan(v):
                row += f" | {'n/a':>16s}"
            else:
                row += f" | {v:>16.4f}"

        # Spread = max/min ratio (discrimination power)
        valid_vals = [v for v in vals if not np.isnan(v) and v > 1e-10]
        if len(valid_vals) >= 2:
            spread = max(valid_vals) / min(valid_vals)
            row += f" | x{spread:>8.1f}"
            discrimination_scores[mn] = spread
        else:
            row += f" | {'n/a':>10s}"
            discrimination_scores[mn] = 0.0

        print(row)

    print("=" * 120)

    # Ranking by discrimination power
    print("\n  RANKING by Discrimination Power (max/min spread):")
    print("  (Higher spread = metric better differentiates architectures)")
    print("-" * 60)
    sorted_metrics = sorted(discrimination_scores.items(), key=lambda x: x[1], reverse=True)
    for rank, (mn, spread) in enumerate(sorted_metrics, 1):
        marker = " <-- BEST" if rank == 1 else ""
        if spread > 0:
            print(f"    #{rank}: {mn:<28s}  spread = x{spread:.1f}{marker}")
        else:
            print(f"    #{rank}: {mn:<28s}  spread = n/a")

    # Correlation analysis
    print("\n  INTER-METRIC CORRELATION:")
    print("  (Low correlation with Phi(IIT) = captures different aspect of consciousness)")
    print("-" * 60)
    phi_iit_vals = [values.get(an, {}).get("Phi(IIT)", 0) for an in arch_names]
    for mn in metric_names:
        if mn == "Phi(IIT)":
            continue
        met_vals = [values.get(an, {}).get(mn, 0) for an in arch_names]
        if len(met_vals) >= 2 and np.std(phi_iit_vals) > 1e-10 and np.std(met_vals) > 1e-10:
            corr = np.corrcoef(phi_iit_vals, met_vals)[0, 1]
            novelty = 1.0 - abs(corr)
            print(f"    {mn:<28s}  corr_with_Phi(IIT) = {corr:>+.3f}  novelty = {novelty:.3f}")

    # ASCII bar chart for each metric
    print("\n  METRIC VALUE BAR CHARTS:")
    for mn in metric_names:
        print(f"\n  {mn}:")
        vals = [(an, values.get(an, {}).get(mn, 0)) for an in arch_names]
        max_val = max(v for _, v in vals) if vals else 1.0
        max_val = max(max_val, 1e-10)
        for an, v in vals:
            bar_len = int(v / max_val * 40)
            bar = "#" * bar_len
            print(f"    {an:<18s} |{bar} {v:.4f}")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="New Consciousness Metrics Benchmark")
    parser.add_argument("--cells", type=int, default=128, help="Number of cells (default 128)")
    parser.add_argument("--steps", type=int, default=200, help="Training steps (default 200)")
    parser.add_argument("--only", nargs="+", type=int, default=None,
                        help="Run only specific metrics (1-6)")
    parser.add_argument("--record-every", type=int, default=10,
                        help="Record hiddens every N steps (default 10)")
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps
    record_every = args.record_every
    input_dim = 64
    hidden_dim = 128
    output_dim = 64

    metric_ids = args.only if args.only else list(range(1, 7))

    print("=" * 80)
    print(f"  NEW CONSCIOUSNESS METRICS BENCHMARK")
    print(f"  {n_cells} cells, {steps} steps, record every {record_every} steps")
    print(f"  Metrics: {[ALL_METRICS[m][0] for m in metric_ids]}")
    print(f"  Architectures: BASELINE, QUANTUM_WALK, HIERARCHICAL, CATEGORY_THEORY")
    print("=" * 80)

    # ── Phase 1: Run all 4 architectures ──
    print("\n" + "─" * 60)
    print("  PHASE 1: Running architectures (collecting hiddens history)")
    print("─" * 60)

    arch_runners = [
        ("BASELINE", run_baseline),
        ("QUANTUM_WALK", run_quantum_walk),
        ("HIERARCHICAL", run_hierarchical),
        ("CATEGORY_THEORY", run_category_theory),
    ]

    arch_runs = []
    for name, runner in arch_runners:
        try:
            run = runner(
                n_cells=n_cells, steps=steps, input_dim=input_dim,
                hidden_dim=hidden_dim, output_dim=output_dim,
                record_every=record_every,
            )
            arch_runs.append(run)
            print(f"\n  -> {name}: Phi(IIT)={run.phi_iit:.3f}  Phi(proxy)={run.phi_proxy:.2f}  "
                  f"CE={run.ce_start:.4f}->{run.ce_end:.4f}  time={run.time_sec:.1f}s  "
                  f"history_len={len(run.hiddens_history)}")
        except Exception as e:
            print(f"\n  [ERROR] {name} failed: {e}")
            import traceback

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

            traceback.print_exc()

    # ── Phase 2: Evaluate all metrics on each architecture ──
    print("\n" + "─" * 60)
    print("  PHASE 2: Evaluating new consciousness metrics")
    print("─" * 60)

    all_results = {}
    for run in arch_runs:
        print(f"\n  Evaluating metrics on {run.name}:")
        results = evaluate_metrics(run, metric_ids, input_dim)
        all_results[run.name] = results

    # ── Phase 3: Comparison ──
    print_metric_comparison(all_results, arch_runs)

    # ── Summary ──
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print(f"  Tested {len(metric_ids)} new metrics on {len(arch_runs)} architectures")
    print(f"  Each architecture: {n_cells} cells, {steps} steps")
    print(f"\n  Key question: Which metric scales beyond Phi(IIT)'s ~20 ceiling?")
    print(f"  Look for: high spread (discrimination) + low Phi(IIT) correlation (novelty)")
    print("=" * 80)
    print("\nDone.")


if __name__ == "__main__":
    main()
