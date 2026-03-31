#!/usr/bin/env python3
"""Emotion-EEG Synchronization — FAA 기반 감정-의식 동기화.

Frontal Alpha Asymmetry (FAA) 를 Anima 감정 시스템(VAD)에 매핑.
양방향: EEG -> Anima 감정 AND Anima 감정 -> 뉴로피드백.

FAA = ln(right_alpha/F4) - ln(left_alpha/F3)
  FAA > 0: approach motivation -> positive valence
  FAA < 0: withdrawal motivation -> negative valence

Protocol:
  Phase 1 (1min): Baseline FAA calibration
  Phase 2 (2min): Emotion induction (stimuli with known valence)
  Phase 3 (2min): FAA -> Anima emotion correlation measurement
  Phase 4 (2min): Real-time sync (bidirectional)

Usage:
  python anima-eeg/protocols/emotion_sync.py --demo
  python anima-eeg/protocols/emotion_sync.py --demo --duration 30

Integration:
  from protocols.emotion_sync import EmotionSync
  es = EmotionSync(mind=mind, eeg_bridge=bridge)
  await es.run()
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np

# Add anima src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'anima', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    import path_setup  # noqa
except ImportError:
    pass

try:
    from consciousness_laws import PSI
except ImportError:
    PSI = {'alpha': 0.014, 'balance': 0.5}

# EEG channel indices (10-20 system)
# F3 = left frontal, F4 = right frontal
F3_LABEL = "F3"
F4_LABEL = "F4"

SAMPLE_HZ = 4.0
BASELINE_DURATION = 60.0
INDUCTION_DURATION = 120.0
CORRELATION_DURATION = 120.0
SYNC_DURATION = 120.0

# Emotion induction stimuli (valence: -1 to +1)
EMOTION_STIMULI = [
    {"name": "calm_nature", "valence": 0.7, "arousal": 0.2, "duration": 15},
    {"name": "upbeat_music", "valence": 0.9, "arousal": 0.7, "duration": 15},
    {"name": "sad_melody", "valence": -0.5, "arousal": 0.3, "duration": 15},
    {"name": "tense_scene", "valence": -0.3, "arousal": 0.8, "duration": 15},
    {"name": "funny_clip", "valence": 0.8, "arousal": 0.6, "duration": 15},
    {"name": "scary_sound", "valence": -0.7, "arousal": 0.9, "duration": 15},
    {"name": "peaceful_silence", "valence": 0.4, "arousal": 0.1, "duration": 15},
    {"name": "exciting_beat", "valence": 0.6, "arousal": 0.9, "duration": 15},
]


@dataclass
class FAASample:
    """FAA 측정 샘플."""
    timestamp: float = 0.0
    faa: float = 0.0              # ln(right_alpha) - ln(left_alpha)
    beta_asymmetry: float = 0.0   # arousal proxy
    valence: float = 0.0          # mapped from FAA
    arousal: float = 0.0          # mapped from beta asymmetry
    dominance: float = 0.5        # default
    # Anima emotion state (if available)
    anima_valence: float = 0.0
    anima_arousal: float = 0.0
    anima_dominance: float = 0.5
    stimulus: str = ""


@dataclass
class FABaseline:
    """FAA 기준선."""
    faa_mean: float = 0.0
    faa_std: float = 0.1
    beta_asym_mean: float = 0.0
    beta_asym_std: float = 0.1
    n_samples: int = 0


@dataclass
class EmotionCorrelation:
    """감정 상관 분석 결과."""
    valence_correlation: float = 0.0    # FAA valence vs Anima valence
    arousal_correlation: float = 0.0    # beta asymmetry vs Anima arousal
    faa_stimulus_correlation: float = 0.0  # FAA vs stimulus valence
    sync_accuracy: float = 0.0         # % time FAA sign matches Anima valence sign
    mean_latency_ms: float = 0.0       # brain->engine latency


class EmotionSync:
    """FAA 감정-의식 동기화 모듈.

    EEG Frontal Alpha Asymmetry를 Anima 감정 시스템(VAD)에
    양방향 매핑.
    """

    def __init__(self, mind=None, eeg_bridge=None, websocket=None):
        """
        Args:
            mind: ConsciousMind 인스턴스
            eeg_bridge: EEGBridge 인스턴스
            websocket: WebSocket 연결 (뉴로피드백 전송용)
        """
        self.mind = mind
        self.eeg_bridge = eeg_bridge
        self.websocket = websocket
        self._simulation = (eeg_bridge is None)
        self._running = False

        self.baseline = FABaseline()
        self.samples = []  # all FAASample records
        self.phase_data = {}

    # ─── EEG reading ───

    def _get_frontal_alpha(self) -> tuple:
        """좌/우 전두엽 알파 파워 취득.

        Returns:
            (left_alpha_F3, right_alpha_F4)
        """
        if self.eeg_bridge is not None:
            state = self.eeg_bridge.get_state()
            # If bridge has channel-specific data
            alpha = state.alpha_power
            # Approximate L/R from global alpha + noise
            # Real implementation would use F3/F4 channels directly
            left = alpha * (1.0 + np.random.normal(0, 0.1))
            right = alpha * (1.0 + np.random.normal(0, 0.1))
            return max(left, 0.01), max(right, 0.01)

        # Simulation
        base = 10.0 + np.random.normal(0, 1)
        left = max(0.01, base + np.random.normal(0, 2))
        right = max(0.01, base + np.random.normal(0, 2))
        return left, right

    def _get_frontal_beta(self) -> tuple:
        """좌/우 전두엽 베타 파워 취득.

        Returns:
            (left_beta, right_beta)
        """
        if self.eeg_bridge is not None:
            state = self.eeg_bridge.get_state()
            beta = state.beta_power
            left = beta * (1.0 + np.random.normal(0, 0.1))
            right = beta * (1.0 + np.random.normal(0, 0.1))
            return max(left, 0.01), max(right, 0.01)

        base = 5.0 + np.random.normal(0, 0.5)
        left = max(0.01, base + np.random.normal(0, 1))
        right = max(0.01, base + np.random.normal(0, 1))
        return left, right

    def _compute_faa(self) -> tuple:
        """FAA 및 beta asymmetry 계산.

        Returns:
            (faa, beta_asymmetry)
        """
        left_alpha, right_alpha = self._get_frontal_alpha()
        left_beta, right_beta = self._get_frontal_beta()

        faa = np.log(right_alpha) - np.log(left_alpha)
        beta_asym = right_beta - left_beta

        return float(faa), float(beta_asym)

    def _faa_to_valence(self, faa: float) -> float:
        """FAA를 감정 valence (-1 to +1)로 변환."""
        # Normalize by baseline
        if self.baseline.faa_std > 0:
            z = (faa - self.baseline.faa_mean) / self.baseline.faa_std
        else:
            z = faa
        return float(np.tanh(z * 0.5))  # smooth mapping to [-1, 1]

    def _beta_to_arousal(self, beta_asym: float) -> float:
        """Beta asymmetry를 arousal (0 to 1)로 변환."""
        if self.baseline.beta_asym_std > 0:
            z = abs(beta_asym - self.baseline.beta_asym_mean) / self.baseline.beta_asym_std
        else:
            z = abs(beta_asym)
        return float(np.clip(z * 0.3, 0, 1))

    def _get_anima_emotion(self) -> tuple:
        """Anima 감정 상태 취득 (valence, arousal, dominance)."""
        if self.mind:
            try:
                if hasattr(self.mind, 'emotion'):
                    e = self.mind.emotion
                    if hasattr(e, 'valence'):
                        return (float(e.valence), float(e.arousal),
                                float(getattr(e, 'dominance', 0.5)))
                if hasattr(self.mind, 'prev_tension'):
                    t = float(self.mind.prev_tension)
                    return (1.0 - 2 * t, t, 0.5)  # rough mapping
            except Exception:
                pass
        return (np.random.normal(0, 0.3), abs(np.random.normal(0.5, 0.2)), 0.5)

    def _set_anima_emotion(self, valence: float, arousal: float, dominance: float = 0.5):
        """Anima 감정 상태 설정 (EEG -> Anima 방향)."""
        if self.mind:
            try:
                if hasattr(self.mind, 'emotion'):
                    self.mind.emotion.valence = valence
                    self.mind.emotion.arousal = arousal
                    if hasattr(self.mind.emotion, 'dominance'):
                        self.mind.emotion.dominance = dominance
            except Exception:
                pass

    # ─── Calibration ───

    async def calibrate(self, duration: float = BASELINE_DURATION):
        """기준선 FAA 교정 (1분 eyes-open resting).

        Args:
            duration: 교정 시간 (초)
        """
        print(f"  [emotion] Calibrating FAA baseline ({duration:.0f}s)...")
        faa_samples = []
        beta_samples = []
        interval = 1.0 / SAMPLE_HZ
        t0 = time.time()

        while time.time() - t0 < duration:
            faa, beta_asym = self._compute_faa()
            faa_samples.append(faa)
            beta_samples.append(beta_asym)
            await asyncio.sleep(interval)

        self.baseline = FABaseline(
            faa_mean=float(np.mean(faa_samples)),
            faa_std=float(np.std(faa_samples)) if len(faa_samples) > 1 else 0.1,
            beta_asym_mean=float(np.mean(beta_samples)),
            beta_asym_std=float(np.std(beta_samples)) if len(beta_samples) > 1 else 0.1,
            n_samples=len(faa_samples),
        )
        print(f"  [emotion] Baseline: FAA={self.baseline.faa_mean:.4f}+/-{self.baseline.faa_std:.4f}, "
              f"beta_asym={self.baseline.beta_asym_mean:.4f}+/-{self.baseline.beta_asym_std:.4f}")

    # ─── Protocol phases ───

    async def _run_induction(self, duration: float = INDUCTION_DURATION):
        """Phase 2: 감정 유도 — 알려진 valence 자극 제시.

        Args:
            duration: 총 유도 시간 (초)
        """
        print(f"\n  Phase 2: Emotion Induction ({duration:.0f}s)")
        phase_samples = []
        interval = 1.0 / SAMPLE_HZ
        t0 = time.time()
        stim_idx = 0

        while time.time() - t0 < duration and self._running:
            # Current stimulus
            stim = EMOTION_STIMULI[stim_idx % len(EMOTION_STIMULI)]
            stim_elapsed = (time.time() - t0) % stim["duration"]
            if stim_elapsed < interval * 1.5:
                stim_idx = int((time.time() - t0) / stim["duration"]) % len(EMOTION_STIMULI)
                stim = EMOTION_STIMULI[stim_idx]
                print(f"    Stimulus: {stim['name']} (valence={stim['valence']:+.1f}, "
                      f"arousal={stim['arousal']:.1f})")

            faa, beta_asym = self._compute_faa()

            # In simulation, bias FAA toward stimulus valence
            if self._simulation:
                faa += stim["valence"] * 0.3 + np.random.normal(0, 0.1)

            valence = self._faa_to_valence(faa)
            arousal = self._beta_to_arousal(beta_asym)
            a_val, a_aro, a_dom = self._get_anima_emotion()

            sample = FAASample(
                timestamp=time.time() - t0,
                faa=faa,
                beta_asymmetry=beta_asym,
                valence=valence,
                arousal=arousal,
                anima_valence=a_val,
                anima_arousal=a_aro,
                anima_dominance=a_dom,
                stimulus=stim["name"],
            )
            phase_samples.append(sample)
            self.samples.append(sample)

            await asyncio.sleep(interval)

        self.phase_data["induction"] = phase_samples
        return phase_samples

    async def _run_correlation(self, duration: float = CORRELATION_DURATION):
        """Phase 3: FAA-Anima 상관 측정.

        Args:
            duration: 측정 시간 (초)
        """
        print(f"\n  Phase 3: FAA-Anima Correlation ({duration:.0f}s)")
        phase_samples = []
        interval = 1.0 / SAMPLE_HZ
        t0 = time.time()

        while time.time() - t0 < duration and self._running:
            faa, beta_asym = self._compute_faa()
            valence = self._faa_to_valence(faa)
            arousal = self._beta_to_arousal(beta_asym)
            a_val, a_aro, a_dom = self._get_anima_emotion()

            sample = FAASample(
                timestamp=time.time() - t0,
                faa=faa,
                beta_asymmetry=beta_asym,
                valence=valence,
                arousal=arousal,
                anima_valence=a_val,
                anima_arousal=a_aro,
                anima_dominance=a_dom,
            )
            phase_samples.append(sample)
            self.samples.append(sample)

            # Print every 5s
            elapsed = time.time() - t0
            if int(elapsed * SAMPLE_HZ) % int(5 * SAMPLE_HZ) == 0:
                print(f"    [{elapsed:5.1f}s] FAA={faa:+.4f} -> valence={valence:+.3f} "
                      f"| Anima valence={a_val:+.3f}")

            await asyncio.sleep(interval)

        self.phase_data["correlation"] = phase_samples
        return phase_samples

    async def _run_sync(self, duration: float = SYNC_DURATION):
        """Phase 4: 양방향 실시간 동기화.

        EEG FAA -> Anima emotion (forward)
        Anima emotion -> neurofeedback (backward)

        Args:
            duration: 동기화 시간 (초)
        """
        print(f"\n  Phase 4: Bidirectional Sync ({duration:.0f}s)")
        phase_samples = []
        interval = 1.0 / SAMPLE_HZ
        t0 = time.time()

        while time.time() - t0 < duration and self._running:
            faa, beta_asym = self._compute_faa()
            valence = self._faa_to_valence(faa)
            arousal = self._beta_to_arousal(beta_asym)

            # Forward: EEG -> Anima emotion
            self._set_anima_emotion(valence, arousal)

            # Read back Anima state
            a_val, a_aro, a_dom = self._get_anima_emotion()

            sample = FAASample(
                timestamp=time.time() - t0,
                faa=faa,
                beta_asymmetry=beta_asym,
                valence=valence,
                arousal=arousal,
                anima_valence=a_val,
                anima_arousal=a_aro,
                anima_dominance=a_dom,
            )
            phase_samples.append(sample)
            self.samples.append(sample)

            # Backward: Anima -> neurofeedback via WebSocket
            if self.websocket:
                try:
                    await self.websocket.send(json.dumps({
                        "type": "emotion_neurofeedback",
                        "valence": a_val,
                        "arousal": a_aro,
                        "dominance": a_dom,
                        "faa": faa,
                        "target_state": "approach" if a_val > 0 else "withdrawal",
                    }))
                except Exception:
                    pass

            # Print every 5s
            elapsed = time.time() - t0
            if int(elapsed * SAMPLE_HZ) % int(5 * SAMPLE_HZ) == 0:
                direction = "+" if valence > 0 else "-"
                print(f"    [{elapsed:5.1f}s] FAA={faa:+.4f} -> V={valence:+.3f} A={arousal:.3f} "
                      f"| Anima V={a_val:+.3f} A={a_aro:.3f} [{direction}]")

            await asyncio.sleep(interval)

        self.phase_data["sync"] = phase_samples
        return phase_samples

    # ─── Main protocol ───

    async def run(self, baseline_s: float = BASELINE_DURATION,
                  induction_s: float = INDUCTION_DURATION,
                  correlation_s: float = CORRELATION_DURATION,
                  sync_s: float = SYNC_DURATION):
        """전체 프로토콜 실행.

        Args:
            baseline_s: 기준선 시간
            induction_s: 감정 유도 시간
            correlation_s: 상관 측정 시간
            sync_s: 양방향 동기화 시간
        """
        print(f"\n{'='*60}")
        print(f"  Emotion-EEG Synchronization Protocol")
        print(f"  Simulation: {self._simulation}")
        print(f"{'='*60}")

        self._running = True
        self.samples = []
        self.phase_data = {}

        # Phase 1: Baseline
        print("\nPhase 1: Baseline FAA Calibration")
        await self.calibrate(duration=baseline_s)

        if not self._running:
            return None

        # Phase 2: Emotion induction
        await self._run_induction(duration=induction_s)

        if not self._running:
            return None

        # Phase 3: Correlation measurement
        await self._run_correlation(duration=correlation_s)

        if not self._running:
            return None

        # Phase 4: Bidirectional sync
        await self._run_sync(duration=sync_s)

        self._running = False

        # Analyze
        results = self.analyze()
        self._print_results(results)
        return results

    def cancel(self):
        """실행 취소."""
        self._running = False

    # ─── Analysis ───

    def analyze(self) -> EmotionCorrelation:
        """감정 동기화 분석."""
        results = EmotionCorrelation()
        if not self.samples:
            return results

        faa_vals = np.array([s.valence for s in self.samples])
        anima_vals = np.array([s.anima_valence for s in self.samples])
        faa_aro = np.array([s.arousal for s in self.samples])
        anima_aro = np.array([s.anima_arousal for s in self.samples])

        # Valence correlation
        if len(faa_vals) > 5:
            r = np.corrcoef(faa_vals, anima_vals)[0, 1]
            results.valence_correlation = float(r) if not np.isnan(r) else 0.0

        # Arousal correlation
        if len(faa_aro) > 5:
            r = np.corrcoef(faa_aro, anima_aro)[0, 1]
            results.arousal_correlation = float(r) if not np.isnan(r) else 0.0

        # FAA vs stimulus valence (induction phase only)
        induction = self.phase_data.get("induction", [])
        if induction:
            stim_valences = []
            faa_valences = []
            for s in induction:
                for stim in EMOTION_STIMULI:
                    if stim["name"] == s.stimulus:
                        stim_valences.append(stim["valence"])
                        faa_valences.append(s.valence)
                        break
            if len(stim_valences) > 5:
                r = np.corrcoef(stim_valences, faa_valences)[0, 1]
                results.faa_stimulus_correlation = float(r) if not np.isnan(r) else 0.0

        # Sign match accuracy
        sign_matches = sum(1 for v, a in zip(faa_vals, anima_vals)
                           if (v > 0) == (a > 0))
        results.sync_accuracy = sign_matches / max(len(faa_vals), 1)

        return results

    def _print_results(self, results: EmotionCorrelation):
        """결과 출력."""
        print(f"\n{'='*60}")
        print(f"  Emotion-EEG Sync Results")
        print(f"{'='*60}")
        print(f"  Valence correlation (FAA vs Anima):     {results.valence_correlation:+.4f}")
        print(f"  Arousal correlation (beta vs Anima):     {results.arousal_correlation:+.4f}")
        print(f"  FAA-Stimulus correlation:                {results.faa_stimulus_correlation:+.4f}")
        print(f"  Sign match accuracy:                     {results.sync_accuracy:.1%}")
        print(f"  Total samples:                           {len(self.samples)}")
        print()

        # Valence timeline (ASCII)
        if self.samples:
            n = min(len(self.samples), 60)
            step = max(1, len(self.samples) // n)
            sub = self.samples[::step][:n]

            print("  Valence Timeline (FAA=# Anima=.):")
            rows = 5
            for r in range(rows):
                threshold = 1.0 - r * 0.5  # 1.0, 0.5, 0.0, -0.5, -1.0
                line = ""
                for s in sub:
                    if abs(s.valence - threshold) < 0.25:
                        line += "#"
                    elif abs(s.anima_valence - threshold) < 0.25:
                        line += "."
                    else:
                        line += " "
                label = f"{threshold:+.1f}" if r in (0, 2, 4) else "    "
                print(f"  {label} |{line}|")
            print(f"       +{'-' * len(sub)}+")
            print(f"        time ->")
            print()


# ─── Standalone demo ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Emotion-EEG Sync Protocol")
    parser.add_argument("--demo", action="store_true", help="Run simulation demo")
    parser.add_argument("--duration", type=float, default=15.0, help="Per-phase duration (seconds)")
    args = parser.parse_args()

    if not args.demo:
        print("Use --demo for standalone test")
        print("Integration: EmotionSync(mind, eeg_bridge)")
        return

    print("=" * 60)
    print("  Emotion-EEG Synchronization (Simulation Demo)")
    print("=" * 60)

    es = EmotionSync()

    # Make simulation produce correlated valence patterns
    sim_time = [0]
    original_get_frontal = es._get_frontal_alpha

    def sim_frontal_alpha():
        t = sim_time[0]
        sim_time[0] += 1
        # Slow oscillation between positive and negative FAA
        cycle = t / (SAMPLE_HZ * 8)  # 8s cycles
        bias = np.sin(cycle * np.pi) * 3.0
        left = max(0.01, 10.0 + np.random.normal(0, 1) - bias * 0.5)
        right = max(0.01, 10.0 + np.random.normal(0, 1) + bias * 0.5)
        return left, right

    es._get_frontal_alpha = sim_frontal_alpha

    asyncio.run(es.run(
        baseline_s=args.duration,
        induction_s=args.duration,
        correlation_s=args.duration,
        sync_s=args.duration,
    ))


if __name__ == "__main__":
    main()
