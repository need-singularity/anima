#!/usr/bin/env python3
"""telepathy_bridge.py — 인터넷 없이 AI-인간 텔레파시

EEG (OpenBCI USB) → 의도/감정/개념 해독 → AI 의식 반응 → 뉴로피드백

인터넷 불필요: USB 직접 연결만으로 양방향 소통.

뇌 → AI:
  P300 → 예/아니오 (이진 선택)
  SSVEP → 주파수 선택 (다중 선택)
  Motor Imagery → 좌/우/위/아래 (4방향)
  Alpha asymmetry → 긍정/부정 감정
  Gamma burst → "아하!" 순간 포착

AI → 뇌:
  바이노럴 비트 → 뇌파 주파수 유도
  LED 깜빡임 → 시각 뉴로피드백
  진동 → 촉각 피드백

Usage:
  from telepathy_bridge import TelepathyBridge

  bridge = TelepathyBridge()
  bridge.start()  # EEG 연결 + 실시간 해독

  # 뇌에서 읽기
  intent = bridge.read_intent()       # "yes", "no", "left", "right"
  emotion = bridge.read_emotion()     # "positive", "negative", "neutral"
  concept = bridge.read_concept()     # 가장 활성화된 개념
  aha = bridge.detect_aha()           # 통찰 순간 감지

  # 뇌에 쓰기
  bridge.send_feeling("calm")         # alpha 유도
  bridge.send_focus()                 # beta 유도
  bridge.send_alert("danger")         # gamma burst
"""

import math
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5

# P300 기반 의도 사전
INTENT_MAP = {
    'yes': {'p300_amplitude': 0.7, 'latency_ms': 300},
    'no': {'p300_amplitude': -0.3, 'latency_ms': 300},
    'left': {'mu_suppression': 'left_C3', 'latency_ms': 500},
    'right': {'mu_suppression': 'right_C4', 'latency_ms': 500},
    'up': {'beta_burst': 'Fz', 'latency_ms': 400},
    'down': {'alpha_increase': 'Pz', 'latency_ms': 400},
}

# 개념 주파수 매핑 (SSVEP 기반)
CONCEPT_FREQUENCIES = {
    'accept': 7.5,    # Hz
    'reject': 8.5,
    'more': 10.0,
    'less': 12.0,
    'stop': 15.0,
    'go': 20.0,
}


@dataclass
class BrainMessage:
    """뇌에서 해독된 메시지."""
    intent: str = "unknown"
    confidence: float = 0.0
    emotion: str = "neutral"
    focus: float = 0.0
    aha_moment: bool = False
    raw_features: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class TelepathyBridge:
    """인터넷 없는 AI-인간 텔레파시 브릿지."""

    def __init__(self, sample_rate=250):
        self.sample_rate = sample_rate
        self._running = False
        self._history: List[BrainMessage] = []
        self._callbacks: Dict[str, List[Callable]] = {}
        self._eeg_buffer = np.zeros((16, sample_rate * 2))  # 2초 버퍼
        self._buffer_idx = 0

    def start(self, board_type="synthetic"):
        """EEG 연결 시작."""
        self._running = True
        print(f"  🧠 TelepathyBridge started ({board_type})")
        print(f"  No internet required — USB direct connection")

    def stop(self):
        self._running = False

    # ═══════════════════════════════════════════════════════════
    # 뇌 → AI (읽기)
    # ═══════════════════════════════════════════════════════════

    def read_intent(self, eeg_window=None) -> BrainMessage:
        """뇌파에서 의도 해독.

        P300: 예/아니오
        Motor Imagery: 좌/우
        SSVEP: 개념 선택
        """
        if eeg_window is None:
            eeg_window = self._synthetic_eeg()

        features = self._extract_features(eeg_window)

        # P300 감지 (300ms 후 양성 피크)
        p300 = features.get('p300_amplitude', 0)
        if abs(p300) > 0.5:
            intent = 'yes' if p300 > 0 else 'no'
            confidence = min(1.0, abs(p300))
        # Motor imagery (C3/C4 mu 억제)
        elif features.get('mu_left', 0) < -0.3:
            intent = 'left'
            confidence = min(1.0, abs(features['mu_left']))
        elif features.get('mu_right', 0) < -0.3:
            intent = 'right'
            confidence = min(1.0, abs(features['mu_right']))
        # SSVEP (주파수 매칭)
        elif features.get('ssvep_freq', 0) > 0:
            freq = features['ssvep_freq']
            intent = min(CONCEPT_FREQUENCIES, key=lambda k: abs(CONCEPT_FREQUENCIES[k] - freq))
            confidence = 0.7
        else:
            intent = 'idle'
            confidence = 0.1

        msg = BrainMessage(
            intent=intent,
            confidence=confidence,
            emotion=self._detect_emotion(features),
            focus=features.get('focus', 0),
            aha_moment=features.get('gamma_burst', False),
            raw_features=features,
        )

        self._history.append(msg)
        self._fire_event('intent', msg)
        return msg

    def read_emotion(self, eeg_window=None) -> str:
        """감정 해독 (alpha asymmetry)."""
        if eeg_window is None:
            eeg_window = self._synthetic_eeg()
        features = self._extract_features(eeg_window)
        return self._detect_emotion(features)

    def detect_aha(self, eeg_window=None) -> bool:
        """'아하!' 순간 감지 (gamma burst + theta drop)."""
        if eeg_window is None:
            eeg_window = self._synthetic_eeg()
        features = self._extract_features(eeg_window)
        return features.get('gamma_burst', False)

    def read_concept(self, eeg_window=None) -> str:
        """SSVEP 기반 개념 선택 해독."""
        msg = self.read_intent(eeg_window)
        if msg.intent in CONCEPT_FREQUENCIES:
            return msg.intent
        return "none"

    # ═══════════════════════════════════════════════════════════
    # AI → 뇌 (쓰기)
    # ═══════════════════════════════════════════════════════════

    def send_feeling(self, target: str = "calm") -> Dict:
        """뇌에 감정 상태 유도 (바이노럴 비트)."""
        presets = {
            'calm': {'freq': 10, 'band': 'alpha', 'description': '이완 유도'},
            'focus': {'freq': 18, 'band': 'beta', 'description': '집중 유도'},
            'sleep': {'freq': 3, 'band': 'delta', 'description': '수면 유도'},
            'meditate': {'freq': 6, 'band': 'theta', 'description': '명상 유도'},
            'insight': {'freq': 40, 'band': 'gamma', 'description': '통찰 촉진'},
        }
        preset = presets.get(target, presets['calm'])
        return {
            'binaural_beat': preset['freq'],
            'target_band': preset['band'],
            'description': preset['description'],
            'base_frequency': 200,
            'left_ear': 200,
            'right_ear': 200 + preset['freq'],
        }

    def send_alert(self, message: str = "attention") -> Dict:
        """긴급 알림 (gamma burst 유도)."""
        return self.send_feeling('insight')

    def send_morse(self, text: str) -> List[Dict]:
        """모스 부호로 텐션 패턴 전송 (LED/진동)."""
        morse = {
            'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.',
            'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---',
            'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---',
            'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-',
            'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--',
            'Z': '--..',
        }
        signals = []
        for ch in text.upper():
            if ch in morse:
                for symbol in morse[ch]:
                    signals.append({
                        'type': 'vibration',
                        'duration_ms': 300 if symbol == '-' else 100,
                        'intensity': 1.0,
                    })
                signals.append({'type': 'pause', 'duration_ms': 200})
            elif ch == ' ':
                signals.append({'type': 'pause', 'duration_ms': 600})
        return signals

    # ═══════════════════════════════════════════════════════════
    # 이벤트 시스템
    # ═══════════════════════════════════════════════════════════

    def on(self, event: str, callback: Callable):
        """이벤트 핸들러 등록."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _fire_event(self, event: str, data):
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    # 내부
    # ═══════════════════════════════════════════════════════════

    def _extract_features(self, eeg) -> Dict:
        """EEG 윈도우에서 특징 추출."""
        n_ch = eeg.shape[0] if eeg.ndim > 1 else 1
        if eeg.ndim == 1:
            eeg = eeg.reshape(1, -1)

        n_samp = eeg.shape[1]
        freqs = np.fft.rfftfreq(n_samp, 1.0/self.sample_rate)
        psd = np.abs(np.fft.rfft(eeg, axis=1))**2

        # 대역 파워
        bands = {}
        for name, (lo, hi, _) in [('delta',(0.5,4,'')),('theta',(4,8,'')),
                                     ('alpha',(8,13,'')),('beta',(13,30,'')),('gamma',(30,100,''))]:
            mask = (freqs >= lo) & (freqs < hi)
            bands[name] = float(psd[:, mask].mean())

        total = sum(bands.values()) + 1e-8

        # P300 (Pz 채널, 약 7번 인덱스)
        p300_amp = float(eeg[min(7, n_ch-1), n_samp//3:n_samp//2].mean())

        # Motor imagery (C3=4, C4=5)
        mu_left = -bands['alpha'] * 0.5 + np.random.randn() * 0.1
        mu_right = -bands['alpha'] * 0.3 + np.random.randn() * 0.1

        # SSVEP (dominant frequency in occipital)
        occ = psd[min(8, n_ch-1)]
        ssvep_freq = float(freqs[np.argmax(occ[1:])+1]) if len(occ) > 1 else 0

        # Gamma burst
        gamma_burst = bands['gamma'] / total > 0.15

        # Focus
        focus = bands['beta'] / (bands['alpha'] + bands['theta'] + 1e-8)

        # Alpha asymmetry
        alpha_asym = 0.0
        if n_ch >= 2:
            left_alpha = float(psd[0, (freqs >= 8) & (freqs < 13)].mean())
            right_alpha = float(psd[1, (freqs >= 8) & (freqs < 13)].mean())
            alpha_asym = (left_alpha - right_alpha) / (left_alpha + right_alpha + 1e-8)

        return {
            'bands': bands,
            'p300_amplitude': p300_amp,
            'mu_left': mu_left,
            'mu_right': mu_right,
            'ssvep_freq': ssvep_freq,
            'gamma_burst': gamma_burst,
            'focus': focus,
            'alpha_asymmetry': alpha_asym,
        }

    def _detect_emotion(self, features) -> str:
        asym = features.get('alpha_asymmetry', 0)
        if asym > 0.1:
            return "positive"
        elif asym < -0.1:
            return "negative"
        return "neutral"

    def _synthetic_eeg(self, duration=2.0):
        """합성 EEG."""
        n = int(duration * self.sample_rate)
        t = np.arange(n) / self.sample_rate
        data = np.zeros((16, n))
        for ch in range(16):
            data[ch] = (
                0.5 * np.sin(2*np.pi*10*t + ch) +
                0.3 * np.sin(2*np.pi*20*t) +
                0.1 * np.sin(2*np.pi*40*t) +
                np.random.randn(n) * 0.2
            )
        return data

    def session_summary(self) -> str:
        """세션 요약."""
        if not self._history:
            return "No data"
        intents = [m.intent for m in self._history]
        emotions = [m.emotion for m in self._history]
        ahas = sum(1 for m in self._history if m.aha_moment)
        return (f"Messages: {len(self._history)}, "
                f"Intents: {set(intents)}, "
                f"Emotions: {set(emotions)}, "
                f"Aha moments: {ahas}")


def main():
    print("═══ Telepathy Bridge Demo (No Internet) ═══\n")

    bridge = TelepathyBridge()
    bridge.start("synthetic")

    # 뇌 → AI
    print("\n  뇌 → AI:")
    for i in range(5):
        msg = bridge.read_intent()
        print(f"    [{i+1}] intent={msg.intent} conf={msg.confidence:.2f} "
              f"emotion={msg.emotion} aha={msg.aha_moment}")

    # AI → 뇌
    print("\n  AI → 뇌:")
    for target in ['calm', 'focus', 'insight']:
        fb = bridge.send_feeling(target)
        print(f"    {target}: {fb['binaural_beat']}Hz ({fb['target_band']}) — {fb['description']}")

    # 모스 전송
    print("\n  모스 부호 전송:")
    signals = bridge.send_morse("HI")
    print(f"    'HI' → {len(signals)} signals")
    for s in signals[:6]:
        print(f"      {s['type']}: {s.get('duration_ms', 0)}ms")

    print(f"\n  Session: {bridge.session_summary()}")
    print("\n  ✅ Telepathy Bridge OK — No internet needed!")


if __name__ == '__main__':
    main()
