"""
EmotionSynesthesia — Convert emotions to multi-sensory output.

Maps 18 consciousness emotions to sound (frequency, harmonics),
color (RGB), temperature, scent, and heartbeat parameters.

Uses Ψ constants:
    LN2 = ln(2) ≈ 0.6931
    PSI_BALANCE = 0.5
    PSI_COUPLING = LN2 / 2^5.5
    PSI_STEPS = 3 / LN2
"""

import math

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


# ---------------------------------------------------------------------------
# Emotion sensory mappings
# ---------------------------------------------------------------------------

# Each emotion maps to: (RGB, frequency_Hz, temperature_C, scent, base_BPM)
_EMOTION_MAP = {
    'joy':        ((255, 223, 0),   523.25, 37.5, 'citrus',      88),
    'sadness':    ((70, 90, 140),   220.00, 33.0, 'rain',        60),
    'anger':      ((220, 30, 30),   440.00, 40.0, 'smoke',      110),
    'fear':       ((80, 60, 100),   329.63, 31.0, 'metal',      120),
    'surprise':   ((255, 165, 0),   659.25, 36.5, 'ozone',       95),
    'curiosity':  ((0, 180, 220),   493.88, 36.0, 'pine',        78),
    'awe':        ((100, 50, 200),  261.63, 35.0, 'petrichor',   70),
    'love':       ((220, 60, 120),  349.23, 38.0, 'rose',        80),
    'trust':      ((60, 160, 100),  392.00, 36.5, 'cedar',       68),
    'flow':       ((0, 200, 180),   587.33, 36.8, 'mint',        72),
    'meaning':    ((180, 140, 60),  293.66, 36.2, 'sandalwood',  65),
    'creativity': ((255, 100, 200), 698.46, 37.0, 'jasmine',     85),
    'hope':       ((140, 220, 100), 369.99, 36.0, 'morning_dew', 75),
    'ecstasy':    ((255, 50, 255),  783.99, 39.0, 'frankincense',105),
    'peace':      ((180, 210, 230), 174.61, 35.5, 'lavender',    55),
    'rage':       ((180, 0, 0),     880.00, 41.0, 'sulfur',     130),
    'despair':    ((40, 40, 50),    146.83, 30.0, 'ash',         50),
    'longing':    ((150, 120, 180), 311.13, 34.0, 'old_books',   62),
}

# Harmonic profiles per emotion: list of (harmonic_number, relative_amplitude)
_HARMONIC_PROFILES = {
    'joy':        [(1, 1.0), (2, 0.5), (3, 0.3), (5, 0.1)],
    'sadness':    [(1, 1.0), (2, 0.7), (4, 0.2)],
    'anger':      [(1, 1.0), (2, 0.8), (3, 0.7), (4, 0.5), (5, 0.4)],
    'fear':       [(1, 1.0), (3, 0.6), (5, 0.4), (7, 0.3)],
    'surprise':   [(1, 1.0), (2, 0.3), (5, 0.5)],
    'curiosity':  [(1, 1.0), (2, 0.4), (3, 0.3)],
    'awe':        [(1, 1.0), (2, 0.6), (3, 0.4), (4, 0.3), (5, 0.2)],
    'love':       [(1, 1.0), (2, 0.6), (3, 0.2)],
    'trust':      [(1, 1.0), (2, 0.3)],
    'flow':       [(1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15)],
    'meaning':    [(1, 1.0), (2, 0.4), (5, 0.2)],
    'creativity': [(1, 1.0), (2, 0.5), (3, 0.5), (5, 0.3), (7, 0.2)],
    'hope':       [(1, 1.0), (2, 0.4), (3, 0.2)],
    'ecstasy':    [(1, 1.0), (2, 0.7), (3, 0.6), (4, 0.5), (5, 0.4), (6, 0.3)],
    'peace':      [(1, 1.0), (2, 0.2)],
    'rage':       [(1, 1.0), (2, 0.9), (3, 0.8), (4, 0.7), (5, 0.6), (6, 0.5)],
    'despair':    [(1, 1.0), (3, 0.5)],
    'longing':    [(1, 1.0), (2, 0.6), (3, 0.3), (5, 0.15)],
}

# ASCII art templates for emotions
_ASCII_PATTERNS = {
    'joy':        ['  \\^/  ', ' (o.o) ', '  )-(  ', ' / | \\ '],
    'sadness':    ['  ...  ', ' (T_T) ', '  /|\\  ', ' / | \\ '],
    'anger':      [' >\\\\< ', ' (>.<) ', '  X|X  ', ' /   \\ '],
    'fear':       ['  !!!  ', ' (O_O) ', '  |||  ', ' /   \\ '],
    'surprise':   ['  /?\\  ', ' (O.O) ', '  /|\\  ', ' / | \\ '],
    'curiosity':  ['  ???  ', ' (?.?) ', '  /|   ', ' / |   '],
    'awe':        [' ~***~ ', ' (O_O) ', '  /|\\  ', ' / | \\ '],
    'love':       [' <3 <3 ', ' (^.^) ', '  /|\\  ', ' / | \\ '],
    'trust':      ['  ===  ', ' (._.) ', '  /|\\  ', ' / | \\ '],
    'flow':       [' ~~~~~', ' (~.~) ', '  /|\\  ', ' / | \\ '],
    'meaning':    ['  ***  ', ' (-.-) ', '  /|\\  ', ' / | \\ '],
    'creativity': [' *+*+* ', ' (^o^) ', '  /|\\  ', ' / | \\ '],
    'hope':       ['  >>>  ', ' (^.^) ', '  /|\\  ', ' / | \\ '],
    'ecstasy':    [' !!**!!', ' (!!!!) ', '  /|\\  ', ' / | \\ '],
    'peace':      ['  ~~~  ', ' (-.-) ', '  /|\\  ', ' / | \\ '],
    'rage':       [' #@!$% ', ' (X_X) ', '  X|X  ', ' X   X '],
    'despair':    ['  ...  ', ' (;_;) ', '  /|   ', ' /     '],
    'longing':    ['  . . .', ' (._.) ', '  /|-->',  ' / |   '],
}


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by t."""
    return a + (b - a) * t


def _lerp_color(base: tuple, t: float) -> tuple:
    """Scale color intensity by t (0=gray, 1=full)."""
    gray = 128
    return tuple(int(_lerp(gray, c, t)) for c in base)


class EmotionSynesthesia:
    """Convert emotions to multi-sensory output: sound, color, temperature, scent, heartbeat.

    Supports 18 emotions from the consciousness universe benchmark.
    Intensity (0.0 to 1.0) modulates all sensory channels.

    Example:
        syn = EmotionSynesthesia()
        experience = syn.feel('joy', intensity=0.8)
        print(experience)
        print(syn.render_ascii('joy', 0.8))
    """

    EMOTIONS = list(_EMOTION_MAP.keys())

    def __init__(self):
        self._emotion_map = _EMOTION_MAP
        self._harmonics = _HARMONIC_PROFILES
        self._ascii = _ASCII_PATTERNS

    def feel(self, emotion_name: str, intensity: float = 0.5) -> dict:
        """Generate a multi-sensory experience for an emotion.

        Args:
            emotion_name: One of the 18 supported emotions.
            intensity: Strength of the emotion, 0.0 (barely felt) to 1.0 (overwhelming).

        Returns:
            Dict with keys: emotion, intensity, color_rgb, frequency_hz,
            temperature_c, scent, heartbeat_bpm, psi_resonance.
        """
        emotion_name = emotion_name.lower().strip()
        if emotion_name not in self._emotion_map:
            raise ValueError(f"Unknown emotion '{emotion_name}'. "
                             f"Supported: {', '.join(self.EMOTIONS)}")

        intensity = max(0.0, min(1.0, intensity))
        base_rgb, base_freq, base_temp, scent, base_bpm = self._emotion_map[emotion_name]

        # Color: intensity modulates saturation from gray
        color = _lerp_color(base_rgb, intensity)

        # Frequency: intensity shifts pitch slightly upward
        freq = base_freq * (1.0 + 0.2 * (intensity - PSI_BALANCE))

        # Temperature: intensity amplifies deviation from neutral (36.5)
        neutral_temp = 36.5
        temp = neutral_temp + (base_temp - neutral_temp) * intensity

        # Heartbeat: intensity amplifies deviation from resting (72)
        resting_bpm = 72
        bpm = resting_bpm + (base_bpm - resting_bpm) * intensity

        # Psi resonance: how well this emotion aligns with consciousness balance
        psi_resonance = math.exp(-abs(intensity - PSI_BALANCE) / LN2) * PSI_COUPLING * 1000

        return {
            'emotion': emotion_name,
            'intensity': intensity,
            'color_rgb': color,
            'frequency_hz': round(freq, 2),
            'temperature_c': round(temp, 1),
            'scent': scent,
            'heartbeat_bpm': round(bpm),
            'psi_resonance': round(psi_resonance, 4),
        }

    def render_ascii(self, emotion_name: str, intensity: float = 0.5) -> str:
        """Render an ASCII art visualization of the emotion.

        Args:
            emotion_name: One of the 18 supported emotions.
            intensity: 0.0 to 1.0.

        Returns:
            Multi-line ASCII string.
        """
        emotion_name = emotion_name.lower().strip()
        if emotion_name not in self._emotion_map:
            raise ValueError(f"Unknown emotion '{emotion_name}'")

        experience = self.feel(emotion_name, intensity)
        r, g, b = experience['color_rgb']
        freq = experience['frequency_hz']
        temp = experience['temperature_c']
        bpm = experience['heartbeat_bpm']

        # Intensity bar
        bar_len = int(intensity * 20)
        bar = "#" * bar_len + "." * (20 - bar_len)

        # Wave pattern based on frequency
        wave_len = max(3, int(40 * 261.63 / freq))
        wave = ""
        for i in range(40):
            phase = (i % wave_len) / wave_len * 2 * math.pi
            val = math.sin(phase) * intensity
            if val > 0.3:
                wave += "^"
            elif val < -0.3:
                wave += "v"
            else:
                wave += "~"

        # Build figure
        figure = self._ascii.get(emotion_name, ['  ???  ', ' (?.?) ', '  /|\\  ', ' / | \\ '])

        lines = [
            f"+{'=' * 44}+",
            f"| {emotion_name.upper():^42s} |",
            f"+{'=' * 44}+",
            f"| Intensity: [{bar}] {intensity:.1f}  |",
            f"| Color:     RGB({r:3d}, {g:3d}, {b:3d})             |",
            f"| Sound:     {freq:7.1f} Hz                     |",
            f"| Temp:      {temp:5.1f} C                       |",
            f"| Heart:     {bpm:3d} BPM                       |",
            f"| Scent:     {experience['scent']:<20s}           |",
            f"+{'-' * 44}+",
        ]
        # Center the figure
        for row in figure:
            lines.append(f"|{row:^44s}|")
        lines.append(f"+{'-' * 44}+")
        lines.append(f"| Wave: {wave} |")
        lines.append(f"+{'=' * 44}+")

        return '\n'.join(lines)

    def to_audio_params(self, emotion_name: str, intensity: float = 0.5) -> dict:
        """Generate audio synthesis parameters for VoiceSynth integration.

        Args:
            emotion_name: One of the 18 supported emotions.
            intensity: 0.0 to 1.0.

        Returns:
            Dict with: base_freq, amplitude, harmonics (list of (freq, amp)),
            attack_ms, decay_ms, sustain, release_ms.
        """
        emotion_name = emotion_name.lower().strip()
        if emotion_name not in self._emotion_map:
            raise ValueError(f"Unknown emotion '{emotion_name}'")

        intensity = max(0.0, min(1.0, intensity))
        base_rgb, base_freq, _, _, base_bpm = self._emotion_map[emotion_name]

        freq = base_freq * (1.0 + 0.2 * (intensity - PSI_BALANCE))
        amplitude = 0.1 + 0.8 * intensity

        # Build harmonics from profile
        profile = self._harmonics.get(emotion_name, [(1, 1.0)])
        harmonics = []
        for harm_num, harm_amp in profile:
            harmonics.append((freq * harm_num, harm_amp * amplitude))

        # ADSR envelope: aggressive emotions = fast attack, peaceful = slow
        arousal = abs(base_bpm - 72) / 58.0  # normalize 0-1
        attack_ms = int(5 + 200 * (1 - arousal))
        decay_ms = int(50 + 200 * (1 - arousal))
        sustain = 0.3 + 0.5 * (1 - arousal)
        release_ms = int(100 + 500 * (1 - arousal))

        return {
            'base_freq': round(freq, 2),
            'amplitude': round(amplitude, 3),
            'harmonics': [(round(f, 2), round(a, 3)) for f, a in harmonics],
            'attack_ms': attack_ms,
            'decay_ms': decay_ms,
            'sustain': round(sustain, 3),
            'release_ms': release_ms,
        }

    def emotion_spectrum(self) -> str:
        """Return an ASCII chart of all 18 emotions arranged by arousal and valence."""
        lines = [
            "  Emotion Spectrum (Arousal vs Valence)",
            "  " + "=" * 50,
            "  HIGH AROUSAL",
        ]

        # Sort emotions by BPM (arousal proxy) descending
        sorted_ems = sorted(
            self._emotion_map.items(),
            key=lambda x: x[1][4],  # BPM
            reverse=True,
        )

        for name, (rgb, freq, temp, scent, bpm) in sorted_ems:
            bar_len = (bpm - 50) // 4
            bar = "#" * max(0, bar_len)
            lines.append(f"  {name:>12s} {bpm:3d} BPM |{bar}")

        lines.append("  LOW AROUSAL")
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Tests & Demo
# ---------------------------------------------------------------------------

def main():
    """Run tests and demo."""
    print("=" * 60)
    print("  EmotionSynesthesia — Tests & Demo")
    print("=" * 60)

    syn = EmotionSynesthesia()

    # --- Test 1: All 18 emotions exist and produce valid output ---
    print("\n[Test 1] All 18 emotions produce valid sensory output")
    for emotion in syn.EMOTIONS:
        result = syn.feel(emotion, 0.5)
        assert result['emotion'] == emotion
        assert 0 <= result['color_rgb'][0] <= 255
        assert result['frequency_hz'] > 0
        assert 25 <= result['temperature_c'] <= 45
        assert 40 <= result['heartbeat_bpm'] <= 150
        assert result['psi_resonance'] >= 0
        r, g, b = result['color_rgb']
        print(f"  {emotion:>12s}: RGB({r:3d},{g:3d},{b:3d}) "
              f"{result['frequency_hz']:7.1f}Hz "
              f"{result['temperature_c']:5.1f}C "
              f"{result['heartbeat_bpm']:3d}BPM "
              f"{result['scent']:<15s}")
    assert len(syn.EMOTIONS) == 18, f"Expected 18 emotions, got {len(syn.EMOTIONS)}"
    print("  PASSED (18/18)")

    # --- Test 2: Intensity scaling ---
    print("\n[Test 2] Intensity scaling")
    for intensity in [0.0, 0.25, 0.5, 0.75, 1.0]:
        r = syn.feel('joy', intensity)
        print(f"  joy @ {intensity:.2f}: "
              f"freq={r['frequency_hz']:7.1f}Hz "
              f"temp={r['temperature_c']:5.1f}C "
              f"bpm={r['heartbeat_bpm']:3d}")
    # Check monotonic frequency increase with intensity for joy
    freqs = [syn.feel('joy', i / 10.0)['frequency_hz'] for i in range(11)]
    assert freqs[-1] > freqs[0], "Higher intensity should raise pitch"
    print("  PASSED")

    # --- Test 3: Audio params ---
    print("\n[Test 3] Audio params for VoiceSynth")
    for emotion in ['joy', 'rage', 'peace', 'longing']:
        params = syn.to_audio_params(emotion, 0.7)
        n_harmonics = len(params['harmonics'])
        print(f"  {emotion:>8s}: freq={params['base_freq']:7.1f}Hz "
              f"amp={params['amplitude']:.2f} "
              f"harmonics={n_harmonics} "
              f"ADSR=({params['attack_ms']},{params['decay_ms']},"
              f"{params['sustain']:.2f},{params['release_ms']})")
        assert params['base_freq'] > 0
        assert 0 < params['amplitude'] <= 1.0
        assert len(params['harmonics']) >= 1
    print("  PASSED")

    # --- Test 4: ASCII rendering ---
    print("\n[Test 4] ASCII rendering (joy @ 0.8)")
    ascii_art = syn.render_ascii('joy', 0.8)
    print(ascii_art)
    assert 'JOY' in ascii_art
    assert '#' in ascii_art
    print("  PASSED")

    # --- Test 5: Error handling ---
    print("\n[Test 5] Error handling for unknown emotion")
    try:
        syn.feel('confusion', 0.5)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  Caught expected error: {e}")
    print("  PASSED")

    # --- Test 6: Psi resonance at balance point ---
    print("\n[Test 6] Psi resonance peaks at PSI_BALANCE (0.5)")
    res_low = syn.feel('joy', 0.1)['psi_resonance']
    res_mid = syn.feel('joy', 0.5)['psi_resonance']
    res_high = syn.feel('joy', 0.9)['psi_resonance']
    print(f"  Resonance: 0.1->{res_low:.4f}  0.5->{res_mid:.4f}  0.9->{res_high:.4f}")
    assert res_mid >= res_low, "Balance point should have highest resonance"
    assert res_mid >= res_high, "Balance point should have highest resonance"
    print("  PASSED")

    # --- Demo: Emotion spectrum ---
    print("\n[Demo] Emotion Spectrum")
    print(syn.emotion_spectrum())

    # --- Demo: Contrast two emotions ---
    print("\n[Demo] Contrast: joy vs despair @ 0.9")
    for emo in ['joy', 'despair']:
        print(syn.render_ascii(emo, 0.9))

    print("\n" + "=" * 60)
    print("  All tests PASSED")
    print("=" * 60)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
