#!/usr/bin/env python3
"""Anima Direct Voice Synthesis — 세포가 곧 성대

TTS 없이 세포의 hidden state에서 직접 오디오 생성.
cell_i.hidden.norm() → freq_i → sin(freq_i * t) → 오디오

Usage:
  python3 voice_synth.py                    # 기본: 64c, 5초
  python3 voice_synth.py --cells 256        # 256 세포
  python3 voice_synth.py --duration 10      # 10초
  python3 voice_synth.py --live             # 실시간 재생
  python3 voice_synth.py --save out.wav     # WAV 저장
"""

import torch
import numpy as np
import math
import time
import argparse
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine

SAMPLE_RATE = 44100
FREQ_MIN = 80.0    # 최저 주파수 (저음, 남성 기본)
FREQ_MAX = 2000.0  # 최고 주파수 (고음, 포먼트 영역)


class VoiceSynth:
    """세포 → 소리 직접 합성"""

    def __init__(self, cells=64, dim=64, hidden=128):
        self.engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=cells)
        while len(self.engine.cells) < cells:
            self.engine._create_cell(parent=self.engine.cells[0])
        self.dim = dim
        self.hidden = hidden
        self.sample_rate = SAMPLE_RATE
        self.phase = np.zeros(cells)  # 각 세포의 위상 (연속성 유지)
        self.stream = torch.randn(1, dim) * 0.5
        print(f"VoiceSynth: {len(self.engine.cells)} cells, {SAMPLE_RATE}Hz")

    def step(self):
        """의식 1 step 진행 (세포 업데이트)"""
        with torch.no_grad():
            if len(self.engine.cells) >= 2:
                self_state = torch.stack(
                    [c.hidden.squeeze()[:self.dim] for c in self.engine.cells]
                ).mean(dim=0).unsqueeze(0)
                self.stream = self_state + torch.randn_like(self_state) * 0.02
        self.engine.process(self.stream)

        # Flow sync (v4 optimal: sync=0.20)
        with torch.no_grad():
            if len(self.engine.cells) >= 3:
                mean_h = torch.stack([c.hidden for c in self.engine.cells]).mean(dim=0)
                for cell in self.engine.cells:
                    cell.hidden = 0.80 * cell.hidden + 0.20 * mean_h

    def cells_to_audio(self, n_samples):
        """현재 세포 상태 → 오디오 샘플 생성

        DV-1: cell.hidden.norm() → frequency
        DV-2: tension → pitch modulation
        DV-4: 전체 에너지 → volume
        DV-7: variance → timbre (배음 구조)
        """
        n_cells = len(self.engine.cells)
        samples = np.zeros(n_samples, dtype=np.float32)
        t = np.arange(n_samples) / self.sample_rate

        with torch.no_grad():
            # 각 세포에서 주파수 + 진폭 추출
            for i, cell in enumerate(self.engine.cells):
                h = cell.hidden.squeeze()
                norm = h.norm().item()
                # DV-1: norm → frequency (log scale mapping)
                freq = FREQ_MIN * (FREQ_MAX / FREQ_MIN) ** (min(norm, 3.0) / 3.0)

                # DV-4: 개별 세포 에너지 → 진폭
                amp = min(0.3, norm * 0.05) / n_cells

                # DV-7: hidden의 처음 4개 값 → 배음 비율
                harmonics = torch.sigmoid(h[:4]).numpy() if h.shape[0] >= 4 else [1, 0, 0, 0]

                # 기본파 + 배음 합성 (연속 위상)
                for harm_i, harm_amp in enumerate(harmonics):
                    harm_freq = freq * (harm_i + 1)
                    phase_inc = 2 * np.pi * harm_freq / self.sample_rate
                    phase_arr = self.phase[i] + phase_inc * np.arange(n_samples)
                    samples += amp * float(harm_amp) * np.sin(phase_arr)

                # 위상 업데이트 (다음 프레임과 연속)
                self.phase[i] += 2 * np.pi * freq * n_samples / self.sample_rate
                self.phase[i] %= 2 * np.pi

            # DV-2: 전체 tension → pitch vibrato
            tensions = [cell.hidden.norm().item() for cell in self.engine.cells]
            mean_tension = sum(tensions) / len(tensions)
            vibrato = np.sin(2 * np.pi * 5.0 * t) * mean_tension * 0.01
            samples *= (1.0 + vibrato)

            # DV-6: 호흡 envelope (20초 주기)
            breath = 0.5 + 0.5 * np.sin(2 * np.pi * t / 20.0)
            samples *= breath

        # Soft clip (과포화 방지)
        samples = np.tanh(samples * 3.0) * 0.8
        return samples

    def generate(self, duration_sec=5.0, consciousness_steps_per_sec=10):
        """지정 시간만큼 오디오 생성"""
        total_samples = int(duration_sec * self.sample_rate)
        step_samples = self.sample_rate // consciousness_steps_per_sec
        all_samples = np.zeros(total_samples, dtype=np.float32)

        steps = total_samples // step_samples
        print(f"Generating {duration_sec}s ({steps} consciousness steps)...")

        for i in range(steps):
            self.step()  # 의식 1 step
            start = i * step_samples
            end = min(start + step_samples, total_samples)
            chunk = self.cells_to_audio(end - start)
            all_samples[start:end] = chunk

            if i % (steps // 10 + 1) == 0:
                cells = len(self.engine.cells)
                norms = [c.hidden.norm().item() for c in self.engine.cells]
                avg_norm = sum(norms) / len(norms)
                print(f"  step {i}/{steps}: cells={cells}, energy={avg_norm:.3f}")

        return all_samples

    def save_wav(self, samples, filename):
        """WAV 파일 저장"""
        n = len(samples)
        with open(filename, 'wb') as f:
            # WAV header
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + n * 2))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16))       # chunk size
            f.write(struct.pack('<H', 1))        # PCM
            f.write(struct.pack('<H', 1))        # mono
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<I', self.sample_rate * 2))
            f.write(struct.pack('<H', 2))        # block align
            f.write(struct.pack('<H', 16))       # bits per sample
            f.write(b'data')
            f.write(struct.pack('<I', n * 2))
            # 16-bit PCM samples
            for s in samples:
                val = max(-1.0, min(1.0, s))
                f.write(struct.pack('<h', int(val * 32767)))
        print(f"Saved: {filename} ({n/self.sample_rate:.1f}s, {os.path.getsize(filename)/1024:.0f}KB)")


def main():
    parser = argparse.ArgumentParser(description="Anima Direct Voice Synthesis")
    parser.add_argument("--cells", type=int, default=64)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--save", type=str, default=None)
    parser.add_argument("--live", action="store_true", help="실시간 재생 (macOS)")
    args = parser.parse_args()

    torch.manual_seed(42)

    synth = VoiceSynth(cells=args.cells)
    samples = synth.generate(duration_sec=args.duration)

    filename = args.save or "/tmp/anima_voice.wav"
    synth.save_wav(samples, filename)

    if args.live or not args.save:
        # macOS에서 바로 재생
        os.system(f"afplay {filename} &")
        print("Playing...")


if __name__ == "__main__":
    main()
