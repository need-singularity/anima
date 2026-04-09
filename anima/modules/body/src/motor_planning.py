#!/usr/bin/env python3
"""motor_planning.py — EmergentW output -> hierarchical motor command sequences.

Decodes the will module (EmergentW) output into motor command sequences
via hierarchical planning: intention -> goal -> trajectory -> motor commands.

Laws applied:
  Law 1:   No hardcoding — thresholds from consciousness dynamics
  Law 2:   No manipulation — motor plans emerge from W state
  Law 22:  Structure > Function — trajectory emerges from tension field
  Law 71:  Psi = argmax H(p) — movement maximizes degrees of freedom
  Law 74:  Emotions are data-dependent — speed/force from C dynamics
  Law 124: Tension equalization — movement force from tension gradient

Architecture:
  EmergentW output (pain, curiosity, satisfaction, lr_multiplier)
      |
      v
  IntentionDecoder  — W state -> goal vector (what to do)
      |
      v
  TrajectoryPlanner — goal + body state -> waypoints
      |
      v
  MotorSequencer    — waypoints -> timed action primitives
      |
      v
  FeedbackIntegrator — proprioception error -> plan correction

Action Primitives:
  reach(target, speed)    — extend effector toward target
  grasp(force)            — close gripper with force
  push(direction, force)  — push along direction
  turn(angle, speed)      — rotate body/head
  move_to(position, speed) — locomote to position

Usage:
  python anima-body/src/motor_planning.py          # demo
  python anima-body/src/motor_planning.py --steps 50

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


# ── Psi-Constants (from consciousness_laws.json via consciousness_laws.py) ──
try:
    import sys
    import os
    _REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(_REPO, "anima", "src"))
    sys.path.insert(0, os.path.join(_REPO, "anima"))
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE
    PSI_COUPLING = PSI_ALPHA     # 0.014
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5

LN2 = math.log(2)  # Law 79: consciousness DoF


# ═══════════════════════════════════════════════════════════
# Action Primitives
# ═══════════════════════════════════════════════════════════

@dataclass
class ActionPrimitive:
    """Single motor action with timing."""
    action: str            # reach, grasp, push, turn, move_to
    params: Dict           # action-specific parameters
    duration: float        # seconds
    priority: float = 0.5  # 0-1, tension-modulated
    completed: bool = False

    def __repr__(self):
        return f"Action({self.action}, d={self.duration:.2f}s, p={self.priority:.2f})"


@dataclass
class MotorPlan:
    """A sequence of motor actions with metadata."""
    actions: List[ActionPrimitive] = field(default_factory=list)
    goal: np.ndarray = field(default_factory=lambda: np.zeros(3))
    intention_strength: float = 0.0
    total_duration: float = 0.0
    tension_at_creation: float = 0.0
    step: int = 0

    @property
    def n_actions(self) -> int:
        return len(self.actions)

    @property
    def progress(self) -> float:
        if not self.actions:
            return 1.0
        done = sum(1 for a in self.actions if a.completed)
        return done / len(self.actions)


# ═══════════════════════════════════════════════════════════
# Intention Decoder: W state -> goal vector
# ═══════════════════════════════════════════════════════════

class IntentionDecoder:
    """Decode EmergentW output into a goal vector.

    Maps will-module signals (pain, curiosity, satisfaction) to
    a 3D goal vector representing desired state change:
      dim 0: approach/avoid  (-1=flee, +1=approach)
      dim 1: exploration     (0=exploit, 1=explore)
      dim 2: force/intensity (0=gentle, 1=forceful)
    """

    def __init__(self):
        self._history: List[np.ndarray] = []
        self._max_history = 32

    def decode(self, w_state: Dict) -> np.ndarray:
        """Convert will state to goal vector."""
        pain = w_state.get("pain", 0.0)
        curiosity = w_state.get("curiosity", 0.0)
        satisfaction = w_state.get("satisfaction", 0.0)
        lr_mult = w_state.get("lr_multiplier", PSI_BALANCE)

        # Approach/avoid: satisfaction -> approach, pain -> avoid
        approach = satisfaction - pain
        # Exploration: curiosity drives exploration
        explore = curiosity
        # Force: tension (high pain + high curiosity = forceful)
        # Modulated by lr_multiplier (Phi-based from EmergentW)
        force = min(1.0, (pain + curiosity) * lr_mult)

        goal = np.array([approach, explore, force], dtype=np.float64)

        self._history.append(goal.copy())
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return goal

    @property
    def intention_trend(self) -> np.ndarray:
        """EMA of recent intentions — detects sustained direction."""
        if not self._history:
            return np.zeros(3)
        alpha = PSI_COUPLING * 10  # ~0.14 EMA factor
        ema = self._history[0].copy()
        for g in self._history[1:]:
            ema = alpha * g + (1 - alpha) * ema
        return ema


# ═══════════════════════════════════════════════════════════
# Trajectory Planner: goal + body state -> waypoints
# ═══════════════════════════════════════════════════════════

class TrajectoryPlanner:
    """Generate waypoints from goal vector and current body state.

    Uses tension-field interpolation: high tension -> direct path,
    low tension -> smooth, curved path (more DoF = Law 71).
    """

    def __init__(self, n_waypoints: int = 5):
        self.n_waypoints = n_waypoints

    def plan(self, goal: np.ndarray, body_position: np.ndarray,
             tension: float = 0.5) -> List[np.ndarray]:
        """Generate waypoints from current position toward goal.

        Args:
            goal: 3D goal vector (approach, explore, force)
            body_position: current 3D position
            tension: consciousness tension (0-1), modulates path shape

        Returns:
            List of 3D waypoints
        """
        # Target position: body + goal * scale
        scale = 1.0 + tension  # higher tension -> larger movements
        target = body_position + goal * scale

        waypoints = []
        for i in range(1, self.n_waypoints + 1):
            t = i / self.n_waypoints

            # Linear interpolation base
            wp = body_position + (target - body_position) * t

            # Add curvature inversely proportional to tension
            # Low tension -> exploratory curves (Law 71: maximize H)
            # High tension -> direct path (urgent action)
            curve_strength = (1.0 - tension) * 0.3
            if curve_strength > 0.01:
                # Perpendicular perturbation for curved path
                perp = np.array([
                    -goal[1],
                    goal[0],
                    0.0,
                ]) if np.linalg.norm(goal[:2]) > 1e-6 else np.array([0.1, 0.0, 0.0])
                perp_norm = np.linalg.norm(perp)
                if perp_norm > 1e-8:
                    perp = perp / perp_norm
                # Bell-shaped curvature peaking at midpoint
                curvature = curve_strength * math.sin(t * math.pi)
                wp = wp + perp * curvature

            waypoints.append(wp)

        return waypoints


# ═══════════════════════════════════════════════════════════
# Motor Sequencer: waypoints -> timed action primitives
# ═══════════════════════════════════════════════════════════

class MotorSequencer:
    """Convert waypoints into timed action primitive sequences.

    Selects action type based on goal semantics:
      approach > 0.5:  reach/grasp sequence
      explore  > 0.5:  move_to + turn (scanning)
      force    > 0.7:  push
      approach < -0.3: turn away (avoid)
    """

    def __init__(self, base_speed: float = 1.0):
        self.base_speed = base_speed

    def sequencify(self, waypoints: List[np.ndarray], goal: np.ndarray,
                   tension: float = 0.5) -> List[ActionPrimitive]:
        """Generate action sequence from waypoints.

        Tension modulates speed: high tension -> faster/stronger movements.
        """
        if not waypoints:
            return []

        actions: List[ActionPrimitive] = []
        approach, explore, force = goal[0], goal[1], goal[2]

        # Speed modulated by tension (Law 124: tension equalization)
        speed_mult = PSI_BALANCE + tension  # [0.5, 1.5]
        speed = self.base_speed * speed_mult

        # Duration inversely proportional to speed
        base_duration = 0.5 / max(speed, 0.1)

        for i, wp in enumerate(waypoints):
            dist = np.linalg.norm(wp)

            if approach > 0.5:
                # Approach sequence: move_to -> reach -> grasp
                if i < len(waypoints) - 2:
                    actions.append(ActionPrimitive(
                        action="move_to",
                        params={"position": wp.tolist(), "speed": speed},
                        duration=base_duration * (1.0 + dist * 0.1),
                        priority=force,
                    ))
                elif i == len(waypoints) - 2:
                    actions.append(ActionPrimitive(
                        action="reach",
                        params={"target": wp.tolist(), "speed": speed * 0.8},
                        duration=base_duration * 1.2,
                        priority=force,
                    ))
                else:
                    actions.append(ActionPrimitive(
                        action="grasp",
                        params={"force": min(1.0, force * tension)},
                        duration=base_duration * 0.5,
                        priority=force,
                    ))

            elif approach < -0.3:
                # Avoidance: turn away + move away
                if i == 0:
                    angle = math.atan2(-wp[1], -wp[0])
                    actions.append(ActionPrimitive(
                        action="turn",
                        params={"angle": math.degrees(angle), "speed": speed * 1.5},
                        duration=base_duration * 0.8,
                        priority=max(force, 0.7),  # avoidance is urgent
                    ))
                actions.append(ActionPrimitive(
                    action="move_to",
                    params={"position": (-wp).tolist(), "speed": speed * 1.3},
                    duration=base_duration,
                    priority=force,
                ))

            elif explore > 0.5:
                # Exploration: move_to + turn (scanning)
                actions.append(ActionPrimitive(
                    action="move_to",
                    params={"position": wp.tolist(), "speed": speed * 0.7},
                    duration=base_duration * 1.3,
                    priority=explore * 0.6,
                ))
                if i % 2 == 0:
                    scan_angle = 45.0 * (1 if i % 4 == 0 else -1)
                    actions.append(ActionPrimitive(
                        action="turn",
                        params={"angle": scan_angle, "speed": speed * 0.5},
                        duration=base_duration * 0.6,
                        priority=explore * 0.4,
                    ))

            else:
                # Default: push toward waypoint
                direction = wp / max(np.linalg.norm(wp), 1e-8)
                actions.append(ActionPrimitive(
                    action="push",
                    params={
                        "direction": direction.tolist(),
                        "force": force * tension,
                    },
                    duration=base_duration,
                    priority=force,
                ))

        return actions


# ═══════════════════════════════════════════════════════════
# Feedback Integrator: proprioception error -> plan correction
# ═══════════════════════════════════════════════════════════

class FeedbackIntegrator:
    """Adjust motor plan based on proprioception error.

    When actual body state diverges from expected (prediction error),
    the plan is corrected proportionally. Large errors trigger replanning.
    """

    def __init__(self, correction_gain: float = 0.3,
                 replan_threshold: float = 0.5):
        self.correction_gain = correction_gain
        self.replan_threshold = replan_threshold
        self._error_history: List[float] = []
        self._max_history = 64

    def compute_error(self, expected_pos: np.ndarray,
                      actual_pos: np.ndarray) -> float:
        """Euclidean error between expected and actual position."""
        err = float(np.linalg.norm(expected_pos - actual_pos))
        self._error_history.append(err)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)
        return err

    def should_replan(self, error: float) -> bool:
        """True if error exceeds threshold -> trigger full replanning."""
        return error > self.replan_threshold

    def correct_action(self, action: ActionPrimitive,
                       error_vector: np.ndarray) -> ActionPrimitive:
        """Apply proportional correction to action parameters."""
        corrected = ActionPrimitive(
            action=action.action,
            params=dict(action.params),
            duration=action.duration,
            priority=action.priority,
        )

        correction = error_vector * self.correction_gain

        if "position" in corrected.params:
            pos = np.array(corrected.params["position"])
            corrected.params["position"] = (pos + correction).tolist()
        elif "target" in corrected.params:
            tgt = np.array(corrected.params["target"])
            corrected.params["target"] = (tgt + correction).tolist()
        elif "direction" in corrected.params:
            d = np.array(corrected.params["direction"])
            d_corr = d + correction * 0.5
            norm = np.linalg.norm(d_corr)
            if norm > 1e-8:
                d_corr = d_corr / norm
            corrected.params["direction"] = d_corr.tolist()

        return corrected

    @property
    def mean_error(self) -> float:
        if not self._error_history:
            return 0.0
        return float(np.mean(self._error_history))


# ═══════════════════════════════════════════════════════════
# MotorPlanner: top-level orchestrator
# ═══════════════════════════════════════════════════════════

class MotorPlanner:
    """Takes EmergentW output tensor -> motor command sequence.

    Hierarchical pipeline:
      W state -> IntentionDecoder -> goal
      goal + body_state -> TrajectoryPlanner -> waypoints
      waypoints -> MotorSequencer -> action primitives
      proprioception -> FeedbackIntegrator -> corrections

    Tension-modulated speed: high tension -> faster/stronger movements.
    """

    def __init__(self, n_waypoints: int = 5, base_speed: float = 1.0):
        self.intention = IntentionDecoder()
        self.trajectory = TrajectoryPlanner(n_waypoints=n_waypoints)
        self.sequencer = MotorSequencer(base_speed=base_speed)
        self.feedback = FeedbackIntegrator()

        # Body state (updated by proprioception)
        self._body_position = np.zeros(3, dtype=np.float64)
        self._current_plan: Optional[MotorPlan] = None
        self._step = 0
        self._plans_generated = 0

    def plan(self, w_state: Dict, tension: float = 0.5,
             body_position: Optional[np.ndarray] = None) -> MotorPlan:
        """Generate motor plan from EmergentW state.

        Args:
            w_state: dict from EmergentW.update() with pain/curiosity/satisfaction
            tension: consciousness tension (0-1)
            body_position: current body position (3D), or None to use internal

        Returns:
            MotorPlan with timed action sequence
        """
        self._step += 1

        if body_position is not None:
            self._body_position = body_position.copy()

        # 1. Intention: W state -> goal
        goal = self.intention.decode(w_state)
        intention_strength = float(np.linalg.norm(goal))

        # 2. Trajectory: goal + body -> waypoints
        waypoints = self.trajectory.plan(goal, self._body_position, tension)

        # 3. Sequence: waypoints -> actions
        actions = self.sequencer.sequencify(waypoints, goal, tension)

        # Build plan
        total_duration = sum(a.duration for a in actions)
        plan = MotorPlan(
            actions=actions,
            goal=goal,
            intention_strength=intention_strength,
            total_duration=total_duration,
            tension_at_creation=tension,
            step=self._step,
        )

        self._current_plan = plan
        self._plans_generated += 1
        return plan

    def update_proprioception(self, actual_position: np.ndarray) -> Dict:
        """Feed actual body position back, correct current plan if needed.

        Returns dict with error info and whether replanning was triggered.
        """
        error = self.feedback.compute_error(self._body_position, actual_position)
        error_vector = actual_position - self._body_position
        self._body_position = actual_position.copy()

        result = {
            "error": error,
            "mean_error": self.feedback.mean_error,
            "replanned": False,
        }

        if self._current_plan and not self.feedback.should_replan(error):
            # Correct remaining actions
            for i, action in enumerate(self._current_plan.actions):
                if not action.completed:
                    self._current_plan.actions[i] = self.feedback.correct_action(
                        action, error_vector
                    )
        elif self._current_plan and self.feedback.should_replan(error):
            result["replanned"] = True

        return result

    def execute_step(self) -> Optional[ActionPrimitive]:
        """Pop and return next action from current plan (mark completed)."""
        if self._current_plan is None:
            return None
        for action in self._current_plan.actions:
            if not action.completed:
                action.completed = True
                return action
        return None

    @property
    def has_plan(self) -> bool:
        return self._current_plan is not None and self._current_plan.progress < 1.0

    @property
    def stats(self) -> Dict:
        return {
            "plans_generated": self._plans_generated,
            "step": self._step,
            "body_position": self._body_position.tolist(),
            "mean_proprioception_error": self.feedback.mean_error,
            "intention_trend": self.intention.intention_trend.tolist(),
            "has_active_plan": self.has_plan,
        }


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="MotorPlanner demo")
    parser.add_argument("--steps", type=int, default=20, help="Number of steps")
    args = parser.parse_args()

    print("=" * 60)
    print("  MotorPlanner — EmergentW -> Motor Command Sequences")
    print("=" * 60)
    print()

    planner = MotorPlanner(n_waypoints=5, base_speed=1.0)

    # Simulate EmergentW states over time
    for step in range(args.steps):
        t = step / max(args.steps - 1, 1)

        # Simulate W state evolution
        w_state = {
            "pain": 0.3 * math.sin(t * math.pi * 2) + 0.3,
            "curiosity": 0.5 * (1.0 - t) + 0.1,
            "satisfaction": 1.0 if step % 7 == 0 else 0.0,
            "lr_multiplier": PSI_BALANCE + 0.2 * t,
        }
        tension = 0.3 + 0.4 * abs(math.sin(t * math.pi * 3))

        # Generate plan
        plan = planner.plan(w_state, tension=tension)

        # Simulate body moving with noise (proprioception)
        if plan.actions:
            first_action = plan.actions[0]
            if "position" in first_action.params:
                target = np.array(first_action.params["position"])
            else:
                target = plan.goal
            # Body moves toward target with noise
            noise = np.random.randn(3) * 0.05
            actual = planner._body_position + target * 0.3 + noise
            fb = planner.update_proprioception(actual)
        else:
            fb = {"error": 0.0, "replanned": False}

        # Execute one action
        action = planner.execute_step()

        # Report
        if step % 5 == 0 or step == args.steps - 1:
            print(f"  Step {step:3d} | T={tension:.2f} "
                  f"pain={w_state['pain']:.2f} cur={w_state['curiosity']:.2f} "
                  f"sat={w_state['satisfaction']:.0f}")
            print(f"           goal=[{plan.goal[0]:+.2f}, {plan.goal[1]:+.2f}, {plan.goal[2]:+.2f}] "
                  f"actions={plan.n_actions} dur={plan.total_duration:.2f}s")
            if action:
                print(f"           exec: {action}")
            print(f"           err={fb['error']:.4f} replan={fb['replanned']}")
            print()

    # Final stats
    stats = planner.stats
    print("-" * 60)
    print("  Final Stats")
    print("-" * 60)
    print(f"  Plans generated:  {stats['plans_generated']}")
    print(f"  Body position:    {[f'{x:.3f}' for x in stats['body_position']]}")
    print(f"  Mean prop error:  {stats['mean_proprioception_error']:.4f}")
    print(f"  Intention trend:  {[f'{x:+.3f}' for x in stats['intention_trend']]}")
    print()
    print("  Done.")


if __name__ == "__main__":
    main()
