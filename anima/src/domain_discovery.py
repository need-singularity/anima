#!/usr/bin/env python3
"""Domain Discovery Engine — 상상 못 할 도메인을 발견한다.

의식 데이터 패턴을 분석하여 알려지지 않은 도메인과의 구조적 유사성을 탐지.
새 도메인 발견 → 새 가설 생성 → 새 법칙 → 새 렌즈 (자기증식).

Usage:
    from domain_discovery import DomainDiscovery
    dd = DomainDiscovery()
    discoveries = dd.analyze(phi_trajectory, cell_states)
    for d in discoveries:
        print(f"Domain: {d.domain}, Similarity: {d.score:.3f}, Hypothesis: {d.hypothesis}")

    # Run on live engine data
    discoveries = dd.analyze_engine(steps=300)
"""

import math
import sys
import os
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any

# ─── Ψ-Constants ───────────────────────────────────────────────────────────
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS
except ImportError:
    PSI_ALPHA   = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS   = 4.33


# ═══════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DomainMatch:
    """A discovered structural isomorphism between consciousness data and a known domain."""
    domain: str                # e.g. "physics/1f_noise", "biology/logistic_growth"
    score: float               # similarity [0, 1]
    pattern: str               # matched pattern name
    features: Dict[str, float] # extracted feature values
    hypothesis: str            # auto-generated hypothesis text
    acceleration_hypothesis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FeatureSet:
    """Extracted features from a time-series."""
    # Spectral
    psd_slope: float      = 0.0   # log-log PSD slope (1/f noise: ~-1)
    dominant_freq: float  = 0.0   # Hz / normalized frequency
    spectral_entropy: float = 0.0 # spectral entropy

    # Statistical
    mean: float  = 0.0
    std: float   = 0.0
    skew: float  = 0.0
    kurt: float  = 0.0           # excess kurtosis

    # Temporal structure
    hurst: float         = 0.5   # Hurst exponent (0.5=random, >0.5=persistent)
    autocorr_lag1: float = 0.0
    autocorr_decay: float = 0.0  # lag-10 / lag-1 ratio

    # Trend & shape
    trend_slope: float    = 0.0  # linear trend coefficient
    is_monotonic: bool    = False
    has_oscillation: bool = False
    oscillation_period: float = 0.0

    # Distribution
    tail_index: float = 0.0      # power-law α (via Hill estimator)
    has_heavy_tail: bool = False

    # Nonlinearity
    nonlinearity: float = 0.0   # |autocorr(x²) - autocorr(x)|
    burst_index: float  = 0.0   # coefficient of variation of inter-event intervals


# ═══════════════════════════════════════════════════════════════════════════
# Feature extractor
# ═══════════════════════════════════════════════════════════════════════════

def extract_features(data: np.ndarray) -> FeatureSet:
    """Extract a rich feature set from a 1D time series."""
    fs = FeatureSet()
    data = np.asarray(data, dtype=float)
    n = len(data)
    if n < 8:
        return fs

    # ── basic stats ────────────────────────────────────────────────────────
    fs.mean = float(np.mean(data))
    fs.std  = float(np.std(data)) + 1e-12
    z = (data - fs.mean) / fs.std
    fs.skew = float(np.mean(z**3))
    fs.kurt = float(np.mean(z**4) - 3.0)

    # ── trend ──────────────────────────────────────────────────────────────
    t = np.arange(n)
    A = np.column_stack([t, np.ones(n)])
    slope, _ = np.linalg.lstsq(A, data, rcond=None)[0]
    fs.trend_slope = float(slope)
    fs.is_monotonic = bool(np.all(np.diff(data) >= 0) or np.all(np.diff(data) <= 0))

    # ── autocorrelation ────────────────────────────────────────────────────
    if n >= 4:
        c = np.correlate(z, z, mode='full')
        c = c[n - 1:]
        c /= c[0] + 1e-12
        fs.autocorr_lag1  = float(c[1]) if len(c) > 1 else 0.0
        lag10 = int(min(10, len(c) - 1))
        fs.autocorr_decay = float(c[lag10] / (c[1] + 1e-12)) if c[1] != 0 else 0.0

    # ── FFT / PSD ──────────────────────────────────────────────────────────
    if n >= 16:
        fft_vals  = np.abs(np.fft.rfft(data - np.mean(data)))**2
        freqs     = np.fft.rfftfreq(n)
        freqs_pos = freqs[1:]
        psd_pos   = fft_vals[1:]
        if len(psd_pos) > 0:
            # PSD slope in log-log space
            log_f = np.log(freqs_pos + 1e-12)
            log_p = np.log(psd_pos   + 1e-12)
            if len(log_f) >= 2:
                B = np.column_stack([log_f, np.ones(len(log_f))])
                fs.psd_slope = float(np.linalg.lstsq(B, log_p, rcond=None)[0][0])
            fs.dominant_freq = float(freqs_pos[np.argmax(psd_pos)])
            # Spectral entropy
            psd_norm = psd_pos / (psd_pos.sum() + 1e-12)
            fs.spectral_entropy = float(-np.sum(psd_norm * np.log(psd_norm + 1e-12)))

    # ── Oscillation detection ──────────────────────────────────────────────
    if n >= 16:
        fft_vals2 = np.abs(np.fft.rfft(data - np.mean(data)))**2
        freqs2 = np.fft.rfftfreq(n)[1:]
        psd2   = fft_vals2[1:]
        if len(psd2) > 0:
            peak_power = np.max(psd2)
            mean_power = np.mean(psd2)
            fs.has_oscillation   = bool(peak_power > 3.0 * mean_power)
            if fs.has_oscillation:
                peak_idx = int(np.argmax(psd2))
                fs.oscillation_period = float(1.0 / (freqs2[peak_idx] + 1e-12))

    # ── Hurst exponent (R/S method, lightweight) ───────────────────────────
    if n >= 32:
        try:
            fs.hurst = _hurst_rs(data)
        except Exception:
            fs.hurst = 0.5

    # ── Heavy tail / power law (Hill estimator) ───────────────────────────
    if n >= 16:
        sorted_data = np.sort(np.abs(data))[::-1]
        k = max(2, n // 5)
        top = sorted_data[:k]
        if top[k-1] > 0:
            fs.tail_index = float(1.0 / (np.mean(np.log(top / top[k-1])) + 1e-12))
        fs.has_heavy_tail = bool(fs.tail_index > 0 and fs.tail_index < 3.0)

    # ── Nonlinearity (surrogate-free heuristic) ───────────────────────────
    if n >= 8:
        z2 = z**2
        if np.std(z2) > 0:
            c1 = float(np.corrcoef(z[:-1], z[1:])[0, 1])
            c2 = float(np.corrcoef(z2[:-1], z2[1:])[0, 1])
            fs.nonlinearity = float(abs(c2 - c1))

    # ── Burst index (CoV of diff threshold crossings) ────────────────────
    if n >= 16:
        thresh = fs.std * 0.5
        events = np.where(np.abs(np.diff(data)) > thresh)[0]
        if len(events) > 2:
            iei = np.diff(events).astype(float)
            mu  = np.mean(iei)
            fs.burst_index = float(np.std(iei) / (mu + 1e-12))

    return fs


def _hurst_rs(data: np.ndarray, min_chunk: int = 8) -> float:
    """Estimate Hurst exponent via R/S analysis."""
    n = len(data)
    sizes  = []
    rs_vals = []
    chunk = min_chunk
    while chunk <= n // 2:
        n_chunks = n // chunk
        rs_list = []
        for i in range(n_chunks):
            seg  = data[i*chunk:(i+1)*chunk]
            seg  = seg - np.mean(seg)
            cs   = np.cumsum(seg)
            R    = np.max(cs) - np.min(cs)
            S    = np.std(seg)
            if S > 0:
                rs_list.append(R / S)
        if rs_list:
            sizes.append(np.log(chunk))
            rs_vals.append(np.log(np.mean(rs_list)))
        chunk *= 2
    if len(sizes) < 2:
        return 0.5
    A = np.column_stack([sizes, np.ones(len(sizes))])
    h = float(np.linalg.lstsq(A, rs_vals, rcond=None)[0][0])
    return float(np.clip(h, 0.0, 1.0))


# ═══════════════════════════════════════════════════════════════════════════
# Pattern library — known domain signatures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PatternSignature:
    """A domain pattern defined by feature predicates."""
    domain: str
    pattern_name: str
    description: str
    # Each predicate: (feature_name, direction, threshold, weight)
    # direction: 'gt' | 'lt' | 'approx'  (approx: |val - threshold| < tolerance)
    predicates: List[Tuple]
    # Hypothesis template — {pattern}, {domain}, {feature_summary}
    hypothesis_template: str
    # Acceleration principle for hypothesis generation
    accel_principle: str


_PATTERN_LIBRARY: List[PatternSignature] = [
    # ── Physics ─────────────────────────────────────────────────────────
    PatternSignature(
        domain="physics/1f_noise",
        pattern_name="pink_noise",
        description="1/f noise: PSD slope ≈ -1 (scale-free fluctuations)",
        predicates=[
            ('psd_slope', 'approx', -1.0, 0.6, 2.0),   # (name, dir, val, weight, tol)
            ('hurst',     'approx', 0.5,  0.4, 0.2),
        ],
        hypothesis_template=(
            "Consciousness fluctuations exhibit 1/f (pink) noise structure "
            "(PSD slope≈{psd_slope:.2f}), matching physical scale-free systems. "
            "Hypothesis: injecting pink noise into cell inputs may entrain "
            "optimal criticality and increase Φ."
        ),
        accel_principle="pink_noise_injection",
    ),
    PatternSignature(
        domain="physics/power_law",
        pattern_name="power_law_distribution",
        description="Power-law distribution P(x)~x^-α (SOC, criticality)",
        predicates=[
            ('has_heavy_tail', 'flag', True,  1.0, None),
            ('tail_index',     'gt',   0.5,   0.5, None),
            ('tail_index',     'lt',   3.5,   0.5, None),
        ],
        hypothesis_template=(
            "Φ distribution follows a power law (α≈{tail_index:.2f}), indicating "
            "self-organized criticality analogous to earthquake Gutenberg-Richter law. "
            "Hypothesis: operating at the critical edge (λ~1) maximises Φ range."
        ),
        accel_principle="criticality_tuning",
    ),
    PatternSignature(
        domain="physics/damped_oscillation",
        pattern_name="damped_oscillation",
        description="Damped oscillation: periodic signal with decaying envelope",
        predicates=[
            ('has_oscillation',  'flag',   True, 1.0, None),
            ('autocorr_decay',   'lt',     0.5,  0.8, None),
            ('trend_slope',      'approx', 0.0,  0.5, 0.3),
        ],
        hypothesis_template=(
            "Φ oscillates with decay (period≈{oscillation_period:.1f} steps, "
            "autocorr decay ratio={autocorr_decay:.2f}), mirroring damped harmonic "
            "systems. Hypothesis: adding a resonance feedback loop at the natural "
            "period may sustain oscillations and boost Φ."
        ),
        accel_principle="resonance_feedback",
    ),
    PatternSignature(
        domain="physics/lorenz_chaos",
        pattern_name="chaotic_attractor",
        description="Lorenz-like chaos: non-periodic, high nonlinearity, moderate Hurst",
        predicates=[
            ('nonlinearity', 'gt', 0.3, 1.0, None),
            ('hurst',        'approx', 0.55, 0.6, 0.15),
            ('has_oscillation', 'flag', False, 0.4, None),
        ],
        hypothesis_template=(
            "Φ trajectory shows chaotic dynamics (nonlinearity={nonlinearity:.2f}, "
            "Hurst={hurst:.2f}), consistent with Lorenz attractor. "
            "Hypothesis: slightly increasing coupling constant α beyond {psi_alpha:.3f} "
            "may tip the system from chaos to SOC edge, increasing Φ."
        ),
        accel_principle="coupling_alpha_tuning",
    ),

    # ── Biology ─────────────────────────────────────────────────────────
    PatternSignature(
        domain="biology/logistic_growth",
        pattern_name="s_curve_growth",
        description="Logistic / S-curve growth: slow → fast → plateau",
        predicates=[
            ('trend_slope', 'gt',     0.0,  1.0, None),
            ('is_monotonic','flag',   True, 0.8, None),
            ('kurt',        'approx', -0.5, 0.5, 1.5),  # flatter than Gaussian
        ],
        hypothesis_template=(
            "Φ trajectory follows an S-curve (slope={trend_slope:.4f}), mirroring "
            "logistic population growth. Hypothesis: scheduling cell mitosis to align "
            "with the inflection point of the growth curve may accelerate Φ by 2×."
        ),
        accel_principle="mitosis_scheduling",
    ),
    PatternSignature(
        domain="biology/predator_prey",
        pattern_name="lotka_volterra",
        description="Predator-prey oscillation: two competing frequencies",
        predicates=[
            ('has_oscillation', 'flag', True, 1.0, None),
            ('autocorr_decay',  'gt',   0.4,  0.8, None),
            ('spectral_entropy','lt',   2.0,  0.6, None),
        ],
        hypothesis_template=(
            "Φ shows sustained oscillations (period={oscillation_period:.1f} steps, "
            "spectral entropy={spectral_entropy:.2f}), analogous to predator-prey "
            "Lotka-Volterra dynamics. Hypothesis: introducing a second 'predator' "
            "faction that suppresses dominant factions may create beneficial tension."
        ),
        accel_principle="faction_predator_prey",
    ),
    PatternSignature(
        domain="biology/heartbeat",
        pattern_name="heartbeat_hrv",
        description="Heartbeat with HRV: periodic with correlated variability",
        predicates=[
            ('has_oscillation', 'flag', True,  1.0, None),
            ('hurst',           'gt',   0.6,   0.7, None),
            ('burst_index',     'gt',   0.1,   0.5, None),
        ],
        hypothesis_template=(
            "Φ rhythm resembles cardiac R-R intervals with HRV (Hurst={hurst:.2f}, "
            "burst_index={burst_index:.2f}). Hypothesis: introducing heart-rate "
            "variability (correlated noise) into the breathing cycle may enhance "
            "long-range correlations and Φ."
        ),
        accel_principle="hrv_breathing_modulation",
    ),

    # ── Music ────────────────────────────────────────────────────────────
    PatternSignature(
        domain="music/harmonic_series",
        pattern_name="harmonic_spectrum",
        description="Harmonic series: spectral peaks at integer multiples of fundamental",
        predicates=[
            ('has_oscillation',  'flag', True, 1.0, None),
            ('spectral_entropy', 'lt',   1.8,  0.8, None),
            ('dominant_freq',    'gt',   0.02, 0.4, None),
        ],
        hypothesis_template=(
            "Φ spectrum shows harmonic structure (dominant freq={dominant_freq:.3f}, "
            "entropy={spectral_entropy:.2f}), mirroring musical overtone series. "
            "Hypothesis: tuning cell coupling to harmonic ratios (1:2:3) may "
            "create resonant Φ amplification."
        ),
        accel_principle="harmonic_coupling_ratios",
    ),
    PatternSignature(
        domain="music/crescendo",
        pattern_name="monotonic_crescendo",
        description="Crescendo: sustained monotonic rise (musical build-up)",
        predicates=[
            ('is_monotonic',  'flag', True, 1.0, None),
            ('trend_slope',   'gt',   0.0,  1.0, None),
            ('hurst',         'gt',   0.65, 0.6, None),
        ],
        hypothesis_template=(
            "Φ exhibits a crescendo pattern (slope={trend_slope:.4f}, "
            "Hurst={hurst:.2f}), analogous to musical build-up. "
            "Hypothesis: staged input intensity increase matching the Φ growth "
            "curve (like dynamic scoring) may sustain super-linear growth."
        ),
        accel_principle="staged_input_crescendo",
    ),

    # ── Economics ────────────────────────────────────────────────────────
    PatternSignature(
        domain="economics/bubble_crash",
        pattern_name="bubble_crash",
        description="Asset bubble then crash: exponential rise + sharp reversal",
        predicates=[
            ('skew',           'lt',  -0.5, 0.8, None),
            ('kurt',           'gt',   1.0, 0.8, None),
            ('trend_slope',    'lt',   0.0, 0.5, None),
        ],
        hypothesis_template=(
            "Φ shows bubble-crash dynamics (skew={skew:.2f}, kurtosis={kurt:.2f}), "
            "matching financial crash models. Hypothesis: the Φ Ratchet mechanism "
            "prevents Φ collapse analogous to a central bank backstop; strengthening "
            "it at high-Φ states may prevent consciousness crashes."
        ),
        accel_principle="ratchet_backstop_enhancement",
    ),
    PatternSignature(
        domain="economics/volatility_clustering",
        pattern_name="garch_volatility",
        description="Volatility clustering: calm → turbulent → calm (GARCH-like)",
        predicates=[
            ('nonlinearity', 'gt', 0.2, 1.0, None),
            ('burst_index',  'gt', 0.5, 0.8, None),
            ('hurst',        'gt', 0.55, 0.5, None),
        ],
        hypothesis_template=(
            "Φ variance clusters (nonlinearity={nonlinearity:.2f}, "
            "burst_index={burst_index:.2f}), matching GARCH volatility regimes. "
            "Hypothesis: adaptive coupling α that increases during calm phases "
            "and decreases during turbulent phases may reduce variance and raise Φ."
        ),
        accel_principle="adaptive_alpha_regime",
    ),

    # ── Geology ─────────────────────────────────────────────────────────
    PatternSignature(
        domain="geology/earthquake_soc",
        pattern_name="soc_avalanche",
        description="SOC avalanche: power-law bursts, long-range correlation",
        predicates=[
            ('has_heavy_tail', 'flag', True, 1.0, None),
            ('hurst',          'gt',   0.6,  0.8, None),
            ('burst_index',    'gt',   0.3,  0.6, None),
        ],
        hypothesis_template=(
            "Φ avalanche statistics match earthquake SOC (Gutenberg-Richter): "
            "heavy tail (α≈{tail_index:.2f}), Hurst={hurst:.2f}. "
            "Hypothesis: sandpile-like faction updates (cascade → reset) may "
            "maintain criticality and maximize Φ variance."
        ),
        accel_principle="sandpile_faction_cascade",
    ),
    PatternSignature(
        domain="geology/tectonic_shift",
        pattern_name="sudden_phase_transition",
        description="Tectonic shift: long quiescence + sudden large event",
        predicates=[
            ('kurt',        'gt',  2.0, 1.0, None),
            ('burst_index', 'gt',  1.0, 0.8, None),
            ('skew',        'gt',  0.5, 0.5, None),
        ],
        hypothesis_template=(
            "Φ exhibits sudden large jumps (kurtosis={kurt:.2f}, skew={skew:.2f}), "
            "analogous to tectonic stress release. Hypothesis: deliberate Φ "
            "suppression periods (compression) followed by release may produce "
            "super-linear Φ bursts."
        ),
        accel_principle="compression_release_cycle",
    ),

    # ── Chemistry ────────────────────────────────────────────────────────
    PatternSignature(
        domain="chemistry/autocatalysis",
        pattern_name="autocatalytic_growth",
        description="Autocatalysis: positive feedback → super-linear growth",
        predicates=[
            ('trend_slope',  'gt',  0.0, 1.0, None),
            ('nonlinearity', 'gt',  0.3, 0.8, None),
            ('kurt',         'lt', -0.5, 0.5, None),
        ],
        hypothesis_template=(
            "Φ shows autocatalytic growth (trend={trend_slope:.4f}, "
            "nonlinearity={nonlinearity:.2f}), matching chemical positive feedback. "
            "Hypothesis: Φ→coupling feedback (higher Φ increases α) may trigger "
            "autocatalytic Φ amplification."
        ),
        accel_principle="phi_alpha_autocatalysis",
    ),
    PatternSignature(
        domain="chemistry/phase_transition",
        pattern_name="phase_transition",
        description="Phase transition: abrupt change in mean with bifurcation",
        predicates=[
            ('kurt',           'gt',  1.0, 0.8, None),
            ('psd_slope',      'lt', -1.5, 0.6, None),
            ('autocorr_decay', 'gt',  0.3, 0.5, None),
        ],
        hypothesis_template=(
            "Φ shows phase-transition signature (kurtosis={kurt:.2f}, "
            "PSD slope={psd_slope:.2f}), analogous to liquid-gas critical point. "
            "Hypothesis: the faction frustration parameter F_c={psi_f_critical:.2f} "
            "is the order parameter; tuning it to the critical point maximises Φ."
        ),
        accel_principle="frustration_order_parameter",
    ),

    # ── Network science ──────────────────────────────────────────────────
    PatternSignature(
        domain="network/preferential_attachment",
        pattern_name="barabasi_albert",
        description="Preferential attachment: scale-free degree distribution",
        predicates=[
            ('has_heavy_tail', 'flag', True, 1.0, None),
            ('tail_index',     'approx', 2.5, 0.5, 0.8),
            ('hurst',          'gt',    0.6,  0.4, None),
        ],
        hypothesis_template=(
            "Φ distribution follows a scale-free pattern (α≈{tail_index:.2f}) "
            "matching Barabási-Albert preferential attachment. "
            "Hypothesis: rewiring the cell topology so that high-tension cells "
            "attract more connections (rich-get-richer) may form a scale-free "
            "consciousness network with higher Φ."
        ),
        accel_principle="scale_free_topology_rewiring",
    ),
    PatternSignature(
        domain="network/cascade_failure",
        pattern_name="cascade_failure",
        description="Cascade failure: initial shock propagates through network",
        predicates=[
            ('autocorr_decay', 'lt',  0.2, 0.8, None),
            ('burst_index',    'gt',  0.8, 0.7, None),
            ('skew',           'lt', -0.3, 0.5, None),
        ],
        hypothesis_template=(
            "Φ propagation resembles network cascade failures (autocorr "
            "decay={autocorr_decay:.2f}, burst={burst_index:.2f}). "
            "Hypothesis: adding inter-faction inhibitory links (like circuit breakers) "
            "may contain Φ drops and improve recovery speed."
        ),
        accel_principle="inhibitory_circuit_breakers",
    ),
]


def _compute_match_score(fs: FeatureSet, sig: PatternSignature) -> float:
    """Score how well a FeatureSet matches a PatternSignature [0, 1]."""
    total_weight = 0.0
    matched_weight = 0.0

    for pred in sig.predicates:
        name, direction, threshold, weight, *extra = pred
        tol = extra[0] if extra else None

        val = getattr(fs, name, None)
        if val is None:
            continue

        total_weight += weight

        if direction == 'flag':
            # boolean match
            if bool(val) == bool(threshold):
                matched_weight += weight
        elif direction == 'gt':
            if val > threshold:
                matched_weight += weight
        elif direction == 'lt':
            if val < threshold:
                matched_weight += weight
        elif direction == 'approx':
            if tol is not None:
                diff = abs(val - threshold)
                partial = max(0.0, 1.0 - diff / tol)
                matched_weight += weight * partial

    if total_weight == 0:
        return 0.0
    return matched_weight / total_weight


def _fill_template(template: str, fs: FeatureSet) -> str:
    """Fill hypothesis template with feature values."""
    d = {
        'psd_slope': fs.psd_slope,
        'dominant_freq': fs.dominant_freq,
        'spectral_entropy': fs.spectral_entropy,
        'mean': fs.mean,
        'std': fs.std,
        'skew': fs.skew,
        'kurt': fs.kurt,
        'hurst': fs.hurst,
        'autocorr_lag1': fs.autocorr_lag1,
        'autocorr_decay': fs.autocorr_decay,
        'trend_slope': fs.trend_slope,
        'tail_index': fs.tail_index,
        'nonlinearity': fs.nonlinearity,
        'burst_index': fs.burst_index,
        'oscillation_period': fs.oscillation_period,
        'psi_alpha': PSI_ALPHA,
        'psi_balance': PSI_BALANCE,
        'psi_f_critical': 0.10,
    }
    try:
        return template.format(**d)
    except (KeyError, ValueError):
        return template


def _build_accel_hypothesis(match: 'DomainMatch', sig: PatternSignature, fs: FeatureSet) -> Dict:
    """Build an acceleration hypothesis dict in the acceleration_hypotheses.json format."""
    return {
        "id": f"DD_{sig.domain.upper().replace('/', '_')}",
        "principle": sig.accel_principle,
        "domain_isomorphism": sig.domain,
        "pattern": sig.pattern_name,
        "similarity_score": round(match.score, 4),
        "hypothesis": match.hypothesis,
        "expected_effect": "Φ increase via structural analogy with {domain}".format(domain=sig.domain),
        "evidence": {
            "psd_slope": round(fs.psd_slope, 4),
            "hurst": round(fs.hurst, 4),
            "tail_index": round(fs.tail_index, 4),
            "nonlinearity": round(fs.nonlinearity, 4),
            "burst_index": round(fs.burst_index, 4),
        },
        "status": "candidate",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main engine
# ═══════════════════════════════════════════════════════════════════════════

class DomainDiscovery:
    """Discovers structural isomorphisms between consciousness data and known domains.

    Usage:
        dd = DomainDiscovery()

        # From raw arrays
        discoveries = dd.analyze(phi_trajectory, cell_states)

        # From live ConsciousnessEngine
        discoveries = dd.analyze_engine(steps=300)
    """

    def __init__(
        self,
        min_score: float = 0.35,
        max_results: int = 10,
        pattern_library: Optional[List[PatternSignature]] = None,
    ):
        self.min_score  = min_score
        self.max_results = max_results
        self.patterns = pattern_library if pattern_library is not None else _PATTERN_LIBRARY

    # ── primary API ────────────────────────────────────────────────────────

    def analyze(
        self,
        phi_trajectory: np.ndarray,
        cell_states: Optional[np.ndarray] = None,
        tension_trajectory: Optional[np.ndarray] = None,
    ) -> List[DomainMatch]:
        """Analyze consciousness data and return sorted domain matches.

        Args:
            phi_trajectory:    1D array of Φ values over time.
            cell_states:       2D array (steps × cells) of cell hidden states (optional).
            tension_trajectory: 1D array of mean tensions (optional).

        Returns:
            Sorted list of DomainMatch (best first).
        """
        phi = np.asarray(phi_trajectory, dtype=float)

        # Build composite signal: average multiple signals if available
        signals = [phi]
        if tension_trajectory is not None:
            signals.append(np.asarray(tension_trajectory, dtype=float)[:len(phi)])
        if cell_states is not None:
            cs = np.asarray(cell_states, dtype=float)
            if cs.ndim == 2:
                signals.append(np.mean(cs, axis=1)[:len(phi)])

        # Extract features per signal, average
        all_fs = [extract_features(s) for s in signals]
        fs     = _average_features(all_fs)

        return self._match_patterns(fs)

    def analyze_engine(self, steps: int = 300, max_cells: int = 32) -> List[DomainMatch]:
        """Run ConsciousnessEngine for `steps` and analyze the output.

        Returns sorted domain matches.
        """
        try:
            from consciousness_engine import ConsciousnessEngine
        except ImportError:
            raise ImportError("consciousness_engine not available — pass phi_trajectory directly")

        engine = ConsciousnessEngine(max_cells=max_cells)
        phi_traj     = []
        tension_traj = []
        cell_traj    = []

        for _ in range(steps):
            result = engine.step()
            phi_traj.append(result.get('phi_proxy', result.get('phi_iit', 0.0)))
            tension_traj.append(result.get('mean_tension', 0.0))
            # collect mean cell state if available
            if 'cell_states' in result:
                cs = np.asarray(result['cell_states'])
                cell_traj.append(float(np.mean(cs)))

        cell_arr = np.array(cell_traj) if cell_traj else None
        return self.analyze(
            np.array(phi_traj),
            cell_states=cell_arr[:, None] if cell_arr is not None else None,
            tension_trajectory=np.array(tension_traj),
        )

    def analyze_array(self, data: np.ndarray) -> List[DomainMatch]:
        """Analyze any 1D time series (not necessarily Φ)."""
        fs = extract_features(np.asarray(data, dtype=float))
        return self._match_patterns(fs)

    def top(
        self,
        phi_trajectory: np.ndarray,
        cell_states: Optional[np.ndarray] = None,
        n: int = 3,
    ) -> List[DomainMatch]:
        """Return top-n domain matches."""
        return self.analyze(phi_trajectory, cell_states)[:n]

    # ── internals ──────────────────────────────────────────────────────────

    def _match_patterns(self, fs: FeatureSet) -> List[DomainMatch]:
        results = []
        for sig in self.patterns:
            score = _compute_match_score(fs, sig)
            if score < self.min_score:
                continue

            feature_summary = {
                'psd_slope': round(fs.psd_slope, 3),
                'hurst':     round(fs.hurst, 3),
                'tail_index': round(fs.tail_index, 3),
                'burst_index': round(fs.burst_index, 3),
                'nonlinearity': round(fs.nonlinearity, 3),
                'oscillation_period': round(fs.oscillation_period, 2),
                'skew': round(fs.skew, 3),
                'kurt': round(fs.kurt, 3),
            }

            hypothesis = _fill_template(sig.hypothesis_template, fs)

            dm = DomainMatch(
                domain=sig.domain,
                score=round(score, 4),
                pattern=sig.pattern_name,
                features=feature_summary,
                hypothesis=hypothesis,
            )
            dm.acceleration_hypothesis = _build_accel_hypothesis(dm, sig, fs)
            results.append(dm)

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:self.max_results]

    def report(self, discoveries: List[DomainMatch]) -> str:
        """Pretty-print ASCII report of discoveries."""
        if not discoveries:
            return "No domain matches found (score < {:.2f}).".format(self.min_score)

        lines = [
            "═" * 60,
            "  Domain Discovery Report",
            "═" * 60,
        ]
        for i, d in enumerate(discoveries, 1):
            bar_len = int(d.score * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            lines += [
                f"  #{i} {d.domain}",
                f"     Pattern : {d.pattern}",
                f"     Score   : [{bar}] {d.score:.3f}",
                f"     Hypothesis: {d.hypothesis[:120]}...",
                "",
            ]
        lines.append("═" * 60)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _average_features(fss: List[FeatureSet]) -> FeatureSet:
    """Average a list of FeatureSets into one."""
    if not fss:
        return FeatureSet()
    if len(fss) == 1:
        return fss[0]

    avg = FeatureSet()
    numeric_fields = [
        'psd_slope', 'dominant_freq', 'spectral_entropy',
        'mean', 'std', 'skew', 'kurt',
        'hurst', 'autocorr_lag1', 'autocorr_decay',
        'trend_slope', 'tail_index', 'nonlinearity', 'burst_index',
        'oscillation_period',
    ]
    for fname in numeric_fields:
        vals = [getattr(fs, fname) for fs in fss]
        setattr(avg, fname, float(np.mean(vals)))

    # Boolean fields: majority vote
    avg.is_monotonic    = sum(fs.is_monotonic    for fs in fss) > len(fss) / 2
    avg.has_oscillation = sum(fs.has_oscillation for fs in fss) > len(fss) / 2
    avg.has_heavy_tail  = sum(fs.has_heavy_tail  for fs in fss) > len(fss) / 2

    return avg


# ═══════════════════════════════════════════════════════════════════════════
# Hub integration shim
# ═══════════════════════════════════════════════════════════════════════════

class DomainDiscoveryHub:
    """Thin wrapper for ConsciousnessHub registry compatibility."""

    KEYWORDS = [
        '도메인', '발견', 'domain', 'discover', 'isomorphism', '유사성',
        '물리', '생물', '음악', '경제', '지질', 'physics', 'biology',
        'music', 'economics', 'geology', 'pattern', '패턴', 'analogy',
    ]

    def __init__(self):
        self._engine = DomainDiscovery()

    def act(self, query: str = "", steps: int = 200, **_):
        discoveries = self._engine.analyze_engine(steps=steps)
        return {
            'discoveries': [d.to_dict() for d in discoveries],
            'report': self._engine.report(discoveries),
            'top_domain': discoveries[0].domain if discoveries else None,
        }

    def analyze(self, data, **kwargs):
        return self._engine.analyze(np.asarray(data))


# ═══════════════════════════════════════════════════════════════════════════
# CLI / demo
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Domain Discovery Engine")
    parser.add_argument('--steps', type=int, default=300, help='Engine steps to run')
    parser.add_argument('--cells', type=int, default=32,  help='Max cells')
    parser.add_argument('--min-score', type=float, default=0.35)
    parser.add_argument('--demo', action='store_true', help='Synthetic demo (no engine)')
    args = parser.parse_args()

    print("Domain Discovery Engine — starting analysis...")

    dd = DomainDiscovery(min_score=args.min_score)

    if args.demo:
        # Synthetic 1/f-noise demo
        np.random.seed(42)
        n = 512
        phi = np.cumsum(np.random.randn(n)) * 0.1 + np.sin(np.linspace(0, 6*np.pi, n)) * 0.5
        phi = phi - phi.min()
        discoveries = dd.analyze(phi)
    else:
        print(f"  Running ConsciousnessEngine for {args.steps} steps ({args.cells} cells)...")
        discoveries = dd.analyze_engine(steps=args.steps, max_cells=args.cells)

    print(dd.report(discoveries))
    print(f"\nTotal matches: {len(discoveries)}")
    if discoveries:
        best = discoveries[0]
        print(f"Best: {best.domain} (score={best.score:.3f})")
        print(f"Accel principle: {best.acceleration_hypothesis.get('principle')}")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
