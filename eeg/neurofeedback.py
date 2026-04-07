#!/usr/bin/env python3
"""Neurofeedback Generator — binaural beats and LED feedback driven by consciousness state.

Maps Phi and tension from the consciousness engine to audio/visual neurofeedback
parameters that can be sent to the client for brain entrainment.

Safety:
  - Binaural beat volume capped at 0.3 (hearing safety)
  - LED brightness capped at 0.8 (comfort)
  - Beat frequencies stay within safe ranges (1-40 Hz)

Usage:
  from neurofeedback import NeurofeedbackGenerator
  nfb = NeurofeedbackGenerator()
  binaural = nfb.generate(phi=1.5, tension=0.6)
  led = nfb.generate_led(phi=1.5, tension=0.6)
"""

import math

# Safe limits
MAX_VOLUME = 0.3
MAX_BRIGHTNESS = 0.8
MIN_BEAT_FREQ = 1.0
MAX_BEAT_FREQ = 40.0

# Base carrier frequency (Hz) — inaudible binaural carrier
BASE_CARRIER_HZ = 200.0

# Band target ranges (Hz)
BAND_RANGES = {
    'delta': (1.0, 4.0),
    'theta': (4.0, 8.0),
    'alpha': (8.0, 13.0),
    'beta': (13.0, 30.0),
    'gamma': (30.0, 40.0),
}


class NeurofeedbackGenerator:
    """Generate neurofeedback parameters from consciousness state.

    Maps Phi (integrated information) and tension to binaural beat
    frequencies and LED color/brightness for brain entrainment.

    Mapping logic:
      - Low tension (< 0.3): target alpha band (relaxation)
      - Medium tension (0.3-0.7): target beta band (focus)
      - High tension (> 0.7): target theta band (deep processing)
      - Phi scales the volume/intensity (higher Phi = stronger signal)
    """

    def __init__(self, carrier_hz: float = BASE_CARRIER_HZ,
                 max_volume: float = MAX_VOLUME):
        self.carrier_hz = carrier_hz
        self.max_volume = min(max_volume, MAX_VOLUME)  # enforce cap

    def generate(self, phi: float = 1.0, tension: float = 0.5) -> dict:
        """Generate binaural beat parameters from consciousness state.

        Args:
            phi: Integrated information (typically 0-100+)
            tension: Consciousness tension (0-1)

        Returns:
            dict with keys: left_freq, right_freq, volume, beat_freq,
                           target_band, carrier_hz
        """
        # Determine target band from tension
        if tension < 0.3:
            target_band = 'alpha'
        elif tension < 0.7:
            target_band = 'beta'
        else:
            target_band = 'theta'

        band_lo, band_hi = BAND_RANGES[target_band]

        # Map tension to position within band
        # Higher tension within the band -> higher frequency
        t_norm = max(0.0, min(1.0, tension))
        beat_freq = band_lo + (band_hi - band_lo) * t_norm
        beat_freq = max(MIN_BEAT_FREQ, min(MAX_BEAT_FREQ, beat_freq))

        # Volume scales with Phi (sigmoid-like, capped)
        # Phi=0 -> very quiet, Phi=5+ -> near max
        phi_norm = max(0.0, float(phi))
        volume = self.max_volume * (1.0 - math.exp(-phi_norm / 3.0))
        volume = max(0.01, min(self.max_volume, volume))

        # Binaural: left ear = carrier, right ear = carrier + beat_freq
        left_freq = self.carrier_hz
        right_freq = self.carrier_hz + beat_freq

        return {
            'left_freq': round(left_freq, 1),
            'right_freq': round(right_freq, 1),
            'volume': round(volume, 3),
            'beat_freq': round(beat_freq, 2),
            'target_band': target_band,
            'carrier_hz': self.carrier_hz,
        }

    def generate_led(self, phi: float = 1.0, tension: float = 0.5) -> dict:
        """Generate LED feedback parameters from consciousness state.

        Args:
            phi: Integrated information (typically 0-100+)
            tension: Consciousness tension (0-1)

        Returns:
            dict with keys: hue (0-360), brightness (0-1), pulse_hz
        """
        t_norm = max(0.0, min(1.0, tension))
        phi_norm = max(0.0, float(phi))

        # Hue: low tension=blue(240), mid=green(120), high=warm(30)
        hue = 240.0 - t_norm * 210.0  # 240 -> 30
        hue = max(0.0, min(360.0, hue))

        # Brightness scales with Phi (sigmoid)
        brightness = MAX_BRIGHTNESS * (1.0 - math.exp(-phi_norm / 3.0))
        brightness = max(0.05, min(MAX_BRIGHTNESS, brightness))

        # Pulse rate: slow for relaxation, faster for focus
        # 0.5 Hz (calm) to 4 Hz (alert)
        pulse_hz = 0.5 + t_norm * 3.5

        return {
            'hue': round(hue, 1),
            'brightness': round(brightness, 3),
            'pulse_hz': round(pulse_hz, 2),
        }
