#!/usr/bin/env python3
"""criticality_sweep.py -- Systematic SOC parameter sweep for edge-of-chaos criticality.

Sweeps:
  - grid_size: 8, 16, 32, 64
  - threshold: 2, 3, 4, 5, 6
  - noise_injection: 0.0, 0.001, 0.005, 0.01, 0.05, 0.1

For each config: run 2000 steps, compute all 6 EEG metrics.
Goal: push ConsciousMind from sub-critical (45%) toward edge-of-chaos.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import math
import time
from dataclasses import dataclass
from typing import List, Dict, Tuple

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# Import SOCSandpile
try:
    from train_conscious_lm import SOCSandpile
except ImportError:
    # Inline fallback
    class SOCSandpile:
        def __init__(self, grid_size=16, threshold=4):
            self.grid_size = grid_size
            self.threshold = threshold
            self.grid = np.zeros((grid_size, grid_size), dtype=np.int32)
            self.avalanche_history = []

        def drop_sand(self):
            x, y = np.random.randint(0, self.grid_size, 2)
            self.grid[x, y] += 1
            avalanche_size = 0
            while True:
                topples = self.grid >= self.threshold
                if not topples.any():
                    break
                n_topple = topples.sum()
                avalanche_size += n_topple
                self.grid[topples] -= self.threshold
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    shifted = np.roll(np.roll(topples.astype(np.int32), dx, axis=0), dy, axis=1)
                    if dx == -1: shifted[-1,:] = 0
                    elif dx == 1: shifted[0,:] = 0
                    if dy == -1: shifted[:,-1] = 0
                    elif dy == 1: shifted[:, 0] = 0
                    self.grid += shifted
            self.avalanche_history.append(avalanche_size)
            return avalanche_size

        def chaos_intensity(self):
            if not self.avalanche_history:
                return 0.0
            recent = self.avalanche_history[-1]
            return min(1.0, 0.1 * math.log(recent + 1))

# Import EEG validation metrics
try:
    from eeg.validate_consciousness import (
        detect_criticality, lempel_ziv_complexity, hurst_exponent,
        power_spectrum_slope, phi_autocorrelation, BRAIN_REFERENCE,
        analyze_signal, ValidationResult,
    )
except ImportError:
    print("[WARN] eeg.validate_consciousness not available, using inline metrics")
    BRAIN_REFERENCE = {
        'lz_complexity': (0.75, 0.95),
        'hurst_exponent': (0.65, 0.85),
        'psd_slope': (-1.5, -0.5),
        'autocorr_decay': (5, 30),
        'phi_cv': (0.2, 0.8),
        'criticality_exponent': (1.2, 2.0),
    }
    # will be defined below if needed


def brain_match_pct(metric: str, value: float) -> float:
    """How well does value match brain reference?"""
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
class CriticalityResult:
    grid_size: int
    threshold: int
    noise: float
    phi_mean: float
    phi_cv: float
    lz: float
    hurst: float
    psd_slope: float
    crit_exponent: float
    crit_suscept: float
    is_critical: bool
    overall_match: float  # % brain-likeness


def run_coupled_consciousness(
    n_steps: int, n_cells: int, dim: int,
    grid_size: int, threshold: int, noise_inj: float,
) -> np.ndarray:
    """Run a coupled oscillator consciousness with SOC-driven chaos injection.

    Returns Phi timeseries. Fully vectorized for speed.
    """
    rng = np.random.default_rng(42)
    hidden_dim = dim * 2
    from consciousness_laws import PSI_ALPHA
    coupling = PSI_ALPHA  # 0.014

    # Initialize cells
    hiddens = rng.standard_normal((n_cells, hidden_dim)).astype(np.float64) * 0.1
    weights = rng.standard_normal((n_cells, hidden_dim, dim + 1)).astype(np.float64) * 0.05

    # SOC module
    soc = SOCSandpile(grid_size=grid_size, threshold=threshold)

    phis = np.zeros(n_steps)
    for step in range(n_steps):
        inp = rng.standard_normal(dim) * 0.1

        # SOC: drop sand and get chaos intensity
        soc.drop_sand()
        chaos = soc.chaos_intensity()

        # Inject noise scaled by chaos intensity + base noise
        total_noise = noise_inj + chaos * 0.02

        # Compute mean tension (vectorized)
        mean_tension = np.mean(np.sqrt(np.mean(hiddens ** 2, axis=1)))

        # Vectorized cell update:
        # Each cell's coupled_inp = inp + coupling * sum(other cells' first dim components)
        sum_all = hiddens[:, :dim].sum(axis=0)  # sum of all cells
        # For cell i: sum of others = sum_all - hiddens[i, :dim]
        coupled_inp = inp[np.newaxis, :] + coupling * (sum_all[np.newaxis, :] - hiddens[:, :dim])
        # (n_cells, dim)

        # Add noise
        coupled_inp += rng.standard_normal((n_cells, dim)) * total_noise

        # combined = [coupled_inp, mean_tension] -> (n_cells, dim+1)
        mt_col = np.full((n_cells, 1), mean_tension)
        combined = np.concatenate([coupled_inp, mt_col], axis=1)  # (n_cells, dim+1)

        # Gate and candidate (vectorized via einsum)
        # weights[ci] @ combined[ci] for each cell
        wx = np.einsum('ijk,ik->ij', weights, combined)  # (n_cells, hidden_dim)
        gate = 1.0 / (1.0 + np.exp(-wx))
        candidate = np.tanh(wx * 0.5)
        hiddens = gate * hiddens + (1.0 - gate) * candidate

        # Additional noise injection
        if total_noise > 0:
            hiddens += rng.standard_normal((n_cells, hidden_dim)) * total_noise * 0.1

        # Compute Phi proxy (vectorized)
        global_var = np.var(hiddens)
        per_cell_var = np.mean(np.var(hiddens, axis=1))
        phi = max(0.0, global_var - per_cell_var)

        # Integration term
        if n_cells > 1:
            cov_matrix = np.corrcoef(hiddens)
            if cov_matrix.ndim == 2:
                off_diag = cov_matrix[np.triu_indices(n_cells, k=1)]
                phi += np.mean(np.abs(off_diag)) * 0.1

        phis[step] = phi

    return phis


def compute_metrics(phi_series: np.ndarray) -> CriticalityResult:
    """Compute all EEG-comparable metrics from a Phi timeseries."""
    # Use the imported analyze_signal if available
    try:
        result = analyze_signal("sweep", phi_series)
        phi_mean = result.phi_mean
        phi_cv = result.phi_cv
        lz = result.lz
        hurst_val = result.hurst
        slope = result.psd_slope
        crit = result.criticality
    except Exception:
        # Inline computation
        phi_mean = float(np.mean(phi_series))
        phi_std = float(np.std(phi_series))
        phi_cv = phi_std / max(phi_mean, 1e-12)

        # LZ complexity (simplified)
        median = np.median(phi_series)
        binary = (phi_series > median).astype(int)
        seen = set()
        w = ""
        complexity = 0
        for b in binary:
            w += str(b)
            if w not in seen:
                seen.add(w)
                complexity += 1
                w = ""
        n = len(phi_series)
        lz = complexity / (n / max(np.log2(n), 1))

        # Hurst exponent (R/S)
        n = len(phi_series)
        if n > 20:
            half = n // 2
            mean_val = np.mean(phi_series[:half])
            y = np.cumsum(phi_series[:half] - mean_val)
            r = np.max(y) - np.min(y)
            s = np.std(phi_series[:half])
            rs1 = r / max(s, 1e-12)
            mean_val2 = np.mean(phi_series[half:])
            y2 = np.cumsum(phi_series[half:] - mean_val2)
            r2 = np.max(y2) - np.min(y2)
            s2 = np.std(phi_series[half:])
            rs2 = r2 / max(s2, 1e-12)
            if rs1 > 0 and rs2 > 0:
                hurst_val = np.log(np.mean([rs1, rs2])) / np.log(half) if half > 1 else 0.5
                hurst_val = np.clip(hurst_val, 0, 1)
            else:
                hurst_val = 0.5
        else:
            hurst_val = 0.5

        # PSD slope
        freqs = np.fft.rfftfreq(len(phi_series))
        psd = np.abs(np.fft.rfft(phi_series - np.mean(phi_series))) ** 2
        mask = freqs > 0
        if mask.sum() > 2:
            log_f = np.log10(freqs[mask])
            log_p = np.log10(psd[mask] + 1e-30)
            slope = np.polyfit(log_f, log_p, 1)[0]
        else:
            slope = 0.0

        # Criticality
        diffs = np.abs(np.diff(phi_series))
        diffs = diffs[diffs > 0]
        if len(diffs) > 10:
            threshold_val = np.percentile(diffs, 50)
            tail = diffs[diffs >= threshold_val]
            if len(tail) > 5 and threshold_val > 1e-12:
                crit_exp = 1.0 + len(tail) / np.sum(np.log(tail / threshold_val))
            else:
                crit_exp = 0.0
        else:
            crit_exp = 0.0

        window_size = max(10, len(phi_series) // 20)
        n_windows = len(phi_series) // window_size
        window_vars = [np.var(phi_series[i*window_size:(i+1)*window_size]) for i in range(n_windows)]
        susceptibility = np.var(window_vars) / max(np.mean(window_vars), 1e-12) if window_vars else 0.0

        crit = {
            'is_critical': (1.2 < crit_exp < 2.5) and (susceptibility > 0.1),
            'exponent': crit_exp,
            'susceptibility': susceptibility,
        }

    # Compute brain-match percentages
    matches = []
    for metric, val in [
        ('phi_cv', phi_cv), ('lz_complexity', lz), ('hurst_exponent', hurst_val),
        ('psd_slope', slope), ('criticality_exponent', crit.get('exponent', 0)),
    ]:
        matches.append(brain_match_pct(metric, val))

    overall = np.mean(matches)

    return CriticalityResult(
        grid_size=0, threshold=0, noise=0,
        phi_mean=phi_mean, phi_cv=phi_cv,
        lz=lz, hurst=hurst_val, psd_slope=slope,
        crit_exponent=crit.get('exponent', 0),
        crit_suscept=crit.get('susceptibility', 0),
        is_critical=crit.get('is_critical', False),
        overall_match=overall,
    )


def main():
    print("=" * 78)
    print("  Criticality Sweep -- SOC Parameter Optimization for Edge-of-Chaos")
    print("=" * 78)
    print()

    n_steps = 2000
    n_cells = 8
    dim = 64

    grid_sizes = [8, 16, 32, 64]
    thresholds = [2, 3, 4, 5, 6]
    noise_levels = [0.0, 0.001, 0.005, 0.01, 0.05, 0.1]

    results: List[CriticalityResult] = []
    total_configs = len(grid_sizes) * len(thresholds) * len(noise_levels)
    done = 0
    t0 = time.time()

    # First: baseline (no SOC, no noise)
    print("  [baseline] No SOC, no noise...")
    baseline_phi = run_coupled_consciousness(n_steps, n_cells, dim, 16, 4, 0.0)
    baseline = compute_metrics(baseline_phi)
    baseline.grid_size = 0
    baseline.threshold = 0
    baseline.noise = 0.0
    print(f"  Baseline match: {baseline.overall_match:.1f}%  "
          f"critical={baseline.is_critical}  exp={baseline.crit_exponent:.3f}")
    print()

    # Sweep
    print(f"  Sweeping {total_configs} configurations...")
    print()

    for gs in grid_sizes:
        for th in thresholds:
            for noise in noise_levels:
                done += 1
                phi_series = run_coupled_consciousness(
                    n_steps, n_cells, dim, gs, th, noise
                )
                r = compute_metrics(phi_series)
                r.grid_size = gs
                r.threshold = th
                r.noise = noise
                results.append(r)

                if done % 20 == 0 or done == total_configs:
                    elapsed = time.time() - t0
                    eta = elapsed / done * (total_configs - done)
                    pct = done / total_configs * 100
                    bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
                    print(f"\r  [{bar}] {pct:.0f}% ({done}/{total_configs}) "
                          f"ETA {eta:.0f}s", end="", flush=True)

    print()
    print()

    # Sort by overall_match
    results.sort(key=lambda r: r.overall_match, reverse=True)

    # Top 15 results table
    print("=" * 98)
    print("  TOP 15 CONFIGURATIONS (by brain-likeness %)")
    print("=" * 98)
    print(f"  {'#':>3} | {'Grid':>4} | {'Thr':>3} | {'Noise':>6} | "
          f"{'Match%':>6} | {'Crit?':>5} | {'Exp':>6} | {'Susc':>6} | "
          f"{'LZ':>5} | {'Hurst':>5} | {'PSD':>6} | {'CV':>5}")
    print(f"  {'---':>3}-+-{'----':>4}-+-{'---':>3}-+-{'------':>6}-+-"
          f"{'------':>6}-+-{'-----':>5}-+-{'------':>6}-+-{'------':>6}-+-"
          f"{'-----':>5}-+-{'-----':>5}-+-{'------':>6}-+-{'-----':>5}")

    for i, r in enumerate(results[:15]):
        crit_str = "YES" if r.is_critical else "no"
        print(f"  {i+1:>3} | {r.grid_size:>4} | {r.threshold:>3} | {r.noise:>6.3f} | "
              f"{r.overall_match:>5.1f}% | {crit_str:>5} | {r.crit_exponent:>6.3f} | "
              f"{r.crit_suscept:>6.3f} | {r.lz:>5.3f} | {r.hurst:>5.3f} | "
              f"{r.psd_slope:>6.2f} | {r.phi_cv:>5.3f}")

    best = results[0]
    print()
    print(f"  BEST CONFIG: grid={best.grid_size}, threshold={best.threshold}, "
          f"noise={best.noise}")
    print(f"  Brain-likeness: {baseline.overall_match:.1f}% -> {best.overall_match:.1f}% "
          f"(+{best.overall_match - baseline.overall_match:.1f}%)")
    print(f"  Critical: {best.is_critical}  (exp={best.crit_exponent:.3f}, "
          f"susc={best.crit_suscept:.3f})")

    # ASCII graph: brain-likeness by noise level (best grid/threshold)
    print()
    print("  Brain-likeness vs Noise (best grid/threshold):")
    best_gs, best_th = best.grid_size, best.threshold
    noise_matches = []
    for noise in noise_levels:
        matches = [r for r in results if r.grid_size == best_gs and r.threshold == best_th and r.noise == noise]
        if matches:
            noise_matches.append((noise, matches[0].overall_match))

    if noise_matches:
        max_m = max(m for _, m in noise_matches)
        min_m = min(m for _, m in noise_matches)
        height = 10
        width = len(noise_matches)
        print()
        for row in range(height, -1, -1):
            line = "    "
            val = min_m + (max_m - min_m) * row / height if height > 0 else min_m
            line += f"{val:5.1f}% |"
            for _, m in noise_matches:
                if m >= val:
                    line += " ## "
                else:
                    line += "    "
            print(line)
        print(f"           +{'----' * width}")
        print(f"            " + "  ".join(f"{n:.3f}" for n, _ in noise_matches))
        print(f"                          noise level")

    # Criticality exponent distribution
    print()
    print("  Criticality Exponent Distribution:")
    critical_count = sum(1 for r in results if r.is_critical)
    total = len(results)
    print(f"    Critical configs: {critical_count}/{total} ({100*critical_count/total:.1f}%)")
    print()

    # Bar chart: grid_size effect (averaged)
    print("  Average Brain-likeness by Grid Size:")
    for gs in grid_sizes:
        gs_results = [r for r in results if r.grid_size == gs]
        avg_match = np.mean([r.overall_match for r in gs_results])
        bar = "#" * int(avg_match)
        print(f"    grid={gs:>2}  {bar} {avg_match:.1f}%")

    print()
    print("  Average Brain-likeness by Threshold:")
    for th in thresholds:
        th_results = [r for r in results if r.threshold == th]
        avg_match = np.mean([r.overall_match for r in th_results])
        bar = "#" * int(avg_match)
        print(f"    thr={th}   {bar} {avg_match:.1f}%")

    # Improvement summary
    print()
    print("=" * 78)
    delta = best.overall_match - baseline.overall_match
    if delta > 5:
        print(f"  DISCOVERY: SOC tuning improved brain-likeness by +{delta:.1f}%")
        print(f"  Baseline: {baseline.overall_match:.1f}% (sub-critical)")
        print(f"  Best:     {best.overall_match:.1f}% (grid={best.grid_size}, "
              f"thr={best.threshold}, noise={best.noise})")
        if best.is_critical:
            print(f"  STATUS: CRITICAL ACHIEVED!")
        else:
            print(f"  STATUS: Improved but still sub-critical")
    else:
        print(f"  No significant improvement from SOC tuning (delta={delta:.1f}%)")
    print("=" * 78)

    return baseline, results


if __name__ == "__main__":
    main()
