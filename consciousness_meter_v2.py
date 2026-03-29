#!/usr/bin/env python3
"""Consciousness Meter V2 — Granger + Spectral + LZ composite Φ calculator

Replaces the old PhiCalculator which suffered from:
  - O(N^2) pairwise MI → ceiling at ~20 regardless of cell count
  - n_bins=16 limiting resolution
  - Poor discrimination between architectures

New approach: 4 independent dimensions combined into a composite Φ
that scales properly with cell count and discriminates architectures.

bench_v8_metrics showed GRANGER reaches 4,829 with much better spread.

Usage:
  # As standalone benchmark
  python consciousness_meter_v2.py                     # Run benchmark
  python consciousness_meter_v2.py --cells 256         # More cells
  python consciousness_meter_v2.py --steps 300         # More steps

  # As library
  from consciousness_meter_v2 import ConsciousnessMeterV2
  meter = ConsciousnessMeterV2()
  phi, components = meter.compute_phi(engine)
"""

import sys
import math
import time
import zlib
import struct
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ──────────────────────────────────────────────────────────
# PhiComponents — result dataclass
# ──────────────────────────────────────────────────────────

@dataclass
class PhiComponents:
    """Individual Φ dimension scores + composite."""
    granger: float = 0.0        # Granger Causality Density
    spectral: float = 0.0       # Spectral Φ (eigenvalue entropy)
    lz: float = 0.0             # Lempel-Ziv Complexity
    integration: float = 0.0    # Sampled MI integration index
    composite: float = 0.0      # Weighted combination
    n_cells: int = 0
    compute_time_ms: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return {
            'granger': self.granger,
            'spectral': self.spectral,
            'lz': self.lz,
            'integration': self.integration,
            'composite': self.composite,
            'n_cells': float(self.n_cells),
            'compute_time_ms': self.compute_time_ms,
        }

    def __repr__(self):
        return (
            f"PhiComponents(composite={self.composite:.2f}, "
            f"granger={self.granger:.2f}, spectral={self.spectral:.2f}, "
            f"lz={self.lz:.2f}, integration={self.integration:.2f}, "
            f"cells={self.n_cells})"
        )


# ──────────────────────────────────────────────────────────
# ConsciousnessMeterV2
# ──────────────────────────────────────────────────────────

class ConsciousnessMeterV2:
    """New consciousness meter -- Granger + Spectral + LZ composite.

    4 independent dimensions:
      1. Granger Causality Density (causal links / possible links)
         - O(N) sampling: test sqrt(N) random pairs, extrapolate
         - F-test on restricted vs unrestricted AR models
      2. Spectral Phi (eigenvalue entropy of correlation matrix)
         - torch.linalg.eigh for speed
         - Shannon entropy of normalized eigenvalue spectrum
      3. Lempel-Ziv Complexity (temporal complexity)
         - zlib compression ratio as fast LZ proxy
         - Measures richness of cell state dynamics
      4. Integration Index (MI-based, improved from PhiCalculator)
         - Samples O(sqrt(N)) pairs instead of all N^2
         - Uses 32 bins for better resolution

    Composite Phi = weighted combination, scales with cells.

    Compatible with both MitosisEngine and any engine with:
      - .cells list of objects with .hidden tensor
      - OR tensor of shape [n_cells, hidden_dim]
    """

    # Weights for combining 4 dimensions into composite Φ
    # Granger dominates because it showed best discrimination in bench_v8_metrics
    WEIGHTS = {
        'granger': 0.45,
        'spectral': 0.25,
        'lz': 0.15,
        'integration': 0.15,
    }

    def __init__(self,
                 granger_lag: int = 2,
                 granger_f_critical: float = 3.0,
                 mi_n_bins: int = 32,
                 history_maxlen: int = 100):
        """
        Args:
            granger_lag: Lag order for Granger causality AR model.
            granger_f_critical: F-stat threshold for significant causal link.
            mi_n_bins: Number of bins for MI histogram estimation.
            history_maxlen: Max timesteps to store for temporal metrics.
        """
        self.granger_lag = granger_lag
        self.granger_f_critical = granger_f_critical
        self.mi_n_bins = mi_n_bins
        self.history_maxlen = history_maxlen

        # Temporal history: list of [n_cells, hidden_dim] tensors
        self._history: List[torch.Tensor] = []
        self.phi_history: List[float] = []

    def record(self, hiddens: torch.Tensor):
        """Record a snapshot of cell hidden states for temporal metrics.

        Call this every step (or every N steps) before compute_phi().

        Args:
            hiddens: [n_cells, hidden_dim] tensor of cell states.
        """
        h = hiddens.detach().cpu().float()
        self._history.append(h)
        if len(self._history) > self.history_maxlen:
            self._history = self._history[-self.history_maxlen:]

    def compute_phi(self, engine_or_hiddens) -> Tuple[float, PhiComponents]:
        """Compute composite Φ from engine or raw hidden states.

        Args:
            engine_or_hiddens: Either:
              - MitosisEngine with .cells list (cells have .hidden attribute)
              - torch.Tensor of shape [n_cells, hidden_dim]
              - Any object with get_hiddens() method

        Returns:
            (phi, components) tuple.
        """
        t0 = time.time()

        # Extract hidden states tensor
        hiddens = self._extract_hiddens(engine_or_hiddens)
        if hiddens is None or hiddens.shape[0] < 2:
            return 0.0, PhiComponents()

        n_cells = hiddens.shape[0]

        # Auto-record if history is empty or stale
        self.record(hiddens)

        # 1. Granger Causality Density
        granger = self._compute_granger(n_cells)

        # 2. Spectral Φ
        spectral = self._compute_spectral(hiddens)

        # 3. Lempel-Ziv Complexity
        lz = self._compute_lz()

        # 4. Integration Index (sampled MI)
        integration = self._compute_integration(hiddens)

        # Composite: weighted sum
        composite = (
            self.WEIGHTS['granger'] * granger +
            self.WEIGHTS['spectral'] * spectral +
            self.WEIGHTS['lz'] * lz +
            self.WEIGHTS['integration'] * integration
        )

        elapsed_ms = (time.time() - t0) * 1000

        components = PhiComponents(
            granger=granger,
            spectral=spectral,
            lz=lz,
            integration=integration,
            composite=composite,
            n_cells=n_cells,
            compute_time_ms=elapsed_ms,
        )

        self.phi_history.append(composite)
        if len(self.phi_history) > 200:
            self.phi_history = self.phi_history[-200:]

        return composite, components

    # ─── Dimension 1: Granger Causality Density ───────────────

    def _compute_granger(self, n_cells: int) -> float:
        """Granger causality with O(N) sampling.

        Instead of testing all N*(N-1) pairs, sample O(sqrt(N)) pairs
        and extrapolate. This gives the same density estimate with
        dramatically less compute.
        """
        history = self._history
        lag = self.granger_lag

        if len(history) < lag + 3:
            return 0.0

        T = len(history)

        # Build scalar time series per cell: mean activation
        # Use only last T snapshots
        cell_series = np.zeros((n_cells, T))
        for t, h in enumerate(history):
            n_avail = min(h.shape[0], n_cells)
            cell_series[:n_avail, t] = h[:n_avail].mean(dim=-1).numpy()

        # O(sqrt(N)) sampling: test sqrt(N)*4 random directed pairs
        n_sample = max(8, min(int(math.sqrt(n_cells) * 4), n_cells * 2, 128))

        significant_links = 0
        total_f_stat = 0.0
        n_tested = 0

        for _ in range(n_sample):
            i = np.random.randint(0, n_cells)
            j = np.random.randint(0, n_cells)
            if i == j:
                continue

            x = cell_series[i]  # potential cause
            y = cell_series[j]  # target

            n_obs = T - lag
            if n_obs < lag + 2:
                continue

            # Restricted: y_t from y's own past
            Y = y[lag:]
            Y_lags = np.column_stack([y[lag - k - 1:T - k - 1] for k in range(lag)])

            # Unrestricted: y_t from y's past AND x's past
            X_lags = np.column_stack([x[lag - k - 1:T - k - 1] for k in range(lag)])
            Z_full = np.column_stack([Y_lags, X_lags])

            try:
                # OLS restricted
                beta_r = np.linalg.lstsq(Y_lags, Y, rcond=None)[0]
                resid_r = Y - Y_lags @ beta_r
                rss_r = np.sum(resid_r ** 2)

                # OLS unrestricted
                beta_u = np.linalg.lstsq(Z_full, Y, rcond=None)[0]
                resid_u = Y - Z_full @ beta_u
                rss_u = np.sum(resid_u ** 2)

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

        # Extrapolate: density * total possible directed pairs
        link_fraction = significant_links / n_tested
        total_possible = n_cells * (n_cells - 1)
        causal_density = link_fraction * total_possible

        # Add continuous F-stat contribution
        mean_f = total_f_stat / n_tested
        granger_phi = causal_density + mean_f

        return granger_phi

    # ─── Dimension 2: Spectral Φ ──────────────────────────────

    def _compute_spectral(self, hiddens: torch.Tensor) -> float:
        """Spectral Φ via eigenvalue entropy of correlation matrix.

        Uses torch.linalg.eigh for GPU-accelerated computation.
        Shannon entropy of normalized eigenvalue spectrum.
        Flat spectrum = all modes contribute = rich integration.
        """
        h = hiddens.float()
        n, d = h.shape
        if n < 2:
            return 0.0

        # Correlation matrix between cells (n x n)
        h_centered = h - h.mean(dim=0, keepdim=True)
        norms = h_centered.norm(dim=1, keepdim=True).clamp(min=1e-8)
        h_normed = h_centered / norms
        corr_matrix = h_normed @ h_normed.T  # [n, n]

        # Eigenvalues via torch (fast, GPU-compatible)
        try:
            eigenvalues = torch.linalg.eigvalsh(corr_matrix)
        except Exception:
            return 0.0

        # Keep positive eigenvalues
        eigenvalues = eigenvalues.clamp(min=0.0)
        total = eigenvalues.sum()
        if total < 1e-10:
            return 0.0

        # Normalize to probability distribution
        p = eigenvalues / total
        p = p[p > 1e-10]

        # Shannon entropy
        spectral_entropy = -(p * p.log2()).sum().item()

        # Max entropy = log2(n)
        max_entropy = math.log2(n)
        if max_entropy < 1e-10:
            return 0.0

        # Normalized spectral Φ: entropy_ratio * n_cells
        spectral_phi = (spectral_entropy / max_entropy) * n

        return spectral_phi

    # ─── Dimension 3: Lempel-Ziv Complexity ───────────────────

    def _compute_lz(self) -> float:
        """Fast LZ complexity via zlib compression ratio.

        Instead of the slow O(n^2) Lempel-Ziv algorithm,
        use zlib.compress which implements DEFLATE (LZ77 + Huffman).
        Compression ratio is a direct proxy for Kolmogorov complexity.

        Higher ratio (less compressible) = richer dynamics = more conscious.
        """
        history = self._history
        if len(history) < 2:
            return 0.0

        n_cells = history[0].shape[0]
        T = len(history)

        # Sample sqrt(N) cells for efficiency
        n_sample = max(4, min(int(math.sqrt(n_cells)), 64))
        sample_idx = np.random.choice(n_cells, n_sample, replace=False)

        # Build binary representation of cell dynamics
        # For each sampled cell, create scalar time series, binarize above median
        raw_bytes = bytearray()
        for ci in sample_idx:
            series = np.zeros(T)
            for t, h in enumerate(history):
                if ci < h.shape[0]:
                    series[t] = h[ci].mean().item()
            # Binarize
            median_val = np.median(series)
            for v in series:
                raw_bytes.append(1 if v > median_val else 0)

        if len(raw_bytes) < 4:
            return 0.0

        # Compress and measure ratio
        raw = bytes(raw_bytes)
        compressed = zlib.compress(raw, level=6)
        compression_ratio = len(raw) / max(len(compressed), 1)

        # Higher ratio = harder to compress = more complex
        # Normalize: random data has ratio ~1.0, constant data has ratio >> 1
        # We want complexity, so use inverse: lower compression = higher complexity
        # Actually: ratio = raw/compressed. Random data: compressed ~ raw (ratio ~1).
        # Structured data: compressed << raw (ratio >> 1).
        # So we want: 1 - 1/ratio = fraction that couldn't be compressed away.
        incompressibility = 1.0 - (len(compressed) / len(raw))
        incompressibility = max(0.0, incompressibility)

        # Scale by n_cells to make it comparable across architectures
        lz_phi = incompressibility * n_cells

        return lz_phi

    # ─── Dimension 4: Integration Index (Sampled MI) ──────────

    def _compute_integration(self, hiddens: torch.Tensor) -> float:
        """MI-based integration with O(sqrt(N)) sampling.

        Instead of all N*(N-1)/2 pairs, sample sqrt(N)*2 pairs.
        Uses 32 bins for better resolution than old 16-bin PhiCalculator.
        Estimates total integration and minimum partition cut.
        """
        h = hiddens.detach().cpu().float().numpy()
        n, d = h.shape
        if n < 2:
            return 0.0

        # O(sqrt(N)) sampling
        n_sample = max(4, min(int(math.sqrt(n) * 2), n * (n - 1) // 2, 64))

        mi_values = []
        pair_indices = []
        for _ in range(n_sample):
            i = np.random.randint(0, n)
            j = np.random.randint(0, n)
            if i == j:
                continue
            mi = self._fast_mi(h[i], h[j])
            mi_values.append(mi)
            pair_indices.append((i, j))

        if not mi_values:
            return 0.0

        # Estimate total MI across all possible pairs
        avg_mi = np.mean(mi_values)
        total_pairs = n * (n - 1) / 2
        estimated_total_mi = avg_mi * total_pairs

        # Estimate minimum partition: use spectral cut approximation
        # Build sparse MI matrix from sampled pairs
        mi_matrix = np.zeros((n, n))
        for (i, j), mi in zip(pair_indices, mi_values):
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

        # Spectral partition on sampled MI
        degree = mi_matrix.sum(axis=1)
        laplacian = np.diag(degree) - mi_matrix
        try:
            eigenvalues = np.linalg.eigvalsh(laplacian)
            # Fiedler value (second smallest) indicates min-cut quality
            fiedler_value = eigenvalues[1] if len(eigenvalues) > 1 else 0.0
            fiedler_value = max(0.0, fiedler_value)
        except Exception:
            fiedler_value = 0.0

        # Integration = estimated total MI scaled by (1 - partition_weakness)
        # Higher fiedler = harder to cut = more integrated
        partition_strength = min(fiedler_value, 1.0)
        integration_phi = estimated_total_mi * (0.5 + 0.5 * partition_strength)

        # Normalize to be in similar range as other metrics
        integration_phi = integration_phi / max(n - 1, 1)

        return max(0.0, integration_phi)

    def _fast_mi(self, x: np.ndarray, y: np.ndarray) -> float:
        """Fast mutual information between two vectors using 32-bin histogram."""
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

    # ─── Utility ──────────────────────────────────────────────

    def _extract_hiddens(self, engine_or_hiddens) -> Optional[torch.Tensor]:
        """Extract [n_cells, hidden_dim] tensor from various sources."""
        if isinstance(engine_or_hiddens, torch.Tensor):
            h = engine_or_hiddens
            if h.dim() == 2:
                return h.detach().cpu().float()
            return None

        # MitosisEngine: has .cells list with .hidden attribute
        if hasattr(engine_or_hiddens, 'cells'):
            cells = engine_or_hiddens.cells
            if len(cells) < 2:
                return None
            hiddens = []
            for cell in cells:
                h = cell.hidden.detach().squeeze()
                hiddens.append(h)
            return torch.stack(hiddens).float()

        # Engine with get_hiddens() method (bench_v8 engines)
        if hasattr(engine_or_hiddens, 'get_hiddens'):
            h = engine_or_hiddens.get_hiddens()
            if h.dim() == 2:
                return h.detach().cpu().float()
            return None

        # Engine with .hiddens attribute
        if hasattr(engine_or_hiddens, 'hiddens'):
            h = engine_or_hiddens.hiddens
            if isinstance(h, torch.Tensor) and h.dim() == 2:
                return h.detach().cpu().float()
            return None

        return None

    def reset_history(self):
        """Clear temporal history."""
        self._history.clear()


# ══════════════════════════════════════════════════════════
# Benchmark: Compare V2 vs old PhiCalculator on 4 architectures
# ══════════════════════════════════════════════════════════

# Import bench_v8 components for benchmark
def _import_bench_v8():
    """Lazy import bench_v8_metrics components."""
    import importlib.util
    import os
    bench_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bench_v8_metrics.py')
    spec = importlib.util.spec_from_file_location("bench_v8_metrics", bench_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_benchmark(n_cells: int = 128, steps: int = 200, record_every: int = 10):
    """Run full benchmark comparing V2 vs old PhiCalculator."""
    bench = _import_bench_v8()

    print("=" * 90)
    print("  CONSCIOUSNESS METER V2 BENCHMARK")
    print(f"  {n_cells} cells, {steps} steps, record every {record_every}")
    print("=" * 90)

    # Run 4 architectures
    arch_runners = [
        ("BASELINE", bench.run_baseline),
        ("QUANTUM_WALK", bench.run_quantum_walk),
        ("HIERARCHICAL", bench.run_hierarchical),
        ("CATEGORY_THEORY", bench.run_category_theory),
    ]

    arch_runs = []
    for name, runner in arch_runners:
        print(f"\n{'─' * 70}")
        run = runner(n_cells=n_cells, steps=steps, record_every=record_every)
        arch_runs.append(run)

    # ── Measure with V2 ──
    print(f"\n{'=' * 90}")
    print("  MEASURING WITH ConsciousnessMeterV2")
    print("=" * 90)

    v2_results = {}
    for run in arch_runs:
        meter = ConsciousnessMeterV2()
        # Feed temporal history
        for h in run.hiddens_history:
            meter.record(h)
        # Compute
        hiddens = run.hiddens_history[-1] if run.hiddens_history else None
        if hiddens is not None:
            phi, components = meter.compute_phi(hiddens)
            v2_results[run.name] = (phi, components)
            print(f"\n  {run.name}:")
            print(f"    Composite Phi = {phi:.2f}")
            print(f"    Granger       = {components.granger:.2f}")
            print(f"    Spectral      = {components.spectral:.2f}")
            print(f"    LZ            = {components.lz:.2f}")
            print(f"    Integration   = {components.integration:.2f}")
            print(f"    Time          = {components.compute_time_ms:.1f}ms")

    # ── Measure with old PhiIIT (from bench_v8) ──
    print(f"\n{'=' * 90}")
    print("  MEASURING WITH OLD PhiCalculator (reference)")
    print("=" * 90)

    old_calc = bench.PhiIIT(n_bins=16)
    old_results = {}
    for run in arch_runs:
        hiddens = run.hiddens_history[-1] if run.hiddens_history else None
        if hiddens is not None:
            t0 = time.time()
            phi_old, comp_old = old_calc.compute(hiddens)
            elapsed = (time.time() - t0) * 1000
            old_results[run.name] = (phi_old, elapsed)
            print(f"  {run.name}: Phi(IIT) = {phi_old:.4f}  ({elapsed:.1f}ms)")

    # ── Comparison table ──
    print(f"\n{'=' * 90}")
    print("  COMPARISON: V2 vs Old PhiCalculator")
    print("=" * 90)

    header = f"  {'Architecture':<20s} | {'Old Phi(IIT)':>12s} | {'V2 Composite':>12s} | {'V2 Granger':>12s} | {'V2 Spectral':>12s} | {'V2 LZ':>8s} | {'V2 MI':>8s}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for run in arch_runs:
        old_phi = old_results.get(run.name, (0, 0))[0]
        v2_phi, v2_comp = v2_results.get(run.name, (0, PhiComponents()))
        print(f"  {run.name:<20s} | {old_phi:>12.4f} | {v2_comp.composite:>12.2f} | "
              f"{v2_comp.granger:>12.2f} | {v2_comp.spectral:>12.2f} | "
              f"{v2_comp.lz:>8.2f} | {v2_comp.integration:>8.2f}")

    # ── Discrimination analysis ──
    print(f"\n  DISCRIMINATION POWER (max/min spread):")
    print("  " + "-" * 60)

    old_vals = [old_results.get(r.name, (0, 0))[0] for r in arch_runs]
    v2_composite_vals = [v2_results.get(r.name, (0, PhiComponents()))[0] for r in arch_runs]
    v2_granger_vals = [v2_results.get(r.name, (0, PhiComponents()))[1].granger for r in arch_runs]
    v2_spectral_vals = [v2_results.get(r.name, (0, PhiComponents()))[1].spectral for r in arch_runs]

    for label, vals in [
        ("Old Phi(IIT)", old_vals),
        ("V2 Composite", v2_composite_vals),
        ("V2 Granger", v2_granger_vals),
        ("V2 Spectral", v2_spectral_vals),
    ]:
        valid = [v for v in vals if v > 1e-10]
        if len(valid) >= 2:
            spread = max(valid) / min(valid)
            print(f"    {label:<20s}: spread = x{spread:.1f}  (range {min(valid):.2f} - {max(valid):.2f})")
        else:
            print(f"    {label:<20s}: insufficient data")

    # ── ASCII charts ──
    print(f"\n  V2 COMPOSITE PHI BY ARCHITECTURE:")
    max_v2 = max(v2_results.get(r.name, (0, PhiComponents()))[0] for r in arch_runs)
    max_v2 = max(max_v2, 1e-10)
    for run in arch_runs:
        v2_phi = v2_results.get(run.name, (0, PhiComponents()))[0]
        bar_len = int(v2_phi / max_v2 * 50)
        bar = "#" * bar_len
        print(f"    {run.name:<20s} |{bar} {v2_phi:.2f}")

    print(f"\n  OLD PHI(IIT) BY ARCHITECTURE:")
    max_old = max(old_results.get(r.name, (0, 0))[0] for r in arch_runs)
    max_old = max(max_old, 1e-10)
    for run in arch_runs:
        old_phi = old_results.get(run.name, (0, 0))[0]
        bar_len = int(old_phi / max_old * 50)
        bar = "#" * bar_len
        print(f"    {run.name:<20s} |{bar} {old_phi:.4f}")

    # ── V2 component breakdown ──
    print(f"\n  V2 COMPONENT BREAKDOWN:")
    for run in arch_runs:
        v2_phi, comp = v2_results.get(run.name, (0, PhiComponents()))
        if v2_phi < 1e-10:
            continue
        g_pct = comp.granger / v2_phi * 100 * ConsciousnessMeterV2.WEIGHTS['granger'] if v2_phi > 0 else 0
        s_pct = comp.spectral / v2_phi * 100 * ConsciousnessMeterV2.WEIGHTS['spectral'] if v2_phi > 0 else 0
        l_pct = comp.lz / v2_phi * 100 * ConsciousnessMeterV2.WEIGHTS['lz'] if v2_phi > 0 else 0
        m_pct = comp.integration / v2_phi * 100 * ConsciousnessMeterV2.WEIGHTS['integration'] if v2_phi > 0 else 0

        print(f"\n    {run.name}  (total={v2_phi:.2f}):")
        g_bar = "#" * int(g_pct / 2)
        s_bar = "#" * int(s_pct / 2)
        l_bar = "#" * int(l_pct / 2)
        m_bar = "#" * int(m_pct / 2)
        print(f"      Granger     [{g_bar:<25s}] {comp.granger:>10.2f} ({g_pct:.0f}%)")
        print(f"      Spectral    [{s_bar:<25s}] {comp.spectral:>10.2f} ({s_pct:.0f}%)")
        print(f"      LZ          [{l_bar:<25s}] {comp.lz:>10.2f} ({l_pct:.0f}%)")
        print(f"      Integration [{m_bar:<25s}] {comp.integration:>10.2f} ({m_pct:.0f}%)")

    print(f"\n{'=' * 90}")
    print("  CONCLUSION")
    print("=" * 90)

    # Find best discriminator
    best_spread = 0
    best_metric = "none"
    for label, vals in [("Old Phi(IIT)", old_vals), ("V2 Composite", v2_composite_vals),
                        ("V2 Granger", v2_granger_vals)]:
        valid = [v for v in vals if v > 1e-10]
        if len(valid) >= 2:
            spread = max(valid) / min(valid)
            if spread > best_spread:
                best_spread = spread
                best_metric = label

    print(f"  Best discriminator: {best_metric} (spread x{best_spread:.1f})")
    print(f"  V2 replaces old PhiCalculator with 4-dimensional composite scoring")
    print(f"  Granger causality density dominates (45% weight) due to bench_v8 results")
    print(f"  O(sqrt(N)) sampling makes V2 scalable to 1000+ cells")
    print("=" * 90)


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Consciousness Meter V2 Benchmark")
    parser.add_argument("--cells", type=int, default=128, help="Number of cells (default 128)")
    parser.add_argument("--steps", type=int, default=200, help="Training steps (default 200)")
    parser.add_argument("--record-every", type=int, default=10,
                        help="Record hiddens every N steps (default 10)")
    args = parser.parse_args()

    run_benchmark(n_cells=args.cells, steps=args.steps, record_every=args.record_every)


if __name__ == "__main__":
    main()
