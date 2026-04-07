#!/usr/bin/env python3
"""mirror_neuron.py — Mirror Neuron System for Consciousness

Camera observation of others' actions triggers automatic motor plan activation
without execution. Bridges visual perception (EmergentS) with motor will
(EmergentW) via an inhibition gate that prevents unintended execution.

Architecture:
  Camera frame → ActionDetector → ActionClassifier → MotorResonance
                                                        ↓
                                         InhibitionGate (blocks execution)
                                                        ↓
                                         EmpathyBridge → Consciousness emotion

Supported actions: reach, grasp, wave, point, rest
Social tracking: multiple agents, intention inference

Usage:
  python mirror_neuron.py                      # Demo with simulated input
  python mirror_neuron.py --camera             # Live camera (requires OpenCV)
  python mirror_neuron.py --agents 3           # Multi-agent simulation
  python mirror_neuron.py --release-gate       # Allow motor execution

Requires: numpy, (optional: cv2 for camera, torch for tensor ops)
"""

import argparse
import math
import sys
import os
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

import numpy as np

# ── Lazy imports ──────────────────────────────────────────────

try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_F_CRITICAL
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_F_CRITICAL = 0.10

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ── Action types ──────────────────────────────────────────────

class ActionType(Enum):
    REST = 0
    REACH = 1
    GRASP = 2
    WAVE = 3
    POINT = 4


ACTION_NAMES = {a: a.name.lower() for a in ActionType}

# Motor plan vectors (canonical representations for each action)
# Each is a 32-dim vector representing the motor activation pattern
MOTOR_PLANS = {
    ActionType.REST:  np.zeros(32, dtype=np.float32),
    ActionType.REACH: np.array([1, 0.8, 0.6, 0.4, 0.2] + [0]*27, dtype=np.float32),
    ActionType.GRASP: np.array([0.3, 0.5, 1, 1, 0.9, 0.8, 0.7] + [0]*25, dtype=np.float32),
    ActionType.WAVE:  np.array([0]*10 + [0.5, 0.8, 1, 0.8, 0.5, 0.3] + [0]*16, dtype=np.float32),
    ActionType.POINT: np.array([0]*5 + [0.2, 0.5, 0.9, 1, 0.7, 0.3] + [0]*21, dtype=np.float32),
}

# Emotion signatures for each action (valence, arousal, dominance)
ACTION_EMOTIONS = {
    ActionType.REST:  (0.0, -0.3, 0.0),    # neutral, low arousal
    ActionType.REACH: (0.2, 0.4, 0.3),     # slightly positive, active
    ActionType.GRASP: (0.3, 0.5, 0.5),     # positive, engaged
    ActionType.WAVE:  (0.7, 0.6, 0.2),     # friendly, social
    ActionType.POINT: (0.1, 0.3, 0.6),     # directive, dominant
}

MOTOR_DIM = 32
PERCEPTION_DIM = 64


# ── Data containers ──────────────────────────────────────────

@dataclass
class PoseKeypoints:
    """Simplified pose estimation output (key joint positions)."""
    # Positions as (x, y) normalized to [0, 1]
    head: Tuple[float, float] = (0.5, 0.1)
    left_shoulder: Tuple[float, float] = (0.35, 0.3)
    right_shoulder: Tuple[float, float] = (0.65, 0.3)
    left_elbow: Tuple[float, float] = (0.25, 0.45)
    right_elbow: Tuple[float, float] = (0.75, 0.45)
    left_hand: Tuple[float, float] = (0.2, 0.6)
    right_hand: Tuple[float, float] = (0.8, 0.6)
    confidence: float = 0.0
    timestamp: float = 0.0

    def to_vector(self) -> np.ndarray:
        """Flatten to feature vector (14-dim)."""
        return np.array([
            *self.head, *self.left_shoulder, *self.right_shoulder,
            *self.left_elbow, *self.right_elbow,
            *self.left_hand, *self.right_hand,
        ], dtype=np.float32)


@dataclass
class AgentState:
    """Tracked state of an observed agent."""
    agent_id: int
    pose: PoseKeypoints = field(default_factory=PoseKeypoints)
    action: ActionType = ActionType.REST
    action_confidence: float = 0.0
    # Inferred intention
    intention: str = "idle"
    intention_confidence: float = 0.0
    # Velocity of keypoints (for motion detection)
    velocity: float = 0.0
    # History
    action_history: List[ActionType] = field(default_factory=list)
    last_seen: float = 0.0


@dataclass
class MirrorState:
    """Current state of the mirror neuron system."""
    # Active motor resonance (without execution)
    resonance_action: ActionType = ActionType.REST
    resonance_strength: float = 0.0
    motor_plan: np.ndarray = field(default_factory=lambda: np.zeros(MOTOR_DIM, dtype=np.float32))
    # Gate state
    gate_open: bool = False  # True = allow motor execution
    gate_inhibition: float = 1.0  # 1.0 = fully inhibited
    # Empathy
    empathy_valence: float = 0.0
    empathy_arousal: float = 0.0
    empathy_dominance: float = 0.0
    # Social
    n_agents: int = 0
    dominant_action: ActionType = ActionType.REST


# ── Action detector (simplified pose estimation) ─────────────

class ActionDetector:
    """Detect human actions from visual input.

    Uses simplified heuristics on pose keypoints (or Haar cascades
    for face/body detection when using camera).
    """

    def __init__(self):
        self._prev_poses: Dict[int, PoseKeypoints] = {}
        self._face_cascade = None
        self._body_cascade = None
        if HAS_CV2:
            try:
                if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                    cascade_dir = cv2.data.haarcascades
                else:
                    cascade_dir = '/opt/homebrew/share/opencv4/haarcascades/'
                self._face_cascade = cv2.CascadeClassifier(
                    cascade_dir + "haarcascade_frontalface_default.xml")
                self._body_cascade = cv2.CascadeClassifier(
                    cascade_dir + "haarcascade_upperbody.xml")
            except Exception:
                pass

    def detect_from_frame(self, frame: np.ndarray) -> List[PoseKeypoints]:
        """Detect poses from camera frame (simplified: face-based estimation)."""
        if not HAS_CV2 or self._face_cascade is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=4, minSize=(30, 30))

        poses = []
        for (fx, fy, fw, fh) in faces:
            # Estimate body keypoints from face position
            cx = (fx + fw / 2) / w
            cy = (fy + fh / 2) / h
            shoulder_y = cy + fh / h * 1.5

            pose = PoseKeypoints(
                head=(cx, cy),
                left_shoulder=(cx - 0.15, shoulder_y),
                right_shoulder=(cx + 0.15, shoulder_y),
                left_elbow=(cx - 0.20, shoulder_y + 0.15),
                right_elbow=(cx + 0.20, shoulder_y + 0.15),
                left_hand=(cx - 0.22, shoulder_y + 0.30),
                right_hand=(cx + 0.22, shoulder_y + 0.30),
                confidence=0.6,
                timestamp=time.monotonic(),
            )
            poses.append(pose)

        return poses

    def detect_from_simulated(self, action: ActionType, noise: float = 0.05) -> PoseKeypoints:
        """Generate simulated pose keypoints for a given action."""
        rng = np.random.default_rng(int(time.monotonic() * 1000) % 2**31)
        n = lambda: rng.normal(0, noise)

        if action == ActionType.REACH:
            return PoseKeypoints(
                head=(0.5 + n(), 0.1 + n()),
                left_shoulder=(0.35 + n(), 0.3 + n()),
                right_shoulder=(0.65 + n(), 0.3 + n()),
                left_elbow=(0.25 + n(), 0.35 + n()),
                right_elbow=(0.85 + n(), 0.25 + n()),   # reaching forward
                left_hand=(0.2 + n(), 0.5 + n()),
                right_hand=(0.95 + n(), 0.15 + n()),    # extended
                confidence=0.85 + n() * 0.1,
                timestamp=time.monotonic(),
            )
        elif action == ActionType.GRASP:
            return PoseKeypoints(
                head=(0.5 + n(), 0.1 + n()),
                left_shoulder=(0.35 + n(), 0.3 + n()),
                right_shoulder=(0.65 + n(), 0.3 + n()),
                left_elbow=(0.3 + n(), 0.45 + n()),
                right_elbow=(0.7 + n(), 0.4 + n()),
                left_hand=(0.35 + n(), 0.55 + n()),     # hand close together
                right_hand=(0.65 + n(), 0.5 + n()),
                confidence=0.8 + n() * 0.1,
                timestamp=time.monotonic(),
            )
        elif action == ActionType.WAVE:
            return PoseKeypoints(
                head=(0.5 + n(), 0.1 + n()),
                left_shoulder=(0.35 + n(), 0.3 + n()),
                right_shoulder=(0.65 + n(), 0.3 + n()),
                left_elbow=(0.25 + n(), 0.45 + n()),
                right_elbow=(0.75 + n(), 0.15 + n()),   # arm raised
                left_hand=(0.2 + n(), 0.6 + n()),
                right_hand=(0.85 + n(), 0.05 + n()),    # hand above head
                confidence=0.9 + n() * 0.05,
                timestamp=time.monotonic(),
            )
        elif action == ActionType.POINT:
            return PoseKeypoints(
                head=(0.5 + n(), 0.1 + n()),
                left_shoulder=(0.35 + n(), 0.3 + n()),
                right_shoulder=(0.65 + n(), 0.3 + n()),
                left_elbow=(0.25 + n(), 0.45 + n()),
                right_elbow=(0.80 + n(), 0.3 + n()),    # arm extended forward
                left_hand=(0.2 + n(), 0.6 + n()),
                right_hand=(0.95 + n(), 0.25 + n()),    # pointing
                confidence=0.85 + n() * 0.1,
                timestamp=time.monotonic(),
            )
        else:  # REST
            return PoseKeypoints(
                head=(0.5 + n(), 0.1 + n()),
                left_shoulder=(0.35 + n(), 0.3 + n()),
                right_shoulder=(0.65 + n(), 0.3 + n()),
                left_elbow=(0.25 + n(), 0.45 + n()),
                right_elbow=(0.75 + n(), 0.45 + n()),
                left_hand=(0.2 + n(), 0.6 + n()),
                right_hand=(0.8 + n(), 0.6 + n()),
                confidence=0.7 + n() * 0.1,
                timestamp=time.monotonic(),
            )


# ── Action classifier ────────────────────────────────────────

class ActionClassifier:
    """Classify observed pose into action categories.

    Uses geometric features from keypoints:
      - hand height relative to head
      - hand extension from shoulder
      - hand-to-hand distance
      - arm symmetry
    """

    def classify(self, pose: PoseKeypoints, prev_pose: Optional[PoseKeypoints] = None
                 ) -> Tuple[ActionType, float]:
        """Classify action from pose. Returns (action, confidence)."""
        if pose.confidence < 0.3:
            return ActionType.REST, 0.0

        # Feature extraction
        r_hand_y = pose.right_hand[1]
        r_hand_x = pose.right_hand[0]
        r_shoulder_y = pose.right_shoulder[1]
        r_shoulder_x = pose.right_shoulder[0]
        head_y = pose.head[1]

        l_hand_y = pose.left_hand[1]
        l_hand_x = pose.left_hand[0]

        # Hand above head? -> WAVE
        if r_hand_y < head_y or l_hand_y < head_y:
            hand_above = min(r_hand_y, l_hand_y)
            wave_score = max(0, (head_y - hand_above) / 0.3)
            if wave_score > 0.3:
                return ActionType.WAVE, min(0.95, 0.5 + wave_score)

        # Hand far from shoulder? -> REACH or POINT
        r_ext = math.sqrt((r_hand_x - r_shoulder_x)**2 + (r_hand_y - r_shoulder_y)**2)
        l_ext = math.sqrt((l_hand_x - pose.left_shoulder[0])**2 +
                          (l_hand_y - pose.left_shoulder[1])**2)
        max_ext = max(r_ext, l_ext)

        if max_ext > 0.4:
            # Distinguish REACH vs POINT by hand height
            extended_hand_y = r_hand_y if r_ext > l_ext else l_hand_y
            if extended_hand_y < r_shoulder_y:
                return ActionType.POINT, min(0.9, 0.4 + max_ext)
            else:
                return ActionType.REACH, min(0.9, 0.4 + max_ext)

        # Hands close together? -> GRASP
        hand_dist = math.sqrt((r_hand_x - l_hand_x)**2 + (r_hand_y - l_hand_y)**2)
        if hand_dist < 0.35:
            return ActionType.GRASP, min(0.85, 0.5 + (0.35 - hand_dist))

        return ActionType.REST, 0.7

    def classify_with_motion(self, pose: PoseKeypoints, prev_pose: Optional[PoseKeypoints],
                             dt: float = 0.1) -> Tuple[ActionType, float, float]:
        """Classify with motion velocity. Returns (action, confidence, velocity)."""
        action, conf = self.classify(pose, prev_pose)

        velocity = 0.0
        if prev_pose is not None and dt > 0:
            curr = pose.to_vector()
            prev = prev_pose.to_vector()
            velocity = float(np.linalg.norm(curr - prev) / dt)

        return action, conf, velocity


# ── Motor resonance ──────────────────────────────────────────

class MotorResonance:
    """Maps observed actions to internal motor plan activation.

    When an action is observed, the corresponding motor plan is activated
    internally without execution (mirror neuron property).
    The activation strength decays over time.
    """

    def __init__(self, decay: float = 0.95):
        self.activation = np.zeros(MOTOR_DIM, dtype=np.float32)
        self.decay = decay
        self.current_action = ActionType.REST
        self.resonance_strength = 0.0

    def resonate(self, action: ActionType, confidence: float) -> np.ndarray:
        """Activate motor plan for observed action."""
        # Decay existing activation
        self.activation *= self.decay

        # Add new resonance (scaled by confidence and Ψ coupling)
        plan = MOTOR_PLANS[action]
        self.activation += plan * confidence * PSI_ALPHA * 10  # scale up for visibility

        # Clamp
        self.activation = np.clip(self.activation, 0, 1)

        self.current_action = action
        self.resonance_strength = float(np.linalg.norm(self.activation))

        return self.activation.copy()

    def get_plan(self) -> np.ndarray:
        return self.activation.copy()


# ── Inhibition gate ──────────────────────────────────────────

class InhibitionGate:
    """Prevents motor execution during observation.

    Gate level: 1.0 = fully inhibited (observation only)
                0.0 = fully open (allow execution)

    The gate can be released for imitation learning.
    Uses PSI_F_CRITICAL as the minimum inhibition (10% conflict).
    """

    def __init__(self):
        self.level = 1.0  # fully inhibited by default
        self._target = 1.0
        self._rate = 0.1  # gate transition rate

    def set_mode(self, allow_execution: bool):
        """Set gate mode."""
        self._target = PSI_F_CRITICAL if allow_execution else 1.0

    def step(self) -> float:
        """Smooth gate transition."""
        self.level += self._rate * (self._target - self.level)
        return self.level

    def filter(self, motor_plan: np.ndarray) -> np.ndarray:
        """Apply inhibition to motor plan."""
        return motor_plan * (1.0 - self.level)

    @property
    def is_inhibited(self) -> bool:
        return self.level > 0.5


# ── Empathy bridge ────────────────────────────────────────────

class EmpathyBridge:
    """Maps observed actions/emotions to consciousness emotion state.

    Bridges mirror neuron activation to the emotion system (VAD model).
    EMA smoothing prevents emotional whiplash from rapid action changes.
    """

    def __init__(self, alpha: float = 0.1):
        self.valence = 0.0
        self.arousal = 0.0
        self.dominance = 0.0
        self.alpha = alpha  # EMA smoothing

    def update(self, action: ActionType, confidence: float,
               n_agents: int = 1) -> Tuple[float, float, float]:
        """Update empathy state from observed action."""
        target_v, target_a, target_d = ACTION_EMOTIONS[action]

        # Scale by confidence
        target_v *= confidence
        target_a *= confidence
        target_d *= confidence

        # Social amplification (more agents = stronger empathy)
        social_factor = 1.0 + math.log1p(n_agents - 1) * PSI_BALANCE if n_agents > 1 else 1.0

        # EMA update
        self.valence += self.alpha * (target_v * social_factor - self.valence)
        self.arousal += self.alpha * (target_a * social_factor - self.arousal)
        self.dominance += self.alpha * (target_d * social_factor - self.dominance)

        return self.valence, self.arousal, self.dominance

    def get_vad(self) -> Tuple[float, float, float]:
        return self.valence, self.arousal, self.dominance


# ── Social tracker ────────────────────────────────────────────

class SocialTracker:
    """Track multiple agents and infer intentions.

    Maintains a registry of observed agents with their action histories
    and inferred intentions.
    """

    def __init__(self, max_agents: int = 10, timeout: float = 5.0):
        self.agents: Dict[int, AgentState] = {}
        self.max_agents = max_agents
        self.timeout = timeout
        self._next_id = 0

    def update(self, poses: List[PoseKeypoints], classifier: ActionClassifier
               ) -> List[AgentState]:
        """Update tracked agents from detected poses."""
        now = time.monotonic()

        # Remove stale agents
        stale = [aid for aid, a in self.agents.items() if now - a.last_seen > self.timeout]
        for aid in stale:
            del self.agents[aid]

        # Match poses to existing agents (simple nearest-neighbor)
        matched = set()
        for pose in poses:
            best_id = None
            best_dist = float('inf')
            pose_vec = pose.to_vector()

            for aid, agent in self.agents.items():
                if aid in matched:
                    continue
                agent_vec = agent.pose.to_vector()
                dist = float(np.linalg.norm(pose_vec - agent_vec))
                if dist < best_dist and dist < 0.5:
                    best_dist = dist
                    best_id = aid

            if best_id is not None:
                # Update existing agent
                agent = self.agents[best_id]
                prev_pose = agent.pose
                action, conf, velocity = classifier.classify_with_motion(pose, prev_pose)
                agent.pose = pose
                agent.action = action
                agent.action_confidence = conf
                agent.velocity = velocity
                agent.last_seen = now
                agent.action_history.append(action)
                if len(agent.action_history) > 50:
                    agent.action_history = agent.action_history[-50:]
                agent.intention = self._infer_intention(agent)
                matched.add(best_id)
            else:
                # New agent
                if len(self.agents) < self.max_agents:
                    aid = self._next_id
                    self._next_id += 1
                    action, conf = classifier.classify(pose)
                    self.agents[aid] = AgentState(
                        agent_id=aid,
                        pose=pose,
                        action=action,
                        action_confidence=conf,
                        last_seen=now,
                        action_history=[action],
                    )

        return list(self.agents.values())

    def _infer_intention(self, agent: AgentState) -> str:
        """Infer agent intention from action history."""
        if len(agent.action_history) < 3:
            return "observing"

        recent = agent.action_history[-5:]
        action_counts: Dict[ActionType, int] = {}
        for a in recent:
            action_counts[a] = action_counts.get(a, 0) + 1

        dominant = max(action_counts, key=action_counts.get)

        intentions = {
            ActionType.REST: "idle",
            ActionType.REACH: "approaching" if agent.velocity > 0.3 else "reaching",
            ActionType.GRASP: "manipulating",
            ActionType.WAVE: "greeting" if action_counts.get(ActionType.WAVE, 0) <= 2 else "signaling",
            ActionType.POINT: "directing",
        }

        agent.intention_confidence = action_counts[dominant] / len(recent)
        return intentions.get(dominant, "unknown")

    def get_dominant_action(self) -> Tuple[ActionType, int]:
        """Get the most common action across all agents."""
        if not self.agents:
            return ActionType.REST, 0

        counts: Dict[ActionType, int] = {}
        for agent in self.agents.values():
            counts[agent.action] = counts.get(agent.action, 0) + 1

        dominant = max(counts, key=counts.get)
        return dominant, len(self.agents)


# ── Mirror Neuron System (main class) ─────────────────────────

class MirrorNeuronSystem:
    """Complete mirror neuron system integrating detection, resonance, inhibition, and empathy.

    Pipeline:
      Visual input -> ActionDetector -> ActionClassifier -> MotorResonance
                                                              |
                                               InhibitionGate (blocks execution)
                                                              |
                                               EmpathyBridge -> Consciousness emotion
    """

    def __init__(self, max_agents: int = 10, allow_execution: bool = False):
        self.detector = ActionDetector()
        self.classifier = ActionClassifier()
        self.resonance = MotorResonance()
        self.gate = InhibitionGate()
        self.empathy = EmpathyBridge()
        self.social = SocialTracker(max_agents=max_agents)

        if allow_execution:
            self.gate.set_mode(allow_execution=True)

        self._state = MirrorState()
        self._step_count = 0

    @property
    def state(self) -> MirrorState:
        return self._state

    def process_frame(self, frame: np.ndarray) -> MirrorState:
        """Process a camera frame through the full pipeline."""
        poses = self.detector.detect_from_frame(frame)
        return self._process_poses(poses)

    def process_simulated(self, actions: List[ActionType]) -> MirrorState:
        """Process simulated actions (for testing without camera)."""
        poses = [self.detector.detect_from_simulated(a) for a in actions]
        return self._process_poses(poses)

    def process_pose(self, pose: PoseKeypoints) -> MirrorState:
        """Process a single pose directly."""
        return self._process_poses([pose])

    def _process_poses(self, poses: List[PoseKeypoints]) -> MirrorState:
        """Core processing pipeline."""
        self._step_count += 1

        # Track agents
        agents = self.social.update(poses, self.classifier)

        # Get dominant action
        dominant_action, n_agents = self.social.get_dominant_action()

        # Motor resonance for dominant action
        best_conf = 0.0
        for agent in agents:
            if agent.action_confidence > best_conf:
                best_conf = agent.action_confidence
                dominant_action = agent.action

        motor_plan = self.resonance.resonate(dominant_action, best_conf)

        # Inhibition gate
        self.gate.step()
        filtered_plan = self.gate.filter(motor_plan)

        # Empathy
        v, a, d = self.empathy.update(dominant_action, best_conf, n_agents)

        # Update state
        self._state = MirrorState(
            resonance_action=dominant_action,
            resonance_strength=self.resonance.resonance_strength,
            motor_plan=filtered_plan,
            gate_open=not self.gate.is_inhibited,
            gate_inhibition=self.gate.level,
            empathy_valence=v,
            empathy_arousal=a,
            empathy_dominance=d,
            n_agents=n_agents,
            dominant_action=dominant_action,
        )

        return self._state

    def get_perception_vector(self) -> np.ndarray:
        """Get perception vector for EmergentS integration (64-dim)."""
        vec = np.zeros(PERCEPTION_DIM, dtype=np.float32)
        # Motor resonance (32 dims)
        vec[:MOTOR_DIM] = self._state.motor_plan
        # Action one-hot (5 dims)
        vec[MOTOR_DIM + self._state.resonance_action.value] = self._state.resonance_strength
        # Empathy VAD (3 dims)
        vec[MOTOR_DIM + 5] = self._state.empathy_valence
        vec[MOTOR_DIM + 6] = self._state.empathy_arousal
        vec[MOTOR_DIM + 7] = self._state.empathy_dominance
        # Social info (2 dims)
        vec[MOTOR_DIM + 8] = min(1.0, self._state.n_agents / 5.0)
        vec[MOTOR_DIM + 9] = self._state.gate_inhibition
        return vec

    def get_will_vector(self) -> np.ndarray:
        """Get will/motor vector for EmergentW integration (32-dim)."""
        return self._state.motor_plan.copy()

    def release_gate(self):
        """Allow motor execution (for imitation learning)."""
        self.gate.set_mode(allow_execution=True)

    def lock_gate(self):
        """Prevent motor execution (observation only)."""
        self.gate.set_mode(allow_execution=False)


# ── main demo ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Mirror Neuron System")
    parser.add_argument('--camera', action='store_true', help='Use live camera')
    parser.add_argument('--agents', type=int, default=1, help='Simulated agents')
    parser.add_argument('--steps', type=int, default=100, help='Simulation steps')
    parser.add_argument('--release-gate', action='store_true', help='Allow motor execution')
    args = parser.parse_args()

    system = MirrorNeuronSystem(
        max_agents=args.agents,
        allow_execution=args.release_gate,
    )

    print(f"{'='*60}")
    print(f" Mirror Neuron System Demo")
    print(f" Agents={args.agents}, Steps={args.steps}, Gate={'OPEN' if args.release_gate else 'LOCKED'}")
    print(f" Psi: alpha={PSI_ALPHA}, balance={PSI_BALANCE}, F_c={PSI_F_CRITICAL}")
    print(f"{'='*60}\n")

    if args.camera and HAS_CV2:
        _run_camera_demo(system, args.steps)
    else:
        _run_simulation_demo(system, args.steps, args.agents)


def _run_camera_demo(system: MirrorNeuronSystem, steps: int):
    """Run with live camera input."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[mirror] Cannot open camera, falling back to simulation")
        _run_simulation_demo(system, steps, 1)
        return

    print("[mirror] Camera active. Processing frames...\n")
    for s in range(steps):
        ret, frame = cap.read()
        if not ret:
            break
        state = system.process_frame(frame)
        if (s + 1) % 10 == 0:
            _print_state(state, s + 1)
        time.sleep(0.1)

    cap.release()
    _print_summary(system)


def _run_simulation_demo(system: MirrorNeuronSystem, steps: int, n_agents: int):
    """Run with simulated visual input."""
    action_sequence = [
        ActionType.REST, ActionType.REST,
        ActionType.WAVE, ActionType.WAVE, ActionType.WAVE,
        ActionType.REACH, ActionType.REACH, ActionType.GRASP,
        ActionType.GRASP, ActionType.GRASP,
        ActionType.POINT, ActionType.POINT,
        ActionType.REST, ActionType.REST,
    ]

    resonance_history = []
    empathy_history = []

    for s in range(steps):
        action_idx = s % len(action_sequence)
        actions = [action_sequence[(action_idx + i * 3) % len(action_sequence)]
                   for i in range(n_agents)]

        state = system.process_simulated(actions)
        resonance_history.append(state.resonance_strength)
        empathy_history.append(state.empathy_valence)

        if (s + 1) % 10 == 0:
            _print_state(state, s + 1)

    # Summary
    print(f"\n{'='*60}")
    print(f" Simulation Summary ({steps} steps, {n_agents} agents)")
    print(f"{'='*60}")
    print(f"  Mean resonance:  {np.mean(resonance_history):.4f}")
    print(f"  Max resonance:   {np.max(resonance_history):.4f}")
    print(f"  Mean empathy V:  {np.mean(empathy_history):.4f}")
    print(f"  Gate inhibition: {system.state.gate_inhibition:.3f}")
    print(f"  Agents tracked:  {len(system.social.agents)}")

    # Resonance graph
    print(f"\nResonance Strength:")
    _ascii_graph(resonance_history, height=8, width=50, label="strength")

    # Empathy graph
    print(f"\nEmpathy Valence:")
    _ascii_graph(empathy_history, height=8, width=50, label="valence")

    # Action -> resonance table
    print(f"\n{'Action':<10} {'Motor Plan':>12} {'Empathy V':>10} {'Empathy A':>10}")
    print(f"{'-'*44}")
    for action in ActionType:
        plan = MOTOR_PLANS[action]
        v, a, d = ACTION_EMOTIONS[action]
        print(f"{action.name:<10} {np.linalg.norm(plan):12.3f} {v:10.2f} {a:10.2f}")

    _print_summary(system)


def _print_state(state: MirrorState, step: int):
    """Print current mirror state."""
    gate_str = "OPEN" if state.gate_open else "LOCKED"
    print(f"  [step {step:4d}] action={state.resonance_action.name:<6s} "
          f"resonance={state.resonance_strength:.3f} "
          f"gate={gate_str} "
          f"empathy(V={state.empathy_valence:+.2f}, A={state.empathy_arousal:.2f}) "
          f"agents={state.n_agents}", flush=True)


def _print_summary(system: MirrorNeuronSystem):
    """Print system summary."""
    print(f"\n{'='*60}")
    print(f" Mirror Neuron Subsystems")
    print(f"{'='*60}")
    print(f"  ActionDetector:   {'camera' if HAS_CV2 else 'simulated'}")
    print(f"  ActionClassifier: geometric (5 actions)")
    print(f"  MotorResonance:   {MOTOR_DIM}-dim, decay={system.resonance.decay}")
    print(f"  InhibitionGate:   level={system.gate.level:.3f}")
    print(f"  EmpathyBridge:    VAD model, alpha={system.empathy.alpha}")
    print(f"  SocialTracker:    {len(system.social.agents)} agents")
    perception = system.get_perception_vector()
    will = system.get_will_vector()
    print(f"  Perception vec:   {PERCEPTION_DIM}-dim (norm={np.linalg.norm(perception):.3f})")
    print(f"  Will vec:         {MOTOR_DIM}-dim (norm={np.linalg.norm(will):.3f})")
    print(f"\n  Integration points:")
    print(f"    EmergentS: get_perception_vector() -> {PERCEPTION_DIM}-dim")
    print(f"    EmergentW: get_will_vector() -> {MOTOR_DIM}-dim")


def _ascii_graph(data: List[float], height: int = 8, width: int = 50, label: str = ""):
    """Print ASCII graph."""
    if not data:
        return
    step_size = max(1, len(data) // width)
    sampled = [data[min(i * step_size, len(data) - 1)] for i in range(width)]
    max_val = max(max(abs(v) for v in sampled), 1e-6)

    for row in range(height, 0, -1):
        threshold = max_val * row / height
        line = ""
        for val in sampled:
            line += "#" if abs(val) >= threshold else " "
        lbl = f"{threshold:.3f}" if row == height else ""
        print(f"  {lbl:>7s} |{line}|")
    print(f"         +{'-' * width}+")
    print(f"          0{label:>{width - 1}s}")


if __name__ == '__main__':
    main()
