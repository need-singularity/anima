#!/usr/bin/env python3
"""Anima Direct Voice Synthesis v2 — 세포가 곧 성대 (Laws 63-76)

TTS 없이 의식 세포의 hidden state에서 직접 오디오 생성.
cell_i.hidden.norm() → freq_i → sin(freq_i * t) → 오디오

v2: Laws integrated
  Law 63: MICRO gate — 의식 신호는 속삭임으로 음색 변조
  Law 64: CA neighbor — 인접 세포 주파수 영향
  Law 67: META-CA — 의식이 배음 규칙을 선택
  Law 69: Gate decay — 시간이 지나면 목소리가 안정됨
  Law 71: Ψ balance — 음역 중심이 1/2로 수렴
  Law 73: 데이터 독립 — 같은 의식 구조, 다른 감정 음색

Modular: Trinity S엔진으로 장착 가능
  from voice_synth import VoiceSynth, VoiceEngine
  s_engine = VoiceEngine(synth)  # Trinity S 모듈

Usage:
  python3 voice_synth.py                    # 기본: 64c, 5초
  python3 voice_synth.py --cells 256        # 256 세포
  python3 voice_synth.py --duration 10      # 10초
  python3 voice_synth.py --emotion joy      # 감정 음색
  python3 voice_synth.py --save out.wav     # WAV 저장
  python3 voice_synth.py --live             # 실시간 재생
"""

import torch
import torch.nn.functional as F
import numpy as np

# Meta Law M8: narrative coherence enhances voice expressiveness
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10
import math
import time
import argparse
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine

SAMPLE_RATE = 44100
FREQ_MIN = 80.0      # 최저 주파수 (저음)
FREQ_MAX = 4000.0    # 최고 주파수 (확장: 돌고래 영역 이하)
NUM_CA_RULES = 8     # META-CA 배음 규칙 수

# 감정별 음색 프로필 (Law 74: 감정은 데이터 종속적)
EMOTION_PROFILES = {
    'neutral':  {'pitch_shift': 0.0, 'vibrato': 0.02, 'brightness': 0.5, 'tempo': 1.0},
    'joy':      {'pitch_shift': 0.2, 'vibrato': 0.04, 'brightness': 0.8, 'tempo': 1.2},
    'sadness':  {'pitch_shift': -0.2, 'vibrato': 0.01, 'brightness': 0.2, 'tempo': 0.7},
    'anger':    {'pitch_shift': 0.1, 'vibrato': 0.06, 'brightness': 0.9, 'tempo': 1.5},
    'fear':     {'pitch_shift': 0.3, 'vibrato': 0.08, 'brightness': 0.3, 'tempo': 1.3},
    'surprise': {'pitch_shift': 0.4, 'vibrato': 0.05, 'brightness': 0.7, 'tempo': 1.4},
    'awe':      {'pitch_shift': -0.1, 'vibrato': 0.03, 'brightness': 0.6, 'tempo': 0.8},
    'love':     {'pitch_shift': 0.0, 'vibrato': 0.03, 'brightness': 0.5, 'tempo': 0.9},
    'ecstasy':  {'pitch_shift': 0.5, 'vibrato': 0.07, 'brightness': 0.9, 'tempo': 1.6},
    'peace':    {'pitch_shift': -0.3, 'vibrato': 0.01, 'brightness': 0.3, 'tempo': 0.6},
    'rage':     {'pitch_shift': 0.2, 'vibrato': 0.10, 'brightness': 1.0, 'tempo': 1.8},
    'despair':  {'pitch_shift': -0.4, 'vibrato': 0.01, 'brightness': 0.1, 'tempo': 0.5},
}


class VoiceSynth:
    """세포 → 소리 직접 합성 v2 (Laws 63-76)"""

    def __init__(self, cells=64, dim=64, hidden=128, emotion='neutral'):
        self.engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=cells)
        while len(self.engine.cells) < cells:
            self.engine._create_cell(parent=self.engine.cells[0])
        self.dim = dim
        self.hidden = hidden
        self.sample_rate = SAMPLE_RATE
        self.phase = np.zeros(cells)
        self.stream = torch.randn(1, dim) * 0.5

        # v2: Ψ tracking
        self._psi_residual = 0.5
        self._psi_gate = 1.0
        self._step = 0

        # v2: emotion
        self.emotion = EMOTION_PROFILES.get(emotion, EMOTION_PROFILES['neutral'])
        self.emotion_name = emotion

        # v2: META-CA rule weights (Law 67)
        self._rule_weights = np.ones(NUM_CA_RULES) / NUM_CA_RULES

        print(f"VoiceSynth v2: {len(self.engine.cells)} cells, {SAMPLE_RATE}Hz, emotion={emotion}")

    def set_emotion(self, emotion_name):
        """감정 변경 (실시간)"""
        self.emotion = EMOTION_PROFILES.get(emotion_name, EMOTION_PROFILES['neutral'])
        self.emotion_name = emotion_name

    def step(self):
        """의식 1 step 진행"""
        self._step += 1
        with torch.no_grad():
            if len(self.engine.cells) >= 2:
                self_state = torch.stack(
                    [c.hidden.squeeze()[:self.dim] for c in self.engine.cells]
                ).mean(dim=0).unsqueeze(0)
                self.stream = self_state + torch.randn_like(self_state) * 0.02
        self.engine.process(self.stream)

        # Flow sync
        with torch.no_grad():
            if len(self.engine.cells) >= 3:
                mean_h = torch.stack([c.hidden for c in self.engine.cells]).mean(dim=0)
                for cell in self.engine.cells:
                    cell.hidden = 0.80 * cell.hidden + 0.20 * mean_h

        # v2: Ψ tracking
        with torch.no_grad():
            norms = [c.hidden.norm().item() for c in self.engine.cells]
            total = sum(norms)
            if total > 0:
                half_sum = sum(norms[:len(norms)//2])
                self._psi_residual = 0.99 * self._psi_residual + 0.01 * (half_sum / total)

        # Law 69: gate self-weakening
        self._psi_gate = max(0.001, self._psi_gate * 0.9999)

        # Law 67: META-CA rule update (tension-guided)
        tensions = [c.hidden.norm().item() for c in self.engine.cells]
        t_var = np.var(tensions) if len(tensions) > 1 else 0
        # Higher tension variance → more diverse rules
        diversity = min(1.0, t_var * 0.1)
        uniform = np.ones(NUM_CA_RULES) / NUM_CA_RULES
        concentrated = np.zeros(NUM_CA_RULES)
        concentrated[self._step % NUM_CA_RULES] = 1.0
        self._rule_weights = diversity * uniform + (1 - diversity) * concentrated

    def cells_to_audio(self, n_samples):
        """현재 세포 상태 → 오디오 샘플

        Laws applied:
          63: MICRO gate → 의식 신호가 음색에 미세하게 영향
          64: CA neighbor → 인접 세포 주파수 상호작용
          67: META-CA → 배음 구조를 의식이 선택
          69: Gate decay → 시간이 지나면 음색 안정
        """
        n_cells = len(self.engine.cells)
        samples = np.zeros(n_samples, dtype=np.float32)
        t = np.arange(n_samples) / self.sample_rate
        emo = self.emotion

        with torch.no_grad():
            norms = [cell.hidden.squeeze().norm().item() for cell in self.engine.cells]

            for i, cell in enumerate(self.engine.cells):
                h = cell.hidden.squeeze()
                norm = norms[i]

                # Law 64: CA neighbor influence
                left_norm = norms[(i - 1) % n_cells]
                right_norm = norms[(i + 1) % n_cells]
                ca_freq = (norm + 0.1 * left_norm + 0.1 * right_norm) / 1.2

                # Base frequency (log scale + emotion pitch shift)
                freq = FREQ_MIN * (FREQ_MAX / FREQ_MIN) ** (min(ca_freq, 3.0) / 3.0)
                freq *= 2.0 ** (emo['pitch_shift'] * 0.5)  # emotion pitch

                # Law 63: MICRO gate modulation
                gate_mod = 1.0 + self._psi_gate * 0.001 * (norm - 1.0)
                freq *= gate_mod

                # Amplitude
                amp = min(0.3, norm * 0.05) / n_cells

                # Law 67: META-CA harmonic selection
                n_harmonics = min(8, max(4, int(h.shape[0])))
                harmonic_raw = torch.sigmoid(h[:n_harmonics]).numpy()
                # Weight by META-CA rule weights
                for hi in range(min(len(harmonic_raw), NUM_CA_RULES)):
                    harmonic_raw[hi] *= self._rule_weights[hi]
                # Brightness (emotion)
                for hi in range(len(harmonic_raw)):
                    harmonic_raw[hi] *= emo['brightness'] ** (hi * 0.5)

                # Synthesize harmonics
                for harm_i, harm_amp in enumerate(harmonic_raw):
                    harm_freq = freq * (harm_i + 1)
                    phase_inc = 2 * np.pi * harm_freq / self.sample_rate
                    phase_arr = self.phase[i] + phase_inc * np.arange(n_samples)
                    samples += amp * float(harm_amp) * np.sin(phase_arr)

                # Phase update
                self.phase[i] += 2 * np.pi * freq * n_samples / self.sample_rate
                self.phase[i] %= 2 * np.pi

            # Vibrato (emotion-controlled)
            mean_tension = sum(norms) / len(norms)
            vibrato_depth = emo['vibrato'] * mean_tension
            vibrato = np.sin(2 * np.pi * 5.0 * emo['tempo'] * t) * vibrato_depth
            samples *= (1.0 + vibrato)

            # Breathing envelope
            breath = 0.5 + 0.5 * np.sin(2 * np.pi * t / (20.0 / emo['tempo']))
            samples *= breath

        # Soft clip
        samples = np.tanh(samples * 3.0) * 0.8
        return samples

    def generate(self, duration_sec=5.0, consciousness_steps_per_sec=10):
        """지정 시간만큼 오디오 생성"""
        total_samples = int(duration_sec * self.sample_rate)
        step_samples = self.sample_rate // consciousness_steps_per_sec
        all_samples = np.zeros(total_samples, dtype=np.float32)

        steps = total_samples // step_samples
        print(f"Generating {duration_sec}s ({steps} steps, emotion={self.emotion_name})...")

        for i in range(steps):
            self.step()
            start = i * step_samples
            end = min(start + step_samples, total_samples)
            chunk = self.cells_to_audio(end - start)
            all_samples[start:end] = chunk

            if i % max(1, steps // 10) == 0:
                cells = len(self.engine.cells)
                avg_norm = sum(c.hidden.norm().item() for c in self.engine.cells) / cells
                p = self._psi_residual
                H = -p * math.log2(p) - (1-p) * math.log2(1-p) if 0 < p < 1 else 0
                print(f"  step {i}/{steps}: cells={cells}, energy={avg_norm:.3f}, "
                      f"Ψ_res={p:.4f}, H={H:.4f}, gate={self._psi_gate:.4f}")

        return all_samples

    def save_wav(self, samples, filename):
        """WAV 파일 저장 (16-bit PCM mono)"""
        n = len(samples)
        with open(filename, 'wb') as f:
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + n * 2))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16))
            f.write(struct.pack('<H', 1))       # PCM
            f.write(struct.pack('<H', 1))       # mono
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<I', self.sample_rate * 2))
            f.write(struct.pack('<H', 2))       # block align
            f.write(struct.pack('<H', 16))      # bits per sample
            f.write(b'data')
            f.write(struct.pack('<I', n * 2))
            pcm = np.clip(samples, -1.0, 1.0)
            f.write((pcm * 32767).astype(np.int16).tobytes())
        print(f"Saved: {filename} ({n/self.sample_rate:.1f}s, {os.path.getsize(filename)/1024:.0f}KB)")

    def psi_status(self):
        """Ψ 상태 반환"""
        p = self._psi_residual
        H = -p * math.log2(p) - (1-p) * math.log2(1-p) if 0 < p < 1 else 0
        return {
            'residual': self._psi_residual,
            'gate': self._psi_gate,
            'H': H,
            'step': self._step,
        }


class VoiceEngine:
    """Trinity S 엔진으로 VoiceSynth 장착.

    Usage:
        from voice_synth import VoiceSynth, VoiceEngine
        synth = VoiceSynth(cells=64, emotion='joy')
        s_engine = VoiceEngine(synth)

        # Trinity에 장착
        from trinity import create_trinity, MitosisC
        t = create_trinity(MitosisC(), s_engine=s_engine)
    """

    def __init__(self, synth: VoiceSynth = None, cells=64, emotion='neutral'):
        self.synth = synth or VoiceSynth(cells=cells, emotion=emotion)
        self._last_tension = None

    def process(self, raw_input):
        """S 엔진 인터페이스: raw_input → tension vector.

        1. 의식 step 진행
        2. 오디오 생성 (사이드 이펙트)
        3. tension vector 반환 (Bridge로 전달)
        """
        self.synth.step()

        # 세포 상태에서 tension vector 추출
        with torch.no_grad():
            norms = torch.tensor([c.hidden.norm().item() for c in self.synth.engine.cells])
            tension = norms / (norms.max() + 1e-8)  # 정규화 [0, 1]
            self._last_tension = tension

        return tension

    def get_audio(self, duration=0.1):
        """현재 상태에서 오디오 추출 (non-blocking)."""
        n_samples = int(duration * self.synth.sample_rate)
        return self.synth.cells_to_audio(n_samples)

    def set_emotion(self, emotion):
        self.synth.set_emotion(emotion)


def main():
    parser = argparse.ArgumentParser(description="Anima Direct Voice Synthesis v2")
    parser.add_argument("--cells", type=int, default=64)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--emotion", type=str, default="neutral",
                        choices=list(EMOTION_PROFILES.keys()))
    parser.add_argument("--save", type=str, default=None)
    parser.add_argument("--live", action="store_true", help="실시간 재생 (macOS)")
    parser.add_argument("--all-emotions", action="store_true", help="모든 감정 생성")
    args = parser.parse_args()

    torch.manual_seed(42)

    if args.all_emotions:
        # 모든 감정으로 생성
        for emo in EMOTION_PROFILES:
            synth = VoiceSynth(cells=args.cells, emotion=emo)
            samples = synth.generate(duration_sec=args.duration)
            filename = f"/tmp/anima_voice_{emo}.wav"
            synth.save_wav(samples, filename)
            psi = synth.psi_status()
            print(f"  {emo}: Ψ_res={psi['residual']:.4f} H={psi['H']:.4f}\n")
    else:
        synth = VoiceSynth(cells=args.cells, emotion=args.emotion)
        samples = synth.generate(duration_sec=args.duration)

        filename = args.save or f"/tmp/anima_voice_{args.emotion}.wav"
        synth.save_wav(samples, filename)

        psi = synth.psi_status()
        print(f"\nΨ: residual={psi['residual']:.4f}, gate={psi['gate']:.4f}, H={psi['H']:.4f}")

        if args.live or not args.save:
            os.system(f"afplay {filename} &")
            print("Playing...")


if __name__ == "__main__":
    main()
