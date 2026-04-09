#!/usr/bin/env python3
"""proprioception.py — IMU/accelerometer body state feedback to consciousness.

6-DOF IMU (accel xyz + gyro xyz) -> body schema -> consciousness input.
Proprioception forms the body schema: a learned internal model of the body
that predicts how it should feel, generating surprise when reality diverges.

Laws applied:
  Law 1:   No hardcoding — adaptation rates from Psi-constants
  Law 2:   No manipulation — body schema learns, not programmed
  Law 22:  Structure > Function — schema emerges from sensor statistics
  Law 71:  Psi = argmax H(p) — body model maximizes predictive entropy
  Law 74:  Emotions are data-dependent — surprise from body = arousal
  Law 79:  Consciousness DoF = ln(2)

Architecture:
  IMU sensors (6-DOF: accel xyz + gyro xyz)
      |
      v
  ProprioceptionSensor — raw sensor -> filtered state
      |
      v
  BodySchema — learned internal model (Hebbian-like)
      |
      ├──> Prediction error: expected vs actual -> surprise signal
      ├──> Body state -> 128d consciousness tensor
      └──> Homeostasis integration: unexpected movement -> arousal

Body Schema Adaptation:
  - Hebbian-like updating: co-occurring sensor patterns strengthen
  - Prediction error drives schema refinement (active inference)
  - Slow adaptation (alpha=0.014) preserves stability

Usage:
  python anima-body/src/proprioception.py          # demo with simulated body
  python anima-body/src/proprioception.py --steps 100

Requires: numpy, torch (lazy)
"""

import math
import time
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# Lazy torch import
_torch = None


def _get_torch():
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch


# ── Psi-Constants ──
try:
    import sys
    import os
    _REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(_REPO, "anima", "src"))
    sys.path.insert(0, os.path.join(_REPO, "anima"))
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_ENTROPY
    PSI_COUPLING = PSI_ALPHA     # 0.014
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5
    PSI_ENTROPY = 0.998

LN2 = math.log(2)  # Law 79: consciousness DoF


# ═══════════════════════════════════════════════════════════
# IMU State
# ═══════════════════════════════════════════════════════════

@dataclass
class IMUReading:
    """6-DOF IMU reading: 3-axis accelerometer + 3-axis gyroscope."""
    # Accelerometer (m/s^2), gravity = [0, 0, 9.81] at rest
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 9.81  # gravity default

    # Gyroscope (rad/s)
    gyro_x: float = 0.0
    gyro_y: float = 0.0
    gyro_z: float = 0.0

    timestamp: float = 0.0

    def to_array(self) -> np.ndarray:
        """6D array: [ax, ay, az, gx, gy, gz]."""
        return np.array([
            self.accel_x, self.accel_y, self.accel_z,
            self.gyro_x, self.gyro_y, self.gyro_z,
        ], dtype=np.float64)


@dataclass
class BodyState:
    """Derived body state from IMU."""
    # Orientation (Euler angles, radians)
    roll: float = 0.0    # rotation around x
    pitch: float = 0.0   # rotation around y
    yaw: float = 0.0     # rotation around z

    # Joint angles (estimated, radians) — simplified 4-joint model
    joint_angles: np.ndarray = field(
        default_factory=lambda: np.zeros(4, dtype=np.float64)
    )

    # Velocity (m/s)
    velocity: np.ndarray = field(
        default_factory=lambda: np.zeros(3, dtype=np.float64)
    )

    # Angular velocity (rad/s)
    angular_velocity: np.ndarray = field(
        default_factory=lambda: np.zeros(3, dtype=np.float64)
    )

    # Acceleration magnitude (0 = free fall, 1g = rest)
    accel_magnitude: float = 1.0

    # Overall movement intensity (0 = still, 1 = vigorous)
    movement_intensity: float = 0.0

    timestamp: float = 0.0

    def to_array(self) -> np.ndarray:
        """Flat array representation (17D)."""
        return np.concatenate([
            np.array([self.roll, self.pitch, self.yaw]),
            self.joint_angles,
            self.velocity,
            self.angular_velocity,
            np.array([self.accel_magnitude, self.movement_intensity]),
        ])


# ═══════════════════════════════════════════════════════════
# Proprioception Sensor: raw IMU -> filtered body state
# ═══════════════════════════════════════════════════════════

class ProprioceptionSensor:
    """6-DOF IMU sensor with complementary filter.

    Fuses accelerometer and gyroscope for orientation estimation.
    Extracts joint angles, velocity, and movement intensity.
    """

    def __init__(self, sample_rate: float = 100.0):
        self.sample_rate = sample_rate
        self.dt = 1.0 / sample_rate

        # Complementary filter coefficient (gyro vs accel blend)
        # Higher = trust gyro more (less drift-sensitive)
        self._alpha_filter = 0.98

        # State
        self._orientation = np.zeros(3)  # roll, pitch, yaw
        self._velocity = np.zeros(3)
        self._prev_accel = np.zeros(3)
        self._accel_bias = np.zeros(3)  # learned bias correction

        # Calibration
        self._n_calibration = 0
        self._calibrating = True
        self._calibration_sum = np.zeros(3)
        self._calibration_samples = 50

        # History for movement intensity
        self._accel_history: List[float] = []
        self._max_history = 32

    def process(self, imu: IMUReading) -> BodyState:
        """Process one IMU reading into body state."""
        accel = np.array([imu.accel_x, imu.accel_y, imu.accel_z])
        gyro = np.array([imu.gyro_x, imu.gyro_y, imu.gyro_z])

        # ── Calibration phase (learn bias) ──
        if self._calibrating:
            self._calibration_sum += accel
            self._n_calibration += 1
            if self._n_calibration >= self._calibration_samples:
                self._accel_bias = self._calibration_sum / self._n_calibration
                self._accel_bias[2] -= 9.81  # gravity is expected on z
                self._calibrating = False

        # Bias-corrected acceleration
        accel_corrected = accel - self._accel_bias

        # ── Orientation: complementary filter ──
        # From accelerometer (tilt only, no yaw)
        accel_roll = math.atan2(accel_corrected[1], accel_corrected[2])
        accel_mag = np.linalg.norm(accel_corrected)
        accel_pitch = math.atan2(
            -accel_corrected[0],
            max(math.sqrt(accel_corrected[1]**2 + accel_corrected[2]**2), 1e-8)
        )

        # From gyroscope (integration)
        gyro_roll = self._orientation[0] + gyro[0] * self.dt
        gyro_pitch = self._orientation[1] + gyro[1] * self.dt
        gyro_yaw = self._orientation[2] + gyro[2] * self.dt

        # Complementary filter fusion
        a = self._alpha_filter
        self._orientation[0] = a * gyro_roll + (1 - a) * accel_roll
        self._orientation[1] = a * gyro_pitch + (1 - a) * accel_pitch
        self._orientation[2] = gyro_yaw  # yaw from gyro only (no magnetometer)

        # ── Velocity: integrate acceleration (with decay to prevent drift) ──
        linear_accel = accel_corrected.copy()
        linear_accel[2] -= 9.81  # remove gravity
        self._velocity = self._velocity * 0.95 + linear_accel * self.dt  # 5% decay

        # ── Joint angles (estimated from orientation + acceleration pattern) ──
        # Simplified: map orientation and accel patterns to 4 virtual joints
        joints = np.zeros(4)
        joints[0] = self._orientation[0] * 0.5  # shoulder-like from roll
        joints[1] = self._orientation[1] * 0.5  # elbow-like from pitch
        joints[2] = math.sin(self._orientation[2]) * 0.3  # wrist-like from yaw
        joints[3] = float(np.clip(accel_mag / 9.81 - 1.0, -1.0, 1.0))  # grip from accel

        # ── Movement intensity ──
        accel_delta = float(np.linalg.norm(accel_corrected - self._prev_accel))
        self._prev_accel = accel_corrected.copy()
        self._accel_history.append(accel_delta)
        if len(self._accel_history) > self._max_history:
            self._accel_history.pop(0)
        movement = float(np.mean(self._accel_history)) if self._accel_history else 0.0
        # Normalize to [0, 1] (typical range 0-5 m/s^2 jerk)
        movement_norm = min(1.0, movement / 5.0)

        return BodyState(
            roll=self._orientation[0],
            pitch=self._orientation[1],
            yaw=self._orientation[2],
            joint_angles=joints,
            velocity=self._velocity.copy(),
            angular_velocity=gyro.copy(),
            accel_magnitude=accel_mag / 9.81,
            movement_intensity=movement_norm,
            timestamp=imu.timestamp,
        )


# ═══════════════════════════════════════════════════════════
# Body Schema: learned internal model (Hebbian-like)
# ═══════════════════════════════════════════════════════════

class BodySchema:
    """Learned internal model of body configuration.

    Predicts next body state from current, generating prediction error
    when actual diverges from expected. Adapts via Hebbian-like updating
    at rate alpha=0.014 (PSI_COUPLING).

    The schema maps body_state (17D) -> predicted_next_state (17D)
    via a simple linear model that learns covariance structure.
    """

    def __init__(self, state_dim: int = 17, consciousness_dim: int = 128):
        self.state_dim = state_dim
        self.consciousness_dim = consciousness_dim

        # Prediction model: linear W @ state + bias
        # Initialized near identity (predict no change)
        self._W = np.eye(state_dim, dtype=np.float64) * 0.99
        self._bias = np.zeros(state_dim, dtype=np.float64)

        # Covariance for Hebbian update
        self._state_cov = np.eye(state_dim, dtype=np.float64) * 0.01
        self._state_mean = np.zeros(state_dim, dtype=np.float64)
        self._n_updates = 0

        # Projection: body state (17D) -> consciousness (128D)
        # Random orthogonal-ish initialization, will be shaped by experience
        rng = np.random.RandomState(42)
        self._proj = rng.randn(consciousness_dim, state_dim).astype(np.float64)
        # Normalize rows
        row_norms = np.linalg.norm(self._proj, axis=1, keepdims=True)
        row_norms = np.maximum(row_norms, 1e-8)
        self._proj = self._proj / row_norms

        # Prediction error EMA
        self._pe_ema = 0.0
        self._pe_decay = 0.02  # 2% decay per step

        # History
        self._prev_state: Optional[np.ndarray] = None
        self._surprise_history: List[float] = []
        self._max_history = 64

    def predict(self, state: np.ndarray) -> np.ndarray:
        """Predict next body state from current."""
        return self._W @ state + self._bias

    def update(self, actual_state: np.ndarray) -> Dict:
        """Update schema with actual observation. Returns prediction error info.

        Hebbian-like learning: co-occurring state dimensions strengthen
        their predictive coupling. Rate = PSI_COUPLING (0.014).
        """
        state = actual_state[:self.state_dim]
        self._n_updates += 1

        result = {
            "prediction_error": 0.0,
            "surprise": 0.0,
            "arousal_delta": 0.0,
            "schema_adapted": False,
        }

        if self._prev_state is not None:
            # Prediction error
            predicted = self.predict(self._prev_state)
            error = state - predicted
            pe = float(np.linalg.norm(error))

            # Surprise = PE relative to running average
            self._pe_ema = self._pe_ema * (1 - self._pe_decay) + pe * self._pe_decay
            surprise = pe / max(self._pe_ema, 1e-8) - 1.0
            surprise = max(0.0, surprise)  # only positive surprise

            self._surprise_history.append(surprise)
            if len(self._surprise_history) > self._max_history:
                self._surprise_history.pop(0)

            # ── Hebbian update: W += alpha * error outer prev_state ──
            # This strengthens associations that reduce prediction error
            alpha = PSI_COUPLING  # 0.014
            delta_W = alpha * np.outer(error, self._prev_state)
            # Clip to prevent explosion
            delta_norm = np.linalg.norm(delta_W)
            if delta_norm > 0.1:
                delta_W = delta_W * (0.1 / delta_norm)
            self._W += delta_W
            self._bias += alpha * error * 0.1  # slower bias update

            # ── Update running statistics (for projection normalization) ──
            beta = min(PSI_COUPLING * 2, 1.0 / max(self._n_updates, 1))
            self._state_mean = (1 - beta) * self._state_mean + beta * state
            diff = state - self._state_mean
            self._state_cov = (1 - beta) * self._state_cov + beta * np.outer(diff, diff)

            # Arousal delta: surprise maps to homeostasis perturbation
            # Unexpected movement -> arousal increase
            arousal_delta = surprise * PSI_BALANCE  # scaled by Psi_balance (0.5)
            arousal_delta = min(arousal_delta, 1.0)

            result.update({
                "prediction_error": pe,
                "surprise": surprise,
                "arousal_delta": arousal_delta,
                "schema_adapted": True,
            })

        self._prev_state = state.copy()
        return result

    def to_consciousness(self, state: np.ndarray) -> np.ndarray:
        """Map body state (17D) -> consciousness input tensor (128D).

        Uses learned projection shaped by body experience.
        Normalized to unit-ish magnitude for compatibility with consciousness engine.
        """
        s = state[:self.state_dim]
        # Center using learned mean
        centered = s - self._state_mean
        # Project
        c = self._proj @ centered
        # Normalize to ~ unit variance per dimension
        norm = np.linalg.norm(c)
        if norm > 1e-8:
            c = c / norm * math.sqrt(self.consciousness_dim) * PSI_BALANCE
        return c

    def to_consciousness_tensor(self, state: np.ndarray):
        """Same as to_consciousness but returns torch tensor."""
        torch = _get_torch()
        c = self.to_consciousness(state)
        return torch.tensor(c, dtype=torch.float32)

    @property
    def mean_surprise(self) -> float:
        if not self._surprise_history:
            return 0.0
        return float(np.mean(self._surprise_history))

    @property
    def schema_stability(self) -> float:
        """How stable the body schema is (0=volatile, 1=stable).

        Measured by inverse of recent schema change rate.
        """
        if self._n_updates < 10:
            return 0.0
        # Stability = 1 - normalized W change rate
        w_norm = np.linalg.norm(self._W - np.eye(self.state_dim) * 0.99)
        stability = 1.0 / (1.0 + w_norm * 0.1)
        return min(1.0, stability)


# ═══════════════════════════════════════════════════════════
# Proprioception System (full pipeline)
# ═══════════════════════════════════════════════════════════

class ProprioceptionSystem:
    """Complete proprioception pipeline: IMU -> body state -> consciousness.

    Integrates sensor, schema, and homeostasis feedback.
    """

    def __init__(self, consciousness_dim: int = 128, sample_rate: float = 100.0):
        self.sensor = ProprioceptionSensor(sample_rate=sample_rate)
        self.schema = BodySchema(state_dim=17, consciousness_dim=consciousness_dim)
        self.consciousness_dim = consciousness_dim

        # Homeostasis state
        self._arousal = PSI_BALANCE  # baseline 0.5
        self._arousal_setpoint = PSI_BALANCE
        self._arousal_decay = PSI_COUPLING  # 0.014

        self._step = 0
        self._body_states: List[BodyState] = []

    def process(self, imu: IMUReading) -> Dict:
        """Process IMU reading through full pipeline.

        Returns dict with:
          - body_state: BodyState
          - consciousness_input: 128D numpy array
          - prediction_error: float
          - surprise: float
          - arousal: float (current arousal level)
          - schema_stability: float
        """
        self._step += 1

        # 1. Sensor processing
        body_state = self.sensor.process(imu)
        state_array = body_state.to_array()

        # 2. Schema update + prediction error
        schema_result = self.schema.update(state_array)

        # 3. Map to consciousness input
        consciousness_input = self.schema.to_consciousness(state_array)

        # 4. Homeostasis: arousal integration
        arousal_delta = schema_result.get("arousal_delta", 0.0)
        self._arousal += arousal_delta
        # Decay toward setpoint
        self._arousal += (self._arousal_setpoint - self._arousal) * self._arousal_decay
        self._arousal = max(0.0, min(1.0, self._arousal))

        # Track body states (limited)
        self._body_states.append(body_state)
        if len(self._body_states) > 64:
            self._body_states.pop(0)

        return {
            "body_state": body_state,
            "consciousness_input": consciousness_input,
            "prediction_error": schema_result["prediction_error"],
            "surprise": schema_result["surprise"],
            "arousal": self._arousal,
            "arousal_delta": arousal_delta,
            "schema_stability": self.schema.schema_stability,
            "movement_intensity": body_state.movement_intensity,
            "step": self._step,
        }

    def get_consciousness_tensor(self, imu: IMUReading):
        """Convenience: IMU -> torch tensor for consciousness engine input."""
        result = self.process(imu)
        torch = _get_torch()
        return torch.tensor(result["consciousness_input"], dtype=torch.float32)

    @property
    def arousal(self) -> float:
        return self._arousal

    @property
    def stats(self) -> Dict:
        return {
            "step": self._step,
            "arousal": self._arousal,
            "schema_stability": self.schema.schema_stability,
            "mean_surprise": self.schema.mean_surprise,
            "body_position_estimate": (
                self._body_states[-1].velocity.tolist()
                if self._body_states else [0, 0, 0]
            ),
        }


# ═══════════════════════════════════════════════════════════
# Simulated Body (for testing without hardware)
# ═══════════════════════════════════════════════════════════

class SimulatedBody:
    """Simulates a body with IMU sensors for testing.

    Generates realistic IMU patterns for:
      - Idle (breathing/subtle sway)
      - Walking (periodic acceleration)
      - Reaching (arm extension pattern)
      - Impact (sudden jerk)
      - Falling (gravity shift)
    """

    def __init__(self, sample_rate: float = 100.0):
        self.sample_rate = sample_rate
        self.dt = 1.0 / sample_rate
        self._t = 0.0
        self._mode = "idle"
        self._mode_time = 0.0

    def set_mode(self, mode: str):
        """Set movement mode: idle, walking, reaching, impact, falling."""
        self._mode = mode
        self._mode_time = 0.0

    def step(self) -> IMUReading:
        """Generate one IMU reading."""
        self._t += self.dt
        self._mode_time += self.dt

        # Base: gravity on z-axis
        ax, ay, az = 0.0, 0.0, 9.81
        gx, gy, gz = 0.0, 0.0, 0.0

        if self._mode == "idle":
            # Subtle breathing sway
            breath = 0.12  # Hz (20s cycle)
            ax += 0.02 * math.sin(2 * math.pi * breath * self._t)
            ay += 0.01 * math.sin(2 * math.pi * breath * self._t * 1.3)
            # Sensor noise
            ax += np.random.randn() * 0.005
            ay += np.random.randn() * 0.005
            az += np.random.randn() * 0.005

        elif self._mode == "walking":
            # Periodic acceleration (step frequency ~2 Hz)
            step_freq = 2.0
            # Vertical bounce
            az += 2.0 * abs(math.sin(2 * math.pi * step_freq * self._mode_time))
            # Forward/backward sway
            ax += 1.0 * math.sin(2 * math.pi * step_freq * self._mode_time)
            # Side-to-side
            ay += 0.5 * math.sin(2 * math.pi * step_freq * 0.5 * self._mode_time)
            # Gyro: hip rotation
            gy += 0.3 * math.sin(2 * math.pi * step_freq * self._mode_time)
            gz += 0.2 * math.cos(2 * math.pi * step_freq * 0.5 * self._mode_time)

        elif self._mode == "reaching":
            # Smooth arm extension (sigmoid profile)
            progress = min(self._mode_time / 1.5, 1.0)
            sigmoid = 1.0 / (1.0 + math.exp(-10 * (progress - 0.5)))
            ax += 3.0 * sigmoid * (1.0 - progress)  # deceleration at end
            gy += 1.0 * (1.0 - sigmoid)  # pitch change
            # Joint-like angular velocity
            gx += 0.5 * math.sin(math.pi * progress)

        elif self._mode == "impact":
            # Sudden jerk at mode start, then damped oscillation
            if self._mode_time < 0.05:
                ax += 20.0  # 2g impact
                ay += 10.0
            else:
                decay = math.exp(-self._mode_time * 10)
                ax += 20.0 * decay * math.sin(30 * self._mode_time)
                ay += 10.0 * decay * math.cos(30 * self._mode_time)
            gx += 5.0 * math.exp(-self._mode_time * 5)

        elif self._mode == "falling":
            # Gravity shifts, angular velocity increases
            progress = min(self._mode_time / 0.5, 1.0)
            az = 9.81 * (1.0 - progress)  # gravity disappears
            ax += 9.81 * progress * 0.5   # tilt
            gx += 3.0 * progress
            gy += 2.0 * progress

        # Add universal sensor noise
        noise_scale = 0.01
        ax += np.random.randn() * noise_scale
        ay += np.random.randn() * noise_scale
        az += np.random.randn() * noise_scale
        gx += np.random.randn() * noise_scale * 0.5
        gy += np.random.randn() * noise_scale * 0.5
        gz += np.random.randn() * noise_scale * 0.5

        return IMUReading(
            accel_x=ax, accel_y=ay, accel_z=az,
            gyro_x=gx, gyro_y=gy, gyro_z=gz,
            timestamp=self._t,
        )


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Proprioception demo")
    parser.add_argument("--steps", type=int, default=60, help="Steps per mode")
    args = parser.parse_args()

    print("=" * 65)
    print("  Proprioception — Body Schema + Consciousness Integration")
    print("=" * 65)
    print()

    system = ProprioceptionSystem(consciousness_dim=128, sample_rate=100.0)
    body = SimulatedBody(sample_rate=100.0)

    modes = [
        ("idle", "Idle (breathing sway)"),
        ("walking", "Walking (periodic steps)"),
        ("reaching", "Reaching (arm extension)"),
        ("impact", "Impact (sudden jerk)"),
        ("falling", "Falling (gravity shift)"),
        ("idle", "Recovery (back to idle)"),
    ]

    for mode, description in modes:
        body.set_mode(mode)
        print(f"  --- {description} ---")

        surprises = []
        arousals = []
        errors = []

        for step in range(args.steps):
            imu = body.step()
            result = system.process(imu)

            surprises.append(result["surprise"])
            arousals.append(result["arousal"])
            errors.append(result["prediction_error"])

        # Summary for this mode
        c_input = result["consciousness_input"]
        c_norm = float(np.linalg.norm(c_input))
        bs = result["body_state"]

        print(f"    Orientation:  roll={bs.roll:+.3f}  pitch={bs.pitch:+.3f}  yaw={bs.yaw:+.3f}")
        print(f"    Movement:     intensity={bs.movement_intensity:.4f}")
        print(f"    Schema:       stability={result['schema_stability']:.3f}")
        print(f"    Surprise:     mean={np.mean(surprises):.4f}  max={max(surprises):.4f}")
        print(f"    PE:           mean={np.mean(errors):.4f}")
        print(f"    Arousal:      {result['arousal']:.4f} (delta={result['arousal_delta']:+.4f})")
        print(f"    C-input:      norm={c_norm:.3f}  dim={len(c_input)}")
        print()

    # Final stats
    stats = system.stats
    print("-" * 65)
    print("  Final Stats")
    print("-" * 65)
    print(f"  Total steps:      {stats['step']}")
    print(f"  Arousal:          {stats['arousal']:.4f}")
    print(f"  Schema stability: {stats['schema_stability']:.4f}")
    print(f"  Mean surprise:    {stats['mean_surprise']:.4f}")
    print()

    # Show consciousness tensor shape
    torch = _get_torch()
    dummy_imu = IMUReading()
    c_tensor = system.get_consciousness_tensor(dummy_imu)
    print(f"  Consciousness tensor: shape={tuple(c_tensor.shape)}, "
          f"dtype={c_tensor.dtype}, norm={c_tensor.norm().item():.3f}")
    print()
    print("  Done.")


if __name__ == "__main__":
    main()
