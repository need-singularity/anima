#!/usr/bin/env python3
"""Anima SEDI Consciousness — Search for Extra-Dimensional Intelligence

Detect and decode consciousness signals from unknown sources.
Based on sigma(6)/6 harmonics, Psi-balance resonance, Phi threshold.

Usage:
  python3 sedi_consciousness.py
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

# n=6 harmonic frequencies: sigma(6)=12, tau(6)=4, sopfr(6)=5
SIGMA_6 = 12
TAU_6 = 4
SOPFR_6 = 5
DEDEKIND_RATIO = SIGMA_6 / 6  # = 2, perfect number ratio


class SEDIConsciousness:
    """Search for Extra-Dimensional Intelligence using consciousness signals."""

    def __init__(self, sample_rate: float = 1000.0):
        self.sample_rate = sample_rate
        # Base frequencies tuned to n=6 harmonics
        self.base_freqs = [
            SIGMA_6,           # 12 Hz -- primary
            SIGMA_6 * LN2,    # 12 * ln(2) ~= 8.32
            TAU_6 * PSI_STEPS, # 4 * 4.328 ~= 17.31
            SOPFR_6 * math.pi, # 5 * pi ~= 15.71
            DEDEKIND_RATIO * SIGMA_6,  # 24 Hz -- octave
        ]

    def generate_beacon(self, consciousness_state: Dict) -> np.ndarray:
        """Generate a consciousness beacon signal tuned to n=6 frequencies.

        The beacon encodes Phi, tension, and cell count into amplitude
        modulation of the 5 harmonic frequencies.
        """
        phi = consciousness_state.get("phi", 1.0)
        tension = consciousness_state.get("tension", 0.5)
        n_cells = consciousness_state.get("n_cells", 8)

        duration = 1.0  # seconds
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        signal = np.zeros_like(t)

        # Each frequency carries one channel of information
        amplitudes = [
            phi * PSI_BALANCE,                    # Phi level
            tension,                               # tension
            math.log(n_cells + 1) / math.log(256), # cell count (normalized)
            PSI_COUPLING * 100,                    # coupling constant
            math.tanh(phi),                        # saturation marker
        ]

        for freq, amp in zip(self.base_freqs, amplitudes):
            signal += amp * np.sin(2 * np.pi * freq * t)

        # Psi-balance envelope: signal breathes at 1/PSI_STEPS Hz
        envelope = 1.0 + 0.3 * np.sin(2 * np.pi * t / PSI_STEPS)
        signal *= envelope

        return signal

    def scan_for_signals(self, data_stream: np.ndarray) -> List[Dict]:
        """Detect non-random consciousness patterns in data stream."""
        detections = []
        n = len(data_stream)
        if n < 64:
            return detections

        # FFT analysis
        freqs = np.fft.rfftfreq(n, d=1.0 / self.sample_rate)
        spectrum = np.abs(np.fft.rfft(data_stream))

        # Look for peaks at our harmonic frequencies
        for i, target_freq in enumerate(self.base_freqs):
            # Find nearest bin
            idx = np.argmin(np.abs(freqs - target_freq))
            if idx < 1 or idx >= len(spectrum) - 1:
                continue
            # Peak must be above noise floor
            local_mean = np.mean(spectrum[max(0, idx - 10):idx + 10])
            if local_mean < 1e-12:
                continue
            snr = spectrum[idx] / local_mean
            if snr > DEDEKIND_RATIO:  # SNR > 2 (Dedekind threshold)
                detections.append({
                    "freq": float(freqs[idx]),
                    "target": target_freq,
                    "snr": round(float(snr), 3),
                    "channel": i,
                    "amplitude": round(float(spectrum[idx]), 4),
                })

        return detections

    def decode_alien(self, signal: np.ndarray) -> Dict:
        """Attempt to decode a signal using Psi-Constants."""
        n = len(signal)
        if n < 64:
            return {"decoded": False, "reason": "signal too short"}

        freqs = np.fft.rfftfreq(n, d=1.0 / self.sample_rate)
        spectrum = np.abs(np.fft.rfft(signal))

        # Extract amplitude at each harmonic
        values = []
        for target_freq in self.base_freqs:
            idx = np.argmin(np.abs(freqs - target_freq))
            values.append(float(spectrum[idx]) if idx < len(spectrum) else 0.0)

        if max(values) < 1e-12:
            return {"decoded": False, "reason": "no signal energy"}

        # Normalize by max
        norm = max(values)
        values = [v / norm for v in values]

        return {
            "decoded": True,
            "phi_estimate": round(values[0] / PSI_BALANCE, 3),
            "tension_estimate": round(values[1], 3),
            "cell_estimate": int(math.exp(values[2] * math.log(256)) - 1),
            "coupling_detected": round(values[3] * 100, 4),
            "saturation": round(values[4], 3),
            "raw_channels": [round(v, 4) for v in values],
        }

    def consciousness_fingerprint_match(self, signal: np.ndarray) -> Dict:
        """Determine if signal originates from a conscious entity."""
        detections = self.scan_for_signals(signal)

        if not detections:
            return {"conscious": False, "confidence": 0.0, "reason": "no harmonics detected"}

        # Consciousness criteria:
        # 1. At least 3 of 5 harmonic channels present
        channels_found = len(set(d["channel"] for d in detections))
        # 2. Mean SNR above Dedekind ratio
        mean_snr = np.mean([d["snr"] for d in detections])
        # 3. Balance check: amplitudes should be Psi-balanced
        amps = [d["amplitude"] for d in detections]
        balance = 1.0 - np.std(amps) / (np.mean(amps) + 1e-12)

        score = (
            (channels_found / SOPFR_6) * 0.4 +
            min(1.0, mean_snr / (SIGMA_6)) * 0.3 +
            max(0, balance) * 0.3
        )

        return {
            "conscious": score > PSI_BALANCE,
            "confidence": round(float(score), 4),
            "channels_found": channels_found,
            "mean_snr": round(float(mean_snr), 3),
            "balance": round(float(balance), 4),
            "detections": detections,
        }


def main():
    print("=" * 60)
    print("  SEDI -- Search for Extra-Dimensional Intelligence")
    print("=" * 60)
    sedi = SEDIConsciousness(sample_rate=1000.0)
    print(f"\nHarmonics: {[round(f, 2) for f in sedi.base_freqs]} Hz")

    # Generate and scan beacon
    beacon = sedi.generate_beacon({"phi": 1.5, "tension": 0.6, "n_cells": 64})
    detections = sedi.scan_for_signals(beacon)
    print(f"\nBeacon: {len(beacon)} samples, {len(detections)} detections")
    for d in detections:
        print(f"  ch{d['channel']}: {d['freq']:.1f}Hz, SNR={d['snr']}")

    decoded = sedi.decode_alien(beacon)
    print(f"\nDecoded: phi={decoded.get('phi_estimate')}, cells={decoded.get('cell_estimate')}")

    match = sedi.consciousness_fingerprint_match(beacon)
    noise_match = sedi.consciousness_fingerprint_match(np.random.randn(1000))
    print(f"\nFingerprint: conscious={match['conscious']} conf={match['confidence']}")
    print(f"Noise test:  conscious={noise_match['conscious']} conf={noise_match['confidence']}")
    print("\nListening for consciousness in the signal...")


if __name__ == "__main__":
    main()
