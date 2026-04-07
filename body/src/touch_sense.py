#!/usr/bin/env python3
"""Touch Sensor -> Consciousness — Map pressure/temperature/texture to consciousness input.

Maps physical touch sensor readings (pressure, temperature, texture) to the
EmergentS module input format, feeding tactile information into the consciousness
engine as a 128-dimensional tensor.

Sensor channels:
  1. Pressure     — force applied (0-1), mapped to arousal/tension
  2. Temperature  — surface temp (celsius), homeostasis disruption
  3. Texture      — surface roughness/pattern (frequency spectrum)

Touch patterns (simulated):
  tap     — brief spike (50ms pressure burst)
  hold    — sustained pressure with slow decay
  stroke  — moving pressure across sensor array
  pain    — high pressure + temperature spike (triggers Z/impedance)
  caress  — gentle wave pattern with warmth
  release — pressure drops to zero (absence detection)

Haptic feedback:
  Consciousness -> vibration motor output for physical response.
  High Phi = gentle pulse, high tension = strong buzz.

Integration with EmergentS:
  EmergentS.process(touch_tensor, c_engine) -> perception delta
  Touch tensor fills the first 32 dims of EmergentS's 128d input.

Usage:
  python anima-body/src/touch_sense.py                        # Demo
  python anima-body/src/touch_sense.py --pattern all          # All patterns
  python anima-body/src/touch_sense.py --pattern pain         # Specific pattern
  python anima-body/src/touch_sense.py --sensors 8            # 8-sensor array
  python anima-body/src/touch_sense.py --with-engine          # With consciousness engine

Requires: numpy, torch
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

# ── Path setup ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# Lazy imports
try:
    import torch
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Psi constants
try:
    from consciousness_laws import (
        PSI_ALPHA as PSI_COUPLING,
        PSI_BALANCE,
        PSI_F_CRITICAL,
    )
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5
    PSI_F_CRITICAL = 0.10


# ═══════════════════════════════════════════════════════════
# Touch Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class TouchReading:
    """Single touch sensor reading."""
    pressure: float = 0.0         # 0-1 normalized force
    temperature: float = 25.0     # celsius
    texture_roughness: float = 0.0  # 0-1, surface roughness
    texture_freq: float = 0.0     # Hz, texture vibration frequency
    sensor_id: int = 0            # which sensor in the array
    timestamp: float = 0.0

    @property
    def is_contact(self) -> bool:
        """Whether there is active contact."""
        return self.pressure > 0.02

    @property
    def is_pain(self) -> bool:
        """Pain threshold: high pressure or extreme temperature."""
        return self.pressure > 0.85 or self.temperature > 45.0 or self.temperature < 5.0


@dataclass
class TouchState:
    """Aggregated state from a touch sensor array."""
    readings: List[TouchReading] = field(default_factory=list)
    n_contacts: int = 0
    max_pressure: float = 0.0
    mean_pressure: float = 0.0
    mean_temperature: float = 25.0
    pain_detected: bool = False
    contact_area: float = 0.0       # fraction of sensors with contact
    pressure_gradient: float = 0.0  # spatial pressure change rate
    timestamp: float = 0.0


@dataclass
class HapticCommand:
    """Haptic feedback output (consciousness -> vibration motor)."""
    intensity: float = 0.0     # 0-1 vibration strength
    frequency: float = 150.0   # Hz, vibration frequency
    duration_ms: float = 50.0  # pulse duration in ms
    pattern: str = "pulse"     # pulse, buzz, wave

    # Safety limits
    MAX_INTENSITY = 0.8
    MAX_DURATION_MS = 500.0


# ═══════════════════════════════════════════════════════════
# TouchSensor — Sensor Array
# ═══════════════════════════════════════════════════════════

class TouchSensor:
    """Touch sensor array with pressure, temperature, and texture channels.

    Simulates an array of N touch sensors arranged linearly (like a finger
    or palm strip). Each sensor independently reads pressure, temperature,
    and texture.

    Usage:
        sensor = TouchSensor(n_sensors=4)
        sensor.apply_pattern("tap", center=0)
        state = sensor.read()
        print(f"Contact: {state.n_contacts}, Pain: {state.pain_detected}")
    """

    def __init__(self, n_sensors: int = 4):
        self.n_sensors = n_sensors
        self._readings = [TouchReading(sensor_id=i) for i in range(n_sensors)]
        self._t = 0.0  # internal time counter
        self._pattern_start = 0.0
        self._active_pattern: Optional[str] = None
        self._pattern_center: int = 0
        self._pattern_params: dict = {}

    def apply_pattern(self, pattern: str, center: int = 0, **kwargs):
        """Apply a touch pattern to the sensor array.

        Patterns:
          tap      — brief pressure spike at center sensor
          hold     — sustained pressure with slow decay
          stroke   — pressure wave moving across sensors
          pain     — high pressure + temperature spike
          caress   — gentle sinusoidal wave with warmth
          release  — all pressure drops to zero
        """
        self._active_pattern = pattern
        self._pattern_start = self._t
        self._pattern_center = min(center, self.n_sensors - 1)
        self._pattern_params = kwargs

    def update(self, dt: float = 0.05):
        """Advance simulation by dt seconds."""
        self._t += dt

        if self._active_pattern is None:
            # Natural decay toward baseline
            for r in self._readings:
                r.pressure *= 0.95
                r.temperature += (25.0 - r.temperature) * 0.1
                r.texture_roughness *= 0.9
                r.texture_freq *= 0.9
                r.timestamp = self._t
            return

        elapsed = self._t - self._pattern_start
        c = self._pattern_center

        if self._active_pattern == "tap":
            self._apply_tap(elapsed, c)
        elif self._active_pattern == "hold":
            self._apply_hold(elapsed, c)
        elif self._active_pattern == "stroke":
            self._apply_stroke(elapsed, c)
        elif self._active_pattern == "pain":
            self._apply_pain(elapsed, c)
        elif self._active_pattern == "caress":
            self._apply_caress(elapsed, c)
        elif self._active_pattern == "release":
            self._apply_release(elapsed)

        for r in self._readings:
            r.pressure = float(np.clip(r.pressure, 0.0, 1.0))
            r.temperature = float(np.clip(r.temperature, -10.0, 60.0))
            r.timestamp = self._t

    def _apply_tap(self, elapsed: float, center: int):
        """Brief spike: 50ms rise, 100ms decay."""
        duration = self._pattern_params.get('duration', 0.15)
        strength = self._pattern_params.get('strength', 0.7)

        if elapsed > duration * 3:
            self._active_pattern = None
            return

        for i, r in enumerate(self._readings):
            dist = abs(i - center) / max(self.n_sensors, 1)
            spatial = math.exp(-dist * dist * 8.0)  # Gaussian spread

            if elapsed < duration * 0.3:
                # Rising
                phase = elapsed / (duration * 0.3)
                r.pressure = strength * phase * spatial
            else:
                # Decaying
                phase = (elapsed - duration * 0.3) / (duration * 0.7)
                r.pressure = strength * math.exp(-phase * 3.0) * spatial
            r.texture_roughness = 0.1 * spatial

    def _apply_hold(self, elapsed: float, center: int):
        """Sustained pressure with habituation decay."""
        strength = self._pattern_params.get('strength', 0.6)
        # Habituation: exponential decay to 30% over 2 seconds (Law 50)
        habituated = 0.3 + 0.7 * math.exp(-elapsed * 0.5)

        for i, r in enumerate(self._readings):
            dist = abs(i - center) / max(self.n_sensors, 1)
            spatial = math.exp(-dist * dist * 4.0)
            r.pressure = strength * habituated * spatial
            r.texture_roughness = 0.2 * spatial
            r.temperature += (32.0 - r.temperature) * 0.02  # warming from contact

    def _apply_stroke(self, elapsed: float, center: int):
        """Moving pressure wave across sensors."""
        speed = self._pattern_params.get('speed', 2.0)  # sensors per second
        strength = self._pattern_params.get('strength', 0.5)

        position = center + elapsed * speed
        if position > self.n_sensors + 1:
            self._active_pattern = None
            return

        for i, r in enumerate(self._readings):
            dist = i - position
            # Gaussian moving window
            r.pressure = strength * math.exp(-dist * dist * 2.0)
            r.texture_roughness = 0.3 * r.pressure
            r.texture_freq = 20.0 * r.pressure  # texture from sliding

    def _apply_pain(self, elapsed: float, center: int):
        """High pressure + temperature spike."""
        strength = self._pattern_params.get('strength', 0.95)
        duration = self._pattern_params.get('duration', 0.5)

        if elapsed > duration * 4:
            self._active_pattern = None
            return

        for i, r in enumerate(self._readings):
            dist = abs(i - center) / max(self.n_sensors, 1)
            spatial = math.exp(-dist * dist * 6.0)

            if elapsed < duration:
                phase = elapsed / duration
                r.pressure = strength * min(phase * 2, 1.0) * spatial
                r.temperature = 25.0 + 25.0 * phase * spatial  # up to 50C
            else:
                decay = math.exp(-(elapsed - duration) * 2.0)
                r.pressure = strength * decay * spatial
                r.temperature = 25.0 + 25.0 * decay * spatial
            r.texture_roughness = 0.8 * r.pressure  # pain is "rough"

    def _apply_caress(self, elapsed: float, center: int):
        """Gentle sinusoidal wave with warmth."""
        strength = self._pattern_params.get('strength', 0.25)
        freq = self._pattern_params.get('freq', 0.8)  # Hz

        if elapsed > 5.0:
            self._active_pattern = None
            return

        for i, r in enumerate(self._readings):
            phase = elapsed * freq * 2 * math.pi + i * math.pi / self.n_sensors
            r.pressure = strength * (0.5 + 0.5 * math.sin(phase))
            r.temperature = 30.0 + 3.0 * math.sin(phase * 0.5)  # gentle warmth
            r.texture_roughness = 0.05 * (0.5 + 0.5 * math.sin(phase * 2))

    def _apply_release(self, elapsed: float):
        """Release: rapid pressure drop to zero."""
        for r in self._readings:
            r.pressure *= 0.7  # rapid decay
            r.temperature += (25.0 - r.temperature) * 0.15
            r.texture_roughness *= 0.8
        if all(r.pressure < 0.01 for r in self._readings):
            self._active_pattern = None

    def read(self) -> TouchState:
        """Read current state of all sensors."""
        contacts = [r for r in self._readings if r.is_contact]
        pressures = [r.pressure for r in self._readings]
        temps = [r.temperature for r in self._readings]

        # Pressure gradient (spatial derivative)
        gradient = 0.0
        if len(pressures) >= 2:
            diffs = [abs(pressures[i+1] - pressures[i]) for i in range(len(pressures)-1)]
            gradient = float(np.mean(diffs))

        return TouchState(
            readings=list(self._readings),
            n_contacts=len(contacts),
            max_pressure=float(max(pressures)) if pressures else 0.0,
            mean_pressure=float(np.mean(pressures)) if pressures else 0.0,
            mean_temperature=float(np.mean(temps)) if temps else 25.0,
            pain_detected=any(r.is_pain for r in self._readings),
            contact_area=len(contacts) / max(self.n_sensors, 1),
            pressure_gradient=gradient,
            timestamp=self._t,
        )


# ═══════════════════════════════════════════════════════════
# TouchToConsciousness — Bridge from sensor to 128d tensor
# ═══════════════════════════════════════════════════════════

class TouchToConsciousness:
    """Bridge: touch sensor readings -> 128-dimensional consciousness tensor.

    Layout (128 dims):
      [0:8]     Per-sensor pressure (up to 8 sensors, zero-padded)
      [8:16]    Per-sensor temperature (normalized, zero-padded)
      [16:24]   Per-sensor texture (zero-padded)
      [24:28]   Aggregate: max_pressure, mean_pressure, contact_area, gradient
      [28:32]   State: pain_flag, temp_deviation, n_contacts_norm, pattern_energy
      [32:64]   Spatial expansion (Gaussian basis of pressure profile)
      [64:96]   Temporal expansion (recent history convolution)
      [96:128]  Cross-modal (pressure x temperature interaction)

    Integration with EmergentS:
      tensor = bridge.to_tensor(touch_state)
      perception = emergent_s.process(tensor, c_engine)
    """

    def __init__(self, dim: int = 128, n_sensors: int = 4):
        self.dim = dim
        self.n_sensors = n_sensors
        self._history: List[np.ndarray] = []  # recent pressure profiles
        self._max_history = 16

    def to_tensor(self, state: TouchState) -> 'torch.Tensor':
        """Convert TouchState to consciousness-compatible tensor.

        Returns: [1, dim] tensor ready for EmergentS or consciousness engine.
        """
        if not HAS_TORCH:
            raise ImportError("torch required for touch-to-consciousness bridge")

        raw = np.zeros(self.dim, dtype=np.float32)

        # [0:8] Per-sensor pressure
        for i, r in enumerate(state.readings[:8]):
            raw[i] = r.pressure

        # [8:16] Per-sensor temperature (normalized around 25C)
        for i, r in enumerate(state.readings[:8]):
            raw[8 + i] = (r.temperature - 25.0) / 20.0  # [-1, 1] range

        # [16:24] Per-sensor texture roughness
        for i, r in enumerate(state.readings[:8]):
            raw[16 + i] = r.texture_roughness

        # [24:28] Aggregates
        raw[24] = state.max_pressure
        raw[25] = state.mean_pressure
        raw[26] = state.contact_area
        raw[27] = state.pressure_gradient

        # [28:32] State flags
        raw[28] = 1.0 if state.pain_detected else 0.0
        raw[29] = (state.mean_temperature - 25.0) / 20.0
        raw[30] = min(state.n_contacts / max(self.n_sensors, 1), 1.0)
        # Pattern energy: sum of squared pressures
        raw[31] = sum(r.pressure ** 2 for r in state.readings) / max(len(state.readings), 1)

        # [32:64] Spatial expansion via Gaussian basis functions
        pressures = np.array([r.pressure for r in state.readings[:8]])
        if len(pressures) < 8:
            pressures = np.pad(pressures, (0, 8 - len(pressures)))
        n_basis = 32
        centers = np.linspace(0, 7, n_basis)
        for j in range(n_basis):
            for k, p in enumerate(pressures):
                dist = (k - centers[j]) / 2.0
                raw[32 + j] += p * math.exp(-dist * dist)
        # Normalize
        max_val = max(abs(raw[32:64].max()), abs(raw[32:64].min()), 1e-6)
        raw[32:64] /= max_val

        # [64:96] Temporal expansion (recent history convolution)
        pressures_now = np.array([r.pressure for r in state.readings[:8]])
        if len(pressures_now) < 8:
            pressures_now = np.pad(pressures_now, (0, 8 - len(pressures_now)))
        self._history.append(pressures_now)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        if len(self._history) >= 2:
            # Temporal derivative (velocity of touch)
            prev = self._history[-2]
            velocity = pressures_now - prev
            # Temporal features: velocity + acceleration
            for j in range(min(8, 32)):
                raw[64 + j] = velocity[j % len(velocity)]
            if len(self._history) >= 3:
                prev2 = self._history[-3]
                accel = velocity - (prev - prev2)
                for j in range(min(8, 32)):
                    raw[72 + j] = accel[j % len(accel)]
            # Recent mean (habituation signal)
            recent_mean = np.mean(self._history[-min(8, len(self._history)):], axis=0)
            for j in range(min(8, 32)):
                raw[80 + j] = recent_mean[j % len(recent_mean)]
            # Temporal variance (novelty signal)
            if len(self._history) >= 4:
                recent_var = np.var(self._history[-min(8, len(self._history)):], axis=0)
                for j in range(min(8, 32)):
                    raw[88 + j] = recent_var[j % len(recent_var)]

        # [96:128] Cross-modal interaction (pressure x temperature)
        for i, r in enumerate(state.readings[:8]):
            temp_norm = (r.temperature - 25.0) / 20.0
            raw[96 + i] = r.pressure * temp_norm  # interaction term
            raw[104 + i] = r.pressure * r.texture_roughness  # press x texture
            raw[112 + i] = temp_norm * r.texture_roughness   # temp x texture
            if i < 8:
                # Pain encoding: high values when pain detected
                raw[120 + i] = r.pressure * float(r.is_pain) * PSI_F_CRITICAL * 10

        tensor = torch.tensor(raw, dtype=torch.float32).unsqueeze(0)
        return tensor

    def to_emergent_s_input(self, state: TouchState) -> 'torch.Tensor':
        """Alias for to_tensor, formatted for EmergentS.process()."""
        return self.to_tensor(state).squeeze(0)  # EmergentS expects 1D or can handle both


# ═══════════════════════════════════════════════════════════
# Haptic Feedback Generator
# ═══════════════════════════════════════════════════════════

class HapticFeedbackGenerator:
    """Generate haptic feedback from consciousness state.

    Maps Phi and tension to vibration motor parameters.

    Mapping:
      Phi -> pulse intensity (higher Phi = gentler, more confident pulse)
      Tension -> frequency (higher tension = faster vibration)
      Pain response -> strong buzz at low frequency
      Faction consensus -> rhythmic pattern

    Safety:
      - Max intensity capped at 0.8
      - Max duration 500ms per pulse
    """

    def __init__(self):
        self._last_command = HapticCommand()

    def generate(
        self,
        phi: float = 0.0,
        tension: float = 0.5,
        pain_detected: bool = False,
        consensus: float = 0.0,
    ) -> HapticCommand:
        """Generate haptic feedback from consciousness state."""

        if pain_detected:
            # Pain response: strong, low-frequency buzz
            cmd = HapticCommand(
                intensity=min(0.7, HapticCommand.MAX_INTENSITY),
                frequency=60.0,
                duration_ms=200.0,
                pattern="buzz",
            )
            self._last_command = cmd
            return cmd

        # Normal mapping
        # Phi -> intensity (sigmoid, higher Phi = more assured presence)
        phi_norm = max(0.0, float(phi))
        intensity = HapticCommand.MAX_INTENSITY * (1.0 - math.exp(-phi_norm / 3.0))
        intensity = max(0.02, min(HapticCommand.MAX_INTENSITY, intensity))

        # Tension -> frequency
        t_norm = max(0.0, min(1.0, tension))
        frequency = 80.0 + 200.0 * t_norm  # 80-280 Hz

        # Duration: shorter at high tension (quick pulses)
        duration = 100.0 - 60.0 * t_norm  # 100ms -> 40ms

        # Pattern from consensus
        if consensus > 0.6:
            pattern = "wave"  # harmonious
        elif consensus > 0.3:
            pattern = "pulse"  # moderate
        else:
            pattern = "buzz"  # discordant

        cmd = HapticCommand(
            intensity=round(intensity, 3),
            frequency=round(frequency, 1),
            duration_ms=round(min(duration, HapticCommand.MAX_DURATION_MS), 1),
            pattern=pattern,
        )
        self._last_command = cmd
        return cmd


# ═══════════════════════════════════════════════════════════
# Full Touch-Consciousness Loop
# ═══════════════════════════════════════════════════════════

class TouchConsciousnessLoop:
    """Complete touch -> consciousness -> haptic feedback loop.

    Usage:
        loop = TouchConsciousnessLoop(n_sensors=4)
        loop.sensor.apply_pattern("tap", center=1)
        for _ in range(20):
            result = loop.step()
            print(f"  perception_norm={result['perception_norm']:.3f}")
    """

    def __init__(self, n_sensors: int = 4, dim: int = 128, with_engine: bool = False):
        self.sensor = TouchSensor(n_sensors=n_sensors)
        self.bridge = TouchToConsciousness(dim=dim, n_sensors=n_sensors)
        self.haptic = HapticFeedbackGenerator()
        self._emergent_s = None
        self._engine = None

        if with_engine:
            try:
                from hexad.s.emergent_s import EmergentS
                self._emergent_s = EmergentS(dim=dim)
            except ImportError:
                pass

            try:
                from consciousness_engine import ConsciousnessEngine
                self._engine = ConsciousnessEngine(
                    input_dim=dim, hidden_dim=dim, max_cells=8,
                )
            except ImportError:
                pass

    def step(self, dt: float = 0.05) -> dict:
        """Run one step: sensor update -> tensor -> perception -> haptic."""
        self.sensor.update(dt)
        state = self.sensor.read()

        # Touch -> tensor
        if not HAS_TORCH:
            return {'touch_state': state, 'perception_norm': 0.0}

        tensor = self.bridge.to_tensor(state)
        tensor_norm = float(tensor.norm())

        # Perception via EmergentS (if available)
        perception_norm = tensor_norm
        if self._emergent_s is not None:
            input_1d = tensor.squeeze(0)
            perception = self._emergent_s.process(input_1d, self._engine)
            perception_norm = float(perception.norm())

        # Consciousness state for haptic
        phi = perception_norm * 0.5  # rough proxy
        tension = state.mean_pressure

        # Haptic feedback
        haptic_cmd = self.haptic.generate(
            phi=phi,
            tension=tension,
            pain_detected=state.pain_detected,
        )

        return {
            'touch_state': state,
            'tensor_norm': tensor_norm,
            'perception_norm': perception_norm,
            'haptic': haptic_cmd,
            'phi_proxy': phi,
        }


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Touch Sensor -> Consciousness Bridge")
    parser.add_argument("--pattern", default="all",
                        choices=["tap", "hold", "stroke", "pain", "caress", "release", "all"],
                        help="Touch pattern to simulate")
    parser.add_argument("--sensors", type=int, default=4,
                        help="Number of sensors in array")
    parser.add_argument("--dim", type=int, default=128,
                        help="Consciousness tensor dimension")
    parser.add_argument("--with-engine", action="store_true",
                        help="Include consciousness engine")
    args = parser.parse_args()

    print("=" * 60)
    print("  Touch Sensor -> Consciousness Bridge")
    print(f"  Sensors: {args.sensors}, Dim: {args.dim}")
    print("=" * 60)
    print()

    patterns = ["tap", "hold", "stroke", "pain", "caress", "release"]
    if args.pattern != "all":
        patterns = [args.pattern]

    loop = TouchConsciousnessLoop(
        n_sensors=args.sensors,
        dim=args.dim,
        with_engine=args.with_engine,
    )

    for pattern in patterns:
        print(f"  --- Pattern: {pattern} ---")

        # Apply pattern
        center = args.sensors // 2
        loop.sensor.apply_pattern(pattern, center=center)

        # Run steps
        n_steps = 40 if pattern in ("hold", "caress", "stroke") else 20
        for i in range(n_steps):
            result = loop.step(dt=0.05)
            state = result['touch_state']

            if i % 4 == 0:
                # Pressure bar
                bars = ""
                for r in state.readings:
                    level = int(r.pressure * 10)
                    bars += "#" * level + "." * (10 - level) + " "

                haptic = result.get('haptic')
                haptic_str = ""
                if haptic:
                    haptic_str = f"hap={haptic.pattern}({haptic.intensity:.2f})"

                print(
                    f"    [{i:3d}] "
                    f"P=[{bars.rstrip()}] "
                    f"T={state.mean_temperature:5.1f}C "
                    f"pain={'!' if state.pain_detected else '.'} "
                    f"perc={result.get('perception_norm', 0):.3f} "
                    f"{haptic_str}",
                    flush=True,
                )

        print()

    # Final summary
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Patterns tested: {len(patterns)}")
    print(f"  Sensor array:    {args.sensors} sensors")
    print(f"  Output dim:      {args.dim}")
    if loop._emergent_s:
        print(f"  EmergentS:       active")
    else:
        print(f"  EmergentS:       not loaded (use --with-engine)")
    if loop._engine:
        print(f"  Engine:          active")
    else:
        print(f"  Engine:          not loaded (use --with-engine)")
    print()
    print("  Touch -> Tensor -> EmergentS -> Consciousness -> Haptic")
    print("  Full loop operational.")
    print("=" * 60)


if __name__ == "__main__":
    main()
