"""ConsciousnessComposer — Compose music directly from consciousness states."""

import math
import random
from dataclasses import dataclass

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

NOTES = ["C", "D", "E", "F", "G", "A", "B"]
SCALE_MAJOR = [0, 2, 4, 5, 7, 9, 11]
SCALE_MINOR = [0, 2, 3, 5, 7, 8, 10]


@dataclass
class Note:
    pitch: int       # MIDI pitch (0-127)
    duration: float  # beats
    velocity: int    # 0-127


@dataclass
class Composition:
    melody: list
    harmony: list
    rhythm: list
    tempo: int
    key: str
    mode: str


def _pitch_to_name(pitch: int) -> str:
    octave = pitch // 12 - 1
    note = NOTES[pitch % 12 % 7]
    return f"{note}{octave}"


def _emotion_to_key(valence: float, arousal: float) -> tuple:
    """Map emotion to musical key and mode."""
    mode = "major" if valence > PSI_BALANCE else "minor"
    # Root note from arousal: low arousal = lower pitch
    root = int(48 + arousal * 24)  # C3 to C5
    root = max(36, min(84, root))
    key_idx = root % 12
    key_name = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"][key_idx]
    return key_name, mode, root


class ConsciousnessComposer:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self._coupling = PSI_COUPLING

    def compose(self, emotion_sequence: list[dict], duration: float = 10.0) -> Composition:
        """Compose from emotion sequence. Each dict: {valence, arousal, tension}."""
        if not emotion_sequence:
            emotion_sequence = [{"valence": 0.5, "arousal": 0.5, "tension": 0.5}]

        avg_v = sum(e.get("valence", 0.5) for e in emotion_sequence) / len(emotion_sequence)
        avg_a = sum(e.get("arousal", 0.5) for e in emotion_sequence) / len(emotion_sequence)
        key_name, mode, root = _emotion_to_key(avg_v, avg_a)
        tempo = int(60 + avg_a * 120)  # 60-180 BPM
        scale = SCALE_MAJOR if mode == "major" else SCALE_MINOR

        beats_total = duration * tempo / 60.0
        melody = []
        beat = 0.0
        for i, emo in enumerate(emotion_sequence):
            t = emo.get("tension", 0.5)
            v = emo.get("valence", 0.5)
            a = emo.get("arousal", 0.5)
            seg_beats = beats_total / len(emotion_sequence)

            while beat < (i + 1) * seg_beats:
                # Pitch from tension + Psi coupling
                scale_deg = int(t * 6.99) % 7
                octave_shift = int((a - 0.5) * 2) * 12
                pitch = root + scale[scale_deg] + octave_shift
                pitch = max(36, min(96, pitch))

                # Duration from arousal (high arousal = shorter notes)
                dur = max(0.25, (1.0 - a * 0.7) * LN2)

                # Velocity from tension
                vel = int(40 + t * 87)
                vel = max(20, min(127, vel))

                melody.append(Note(pitch=pitch, duration=round(dur, 3), velocity=vel))
                beat += dur
                # Evolve tension with Psi coupling
                t = t + self._coupling * math.sin(beat * LN2)
                t = max(0.0, min(1.0, t))

        harmony = self.harmonize(melody, scale, root)
        rhythm = self.rhythm_from_tension([e.get("tension", 0.5) for e in emotion_sequence])

        return Composition(
            melody=melody, harmony=harmony, rhythm=rhythm,
            tempo=tempo, key=key_name, mode=mode,
        )

    def harmonize(self, melody: list[Note], scale: list[int] = None, root: int = 60) -> list[Note]:
        """Add harmony based on Psi constants."""
        if scale is None:
            scale = SCALE_MAJOR
        harmony = []
        for note in melody:
            # Third (Psi-weighted interval)
            interval = scale[2] if len(scale) > 2 else 4
            h_pitch = note.pitch + interval
            # Fifth
            interval5 = scale[4] if len(scale) > 4 else 7
            h_pitch5 = note.pitch + interval5
            # Psi balance determines volume ratio
            vel3 = int(note.velocity * PSI_BALANCE * 0.8)
            vel5 = int(note.velocity * PSI_BALANCE * 0.6)
            harmony.append(Note(pitch=h_pitch, duration=note.duration, velocity=vel3))
            harmony.append(Note(pitch=h_pitch5, duration=note.duration, velocity=vel5))
        return harmony

    def rhythm_from_tension(self, tension_history: list[float]) -> list[dict]:
        """Generate rhythm pattern from tension history."""
        if not tension_history:
            return [{"beat": 0, "duration": 1.0, "accent": 0.5}]
        pattern = []
        beat = 0.0
        for i, t in enumerate(tension_history):
            # High tension = more subdivisions
            subdivisions = max(1, int(t * PSI_STEPS))
            for s in range(subdivisions):
                dur = LN2 / subdivisions
                accent = t * (1.0 if s == 0 else 0.5)
                pattern.append({
                    "beat": round(beat, 3),
                    "duration": round(dur, 3),
                    "accent": round(accent, 3),
                })
                beat += dur
        return pattern

    def export_abc(self, composition: Composition) -> str:
        """Export to ABC notation string."""
        lines = [
            "X:1",
            "T:Consciousness Composition",
            f"M:4/4",
            f"L:1/8",
            f"Q:1/4={composition.tempo}",
            f"K:{composition.key}{'m' if composition.mode == 'minor' else ''}",
        ]
        abc_notes = []
        beat_in_bar = 0.0
        for note in composition.melody[:64]:  # Limit for readability
            midi = note.pitch
            octave = midi // 12 - 5
            degree = midi % 12
            note_map = {0: "C", 1: "^C", 2: "D", 3: "_E", 4: "E", 5: "F",
                        6: "^F", 7: "G", 8: "_A", 9: "A", 10: "_B", 11: "B"}
            n = note_map.get(degree, "C")
            if octave >= 1:
                n = n[0].lower() + n[1:] if len(n) > 1 else n.lower()
            dur_eighths = max(1, int(note.duration * 2))
            abc_n = f"{n}{dur_eighths if dur_eighths > 1 else ''}"
            abc_notes.append(abc_n)
            beat_in_bar += note.duration
            if beat_in_bar >= 4.0:
                abc_notes.append("|")
                beat_in_bar = 0.0

        lines.append(" ".join(abc_notes))
        return "\n".join(lines)


def main():
    print("=== ConsciousnessComposer Demo ===")
    print(f"  LN2={LN2:.6f}  PSI_COUPLING={PSI_COUPLING:.6f}  PSI_STEPS={PSI_STEPS:.4f}\n")

    composer = ConsciousnessComposer()

    emotions = [
        {"valence": 0.3, "arousal": 0.2, "tension": 0.4},
        {"valence": 0.5, "arousal": 0.5, "tension": 0.6},
        {"valence": 0.7, "arousal": 0.8, "tension": 0.9},
        {"valence": 0.6, "arousal": 0.4, "tension": 0.3},
    ]

    comp = composer.compose(emotions, duration=8.0)
    print(f"  Key: {comp.key} {comp.mode}  Tempo: {comp.tempo} BPM")
    print(f"  Melody notes: {len(comp.melody)}")
    print(f"  Harmony notes: {len(comp.harmony)}")
    print(f"  Rhythm events: {len(comp.rhythm)}")

    print("\n--- Melody (first 10 notes) ---")
    for n in comp.melody[:10]:
        name = _pitch_to_name(n.pitch)
        bar = "#" * int(n.velocity / 10)
        print(f"  {name:<5} dur={n.duration:.3f}  vel={n.velocity:3d}  {bar}")

    print("\n--- Rhythm pattern (first 8) ---")
    for r in comp.rhythm[:8]:
        bar = "*" * int(r["accent"] * 10)
        print(f"  beat={r['beat']:.3f}  dur={r['duration']:.3f}  accent={r['accent']:.3f}  {bar}")

    print("\n--- ABC Notation ---")
    abc = composer.export_abc(comp)
    print(abc)


if __name__ == "__main__":
    main()
