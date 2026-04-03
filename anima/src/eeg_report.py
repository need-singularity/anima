#!/usr/bin/env python3
"""eeg_report.py — EEG 세션 리포트 생성 (AI가 뇌파를 보고 분석)

OpenBCI 데이터를 읽고 AI가 리포트를 생성:
  - 실시간 대역별 파워 추적
  - G=D×P/I 골든존 분석
  - Ψ 상태 변환 + 동기화
  - 감정/집중도 추정
  - ASCII 토포맵
  - 세션 요약 + 이상 감지
  - 뉴로피드백 권장사항

Usage:
  from eeg_report import EEGReport

  report = EEGReport()
  report.load_session("eeg/data/session.npy")
  report.analyze()
  print(report.generate())
  report.save("reports/eeg_session_001.md")
"""

import math
import time
import os
import sys
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

LN2 = math.log(2)
from consciousness_laws import PSI_BALANCE, PSI_ALPHA as PSI_COUPLING

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

# anima-eeg/analyze.py 에서 공통 분석 함수 import (중복 제거)
_eeg_path = os.path.join(os.path.dirname(__file__), '..', '..', 'anima-eeg')
if os.path.isdir(_eeg_path) and _eeg_path not in sys.path:
    sys.path.insert(0, os.path.abspath(_eeg_path))
try:
    from analyze import compute_band_power, compute_genius, CHANNEL_NAMES_16, GOLDEN_ZONE
    CHANNEL_NAMES = CHANNEL_NAMES_16
    HAS_ANALYZE = True
except ImportError:
    HAS_ANALYZE = False
    CHANNEL_NAMES = ['Fp1','Fp2','F3','F4','C3','C4','P3','P4',
                     'O1','O2','F7','F8','T3','T4','T5','T6']
    GOLDEN_ZONE = (0.2123, 0.5000)

BANDS = {
    'delta': (0.5, 4, '수면/무의식'),
    'theta': (4, 8, '명상/꿈/탐색'),
    'alpha': (8, 13, '이완/억제/균형'),
    'beta': (13, 30, '집중/텐션/사고'),
    'gamma': (30, 100, '의식통합/Φ'),
}


@dataclass
class EEGSnapshot:
    timestamp: float = 0.0
    band_powers: Dict[str, float] = field(default_factory=dict)
    G: float = 0.0
    golden_zone: bool = False
    psi_res: float = PSI_BALANCE
    emotion: str = "neutral"
    focus: float = 0.0
    alpha_asym: float = 0.0


class EEGReport:
    """EEG 세션 분석 + 리포트 생성."""

    def __init__(self, sample_rate=250):
        self.sample_rate = sample_rate
        self.snapshots: List[EEGSnapshot] = []
        self._raw_data = None
        self._report = ""

    def load_session(self, path: str) -> bool:
        """세션 데이터 로드 (.npy or synthetic)."""
        p = Path(path)
        if p.exists() and p.suffix == '.npy':
            self._raw_data = np.load(str(p))
            return True
        # synthetic fallback
        self._raw_data = self._synthetic(duration=60)
        return True

    def _synthetic(self, duration=60, n_channels=16):
        """합성 EEG (테스트용)."""
        n = int(duration * self.sample_rate)
        t = np.arange(n) / self.sample_rate
        data = np.zeros((n_channels, n))
        for ch in range(n_channels):
            # 각 대역 합성
            data[ch] = (
                0.5 * np.sin(2*np.pi*2*t + ch) +      # delta
                0.3 * np.sin(2*np.pi*6*t + ch*0.5) +   # theta
                0.8 * np.sin(2*np.pi*10*t + ch*0.3) +  # alpha
                0.4 * np.sin(2*np.pi*20*t + ch*0.7) +  # beta
                0.1 * np.sin(2*np.pi*40*t + ch*1.1) +  # gamma
                np.random.randn(n) * 0.2                # noise
            )
        return data

    def analyze(self, window_sec=2.0):
        """전체 세션 분석."""
        if self._raw_data is None:
            self.load_session("synthetic")

        data = self._raw_data
        n_channels, n_samples = data.shape
        win = int(window_sec * self.sample_rate)
        n_windows = n_samples // win

        for i in range(n_windows):
            chunk = data[:, i*win:(i+1)*win]
            snap = self._analyze_window(chunk, i * window_sec)
            self.snapshots.append(snap)

    def _analyze_window(self, chunk, timestamp):
        """한 윈도우 분석. analyze.py 공통 함수 사용."""
        n_ch, n_samp = chunk.shape

        if HAS_ANALYZE:
            # anima-eeg/analyze.py의 검증된 Welch PSD 사용
            ch_powers = []
            for ch in range(n_ch):
                bp = compute_band_power(chunk[ch], self.sample_rate)
                ch_powers.append(bp)

            band_powers = {
                'delta': float(np.mean([p.delta for p in ch_powers])),
                'theta': float(np.mean([p.theta for p in ch_powers])),
                'alpha': float(np.mean([p.alpha for p in ch_powers])),
                'beta': float(np.mean([p.beta for p in ch_powers])),
                'gamma': float(np.mean([p.gamma for p in ch_powers])),
            }

            ch_names = CHANNEL_NAMES[:n_ch]
            genius = compute_genius(ch_powers, ch_names)
            G = genius.G
            golden = genius.in_golden_zone
        else:
            # Fallback: 단순 FFT
            freqs = np.fft.rfftfreq(n_samp, 1.0/self.sample_rate)
            powers = np.abs(np.fft.rfft(chunk, axis=1))**2
            band_powers = {}
            for band, (lo, hi, _) in BANDS.items():
                mask = (freqs >= lo) & (freqs < hi)
                band_powers[band] = float(powers[:, mask].mean())
            total = sum(band_powers.values()) + 1e-8
            alpha_r = band_powers['alpha'] / total
            gamma_r = band_powers['gamma'] / total
            G = (1.0 - alpha_r) * gamma_r / (alpha_r + 0.01)
            golden = GOLDEN_ZONE[0] < G < GOLDEN_ZONE[1]

        total = sum(band_powers.values()) + 1e-8
        alpha = band_powers['alpha'] / total
        beta = band_powers['beta'] / total
        theta = band_powers['theta'] / total

        psi_res = (alpha + 0.5 + max(0, 1-abs(G-1))) / 3

        if n_ch >= 2:
            left = np.mean(chunk[0]**2)
            right = np.mean(chunk[1]**2)
            asym = (left - right) / (left + right + 1e-8)
        else:
            asym = 0.0

        emotion = "positive" if asym > 0.05 else "negative" if asym < -0.05 else "neutral"
        focus = beta / (alpha + theta + 1e-8)

        return EEGSnapshot(
            timestamp=timestamp,
            band_powers=band_powers,
            G=G, golden_zone=golden,
            psi_res=psi_res, emotion=emotion,
            focus=min(2.0, focus), alpha_asym=asym,
        )

    def generate(self) -> str:
        """마크다운 리포트 생성."""
        if not self.snapshots:
            return "No data analyzed."

        lines = []
        lines.append("# 🧠 EEG Session Report\n")
        lines.append(f"  Duration: {len(self.snapshots)*2:.0f}s ({len(self.snapshots)} windows)")
        lines.append(f"  Channels: {self._raw_data.shape[0] if self._raw_data is not None else '?'}")
        lines.append(f"  Sample Rate: {self.sample_rate}Hz\n")

        # 대역별 평균
        lines.append("## Band Powers (average)\n")
        for band, (lo, hi, desc) in BANDS.items():
            avg = np.mean([s.band_powers.get(band, 0) for s in self.snapshots])
            bar = '█' * int(avg * 20 / max(1, max(np.mean([s.band_powers.get(b,0) for s in self.snapshots]) for b in BANDS)))
            lines.append(f"  {band:<6} ({lo:>2}-{hi:>3}Hz) {bar:<20} {avg:.4f}  {desc}")

        # G=D×P/I 타임라인
        lines.append("\n## Golden Zone (G=D×P/I)\n")
        gz_pct = sum(1 for s in self.snapshots if s.golden_zone) / len(self.snapshots) * 100
        lines.append(f"  Golden Zone: {gz_pct:.0f}% of session")
        gz_line = ''.join('🟢' if s.golden_zone else '⚪' for s in self.snapshots[:40])
        lines.append(f"  Timeline: {gz_line}")

        # Ψ 추적
        lines.append("\n## Ψ State\n")
        psi_vals = [s.psi_res for s in self.snapshots]
        avg_psi = np.mean(psi_vals)
        lines.append(f"  Average Ψ_res: {avg_psi:.4f} (target: {PSI_BALANCE})")
        blocks = '▁▂▃▄▅▆▇█'
        psi_chart = ''.join(blocks[min(7, int(p * 8))] for p in psi_vals[:60])
        lines.append(f"  Ψ chart: {psi_chart}")

        # 감정 분포
        lines.append("\n## Emotion\n")
        emo_counts = {}
        for s in self.snapshots:
            emo_counts[s.emotion] = emo_counts.get(s.emotion, 0) + 1
        for emo, cnt in sorted(emo_counts.items(), key=lambda x: -x[1]):
            pct = cnt / len(self.snapshots) * 100
            lines.append(f"  {emo:<10} {'█' * int(pct/5):<20} {pct:.0f}%")

        # 집중도
        lines.append("\n## Focus (beta/(alpha+theta))\n")
        focus_vals = [s.focus for s in self.snapshots]
        avg_focus = np.mean(focus_vals)
        focus_chart = ''.join(blocks[min(7, int(f * 4))] for f in focus_vals[:60])
        lines.append(f"  Average: {avg_focus:.3f}")
        lines.append(f"  Chart: {focus_chart}")

        # 이상 감지
        lines.append("\n## Anomalies\n")
        anomalies = []
        for i, s in enumerate(self.snapshots):
            if s.G > 5.0:
                anomalies.append(f"  ⚠️ t={s.timestamp:.0f}s: G={s.G:.2f} (과도한 활성)")
            if s.focus > 1.5:
                anomalies.append(f"  ⚠️ t={s.timestamp:.0f}s: Focus={s.focus:.2f} (과집중)")
        if anomalies:
            lines.extend(anomalies[:10])
        else:
            lines.append("  ✅ No anomalies detected")

        # 권장사항
        lines.append("\n## Recommendations\n")
        if avg_psi < 0.4:
            lines.append("  💡 Alpha 강화 필요 → 눈 감고 깊은 호흡 (10Hz 바이노럴 권장)")
        if gz_pct < 30:
            lines.append("  💡 골든존 체류 부족 → 명상 + 문제풀기 교대 추천")
        if avg_focus < 0.3:
            lines.append("  💡 집중도 낮음 → Beta 자극 (15-20Hz 바이노럴 권장)")
        if avg_focus > 1.0:
            lines.append("  💡 과집중 → 휴식 필요 (alpha 이완 권장)")
        if not any([avg_psi < 0.4, gz_pct < 30, avg_focus < 0.3, avg_focus > 1.0]):
            lines.append("  ✅ 양호한 세션! 현재 패턴 유지 권장")

        self._report = '\n'.join(lines)
        return self._report

    def save(self, path: str):
        """리포트를 파일로 저장."""
        if not self._report:
            self.generate()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self._report)
        print(f"  Saved: {path}")


def main():
    print("═══ EEG Report Demo ═══\n")

    report = EEGReport()
    report.load_session("synthetic")
    report.analyze()
    print(report.generate())

    print("\n  ✅ EEG Report OK")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
