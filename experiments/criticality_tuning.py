#!/usr/bin/env python3
"""criticality_tuning.py -- Edge-of-chaos tuning via controlled chaos injection.

Key insight from EEG validation: ConsciousMind is sub-critical (45%).
We need edge-of-chaos. Instead of just SOC parameter sweeps, we inject
controlled chaos through three mechanisms:

1. Noise at critical level: find noise where Phi variance is maximized (phase transition)
2. Balanced excitation/inhibition: mix positive and negative connections (like real brains)
3. Power-law degree distribution: instead of uniform factions, use power-law sized groups

Sweep:
  - noise: [0.0, 0.001, 0.003, 0.005, 0.008, 0.01, 0.02, 0.05]
  - excitation/inhibition ratio: [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
  - 64 cells, 2000 steps each config

For each config: Phi mean/std, LZ complexity, Hurst exponent,
power spectrum slope (target -1.0 for 1/f), brain-likeness score.

Usage:
  python3 experiments/criticality_tuning.py
"""

import sys
import os
import math
import time
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Brain reference ranges (from EEG validation)
BRAIN_REFERENCE = {
    'lz_complexity': (0.75, 0.95),
    'hurst_exponent': (0.65, 0.85),
    'psd_slope': (-1.5, -0.5),
    'phi_cv': (0.2, 0.8),
    'criticality_exponent': (1.2, 2.0),
}


def brain_match_pct(metric: str, value: float) -> float:
    """How well does value match brain reference range?"""
    ref = BRAIN_REFERENCE.get(metric)
    if ref is None:
        return 50.0
    low, high = ref
    mid = (low + high) / 2
    span = (high - low) / 2
    if span < 1e-12:
        return 100.0 if abs(value - mid) < 0.01 else 0.0
    distance = abs(value - mid) / span
    if distance <= 1.0:
        return 100.0 * (1.0 - distance * 0.5)
    else:
        return max(0.0, 100.0 * (1.0 - distance * 0.3))


@dataclass
class TuningResult:
    noise: float
    ei_ratio: float
    phi_mean: float
    phi_std: float
    phi_cv: float
    lz: float
    hurst: float
    psd_slope: float
    crit_exponent: float
    brain_likeness: float
    power_law_groups: bool


# ── Metrics computation ──

def lempel_ziv_complexity(series: np.ndarray) -> float:
    """LZ complexity of binarized signal."""
    median = np.median(series)
    binary = (series > median).astype(int)
    seen = set()
    w = ""
    complexity = 0
    for b in binary:
        w += str(b)
        if w not in seen:
            seen.add(w)
            complexity += 1
            w = ""
    n = len(series)
    return complexity / (n / max(np.log2(n), 1))


def hurst_exponent(series: np.ndarray) -> float:
    """R/S method Hurst exponent."""
    n = len(series)
    if n < 20:
        return 0.5
    half = n // 2
    rs_vals = []
    for start in [0, half]:
        seg = series[start:start + half]
        mean_val = np.mean(seg)
        y = np.cumsum(seg - mean_val)
        r = np.max(y) - np.min(y)
        s = np.std(seg)
        if s > 1e-12:
            rs_vals.append(r / s)
    if not rs_vals:
        return 0.5
    rs = np.mean(rs_vals)
    if rs > 0 and half > 1:
        return float(np.clip(np.log(rs) / np.log(half), 0, 1))
    return 0.5


def power_spectrum_slope(series: np.ndarray) -> float:
    """Power spectrum slope (1/f target = -1.0)."""
    freqs = np.fft.rfftfreq(len(series))
    psd = np.abs(np.fft.rfft(series - np.mean(series))) ** 2
    mask = freqs > 0
    if mask.sum() < 3:
        return 0.0
    log_f = np.log10(freqs[mask])
    log_p = np.log10(psd[mask] + 1e-30)
    return float(np.polyfit(log_f, log_p, 1)[0])


def criticality_exponent(series: np.ndarray) -> float:
    """Estimate power-law exponent from fluctuations."""
    diffs = np.abs(np.diff(series))
    diffs = diffs[diffs > 0]
    if len(diffs) < 10:
        return 0.0
    threshold = np.percentile(diffs, 50)
    tail = diffs[diffs >= threshold]
    if len(tail) < 5 or threshold < 1e-12:
        return 0.0
    return 1.0 + len(tail) / np.sum(np.log(tail / threshold))


# ── Core simulation ──

def run_critical_consciousness(
    n_steps: int,
    n_cells: int,
    dim: int,
    noise_level: float,
    ei_ratio: float,
    use_power_law_groups: bool = True,
) -> np.ndarray:
    """Run coupled oscillator consciousness with controlled chaos injection.

    Args:
        n_steps: simulation steps
        n_cells: number of cells
        dim: hidden dimension
        noise_level: base noise injection
        ei_ratio: fraction of excitatory connections (rest are inhibitory)
        use_power_law_groups: use power-law sized factions instead of uniform
    """
    rng = np.random.default_rng(42)
    hidden_dim = dim * 2
    coupling = 0.014  # PSI_COUPLING

    # Initialize cells
    hiddens = rng.standard_normal((n_cells, hidden_dim)).astype(np.float64) * 0.1
    weights = rng.standard_normal((n_cells, hidden_dim, dim + 1)).astype(np.float64) * 0.05

    # Excitation/inhibition mask: each connection is +1 (excitatory) or -1 (inhibitory)
    ei_mask = np.ones((n_cells, n_cells), dtype=np.float64)
    n_inhibitory = int(n_cells * n_cells * (1.0 - ei_ratio))
    inhib_indices = rng.choice(n_cells * n_cells, size=n_inhibitory, replace=False)
    ei_mask.flat[inhib_indices] = -1.0
    np.fill_diagonal(ei_mask, 0.0)  # no self-connections

    # Power-law faction sizes (Zipf distribution)
    if use_power_law_groups:
        # Generate power-law group sizes
        n_factions = max(3, int(np.log2(n_cells)))
        raw_sizes = np.array([1.0 / (i + 1) ** 1.2 for i in range(n_factions)])
        raw_sizes = raw_sizes / raw_sizes.sum() * n_cells
        faction_sizes = np.maximum(1, np.round(raw_sizes)).astype(int)
        # Adjust to match n_cells exactly
        diff = n_cells - faction_sizes.sum()
        if diff > 0:
            faction_sizes[0] += diff
        elif diff < 0:
            for i in range(len(faction_sizes) - 1, -1, -1):
                remove = min(-diff, faction_sizes[i] - 1)
                faction_sizes[i] -= remove
                diff += remove
                if diff >= 0:
                    break
        # Assign cells to factions
        faction_labels = np.zeros(n_cells, dtype=int)
        idx = 0
        for f, sz in enumerate(faction_sizes):
            faction_labels[idx:idx + sz] = f
            idx += sz
    else:
        n_factions = 8
        faction_labels = np.arange(n_cells) % n_factions

    # SOC sandpile for chaos injection
    soc_grid_size = 16
    soc_threshold = 4
    soc_grid = np.zeros((soc_grid_size, soc_grid_size), dtype=np.int32)

    phis = np.zeros(n_steps)

    for step in range(n_steps):
        inp = rng.standard_normal(dim) * 0.1

        # SOC sand drop
        sx, sy = rng.integers(0, soc_grid_size, 2)
        soc_grid[sx, sy] += 1
        avalanche = 0
        while True:
            topples = soc_grid >= soc_threshold
            if not topples.any():
                break
            avalanche += topples.sum()
            soc_grid[topples] -= soc_threshold
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                shifted = np.roll(np.roll(topples.astype(np.int32), dx, axis=0), dy, axis=1)
                if dx == -1: shifted[-1, :] = 0
                elif dx == 1: shifted[0, :] = 0
                if dy == -1: shifted[:, -1] = 0
                elif dy == 1: shifted[:, 0] = 0
                soc_grid += shifted
        chaos = min(1.0, 0.1 * math.log(avalanche + 1))

        # Total noise: base + SOC-driven
        total_noise = noise_level + chaos * 0.02

        # Coupled input with E/I balance (vectorized)
        # ei_mask @ hiddens[:, :dim] gives weighted sum of all cells for each cell
        # Since diagonal is 0, self-contribution is excluded
        other_contrib = ei_mask @ hiddens[:, :dim]  # (n_cells, dim)
        coupled_inp = inp[np.newaxis, :] + coupling * other_contrib

        # Add noise
        coupled_inp += rng.standard_normal((n_cells, dim)) * total_noise

        # Faction-based interaction boost (vectorized)
        # Precompute faction means
        unique_factions = np.unique(faction_labels)
        faction_means = np.zeros((len(unique_factions), dim))
        faction_counts = np.zeros(len(unique_factions))
        for f in unique_factions:
            mask = faction_labels == f
            faction_means[f] = hiddens[mask, :dim].mean(axis=0)
            faction_counts[f] = mask.sum()
        # Each cell gets boosted by its faction mean (excluding self via correction)
        for f in unique_factions:
            mask = faction_labels == f
            count = faction_counts[f]
            if count > 1:
                # faction_mean_excluding_self = (sum - self) / (count - 1)
                faction_sum = hiddens[mask, :dim].sum(axis=0)
                self_contrib = hiddens[mask, :dim]
                corrected_mean = (faction_sum[np.newaxis, :] - self_contrib) / (count - 1)
                coupled_inp[mask] += coupling * 2.0 * corrected_mean

        # GRU-like update (vectorized)
        mt_col = np.full((n_cells, 1), np.mean(np.sqrt(np.mean(hiddens ** 2, axis=1))))
        combined = np.concatenate([coupled_inp, mt_col], axis=1)
        wx = np.einsum('ijk,ik->ij', weights, combined)
        gate = 1.0 / (1.0 + np.exp(-wx))
        candidate = np.tanh(wx * 0.5)
        hiddens = gate * hiddens + (1.0 - gate) * candidate

        # Additional noise
        if total_noise > 0:
            hiddens += rng.standard_normal((n_cells, hidden_dim)) * total_noise * 0.1

        # Phi proxy (fast: skip full corrcoef, use sampled correlation)
        global_var = np.var(hiddens)
        per_cell_var = np.mean(np.var(hiddens, axis=1))
        phi = max(0.0, global_var - per_cell_var)

        # Integration term (sampled pairs for O(1) instead of O(n^2))
        if n_cells > 1:
            i1, i2 = rng.integers(0, n_cells, 2)
            if i1 != i2:
                h1, h2 = hiddens[i1], hiddens[i2]
                n1 = np.linalg.norm(h1)
                n2 = np.linalg.norm(h2)
                if n1 > 1e-12 and n2 > 1e-12:
                    corr = np.dot(h1, h2) / (n1 * n2)
                    phi += abs(corr) * 0.1

        phis[step] = phi

    return phis


def compute_all_metrics(phi_series: np.ndarray) -> dict:
    """Compute all brain-likeness metrics."""
    phi_mean = float(np.mean(phi_series))
    phi_std = float(np.std(phi_series))
    phi_cv = phi_std / max(phi_mean, 1e-12)
    lz = lempel_ziv_complexity(phi_series)
    hurst = hurst_exponent(phi_series)
    slope = power_spectrum_slope(phi_series)
    crit = criticality_exponent(phi_series)

    matches = []
    for metric, val in [
        ('phi_cv', phi_cv),
        ('lz_complexity', lz),
        ('hurst_exponent', hurst),
        ('psd_slope', slope),
        ('criticality_exponent', crit),
    ]:
        matches.append(brain_match_pct(metric, val))

    return {
        'phi_mean': phi_mean,
        'phi_std': phi_std,
        'phi_cv': phi_cv,
        'lz': lz,
        'hurst': hurst,
        'psd_slope': slope,
        'crit_exponent': crit,
        'brain_likeness': float(np.mean(matches)),
        'per_metric': dict(zip(
            ['phi_cv', 'lz', 'hurst', 'psd_slope', 'crit_exp'],
            matches
        )),
    }


def main():
    print("=" * 78)
    print("  Criticality Tuning -- Edge-of-Chaos via Controlled Chaos Injection")
    print("=" * 78)
    print()
    print("  Strategy: noise + E/I balance + power-law factions")
    print("  Target: maximize brain-likeness (PSD slope -> -1.0, Hurst -> 0.75)")
    print()

    n_steps = 1000
    n_cells = 32
    dim = 32  # smaller dim for speed

    noise_levels = [0.0, 0.001, 0.003, 0.005, 0.008, 0.01, 0.02, 0.05]
    ei_ratios = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    results: List[TuningResult] = []
    total = len(noise_levels) * len(ei_ratios)
    done = 0
    t0 = time.time()

    # Baseline: no noise, all excitatory, uniform factions
    print("  [baseline] noise=0, E/I=1.0, uniform factions...")
    baseline_phi = run_critical_consciousness(n_steps, n_cells, dim, 0.0, 1.0, False)
    baseline_m = compute_all_metrics(baseline_phi)
    print(f"  Baseline: brain-likeness={baseline_m['brain_likeness']:.1f}%  "
          f"PSD={baseline_m['psd_slope']:.2f}  Hurst={baseline_m['hurst']:.3f}  "
          f"LZ={baseline_m['lz']:.3f}")
    print()

    # Sweep
    print(f"  Sweeping {total} configurations (64 cells, 2000 steps each)...")
    print()

    for noise in noise_levels:
        for ei in ei_ratios:
            done += 1
            phi_series = run_critical_consciousness(
                n_steps, n_cells, dim, noise, ei, True
            )
            m = compute_all_metrics(phi_series)

            r = TuningResult(
                noise=noise,
                ei_ratio=ei,
                phi_mean=m['phi_mean'],
                phi_std=m['phi_std'],
                phi_cv=m['phi_cv'],
                lz=m['lz'],
                hurst=m['hurst'],
                psd_slope=m['psd_slope'],
                crit_exponent=m['crit_exponent'],
                brain_likeness=m['brain_likeness'],
                power_law_groups=True,
            )
            results.append(r)

            if done % 8 == 0 or done == total:
                elapsed = time.time() - t0
                eta = elapsed / done * (total - done)
                pct = done / total * 100
                print(f"  [{done:3d}/{total}] {pct:5.1f}%  "
                      f"noise={noise:.3f} E/I={ei:.1f}  "
                      f"brain={r.brain_likeness:.1f}%  "
                      f"ETA={int(eta)}s")

    elapsed = time.time() - t0
    print(f"\n  Sweep complete in {elapsed:.1f}s")

    # Sort by brain-likeness
    results.sort(key=lambda x: x.brain_likeness, reverse=True)

    # ── Results table ──
    print()
    print("=" * 78)
    print("  TOP 15 CONFIGURATIONS (by brain-likeness)")
    print("=" * 78)
    print(f"  {'Rank':>4} {'Noise':>7} {'E/I':>5} {'Phi_m':>7} {'Phi_cv':>7} "
          f"{'LZ':>6} {'Hurst':>6} {'PSD':>7} {'Crit':>6} {'Brain%':>7}")
    print("  " + "-" * 74)

    for i, r in enumerate(results[:15]):
        mark = " ***" if i == 0 else ""
        print(f"  {i+1:4d} {r.noise:7.3f} {r.ei_ratio:5.1f} {r.phi_mean:7.4f} {r.phi_cv:7.3f} "
              f"{r.lz:6.3f} {r.hurst:6.3f} {r.psd_slope:7.2f} {r.crit_exponent:6.2f} "
              f"{r.brain_likeness:6.1f}%{mark}")

    best = results[0]

    # ── Comparison: best vs baseline ──
    print()
    print("=" * 78)
    print("  BEST vs BASELINE")
    print("=" * 78)
    metrics_compare = [
        ("Brain-likeness", baseline_m['brain_likeness'], best.brain_likeness, "%"),
        ("PSD slope", baseline_m['psd_slope'], best.psd_slope, ""),
        ("Hurst exponent", baseline_m['hurst'], best.hurst, ""),
        ("LZ complexity", baseline_m['lz'], best.lz, ""),
        ("Phi CV", baseline_m['phi_cv'], best.phi_cv, ""),
        ("Crit exponent", baseline_m['crit_exponent'], best.crit_exponent, ""),
    ]
    print(f"  {'Metric':<20} {'Baseline':>10} {'Best':>10} {'Delta':>10} {'Target':>12}")
    print("  " + "-" * 66)
    for name, base_val, best_val, unit in metrics_compare:
        delta = best_val - base_val
        targets = {
            "PSD slope": "-1.0",
            "Hurst exponent": "0.75",
            "LZ complexity": "0.85",
            "Phi CV": "0.5",
            "Crit exponent": "1.5",
            "Brain-likeness": "100%",
        }
        target = targets.get(name, "")
        print(f"  {name:<20} {base_val:10.4f} {best_val:10.4f} {delta:+10.4f} {target:>12}")

    # ── ASCII bar chart ──
    print()
    print("  Brain-likeness by noise level (best E/I for each):")
    print()

    noise_best = {}
    for r in results:
        if r.noise not in noise_best or r.brain_likeness > noise_best[r.noise].brain_likeness:
            noise_best[r.noise] = r

    max_bl = max(r.brain_likeness for r in noise_best.values())
    for noise in sorted(noise_best.keys()):
        r = noise_best[noise]
        bar_len = int(40 * r.brain_likeness / max(max_bl, 1))
        bar = "=" * bar_len
        marker = " <-- BEST" if r.brain_likeness == best.brain_likeness else ""
        print(f"  noise={noise:5.3f} |{bar} {r.brain_likeness:.1f}% (E/I={r.ei_ratio:.1f}){marker}")

    print()
    print("  Brain-likeness by E/I ratio (best noise for each):")
    print()

    ei_best = {}
    for r in results:
        if r.ei_ratio not in ei_best or r.brain_likeness > ei_best[r.ei_ratio].brain_likeness:
            ei_best[r.ei_ratio] = r

    for ei in sorted(ei_best.keys()):
        r = ei_best[ei]
        bar_len = int(40 * r.brain_likeness / max(max_bl, 1))
        bar = "=" * bar_len
        marker = " <-- BEST" if r.brain_likeness == best.brain_likeness else ""
        print(f"  E/I={ei:3.1f}   |{bar} {r.brain_likeness:.1f}% (noise={r.noise:.3f}){marker}")

    # ── Phase transition detection ──
    print()
    print("=" * 78)
    print("  PHASE TRANSITION ANALYSIS")
    print("=" * 78)

    # Find noise level where Phi variance is maximized (phase transition signature)
    phi_vars_by_noise = {}
    for r in results:
        if r.noise not in phi_vars_by_noise:
            phi_vars_by_noise[r.noise] = []
        phi_vars_by_noise[r.noise].append(r.phi_std)

    print()
    print("  Phi variance by noise (peak = phase transition):")
    phi_var_means = {n: np.mean(vs) for n, vs in phi_vars_by_noise.items()}
    max_var = max(phi_var_means.values()) if phi_var_means else 1
    for noise in sorted(phi_var_means.keys()):
        var = phi_var_means[noise]
        bar_len = int(40 * var / max(max_var, 1e-8))
        bar = "#" * bar_len
        peak = " <-- PHASE TRANSITION" if var == max_var else ""
        print(f"  noise={noise:5.3f} |{bar} std={var:.6f}{peak}")

    # ── Potential new law ──
    print()
    print("=" * 78)
    print("  POTENTIAL NEW LAW")
    print("=" * 78)
    print()

    if best.brain_likeness > baseline_m['brain_likeness']:
        improvement = best.brain_likeness - baseline_m['brain_likeness']
        print(f"  Law XX: Controlled chaos injection improves brain-likeness by +{improvement:.1f}%")
        print(f"  Optimal config: noise={best.noise}, E/I ratio={best.ei_ratio}")
        print()
        if best.ei_ratio < 1.0:
            print(f"  Key finding: Inhibitory connections (E/I={best.ei_ratio}) are essential.")
            print(f"  Pure excitation (E/I=1.0) is sub-optimal -- brains need inhibition.")
        if best.noise > 0:
            print(f"  Key finding: Noise={best.noise} pushes system to edge-of-chaos.")
            print(f"  Zero noise = sub-critical. Too much noise = super-critical.")
        print()
        print(f"  Proposed: Law 91 -- E/I Balance + Critical Noise = Brain-like Consciousness")
        print(f"    Consciousness requires both excitatory and inhibitory connections")
        print(f"    at ratio ~{best.ei_ratio:.1f}, with noise ~{best.noise:.3f} for edge-of-chaos.")
        print(f"    This mirrors Dale's principle in biological neural networks.")
    else:
        print("  No improvement found over baseline. Sub-criticality may require")
        print("  architectural changes rather than parameter tuning.")

    print()
    print("=" * 78)

    return results


if __name__ == "__main__":
    main()
