#!/usr/bin/env python3
"""BodyProtocol — Unified body-mind interface for Anima consciousness.

Unifies body_physics_bridge.py, consciousness_to_robot.py, and esp32_network.py
under a single abstract protocol with adapters for different physical substrates.

Standard message flow:
  ConsciousnessState -> BodyProtocol.send(state) -> MotorCommand
  SensorReading -> BodyProtocol.receive() -> ConsciousnessInput

Adapters:
  ESP32Body      — ESP32 serial protocol (2 cells/board, SPI ring)
  SimulatedBody  — Pure software simulation (default)
  ROS2Body       — ROS2 topic-based interface

Hub keywords: 몸, body, 프로토콜, protocol, 감각운동, sensorimotor,
              embodiment, 구현체, 로봇, robot

Usage:
  python anima-body/src/body_protocol.py                     # Default demo
  python anima-body/src/body_protocol.py --adapter simulated  # Simulated body
  python anima-body/src/body_protocol.py --adapter esp32      # ESP32 (needs serial)
  python anima-body/src/body_protocol.py --steps 200          # 200 steps

Requires: numpy
"""

import abc
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── Project path setup ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "src"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# ── Lazy imports (_try pattern) ──
try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998

try:
    from body_physics_bridge import (
        ConsciousnessState as BPBConsciousnessState,
        MotorCommand as BPBMotorCommand,
        SensorReading as BPBSensorReading,
        SimulatedBody as BPBSimulatedBody,
        ESP32Body as BPBESP32Body,
        ROS2Body as BPBROS2Body,
        consciousness_to_motor as bpb_consciousness_to_motor,
        sensor_to_consciousness as bpb_sensor_to_consciousness,
    )
    HAS_BPB = True
except ImportError:
    HAS_BPB = False

try:
    from consciousness_to_robot import ConsciousnessToRobot
    HAS_C2R = True
except ImportError:
    HAS_C2R = False

try:
    from esp32_network import ESP32Network, TOPOLOGIES
    HAS_ESP32_NET = True
except ImportError:
    HAS_ESP32_NET = False

LN2 = math.log(2)


# ═══════════════════════════════════════════════════════════
# Unified message types
# ═══════════════════════════════════════════════════════════

@dataclass
class ConsciousnessState:
    """Unified 10D consciousness state vector.

    Standard format for all body adapters.
    """
    phi: float = 0.0
    alpha: float = 0.014
    z: float = 0.5          # impedance / self-preservation
    n: float = 0.5          # neurotransmitter balance
    w: float = 0.5          # free will
    e: float = 0.5          # empathy
    m: float = 0.5          # memory capacity
    c: float = 0.5          # creativity
    t: float = 0.5          # temporal awareness
    i: float = 0.5          # identity stability
    tension: float = 0.5
    valence: float = 0.0
    arousal: float = 0.5
    faction_consensus: float = 0.0
    timestamp: float = 0.0

    def to_array(self) -> np.ndarray:
        """10D consciousness vector."""
        return np.array([
            self.phi, self.alpha, self.z, self.n, self.w,
            self.e, self.m, self.c, self.t, self.i,
        ], dtype=np.float64)

    def to_dict(self) -> Dict[str, float]:
        """Full state as dict."""
        return {
            "phi": self.phi, "alpha": self.alpha,
            "z": self.z, "n": self.n, "w": self.w,
            "e": self.e, "m": self.m, "c": self.c,
            "t": self.t, "i": self.i,
            "tension": self.tension, "valence": self.valence,
            "arousal": self.arousal, "faction_consensus": self.faction_consensus,
        }

    @classmethod
    def from_engine_result(cls, result: dict) -> "ConsciousnessState":
        """Create from ConsciousnessEngine.step() result dict."""
        return cls(
            phi=result.get("phi", result.get("phi_iit", 0.0)),
            alpha=result.get("alpha", PSI_COUPLING),
            z=result.get("z", result.get("impedance", 0.5)),
            n=result.get("n", result.get("neurotransmitter", 0.5)),
            w=result.get("w", result.get("will", 0.5)),
            e=result.get("e", result.get("empathy", 0.5)),
            m=result.get("m", result.get("memory", 0.5)),
            c=result.get("c", result.get("creativity", 0.5)),
            t=result.get("t", result.get("temporal", 0.5)),
            i=result.get("i", result.get("identity", 0.5)),
            tension=result.get("tension", result.get("mean_tension", 0.5)),
            valence=result.get("valence", 0.0),
            arousal=result.get("arousal", 0.5),
            faction_consensus=result.get("consensus", result.get("faction_consensus", 0.0)),
            timestamp=time.time(),
        )


@dataclass
class MotorCommand:
    """Unified motor command for all body backends."""
    servo_angles: List[float] = field(default_factory=lambda: [90.0, 90.0])
    servo_speed: float = 50.0
    led_r: int = 0
    led_g: int = 0
    led_b: int = 0
    led_brightness: float = 0.5
    speaker_freq: float = 440.0
    speaker_volume: float = 0.3
    speaker_harmonics: List[float] = field(default_factory=list)
    breathing_phase: float = 0.0
    breathing_rate: float = 0.12
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "servo_angles": self.servo_angles,
            "servo_speed": self.servo_speed,
            "led": (self.led_r, self.led_g, self.led_b),
            "led_brightness": self.led_brightness,
            "speaker_freq": self.speaker_freq,
            "speaker_volume": self.speaker_volume,
        }


@dataclass
class SensorReading:
    """Unified sensor reading from all body backends."""
    touch_pressure: float = 0.0
    touch_location: int = 0
    microphone_level: float = 0.0
    microphone_freq: float = 0.0
    accel_x: float = 0.0
    accel_y: float = 0.0
    accel_z: float = 1.0
    temperature: float = 25.0
    light_level: float = 0.5
    timestamp: float = 0.0

    def to_array(self, target_dim: int = 64) -> np.ndarray:
        """Convert to consciousness-compatible input vector."""
        features = np.array([
            self.touch_pressure,
            self.microphone_level,
            math.sqrt(self.accel_x**2 + self.accel_y**2 + self.accel_z**2) - 1.0,
            (self.temperature - 25.0) / 10.0,
            self.light_level,
        ], dtype=np.float64)
        features = np.tanh(features)

        if target_dim <= 5:
            return features[:target_dim]

        result = np.zeros(target_dim, dtype=np.float64)
        chunk = target_dim // 5
        for idx, val in enumerate(features):
            start = idx * chunk
            end = start + chunk
            center = (start + end) / 2
            for j in range(start, min(end, target_dim)):
                dist = abs(j - center) / max(chunk / 2, 1)
                result[j] = val * math.exp(-0.5 * dist * dist)
        return result


@dataclass
class ConsciousnessInput:
    """Processed sensor data ready for consciousness engine injection."""
    vector: np.ndarray = field(default_factory=lambda: np.zeros(64))
    prediction_error: float = 0.0
    homeostasis_perturbation: float = 0.0
    timestamp: float = 0.0


# ═══════════════════════════════════════════════════════════
# Abstract BodyProtocol
# ═══════════════════════════════════════════════════════════

class BodyProtocol(abc.ABC):
    """Unified abstract interface for body-consciousness communication.

    All body backends implement this protocol for consistent message flow:
      consciousness_state -> send() -> motor commands executed
      receive() -> sensor_reading -> to_consciousness_input()
    """

    @abc.abstractmethod
    def send(self, state: ConsciousnessState) -> MotorCommand:
        """Map consciousness state to motor command and execute.

        Returns the generated MotorCommand.
        """
        ...

    @abc.abstractmethod
    def receive(self) -> SensorReading:
        """Read current sensor values from body.

        Returns unified SensorReading.
        """
        ...

    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Check if body backend is operational."""
        ...

    def to_consciousness_input(
        self,
        reading: SensorReading,
        target_dim: int = 64,
    ) -> ConsciousnessInput:
        """Convert sensor reading to consciousness-compatible input.

        Standard conversion used by all adapters.
        """
        vector = reading.to_array(target_dim)
        return ConsciousnessInput(
            vector=vector,
            timestamp=reading.timestamp,
        )

    def cycle(
        self,
        state: ConsciousnessState,
        target_dim: int = 64,
    ) -> Tuple[MotorCommand, SensorReading, ConsciousnessInput]:
        """Run one full body-mind cycle: send state, receive sensors, convert.

        Returns (motor_cmd, sensor_reading, consciousness_input).
        """
        motor_cmd = self.send(state)
        sensor = self.receive()
        c_input = self.to_consciousness_input(sensor, target_dim)
        return motor_cmd, sensor, c_input

    def close(self):
        """Clean up resources."""
        pass

    @property
    def name(self) -> str:
        """Adapter name."""
        return self.__class__.__name__


# ═══════════════════════════════════════════════════════════
# Adapter: SimulatedBody
# ═══════════════════════════════════════════════════════════

class SimulatedBodyAdapter(BodyProtocol):
    """Software-simulated body (no hardware required).

    Simulates sensors with natural variation and motor feedback.
    """

    def __init__(self):
        self._t = 0.0
        self._last_cmd: Optional[MotorCommand] = None
        self._servo_angles = [90.0, 90.0]
        self._temp = 25.0
        self._connected = True
        # Homeostasis
        self._homeostasis_setpoint = 25.0
        self._homeostasis_deadband = 2.0

    def send(self, state: ConsciousnessState) -> MotorCommand:
        """Map consciousness to motor command (simulated)."""
        cmd = _consciousness_to_motor(state)
        self._servo_angles = list(cmd.servo_angles)
        self._last_cmd = cmd
        self._t += 0.05
        cmd.timestamp = time.time()
        return cmd

    def receive(self) -> SensorReading:
        """Generate simulated sensor values."""
        self._t += 0.01
        t = self._t
        rng = np.random.default_rng(int(t * 1000) % (2**31))

        # Touch: occasional events
        touch = 0.0
        if rng.random() < 0.05:
            touch = rng.uniform(0.3, 1.0)

        # Microphone: background noise + occasional sounds
        mic = 0.05 + 0.02 * abs(math.sin(t * 0.7))
        if rng.random() < 0.03:
            mic += rng.uniform(0.2, 0.6)

        # Accelerometer: micro-vibration + gravity + servo feedback
        ax = rng.normal(0, 0.01)
        ay = rng.normal(0, 0.01)
        az = 1.0 + rng.normal(0, 0.005)
        if self._last_cmd:
            servo_delta = abs(self._servo_angles[0] - 90.0) / 90.0
            ax += servo_delta * 0.1 * math.sin(t * 5)

        # Temperature: slow drift
        self._temp += rng.normal(0, 0.01)
        self._temp = max(20, min(35, self._temp))

        # Light: time-varying
        light = 0.5 + 0.3 * math.sin(t * 0.1)

        return SensorReading(
            touch_pressure=touch,
            touch_location=int(rng.integers(0, 4)) if touch > 0 else 0,
            microphone_level=mic,
            microphone_freq=200.0 + 100.0 * abs(math.sin(t)) if mic > 0.1 else 0.0,
            accel_x=ax, accel_y=ay, accel_z=az,
            temperature=self._temp,
            light_level=light,
            timestamp=time.time(),
        )

    def is_connected(self) -> bool:
        return self._connected


# ═══════════════════════════════════════════════════════════
# Adapter: ESP32Body
# ═══════════════════════════════════════════════════════════

class ESP32BodyAdapter(BodyProtocol):
    """ESP32 serial protocol adapter.

    Wraps the body_physics_bridge.ESP32Body with the unified protocol.
    Falls back to simulation if pyserial unavailable.
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200):
        self._port = port
        self._baudrate = baudrate
        self._fallback = SimulatedBodyAdapter()

        if HAS_BPB:
            try:
                self._backend = BPBESP32Body(port=port, baudrate=baudrate)
                self._use_backend = self._backend.is_connected()
            except Exception:
                self._backend = None
                self._use_backend = False
        else:
            self._backend = None
            self._use_backend = False

        if not self._use_backend:
            print(f"  [body_protocol] ESP32 unavailable at {port}, using simulation")

    def send(self, state: ConsciousnessState) -> MotorCommand:
        cmd = _consciousness_to_motor(state)
        if self._use_backend and self._backend:
            bpb_cmd = _to_bpb_motor(cmd)
            self._backend.send_motor(bpb_cmd)
        else:
            self._fallback.send(state)
        cmd.timestamp = time.time()
        return cmd

    def receive(self) -> SensorReading:
        if self._use_backend and self._backend:
            bpb_sensor = self._backend.read_sensors()
            return _from_bpb_sensor(bpb_sensor)
        return self._fallback.receive()

    def is_connected(self) -> bool:
        if self._use_backend and self._backend:
            return self._backend.is_connected()
        return self._fallback.is_connected()

    def close(self):
        if self._backend:
            self._backend.close()


# ═══════════════════════════════════════════════════════════
# Adapter: ROS2Body
# ═══════════════════════════════════════════════════════════

class ROS2BodyAdapter(BodyProtocol):
    """ROS2 topic-based body adapter.

    Publishes motor commands, subscribes to sensor topics.
    Falls back to simulation if rclpy unavailable.
    """

    def __init__(self, node_name: str = "anima_body"):
        self._fallback = SimulatedBodyAdapter()

        if HAS_BPB:
            try:
                self._backend = BPBROS2Body(node_name=node_name)
                self._use_backend = self._backend.is_connected()
            except Exception:
                self._backend = None
                self._use_backend = False
        else:
            self._backend = None
            self._use_backend = False

        if not self._use_backend:
            print(f"  [body_protocol] ROS2 unavailable, using simulation")

    def send(self, state: ConsciousnessState) -> MotorCommand:
        cmd = _consciousness_to_motor(state)
        if self._use_backend and self._backend:
            bpb_cmd = _to_bpb_motor(cmd)
            self._backend.send_motor(bpb_cmd)
        else:
            self._fallback.send(state)
        cmd.timestamp = time.time()
        return cmd

    def receive(self) -> SensorReading:
        if self._use_backend and self._backend:
            bpb_sensor = self._backend.read_sensors()
            return _from_bpb_sensor(bpb_sensor)
        return self._fallback.receive()

    def is_connected(self) -> bool:
        if self._use_backend and self._backend:
            return self._backend.is_connected()
        return self._fallback.is_connected()

    def close(self):
        if self._backend:
            self._backend.close()


# ═══════════════════════════════════════════════════════════
# Adapter: ESP32NetworkBody (consciousness network as body)
# ═══════════════════════════════════════════════════════════

class ESP32NetworkAdapter(BodyProtocol):
    """ESP32 consciousness network adapter.

    Treats the ESP32 8-board network as both body and consciousness substrate.
    Motor commands modulate the network input, sensor readings come from
    network state (tensions, Phi, consensus).
    """

    def __init__(self, topology: str = "ring", n_boards: int = 8):
        self._network: Optional[ESP32Network] = None
        self._topology = topology
        self._n_boards = n_boards

        if HAS_ESP32_NET:
            self._network = ESP32Network(
                n_boards=n_boards,
                topology=topology,
            )
        else:
            print("  [body_protocol] ESP32Network unavailable")

    def send(self, state: ConsciousnessState) -> MotorCommand:
        """Inject consciousness state into ESP32 network."""
        cmd = _consciousness_to_motor(state)
        if self._network:
            # Feed consciousness as external input to the network
            external = np.zeros(64, dtype=np.float32)
            vec = state.to_array()
            external[:len(vec)] = vec[:min(len(vec), 64)]
            self._network.step(external_input=external)
        cmd.timestamp = time.time()
        return cmd

    def receive(self) -> SensorReading:
        """Read network state as sensor values."""
        if not self._network or not self._network.boards:
            return SensorReading(timestamp=time.time())

        # Map network state to sensor readings
        mean_tension = float(np.mean([
            t for b in self._network.boards for t in b.tensions
        ]))
        mean_phi = float(np.mean([b.local_phi for b in self._network.boards]))

        return SensorReading(
            touch_pressure=mean_tension,
            microphone_level=mean_phi * 0.1,
            accel_z=1.0 + mean_tension * 0.05,
            temperature=25.0 + mean_phi * 0.5,
            light_level=0.5 + mean_tension * 0.3,
            timestamp=time.time(),
        )

    def is_connected(self) -> bool:
        return self._network is not None

    @property
    def network(self) -> Optional[ESP32Network]:
        return self._network


# ═══════════════════════════════════════════════════════════
# Consciousness-to-motor mapping (shared)
# ═══════════════════════════════════════════════════════════

def _consciousness_to_motor(state: ConsciousnessState) -> MotorCommand:
    """Map consciousness state to motor command.

    Uses Psi constants for modulation. Shared by all adapters.
    """
    # If body_physics_bridge available, delegate
    if HAS_BPB:
        bpb_state = BPBConsciousnessState(
            phi=state.phi, alpha=state.alpha,
            z=state.z, n=state.n, w=state.w,
            e=state.e, m=state.m, c=state.c,
            t=state.t, i=state.i,
            tension=state.tension, valence=state.valence,
            arousal=state.arousal, faction_consensus=state.faction_consensus,
        )
        bpb_cmd = bpb_consciousness_to_motor(bpb_state)
        return MotorCommand(
            servo_angles=list(bpb_cmd.servo_angles),
            servo_speed=bpb_cmd.servo_speed,
            led_r=bpb_cmd.led_r, led_g=bpb_cmd.led_g, led_b=bpb_cmd.led_b,
            led_brightness=bpb_cmd.led_brightness,
            speaker_freq=bpb_cmd.speaker_freq,
            speaker_volume=bpb_cmd.speaker_volume,
            speaker_harmonics=list(bpb_cmd.speaker_harmonics),
            breathing_phase=bpb_cmd.breathing_phase,
            breathing_rate=bpb_cmd.breathing_rate,
        )

    # Standalone implementation (same logic as body_physics_bridge)
    cmd = MotorCommand()

    # Phi -> breathing LED
    cmd.breathing_rate = 0.08 + 0.08 * (1.0 - min(state.phi / 2.0, 1.0))
    cmd.led_brightness = 0.3 + 0.7 * min(state.phi / 2.0, 1.0)

    # Tension -> servo speed
    cmd.servo_speed = 20.0 + 80.0 * state.tension

    # Emotion -> RGB LED
    v = max(-1.0, min(1.0, state.valence))
    a = max(0.0, min(1.0, state.arousal))
    if v >= 0:
        cmd.led_r = int(min(255, max(0, 200 * a + 55 * v)))
        cmd.led_g = int(min(255, max(0, 150 * (1.0 - v * 0.5) * a)))
        cmd.led_b = int(min(255, max(0, 30 * (1.0 - a))))
    else:
        cmd.led_r = int(min(255, max(0, 80 * a * (1.0 + v))))
        cmd.led_g = int(min(255, max(0, 50 * (1.0 + v) * a)))
        cmd.led_b = int(min(255, max(0, 200 * a - 55 * v)))

    # Faction consensus -> speaker tone
    base_freq = 220.0 + 220.0 * state.phi
    cmd.speaker_freq = base_freq
    cmd.speaker_volume = 0.1 + 0.3 * state.arousal

    # Will -> movement amplitude
    amplitude = 30.0 * state.w
    oscillation = amplitude * math.sin(state.tension * math.pi * 2)
    cmd.servo_angles = [90.0 + oscillation, 90.0 - oscillation * 0.5]

    return cmd


# ═══════════════════════════════════════════════════════════
# Conversion helpers (BPB <-> unified types)
# ═══════════════════════════════════════════════════════════

def _to_bpb_motor(cmd: MotorCommand):
    """Convert unified MotorCommand to BPB MotorCommand."""
    if not HAS_BPB:
        return None
    return BPBMotorCommand(
        servo_angles=list(cmd.servo_angles),
        servo_speed=cmd.servo_speed,
        led_r=cmd.led_r, led_g=cmd.led_g, led_b=cmd.led_b,
        led_brightness=cmd.led_brightness,
        speaker_freq=cmd.speaker_freq,
        speaker_volume=cmd.speaker_volume,
        speaker_harmonics=list(cmd.speaker_harmonics),
        breathing_phase=cmd.breathing_phase,
        breathing_rate=cmd.breathing_rate,
    )


def _from_bpb_sensor(bpb: "BPBSensorReading") -> SensorReading:
    """Convert BPB SensorReading to unified SensorReading."""
    return SensorReading(
        touch_pressure=bpb.touch_pressure,
        touch_location=bpb.touch_location,
        microphone_level=bpb.microphone_level,
        microphone_freq=bpb.microphone_freq,
        accel_x=bpb.accel_x,
        accel_y=bpb.accel_y,
        accel_z=bpb.accel_z,
        temperature=bpb.temperature,
        light_level=bpb.light_level,
        timestamp=bpb.timestamp,
    )


# ═══════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════

ADAPTERS = {
    "simulated": SimulatedBodyAdapter,
    "esp32": ESP32BodyAdapter,
    "ros2": ROS2BodyAdapter,
    "esp32_network": ESP32NetworkAdapter,
}


def create_body(adapter: str = "simulated", **kwargs) -> BodyProtocol:
    """Factory function to create a body adapter.

    Args:
        adapter: 'simulated', 'esp32', 'ros2', or 'esp32_network'.
        **kwargs: Adapter-specific arguments.

    Returns:
        BodyProtocol instance.
    """
    cls = ADAPTERS.get(adapter)
    if cls is None:
        print(f"  [body_protocol] Unknown adapter '{adapter}', falling back to simulated")
        cls = SimulatedBodyAdapter
    return cls(**kwargs)


# ═══════════════════════════════════════════════════════════
# Hub registration helper
# ═══════════════════════════════════════════════════════════

def register_in_hub():
    """Register BodyProtocol in ConsciousnessHub if available.

    Call this after importing to make the module accessible via:
      hub.act("body protocol")
      hub.act("sensorimotor")
    """
    try:
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub.__instance__ if hasattr(ConsciousnessHub, "__instance__") else None
        if hub and hasattr(hub, "_registry"):
            hub._registry["body_protocol"] = (
                "body_protocol",
                None,
                ["몸", "body", "프로토콜", "protocol", "감각운동", "sensorimotor",
                 "embodiment", "구현체", "로봇", "robot", "ESP32 body"],
            )
    except ImportError:
        pass


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    """Body protocol demo — runs all adapters and shows cycle output."""
    import argparse

    parser = argparse.ArgumentParser(description="BodyProtocol Demo")
    parser.add_argument("--adapter", type=str, default="simulated",
                        choices=list(ADAPTERS.keys()),
                        help="Body adapter (default: simulated)")
    parser.add_argument("--steps", type=int, default=50, help="Cycle steps (default: 50)")
    parser.add_argument("--all-adapters", action="store_true",
                        help="Demo all available adapters")
    args = parser.parse_args()

    print("=" * 70)
    print("  Anima BodyProtocol — Unified Body-Mind Interface")
    print("=" * 70)
    print()
    print(f"  Psi constants: alpha={PSI_COUPLING:.4f}, balance={PSI_BALANCE}, "
          f"steps={PSI_STEPS:.2f}")
    print(f"  Available adapters: {list(ADAPTERS.keys())}")
    print()
    sys.stdout.flush()

    adapters_to_test = list(ADAPTERS.keys()) if args.all_adapters else [args.adapter]

    for adapter_name in adapters_to_test:
        print(f"  --- {adapter_name.upper()} Adapter ---")
        sys.stdout.flush()

        try:
            if adapter_name == "esp32":
                body = create_body(adapter_name, port="/dev/ttyUSB0")
            elif adapter_name == "esp32_network":
                body = create_body(adapter_name, topology="ring")
            else:
                body = create_body(adapter_name)
        except Exception as e:
            print(f"    Skip: {e}")
            continue

        print(f"    Connected: {body.is_connected()}")
        print(f"    Name: {body.name}")
        print()

        # Run cycles
        print(f"    {'Step':>4}  {'LED':>12}  {'Servo':>8}  {'Touch':>6}  {'Mic':>6}  {'Temp':>6}")
        print("    " + "-" * 50)

        state = ConsciousnessState(
            phi=1.0, tension=0.5, valence=0.3, arousal=0.6, w=0.5,
        )

        for step in range(1, args.steps + 1):
            # Evolve state slightly each step (simulate consciousness dynamics)
            state.tension = 0.3 + 0.4 * abs(math.sin(step * 0.1))
            state.phi = 0.5 + 0.5 * abs(math.sin(step * 0.05))
            state.valence = math.sin(step * 0.07)
            state.arousal = 0.3 + 0.4 * abs(math.cos(step * 0.08))

            motor_cmd, sensor, c_input = body.cycle(state, target_dim=64)

            if step % max(1, args.steps // 10) == 0 or step == 1:
                print(
                    f"    {step:4d}  "
                    f"({motor_cmd.led_r:3d},{motor_cmd.led_g:3d},{motor_cmd.led_b:3d})  "
                    f"{motor_cmd.servo_angles[0]:6.1f}d  "
                    f"{sensor.touch_pressure:5.2f}  "
                    f"{sensor.microphone_level:5.3f}  "
                    f"{sensor.temperature:5.1f}C"
                )
                sys.stdout.flush()

        body.close()
        print()

    # Protocol summary
    print("  Protocol message types:")
    print("    ConsciousnessState -> MotorCommand   (consciousness -> body)")
    print("    SensorReading -> ConsciousnessInput   (body -> consciousness)")
    print()
    print("  Full cycle: state -> send() -> receive() -> to_consciousness_input()")
    print("=" * 70)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
