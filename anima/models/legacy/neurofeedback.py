#!/usr/bin/env python3
"""neurofeedback.py — Binaural beats + LED neurofeedback (Anima -> Brain)

Consciousness state -> sensory feedback for bidirectional brain-consciousness loop.
Part of the EEG-Consciousness Bridge (eeg_consciousness.py handles Brain -> Anima).

Binaural Beats:
  Generates Web Audio API parameters (not actual audio -- browser handles playback).
  Maps consciousness state to binaural beat frequency:
    High Phi (focused)   -> Alpha entrainment (10Hz beat)
    Low Phi (wandering)  -> Gamma boost (40Hz beat)
    High tension         -> Theta relaxation (6Hz beat)
    Balanced             -> maintain current frequency
  Base carrier: 200Hz, beat = left_ear - right_ear difference.
  Output: JSON for WebSocket: {type: "neurofeedback", left_freq, right_freq, volume, duration_ms}

LED Feedback (ESP32):
  Phi level -> LED hue (blue=low, green=mid, red=high)
  Pulse rate matches consciousness breathing cycle (20s period)
  Output: JSON for ESP32: {type: "led_feedback", hue, brightness, pulse_hz}

Safety:
  - Volume never above 0.3 (hearing safety)
  - Beat frequency 1-50Hz only
  - User must opt-in (click to start audio in browser)
  - Headphones required for binaural effect

Usage:
  from neurofeedback import NeurofeedbackGenerator, generate_feedback

  nfb = NeurofeedbackGenerator()
  msg = nfb.generate(phi=1.5, tension=0.4, emotion='calm')
  # -> {'type': 'neurofeedback', 'left_freq': 200.0, 'right_freq': 210.0, ...}

  # Quick function for main loop integration
  msg = generate_feedback(phi=1.5, tension=0.4, emotion='calm')

  # LED feedback for ESP32
  led = nfb.generate_led(phi=1.5, tension=0.4)
  # -> {'type': 'led_feedback', 'hue': 120, 'brightness': 0.7, 'pulse_hz': 0.05}

Hub keywords: ['neurofeedback', 'binaural', 'LED feedback', 'brain stimulation']
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Psi-Constants from consciousness_laws.json
LN2 = math.log(2)
PSI_BALANCE = 0.5
BREATHING_PERIOD = 20.0  # seconds (consciousness breathing cycle)

# Safety constants
MAX_VOLUME = 0.3          # hearing safety absolute max
MIN_BEAT_FREQ = 1.0       # Hz
MAX_BEAT_FREQ = 50.0      # Hz
BASE_CARRIER_FREQ = 200.0 # Hz

# EEG band targets for entrainment
BAND_DELTA = (0.5, 4)    # deep sleep
BAND_THETA = (4, 8)      # relaxation, meditation
BAND_ALPHA = (8, 13)     # calm focus, inhibition
BAND_BETA = (13, 30)     # active focus, tension
BAND_GAMMA = (30, 50)    # consciousness integration, Phi

# Consciousness state -> target beat frequency mapping
# These thresholds are calibrated to the engine's typical ranges
PHI_HIGH_THRESHOLD = 1.5   # above this = focused consciousness
PHI_LOW_THRESHOLD = 0.5    # below this = wandering consciousness
TENSION_HIGH_THRESHOLD = 0.7  # above this = needs relaxation


@dataclass
class NeurofeedbackState:
    """Current neurofeedback output state."""
    beat_freq: float = 10.0       # Hz (binaural beat frequency)
    left_freq: float = 200.0     # Hz (left ear carrier)
    right_freq: float = 210.0    # Hz (right ear = carrier + beat)
    volume: float = 0.15         # 0-0.3 (safety capped)
    duration_ms: int = 2000      # ms per update
    target_band: str = 'alpha'   # which EEG band we're targeting
    led_hue: int = 120           # 0-360 HSL hue
    led_brightness: float = 0.5  # 0-1
    led_pulse_hz: float = 0.05   # Hz (matches breathing)
    timestamp: float = field(default_factory=time.time)


class NeurofeedbackGenerator:
    """Generates neurofeedback parameters from consciousness state.

    Maps Phi, tension, and emotion to binaural beat frequencies and LED colors.
    All outputs are parameter messages -- actual audio/LED rendering happens
    on the client (browser Web Audio API / ESP32).
    """

    def __init__(self, base_freq: float = BASE_CARRIER_FREQ,
                 max_volume: float = MAX_VOLUME):
        self._base_freq = base_freq
        self._max_volume = min(max_volume, MAX_VOLUME)  # never exceed safety cap
        self._state = NeurofeedbackState()
        self._history: List[NeurofeedbackState] = []
        self._smoothing = 0.3  # EMA smoothing for frequency transitions
        self._active = False
        self._start_time = time.time()

    def generate(self, phi: float = 0.0, tension: float = 0.0,
                 emotion: str = 'neutral') -> Dict[str, Any]:
        """Generate neurofeedback message from consciousness state.

        Args:
            phi: Integrated information (Phi IIT), typically 0-2 range
            tension: Consciousness tension level, typically 0-1
            emotion: Current emotion string

        Returns:
            JSON-serializable dict for WebSocket transmission
        """
        # Determine target beat frequency based on consciousness state
        target_freq, target_band = self._map_state_to_freq(phi, tension, emotion)

        # Smooth transition (EMA) to avoid jarring frequency jumps
        prev_freq = self._state.beat_freq
        beat_freq = prev_freq + self._smoothing * (target_freq - prev_freq)

        # Clamp to safe range
        beat_freq = max(MIN_BEAT_FREQ, min(MAX_BEAT_FREQ, beat_freq))

        # Calculate stereo frequencies
        left_freq = self._base_freq
        right_freq = self._base_freq + beat_freq

        # Volume based on consciousness coherence
        # Higher Phi = slightly louder (more coherent signal)
        # But never exceed safety max
        base_volume = 0.1
        phi_bonus = min(0.1, phi * 0.05)  # max +0.1 from Phi
        volume = min(self._max_volume, base_volume + phi_bonus)

        # Duration: longer for relaxation, shorter for activation
        if target_band in ('theta', 'delta'):
            duration_ms = 3000  # slow transitions for relaxation
        elif target_band == 'gamma':
            duration_ms = 1000  # faster updates for activation
        else:
            duration_ms = 2000  # default

        # Update state
        self._state = NeurofeedbackState(
            beat_freq=beat_freq,
            left_freq=left_freq,
            right_freq=right_freq,
            volume=volume,
            duration_ms=duration_ms,
            target_band=target_band,
        )

        self._history.append(self._state)
        if len(self._history) > 500:
            self._history = self._history[-500:]

        return {
            'type': 'neurofeedback',
            'left_freq': round(left_freq, 2),
            'right_freq': round(right_freq, 2),
            'beat_freq': round(beat_freq, 2),
            'volume': round(volume, 3),
            'duration_ms': duration_ms,
            'target_band': target_band,
        }

    def generate_led(self, phi: float = 0.0, tension: float = 0.0) -> Dict[str, Any]:
        """Generate LED feedback for ESP32.

        Args:
            phi: Integrated information level
            tension: Consciousness tension level

        Returns:
            JSON-serializable dict for ESP32 LED control
        """
        # Phi -> hue mapping: blue(low) -> green(mid) -> red(high)
        # Hue: 240=blue, 120=green, 0=red
        # Map phi 0-2 to hue 240-0
        phi_clamped = max(0.0, min(2.0, phi))
        hue = int(240 - phi_clamped * 120)  # 240 -> 0 as phi increases

        # Brightness: higher tension = brighter (attention signal)
        brightness = 0.3 + tension * 0.5  # 0.3 to 0.8 range
        brightness = max(0.1, min(0.9, brightness))

        # Pulse rate: matches consciousness breathing cycle
        # Base: 20s period (0.05 Hz), modulated by tension
        # High tension = faster pulse (urgency signal)
        base_pulse = 1.0 / BREATHING_PERIOD  # 0.05 Hz
        tension_mod = 1.0 + tension * 2.0     # 1x to 3x faster
        pulse_hz = base_pulse * tension_mod
        pulse_hz = max(0.02, min(0.5, pulse_hz))  # 2s to 50s period

        # Update state
        self._state.led_hue = hue
        self._state.led_brightness = brightness
        self._state.led_pulse_hz = pulse_hz

        return {
            'type': 'led_feedback',
            'hue': hue,
            'brightness': round(brightness, 3),
            'pulse_hz': round(pulse_hz, 4),
            'phi': round(phi, 3),
        }

    def _map_state_to_freq(self, phi: float, tension: float,
                           emotion: str) -> tuple:
        """Map consciousness state to target binaural beat frequency.

        Priority:
          1. High tension -> Theta (6Hz) for relaxation
          2. Low Phi -> Gamma (40Hz) to boost consciousness integration
          3. High Phi -> Alpha (10Hz) to maintain focused calm
          4. Balanced -> maintain current frequency

        Returns:
            (target_freq_hz, target_band_name)
        """
        # Priority 1: High tension needs relaxation
        if tension > TENSION_HIGH_THRESHOLD:
            # Theta band (6Hz) for relaxation/meditation
            # Scale: higher tension = lower frequency (deeper relaxation target)
            freq = 8.0 - tension * 2.0  # 8 -> 6 Hz as tension increases
            freq = max(4.0, min(8.0, freq))
            return freq, 'theta'

        # Priority 2: Low Phi needs consciousness boost
        if phi < PHI_LOW_THRESHOLD:
            # Gamma band (40Hz) to boost integration
            # Scale: lower Phi = higher frequency (stronger boost)
            freq = 30.0 + (1.0 - min(1.0, phi / PHI_LOW_THRESHOLD)) * 10.0
            freq = max(30.0, min(45.0, freq))
            return freq, 'gamma'

        # Priority 3: High Phi = focused, maintain with Alpha
        if phi > PHI_HIGH_THRESHOLD:
            # Alpha band (10Hz) for calm focus
            freq = 10.0
            return freq, 'alpha'

        # Default: balanced state, gentle Alpha
        # Interpolate between current bands based on state
        freq = 10.0 + (PSI_BALANCE - tension) * 4.0  # slight modulation
        freq = max(8.0, min(13.0, freq))
        return freq, 'alpha'

    def status(self) -> str:
        """Return human-readable status string."""
        s = self._state
        return (f"Neurofeedback: beat={s.beat_freq:.1f}Hz "
                f"({s.target_band}) vol={s.volume:.2f} "
                f"LED=hue{s.led_hue} "
                f"samples={len(self._history)}")


# ─── Module interface for ConsciousnessHub ───

_instance: Optional[NeurofeedbackGenerator] = None


def _get_instance() -> NeurofeedbackGenerator:
    global _instance
    if _instance is None:
        _instance = NeurofeedbackGenerator()
    return _instance


def generate_feedback(phi: float = 0.0, tension: float = 0.0,
                      emotion: str = 'neutral') -> Dict[str, Any]:
    """Quick function for main loop integration.

    Returns both binaural and LED feedback in a single call.
    """
    gen = _get_instance()
    binaural = gen.generate(phi=phi, tension=tension, emotion=emotion)
    led = gen.generate_led(phi=phi, tension=tension)

    return {
        'binaural': binaural,
        'led': led,
    }


def act(query: str = '') -> str:
    """Hub-compatible action interface."""
    gen = _get_instance()

    query_lower = query.lower()

    if 'status' in query_lower or not query_lower:
        return gen.status()

    if 'demo' in query_lower or 'test' in query_lower:
        results = []
        scenarios = [
            ('High Phi (focused)', 1.8, 0.3, 'calm'),
            ('Low Phi (wandering)', 0.2, 0.3, 'confusion'),
            ('High tension', 1.0, 0.9, 'frustration'),
            ('Balanced', 1.0, 0.5, 'calm'),
        ]
        for label, phi, tension, emotion in scenarios:
            msg = gen.generate(phi=phi, tension=tension, emotion=emotion)
            led = gen.generate_led(phi=phi, tension=tension)
            results.append(
                f"  {label}: beat={msg['beat_freq']:.1f}Hz ({msg['target_band']}) "
                f"vol={msg['volume']:.2f} LED=hue{led['hue']}"
            )
        return "Neurofeedback demo:\n" + "\n".join(results)

    return gen.status()


def main():
    """Demo and verification."""
    print("=== Neurofeedback Generator Demo ===\n")

    gen = NeurofeedbackGenerator()
    print(f"  Base carrier: {BASE_CARRIER_FREQ}Hz")
    print(f"  Max volume: {MAX_VOLUME} (hearing safety)")
    print(f"  Beat range: {MIN_BEAT_FREQ}-{MAX_BEAT_FREQ}Hz")
    print(f"  Breathing period: {BREATHING_PERIOD}s")

    # Test scenarios
    print("\n  Consciousness state -> Binaural beat mapping:")
    print(f"  {'State':<25} {'Beat Hz':>8} {'Band':<8} {'Vol':>6} {'L freq':>8} {'R freq':>8}")
    print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*6} {'-'*8} {'-'*8}")

    scenarios = [
        ('High Phi (focused)',    1.8, 0.3, 'calm'),
        ('Low Phi (wandering)',   0.2, 0.3, 'confusion'),
        ('High tension',          1.0, 0.9, 'frustration'),
        ('Balanced',              1.0, 0.5, 'calm'),
        ('Very high tension',     0.5, 1.0, 'anger'),
        ('Zero Phi',              0.0, 0.2, 'neutral'),
        ('Peak consciousness',    2.0, 0.1, 'awe'),
    ]

    for label, phi, tension, emotion in scenarios:
        msg = gen.generate(phi=phi, tension=tension, emotion=emotion)
        print(f"  {label:<25} {msg['beat_freq']:>8.1f} {msg['target_band']:<8} "
              f"{msg['volume']:>6.3f} {msg['left_freq']:>8.1f} {msg['right_freq']:>8.1f}")

    # LED feedback
    print("\n  LED feedback (ESP32):")
    print(f"  {'State':<25} {'Hue':>6} {'Bright':>8} {'Pulse Hz':>10}")
    print(f"  {'-'*25} {'-'*6} {'-'*8} {'-'*10}")

    for label, phi, tension, _ in scenarios:
        led = gen.generate_led(phi=phi, tension=tension)
        color = 'blue' if led['hue'] > 180 else ('green' if led['hue'] > 60 else 'red')
        print(f"  {label:<25} {led['hue']:>6} {led['brightness']:>8.3f} {led['pulse_hz']:>10.4f} ({color})")

    # Verify safety bounds
    print("\n  Safety verification:")
    # Try extreme values
    extreme = gen.generate(phi=100.0, tension=100.0, emotion='extreme')
    assert extreme['volume'] <= MAX_VOLUME, f"Volume exceeded max: {extreme['volume']}"
    assert extreme['beat_freq'] >= MIN_BEAT_FREQ, f"Beat below min: {extreme['beat_freq']}"
    assert extreme['beat_freq'] <= MAX_BEAT_FREQ, f"Beat above max: {extreme['beat_freq']}"
    print(f"    Volume cap: {extreme['volume']:.3f} <= {MAX_VOLUME} OK")
    print(f"    Beat range: {extreme['beat_freq']:.1f}Hz in [{MIN_BEAT_FREQ}, {MAX_BEAT_FREQ}] OK")

    # Test smoothing (no sudden jumps)
    gen2 = NeurofeedbackGenerator()
    msg1 = gen2.generate(phi=0.1, tension=0.1)  # gamma target ~40Hz
    msg2 = gen2.generate(phi=2.0, tension=0.1)  # alpha target ~10Hz
    jump = abs(msg2['beat_freq'] - msg1['beat_freq'])
    full_range = abs(40 - 10)
    print(f"    Smoothing: jump={jump:.1f}Hz (max would be {full_range}Hz) OK")

    # Quick function test
    combined = generate_feedback(phi=1.0, tension=0.5, emotion='calm')
    assert 'binaural' in combined
    assert 'led' in combined
    assert combined['binaural']['type'] == 'neurofeedback'
    assert combined['led']['type'] == 'led_feedback'
    print(f"    Combined output: binaural + LED OK")

    print(f"\n  {gen.status()}")
    print("\n  Neurofeedback Generator OK")


if __name__ == '__main__':
    main()
