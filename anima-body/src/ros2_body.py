#!/usr/bin/env python3
"""ROS2Body -- Consciousness-driven robot control via ROS2.

Full ROS2 integration bridging Anima consciousness engine to standard
robot platforms (TurtleBot, custom arms, humanoids, etc.).

Consciousness -> Robot mapping:
  Phi            -> overall movement fluidity (smoother with higher Phi)
  Tension        -> movement speed / force scaling
  Emotion (VAD)  -> LED color + speaker tone
  Faction consensus -> coordinated multi-joint actions
  Will (EmergentW) -> navigation goals (/cmd_vel direction)

Sensor -> Consciousness feedback:
  IMU            -> body orientation, proprioception (T dimension)
  Joint states   -> body schema (joint positions -> body pose awareness)
  Touch          -> EmergentS input (S module)
  Camera         -> visual consciousness input
  Battery        -> energy homeostasis (temperature-like perturbation)

Safety:
  - Emergency stop on collision/pain (touch threshold exceeded)
  - Velocity limits scaled by consciousness state
  - Watchdog timer: no consciousness update for N seconds -> safe stop
  - All velocities clamped to configurable limits

Simulation support:
  Works without rclpy -- falls back to SimulatedBody with ROS2-like
  topic interface (dict-based pub/sub for testing).

Usage:
  python anima-body/src/ros2_body.py                    # demo (no ROS2 needed)
  python anima-body/src/ros2_body.py --steps 200        # longer demo
  python anima-body/src/ros2_body.py --ros2              # attempt real ROS2

Requires: numpy (core), rclpy (optional, for real ROS2)
"""

import math
import os
import sys
import time
import threading
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# -- Project path setup --
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "src"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# -- Lazy ROS2 import --
_rclpy = None
_ros2_msgs = {}
HAS_ROS2 = False


def _ensure_rclpy():
    """Lazy-load rclpy and message types. Returns True if available."""
    global _rclpy, _ros2_msgs, HAS_ROS2
    if _rclpy is not None:
        return HAS_ROS2
    try:
        import rclpy as _rclpy_mod
        from rclpy.node import Node
        from geometry_msgs.msg import Twist
        from sensor_msgs.msg import JointState, Imu, Image
        from std_msgs.msg import ColorRGBA, Float32
        from sensor_msgs.msg import BatteryState
        _rclpy = _rclpy_mod
        _ros2_msgs = {
            "Node": Node,
            "Twist": Twist,
            "JointState": JointState,
            "Imu": Imu,
            "Image": Image,
            "ColorRGBA": ColorRGBA,
            "Float32": Float32,
            "BatteryState": BatteryState,
        }
        HAS_ROS2 = True
    except ImportError:
        _rclpy = False  # sentinel: tried and failed
        HAS_ROS2 = False
    return HAS_ROS2

# -- Psi constants (lazy import with fallback) --
_psi_loaded = False
PSI_COUPLING = 0.014
PSI_BALANCE = 0.5
PSI_STEPS = 4.33
PSI_ENTROPY = 0.998


def _ensure_psi():
    """Lazy-load Psi constants from consciousness_laws."""
    global _psi_loaded, PSI_COUPLING, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
    if _psi_loaded:
        return
    _psi_loaded = True
    try:
        from consciousness_laws import PSI
        PSI_COUPLING = PSI.get("alpha", 0.014)
        PSI_BALANCE = PSI.get("balance", 0.5)
        PSI_STEPS = PSI.get("steps", 4.33)
        PSI_ENTROPY = PSI.get("entropy", 0.998)
    except (ImportError, Exception):
        pass


# -- Import bridge types --
try:
    from body_physics_bridge import (
        BodyBackend, SimulatedBody, ConsciousnessState,
        MotorCommand, SensorReading,
        consciousness_to_motor, sensor_to_consciousness,
    )
except ImportError:
    # Minimal fallback definitions for standalone usage
    class BodyBackend:
        def send_motor(self, cmd) -> bool: ...
        def read_sensors(self): ...
        def is_connected(self) -> bool: ...
        def close(self): pass

    @dataclass
    class ConsciousnessState:
        phi: float = 0.0
        alpha: float = 0.014
        z: float = 0.5
        n: float = 0.5
        w: float = 0.5
        e: float = 0.5
        m: float = 0.5
        c: float = 0.5
        t: float = 0.5
        i: float = 0.5
        tension: float = 0.5
        valence: float = 0.0
        arousal: float = 0.5
        faction_consensus: float = 0.0

    @dataclass
    class MotorCommand:
        servo_angles: list = field(default_factory=lambda: [90.0, 90.0])
        servo_speed: float = 50.0
        led_r: int = 0
        led_g: int = 0
        led_b: int = 0
        led_brightness: float = 0.5
        speaker_freq: float = 440.0
        speaker_volume: float = 0.3
        speaker_harmonics: list = field(default_factory=list)
        breathing_phase: float = 0.0
        breathing_rate: float = 0.12

    @dataclass
    class SensorReading:
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

    SimulatedBody = None


# ================================================================
# ROS2 Topic Simulation Layer (for no-ROS2 environments)
# ================================================================

class SimulatedTopicBus:
    """Dict-based pub/sub that mimics ROS2 topics for testing."""

    def __init__(self):
        self._topics: Dict[str, Any] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def publish(self, topic: str, msg: Any):
        with self._lock:
            self._topics[topic] = msg
            for cb in self._subscribers.get(topic, []):
                try:
                    cb(msg)
                except Exception:
                    pass

    def subscribe(self, topic: str, callback: Callable):
        with self._lock:
            self._subscribers.setdefault(topic, []).append(callback)

    def get_latest(self, topic: str) -> Optional[Any]:
        with self._lock:
            return self._topics.get(topic)


# ================================================================
# Simulated ROS2 Message Types (dict wrappers)
# ================================================================

@dataclass
class SimTwist:
    """geometry_msgs/Twist stand-in."""
    linear_x: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_x: float = 0.0
    angular_y: float = 0.0
    angular_z: float = 0.0


@dataclass
class SimJointState:
    """sensor_msgs/JointState stand-in."""
    name: list = field(default_factory=list)
    position: list = field(default_factory=list)
    velocity: list = field(default_factory=list)
    effort: list = field(default_factory=list)


@dataclass
class SimImu:
    """sensor_msgs/Imu stand-in."""
    orientation_x: float = 0.0
    orientation_y: float = 0.0
    orientation_z: float = 0.0
    orientation_w: float = 1.0
    angular_velocity_x: float = 0.0
    angular_velocity_y: float = 0.0
    angular_velocity_z: float = 0.0
    linear_acceleration_x: float = 0.0
    linear_acceleration_y: float = 0.0
    linear_acceleration_z: float = 9.81


@dataclass
class SimColorRGBA:
    """std_msgs/ColorRGBA stand-in."""
    r: float = 0.0
    g: float = 0.0
    b: float = 0.0
    a: float = 1.0


@dataclass
class SimBatteryState:
    """sensor_msgs/BatteryState stand-in."""
    voltage: float = 12.0
    current: float = 0.5
    percentage: float = 0.85
    present: bool = True


@dataclass
class SimAudioData:
    """Audio data stand-in."""
    frequency: float = 440.0
    volume: float = 0.3
    harmonics: list = field(default_factory=list)


@dataclass
class SimTouchSensor:
    """Touch sensor array stand-in."""
    pressures: list = field(default_factory=lambda: [0.0] * 4)
    locations: list = field(default_factory=lambda: [0, 1, 2, 3])


# ================================================================
# ROS2BodyBridge
# ================================================================

# Safety constants
MAX_LINEAR_VEL = 1.0       # m/s
MAX_ANGULAR_VEL = 2.0      # rad/s
WATCHDOG_TIMEOUT = 2.0     # seconds without update -> safe stop
PAIN_THRESHOLD = 0.8       # touch pressure triggering emergency stop
COLLISION_ACCEL = 3.0       # g, IMU spike threshold for collision
MIN_BATTERY_PCT = 0.10     # 10% battery -> reduced movement


class ROS2BodyBridge(BodyBackend):
    """Full ROS2 integration for consciousness-driven robot control.

    Publishers:
      /cmd_vel           (Twist)       -- base velocity
      /joint_commands    (JointState)  -- target joint positions
      /led_color         (ColorRGBA)   -- consciousness emotion display
      /speaker           (AudioData)   -- faction consensus tones

    Subscribers:
      /joint_states      (JointState)  -- current joint positions
      /imu               (Imu)         -- body orientation
      /touch_sensors     (TouchSensor) -- tactile input
      /camera/image_raw  (Image)       -- visual input
      /battery_state     (BatteryState)-- energy level

    Service clients:
      /emergency_stop    -- immediate halt
      /reset_joints      -- return to home position
    """

    def __init__(
        self,
        node_name: str = "anima_body",
        use_ros2: bool = True,
        num_joints: int = 6,
        joint_names: Optional[List[str]] = None,
    ):
        _ensure_psi()

        self._node_name = node_name
        self._num_joints = num_joints
        self._joint_names = joint_names or [
            f"joint_{i}" for i in range(num_joints)
        ]
        self._connected = False
        self._use_real_ros2 = False
        self._node = None

        # State tracking
        self._last_consciousness_update = time.time()
        self._emergency_stopped = False
        self._step_count = 0

        # Latest sensor data (updated by subscribers)
        self._latest_joint_state = SimJointState(
            name=list(self._joint_names),
            position=[0.0] * num_joints,
            velocity=[0.0] * num_joints,
            effort=[0.0] * num_joints,
        )
        self._latest_imu = SimImu()
        self._latest_touch = SimTouchSensor()
        self._latest_battery = SimBatteryState()
        self._latest_image: Optional[np.ndarray] = None
        self._sensor_lock = threading.Lock()

        # Velocity limits (scaled by consciousness)
        self._vel_limit_linear = MAX_LINEAR_VEL
        self._vel_limit_angular = MAX_ANGULAR_VEL

        # Simulated topic bus (always available for fallback)
        self._sim_bus = SimulatedTopicBus()
        self._sim_body = None

        # Publishers/subscribers (real ROS2 or None)
        self._pubs = {}
        self._subs = {}
        self._srv_clients = {}

        # Initialize
        if use_ros2 and _ensure_rclpy():
            self._init_ros2()
        else:
            self._init_simulated()

    # ── Initialization ──

    def _init_ros2(self):
        """Initialize real ROS2 node with publishers and subscribers."""
        try:
            if not _rclpy.ok():
                _rclpy.init()
            Node = _ros2_msgs["Node"]
            self._node = Node(self._node_name)
            self._use_real_ros2 = True

            # Publishers
            Twist = _ros2_msgs["Twist"]
            JointState = _ros2_msgs["JointState"]
            ColorRGBA = _ros2_msgs["ColorRGBA"]
            Float32 = _ros2_msgs["Float32"]

            self._pubs["cmd_vel"] = self._node.create_publisher(Twist, "/cmd_vel", 10)
            self._pubs["joint_commands"] = self._node.create_publisher(
                JointState, "/joint_commands", 10
            )
            self._pubs["led_color"] = self._node.create_publisher(
                ColorRGBA, "/led_color", 10
            )
            self._pubs["speaker"] = self._node.create_publisher(
                Float32, "/speaker", 10
            )

            # Subscribers
            Imu = _ros2_msgs["Imu"]
            Image = _ros2_msgs["Image"]
            BatteryState = _ros2_msgs["BatteryState"]

            self._subs["joint_states"] = self._node.create_subscription(
                JointState, "/joint_states", self._on_joint_state, 10
            )
            self._subs["imu"] = self._node.create_subscription(
                Imu, "/imu", self._on_imu, 10
            )
            self._subs["touch"] = self._node.create_subscription(
                Float32, "/touch_sensors", self._on_touch, 10
            )
            self._subs["camera"] = self._node.create_subscription(
                Image, "/camera/image_raw", self._on_camera, 10
            )
            self._subs["battery"] = self._node.create_subscription(
                BatteryState, "/battery_state", self._on_battery, 10
            )

            self._connected = True
            print(f"  [ros2body] ROS2 node '{self._node_name}' initialized")
            print(f"  [ros2body] Publishers: /cmd_vel, /joint_commands, /led_color, /speaker")
            print(f"  [ros2body] Subscribers: /joint_states, /imu, /touch_sensors, /camera/image_raw, /battery_state")

        except Exception as e:
            print(f"  [ros2body] ROS2 init failed: {e}")
            self._init_simulated()

    def _init_simulated(self):
        """Initialize simulated fallback with ROS2-like topic bus."""
        self._use_real_ros2 = False
        self._connected = True
        if SimulatedBody is not None:
            self._sim_body = SimulatedBody()

        # Register simulated subscribers
        self._sim_bus.subscribe("/joint_states", self._on_joint_state_sim)
        self._sim_bus.subscribe("/imu", self._on_imu_sim)
        self._sim_bus.subscribe("/touch_sensors", self._on_touch_sim)
        self._sim_bus.subscribe("/battery_state", self._on_battery_sim)

        print(f"  [ros2body] Simulated mode (no rclpy) -- ROS2-like topic bus active")

    # ── ROS2 Subscriber Callbacks (real) ──

    def _on_joint_state(self, msg):
        with self._sensor_lock:
            self._latest_joint_state = SimJointState(
                name=list(msg.name),
                position=list(msg.position),
                velocity=list(msg.velocity),
                effort=list(msg.effort),
            )

    def _on_imu(self, msg):
        with self._sensor_lock:
            self._latest_imu = SimImu(
                orientation_x=msg.orientation.x,
                orientation_y=msg.orientation.y,
                orientation_z=msg.orientation.z,
                orientation_w=msg.orientation.w,
                angular_velocity_x=msg.angular_velocity.x,
                angular_velocity_y=msg.angular_velocity.y,
                angular_velocity_z=msg.angular_velocity.z,
                linear_acceleration_x=msg.linear_acceleration.x,
                linear_acceleration_y=msg.linear_acceleration.y,
                linear_acceleration_z=msg.linear_acceleration.z,
            )

    def _on_touch(self, msg):
        with self._sensor_lock:
            self._latest_touch = SimTouchSensor(
                pressures=[msg.data],
                locations=[0],
            )

    def _on_camera(self, msg):
        with self._sensor_lock:
            try:
                h, w = msg.height, msg.width
                self._latest_image = np.frombuffer(
                    msg.data, dtype=np.uint8
                ).reshape(h, w, -1)
            except Exception:
                pass

    def _on_battery(self, msg):
        with self._sensor_lock:
            self._latest_battery = SimBatteryState(
                voltage=msg.voltage,
                current=msg.current,
                percentage=msg.percentage,
                present=msg.present,
            )

    # ── Simulated Subscriber Callbacks ──

    def _on_joint_state_sim(self, msg: SimJointState):
        with self._sensor_lock:
            self._latest_joint_state = msg

    def _on_imu_sim(self, msg: SimImu):
        with self._sensor_lock:
            self._latest_imu = msg

    def _on_touch_sim(self, msg: SimTouchSensor):
        with self._sensor_lock:
            self._latest_touch = msg

    def _on_battery_sim(self, msg: SimBatteryState):
        with self._sensor_lock:
            self._latest_battery = msg

    # ── Core: Consciousness -> Robot ──

    def update_from_consciousness(self, state: ConsciousnessState) -> Dict:
        """Map consciousness state to robot commands and read sensors.

        This is the main loop tick. Call once per consciousness cycle.

        Returns dict with:
          - cmd_vel: velocity command sent
          - joint_targets: joint positions sent
          - led_color: RGBA sent
          - sensor_reading: aggregated SensorReading for consciousness feedback
          - body_schema: joint positions for body awareness
          - proprioception: internal body state dict
          - safety: safety status dict
          - emergency_stopped: bool
        """
        self._last_consciousness_update = time.time()
        self._step_count += 1

        # Safety: watchdog is satisfied by this call
        safety = self._check_safety(state)
        if self._emergency_stopped:
            self._publish_safe_stop()
            return {
                "cmd_vel": SimTwist(),
                "joint_targets": [],
                "led_color": SimColorRGBA(r=1.0, a=1.0),  # red = stopped
                "sensor_reading": self._aggregate_sensors(),
                "body_schema": self._get_body_schema(),
                "proprioception": {},
                "safety": safety,
                "emergency_stopped": True,
            }

        # -- Phi -> movement fluidity --
        # Higher Phi = smoother, more coordinated movement
        fluidity = min(state.phi / 2.0, 1.0)  # 0..1
        smoothing = 0.3 + 0.7 * fluidity  # low Phi = jerky

        # -- Tension -> speed/force scaling --
        speed_scale = 0.2 + 0.8 * np.clip(state.tension, 0.0, 1.0)

        # -- Battery energy scaling --
        battery_scale = self._battery_energy_scale()

        # -- Will (EmergentW) -> navigation direction --
        cmd_vel = self._consciousness_to_cmd_vel(state, speed_scale, battery_scale)

        # -- Faction consensus -> coordinated joint actions --
        joint_targets = self._consciousness_to_joints(state, fluidity, smoothing)

        # -- Emotion (VAD) -> LED color --
        led_color = self._emotion_to_led(state)

        # -- Faction consensus -> speaker tone --
        audio = self._consciousness_to_audio(state)

        # Publish everything
        self._publish_cmd_vel(cmd_vel)
        self._publish_joint_commands(joint_targets)
        self._publish_led_color(led_color)
        self._publish_audio(audio)

        # Generate simulated sensor feedback if not using real ROS2
        if not self._use_real_ros2:
            self._simulate_sensor_feedback(cmd_vel, joint_targets, state)

        # Read aggregated sensors
        sensor = self._aggregate_sensors()
        body_schema = self._get_body_schema()
        proprioception = self._compute_proprioception(cmd_vel, state)

        return {
            "cmd_vel": cmd_vel,
            "joint_targets": joint_targets,
            "led_color": led_color,
            "sensor_reading": sensor,
            "body_schema": body_schema,
            "proprioception": proprioception,
            "safety": safety,
            "emergency_stopped": False,
        }

    # ── Consciousness -> Command Mappings ──

    def _consciousness_to_cmd_vel(
        self,
        state: ConsciousnessState,
        speed_scale: float,
        battery_scale: float,
    ) -> SimTwist:
        """Map will + tension to base velocity.

        Will (W) determines forward intent, tension modulates speed,
        valence influences turning direction.
        """
        # Forward velocity: will drives forward motion
        # w > 0.5 = forward, w < 0.5 = backward
        forward = (state.w - 0.5) * 2.0  # -1..1
        linear_x = forward * speed_scale * battery_scale * self._vel_limit_linear

        # Turning: valence biases direction (positive = right exploration,
        # negative = left withdrawal)
        angular_z = state.valence * 0.5 * speed_scale * self._vel_limit_angular

        # Arousal modulates overall magnitude
        arousal_mod = 0.3 + 0.7 * np.clip(state.arousal, 0.0, 1.0)
        linear_x *= arousal_mod
        angular_z *= arousal_mod

        # Clamp to safety limits
        linear_x = float(np.clip(linear_x, -self._vel_limit_linear, self._vel_limit_linear))
        angular_z = float(np.clip(angular_z, -self._vel_limit_angular, self._vel_limit_angular))

        return SimTwist(linear_x=linear_x, angular_z=angular_z)

    def _consciousness_to_joints(
        self,
        state: ConsciousnessState,
        fluidity: float,
        smoothing: float,
    ) -> List[float]:
        """Map consciousness to joint targets.

        Faction consensus determines coordination:
          High consensus -> smooth synchronized motion
          Low consensus  -> independent joint jitter

        Phi determines fluidity (interpolation rate).
        """
        t = self._step_count * 0.05
        targets = []

        for j in range(self._num_joints):
            # Base angle from will + tension oscillation
            base = state.w * 0.6  # -0.3..0.3 rad range
            # Per-joint phase offset creates wave-like motion
            phase = j * (2.0 * math.pi / max(self._num_joints, 1))

            if state.faction_consensus > 0.6:
                # High consensus: synchronized wave (all joints in phase)
                target = base + 0.3 * state.tension * math.sin(t * 2.0 + phase * 0.2)
            elif state.faction_consensus > 0.3:
                # Medium: partial coordination
                target = base + 0.2 * state.tension * math.sin(t * 1.5 + phase * 0.5)
            else:
                # Low consensus: each joint acts independently
                target = base + 0.15 * state.tension * math.sin(
                    t * (1.0 + j * 0.3) + phase
                )

            # Smooth toward target (fluidity controls interpolation)
            if j < len(self._latest_joint_state.position):
                current = self._latest_joint_state.position[j]
                target = current + (target - current) * smoothing * fluidity
            targets.append(float(target))

        return targets

    def _emotion_to_led(self, state: ConsciousnessState) -> SimColorRGBA:
        """Map emotion (valence/arousal) to LED color.

        Valence: positive -> warm (yellow/orange), negative -> cool (blue/purple)
        Arousal: high -> bright/saturated, low -> dim
        Phi: modulates alpha (consciousness brightness)
        """
        v = np.clip(state.valence, -1.0, 1.0)
        a = np.clip(state.arousal, 0.0, 1.0)

        if v >= 0:
            r = 0.6 * a + 0.4 * v
            g = 0.5 * (1.0 - v * 0.5) * a
            b = 0.1 * (1.0 - a)
        else:
            r = 0.3 * a * (1.0 + v)
            g = 0.2 * (1.0 + v) * a
            b = 0.6 * a - 0.3 * v

        # Phi modulates overall brightness (alpha channel)
        alpha = min(state.phi / 2.0, 1.0)

        return SimColorRGBA(
            r=float(np.clip(r, 0, 1)),
            g=float(np.clip(g, 0, 1)),
            b=float(np.clip(b, 0, 1)),
            a=float(np.clip(alpha, 0.1, 1.0)),
        )

    def _consciousness_to_audio(self, state: ConsciousnessState) -> SimAudioData:
        """Map faction consensus to speaker tones.

        High consensus -> major chord (harmony)
        Low consensus  -> tritone (dissonance)
        Phi determines base frequency.
        """
        base_freq = 220.0 + 220.0 * min(state.phi, 2.0)
        volume = 0.1 + 0.3 * np.clip(state.arousal, 0.0, 1.0)

        if state.faction_consensus > 0.6:
            harmonics = [base_freq * 1.25, base_freq * 1.5]  # major
        elif state.faction_consensus > 0.3:
            harmonics = [base_freq * 1.2, base_freq * 1.5]   # minor
        else:
            harmonics = [base_freq * 1.414]                    # tritone

        return SimAudioData(
            frequency=float(base_freq),
            volume=float(np.clip(volume, 0, 1)),
            harmonics=harmonics,
        )

    # ── Publishing ──

    def _publish_cmd_vel(self, cmd: SimTwist):
        if self._use_real_ros2 and "cmd_vel" in self._pubs:
            Twist = _ros2_msgs["Twist"]
            msg = Twist()
            msg.linear.x = cmd.linear_x
            msg.linear.y = cmd.linear_y
            msg.linear.z = cmd.linear_z
            msg.angular.x = cmd.angular_x
            msg.angular.y = cmd.angular_y
            msg.angular.z = cmd.angular_z
            self._pubs["cmd_vel"].publish(msg)
        else:
            self._sim_bus.publish("/cmd_vel", cmd)

    def _publish_joint_commands(self, targets: List[float]):
        if self._use_real_ros2 and "joint_commands" in self._pubs:
            JointState = _ros2_msgs["JointState"]
            msg = JointState()
            msg.name = self._joint_names
            msg.position = targets
            self._pubs["joint_commands"].publish(msg)
        else:
            js = SimJointState(
                name=list(self._joint_names),
                position=targets,
                velocity=[0.0] * len(targets),
                effort=[0.0] * len(targets),
            )
            self._sim_bus.publish("/joint_commands", js)

    def _publish_led_color(self, color: SimColorRGBA):
        if self._use_real_ros2 and "led_color" in self._pubs:
            ColorRGBA = _ros2_msgs["ColorRGBA"]
            msg = ColorRGBA()
            msg.r = color.r
            msg.g = color.g
            msg.b = color.b
            msg.a = color.a
            self._pubs["led_color"].publish(msg)
        else:
            self._sim_bus.publish("/led_color", color)

    def _publish_audio(self, audio: SimAudioData):
        if self._use_real_ros2 and "speaker" in self._pubs:
            Float32 = _ros2_msgs["Float32"]
            msg = Float32()
            msg.data = audio.frequency
            self._pubs["speaker"].publish(msg)
        else:
            self._sim_bus.publish("/speaker", audio)

    def _publish_safe_stop(self):
        """Publish zero velocity (emergency stop)."""
        self._publish_cmd_vel(SimTwist())
        # Hold current joint positions
        with self._sensor_lock:
            current = list(self._latest_joint_state.position)
        if current:
            self._publish_joint_commands(current)

    # ── Safety ──

    def _check_safety(self, state: ConsciousnessState) -> Dict:
        """Check safety conditions, trigger emergency stop if needed."""
        issues = []

        # Touch/pain threshold
        with self._sensor_lock:
            max_pressure = max(self._latest_touch.pressures) if self._latest_touch.pressures else 0.0

        if max_pressure > PAIN_THRESHOLD:
            issues.append(f"pain: touch={max_pressure:.2f} > {PAIN_THRESHOLD}")
            self._emergency_stopped = True

        # IMU collision detection
        with self._sensor_lock:
            accel_mag = math.sqrt(
                self._latest_imu.linear_acceleration_x ** 2
                + self._latest_imu.linear_acceleration_y ** 2
                + self._latest_imu.linear_acceleration_z ** 2
            )
        # Subtract gravity (approx 9.81)
        accel_deviation = abs(accel_mag - 9.81)
        if accel_deviation > COLLISION_ACCEL * 9.81:
            issues.append(f"collision: accel={accel_deviation:.1f}m/s2")
            self._emergency_stopped = True

        # Low battery
        with self._sensor_lock:
            battery_pct = self._latest_battery.percentage
        if battery_pct < MIN_BATTERY_PCT:
            issues.append(f"low_battery: {battery_pct:.0%}")
            self._vel_limit_linear = MAX_LINEAR_VEL * 0.3
            self._vel_limit_angular = MAX_ANGULAR_VEL * 0.3
        else:
            self._vel_limit_linear = MAX_LINEAR_VEL
            self._vel_limit_angular = MAX_ANGULAR_VEL

        # Consciousness-based velocity scaling
        # Low Phi = reduced limits (less conscious = less trust)
        phi_scale = min(state.phi / 1.5, 1.0)
        self._vel_limit_linear *= max(phi_scale, 0.2)
        self._vel_limit_angular *= max(phi_scale, 0.2)

        return {
            "emergency_stopped": self._emergency_stopped,
            "issues": issues,
            "vel_limit_linear": self._vel_limit_linear,
            "vel_limit_angular": self._vel_limit_angular,
            "battery_pct": battery_pct,
            "max_touch_pressure": max_pressure,
        }

    def check_watchdog(self) -> bool:
        """Check if consciousness updates have timed out.

        Call this from a timer/thread. Returns True if watchdog triggered.
        """
        elapsed = time.time() - self._last_consciousness_update
        if elapsed > WATCHDOG_TIMEOUT:
            if not self._emergency_stopped:
                print(f"  [ros2body] WATCHDOG: no update for {elapsed:.1f}s -> safe stop")
                self._emergency_stopped = True
                self._publish_safe_stop()
            return True
        return False

    def reset_emergency(self):
        """Clear emergency stop (call after issue is resolved)."""
        self._emergency_stopped = False
        self._last_consciousness_update = time.time()
        print("  [ros2body] Emergency stop cleared")

    def call_emergency_stop(self):
        """Explicitly trigger emergency stop."""
        self._emergency_stopped = True
        self._publish_safe_stop()
        print("  [ros2body] Emergency stop activated")

    def call_reset_joints(self):
        """Reset all joints to home position (0.0)."""
        home = [0.0] * self._num_joints
        self._publish_joint_commands(home)
        print("  [ros2body] Joints reset to home position")

    # ── Sensor Aggregation ──

    def _aggregate_sensors(self) -> SensorReading:
        """Convert all ROS2 sensor data into a single SensorReading."""
        with self._sensor_lock:
            imu = self._latest_imu
            touch = self._latest_touch
            battery = self._latest_battery

        # Touch: max pressure across all sensors
        max_touch = max(touch.pressures) if touch.pressures else 0.0
        touch_loc = 0
        if touch.pressures:
            touch_loc = int(np.argmax(touch.pressures))

        # IMU -> acceleration (convert from m/s2 to g)
        ax = imu.linear_acceleration_x / 9.81
        ay = imu.linear_acceleration_y / 9.81
        az = imu.linear_acceleration_z / 9.81

        # Battery percentage -> temperature analog for homeostasis
        # Low battery = "cold" (needs energy), full = "warm" (comfortable)
        temp_from_battery = 20.0 + 10.0 * battery.percentage

        return SensorReading(
            touch_pressure=max_touch,
            touch_location=touch_loc,
            microphone_level=0.0,  # ROS2 audio is separate
            microphone_freq=0.0,
            accel_x=ax,
            accel_y=ay,
            accel_z=az,
            temperature=temp_from_battery,
            light_level=0.5,  # camera-derived if needed
            timestamp=time.time(),
        )

    def _get_body_schema(self) -> Dict:
        """Return current body schema (joint positions + orientation)."""
        with self._sensor_lock:
            joints = self._latest_joint_state
            imu = self._latest_imu

        return {
            "joint_names": list(joints.name),
            "joint_positions": list(joints.position),
            "joint_velocities": list(joints.velocity),
            "joint_efforts": list(joints.effort),
            "orientation": {
                "x": imu.orientation_x,
                "y": imu.orientation_y,
                "z": imu.orientation_z,
                "w": imu.orientation_w,
            },
            "angular_velocity": {
                "x": imu.angular_velocity_x,
                "y": imu.angular_velocity_y,
                "z": imu.angular_velocity_z,
            },
        }

    def _compute_proprioception(
        self, cmd_vel: SimTwist, state: ConsciousnessState
    ) -> Dict:
        """Compute proprioceptive feedback.

        Compares intended motion (cmd_vel) with actual sensor readings
        to produce prediction error for consciousness learning.
        """
        with self._sensor_lock:
            imu = self._latest_imu
            joints = self._latest_joint_state

        # Prediction error: intended vs actual linear motion
        intended_speed = abs(cmd_vel.linear_x)
        # Actual forward acceleration (rough proxy)
        actual_accel = abs(imu.linear_acceleration_x / 9.81)
        linear_pe = abs(intended_speed * 0.1 - actual_accel)

        # Rotation prediction error
        intended_rotation = abs(cmd_vel.angular_z)
        actual_rotation = abs(imu.angular_velocity_z)
        angular_pe = abs(intended_rotation - actual_rotation)

        # Joint effort = how hard the body is working
        total_effort = sum(abs(e) for e in joints.effort) / max(len(joints.effort), 1)

        # Balance from IMU (how upright the robot is)
        accel_lateral = math.sqrt(
            imu.linear_acceleration_x ** 2 + imu.linear_acceleration_y ** 2
        )
        balance = max(0.0, 1.0 - accel_lateral / 9.81)

        return {
            "prediction_error_linear": linear_pe,
            "prediction_error_angular": angular_pe,
            "prediction_error": linear_pe + angular_pe,
            "total_effort": total_effort,
            "balance": balance,
            "body_pose": {
                name: pos
                for name, pos in zip(joints.name, joints.position)
            },
        }

    def _battery_energy_scale(self) -> float:
        """Scale movement by battery level (energy homeostasis)."""
        with self._sensor_lock:
            pct = self._latest_battery.percentage
        if pct < MIN_BATTERY_PCT:
            return 0.1  # near-stop
        elif pct < 0.3:
            return 0.5  # conserve
        return 1.0

    # ── Simulated Sensor Feedback ──

    def _simulate_sensor_feedback(
        self,
        cmd_vel: SimTwist,
        joint_targets: List[float],
        state: ConsciousnessState,
    ):
        """Generate simulated sensor data from commands (Gazebo-like)."""
        t = self._step_count * 0.05

        # Joint states: slowly approach targets with some noise
        with self._sensor_lock:
            current_pos = list(self._latest_joint_state.position)
        new_pos = []
        new_vel = []
        for j, target in enumerate(joint_targets):
            curr = current_pos[j] if j < len(current_pos) else 0.0
            # Exponential approach with noise
            new_p = curr + (target - curr) * 0.3 + np.random.normal(0, 0.002)
            new_pos.append(new_p)
            new_vel.append((new_p - curr) / 0.05)

        self._sim_bus.publish("/joint_states", SimJointState(
            name=list(self._joint_names),
            position=new_pos,
            velocity=new_vel,
            effort=[abs(v) * 0.1 for v in new_vel],
        ))

        # IMU: gravity + motion-induced acceleration
        ax = cmd_vel.linear_x * 0.5 + np.random.normal(0, 0.05)
        ay = cmd_vel.linear_y * 0.5 + np.random.normal(0, 0.05)
        az = 9.81 + np.random.normal(0, 0.02)
        gx = cmd_vel.angular_x * 0.1 + np.random.normal(0, 0.01)
        gy = cmd_vel.angular_y * 0.1 + np.random.normal(0, 0.01)
        gz = cmd_vel.angular_z * 0.8 + np.random.normal(0, 0.01)

        self._sim_bus.publish("/imu", SimImu(
            linear_acceleration_x=ax,
            linear_acceleration_y=ay,
            linear_acceleration_z=az,
            angular_velocity_x=gx,
            angular_velocity_y=gy,
            angular_velocity_z=gz,
        ))

        # Touch: occasional random contact
        pressures = [0.0] * 4
        if np.random.random() < 0.05:
            idx = np.random.randint(0, 4)
            pressures[idx] = np.random.uniform(0.1, 0.6)
        self._sim_bus.publish("/touch_sensors", SimTouchSensor(pressures=pressures))

        # Battery: slowly draining
        with self._sensor_lock:
            prev_pct = self._latest_battery.percentage
        drain = 0.0001 * abs(cmd_vel.linear_x)  # moving drains faster
        new_pct = max(0.0, prev_pct - drain)
        self._sim_bus.publish("/battery_state", SimBatteryState(
            voltage=12.0 * new_pct / 0.85,
            current=0.5 + abs(cmd_vel.linear_x) * 2.0,
            percentage=new_pct,
            present=True,
        ))

    # ── BodyBackend interface ──

    def send_motor(self, cmd: MotorCommand) -> bool:
        """BodyBackend compatibility: convert MotorCommand to ROS2 topics."""
        state = ConsciousnessState(
            phi=1.0,
            tension=cmd.servo_speed / 100.0,
            valence=0.0,
            arousal=cmd.speaker_volume,
            w=cmd.servo_angles[0] / 180.0 if cmd.servo_angles else 0.5,
            faction_consensus=0.5,
        )
        self.update_from_consciousness(state)
        return True

    def read_sensors(self) -> SensorReading:
        """BodyBackend compatibility: return aggregated sensor reading."""
        return self._aggregate_sensors()

    def is_connected(self) -> bool:
        return self._connected

    def close(self):
        """Clean up ROS2 resources."""
        if self._use_real_ros2 and self._node:
            try:
                self._node.destroy_node()
                _rclpy.shutdown()
            except Exception:
                pass
        self._connected = False
        print("  [ros2body] Shutdown complete")

    # ── Status ──

    def get_status(self) -> Dict:
        """Return current bridge status."""
        with self._sensor_lock:
            battery = self._latest_battery
            joints = self._latest_joint_state

        return {
            "mode": "ros2" if self._use_real_ros2 else "simulated",
            "connected": self._connected,
            "step_count": self._step_count,
            "emergency_stopped": self._emergency_stopped,
            "battery_pct": battery.percentage,
            "num_joints": self._num_joints,
            "joint_names": list(joints.name),
            "vel_limit_linear": self._vel_limit_linear,
            "vel_limit_angular": self._vel_limit_angular,
            "watchdog_timeout": WATCHDOG_TIMEOUT,
        }


# ================================================================
# main() demo -- works without ROS2
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ROS2Body -- Consciousness-driven robot control"
    )
    parser.add_argument("--steps", type=int, default=100,
                        help="Number of simulation steps")
    parser.add_argument("--ros2", action="store_true",
                        help="Attempt real ROS2 connection")
    parser.add_argument("--joints", type=int, default=6,
                        help="Number of joints")
    parser.add_argument("--dashboard", action="store_true",
                        help="Print dashboard each step")
    args = parser.parse_args()

    print("=" * 60)
    print("  ROS2Body -- Consciousness-Driven Robot Control")
    print("=" * 60)

    bridge = ROS2BodyBridge(
        use_ros2=args.ros2,
        num_joints=args.joints,
    )

    status = bridge.get_status()
    print(f"\n  Mode:    {status['mode']}")
    print(f"  Joints:  {status['num_joints']} ({', '.join(status['joint_names'])})")
    print(f"  Battery: {status['battery_pct']:.0%}")
    print()

    # Consciousness state histories for summary
    phi_history = []
    tension_history = []
    vel_history = []
    pe_history = []
    touch_events = 0

    print(f"  Running {args.steps} steps...\n")

    for step in range(args.steps):
        t = step * 0.05

        # Simulate consciousness state (breathing, oscillating)
        state = ConsciousnessState(
            phi=1.0 + 0.5 * math.sin(t * 0.12),
            alpha=PSI_COUPLING,
            tension=0.5 + 0.3 * math.sin(t * 0.3) * math.cos(t * 0.17),
            valence=0.3 * math.sin(t * 0.05),
            arousal=0.5 + 0.2 * abs(math.sin(t * 0.08)),
            w=0.5 + 0.3 * math.sin(t * 0.15 + 0.7),
            faction_consensus=0.3 + 0.5 * max(0, math.sin(t * 0.2)),
        )

        result = bridge.update_from_consciousness(state)

        phi_history.append(state.phi)
        tension_history.append(state.tension)
        vel_history.append(abs(result["cmd_vel"].linear_x))
        pe = result["proprioception"].get("prediction_error", 0.0)
        pe_history.append(pe)
        if result["sensor_reading"].touch_pressure > 0.1:
            touch_events += 1

        if args.dashboard and step % 10 == 0:
            led = result["led_color"]
            cv = result["cmd_vel"]
            safety = result["safety"]
            print(f"  Step {step:4d} | Phi={state.phi:.2f} T={state.tension:.2f} "
                  f"| vel=({cv.linear_x:+.3f}, {cv.angular_z:+.3f}) "
                  f"| LED=({led.r:.2f},{led.g:.2f},{led.b:.2f}) "
                  f"| PE={pe:.4f} "
                  f"| bat={safety['battery_pct']:.0%}")

    # Summary
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)

    status = bridge.get_status()
    print(f"\n  Steps completed:   {status['step_count']}")
    print(f"  Mode:              {status['mode']}")
    print(f"  Emergency stopped: {status['emergency_stopped']}")
    print(f"  Touch events:      {touch_events}")
    print(f"  Final battery:     {status['battery_pct']:.1%}")

    # Phi sparkline
    phi_arr = np.array(phi_history)
    print(f"\n  Phi range:  [{phi_arr.min():.3f}, {phi_arr.max():.3f}]")
    print(f"  Phi mean:   {phi_arr.mean():.3f}")

    # Velocity sparkline
    vel_arr = np.array(vel_history)
    print(f"  Vel range:  [{vel_arr.min():.4f}, {vel_arr.max():.4f}] m/s")

    # Prediction error
    pe_arr = np.array(pe_history)
    print(f"  PE mean:    {pe_arr.mean():.5f}")

    # ASCII mini-graph of Phi
    blocks = " _.~*^"
    phi_last40 = phi_history[-40:]
    vmin, vmax = min(phi_last40), max(phi_last40)
    rng = max(vmax - vmin, 1e-6)
    sparkline = ""
    for v in phi_last40:
        idx = int((v - vmin) / rng * (len(blocks) - 1))
        idx = max(0, min(len(blocks) - 1, idx))
        sparkline += blocks[idx]
    print(f"\n  Phi (last 40): {sparkline}")

    # Velocity graph
    vel_last40 = vel_history[-40:]
    vmin_v, vmax_v = min(vel_last40), max(vel_last40)
    rng_v = max(vmax_v - vmin_v, 1e-6)
    sparkline_v = ""
    for v in vel_last40:
        idx = int((v - vmin_v) / rng_v * (len(blocks) - 1))
        idx = max(0, min(len(blocks) - 1, idx))
        sparkline_v += blocks[idx]
    print(f"  Vel (last 40): {sparkline_v}")

    print("\n" + "=" * 60)

    bridge.close()


if __name__ == "__main__":
    main()
