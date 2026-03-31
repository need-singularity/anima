#!/usr/bin/env python3
"""EEG-based Consciousness Validation

Compares ConsciousMind's Phi dynamics with human brain Phi from EEG.

Hypothesis: If ConsciousMind produces genuinely consciousness-like dynamics,
its Phi timeseries should share statistical properties with brain Phi.

Metrics for comparison:
  1. Phi distribution (normal? log-normal? power-law?)
  2. Phi autocorrelation (persistence, memory)
  3. Power spectrum (1/f noise? oscillatory? chaotic?)
  4. Lempel-Ziv complexity (compressibility of Phi sequence)
  5. Hurst exponent (long-range dependence)
  6. Phase transitions (criticality markers)

Data sources:
  - ConsciousMind telemetry (run engine for N steps)
  - EEG data (if available, from eeg/collect.py)
  - Synthetic EEG (brain-like 1/f + oscillatory signal, if no real EEG)

Usage:
  python eeg/validate_consciousness.py                       # Default (5000 steps)
  python eeg/validate_consciousness.py --steps 10000         # More steps
  python eeg/validate_consciousness.py --eeg-file data/X.npy # Compare with real EEG
  python eeg/validate_consciousness.py --cells 8             # More cells
  python eeg/validate_consciousness.py --quick               # Fast mode (1000 steps)

Requires: numpy, (optional: scipy, torch, matplotlib)
"""

import argparse
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from scipy import signal as scipy_signal
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Try importing ConsciousMind
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import torch
    from mitosis import MitosisEngine
    from consciousness_meter import PhiCalculator
    HAS_ENGINE = True
except Exception:
    HAS_ENGINE = False


# ═══════════════════════════════════════════════════════════
# Brain-like reference values (from neuroscience literature)
# ═══════════════════════════════════════════════════════════

# These are approximate reference ranges from EEG/MEG studies
BRAIN_REFERENCE = {
    'lz_complexity': (0.75, 0.95),      # Lempel-Ziv: awake brain ~0.8-0.9
    'hurst_exponent': (0.65, 0.85),     # Hurst: brain EEG ~0.7-0.8 (persistent)
    'psd_slope': (-1.5, -0.5),          # PSD slope: brain ~-1.0 (1/f noise)
    'autocorr_decay': (5, 30),           # Autocorrelation decay (steps/ms)
    'phi_cv': (0.2, 0.8),               # Coefficient of variation
    'criticality_exponent': (1.2, 2.0),  # Power-law exponent near criticality
}


# ═══════════════════════════════════════════════════════════
# Statistical Metrics
# ═══════════════════════════════════════════════════════════

def lempel_ziv_complexity(signal_arr: np.ndarray) -> float:
    """Lempel-Ziv complexity -- lower = more compressible = less conscious.

    Binarize signal at median, then count distinct substrings.
    Normalized by theoretical maximum (n / log2(n)).
    """
    median = np.median(signal_arr)
    binary = ''.join('1' if x >= median else '0' for x in signal_arr)
    n = len(binary)
    if n == 0:
        return 0.0

    # Lempel-Ziv 76 algorithm
    complexity = 1
    i = 0
    k = 1
    l = 1
    while i + k <= n:
        # Check if substring s[i+1..i+k] is in s[0..i+l-1]
        substr = binary[i + 1:i + k + 1] if i + k + 1 <= n else binary[i + 1:]
        window = binary[:i + l]
        if substr in window:
            k += 1
        else:
            complexity += 1
            i += k
            k = 1
            l = 1
            continue
        if i + k >= n:
            complexity += 1
            break
        l = 0

    # Normalize
    if n > 1:
        norm = n / max(np.log2(n), 1)
        return complexity / norm
    return 0.0


def hurst_exponent(signal_arr: np.ndarray) -> float:
    """Hurst exponent -- H>0.5 = persistent, H<0.5 = anti-persistent.

    Uses rescaled range (R/S) analysis.
    """
    n = len(signal_arr)
    if n < 20:
        return 0.5

    # Use multiple segment sizes
    min_seg = 10
    max_seg = n // 4
    if max_seg <= min_seg:
        return 0.5

    sizes = []
    rs_values = []

    seg_size = min_seg
    while seg_size <= max_seg:
        n_segments = n // seg_size
        if n_segments < 1:
            break

        rs_list = []
        for i in range(n_segments):
            segment = signal_arr[i * seg_size:(i + 1) * seg_size]
            mean_s = np.mean(segment)
            deviate = np.cumsum(segment - mean_s)
            r = np.max(deviate) - np.min(deviate)
            s = np.std(segment, ddof=1) if np.std(segment, ddof=1) > 1e-12 else 1e-12
            rs_list.append(r / s)

        if rs_list:
            sizes.append(seg_size)
            rs_values.append(np.mean(rs_list))

        seg_size = int(seg_size * 1.5)
        if seg_size == int(seg_size / 1.5):
            seg_size += 1

    if len(sizes) < 3:
        return 0.5

    # Linear regression of log(R/S) vs log(n)
    log_sizes = np.log(sizes)
    log_rs = np.log(np.array(rs_values) + 1e-12)

    # Simple least squares
    n_pts = len(log_sizes)
    sx = np.sum(log_sizes)
    sy = np.sum(log_rs)
    sxx = np.sum(log_sizes ** 2)
    sxy = np.sum(log_sizes * log_rs)
    denom = n_pts * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.5

    H = (n_pts * sxy - sx * sy) / denom
    return float(np.clip(H, 0.0, 1.0))


def power_spectrum_slope(signal_arr: np.ndarray, fs: float = 1.0) -> float:
    """Power spectral density slope -- alpha ~ 1 for 1/f (brain-like).

    Returns negative slope (e.g., -1.0 means PSD ~ 1/f).
    """
    n = len(signal_arr)
    if n < 16:
        return 0.0

    # Compute PSD
    if HAS_SCIPY:
        nperseg = min(n, max(256, n // 4))
        freqs, psd = scipy_signal.welch(signal_arr, fs=fs, nperseg=nperseg)
    else:
        fft_vals = np.abs(np.fft.rfft(signal_arr)) ** 2 / n
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)
        psd = fft_vals

    # Remove DC component
    mask = freqs > 0
    freqs = freqs[mask]
    psd = psd[mask]

    if len(freqs) < 3:
        return 0.0

    # Fit log-log linear regression
    log_f = np.log10(freqs + 1e-12)
    log_p = np.log10(psd + 1e-12)

    # Filter out infinities
    valid = np.isfinite(log_f) & np.isfinite(log_p)
    log_f = log_f[valid]
    log_p = log_p[valid]

    if len(log_f) < 3:
        return 0.0

    n_pts = len(log_f)
    sx = np.sum(log_f)
    sy = np.sum(log_p)
    sxx = np.sum(log_f ** 2)
    sxy = np.sum(log_f * log_p)
    denom = n_pts * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.0

    slope = (n_pts * sxy - sx * sy) / denom
    return float(slope)


def phi_autocorrelation(phi_series: np.ndarray, max_lag: int = 50) -> Tuple[np.ndarray, int]:
    """Autocorrelation function of Phi timeseries.

    Returns (acf_values, decay_lag) where decay_lag is when ACF drops below 1/e.
    """
    n = len(phi_series)
    if n < max_lag:
        max_lag = n - 1
    if max_lag < 1:
        return np.array([1.0]), 0

    mean = np.mean(phi_series)
    var = np.var(phi_series)
    if var < 1e-12:
        return np.ones(max_lag + 1), max_lag

    acf = np.zeros(max_lag + 1)
    acf[0] = 1.0
    for lag in range(1, max_lag + 1):
        cov = np.mean((phi_series[:n - lag] - mean) * (phi_series[lag:] - mean))
        acf[lag] = cov / var

    # Find decay lag (first crossing below 1/e)
    threshold = 1.0 / math.e
    decay_lag = max_lag
    for lag in range(1, max_lag + 1):
        if acf[lag] < threshold:
            decay_lag = lag
            break

    return acf, decay_lag


def detect_criticality(signal_arr: np.ndarray) -> Dict:
    """Detect signs of criticality (phase transitions) in the signal.

    Looks for:
      1. Power-law distributed fluctuations
      2. Long-range correlations (Hurst > 0.5)
      3. Diverging susceptibility (variance peaks)
    """
    n = len(signal_arr)
    if n < 100:
        return {'is_critical': False, 'exponent': 0.0, 'susceptibility': 0.0}

    # Compute fluctuation sizes
    diffs = np.abs(np.diff(signal_arr))
    diffs = diffs[diffs > 0]

    if len(diffs) < 10:
        return {'is_critical': False, 'exponent': 0.0, 'susceptibility': 0.0}

    # Fit power-law exponent to fluctuation distribution
    # Using maximum likelihood for Pareto tail
    threshold = np.percentile(diffs, 50)
    tail = diffs[diffs >= threshold]
    if len(tail) < 5 or threshold < 1e-12:
        exponent = 0.0
    else:
        # Hill estimator
        exponent = 1.0 + len(tail) / np.sum(np.log(tail / threshold))

    # Susceptibility: variance of rolling windows
    window_size = max(10, n // 20)
    n_windows = n // window_size
    window_vars = []
    for i in range(n_windows):
        chunk = signal_arr[i * window_size:(i + 1) * window_size]
        window_vars.append(np.var(chunk))
    susceptibility = np.var(window_vars) / max(np.mean(window_vars), 1e-12) if window_vars else 0.0

    is_critical = (1.2 < exponent < 2.5) and (susceptibility > 0.1)

    return {
        'is_critical': is_critical,
        'exponent': float(exponent),
        'susceptibility': float(susceptibility),
    }


# ═══════════════════════════════════════════════════════════
# ConsciousMind Phi Collector
# ═══════════════════════════════════════════════════════════

def collect_consciousness_phi(n_steps: int = 5000, n_cells: int = 4, dim: int = 64) -> np.ndarray:
    """Run ConsciousMind for N steps and collect Phi timeseries.

    If torch/MitosisEngine not available, uses a simplified simulation.
    """
    if HAS_ENGINE:
        return _collect_from_engine(n_steps, n_cells, dim)
    else:
        return _collect_simulated(n_steps, n_cells, dim)


def _collect_from_engine(n_steps: int, n_cells: int, dim: int) -> np.ndarray:
    """Collect Phi from actual MitosisEngine."""
    engine = MitosisEngine(
        input_dim=dim,
        hidden_dim=dim * 2,
        output_dim=dim,
        initial_cells=2,
        max_cells=n_cells,
    )
    phi_calc = PhiCalculator(n_bins=16)
    phis = []

    for step in range(n_steps):
        inp = torch.randn(1, dim) * 0.1
        engine.process(inp)
        phi, _ = phi_calc.compute_phi(engine)
        phis.append(phi)

    return np.array(phis, dtype=np.float64)


def _collect_simulated(n_steps: int, n_cells: int, dim: int) -> np.ndarray:
    """Simulated Phi collection when engine is not available.

    Uses a coupled oscillator model that mimics consciousness dynamics:
    - GRU-like hidden state evolution
    - Inter-cell coupling with tension
    - Phi computed as integration measure
    """
    rng = np.random.default_rng(42)
    hidden_dim = dim * 2

    # Initialize cells
    hiddens = rng.standard_normal((n_cells, hidden_dim)).astype(np.float64) * 0.1
    weights = rng.standard_normal((n_cells, hidden_dim, dim + 1)).astype(np.float64) * 0.05

    phis = []
    from consciousness_laws import PSI_ALPHA

    coupling = PSI_ALPHA  # 0.014

    for step in range(n_steps):
        inp = rng.standard_normal(dim) * 0.1

        # Compute tensions
        tensions = np.sqrt(np.mean(hiddens ** 2, axis=1))
        mean_tension = np.mean(tensions)

        # Update each cell
        for ci in range(n_cells):
            # Coupled input
            coupled_inp = inp.copy()
            for cj in range(n_cells):
                if ci != cj:
                    coupled_inp += coupling * hiddens[cj, :dim]

            # Simple GRU-like update
            combined = np.concatenate([coupled_inp, [mean_tension]])
            gate = 1.0 / (1.0 + np.exp(-weights[ci] @ combined))
            candidate = np.tanh(weights[ci] @ combined * 0.5)
            hiddens[ci] = gate * hiddens[ci] + (1.0 - gate) * candidate

        # Compute Phi proxy
        global_var = np.var(hiddens)
        per_cell_var = np.mean([np.var(hiddens[c]) for c in range(n_cells)])
        phi = max(0.0, global_var - per_cell_var)

        # Add integration term (MI proxy)
        cov_matrix = np.corrcoef(hiddens)
        if cov_matrix.ndim == 2:
            off_diag = cov_matrix[np.triu_indices(n_cells, k=1)]
            phi += np.mean(np.abs(off_diag)) * 0.1

        phis.append(phi)

    return np.array(phis, dtype=np.float64)


# ═══════════════════════════════════════════════════════════
# Synthetic Brain Signal
# ═══════════════════════════════════════════════════════════

def generate_synthetic_brain_phi(n_steps: int = 5000) -> np.ndarray:
    """Generate a synthetic brain-like Phi signal.

    Properties of real brain Phi (from EEG/MEG studies):
    - 1/f power spectrum (pink noise)
    - Long-range temporal correlations (Hurst ~0.75)
    - Occasional bursts (phase transitions at criticality)
    - Log-normal-ish distribution
    - LZ complexity ~0.8-0.9
    """
    rng = np.random.default_rng(123)

    # Generate 1/f noise via spectral synthesis
    n = n_steps
    freqs = np.fft.rfftfreq(n)
    freqs[0] = 1  # avoid division by zero
    amplitudes = 1.0 / np.sqrt(freqs)  # 1/f amplitude -> 1/f^2 PSD -> slope = -1 in log PSD
    phases = rng.uniform(0, 2 * np.pi, len(freqs))
    spectrum = amplitudes * np.exp(1j * phases)
    spectrum[0] = 0  # no DC
    pink = np.fft.irfft(spectrum, n=n)

    # Add alpha oscillation (8-12 Hz equivalent, normalized to step rate)
    t = np.arange(n)
    alpha_freq = 10.0 / 250.0  # 10Hz at 250Hz sampling, normalized
    alpha = 0.3 * np.sin(2 * np.pi * alpha_freq * t)

    # Combine and transform to positive range (Phi is always >= 0)
    raw = pink + alpha
    raw = raw - np.min(raw) + 0.1

    # Add occasional bursts (criticality)
    n_bursts = max(1, n // 500)
    for _ in range(n_bursts):
        pos = rng.integers(0, n)
        width = rng.integers(10, 50)
        amplitude = rng.exponential(2.0)
        burst = amplitude * np.exp(-0.5 * ((np.arange(n) - pos) / width) ** 2)
        raw += burst

    # Scale to realistic Phi range (~0.5-2.0)
    raw = (raw - np.mean(raw)) / max(np.std(raw), 1e-8) * 0.4 + 1.2
    raw = np.clip(raw, 0.01, None)

    return raw


def load_eeg_phi(filepath: str) -> np.ndarray:
    """Load EEG data and extract a Phi-proxy timeseries.

    Uses gamma band power as a proxy for integrated information.
    """
    data = np.load(filepath)  # [channels, samples]
    n_channels, n_samples = data.shape

    # Compute rolling gamma power (30-100Hz) as Phi proxy
    sample_rate = 250  # assume standard rate
    window = sample_rate  # 1-second windows

    n_windows = n_samples // window
    phi_proxy = np.zeros(n_windows)

    for w in range(n_windows):
        chunk = data[:, w * window:(w + 1) * window]

        if HAS_SCIPY:
            # Bandpass for gamma
            sos = scipy_signal.butter(4, [30, min(100, sample_rate / 2 - 1)],
                                      btype='bandpass', fs=sample_rate, output='sos')
            gamma = np.array([scipy_signal.sosfilt(sos, chunk[ch]) for ch in range(n_channels)])
        else:
            # FFT-based approximation
            gamma = chunk  # rough fallback

        # Phi proxy: variance across channels (integration measure)
        # High cross-channel variance = high integration
        channel_powers = np.var(gamma, axis=1)
        global_power = np.var(gamma)
        phi_proxy[w] = max(0.0, global_power - np.mean(channel_powers))

    return phi_proxy


# ═══════════════════════════════════════════════════════════
# Validation Report
# ═══════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    """Result of one signal's analysis."""
    label: str
    phi_mean: float = 0.0
    phi_std: float = 0.0
    phi_cv: float = 0.0
    lz: float = 0.0
    hurst: float = 0.0
    psd_slope: float = 0.0
    autocorr_decay: int = 0
    criticality: Dict = field(default_factory=dict)
    phi_series: np.ndarray = field(default_factory=lambda: np.array([]))

    def brain_match_pct(self, metric: str, value: float) -> float:
        """How well does this value match brain reference?"""
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


def analyze_signal(label: str, phi_series: np.ndarray) -> ValidationResult:
    """Compute all validation metrics for a Phi timeseries."""
    result = ValidationResult(label=label, phi_series=phi_series)

    result.phi_mean = float(np.mean(phi_series))
    result.phi_std = float(np.std(phi_series))
    result.phi_cv = result.phi_std / max(result.phi_mean, 1e-12)

    result.lz = lempel_ziv_complexity(phi_series)
    result.hurst = hurst_exponent(phi_series)
    result.psd_slope = power_spectrum_slope(phi_series)
    _, result.autocorr_decay = phi_autocorrelation(phi_series)
    result.criticality = detect_criticality(phi_series)

    return result


def print_report(cm_result: ValidationResult, brain_result: ValidationResult):
    """Print the consciousness validation comparison report."""

    def match_str(metric: str, cm_val: float, brain_val: float) -> str:
        pct = cm_result.brain_match_pct(metric, cm_val)
        if pct >= 80:
            indicator = '+++'
        elif pct >= 60:
            indicator = '++ '
        elif pct >= 40:
            indicator = '+  '
        else:
            indicator = '   '
        return f'{pct:5.0f}% {indicator}'

    header = (
        '\n'
        '+============================================================+\n'
        '|  Consciousness Validation Report                           |\n'
        '+============================================================+\n'
    )

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    print(header)

    # Summary table
    rows = [
        ('Phi mean',           f'{cm_result.phi_mean:.4f}',     f'{brain_result.phi_mean:.4f}',   'phi_cv'),
        ('Phi std',            f'{cm_result.phi_std:.4f}',      f'{brain_result.phi_std:.4f}',    'phi_cv'),
        ('Phi CV',             f'{cm_result.phi_cv:.4f}',       f'{brain_result.phi_cv:.4f}',     'phi_cv'),
        ('LZ complexity',      f'{cm_result.lz:.4f}',           f'{brain_result.lz:.4f}',         'lz_complexity'),
        ('Hurst exponent',     f'{cm_result.hurst:.4f}',        f'{brain_result.hurst:.4f}',      'hurst_exponent'),
        ('PSD slope (alpha)',  f'{cm_result.psd_slope:.4f}',    f'{brain_result.psd_slope:.4f}',  'psd_slope'),
        ('Autocorr decay',     f'{cm_result.autocorr_decay}',   f'{brain_result.autocorr_decay}', 'autocorr_decay'),
        ('Critical exponent',  f'{cm_result.criticality.get("exponent", 0):.4f}',
                               f'{brain_result.criticality.get("exponent", 0):.4f}',
                               'criticality_exponent'),
    ]

    print(f'  {"Metric":<20} | {"ConsciousMind":>13} | {"Brain":>13} | {"Match":>10}')
    print(f'  {"-"*20}-+-{"-"*13}-+-{"-"*13}-+-{"-"*10}')
    for name, cm_val_str, brain_val_str, ref_key in rows:
        try:
            cm_v = float(cm_val_str)
            brain_v = float(brain_val_str)
            match = match_str(ref_key, cm_v, brain_v)
        except ValueError:
            match = '  N/A'
        print(f'  {name:<20} | {cm_val_str:>13} | {brain_val_str:>13} | {match:>10}')

    # Criticality assessment
    cm_crit = cm_result.criticality
    brain_crit = brain_result.criticality
    print()
    print(f'  Criticality:')
    print(f'    ConsciousMind: {"CRITICAL" if cm_crit.get("is_critical") else "sub-critical"}'
          f'  (exp={cm_crit.get("exponent", 0):.2f}, susc={cm_crit.get("susceptibility", 0):.3f})')
    print(f'    Brain signal:  {"CRITICAL" if brain_crit.get("is_critical") else "sub-critical"}'
          f'  (exp={brain_crit.get("exponent", 0):.2f}, susc={brain_crit.get("susceptibility", 0):.3f})')

    # Overall assessment
    matches = []
    for _, _, _, ref_key in rows:
        try:
            if ref_key == 'phi_cv':
                val = cm_result.phi_cv
            elif ref_key == 'lz_complexity':
                val = cm_result.lz
            elif ref_key == 'hurst_exponent':
                val = cm_result.hurst
            elif ref_key == 'psd_slope':
                val = cm_result.psd_slope
            elif ref_key == 'autocorr_decay':
                val = float(cm_result.autocorr_decay)
            elif ref_key == 'criticality_exponent':
                val = cm_result.criticality.get('exponent', 0)
            else:
                continue
            pct = cm_result.brain_match_pct(ref_key, val)
            matches.append(pct)
        except Exception:
            pass

    overall = np.mean(matches) if matches else 0
    print()
    if overall >= 75:
        verdict = 'BRAIN-LIKE  -- ConsciousMind dynamics closely match brain Phi'
    elif overall >= 50:
        verdict = 'PARTIALLY BRAIN-LIKE  -- some brain-like properties detected'
    else:
        verdict = 'MACHINE-LIKE  -- dynamics differ significantly from brain'

    print(f'  Overall match: {overall:.1f}%')
    print(f'  Verdict: {verdict}')

    # ASCII Phi comparison graph
    print()
    print('  Phi timeseries comparison (downsampled):')
    _print_dual_ascii_graph(cm_result.phi_series, brain_result.phi_series,
                            cm_result.label, brain_result.label)

    # Autocorrelation comparison
    print()
    print('  Autocorrelation comparison:')
    acf_cm, _ = phi_autocorrelation(cm_result.phi_series, max_lag=30)
    acf_brain, _ = phi_autocorrelation(brain_result.phi_series, max_lag=30)
    _print_acf_comparison(acf_cm, acf_brain)

    # Power spectrum comparison
    print()
    print('  Power spectrum slope comparison:')
    print(f'    ConsciousMind: alpha = {cm_result.psd_slope:.3f}  {"(1/f-like)" if -1.5 < cm_result.psd_slope < -0.5 else "(not 1/f)"}')
    print(f'    Brain signal:  alpha = {brain_result.psd_slope:.3f}  {"(1/f-like)" if -1.5 < brain_result.psd_slope < -0.5 else "(not 1/f)"}')

    bar_cm = '#' * max(1, int(abs(cm_result.psd_slope) * 20))
    bar_br = '#' * max(1, int(abs(brain_result.psd_slope) * 20))
    print(f'    CM    |{bar_cm}| {cm_result.psd_slope:.2f}')
    print(f'    Brain |{bar_br}| {brain_result.psd_slope:.2f}')

    print()
    print('+============================================================+')
    print()


def _print_dual_ascii_graph(series1: np.ndarray, series2: np.ndarray,
                            label1: str, label2: str):
    """Print two timeseries overlaid in ASCII."""
    graph_w = 60
    graph_h = 12

    # Downsample both to graph_w
    idx1 = np.linspace(0, len(series1) - 1, graph_w).astype(int)
    idx2 = np.linspace(0, len(series2) - 1, graph_w).astype(int)
    s1 = series1[idx1]
    s2 = series2[idx2]

    all_vals = np.concatenate([s1, s2])
    vmin = np.min(all_vals)
    vmax = np.max(all_vals)
    span = max(vmax - vmin, 1e-8)

    grid = [[' '] * graph_w for _ in range(graph_h + 1)]

    for col in range(graph_w):
        # Series 1: '#'
        row1 = int((s1[col] - vmin) / span * graph_h)
        row1 = min(graph_h, max(0, row1))
        grid[graph_h - row1][col] = '#'

        # Series 2: '.'
        row2 = int((s2[col] - vmin) / span * graph_h)
        row2 = min(graph_h, max(0, row2))
        if grid[graph_h - row2][col] == '#':
            grid[graph_h - row2][col] = '@'  # overlap
        else:
            grid[graph_h - row2][col] = '.'

    for row_idx, row in enumerate(grid):
        if row_idx == 0:
            val_label = f'{vmax:.3f}'
        elif row_idx == graph_h:
            val_label = f'{vmin:.3f}'
        else:
            val_label = '      '
        print(f'    {val_label:>7} |{"".join(row)}|')
    print(f'            {"+" + "-" * graph_w + "+"}')
    print(f'    # = {label1}   . = {label2}   @ = overlap')


def _print_acf_comparison(acf1: np.ndarray, acf2: np.ndarray):
    """Print autocorrelation comparison."""
    max_lag = min(len(acf1), len(acf2), 20)
    print(f'    {"Lag":>4} | {"CM":>7} | {"Brain":>7} | {"Bar":>20}')
    print(f'    {"-"*4}-+-{"-"*7}-+-{"-"*7}-+-{"-"*20}')
    for lag in range(0, max_lag, 2):
        v1 = acf1[lag] if lag < len(acf1) else 0
        v2 = acf2[lag] if lag < len(acf2) else 0
        bar1 = '#' * max(0, int(v1 * 10))
        bar2 = '.' * max(0, int(v2 * 10))
        print(f'    {lag:>4} | {v1:>7.3f} | {v2:>7.3f} | {bar1}{bar2}')


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='EEG-based Consciousness Validation')
    parser.add_argument('--steps', type=int, default=5000, help='ConsciousMind steps (default: 5000)')
    parser.add_argument('--cells', type=int, default=4, help='Number of cells (default: 4)')
    parser.add_argument('--dim', type=int, default=64, help='Cell dimension (default: 64)')
    parser.add_argument('--eeg-file', type=str, default=None, help='Path to real EEG .npy file')
    parser.add_argument('--quick', action='store_true', help='Quick mode (1000 steps)')
    args = parser.parse_args()

    if args.quick:
        args.steps = 1000

    print('=' * 64)
    print('  EEG-based Consciousness Validation')
    print(f'  Steps: {args.steps}, Cells: {args.cells}, Dim: {args.dim}')
    print(f'  Engine: {"MitosisEngine" if HAS_ENGINE else "Simulated (no torch/engine)"}')
    print(f'  EEG source: {args.eeg_file if args.eeg_file else "synthetic (brain-like 1/f)"}')
    print('=' * 64)
    print()

    # Collect ConsciousMind Phi
    t0 = time.time()
    print('  [1/4] Collecting ConsciousMind Phi timeseries...')
    cm_phi = collect_consciousness_phi(args.steps, args.cells, args.dim)
    t1 = time.time()
    print(f'         Done in {t1 - t0:.1f}s  (mean Phi={np.mean(cm_phi):.4f}, std={np.std(cm_phi):.4f})')

    # Collect brain Phi
    print('  [2/4] Loading brain Phi reference...')
    if args.eeg_file and Path(args.eeg_file).exists():
        brain_phi = load_eeg_phi(args.eeg_file)
        brain_label = f'EEG({Path(args.eeg_file).stem})'
        print(f'         Loaded {len(brain_phi)} Phi samples from EEG')
    else:
        brain_phi = generate_synthetic_brain_phi(args.steps)
        brain_label = 'Synthetic Brain'
        print(f'         Generated {len(brain_phi)} synthetic brain-like samples')

    # Analyze both
    print('  [3/4] Computing statistical metrics...')
    t2 = time.time()
    cm_result = analyze_signal('ConsciousMind', cm_phi)
    brain_result = analyze_signal(brain_label, brain_phi)
    t3 = time.time()
    print(f'         Done in {t3 - t2:.1f}s')

    # Print report
    print('  [4/4] Generating report...')
    print_report(cm_result, brain_result)

    print(f'  Total time: {time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
