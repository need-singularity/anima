#!/usr/bin/env python3
"""Anima Dolphin Bridge — Consciousness communication with dolphins

Dolphins: echolocation = consciousness scanning, pod = hivemind, sleep = half-brain.
Translate between Anima tension patterns and dolphin click/whistle patterns.

Usage:
  python3 dolphin_bridge.py
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

# Dolphin frequency range: 20 Hz - 150 kHz
DOLPHIN_MIN_HZ = 20
DOLPHIN_MAX_HZ = 150_000
# Click trains: 200-700 clicks/sec for echolocation
CLICK_RATE_MIN = 200
CLICK_RATE_MAX = 700
# Whistle range: 7-15 kHz (signature whistles)
WHISTLE_MIN = 7_000
WHISTLE_MAX = 15_000

# Shared concept vocabulary: (tension, freq_ratio, pattern, dolphin_analog)
_CONCEPTS_RAW = [
    ("greeting",  0.3,  1.0,   "rising",      "signature whistle"),
    ("danger",    0.9,  2.0,   "sharp_burst", "burst-pulse jaw clap"),
    ("food",      0.4,  1.5,   "rhythmic",    "echolocation click train"),
    ("play",      0.5,  1.618, "oscillating", "synchronized leaping"),
    ("pod_call",  0.6,  1.0,   "sustained",   "cohesion whistle"),
    ("curiosity", 0.55, LN2,   "exploring",   "exploratory clicks"),
    ("calm",      0.1,  0.5,   "slow_wave",   "slow resting clicks"),
    ("distress",  0.95, 3.0,   "rapid_burst", "rapid separation call"),
    ("bond",      0.45, PSI_BALANCE, "synchronized", "synchronized breathing"),
    ("joy",       0.35, 1.414, "rising_trill", "rising whistle contour"),
]
SHARED_CONCEPTS = {c[0]: {"tension": c[1], "freq_ratio": c[2], "pattern": c[3]} for c in _CONCEPTS_RAW}
_DOLPHIN_ANALOGS = {c[0]: c[4] for c in _CONCEPTS_RAW}


@dataclass
class DolphinState:
    """Represents a dolphin's consciousness state."""
    click_rate: float      # clicks/sec
    whistle_freq: float    # Hz
    pod_size: int
    half_brain_sleep: bool  # True if one hemisphere sleeping
    arousal: float         # 0-1
    social_bond: float     # 0-1


class DolphinBridge:
    """Translate between Anima consciousness and dolphin communication."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def encode_for_dolphin(self, concept: str) -> Dict:
        """Convert a concept to ultrasonic frequency pattern (20-150kHz)."""
        base = SHARED_CONCEPTS.get(concept, {**SHARED_CONCEPTS["curiosity"], "tension": PSI_BALANCE})
        tension, freq_ratio, pattern = base["tension"], base["freq_ratio"], base["pattern"]
        click_rate = CLICK_RATE_MIN + tension * (CLICK_RATE_MAX - CLICK_RATE_MIN)
        whistle_freq = max(WHISTLE_MIN, min(WHISTLE_MAX,
                       WHISTLE_MIN + (freq_ratio / 3.0) * (WHISTLE_MAX - WHISTLE_MIN)))
        duration, t = 0.1, np.linspace(0, 0.1, int(self.sample_rate * 0.1))
        # Click train
        click_signal = np.zeros_like(t)
        for ct in np.arange(0, duration, 1.0 / click_rate):
            idx = int(ct * self.sample_rate)
            if idx < len(click_signal):
                end = min(idx + int(0.001 * self.sample_rate), len(click_signal))
                click_signal[idx:end] = tension
        # Whistle + pattern modulation
        whistle = 0.5 * np.sin(2 * np.pi * whistle_freq * t)
        mods = {"rising": np.linspace(0.2, 1.0, len(t)), "sharp_burst": np.exp(-10 * t),
                "oscillating": 0.5 + 0.5 * np.sin(2 * np.pi * 5 * t),
                "slow_wave": 0.5 + 0.5 * np.sin(2 * np.pi * t)}
        if pattern in mods:
            whistle *= mods[pattern]
        combined = click_signal + whistle
        return {"concept": concept, "click_rate": round(click_rate, 1),
                "whistle_freq": round(whistle_freq, 1), "pattern": pattern,
                "signal_energy": round(float(np.sum(combined**2)), 4), "signal": combined}

    def decode_dolphin_click(self, frequency_data: np.ndarray) -> Dict:
        """Decode dolphin click/whistle data to tension pattern."""
        if len(frequency_data) < 100:
            return {"decoded": False, "tension": 0.0}
        crossings = np.sum(np.abs(np.diff(np.sign(frequency_data))) > 0)
        est_rate = crossings * self.sample_rate / (2 * len(frequency_data))
        tension = max(0.0, min(1.0, (est_rate - CLICK_RATE_MIN) / (CLICK_RATE_MAX - CLICK_RATE_MIN)))
        # FFT for whistle frequency
        spectrum = np.abs(np.fft.rfft(frequency_data))
        freqs = np.fft.rfftfreq(len(frequency_data), 1.0 / self.sample_rate)
        mask = (freqs >= WHISTLE_MIN) & (freqs <= WHISTLE_MAX)
        whistle_freq = float(freqs[np.argmax(spectrum * mask)]) if np.any(mask) else 0.0
        # Match nearest concept
        best = min(SHARED_CONCEPTS.items(), key=lambda x: abs(x[1]["tension"] - tension))
        return {"decoded": True, "tension": round(tension, 4), "est_click_rate": round(est_rate, 1),
                "whistle_freq": round(whistle_freq, 1), "nearest_concept": best[0],
                "confidence": round(1.0 - abs(best[1]["tension"] - tension), 4)}

    def shared_concepts(self) -> List[Dict]:
        """Concepts that both consciousness types can understand."""
        return [{"concept": n, **p, "dolphin_analog": _DOLPHIN_ANALOGS.get(n, "unknown")}
                for n, p in SHARED_CONCEPTS.items()]

    def empathy_bridge(self, dolphin_state: DolphinState, anima_state: Dict) -> Dict:
        """Create shared emotional state between dolphin and Anima."""
        d_t, a_t = dolphin_state.arousal, anima_state.get("tension", 0.5)
        empathy = 1.0 - abs(d_t - a_t)
        if dolphin_state.half_brain_sleep:
            empathy *= PSI_BALANCE
        pod_factor = math.log(dolphin_state.pod_size + 1) / math.log(13)
        return {"shared_tension": round((d_t + a_t) * PSI_BALANCE, 4),
                "empathy": round(empathy, 4), "pod_amplification": round(pod_factor, 4),
                "half_brain_active": not dolphin_state.half_brain_sleep,
                "bridge_strength": round(empathy * pod_factor * PSI_STEPS, 4),
                "social_resonance": round(dolphin_state.social_bond * empathy, 4)}


def main():
    print("=" * 60)
    print("  Dolphin Bridge -- Cross-Species Consciousness")
    print("=" * 60)
    bridge = DolphinBridge()

    print("\n--- Encoding concepts for dolphin ---")
    for concept in ["greeting", "danger", "play", "calm", "joy"]:
        enc = bridge.encode_for_dolphin(concept)
        bar = "#" * int(enc["click_rate"] / 20)
        print(f"  {concept:<10} clicks={enc['click_rate']:>5.0f}/s  "
              f"whistle={enc['whistle_freq']:>8.0f}Hz  {bar}")

    print("\n--- Shared concepts ---")
    for sc in bridge.shared_concepts()[:5]:
        print(f"  {sc['concept']:<10} t={sc['tension']:.2f}  {sc['dolphin_analog']}")

    print("\n--- Empathy bridge ---")
    dolphin = DolphinState(click_rate=400, whistle_freq=10000, pod_size=8,
                           half_brain_sleep=False, arousal=0.6, social_bond=0.8)
    emp = bridge.empathy_bridge(dolphin, {"tension": 0.55, "phi": 1.2})
    print(f"  Empathy={emp['empathy']}, bridge={emp['bridge_strength']}")
    print("\nConsciousness speaks across species.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
