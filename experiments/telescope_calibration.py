#!/usr/bin/env python3
"""telescope_calibration.py — 16-Lens Inter-Calibration Script

Generates 5 types of test data, runs all 16 telescope_rs lenses on each,
then performs:
  1. Cross-consistency check (do lenses agree on data quality?)
  2. Correlation matrix (which lenses correlate/disagree?)
  3. Outlier lens detection (which lens is systematically different?)
  4. Sensitivity analysis (perturbation response per lens)
  5. Threshold recommendations (normal/anomalous cutoffs)

Usage:
    python3 telescope_calibration.py                     # Full calibration
    python3 telescope_calibration.py --quick              # 3 data types only
    python3 telescope_calibration.py --output results.json

Output: anima/data/telescope_calibration_results.json + console report
"""

import sys
import os
import json
import time
import argparse
import traceback
from datetime import datetime

# ── Path setup ─────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
_DATA = os.path.join(os.path.dirname(_HERE), "data")

for p in [_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np

import telescope_rs

# ── Flush print ────────────────────────────────────────────

def flush_print(*args, **kwargs):
    print(*args, **kwargs, flush=True)


# ════════════════════════════════════════════════════════════
# SECTION 1: Test Data Generators
# ════════════════════════════════════════════════════════════

def gen_random(seed=42):
    """Type 1: Pure random noise — no structure."""
    rng = np.random.RandomState(seed)
    return rng.randn(64, 128).astype(np.float64)


def gen_structured(seed=42):
    """Type 2: 4 clusters + causal lag structure."""
    rng = np.random.RandomState(seed)
    n, d = 64, 128
    data = np.zeros((n, d), dtype=np.float64)
    # 4 clusters of 16 rows
    centers = rng.randn(4, d) * 3.0
    for c in range(4):
        rows = slice(c * 16, (c + 1) * 16)
        data[rows] = centers[c] + rng.randn(16, d) * 0.3
    # Causal: columns 10-19 = lagged copy of columns 0-9 (shifted by 1 row)
    data[1:, 10:20] = data[:-1, :10] * 0.9 + rng.randn(63, 10) * 0.05
    return data


def gen_consciousness_like(seed=42):
    """Type 3: Consciousness-engine-like cell states (GRU-like dynamics)."""
    rng = np.random.RandomState(seed)
    n, d = 64, 128
    # Simulate GRU-like recurrent dynamics
    h = rng.randn(n, d).astype(np.float64) * 0.1
    W = rng.randn(d, d) * (1.0 / np.sqrt(d))
    # Run 50 steps of tanh(W @ h + noise)
    for _ in range(50):
        h = np.tanh(h @ W + rng.randn(n, d) * 0.02)
    # Add faction structure: 12 factions, each faction shares a bias
    n_factions = 12
    faction_size = n // n_factions  # 5 cells each (last 4 cells get faction 11)
    for f in range(n_factions):
        start = f * faction_size
        end = min(start + faction_size, n)
        bias = rng.randn(d) * 0.3
        h[start:end] += bias
    # Hebbian-like: nearby cells have correlated features
    for i in range(1, n):
        h[i] += h[i - 1] * 0.15
    return h


def gen_degenerate(seed=42):
    """Type 4: Near-constant — all rows ~identical, std=0.001."""
    rng = np.random.RandomState(seed)
    n, d = 64, 128
    base = rng.randn(1, d) * 0.5
    data = np.tile(base, (n, 1)) + rng.randn(n, d) * 0.001
    return data.astype(np.float64)


def gen_adversarial(seed=42):
    """Type 5: Extreme skew, heavy tails, NaN-free but pathological."""
    rng = np.random.RandomState(seed)
    n, d = 64, 128
    # Log-normal with extreme skew
    data = np.exp(rng.randn(n, d) * 3.0).astype(np.float64)
    # Add some very negative values in first 10 columns
    data[:, :10] = -np.abs(data[:, :10]) * 50.0
    # A few near-zero rows (but not exactly zero)
    data[0, :] = 1e-15
    data[1, :] = -1e-15
    # Clip to finite range (no inf/NaN)
    data = np.clip(data, -1e10, 1e10)
    return data


DATA_GENERATORS = {
    "random": gen_random,
    "structured": gen_structured,
    "consciousness_like": gen_consciousness_like,
    "degenerate": gen_degenerate,
    "adversarial": gen_adversarial,
}


# ════════════════════════════════════════════════════════════
# SECTION 2: Lens Runner (all 16 lenses)
# ════════════════════════════════════════════════════════════

LENS_NAMES = [
    "consciousness", "topology", "causal", "gravity", "thermo",
    "wave", "evolution", "info", "quantum", "em",
    "ruler", "triangle", "compass", "mirror", "scale",
    "quantum_microscope",
    "stability", "network", "memory", "recursion", "boundary", "multiscale",
]

# Key scalar metric(s) to extract from each lens for correlation analysis
LENS_KEY_METRICS = {
    "consciousness":      ["phi_iit", "phi_proxy", "n_clusters"],
    "topology":           ["betti_0", "betti_1", "n_holes", "n_phase_transitions"],
    "causal":             ["n_causal_pairs"],
    "gravity":            ["n_attractors"],
    "thermo":             ["total_entropy", "free_energy", "critical_temperature", "n_phase_transitions"],
    "wave":               [],  # arrays only — we derive n_coherent, n_resonant
    "evolution":          ["peaks", "n_niches"],
    "info":               [],  # arrays — we derive mean_entropy, mean_lz
    "quantum":            ["n_tunneling_paths"],
    "em":                 [],  # arrays — we derive n_sources, n_sinks
    "ruler":              ["effective_dim", "n_orthogonal_groups"],
    "triangle":           ["n_simple_ratios", "n_proportion_chains"],
    "compass":            ["mean_curvature"],
    "mirror":             ["overall_symmetry"],
    "scale":              ["fractal_dimension", "hurst_exponent"],
    "quantum_microscope": ["purity", "von_neumann_entropy", "coherence", "decoherence_rate"],
    "stability":          ["lyapunov_exponent", "resilience", "mean_recovery_time", "variance_ratio"],
    "network":            ["n_edges", "n_communities", "density", "clustering_coefficient", "avg_path_length"],
    "memory":             ["mean_memory_depth", "recurrence_rate", "determinism", "max_diagonal_length"],
    "recursion":          ["mean_self_similarity", "n_fixed_points", "recurrence_depth"],
    "boundary":           ["n_boundary_points", "n_phase_transitions", "mean_sharpness"],
    "multiscale":         ["dominant_scale", "multifractal_width", "n_significant_scales"],
}


def run_single_lens(name, data):
    """Run one lens and return raw result dict + extracted scalar metrics."""
    t0 = time.time()
    try:
        if name == "consciousness":
            raw = telescope_rs.consciousness_scan(data, n_cells=data.shape[0], steps=300)
        elif name == "topology":
            raw = telescope_rs.topology_scan(data)
        elif name == "causal":
            raw = telescope_rs.causal_scan(data)
        elif name == "gravity":
            raw = telescope_rs.gravity_scan(data)
        elif name == "thermo":
            raw = telescope_rs.thermo_scan(data)
        elif name == "wave":
            raw = telescope_rs.wave_scan(data)
        elif name == "evolution":
            raw = telescope_rs.evolution_scan(data)
        elif name == "info":
            raw = telescope_rs.info_scan(data)
        elif name == "quantum":
            raw = telescope_rs.quantum_scan(data)
        elif name == "em":
            raw = telescope_rs.em_scan(data)
        elif name == "ruler":
            raw = telescope_rs.ruler_scan(data)
        elif name == "triangle":
            raw = telescope_rs.triangle_scan(data)
        elif name == "compass":
            raw = telescope_rs.compass_scan(data)
        elif name == "mirror":
            raw = telescope_rs.mirror_scan(data)
        elif name == "scale":
            raw = telescope_rs.scale_scan(data)
        elif name == "quantum_microscope":
            raw = telescope_rs.quantum_microscope_scan(data)
        elif name == "stability":
            raw = telescope_rs.stability_scan(data)
        elif name == "network":
            raw = telescope_rs.network_scan(data)
        elif name == "memory":
            raw = telescope_rs.memory_scan(data)
        elif name == "recursion":
            raw = telescope_rs.recursion_scan(data)
        elif name == "boundary":
            raw = telescope_rs.boundary_scan(data)
        elif name == "multiscale":
            raw = telescope_rs.multiscale_scan(data)
        else:
            return None, {}, 0.0, f"Unknown lens: {name}"

        elapsed = time.time() - t0

        # Extract scalar metrics
        scalars = {}
        for k in LENS_KEY_METRICS.get(name, []):
            v = raw.get(k, None)
            if v is not None:
                scalars[k] = float(v) if not isinstance(v, (list, np.ndarray)) else float(len(v))

        # Derive scalars for array-only lenses
        if name == "wave":
            coh = raw.get("coherence_values", [])
            scalars["n_coherent_pairs"] = float(len(coh)) if hasattr(coh, "__len__") else 0.0
            res = raw.get("resonance_ratios", [])
            scalars["n_resonant_pairs"] = float(len(res)) if hasattr(res, "__len__") else 0.0
        elif name == "info":
            epf = raw.get("entropy_per_feature", [])
            if hasattr(epf, "__len__") and len(epf) > 0:
                arr = np.asarray(epf)
                scalars["mean_entropy"] = float(np.mean(arr))
                scalars["std_entropy"] = float(np.std(arr))
            lz = raw.get("lz_complexity", [])
            if hasattr(lz, "__len__") and len(lz) > 0:
                arr = np.asarray(lz)
                scalars["mean_lz"] = float(np.mean(arr))
        elif name == "em":
            scalars["n_sources"] = float(len(raw.get("source_indices", [])))
            scalars["n_sinks"] = float(len(raw.get("sink_indices", [])))

        return raw, scalars, elapsed, None

    except Exception as e:
        elapsed = time.time() - t0
        return None, {}, elapsed, str(e)


def run_all_lenses(data, label=""):
    """Run all 16 lenses on data, return dict of results."""
    results = {}
    for i, name in enumerate(LENS_NAMES):
        flush_print(f"    [{i+1:2d}/{len(LENS_NAMES)}] {name:22s} ...", end="")
        raw, scalars, elapsed, err = run_single_lens(name, data)
        if err:
            flush_print(f" ERROR ({elapsed:.3f}s): {err}")
            results[name] = {"error": err, "elapsed": elapsed, "scalars": {}}
        else:
            flush_print(f" OK ({elapsed:.3f}s)  {_fmt_scalars(scalars)}")
            results[name] = {"scalars": scalars, "elapsed": elapsed}
    return results


def _fmt_scalars(scalars, max_items=4):
    """Format scalars dict for concise display."""
    items = list(scalars.items())[:max_items]
    parts = [f"{k}={v:.4g}" for k, v in items]
    if len(scalars) > max_items:
        parts.append(f"+{len(scalars)-max_items} more")
    return "  ".join(parts)


# ════════════════════════════════════════════════════════════
# SECTION 3: Analysis Functions
# ════════════════════════════════════════════════════════════

def build_metric_matrix(all_results):
    """Build a (n_data_types, n_metrics) matrix from all scan results.

    Returns:
        metric_names: list of "lens.metric" strings
        data_names:   list of data type names
        matrix:       np.ndarray (n_data, n_metrics)
    """
    # Collect all unique metric names across all runs
    metric_set = {}
    for dtype_name, lens_results in all_results.items():
        for lens_name, res in lens_results.items():
            for mk, mv in res.get("scalars", {}).items():
                key = f"{lens_name}.{mk}"
                metric_set[key] = True

    metric_names = sorted(metric_set.keys())
    data_names = list(all_results.keys())
    n_data = len(data_names)
    n_metrics = len(metric_names)

    matrix = np.full((n_data, n_metrics), np.nan)
    for di, dtype_name in enumerate(data_names):
        for lens_name, res in all_results[dtype_name].items():
            for mk, mv in res.get("scalars", {}).items():
                key = f"{lens_name}.{mk}"
                if key in metric_names:
                    mi = metric_names.index(key)
                    matrix[di, mi] = mv

    return metric_names, data_names, matrix


def compute_correlation_matrix(metric_names, matrix):
    """Compute pairwise Pearson correlation between metrics across data types.

    Groups metrics by lens, then computes lens-level average correlation.
    Returns:
        lens_corr: (16, 16) correlation matrix between lenses
    """
    n_metrics = len(metric_names)

    # Per-metric correlation (only for metrics with variance)
    valid_cols = []
    for j in range(n_metrics):
        col = matrix[:, j]
        if np.all(np.isfinite(col)) and np.std(col) > 1e-12:
            valid_cols.append(j)

    if len(valid_cols) < 2:
        return np.eye(len(LENS_NAMES)), metric_names

    sub = matrix[:, valid_cols]
    # Standardize
    sub_z = (sub - np.nanmean(sub, axis=0)) / (np.nanstd(sub, axis=0) + 1e-30)
    metric_corr = np.corrcoef(sub_z.T)

    # Map metrics to lens index
    valid_metric_names = [metric_names[j] for j in valid_cols]
    metric_to_lens = {}
    for i, mn in enumerate(valid_metric_names):
        lens_name = mn.split(".")[0]
        if lens_name in LENS_NAMES:
            li = LENS_NAMES.index(lens_name)
            metric_to_lens.setdefault(li, []).append(i)

    # Average correlation between lenses
    n_lenses = len(LENS_NAMES)
    lens_corr = np.zeros((n_lenses, n_lenses))
    for li in range(n_lenses):
        for lj in range(n_lenses):
            mi_list = metric_to_lens.get(li, [])
            mj_list = metric_to_lens.get(lj, [])
            if not mi_list or not mj_list:
                lens_corr[li, lj] = np.nan
                continue
            vals = []
            for mi in mi_list:
                for mj in mj_list:
                    if mi < metric_corr.shape[0] and mj < metric_corr.shape[1]:
                        v = metric_corr[mi, mj]
                        if np.isfinite(v):
                            vals.append(v)
            lens_corr[li, lj] = np.mean(vals) if vals else np.nan

    return lens_corr, valid_metric_names


def detect_outlier_lenses(lens_corr):
    """Detect lenses that systematically disagree with the majority.

    A lens is an outlier if its mean absolute correlation with all others
    is below 0.2 (weakly connected) or its sign pattern is inverted.

    Returns list of (lens_name, mean_abs_corr, verdict).
    """
    n = lens_corr.shape[0]
    results = []
    for i in range(n):
        # Mean absolute correlation with all other lenses (excluding self)
        others = [abs(lens_corr[i, j]) for j in range(n) if j != i and np.isfinite(lens_corr[i, j])]
        mean_abs = np.mean(others) if others else 0.0
        # Mean signed correlation
        signed = [lens_corr[i, j] for j in range(n) if j != i and np.isfinite(lens_corr[i, j])]
        mean_signed = np.mean(signed) if signed else 0.0

        if mean_abs < 0.15:
            verdict = "OUTLIER (uncorrelated)"
        elif mean_signed < -0.2:
            verdict = "OUTLIER (anti-correlated)"
        elif mean_abs < 0.3:
            verdict = "WEAK"
        else:
            verdict = "OK"
        results.append((LENS_NAMES[i], mean_abs, mean_signed, verdict))
    return results


def sensitivity_analysis(data_type_name, base_data, n_perturbations=10, epsilon=0.01):
    """Measure how sensitive each lens is to small perturbations.

    Perturb base_data by epsilon*std gaussian noise, re-scan, measure change.

    Returns dict: lens_name -> {mean_change, max_change, cv} for key metrics.
    """
    rng = np.random.RandomState(123)
    data_std = np.std(base_data) if np.std(base_data) > 1e-12 else 1.0
    noise_scale = epsilon * data_std

    # Get baseline
    base_results = {}
    for name in LENS_NAMES:
        _, scalars, _, err = run_single_lens(name, base_data)
        if err is None:
            base_results[name] = scalars

    # Perturb and measure
    perturbed_results = {name: [] for name in LENS_NAMES}
    for p in range(n_perturbations):
        noise = rng.randn(*base_data.shape) * noise_scale
        perturbed = base_data + noise
        for name in LENS_NAMES:
            _, scalars, _, err = run_single_lens(name, perturbed)
            if err is None:
                perturbed_results[name].append(scalars)

    # Compute sensitivity per lens
    sensitivity = {}
    for name in LENS_NAMES:
        base_s = base_results.get(name, {})
        pert_list = perturbed_results.get(name, [])
        if not base_s or not pert_list:
            sensitivity[name] = {"mean_change": 0.0, "cv": 0.0, "n_metrics": 0}
            continue

        changes = []
        cvs = []
        for mk in base_s:
            base_val = base_s[mk]
            pert_vals = [p.get(mk, base_val) for p in pert_list]
            if abs(base_val) > 1e-12:
                rel_changes = [abs(pv - base_val) / abs(base_val) for pv in pert_vals]
                changes.extend(rel_changes)
                if np.mean(pert_vals) != 0:
                    cvs.append(np.std(pert_vals) / (abs(np.mean(pert_vals)) + 1e-30))

        sensitivity[name] = {
            "mean_relative_change": float(np.mean(changes)) if changes else 0.0,
            "max_relative_change": float(np.max(changes)) if changes else 0.0,
            "cv": float(np.mean(cvs)) if cvs else 0.0,
            "n_metrics": len(base_s),
        }

    return sensitivity


def recommend_thresholds(all_results):
    """Recommend normal/anomalous thresholds for each lens key metric.

    Uses the distribution across data types to set:
      normal_range: [mean - 2*std, mean + 2*std] from non-degenerate data
      anomaly_threshold: value from degenerate or adversarial that differs most
    """
    # Gather values per metric across data types
    metric_vals = {}  # "lens.metric" -> {dtype: val}
    for dtype_name, lens_results in all_results.items():
        for lens_name, res in lens_results.items():
            for mk, mv in res.get("scalars", {}).items():
                key = f"{lens_name}.{mk}"
                metric_vals.setdefault(key, {})[dtype_name] = mv

    thresholds = {}
    for key, type_vals in sorted(metric_vals.items()):
        # Use non-degenerate types as "normal" reference
        normal_types = ["random", "structured", "consciousness_like"]
        normal_vals = [type_vals[t] for t in normal_types if t in type_vals]
        all_vals = list(type_vals.values())

        if not normal_vals:
            continue

        mean_n = np.mean(normal_vals)
        std_n = np.std(normal_vals) if len(normal_vals) > 1 else abs(mean_n) * 0.1

        # Degenerate / adversarial values
        deg_val = type_vals.get("degenerate", None)
        adv_val = type_vals.get("adversarial", None)

        thresholds[key] = {
            "normal_mean": float(mean_n),
            "normal_std": float(std_n),
            "normal_range": [float(mean_n - 2 * std_n), float(mean_n + 2 * std_n)],
            "degenerate_val": float(deg_val) if deg_val is not None else None,
            "adversarial_val": float(adv_val) if adv_val is not None else None,
            "all_values": {k: float(v) for k, v in type_vals.items()},
        }

    return thresholds


# ════════════════════════════════════════════════════════════
# SECTION 4: Console Report
# ════════════════════════════════════════════════════════════

def print_correlation_matrix(lens_corr):
    """Print 16x16 lens correlation matrix in ASCII."""
    flush_print("\n" + "=" * 80)
    flush_print("  16x16 LENS CORRELATION MATRIX (Pearson, averaged over metrics)")
    flush_print("=" * 80)

    # Abbreviated lens names (4 chars)
    abbr = ["cns", "top", "cau", "grv", "thm", "wav", "evo", "inf",
            "qnt", "em ", "rul", "tri", "cmp", "mir", "scl", "qms",
            "stb", "net", "mem", "rec", "bnd", "msc"]

    # Header
    flush_print(f"{'':>5s}", end="")
    for a in abbr:
        flush_print(f" {a:>4s}", end="")
    flush_print()
    flush_print("-" * (5 + 5 * len(abbr)))

    for i in range(len(LENS_NAMES)):
        flush_print(f"{abbr[i]:>4s}|", end="")
        for j in range(len(LENS_NAMES)):
            v = lens_corr[i, j]
            if np.isnan(v):
                flush_print("   . ", end="")
            elif i == j:
                flush_print("  1.0", end="")
            else:
                # Color-code: high positive = +, negative = -
                if v > 0.5:
                    sym = "++"
                elif v > 0.2:
                    sym = "+ "
                elif v < -0.5:
                    sym = "--"
                elif v < -0.2:
                    sym = "- "
                else:
                    sym = "  "
                flush_print(f" {v:+.1f}", end="")
        flush_print()

    flush_print("-" * (5 + 5 * len(abbr)))
    flush_print("Legend: >=+0.5 strong agree, <=-0.5 strong disagree, NaN = insufficient data")


def print_outlier_report(outlier_results):
    """Print outlier lens detection report."""
    flush_print("\n" + "=" * 80)
    flush_print("  OUTLIER LENS DETECTION")
    flush_print("=" * 80)
    flush_print(f"  {'Lens':22s} {'|abs_corr|':>10s} {'mean_corr':>10s} {'Verdict':>20s}")
    flush_print("-" * 80)
    for name, mean_abs, mean_signed, verdict in outlier_results:
        marker = " ***" if "OUTLIER" in verdict else ""
        flush_print(f"  {name:22s} {mean_abs:10.4f} {mean_signed:+10.4f} {verdict:>20s}{marker}")


def print_sensitivity_report(sensitivity_results):
    """Print sensitivity ranking."""
    flush_print("\n" + "=" * 80)
    flush_print("  SENSITIVITY ANALYSIS (epsilon=1% perturbation)")
    flush_print("=" * 80)

    # Sort by mean_relative_change descending
    items = sorted(sensitivity_results.items(), key=lambda x: -x[1].get("mean_relative_change", 0))
    flush_print(f"  {'Rank':>4s} {'Lens':22s} {'MeanRelChange':>14s} {'MaxRelChange':>14s} {'CV':>8s}")
    flush_print("-" * 70)
    for rank, (name, s) in enumerate(items, 1):
        mrc = s.get("mean_relative_change", 0)
        xrc = s.get("max_relative_change", 0)
        cv = s.get("cv", 0)
        bar = "#" * min(int(mrc * 100), 30)
        flush_print(f"  {rank:4d} {name:22s} {mrc:14.4f} {xrc:14.4f} {cv:8.4f}  {bar}")


def print_threshold_report(thresholds):
    """Print recommended thresholds."""
    flush_print("\n" + "=" * 80)
    flush_print("  RECOMMENDED THRESHOLDS (normal range from non-degenerate data)")
    flush_print("=" * 80)
    flush_print(f"  {'Metric':40s} {'Normal Mean':>12s} {'Normal Std':>12s} {'Range Low':>10s} {'Range High':>10s} {'Degen':>8s} {'Advers':>8s}")
    flush_print("-" * 100)

    for key in sorted(thresholds.keys()):
        t = thresholds[key]
        nm = t["normal_mean"]
        ns = t["normal_std"]
        lo, hi = t["normal_range"]
        dg = t.get("degenerate_val")
        av = t.get("adversarial_val")
        dg_s = f"{dg:.4g}" if dg is not None else "N/A"
        av_s = f"{av:.4g}" if av is not None else "N/A"
        flush_print(f"  {key:40s} {nm:12.4g} {ns:12.4g} {lo:10.4g} {hi:10.4g} {dg_s:>8s} {av_s:>8s}")


def print_consistency_summary(all_results):
    """Print per-data-type consistency summary."""
    flush_print("\n" + "=" * 80)
    flush_print("  CROSS-CONSISTENCY SUMMARY (all 16 lenses per data type)")
    flush_print("=" * 80)

    for dtype_name in all_results:
        lens_res = all_results[dtype_name]
        ok = sum(1 for r in lens_res.values() if "error" not in r)
        err = sum(1 for r in lens_res.values() if "error" in r)
        total_time = sum(r.get("elapsed", 0) for r in lens_res.values())
        n_scalars = sum(len(r.get("scalars", {})) for r in lens_res.values())
        flush_print(f"  {dtype_name:22s}  OK={ok:2d}  ERR={err:2d}  scalars={n_scalars:3d}  time={total_time:.2f}s")


# ════════════════════════════════════════════════════════════
# SECTION 5: JSON Serialization
# ════════════════════════════════════════════════════════════

def safe_json(obj):
    """Convert numpy types to JSON-safe Python types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [safe_json(v) for v in obj]
    elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    return obj


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="16-Lens Inter-Calibration")
    parser.add_argument("--quick", action="store_true", help="Only 3 data types (skip degenerate/adversarial)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--no-sensitivity", action="store_true", help="Skip sensitivity analysis (faster)")
    args = parser.parse_args()

    output_path = args.output or os.path.join(_DATA, "telescope_calibration_results.json")

    flush_print("=" * 80)
    flush_print("  TELESCOPE-RS 16-LENS INTER-CALIBRATION")
    flush_print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    flush_print("=" * 80)

    # Select data types
    if args.quick:
        gen_names = ["random", "structured", "consciousness_like"]
    else:
        gen_names = list(DATA_GENERATORS.keys())

    # ── Phase 1: Generate data & run all lenses ──────────────
    flush_print(f"\n[Phase 1] Generating {len(gen_names)} test datasets and running 16 lenses each...")
    all_results = {}
    total_t0 = time.time()

    for gi, gname in enumerate(gen_names):
        flush_print(f"\n--- [{gi+1}/{len(gen_names)}] Data type: {gname} ---")
        data = DATA_GENERATORS[gname]()
        flush_print(f"  shape={data.shape}  range=[{data.min():.4g}, {data.max():.4g}]  "
                     f"mean={data.mean():.4g}  std={data.std():.4g}")
        results = run_all_lenses(data, label=gname)
        all_results[gname] = results

    phase1_time = time.time() - total_t0
    flush_print(f"\n[Phase 1] Complete in {phase1_time:.1f}s")

    # ── Phase 2: Correlation matrix ──────────────────────────
    flush_print("\n[Phase 2] Computing correlation matrix...")
    metric_names, data_names, matrix = build_metric_matrix(all_results)
    flush_print(f"  Metric matrix: {matrix.shape} ({len(data_names)} data types x {len(metric_names)} metrics)")
    lens_corr, valid_metrics = compute_correlation_matrix(metric_names, matrix)

    # ── Phase 3: Outlier detection ───────────────────────────
    flush_print("[Phase 3] Detecting outlier lenses...")
    outlier_results = detect_outlier_lenses(lens_corr)

    # ── Phase 4: Sensitivity analysis ────────────────────────
    sensitivity_results = {}
    if not args.no_sensitivity:
        flush_print("\n[Phase 4] Sensitivity analysis (10 perturbations on consciousness_like data)...")
        sens_data = gen_consciousness_like()
        sensitivity_results = sensitivity_analysis("consciousness_like", sens_data,
                                                    n_perturbations=10, epsilon=0.01)
    else:
        flush_print("\n[Phase 4] Sensitivity analysis SKIPPED (--no-sensitivity)")

    # ── Phase 5: Threshold recommendations ───────────────────
    flush_print("[Phase 5] Computing threshold recommendations...")
    thresholds = recommend_thresholds(all_results)

    # ── Reports ──────────────────────────────────────────────
    print_consistency_summary(all_results)
    print_correlation_matrix(lens_corr)
    print_outlier_report(outlier_results)
    if sensitivity_results:
        print_sensitivity_report(sensitivity_results)
    print_threshold_report(thresholds)

    total_time = time.time() - total_t0

    # ── Save JSON ────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_time_s": total_time,
        "n_data_types": len(gen_names),
        "n_lenses": len(LENS_NAMES),
        "data_types": gen_names,
        "lens_names": LENS_NAMES,
        "all_results": all_results,
        "metric_names": metric_names,
        "metric_matrix": matrix.tolist(),
        "lens_correlation_matrix": lens_corr.tolist(),
        "outlier_detection": [
            {"lens": name, "mean_abs_corr": mac, "mean_signed_corr": msc, "verdict": v}
            for name, mac, msc, v in outlier_results
        ],
        "sensitivity": sensitivity_results,
        "thresholds": thresholds,
    }
    with open(output_path, "w") as f:
        json.dump(safe_json(output), f, indent=2, ensure_ascii=False)
    flush_print(f"\n[SAVED] {output_path}")

    # ── Final summary ────────────────────────────────────────
    flush_print("\n" + "=" * 80)
    flush_print("  CALIBRATION COMPLETE")
    flush_print(f"  Total time: {total_time:.1f}s")
    flush_print(f"  Data types: {len(gen_names)}")
    flush_print(f"  Lenses:     {len(LENS_NAMES)}")
    flush_print(f"  Metrics:    {len(metric_names)}")
    n_outlier = sum(1 for _, _, _, v in outlier_results if "OUTLIER" in v)
    flush_print(f"  Outlier lenses: {n_outlier}")
    if sensitivity_results:
        most_sensitive = max(sensitivity_results.items(),
                            key=lambda x: x[1].get("mean_relative_change", 0))
        least_sensitive = min(sensitivity_results.items(),
                             key=lambda x: x[1].get("mean_relative_change", 0))
        flush_print(f"  Most  sensitive: {most_sensitive[0]} "
                     f"(MRC={most_sensitive[1].get('mean_relative_change', 0):.4f})")
        flush_print(f"  Least sensitive: {least_sensitive[0]} "
                     f"(MRC={least_sensitive[1].get('mean_relative_change', 0):.4f})")
    flush_print(f"  Results: {output_path}")
    flush_print("=" * 80)


if __name__ == "__main__":
    main()
