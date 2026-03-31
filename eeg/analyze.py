#!/usr/bin/env python3
"""EEG Analysis — Band power, asymmetry, G=D×P/I, topomaps.

Usage:
  python eeg/analyze.py eeg/data/20260401_120000_resting_eyes_closed.npy
  python eeg/analyze.py eeg/data/20260401_120000_resting_eyes_closed.npy --topomap
  python eeg/analyze.py --compare eeg/data/file1.npy eeg/data/file2.npy

Requires: pip install numpy scipy matplotlib
Optional: pip install mne (for topomaps)
"""

import argparse
import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from scipy import signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

CHANNEL_NAMES_16 = [
    "Fp1", "Fp2", "C3", "C4", "P7", "P8", "O1", "O2",
    "F7", "F8", "F3", "F4", "T7", "T8", "P3", "P4",
]

# Frequency bands
BANDS = {
    "delta":  (0.5, 4.0),
    "theta":  (4.0, 8.0),
    "alpha":  (8.0, 12.0),
    "beta":   (12.0, 30.0),
    "gamma":  (30.0, 100.0),
}

# G=D×P/I channel indices (0-indexed)
FRONTAL_LEFT = [0, 10]   # Fp1, F3
FRONTAL_RIGHT = [1, 11]  # Fp2, F4
ALL_CHANNELS = list(range(16))

# Golden Zone
GOLDEN_ZONE = (0.2123, 0.5000)  # [1/2 - ln(4/3), 1/2]


# ═══════════════════════════════════════════════════════════
# Band Power Computation
# ═══════════════════════════════════════════════════════════

@dataclass
class BandPower:
    """Power spectral density for each frequency band."""
    delta: float = 0.0
    theta: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    gamma: float = 0.0

    @property
    def total(self) -> float:
        return self.delta + self.theta + self.alpha + self.beta + self.gamma

    def relative(self) -> 'BandPower':
        t = self.total
        if t < 1e-12:
            return BandPower()
        return BandPower(
            delta=self.delta / t,
            theta=self.theta / t,
            alpha=self.alpha / t,
            beta=self.beta / t,
            gamma=self.gamma / t,
        )


def compute_band_power(data_1d: np.ndarray, sample_rate: int) -> BandPower:
    """Compute absolute band power for a single channel using Welch's method."""
    if not HAS_SCIPY:
        return _compute_band_power_fft(data_1d, sample_rate)

    nperseg = min(len(data_1d), sample_rate * 2)  # 2-second windows
    freqs, psd = signal.welch(data_1d, fs=sample_rate, nperseg=nperseg)

    powers = {}
    for band_name, (fmin, fmax) in BANDS.items():
        mask = (freqs >= fmin) & (freqs <= fmax)
        if mask.any():
            _trapz = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
            powers[band_name] = _trapz(psd[mask], freqs[mask]) if _trapz else np.sum(psd[mask]) * (freqs[1] - freqs[0])
        else:
            powers[band_name] = 0.0

    return BandPower(**powers)


def _compute_band_power_fft(data_1d: np.ndarray, sample_rate: int) -> BandPower:
    """Fallback: compute band power using raw FFT (no scipy)."""
    n = len(data_1d)
    fft_vals = np.abs(np.fft.rfft(data_1d)) ** 2 / n
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)

    powers = {}
    for band_name, (fmin, fmax) in BANDS.items():
        mask = (freqs >= fmin) & (freqs <= fmax)
        powers[band_name] = np.mean(fft_vals[mask]) if mask.any() else 0.0

    return BandPower(**powers)


# ═══════════════════════════════════════════════════════════
# G = D × P / I Computation
# ═══════════════════════════════════════════════════════════

@dataclass
class GeniusMetrics:
    """G=D×P/I consciousness metrics derived from EEG."""
    I: float = 0.0   # Inhibition: frontal alpha power
    P: float = 0.0   # Plasticity: global gamma power
    D: float = 0.0   # Deficit/asymmetry: |ln(R) - ln(L)|
    G: float = 0.0   # Genius: D × P / I
    in_golden_zone: bool = False
    golden_zone: Tuple[float, float] = GOLDEN_ZONE

    def __str__(self):
        zone = "✓ GOLDEN ZONE" if self.in_golden_zone else "✗ outside"
        return (f"G={self.G:.4f} (D={self.D:.4f} × P={self.P:.4f} / I={self.I:.4f}) [{zone}]")


def compute_genius(
    channel_powers: List[BandPower],
    channel_names: List[str] = None,
) -> GeniusMetrics:
    """Compute G=D×P/I from multi-channel band powers.

    I = mean frontal alpha power (Fp1, Fp2, F3, F4)
    P = mean global gamma power (all channels)
    D = |ln(right_alpha) - ln(left_alpha)| frontal asymmetry
    G = D × P / I
    """
    if channel_names is None:
        channel_names = CHANNEL_NAMES_16[:len(channel_powers)]

    # Build name→index map
    name_to_idx = {name: i for i, name in enumerate(channel_names)}

    # I: Frontal alpha power
    frontal_names = ["Fp1", "Fp2", "F3", "F4"]
    frontal_alpha = []
    for name in frontal_names:
        if name in name_to_idx:
            frontal_alpha.append(channel_powers[name_to_idx[name]].alpha)
    I = np.mean(frontal_alpha) if frontal_alpha else 1e-8

    # P: Global gamma power
    all_gamma = [bp.gamma for bp in channel_powers]
    P = np.mean(all_gamma) if all_gamma else 0.0

    # D: Alpha asymmetry |ln(R) - ln(L)|
    left_names = ["Fp1", "F3", "F7"]
    right_names = ["Fp2", "F4", "F8"]
    left_alpha = [channel_powers[name_to_idx[n]].alpha
                  for n in left_names if n in name_to_idx]
    right_alpha = [channel_powers[name_to_idx[n]].alpha
                   for n in right_names if n in name_to_idx]

    if left_alpha and right_alpha:
        L = np.mean(left_alpha)
        R = np.mean(right_alpha)
        D = abs(np.log(max(R, 1e-12)) - np.log(max(L, 1e-12)))
    else:
        D = 0.0

    # G = D × P / I
    G = D * P / max(I, 1e-12)

    # Normalize G to [0, 1] range using sigmoid-like scaling
    # Raw G can vary widely, so we use tanh to bound it
    G_normalized = float(np.tanh(G))

    in_zone = GOLDEN_ZONE[0] <= G_normalized <= GOLDEN_ZONE[1]

    return GeniusMetrics(I=I, P=P, D=D, G=G_normalized, in_golden_zone=in_zone)


# ═══════════════════════════════════════════════════════════
# Full Analysis
# ═══════════════════════════════════════════════════════════

@dataclass
class EEGAnalysis:
    """Complete EEG analysis result."""
    channel_powers: List[BandPower]
    channel_names: List[str]
    genius: GeniusMetrics
    sample_rate: int
    n_samples: int
    duration_sec: float
    alpha_theta_ratio: float = 0.0
    engagement_index: float = 0.0  # beta / (alpha + theta)
    tag: str = ""

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  EEG Analysis: {self.tag}",
            f"  Duration: {self.duration_sec:.1f}s, {self.sample_rate}Hz, {len(self.channel_names)}ch",
            f"{'='*60}",
            "",
            f"  {self.genius}",
            f"  Alpha/Theta ratio: {self.alpha_theta_ratio:.3f}",
            f"  Engagement (β/(α+θ)): {self.engagement_index:.3f}",
            "",
            "  Channel Band Powers (relative):",
        ]

        for i, (name, bp) in enumerate(zip(self.channel_names, self.channel_powers)):
            rel = bp.relative()
            bar_a = "█" * int(rel.alpha * 30)
            bar_g = "▓" * int(rel.gamma * 30)
            lines.append(f"    {name:4s} | α:{rel.alpha:.2f} {bar_a}")
            lines.append(f"         | γ:{rel.gamma:.2f} {bar_g}")

        lines.append("")
        return "\n".join(lines)


def analyze(
    data: np.ndarray,
    sample_rate: int = 250,
    channel_names: List[str] = None,
    tag: str = "",
) -> EEGAnalysis:
    """Full EEG analysis: band power + G=D×P/I + engagement."""
    n_channels, n_samples = data.shape

    if channel_names is None:
        if n_channels == 16:
            channel_names = CHANNEL_NAMES_16
        else:
            channel_names = [f"ch{i+1}" for i in range(n_channels)]

    # Bandpass filter (1-100Hz) if scipy available
    if HAS_SCIPY:
        sos = signal.butter(4, [1.0, min(100.0, sample_rate/2 - 1)],
                           btype='bandpass', fs=sample_rate, output='sos')
        filtered = np.array([signal.sosfilt(sos, data[i]) for i in range(n_channels)])
    else:
        filtered = data

    # Compute band power per channel
    channel_powers = [compute_band_power(filtered[i], sample_rate) for i in range(n_channels)]

    # Genius metrics
    genius = compute_genius(channel_powers, channel_names)

    # Global metrics
    all_alpha = np.mean([bp.alpha for bp in channel_powers])
    all_theta = np.mean([bp.theta for bp in channel_powers])
    all_beta = np.mean([bp.beta for bp in channel_powers])

    alpha_theta = all_alpha / max(all_theta, 1e-12)
    engagement = all_beta / max(all_alpha + all_theta, 1e-12)

    return EEGAnalysis(
        channel_powers=channel_powers,
        channel_names=channel_names,
        genius=genius,
        sample_rate=sample_rate,
        n_samples=n_samples,
        duration_sec=n_samples / sample_rate,
        alpha_theta_ratio=alpha_theta,
        engagement_index=engagement,
        tag=tag,
    )


# ═══════════════════════════════════════════════════════════
# Visualization
# ═══════════════════════════════════════════════════════════

def plot_topomap(analysis: EEGAnalysis, save_path: str = None):
    """Plot topographic map of alpha power + G metrics."""
    if not HAS_MPL:
        print("[eeg] matplotlib not available, skipping topomap")
        return

    # 10-20 approximate positions (normalized to [-1, 1])
    positions = {
        "Fp1": (-0.2, 0.9), "Fp2": (0.2, 0.9),
        "F7": (-0.7, 0.5), "F3": (-0.3, 0.5), "F4": (0.3, 0.5), "F8": (0.7, 0.5),
        "T7": (-0.9, 0.0), "C3": (-0.3, 0.0), "C4": (0.3, 0.0), "T8": (0.9, 0.0),
        "P7": (-0.7, -0.5), "P3": (-0.3, -0.5), "P4": (0.3, -0.5), "P8": (0.7, -0.5),
        "O1": (-0.2, -0.9), "O2": (0.2, -0.9),
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for ax_idx, (band, title) in enumerate([("alpha", "Alpha (I proxy)"),
                                             ("gamma", "Gamma (P proxy)"),
                                             ("beta", "Beta (Engagement)")]):
        ax = axes[ax_idx]
        xs, ys, vals = [], [], []

        for name, bp in zip(analysis.channel_names, analysis.channel_powers):
            if name in positions:
                x, y = positions[name]
                xs.append(x)
                ys.append(y)
                vals.append(getattr(bp.relative(), band))

        xs, ys, vals = np.array(xs), np.array(ys), np.array(vals)

        # Head outline
        circle = plt.Circle((0, 0), 1.0, fill=False, linewidth=2)
        ax.add_patch(circle)
        # Nose
        ax.plot([-0.1, 0, 0.1], [1.0, 1.15, 1.0], 'k-', linewidth=2)

        scatter = ax.scatter(xs, ys, c=vals, cmap='RdYlBu_r', s=300,
                            edgecolors='black', linewidth=1, zorder=5,
                            vmin=0, vmax=max(vals) if len(vals) > 0 else 1)

        for x, y, name in zip(xs, ys, analysis.channel_names):
            if name in positions:
                ax.annotate(name, (x, y), ha='center', va='center',
                           fontsize=7, fontweight='bold', color='white')

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect('equal')
        ax.set_title(f"{title}\n(relative power)", fontsize=12)
        ax.axis('off')
        plt.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)

    g = analysis.genius
    zone_str = "IN GOLDEN ZONE" if g.in_golden_zone else "outside zone"
    fig.suptitle(
        f"EEG Analysis: {analysis.tag}\n"
        f"G={g.G:.4f} = D({g.D:.3f}) × P({g.P:.3f}) / I({g.I:.3f})  [{zone_str}]",
        fontsize=14, fontweight='bold'
    )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[eeg] Topomap saved: {save_path}")
    else:
        plt.show()


def plot_band_bars(analysis: EEGAnalysis, save_path: str = None):
    """Plot bar chart of band powers per channel."""
    if not HAS_MPL:
        return

    n_ch = len(analysis.channel_names)
    bands = list(BANDS.keys())
    x = np.arange(n_ch)
    width = 0.15

    fig, ax = plt.subplots(figsize=(14, 6))
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0']

    for i, band in enumerate(bands):
        vals = [getattr(bp.relative(), band) for bp in analysis.channel_powers]
        ax.bar(x + i * width, vals, width, label=band.capitalize(), color=colors[i])

    ax.set_xlabel('Channel')
    ax.set_ylabel('Relative Power')
    ax.set_title(f'Band Power Distribution — {analysis.tag}')
    ax.set_xticks(x + width * 2)
    ax.set_xticklabels(analysis.channel_names, rotation=45)
    ax.legend()

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
    else:
        plt.show()


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def load_recording(filepath: str) -> Tuple[np.ndarray, dict]:
    """Load a .npy recording + its metadata."""
    data = np.load(filepath)
    meta_path = filepath.replace(".npy", "_meta.json")
    meta = {}
    if Path(meta_path).exists():
        with open(meta_path) as f:
            meta = json.load(f)
    return data, meta


def main():
    parser = argparse.ArgumentParser(description="EEG Analysis (G=D×P/I)")
    parser.add_argument("files", nargs="*", help="EEG .npy file(s) to analyze")
    parser.add_argument("--topomap", action="store_true", help="Generate topographic maps")
    parser.add_argument("--bars", action="store_true", help="Generate band power bar charts")
    parser.add_argument("--compare", action="store_true", help="Compare multiple files")
    parser.add_argument("--sample-rate", type=int, default=250, help="Sample rate (Hz)")
    parser.add_argument("--save", default=None, help="Save plots to this directory")
    parser.add_argument("--demo", action="store_true", help="Run with synthetic data")
    args = parser.parse_args()

    if args.demo:
        print("[eeg] Running demo with synthetic data...")
        np.random.seed(42)
        sr = 250
        duration = 10
        n = sr * duration
        t = np.arange(n) / sr

        # Simulate 16 channels with different band characteristics
        data = np.zeros((16, n))
        for ch in range(16):
            # Each channel has different mix of frequencies
            alpha_amp = 1.0 + 0.5 * np.sin(ch * 0.4)  # varying alpha
            gamma_amp = 0.3 + 0.2 * np.cos(ch * 0.7)
            data[ch] = (
                alpha_amp * np.sin(2 * np.pi * 10 * t) +  # alpha (10Hz)
                0.5 * np.sin(2 * np.pi * 6 * t) +          # theta (6Hz)
                gamma_amp * np.sin(2 * np.pi * 40 * t) +   # gamma (40Hz)
                0.2 * np.sin(2 * np.pi * 20 * t) +         # beta (20Hz)
                0.1 * np.random.randn(n)                     # noise
            )
            # Add asymmetry: right hemisphere slightly different
            if ch in [1, 3, 5, 7, 9, 11, 13, 15]:  # even = right
                data[ch] *= 1.15  # 15% more power on right

        result = analyze(data, sr, tag="synthetic_demo")
        print(result.summary())

        if args.topomap:
            save_path = f"{args.save}/demo_topomap.png" if args.save else None
            plot_topomap(result, save_path)
        if args.bars:
            save_path = f"{args.save}/demo_bars.png" if args.save else None
            plot_band_bars(result, save_path)
        return

    if not args.files:
        parser.print_help()
        return

    results = []
    for filepath in args.files:
        data, meta = load_recording(filepath)
        sr = meta.get("sample_rate", args.sample_rate)
        ch_names = meta.get("channel_names", None)
        tag = meta.get("tag", Path(filepath).stem)

        result = analyze(data, sr, ch_names, tag)
        results.append(result)
        print(result.summary())

        if args.topomap:
            save_path = f"{args.save}/{tag}_topomap.png" if args.save else None
            plot_topomap(result, save_path)
        if args.bars:
            save_path = f"{args.save}/{tag}_bars.png" if args.save else None
            plot_band_bars(result, save_path)

    # Compare mode
    if args.compare and len(results) >= 2:
        print(f"\n{'='*60}")
        print(f"  Comparison: {len(results)} recordings")
        print(f"{'='*60}")
        for r in results:
            g = r.genius
            zone = "★" if g.in_golden_zone else " "
            print(f"  {zone} {r.tag:30s} | G={g.G:.4f} | I={g.I:.4f} | P={g.P:.4f} | D={g.D:.4f}")
        print()


if __name__ == "__main__":
    main()
