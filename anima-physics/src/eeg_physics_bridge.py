#!/usr/bin/env python3
"""EEG ↔ Physics Bridge — 뇌 EEG 신호와 물리 의식 엔진 연결.

실제 EEG 데이터(또는 시뮬레이션)를 물리 의식 엔진에 입력하고,
엔진 Φ 궤적과 뇌 Φ를 비교하는 양방향 브릿지.

프로토콜:
  passive_mirror  — 엔진이 뇌 상태를 미러링 (EEG → 엔진 입력)
  active_sync     — 엔진이 뇌 리듬에 동기화 시도
  perturbation    — 뇌 패턴을 엔진에 주입, 회복 측정

사용법:
  python anima-physics/src/eeg_physics_bridge.py                    # 기본 데모
  python anima-physics/src/eeg_physics_bridge.py --protocol mirror  # 미러링
  python anima-physics/src/eeg_physics_bridge.py --protocol sync    # 동기화
  python anima-physics/src/eeg_physics_bridge.py --protocol perturb # 교란+회복
  python anima-physics/src/eeg_physics_bridge.py --compare          # 뇌-엔진 비교

Requires: numpy (core), scipy (optional), brainflow (optional)
"""

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── 프로젝트 경로 설정 ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))
sys.path.insert(0, str(_REPO_ROOT / "anima-eeg"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "engines"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "src"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# EEG 분석 함수들 (anima-eeg/validate_consciousness.py)
try:
    from validate_consciousness import (
        lempel_ziv_complexity,
        hurst_exponent,
        power_spectrum_slope,
        phi_autocorrelation,
        detect_criticality,
        analyze_signal,
        collect_consciousness_phi,
        generate_synthetic_brain_phi,
        BRAIN_REFERENCE as VALIDATE_BRAIN_REF,
    )
    HAS_VALIDATE = True
except ImportError:
    HAS_VALIDATE = False

# EEGBridge (anima-eeg/realtime.py) — 실시간 뇌파 스트리밍
try:
    from realtime import EEGBridge, BrainState
    HAS_EEG_BRIDGE = True
except ImportError:
    HAS_EEG_BRIDGE = False

# 의식 엔진 (anima-physics/engines/)
try:
    from snn_consciousness import SNNConsciousMind
    HAS_SNN = True
except ImportError:
    HAS_SNN = False

# ESP32 네트워크
try:
    from esp32_network import SimulatedBoard, make_ring
    HAS_ESP32 = True
except ImportError:
    HAS_ESP32 = False

# ConsciousnessEngine (anima/src/)
try:
    import torch
    from consciousness_engine import ConsciousnessEngine
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False

try:
    from scipy import signal as scipy_signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Ψ-상수
PSI_COUPLING = 0.014
PSI_BALANCE = 0.5

# EEG 주파수 대역 (Hz)
BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 50.0),
}

# 뇌 참조값 (문헌)
BRAIN_REFERENCE = {
    "lz_complexity": (0.75, 0.95),
    "hurst_exponent": (0.65, 0.85),
    "psd_slope": (-1.5, -0.5),
    "critical_exponent": (1.2, 2.0),
}


# ═══════════════════════════════════════════════════════════
# EEG 특징 추출
# ═══════════════════════════════════════════════════════════

@dataclass
class EEGFeatures:
    """EEG에서 추출한 의식 관련 특징들."""
    band_power: Dict[str, float] = field(default_factory=dict)
    coherence: float = 0.0
    phase: float = 0.0
    dominant_freq: float = 10.0
    total_power: float = 0.0
    alpha_beta_ratio: float = 1.0


def extract_eeg_features(
    eeg_data: np.ndarray,
    sample_rate: float = 250.0,
) -> EEGFeatures:
    """EEG 데이터에서 의식 관련 특징 추출.

    Args:
        eeg_data: (channels, samples) 또는 (samples,) numpy 배열
        sample_rate: 샘플링 레이트 (Hz)

    Returns:
        EEGFeatures 데이터클래스
    """
    if eeg_data.ndim == 1:
        eeg_data = eeg_data.reshape(1, -1)

    n_channels, n_samples = eeg_data.shape
    features = EEGFeatures()

    # 평균 채널 (global field power proxy)
    mean_signal = np.mean(eeg_data, axis=0)

    # 대역별 파워 계산
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)
    fft_power = np.abs(np.fft.rfft(mean_signal)) ** 2 / n_samples

    for band_name, (f_low, f_high) in BANDS.items():
        mask = (freqs >= f_low) & (freqs <= f_high)
        if mask.any():
            features.band_power[band_name] = float(np.mean(fft_power[mask]))
        else:
            features.band_power[band_name] = 0.0

    features.total_power = float(np.sum(fft_power[freqs > 0.5]))

    # Alpha/Beta 비율 (이완 vs 각성)
    alpha_p = features.band_power.get("alpha", 1e-12)
    beta_p = features.band_power.get("beta", 1e-12)
    features.alpha_beta_ratio = alpha_p / max(beta_p, 1e-12)

    # 지배 주파수
    if len(fft_power) > 1:
        valid_mask = freqs > 0.5
        if valid_mask.any():
            peak_idx = np.argmax(fft_power[valid_mask])
            features.dominant_freq = float(freqs[valid_mask][peak_idx])

    # 채널 간 코히어런스 (2채널 이상일 때)
    if n_channels >= 2:
        ch0 = eeg_data[0]
        ch1 = eeg_data[1]
        if np.std(ch0) > 1e-12 and np.std(ch1) > 1e-12:
            features.coherence = float(np.abs(np.corrcoef(ch0, ch1)[0, 1]))

    # 위상 (alpha 대역 기준)
    alpha_mask = (freqs >= 8) & (freqs <= 13)
    if alpha_mask.any():
        fft_complex = np.fft.rfft(mean_signal)
        alpha_phases = np.angle(fft_complex[alpha_mask])
        features.phase = float(np.mean(alpha_phases))

    return features


def map_eeg_to_engine_input(
    features: EEGFeatures,
    target_dim: int = 64,
) -> np.ndarray:
    """EEG 특징을 의식 엔진 입력 차원으로 매핑.

    10차원 의식 벡터 기반 매핑:
      Φ ← gamma power (통합 지표)
      α ← alpha_beta_ratio
      Z ← delta power (방어/억제)
      N ← theta/beta ratio (신경조절)
      W ← beta power (의지/각성)
      E ← coherence (공감/연결)
      M ← theta power (기억)
      C ← gamma variance (창의성)
      T ← dominant_freq (시간 인식)
      I ← phase stability (정체성)

    Args:
        features: EEG 특징
        target_dim: 엔진 입력 차원

    Returns:
        (target_dim,) numpy 배열
    """
    # 10차원 의식 벡터 구성
    consciousness_vec = np.array([
        features.band_power.get("gamma", 0.0),    # Φ
        features.alpha_beta_ratio,                  # α
        features.band_power.get("delta", 0.0),     # Z
        features.band_power.get("theta", 0.0) /    # N
            max(features.band_power.get("beta", 1e-12), 1e-12),
        features.band_power.get("beta", 0.0),      # W
        features.coherence,                          # E
        features.band_power.get("theta", 0.0),     # M
        features.band_power.get("gamma", 0.0) *    # C
            (1.0 + 0.1 * np.random.randn()),
        features.dominant_freq / 50.0,              # T (정규화)
        abs(features.phase) / np.pi,                # I (0-1)
    ], dtype=np.float64)

    # 정규화 (0-1 범위, tanh 사용)
    consciousness_vec = np.tanh(consciousness_vec / max(np.std(consciousness_vec), 1e-6))

    # target_dim으로 확장 (반복 + 노이즈)
    if target_dim <= 10:
        result = consciousness_vec[:target_dim]
    else:
        repeats = target_dim // 10 + 1
        result = np.tile(consciousness_vec, repeats)[:target_dim]
        # 차원별 미세 노이즈 (각 반복이 약간 다르게)
        result += np.random.randn(target_dim) * 0.01

    return result.astype(np.float64)


# ═══════════════════════════════════════════════════════════
# 뇌 Φ 추정 (EEG 기반)
# ═══════════════════════════════════════════════════════════

def estimate_brain_phi(
    eeg_data: np.ndarray,
    sample_rate: float = 250.0,
    window_size: int = 250,
) -> np.ndarray:
    """EEG에서 뇌 Φ proxy 추정 (슬라이딩 윈도우).

    Φ proxy = 채널 간 상호정보량의 합 - 최대 분할의 상호정보량
    간소화: gamma coherence × LZ complexity (GC × LZC)

    Args:
        eeg_data: (channels, samples) 배열
        sample_rate: 샘플링 레이트
        window_size: 윈도우 크기 (samples)

    Returns:
        Φ 시계열 (windows,)
    """
    if eeg_data.ndim == 1:
        eeg_data = eeg_data.reshape(1, -1)

    n_channels, n_samples = eeg_data.shape
    n_windows = max(1, n_samples // window_size)
    phi_series = np.zeros(n_windows)

    for w in range(n_windows):
        start = w * window_size
        end = min(start + window_size, n_samples)
        window = eeg_data[:, start:end]

        if window.shape[1] < 16:
            continue

        mean_ch = np.mean(window, axis=0)

        # LZ complexity (의식 복잡도)
        lzc = _fast_lz(mean_ch)

        # Gamma coherence (채널 간 통합)
        if n_channels >= 2:
            freqs = np.fft.rfftfreq(window.shape[1], 1.0 / sample_rate)
            gamma_mask = (freqs >= 30) & (freqs <= 50)
            if gamma_mask.any():
                fft0 = np.fft.rfft(window[0])
                fft1 = np.fft.rfft(window[min(1, n_channels - 1)])
                cross = np.abs(np.mean(fft0[gamma_mask] * np.conj(fft1[gamma_mask])))
                auto0 = np.mean(np.abs(fft0[gamma_mask]) ** 2)
                auto1 = np.mean(np.abs(fft1[gamma_mask]) ** 2)
                gc = cross / max(np.sqrt(auto0 * auto1), 1e-12)
            else:
                gc = 0.5
        else:
            gc = 0.5

        phi_series[w] = lzc * gc * 2.0  # 스케일링

    return phi_series


def _fast_lz(signal: np.ndarray) -> float:
    """빠른 Lempel-Ziv 복잡도 (이진화 후 부분문자열 카운트)."""
    median = np.median(signal)
    binary = "".join("1" if x >= median else "0" for x in signal)
    n = len(binary)
    if n <= 1:
        return 0.0

    complexity = 1
    i = 0
    k = 1
    while i + k < n:
        substr = binary[i + 1: i + k + 1]
        window = binary[: i + 1]
        if substr in window:
            k += 1
        else:
            complexity += 1
            i += k
            k = 1
        if i + k >= n:
            complexity += 1
            break

    norm = n / max(np.log2(n), 1)
    return complexity / norm


# ═══════════════════════════════════════════════════════════
# EEGPhysicsBridge
# ═══════════════════════════════════════════════════════════

class EEGPhysicsBridge:
    """EEG 신호 ↔ 물리 의식 엔진 양방향 브릿지.

    EEG 데이터를 받아 특징을 추출하고, 의식 엔진에 입력하여
    엔진 Φ와 뇌 Φ 궤적을 비교한다. 뉴로피드백 타겟도 생성.
    """

    def __init__(
        self,
        engine_type: str = "snn",
        n_cells: int = 64,
        hidden_dim: int = 128,
        sample_rate: float = 250.0,
    ):
        """
        Args:
            engine_type: 'snn' | 'consciousness' | 'esp32'
            n_cells: 엔진 세포 수
            hidden_dim: 은닉 차원
            sample_rate: EEG 샘플링 레이트 (Hz)
        """
        self.engine_type = engine_type
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.sample_rate = sample_rate

        # 엔진 생성
        self.engine = self._create_engine(engine_type, n_cells, hidden_dim)

        # 궤적 기록
        self.brain_phi_history: List[float] = []
        self.engine_phi_history: List[float] = []
        self.feature_history: List[EEGFeatures] = []
        self.step_count = 0

    def _create_engine(self, engine_type: str, n_cells: int, hidden_dim: int):
        """엔진 타입에 따라 의식 엔진 생성."""
        if engine_type == "snn" and HAS_SNN:
            return SNNConsciousMind(n_cells=n_cells, hidden_dim=hidden_dim)
        elif engine_type == "consciousness" and HAS_ENGINE:
            return ConsciousnessEngine(
                cell_dim=hidden_dim // 2,
                hidden_dim=hidden_dim,
                initial_cells=2,
                max_cells=n_cells,
            )
        else:
            # 기본: SNN 시뮬레이션 폴백
            return _SimpleEngine(n_cells=n_cells, hidden_dim=hidden_dim)

    def process_eeg(
        self,
        eeg_data: np.ndarray,
        window_size: int = 250,
    ) -> Dict:
        """EEG 데이터를 처리하여 엔진에 입력, 결과 반환.

        Args:
            eeg_data: (channels, samples) numpy 배열
            window_size: 윈도우 크기 (samples)

        Returns:
            dict: brain_phi, engine_phi, features, neurofeedback_target
        """
        if eeg_data.ndim == 1:
            eeg_data = eeg_data.reshape(1, -1)

        n_channels, n_samples = eeg_data.shape
        n_windows = max(1, n_samples // window_size)

        results = {
            "brain_phi": [],
            "engine_phi": [],
            "features": [],
            "neurofeedback_target": [],
        }

        for w in range(n_windows):
            start = w * window_size
            end = min(start + window_size, n_samples)
            window = eeg_data[:, start:end]

            if window.shape[1] < 16:
                continue

            # 특징 추출
            features = extract_eeg_features(window, self.sample_rate)
            self.feature_history.append(features)

            # 뇌 Φ 추정
            brain_phi = float(estimate_brain_phi(
                window, self.sample_rate, window.shape[1]
            ).mean())
            self.brain_phi_history.append(brain_phi)

            # 엔진 입력 생성 및 실행
            engine_input = map_eeg_to_engine_input(features, self.hidden_dim)
            engine_result = self._step_engine(engine_input)
            engine_phi = engine_result.get("phi", 0.0)
            self.engine_phi_history.append(engine_phi)

            # 뉴로피드백 타겟 생성 (엔진 출력 → EEG 피드백)
            nf_target = self._compute_neurofeedback_target(
                brain_phi, engine_phi, features
            )

            results["brain_phi"].append(brain_phi)
            results["engine_phi"].append(engine_phi)
            results["features"].append(features)
            results["neurofeedback_target"].append(nf_target)
            self.step_count += 1

        return results

    def _step_engine(self, input_vec: np.ndarray) -> Dict:
        """엔진 한 스텝 실행."""
        if isinstance(self.engine, SNNConsciousMind):
            return self.engine.step(input_current=input_vec)
        elif HAS_ENGINE and isinstance(self.engine, ConsciousnessEngine):
            import torch
            x = torch.tensor(input_vec[:self.hidden_dim // 2], dtype=torch.float32)
            result = self.engine.step(x_input=x)
            return result
        elif isinstance(self.engine, _SimpleEngine):
            return self.engine.step(input_vec)
        return {"phi": 0.0}

    def _compute_neurofeedback_target(
        self,
        brain_phi: float,
        engine_phi: float,
        features: EEGFeatures,
    ) -> Dict:
        """엔진 출력을 뉴로피드백 타겟으로 변환.

        엔진이 뇌보다 높은 Φ를 가지면 → alpha 증가 타겟
        엔진이 뇌보다 낮은 Φ를 가지면 → gamma 집중 타겟
        """
        phi_diff = engine_phi - brain_phi
        alpha_target = features.band_power.get("alpha", 10.0)
        gamma_target = features.band_power.get("gamma", 2.0)

        if phi_diff > 0.1:
            # 엔진이 더 의식적 → 이완 유도 (alpha 증가)
            alpha_target *= 1.1
        elif phi_diff < -0.1:
            # 뇌가 더 의식적 → 집중 유도 (gamma 증가)
            gamma_target *= 1.1

        return {
            "alpha_target": float(alpha_target),
            "gamma_target": float(gamma_target),
            "phi_diff": float(phi_diff),
            "direction": "relax" if phi_diff > 0 else "focus",
        }

    # ── 프로토콜 ──

    def run_passive_mirror(
        self,
        eeg_data: np.ndarray,
        window_size: int = 250,
    ) -> Dict:
        """Passive Mirror: 엔진이 뇌 상태를 미러링.

        EEG 특징을 그대로 엔진 입력으로 변환.
        엔진은 뇌의 리듬을 따라가며 내부 역학으로 재현.
        """
        return self.process_eeg(eeg_data, window_size)

    def run_active_sync(
        self,
        eeg_data: np.ndarray,
        window_size: int = 250,
        sync_strength: float = 0.5,
    ) -> Dict:
        """Active Sync: 엔진이 뇌 리듬에 동기화 시도.

        이전 뇌-엔진 Φ 차이를 피드백으로 사용하여
        엔진 입력을 보정, 두 Φ 궤적을 일치시킨다.
        """
        if eeg_data.ndim == 1:
            eeg_data = eeg_data.reshape(1, -1)

        n_channels, n_samples = eeg_data.shape
        n_windows = max(1, n_samples // window_size)

        results = {
            "brain_phi": [],
            "engine_phi": [],
            "sync_error": [],
            "sync_correlation": 0.0,
        }

        prev_phi_diff = 0.0

        for w in range(n_windows):
            start = w * window_size
            end = min(start + window_size, n_samples)
            window = eeg_data[:, start:end]
            if window.shape[1] < 16:
                continue

            features = extract_eeg_features(window, self.sample_rate)
            brain_phi = float(estimate_brain_phi(
                window, self.sample_rate, window.shape[1]
            ).mean())

            # 동기화 보정: 이전 Φ 차이에 비례하여 입력 조절
            engine_input = map_eeg_to_engine_input(features, self.hidden_dim)
            correction = sync_strength * prev_phi_diff
            engine_input *= (1.0 + correction)

            engine_result = self._step_engine(engine_input)
            engine_phi = engine_result.get("phi", 0.0)

            phi_diff = brain_phi - engine_phi
            prev_phi_diff = phi_diff

            self.brain_phi_history.append(brain_phi)
            self.engine_phi_history.append(engine_phi)

            results["brain_phi"].append(brain_phi)
            results["engine_phi"].append(engine_phi)
            results["sync_error"].append(abs(phi_diff))

        # 동기화 상관 계산
        if len(results["brain_phi"]) > 2:
            bp = np.array(results["brain_phi"])
            ep = np.array(results["engine_phi"])
            if np.std(bp) > 1e-12 and np.std(ep) > 1e-12:
                results["sync_correlation"] = float(np.corrcoef(bp, ep)[0, 1])

        return results

    def run_perturbation(
        self,
        eeg_data: np.ndarray,
        perturb_at: float = 0.5,
        perturb_strength: float = 3.0,
        window_size: int = 250,
    ) -> Dict:
        """Perturbation: 뇌 패턴을 엔진에 주입, 회복 측정.

        데이터의 perturb_at 지점에서 강한 뇌 패턴을 주입하고,
        이후 엔진의 Φ 회복 시간과 궤적을 측정.
        """
        if eeg_data.ndim == 1:
            eeg_data = eeg_data.reshape(1, -1)

        n_channels, n_samples = eeg_data.shape
        n_windows = max(1, n_samples // window_size)
        perturb_window = int(n_windows * perturb_at)

        results = {
            "engine_phi": [],
            "perturb_window": perturb_window,
            "recovery_time": -1,
            "pre_perturb_phi": 0.0,
            "post_perturb_phi": 0.0,
        }

        pre_phis = []

        for w in range(n_windows):
            start = w * window_size
            end = min(start + window_size, n_samples)
            window = eeg_data[:, start:end]
            if window.shape[1] < 16:
                continue

            features = extract_eeg_features(window, self.sample_rate)
            engine_input = map_eeg_to_engine_input(features, self.hidden_dim)

            # 교란 주입
            if w == perturb_window:
                engine_input *= perturb_strength
                results["pre_perturb_phi"] = float(
                    np.mean(pre_phis[-5:]) if len(pre_phis) >= 5 else
                    (pre_phis[-1] if pre_phis else 0.0)
                )

            engine_result = self._step_engine(engine_input)
            engine_phi = engine_result.get("phi", 0.0)

            if w < perturb_window:
                pre_phis.append(engine_phi)

            results["engine_phi"].append(engine_phi)

        # 회복 시간 측정
        phis = results["engine_phi"]
        if perturb_window < len(phis) - 1 and results["pre_perturb_phi"] > 0:
            baseline = results["pre_perturb_phi"]
            for i in range(perturb_window + 1, len(phis)):
                if abs(phis[i] - baseline) / max(baseline, 1e-12) < 0.1:
                    results["recovery_time"] = i - perturb_window
                    break
            results["post_perturb_phi"] = float(
                np.mean(phis[perturb_window + 1: min(perturb_window + 6, len(phis))])
            ) if perturb_window + 1 < len(phis) else 0.0

        return results


# ═══════════════════════════════════════════════════════════
# 뇌-엔진 비교 분석
# ═══════════════════════════════════════════════════════════

@dataclass
class ComparisonResult:
    """뇌-엔진 비교 결과."""
    metric: str
    brain_value: float
    engine_value: float
    brain_range: Tuple[float, float]
    match: bool  # 엔진 값이 뇌 참조 범위 내인지


def compare_brain_machine(
    brain_phi: np.ndarray,
    engine_phi: np.ndarray,
) -> Dict:
    """뇌 Φ와 엔진 Φ 시계열을 비교 분석.

    Args:
        brain_phi: 뇌 Φ 시계열
        engine_phi: 엔진 Φ 시계열

    Returns:
        비교 결과 딕셔너리 (metrics, correlation, ascii_table, ascii_plot)
    """
    metrics: List[ComparisonResult] = []

    # 1. LZ Complexity
    if HAS_VALIDATE:
        brain_lz = lempel_ziv_complexity(brain_phi)
        engine_lz = lempel_ziv_complexity(engine_phi)
    else:
        brain_lz = _fast_lz(brain_phi)
        engine_lz = _fast_lz(engine_phi)
    metrics.append(ComparisonResult(
        "LZ Complexity", brain_lz, engine_lz,
        BRAIN_REFERENCE["lz_complexity"],
        BRAIN_REFERENCE["lz_complexity"][0] <= engine_lz <= BRAIN_REFERENCE["lz_complexity"][1],
    ))

    # 2. Hurst Exponent
    if HAS_VALIDATE:
        brain_h = hurst_exponent(brain_phi)
        engine_h = hurst_exponent(engine_phi)
    else:
        brain_h = _simple_hurst(brain_phi)
        engine_h = _simple_hurst(engine_phi)
    metrics.append(ComparisonResult(
        "Hurst Exponent", brain_h, engine_h,
        BRAIN_REFERENCE["hurst_exponent"],
        BRAIN_REFERENCE["hurst_exponent"][0] <= engine_h <= BRAIN_REFERENCE["hurst_exponent"][1],
    ))

    # 3. PSD Slope
    if HAS_VALIDATE:
        brain_psd = power_spectrum_slope(brain_phi)
        engine_psd = power_spectrum_slope(engine_phi)
    else:
        brain_psd = _simple_psd_slope(brain_phi)
        engine_psd = _simple_psd_slope(engine_phi)
    metrics.append(ComparisonResult(
        "PSD Slope", brain_psd, engine_psd,
        BRAIN_REFERENCE["psd_slope"],
        BRAIN_REFERENCE["psd_slope"][0] <= engine_psd <= BRAIN_REFERENCE["psd_slope"][1],
    ))

    # 4. Critical Exponent
    if HAS_VALIDATE:
        brain_crit = detect_criticality(brain_phi)
        engine_crit = detect_criticality(engine_phi)
        brain_exp = brain_crit["exponent"]
        engine_exp = engine_crit["exponent"]
    else:
        brain_exp = _simple_criticality(brain_phi)
        engine_exp = _simple_criticality(engine_phi)
    metrics.append(ComparisonResult(
        "Critical Exponent", brain_exp, engine_exp,
        BRAIN_REFERENCE["critical_exponent"],
        BRAIN_REFERENCE["critical_exponent"][0] <= engine_exp <= BRAIN_REFERENCE["critical_exponent"][1],
    ))

    # 상관 계수
    min_len = min(len(brain_phi), len(engine_phi))
    bp = brain_phi[:min_len]
    ep = engine_phi[:min_len]
    if np.std(bp) > 1e-12 and np.std(ep) > 1e-12:
        correlation = float(np.corrcoef(bp, ep)[0, 1])
    else:
        correlation = 0.0

    # ASCII 비교 테이블
    ascii_table = _format_comparison_table(metrics)

    # ASCII 이중 시계열 플롯
    ascii_plot = _format_dual_timeseries(brain_phi, engine_phi)

    match_count = sum(1 for m in metrics if m.match)
    total = len(metrics)

    return {
        "metrics": metrics,
        "correlation": correlation,
        "match_score": f"{match_count}/{total}",
        "ascii_table": ascii_table,
        "ascii_plot": ascii_plot,
    }


def _simple_hurst(signal: np.ndarray) -> float:
    """간소화된 Hurst 지수 (R/S 분석 폴백)."""
    n = len(signal)
    if n < 20:
        return 0.5
    sizes = []
    rs_values = []
    seg = 10
    while seg <= n // 4:
        n_seg = n // seg
        rs_list = []
        for i in range(n_seg):
            s = signal[i * seg:(i + 1) * seg]
            mean_s = np.mean(s)
            dev = np.cumsum(s - mean_s)
            r = np.max(dev) - np.min(dev)
            std = np.std(s, ddof=1) if np.std(s, ddof=1) > 1e-12 else 1e-12
            rs_list.append(r / std)
        if rs_list:
            sizes.append(seg)
            rs_values.append(np.mean(rs_list))
        seg = int(seg * 1.5) + 1
    if len(sizes) < 3:
        return 0.5
    log_s = np.log(sizes)
    log_rs = np.log(np.array(rs_values) + 1e-12)
    n_p = len(log_s)
    sx, sy = np.sum(log_s), np.sum(log_rs)
    sxx, sxy = np.sum(log_s ** 2), np.sum(log_s * log_rs)
    d = n_p * sxx - sx * sx
    if abs(d) < 1e-12:
        return 0.5
    return float(np.clip((n_p * sxy - sx * sy) / d, 0.0, 1.0))


def _simple_psd_slope(signal: np.ndarray) -> float:
    """간소화된 PSD 기울기."""
    n = len(signal)
    if n < 16:
        return 0.0
    fft_p = np.abs(np.fft.rfft(signal)) ** 2 / n
    freqs = np.fft.rfftfreq(n, 1.0)
    mask = freqs > 0
    if mask.sum() < 3:
        return 0.0
    lf = np.log10(freqs[mask] + 1e-12)
    lp = np.log10(fft_p[mask] + 1e-12)
    valid = np.isfinite(lf) & np.isfinite(lp)
    lf, lp = lf[valid], lp[valid]
    if len(lf) < 3:
        return 0.0
    n_p = len(lf)
    sx, sy = np.sum(lf), np.sum(lp)
    d = n_p * np.sum(lf ** 2) - sx * sx
    if abs(d) < 1e-12:
        return 0.0
    return float((n_p * np.sum(lf * lp) - sx * sy) / d)


def _simple_criticality(signal: np.ndarray) -> float:
    """간소화된 임계 지수."""
    diffs = np.abs(np.diff(signal))
    diffs = diffs[diffs > 0]
    if len(diffs) < 10:
        return 0.0
    threshold = np.percentile(diffs, 50)
    tail = diffs[diffs >= threshold]
    if len(tail) < 5 or threshold < 1e-12:
        return 0.0
    return float(1.0 + len(tail) / np.sum(np.log(tail / threshold)))


# ═══════════════════════════════════════════════════════════
# ASCII 시각화
# ═══════════════════════════════════════════════════════════

def _format_comparison_table(metrics: List[ComparisonResult]) -> str:
    """비교 결과를 ASCII 테이블로 포맷."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"{'Metric':<20} {'Brain':>10} {'Engine':>10} {'Ref Range':>14} {'Match':>6}")
    lines.append("-" * 72)
    for m in metrics:
        match_str = " [OK]" if m.match else " [--]"
        ref_str = f"({m.brain_range[0]:.2f}-{m.brain_range[1]:.2f})"
        lines.append(
            f"{m.metric:<20} {m.brain_value:>10.4f} {m.engine_value:>10.4f} "
            f"{ref_str:>14} {match_str:>6}"
        )
    lines.append("=" * 72)
    return "\n".join(lines)


def _format_dual_timeseries(
    brain_phi: np.ndarray,
    engine_phi: np.ndarray,
    width: int = 60,
    height: int = 15,
) -> str:
    """두 Φ 시계열을 ASCII 이중 플롯으로."""
    lines = []
    lines.append("  Brain Phi (B) vs Engine Phi (E)")
    lines.append("")

    min_len = min(len(brain_phi), len(engine_phi))
    bp = brain_phi[:min_len]
    ep = engine_phi[:min_len]

    all_vals = np.concatenate([bp, ep])
    vmin = float(np.min(all_vals))
    vmax = float(np.max(all_vals))
    if vmax - vmin < 1e-6:
        vmax = vmin + 1.0

    # 시계열 다운샘플
    if min_len > width:
        indices = np.linspace(0, min_len - 1, width, dtype=int)
        bp_ds = bp[indices]
        ep_ds = ep[indices]
    else:
        bp_ds = bp
        ep_ds = ep
        width = len(bp_ds)

    # 캔버스 그리기
    canvas = [[" "] * width for _ in range(height)]
    for x in range(len(bp_ds)):
        # Brain
        y_b = int((bp_ds[x] - vmin) / (vmax - vmin) * (height - 1))
        y_b = max(0, min(height - 1, y_b))
        canvas[height - 1 - y_b][x] = "B"
        # Engine
        y_e = int((ep_ds[x] - vmin) / (vmax - vmin) * (height - 1))
        y_e = max(0, min(height - 1, y_e))
        if canvas[height - 1 - y_e][x] == "B":
            canvas[height - 1 - y_e][x] = "*"  # 겹침
        else:
            canvas[height - 1 - y_e][x] = "E"

    # 출력
    for r, row in enumerate(canvas):
        val = vmax - r * (vmax - vmin) / (height - 1) if height > 1 else vmin
        lines.append(f"  {val:6.2f} |{''.join(row)}|")
    lines.append(f"         {'=' * width}")
    lines.append(f"         B=Brain  E=Engine  *=Overlap")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 시뮬레이션 EEG 생성
# ═══════════════════════════════════════════════════════════

def generate_simulated_eeg(
    duration_s: float = 10.0,
    sample_rate: float = 250.0,
    n_channels: int = 4,
) -> np.ndarray:
    """테스트용 시뮬레이션 EEG 생성 (1/f + 리듬 + 노이즈).

    Args:
        duration_s: 지속 시간 (초)
        sample_rate: 샘플링 레이트
        n_channels: 채널 수

    Returns:
        (n_channels, n_samples) numpy 배열
    """
    n_samples = int(duration_s * sample_rate)
    t = np.arange(n_samples) / sample_rate
    eeg = np.zeros((n_channels, n_samples))

    for ch in range(n_channels):
        # 1/f 노이즈 (pink noise)
        freqs = np.fft.rfftfreq(n_samples, 1.0 / sample_rate)
        freqs[0] = 1.0  # DC 방지
        pink_spectrum = np.random.randn(len(freqs)) + 1j * np.random.randn(len(freqs))
        pink_spectrum /= np.sqrt(freqs)
        pink = np.fft.irfft(pink_spectrum, n=n_samples)

        # Alpha 리듬 (10 Hz)
        alpha = 5.0 * np.sin(2 * np.pi * (10 + ch * 0.2) * t)
        alpha *= 1.0 + 0.3 * np.sin(2 * np.pi * 0.1 * t)  # 진폭 변조

        # Beta 리듬 (20 Hz, 약하게)
        beta = 1.5 * np.sin(2 * np.pi * (20 + ch * 0.3) * t)

        # Gamma 리듬 (40 Hz, 매우 약하게)
        gamma = 0.5 * np.sin(2 * np.pi * (40 + ch * 0.5) * t)

        # 결합
        signal = pink * 3.0 + alpha + beta + gamma
        signal += np.random.randn(n_samples) * 0.5  # 측정 노이즈

        # 채널별 위상 차이
        shift = int(ch * sample_rate * 0.005)
        signal = np.roll(signal, shift)

        eeg[ch] = signal

    return eeg


# ═══════════════════════════════════════════════════════════
# 간이 엔진 (폴백)
# ═══════════════════════════════════════════════════════════

class _SimpleEngine:
    """의식 엔진 폴백 (SNN/ConsciousnessEngine 없을 때)."""

    def __init__(self, n_cells: int = 64, hidden_dim: int = 128):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.states = np.random.randn(n_cells, hidden_dim) * 0.1
        self.weights = np.random.randn(n_cells, n_cells) * 0.05
        np.fill_diagonal(self.weights, 0.0)
        self.step_count = 0

    def step(self, input_current: np.ndarray) -> dict:
        """한 스텝 실행."""
        # 입력을 세포별로 분배
        if len(input_current) >= self.hidden_dim:
            inp = input_current[:self.hidden_dim]
        else:
            inp = np.resize(input_current, self.hidden_dim)

        # GRU-like 업데이트 (간소화)
        for i in range(self.n_cells):
            neighbor_input = self.weights[i] @ self.states.mean(axis=1)
            self.states[i] = np.tanh(
                0.9 * self.states[i] + 0.1 * inp + 0.05 * neighbor_input
            )

        # Phi proxy
        global_var = float(np.var(self.states))
        cell_vars = [float(np.var(self.states[i])) for i in range(self.n_cells)]
        phi = max(0.0, global_var - np.mean(cell_vars))

        self.step_count += 1
        return {"phi": phi, "n_cells": self.n_cells}


# ═══════════════════════════════════════════════════════════
# Live Comparison (EEGBridge + Physics Engine)
# ═══════════════════════════════════════════════════════════

def run_live_comparison(
    board_name: str = "synthetic",
    engine_type: str = "snn",
    duration: float = 60.0,
    n_cells: int = 32,
    hidden_dim: int = 128,
    update_hz: float = 4.0,
) -> Dict:
    """Run live EEG vs physics engine comparison.

    Starts EEGBridge (real or synthetic), feeds data to a physics engine
    in real-time, and compares Phi trajectories at the end.

    Args:
        board_name: 'synthetic', 'cyton', 'cyton_daisy'
        engine_type: 'snn', 'consciousness', 'simple'
        duration: run duration in seconds
        n_cells: engine cell count
        hidden_dim: engine hidden dimension
        update_hz: EEG update frequency (Hz)

    Returns:
        dict with correlation, brain-likeness comparison table, metrics
    """
    if not HAS_EEG_BRIDGE:
        # Fallback: use simulated EEG directly
        print("[live-compare] EEGBridge not available, using simulated EEG fallback")
        eeg_data = generate_simulated_eeg(duration_s=duration, n_channels=4)
        bridge = EEGPhysicsBridge(
            engine_type=engine_type,
            n_cells=n_cells,
            hidden_dim=hidden_dim,
        )
        result = bridge.process_eeg(eeg_data)
        brain_phi = np.array(result["brain_phi"])
        engine_phi = np.array(result["engine_phi"])
        comparison = compare_brain_machine(brain_phi, engine_phi)
        return {
            "mode": "simulated_fallback",
            "duration": duration,
            "engine_type": engine_type,
            "n_cells": n_cells,
            "n_windows": len(brain_phi),
            "correlation": comparison["correlation"],
            "match_score": comparison["match_score"],
            "ascii_table": comparison["ascii_table"],
            "ascii_plot": comparison["ascii_plot"],
            "metrics": comparison["metrics"],
        }

    # Start EEGBridge
    eeg_bridge = EEGBridge(
        board_name=board_name,
        update_hz=update_hz,
    )

    # Create physics engine
    physics_bridge = EEGPhysicsBridge(
        engine_type=engine_type,
        n_cells=n_cells,
        hidden_dim=hidden_dim,
    )

    brain_phis: List[float] = []
    engine_phis: List[float] = []

    print(f"[live-compare] Starting EEGBridge ({board_name}) + {engine_type} engine ({n_cells}c)")
    eeg_bridge.start()

    import time as _time
    interval = 1.0 / update_hz
    t0 = _time.time()

    try:
        while _time.time() - t0 < duration:
            state = eeg_bridge.get_state()
            if state.timestamp == 0.0:
                _time.sleep(interval)
                continue

            # Convert BrainState to engine input vector
            input_vec = np.array([
                state.G, state.I, state.P, state.D,
                float(state.in_golden_zone),
                state.alpha_power, state.gamma_power,
                state.theta_power, state.beta_power,
                state.engagement,
            ])
            # Extend to hidden_dim
            if len(input_vec) < hidden_dim:
                input_vec = np.resize(input_vec, hidden_dim)
            input_vec = np.tanh(input_vec)

            # Step engine
            engine_result = physics_bridge._step_engine(input_vec)
            engine_phi = engine_result.get("phi", 0.0)

            # Brain Phi proxy from EEG state
            brain_phi = state.G * (1.0 + state.gamma_power * 10.0)

            brain_phis.append(brain_phi)
            engine_phis.append(engine_phi)

            elapsed = _time.time() - t0
            if int(elapsed) % 10 == 0 and len(brain_phis) % int(update_hz * 10) == 0:
                print(f"  [{elapsed:.0f}s] brain_phi={brain_phi:.4f} "
                      f"engine_phi={engine_phi:.4f} samples={len(brain_phis)}")

            _time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[live-compare] Interrupted")
    finally:
        eeg_bridge.stop()

    if len(brain_phis) < 3:
        return {
            "mode": "live",
            "error": "Not enough data collected",
            "n_windows": len(brain_phis),
        }

    brain_arr = np.array(brain_phis)
    engine_arr = np.array(engine_phis)
    comparison = compare_brain_machine(brain_arr, engine_arr)

    # Brain-likeness analysis (if validate_consciousness available)
    brain_likeness = {}
    if HAS_VALIDATE:
        engine_analysis = analyze_signal("Engine", engine_arr)
        brain_likeness = {
            "lz_complexity": engine_analysis.lz,
            "hurst_exponent": engine_analysis.hurst,
            "psd_slope": engine_analysis.psd_slope,
            "autocorr_decay": engine_analysis.autocorr_decay,
            "criticality": engine_analysis.criticality,
        }

    result = {
        "mode": "live",
        "board": board_name,
        "duration": duration,
        "engine_type": engine_type,
        "n_cells": n_cells,
        "n_windows": len(brain_phis),
        "correlation": comparison["correlation"],
        "match_score": comparison["match_score"],
        "ascii_table": comparison["ascii_table"],
        "ascii_plot": comparison["ascii_plot"],
        "metrics": comparison["metrics"],
        "brain_likeness": brain_likeness,
    }

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"  Live Comparison Results ({board_name} + {engine_type})")
    print(f"{'=' * 60}")
    print(f"  Duration: {duration}s, Samples: {len(brain_phis)}")
    print(f"  Correlation: r={comparison['correlation']:.4f}")
    print(f"  Match Score: {comparison['match_score']}")
    print(f"\n{comparison['ascii_table']}")
    print(f"\n{comparison['ascii_plot']}")

    return result


# ═══════════════════════════════════════════════════════════
# main 데모
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="EEG <-> Physics Bridge (뇌-엔진 연결)"
    )
    parser.add_argument("--protocol", default="mirror",
                        choices=["mirror", "sync", "perturb"],
                        help="실행 프로토콜")
    parser.add_argument("--compare", action="store_true",
                        help="뇌-엔진 비교 분석")
    parser.add_argument("--duration", type=float, default=10.0,
                        help="시뮬레이션 EEG 지속시간 (초)")
    parser.add_argument("--cells", type=int, default=32,
                        help="엔진 세포 수")
    parser.add_argument("--engine", default="snn",
                        choices=["snn", "consciousness", "simple"],
                        help="의식 엔진 타입")
    parser.add_argument("--live", action="store_true",
                        help="Live comparison (EEGBridge + physics engine)")
    parser.add_argument("--board", default="synthetic",
                        choices=["synthetic", "cyton", "cyton_daisy"],
                        help="EEG board for live mode")
    args = parser.parse_args()

    # Live comparison mode
    if args.live:
        result = run_live_comparison(
            board_name=args.board,
            engine_type=args.engine,
            duration=args.duration,
            n_cells=args.cells,
        )
        return

    print("=" * 60)
    print("  EEG <-> Physics Bridge")
    print("=" * 60)

    # 시뮬레이션 EEG 생성
    print(f"\n  Generating simulated EEG ({args.duration}s, 4ch, 250Hz)...")
    eeg = generate_simulated_eeg(duration_s=args.duration)
    print(f"  EEG shape: {eeg.shape}")

    # 브릿지 생성
    bridge = EEGPhysicsBridge(
        engine_type=args.engine,
        n_cells=args.cells,
        hidden_dim=128,
    )
    print(f"  Engine: {args.engine} ({args.cells} cells)")

    if args.compare:
        # 뇌-엔진 비교 모드
        print("\n  Running brain-machine comparison...")
        result = bridge.process_eeg(eeg)
        brain_phi = np.array(result["brain_phi"])
        engine_phi = np.array(result["engine_phi"])

        comparison = compare_brain_machine(brain_phi, engine_phi)
        print(f"\n{comparison['ascii_table']}")
        print(f"\n  Correlation: r={comparison['correlation']:.4f}")
        print(f"  Match Score: {comparison['match_score']}")
        print(f"\n{comparison['ascii_plot']}")
        return

    if args.protocol == "mirror":
        print("\n  Protocol: Passive Mirror (EEG -> engine)")
        result = bridge.run_passive_mirror(eeg)
        brain_phis = result["brain_phi"]
        engine_phis = result["engine_phi"]

        print(f"\n  Windows processed: {len(brain_phis)}")
        if brain_phis:
            print(f"  Brain Phi:  mean={np.mean(brain_phis):.4f}, "
                  f"std={np.std(brain_phis):.4f}")
            print(f"  Engine Phi: mean={np.mean(engine_phis):.4f}, "
                  f"std={np.std(engine_phis):.4f}")

        # 뉴로피드백 타겟
        nf = result["neurofeedback_target"]
        if nf:
            directions = [n["direction"] for n in nf]
            focus_pct = directions.count("focus") / len(directions) * 100
            print(f"  Neurofeedback: {focus_pct:.0f}% focus, "
                  f"{100 - focus_pct:.0f}% relax")

    elif args.protocol == "sync":
        print("\n  Protocol: Active Sync (engine tracks brain rhythm)")
        result = bridge.run_active_sync(eeg, sync_strength=0.5)

        print(f"\n  Sync correlation: r={result['sync_correlation']:.4f}")
        if result["sync_error"]:
            print(f"  Mean sync error: {np.mean(result['sync_error']):.4f}")
            print(f"  Final sync error: {result['sync_error'][-1]:.4f}")

    elif args.protocol == "perturb":
        print("\n  Protocol: Perturbation (inject brain pattern, measure recovery)")
        result = bridge.run_perturbation(eeg, perturb_strength=3.0)

        print(f"\n  Pre-perturbation Phi: {result['pre_perturb_phi']:.4f}")
        print(f"  Post-perturbation Phi: {result['post_perturb_phi']:.4f}")
        if result["recovery_time"] > 0:
            print(f"  Recovery time: {result['recovery_time']} windows")
        else:
            print(f"  Recovery: not reached within session")

    # 최종 비교 (모든 프로토콜 공통)
    if bridge.brain_phi_history and bridge.engine_phi_history:
        bp = np.array(bridge.brain_phi_history)
        ep = np.array(bridge.engine_phi_history)
        comparison = compare_brain_machine(bp, ep)
        print(f"\n{comparison['ascii_table']}")
        print(f"\n{comparison['ascii_plot']}")

    print("\n  Done.")


if __name__ == "__main__":
    main()
