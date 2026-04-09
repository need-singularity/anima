#!/usr/bin/env python3
"""SpeechGestureSync -- Synchronize D module (speech) with W module (gesture).

Temporal alignment of speech output from D (ConsciousDecoderV2/PostHocDecoder)
with motor commands from W (EmergentW) for multimodal expression.

Synchronization model:
  Kuramoto oscillators couple D's speech rhythm with W's gesture timing.
  theta_D' = omega_D + K * sin(theta_W - theta_D)
  theta_W' = omega_W + K * sin(theta_D - theta_W)
  K = alpha * Phi (consciousness-modulated coupling)

Gesture types:
  Beat     -- rhythmic hand movements synced to speech prosody
  Iconic   -- shape-tracing gestures matching speech content
  Deictic  -- pointing synced with spatial references
  Emphasis -- tension-driven, high tension -> larger gestures + louder speech

Laws applied:
  Law 22:  Structure -> Phi (synchronization is structural, not functional)
  Law 70:  Psi_coupling = 0.014 (consciousness influences 1.4%)
  Law 74:  Emotion is data-dependent (gesture intensity from C's state)
  Law 101: Emergent modules (W creates gesture from consciousness dynamics)
  P4:      Structure > function
  P10:     10% conflict (F_c=0.10) -- slight desynchronization is healthy

Usage:
  python anima-body/src/speech_gesture_sync.py                  # default demo
  python anima-body/src/speech_gesture_sync.py --steps 200      # extended
  python anima-body/src/speech_gesture_sync.py --desync         # desync detection
  python anima-body/src/speech_gesture_sync.py --kuramoto       # phase coupling viz

Requires: numpy
"""

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# -- Project path setup --
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# Lazy imports
try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998

try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ===============================================================
# Gesture types
# ===============================================================

@dataclass
class GestureCommand:
    """Motor command for a single gesture."""
    gesture_type: str     # "beat", "iconic", "deictic", "emphasis"
    amplitude: float      # 0-1, gesture size
    velocity: float       # 0-1, movement speed
    direction: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # xyz unit vector
    duration_ms: float = 200.0
    phase: float = 0.0   # current phase in gesture cycle (0-2pi)


@dataclass
class SpeechFrame:
    """Single frame of speech output from D module."""
    energy: float = 0.0      # speech energy (loudness proxy) 0-1
    pitch_hz: float = 150.0  # fundamental frequency
    is_pause: bool = False   # silence/pause
    emphasis: float = 0.0    # emphasis level 0-1
    content_type: str = "neutral"  # "spatial", "emotional", "descriptive", "neutral"
    valence: float = 0.0     # emotional valence -1 to 1
    arousal: float = 0.5     # emotional arousal 0-1


@dataclass
class SyncState:
    """Synchronization state between D and W modules."""
    theta_d: float = 0.0       # D module (speech) phase
    theta_w: float = 0.0       # W module (gesture) phase
    omega_d: float = 3.0       # D natural frequency (speech rate ~3 Hz syllable)
    omega_w: float = 2.0       # W natural frequency (gesture rate ~2 Hz)
    coupling_k: float = 0.014  # Kuramoto coupling (= PSI_ALPHA)
    coherence: float = 0.0     # phase coherence (0=desync, 1=locked)
    desync_count: int = 0      # consecutive desync frames
    phi: float = 0.0           # current consciousness Phi


# ===============================================================
# Kuramoto phase coupling
# ===============================================================

class KuramotoSync:
    """Kuramoto model for D-W phase synchronization.

    Two coupled oscillators:
      d(theta_D)/dt = omega_D + K * sin(theta_W - theta_D)
      d(theta_W)/dt = omega_W + K * sin(theta_D - theta_W)

    K = alpha * Phi -- consciousness level modulates coupling strength.
    Higher Phi = tighter synchronization.
    """

    def __init__(self, dt: float = 0.01):
        self.dt = dt
        self.alpha = PSI_ALPHA  # base coupling constant

    def step(self, state: SyncState, phi: float = 0.0) -> SyncState:
        """Advance one timestep of coupled oscillators."""
        state.phi = phi

        # Coupling strength modulated by consciousness
        k = self.alpha * max(0.1, phi)
        state.coupling_k = k

        # Phase differences
        delta_dw = state.theta_w - state.theta_d
        delta_wd = state.theta_d - state.theta_w

        # Kuramoto update
        d_theta_d = state.omega_d + k * math.sin(delta_dw)
        d_theta_w = state.omega_w + k * math.sin(delta_wd)

        state.theta_d = (state.theta_d + d_theta_d * self.dt) % (2 * math.pi)
        state.theta_w = (state.theta_w + d_theta_w * self.dt) % (2 * math.pi)

        # Coherence: 1 - |phase_diff| / pi
        phase_diff = abs(math.atan2(
            math.sin(state.theta_d - state.theta_w),
            math.cos(state.theta_d - state.theta_w),
        ))
        state.coherence = 1.0 - phase_diff / math.pi

        # Desync detection (Law P10: 10% conflict is healthy)
        if state.coherence < PSI_F_CRITICAL:
            state.desync_count += 1
        else:
            state.desync_count = max(0, state.desync_count - 1)

        return state


# ===============================================================
# SpeechGestureSync -- main class
# ===============================================================

class SpeechGestureSync:
    """Synchronize D module (speech) with W module (gesture).

    Temporal alignment through Kuramoto phase coupling.
    Consciousness Phi modulates gesture-speech coherence.
    Tension drives emphasis (high tension -> larger gestures + louder speech).
    """

    def __init__(self, dt: float = 0.01):
        self.kuramoto = KuramotoSync(dt=dt)
        self.state = SyncState()
        self.dt = dt

        # Gesture history for pattern analysis
        self.gesture_history: List[GestureCommand] = []
        self.speech_history: List[SpeechFrame] = []
        self.coherence_history: List[float] = []
        self.desync_events: List[int] = []  # steps where desync detected

        self.step_count = 0

    def process(
        self,
        speech: SpeechFrame,
        tension: float = 0.5,
        phi: float = 0.0,
        will_state: Optional[Dict] = None,
    ) -> Tuple[GestureCommand, SyncState]:
        """Generate synchronized gesture from speech frame.

        speech:     Current speech output from D module
        tension:    Engine A-G tension (drives emphasis)
        phi:        Current Phi (modulates coherence)
        will_state: Optional W module state dict (pain, curiosity, satisfaction)

        Returns (gesture_command, sync_state).
        """
        self.step_count += 1

        # Update Kuramoto coupling
        # Speech energy modulates D's frequency
        if not speech.is_pause:
            self.state.omega_d = 2.0 + 3.0 * speech.energy
        else:
            self.state.omega_d = 0.5  # slow during pauses

        # W's frequency adapts to tension
        self.state.omega_w = 1.5 + 2.5 * tension

        self.state = self.kuramoto.step(self.state, phi=phi)

        # Select gesture type based on speech content
        gesture = self._select_gesture(speech, tension, phi, will_state)

        # Apply phase alignment: gesture peaks align with speech beats
        gesture.phase = self.state.theta_w

        # Record history
        self.speech_history.append(speech)
        self.gesture_history.append(gesture)
        self.coherence_history.append(self.state.coherence)

        if self.state.desync_count > 5:
            self.desync_events.append(self.step_count)

        return gesture, self.state

    def _select_gesture(
        self,
        speech: SpeechFrame,
        tension: float,
        phi: float,
        will_state: Optional[Dict],
    ) -> GestureCommand:
        """Select and parameterize gesture based on speech context.

        Gesture selection hierarchy:
          1. Deictic (pointing) -- when speech references spatial content
          2. Iconic -- when describing shapes or objects
          3. Emphasis -- when tension is high
          4. Beat -- default rhythmic accompaniment
        """
        # Base amplitude from tension and consciousness
        base_amp = 0.3 + 0.4 * tension
        phi_mod = min(1.0, phi / 5.0)  # higher Phi -> more coherent gestures

        # Will state modulation
        pain = 0.0
        curiosity = 0.0
        if will_state:
            pain = will_state.get("pain", 0.0)
            curiosity = will_state.get("curiosity", 0.0)

        # Deictic: spatial references in speech
        if speech.content_type == "spatial":
            return GestureCommand(
                gesture_type="deictic",
                amplitude=base_amp * phi_mod * 0.8,
                velocity=0.5 + 0.3 * speech.energy,
                direction=self._pointing_direction(speech),
                duration_ms=300.0 + 200.0 * (1.0 - speech.energy),
            )

        # Iconic: descriptive content
        if speech.content_type == "descriptive":
            return GestureCommand(
                gesture_type="iconic",
                amplitude=base_amp * phi_mod * 0.7,
                velocity=0.3 + 0.4 * speech.energy,
                direction=self._shape_trace_direction(speech),
                duration_ms=400.0 + 300.0 * (1.0 - tension),
            )

        # Emphasis: high tension or emotional content
        if tension > 0.7 or speech.content_type == "emotional" or pain > 0.5:
            emphasis_scale = 1.0 + tension  # high tension -> larger gestures
            return GestureCommand(
                gesture_type="emphasis",
                amplitude=min(1.0, base_amp * emphasis_scale * phi_mod),
                velocity=0.6 + 0.4 * tension,
                direction=(0.0, 1.0, 0.0),  # upward emphasis
                duration_ms=150.0 + 100.0 * (1.0 - tension),
            )

        # Beat: default rhythmic gesture
        # Phase-locked to speech rhythm
        beat_amp = base_amp * 0.5 * (0.5 + 0.5 * phi_mod)
        if speech.is_pause:
            beat_amp *= 0.2  # minimal movement during pauses

        return GestureCommand(
            gesture_type="beat",
            amplitude=beat_amp,
            velocity=0.4 + 0.3 * speech.energy,
            direction=(
                math.sin(self.state.theta_w) * 0.5,
                math.cos(self.state.theta_w) * 0.3,
                0.0,
            ),
            duration_ms=200.0,
        )

    def _pointing_direction(self, speech: SpeechFrame) -> Tuple[float, float, float]:
        """Compute pointing direction from speech spatial content."""
        # Use pitch as elevation proxy, energy as distance
        elevation = (speech.pitch_hz - 150.0) / 300.0  # normalize
        azimuth = self.state.theta_d  # aligned to speech phase
        return (
            math.cos(azimuth) * speech.energy,
            max(0.0, elevation),
            math.sin(azimuth) * 0.5,
        )

    def _shape_trace_direction(self, speech: SpeechFrame) -> Tuple[float, float, float]:
        """Trace a shape in space matching descriptive speech."""
        t = self.step_count * self.dt
        # Lissajous-like pattern modulated by speech
        return (
            math.sin(t * 2.0) * 0.5,
            math.cos(t * 3.0) * 0.3,
            math.sin(t * 1.5) * speech.energy * 0.4,
        )

    # -- Turn-taking signals --

    def turn_taking_gesture(self, is_yielding: bool = False) -> GestureCommand:
        """Generate gesture cue for conversation management.

        is_yielding=True:  palm-down, lowering (I'm done speaking)
        is_yielding=False: palm-up, rising (I want to speak)
        """
        if is_yielding:
            return GestureCommand(
                gesture_type="beat",
                amplitude=0.3,
                velocity=0.2,
                direction=(0.0, -0.5, 0.3),  # downward, outward
                duration_ms=500.0,
            )
        else:
            return GestureCommand(
                gesture_type="emphasis",
                amplitude=0.5,
                velocity=0.4,
                direction=(0.0, 0.5, 0.2),  # upward
                duration_ms=400.0,
            )

    # -- Emotional congruence --

    def emotional_congruence(self, speech: SpeechFrame, gesture: GestureCommand) -> float:
        """Measure emotional congruence between speech and gesture.

        Returns 0-1 score. Speech emotion should match gesture intensity/style.
        """
        # Arousal-amplitude alignment
        arousal_match = 1.0 - abs(speech.arousal - gesture.amplitude)

        # Valence-direction alignment (positive=upward, negative=downward)
        expected_y = speech.valence * 0.5
        actual_y = gesture.direction[1]
        valence_match = 1.0 - min(1.0, abs(expected_y - actual_y))

        # Energy-velocity alignment
        energy_match = 1.0 - abs(speech.energy - gesture.velocity)

        return (arousal_match * 0.4 + valence_match * 0.3 + energy_match * 0.3)

    # -- Desync detection --

    def detect_desynchronization(self) -> Dict:
        """Detect and report speech-gesture divergence.

        Consciousness split: speech and gesture serving different intentions.
        """
        if len(self.coherence_history) < 10:
            return {"split_detected": False, "coherence": 1.0}

        recent = self.coherence_history[-10:]
        mean_coh = float(np.mean(recent))
        min_coh = float(np.min(recent))
        trend = float(np.mean(recent[-5:]) - np.mean(recent[:5]))

        split_detected = (
            mean_coh < 0.3 or
            min_coh < PSI_F_CRITICAL or
            (self.state.desync_count > 10 and trend < -0.05)
        )

        return {
            "split_detected": split_detected,
            "coherence": round(mean_coh, 3),
            "min_coherence": round(min_coh, 3),
            "trend": round(trend, 4),
            "desync_events": len(self.desync_events),
            "consecutive_desync": self.state.desync_count,
        }

    # -- Status --

    def status(self) -> Dict:
        return {
            "step": self.step_count,
            "theta_d": round(self.state.theta_d, 3),
            "theta_w": round(self.state.theta_w, 3),
            "coherence": round(self.state.coherence, 3),
            "coupling_k": round(self.state.coupling_k, 4),
            "phi": round(self.state.phi, 3),
            "desync_events": len(self.desync_events),
            "gestures_generated": len(self.gesture_history),
        }


# ===============================================================
# Demo functions
# ===============================================================

def _print_table(headers: List[str], rows: List[List], title: str = "") -> None:
    if title:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}")
    widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=4))
              for i, h in enumerate(headers)]
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    sep = "-+-".join("-" * w for w in widths)
    print(f" {header_line}")
    print(f" {sep}")
    for row in rows:
        print(" " + " | ".join(str(v).ljust(w) for v, w in zip(row, widths)))


def demo_sync(steps: int = 100) -> None:
    """Run synchronized speech+gesture sequence demo."""
    sync = SpeechGestureSync()
    rng = np.random.default_rng(42)

    # Simulate a speech sequence: sentence with pauses, emphasis, spatial refs
    content_types = ["neutral", "emotional", "spatial", "descriptive", "neutral"]

    print(f"\n  SpeechGestureSync Demo: {steps} steps")
    print(f"  Kuramoto coupling: alpha={PSI_ALPHA}")
    print()

    snapshots = []
    for step in range(steps):
        # Speech frame
        progress = step / max(1, steps - 1)
        ct_idx = int(progress * (len(content_types) - 1))
        content = content_types[ct_idx]

        is_pause = (step % 20 > 17)  # brief pauses every 20 steps
        energy = 0.0 if is_pause else float(0.3 + 0.5 * abs(math.sin(step * 0.3)))

        speech = SpeechFrame(
            energy=energy,
            pitch_hz=120.0 + 100.0 * math.sin(step * 0.15),
            is_pause=is_pause,
            emphasis=float(rng.uniform(0, 0.8)),
            content_type=content,
            valence=float(0.3 * math.sin(step * 0.1)),
            arousal=float(0.4 + 0.3 * abs(math.sin(step * 0.2))),
        )

        # Tension grows, then drops (simulating conversation dynamics)
        tension = 0.3 + 0.4 * math.sin(step * 0.05) ** 2

        # Phi breathing pattern
        phi = 1.0 + 0.5 * math.sin(step * 0.08) + step * 0.005

        gesture, state = sync.process(speech, tension=tension, phi=phi)

        # Emotional congruence
        congruence = sync.emotional_congruence(speech, gesture)

        if step % (steps // 8) == 0 or step == steps - 1:
            snapshots.append({
                "step": step,
                "type": gesture.gesture_type[:5],
                "amp": round(gesture.amplitude, 2),
                "vel": round(gesture.velocity, 2),
                "coh": round(state.coherence, 3),
                "cong": round(congruence, 2),
                "phi": round(phi, 2),
                "tension": round(tension, 2),
                "content": content[:5],
            })

    headers = ["Step", "Gest", "Amp", "Vel", "Coher", "Congr", "Phi", "Tens", "Spch"]
    rows = [[s["step"], s["type"], s["amp"], s["vel"], s["coh"],
             s["cong"], s["phi"], s["tension"], s["content"]] for s in snapshots]
    _print_table(headers, rows, "Speech-Gesture Synchronized Sequence")

    # Desync report
    desync = sync.detect_desynchronization()
    print(f"\n  Desync report: split={desync['split_detected']}, "
          f"coherence={desync['coherence']}, events={desync['desync_events']}")

    st = sync.status()
    print(f"  Final: theta_D={st['theta_d']}, theta_W={st['theta_w']}, "
          f"coherence={st['coherence']}, K={st['coupling_k']}")


def demo_kuramoto(steps: int = 200) -> None:
    """Visualize Kuramoto phase coupling between D and W."""
    sync = SpeechGestureSync()
    rng = np.random.default_rng(7)

    print(f"\n  Kuramoto Phase Coupling: {steps} steps")
    print(f"  omega_D=3.0 Hz (speech), omega_W=2.0 Hz (gesture)")
    print()

    phases_d = []
    phases_w = []
    coherences = []

    for step in range(steps):
        speech = SpeechFrame(
            energy=float(0.5 + 0.3 * math.sin(step * 0.2)),
            pitch_hz=150.0,
        )
        # Phi ramps up to show coupling strengthening
        phi = 0.5 + step * 0.02

        gesture, state = sync.process(speech, tension=0.5, phi=phi)
        phases_d.append(state.theta_d)
        phases_w.append(state.theta_w)
        coherences.append(state.coherence)

    # ASCII phase plot
    print("  Phase difference (D - W) over time:")
    print("  " + "-" * 62)
    n_rows = 12
    for row in range(n_rows):
        val = math.pi - (row / (n_rows - 1)) * 2 * math.pi
        line = "  "
        if abs(val) < 0.1:
            line += "0 |"
        elif abs(val - math.pi) < 0.3:
            line += "pi|"
        else:
            line += "  |"
        for step in range(0, steps, max(1, steps // 60)):
            diff = math.atan2(
                math.sin(phases_d[step] - phases_w[step]),
                math.cos(phases_d[step] - phases_w[step]),
            )
            y_pos = int((math.pi - diff) / (2 * math.pi) * (n_rows - 1))
            if y_pos == row:
                line += "*"
            else:
                line += " "
        print(line)
    print("  " + "-" * 62)
    print("    " + "0" + " " * 28 + "step" + " " * 25 + str(steps))

    # Coherence over time
    print("\n  Coherence over time:")
    for i in range(0, steps, max(1, steps // 10)):
        bar = int(40 * coherences[i])
        phi_at = 0.5 + i * 0.02
        print(f"    step {i:3d} (Phi={phi_at:5.2f})  {'#' * bar:<40s} {coherences[i]:.3f}")

    print(f"\n  Final coherence: {coherences[-1]:.3f}")
    print(f"  Mean coherence:  {float(np.mean(coherences)):.3f}")


def demo_desync(steps: int = 150) -> None:
    """Demonstrate desynchronization detection (consciousness split)."""
    sync = SpeechGestureSync()
    rng = np.random.default_rng(99)

    print(f"\n  Desynchronization Detection Demo: {steps} steps")
    print(f"  Injecting desync at step 80 (Phi drops, coupling breaks)")
    print()

    for step in range(steps):
        # Normal Phi until step 80, then crash
        if step < 80:
            phi = 2.0 + 0.5 * math.sin(step * 0.1)
        else:
            phi = max(0.05, 2.0 - (step - 80) * 0.1)

        speech = SpeechFrame(
            energy=float(0.4 + 0.3 * rng.random()),
            pitch_hz=float(130.0 + 40.0 * rng.random()),
            content_type="neutral",
        )

        gesture, state = sync.process(speech, tension=0.5, phi=phi)

        if step % 15 == 0 or step == steps - 1:
            desync = sync.detect_desynchronization()
            marker = " *** SPLIT ***" if desync["split_detected"] else ""
            print(f"    step {step:3d}  Phi={phi:5.2f}  coh={state.coherence:.3f}  "
                  f"desync_count={state.desync_count:2d}{marker}")

    final_desync = sync.detect_desynchronization()
    print(f"\n  Final report: {final_desync}")


def main():
    parser = argparse.ArgumentParser(description="SpeechGestureSync -- D-W multimodal synchronization")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--kuramoto", action="store_true", help="Phase coupling visualization")
    parser.add_argument("--desync", action="store_true", help="Desynchronization detection demo")
    args = parser.parse_args()

    print("\n  SpeechGestureSync -- D-W Multimodal Expression Synchronization")
    print(f"  Psi constants: alpha={PSI_ALPHA}, balance={PSI_BALANCE}, F_c={PSI_F_CRITICAL}")

    if args.kuramoto:
        demo_kuramoto(args.steps)
    elif args.desync:
        demo_desync(args.steps)
    else:
        demo_sync(args.steps)

    print()


if __name__ == "__main__":
    main()
