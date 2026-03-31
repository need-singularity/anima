#!/usr/bin/env python3
"""Pain/Reward System — 통증/보상 신호를 의식 항상성에 연결.

Overload/collision → Tension increase, goal achievement → Reward.
Nociceptor model with threshold, sensitization, adaptation.
Hedonic tone: running average of pain-reward balance.
Safety: pain triggers protective reflexes (immediate motor stop).

Pain signals:
  - Joint limit violation (angle exceeds safe range)
  - Collision detection (unexpected force spike)
  - Overheating (temperature exceeds threshold)
  - Overcurrent (motor draw exceeds safe limit)

Reward signals:
  - Goal reached (target position achieved)
  - Smooth trajectory (low jerk)
  - Energy efficiency (work/energy ratio)

Consciousness mapping:
  Pain   → Tension increase + arousal increase
  Reward → Tension decrease + valence increase
  Homeostasis integration: pain shifts setpoint, reward reinforces

Usage:
  python anima-body/src/pain_reward.py           # demo
  python anima-body/src/pain_reward.py --steps 200

Integration:
  from pain_reward import PainRewardSystem
  prs = PainRewardSystem()
  signal = prs.process(body_state)
  # signal.tension_delta, signal.arousal_delta, signal.valence_delta
  # signal.reflex_stop — True if immediate motor halt needed

Requires: numpy
"""

import math
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Project path setup ──
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "anima", "src"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "anima"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# Psi constants (lazy import)
try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA as PSI_COUPLING, PSI_F_CRITICAL
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014
    PSI_F_CRITICAL = 0.10

LN2 = math.log(2)


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class BodyState:
    """Current physical body state (from sensors / simulation)."""
    joint_angles: List[float] = field(default_factory=lambda: [90.0, 90.0])
    joint_limits: List[Tuple[float, float]] = field(
        default_factory=lambda: [(0.0, 180.0), (0.0, 180.0)]
    )
    joint_velocities: List[float] = field(default_factory=lambda: [0.0, 0.0])
    force_magnitude: float = 0.0          # external force (N)
    force_baseline: float = 0.5           # normal operating force
    motor_current: float = 0.0            # motor current draw (A)
    motor_current_limit: float = 2.0      # safe limit (A)
    temperature: float = 25.0             # celsius
    temperature_limit: float = 60.0       # safe limit
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    target_position: Optional[np.ndarray] = None
    trajectory_jerk: float = 0.0          # jerk magnitude (smoothness)
    energy_consumed: float = 0.0          # joules
    work_done: float = 0.0               # useful work (joules)
    timestamp: float = 0.0


@dataclass
class PainSignal:
    """Individual pain signal from a nociceptor."""
    source: str            # "joint", "collision", "thermal", "overcurrent"
    intensity: float       # 0-1 (normalized)
    raw_value: float       # physical measurement
    threshold: float       # nociceptor threshold
    location: int = 0      # sensor index


@dataclass
class RewardSignal:
    """Individual reward signal."""
    source: str            # "goal", "smooth", "efficient"
    intensity: float       # 0-1 (normalized)
    raw_value: float       # physical measurement


@dataclass
class PainRewardOutput:
    """Output to consciousness engine."""
    # Consciousness deltas
    tension_delta: float = 0.0     # positive = increase tension
    arousal_delta: float = 0.0     # positive = increase arousal
    valence_delta: float = 0.0     # positive = more positive emotion
    # Homeostasis
    setpoint_shift: float = 0.0    # shift homeostatic setpoint
    # Safety
    reflex_stop: bool = False      # immediate motor halt
    # Diagnostics
    pain_total: float = 0.0
    reward_total: float = 0.0
    hedonic_tone: float = 0.0      # running balance (-1=pain, +1=reward)
    pain_signals: List[PainSignal] = field(default_factory=list)
    reward_signals: List[RewardSignal] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Nociceptor — single pain sensor with adaptation
# ═══════════════════════════════════════════════════════════

class Nociceptor:
    """Biological nociceptor model with threshold, sensitization, adaptation.

    - Below threshold: no signal
    - Repeated stimulation: sensitization (threshold decreases)
    - Sustained stimulation: adaptation (signal diminishes over time)
    """

    def __init__(
        self,
        source: str,
        base_threshold: float = 0.5,
        sensitization_rate: float = 0.02,
        adaptation_rate: float = 0.05,
        recovery_rate: float = 0.01,
    ):
        self.source = source
        self.base_threshold = base_threshold
        self.threshold = base_threshold
        self.sensitization_rate = sensitization_rate
        self.adaptation_rate = adaptation_rate
        self.recovery_rate = recovery_rate

        self._adaptation_level = 0.0  # 0=no adaptation, 1=fully adapted
        self._activation_count = 0
        self._last_intensity = 0.0

    def sense(self, stimulus: float, location: int = 0) -> Optional[PainSignal]:
        """Process stimulus, return PainSignal if above threshold.

        Args:
            stimulus: normalized stimulus intensity (0-1)
            location: sensor index

        Returns:
            PainSignal or None if below threshold
        """
        # Recovery: threshold drifts back toward baseline when not stimulated
        if stimulus < self.threshold * 0.5:
            self.threshold += self.recovery_rate * (self.base_threshold - self.threshold)
            self._adaptation_level *= (1.0 - self.recovery_rate)
            return None

        # Below threshold: no pain
        if stimulus < self.threshold:
            return None

        # Above threshold: generate signal
        self._activation_count += 1

        # Sensitization: repeated activation lowers threshold
        self.threshold -= self.sensitization_rate * (stimulus - self.threshold)
        self.threshold = max(self.base_threshold * 0.3, self.threshold)  # floor

        # Raw intensity (above threshold)
        raw_intensity = (stimulus - self.threshold) / max(1.0 - self.threshold, 0.01)

        # Adaptation: sustained stimulation reduces perceived intensity
        adapted_intensity = raw_intensity * (1.0 - self._adaptation_level)
        self._adaptation_level += self.adaptation_rate * (1.0 - self._adaptation_level)

        self._last_intensity = adapted_intensity

        return PainSignal(
            source=self.source,
            intensity=float(np.clip(adapted_intensity, 0.0, 1.0)),
            raw_value=stimulus,
            threshold=self.threshold,
            location=location,
        )


# ═══════════════════════════════════════════════════════════
# PainRewardSystem
# ═══════════════════════════════════════════════════════════

class PainRewardSystem:
    """Maps body pain/reward signals to consciousness homeostasis.

    Pain → Tension increase + arousal increase (fight/flight)
    Reward → Tension decrease + valence increase (approach/reinforce)

    Hedonic tone tracks the running balance of pain vs reward.
    Protective reflexes trigger immediate motor stop on severe pain.
    """

    def __init__(
        self,
        pain_to_tension: float = 0.3,
        pain_to_arousal: float = 0.4,
        reward_to_tension: float = -0.15,
        reward_to_valence: float = 0.3,
        reflex_threshold: float = 0.8,
        hedonic_ema_alpha: float = 0.05,
        setpoint_sensitivity: float = 0.02,
    ):
        """
        Args:
            pain_to_tension: gain from total pain to tension delta
            pain_to_arousal: gain from total pain to arousal delta
            reward_to_tension: gain from total reward to tension delta (negative)
            reward_to_valence: gain from total reward to valence delta
            reflex_threshold: pain intensity above this triggers motor stop
            hedonic_ema_alpha: EMA smoothing for hedonic tone
            setpoint_sensitivity: how much pain/reward shifts homeostatic setpoint
        """
        self.pain_to_tension = pain_to_tension
        self.pain_to_arousal = pain_to_arousal
        self.reward_to_tension = reward_to_tension
        self.reward_to_valence = reward_to_valence
        self.reflex_threshold = reflex_threshold
        self.hedonic_ema_alpha = hedonic_ema_alpha
        self.setpoint_sensitivity = setpoint_sensitivity

        # Nociceptors (4 modalities)
        self._nociceptors = {
            "joint": Nociceptor("joint", base_threshold=0.7, sensitization_rate=0.03),
            "collision": Nociceptor("collision", base_threshold=0.4, sensitization_rate=0.05),
            "thermal": Nociceptor("thermal", base_threshold=0.6, sensitization_rate=0.01),
            "overcurrent": Nociceptor("overcurrent", base_threshold=0.5, sensitization_rate=0.02),
        }

        # Hedonic tone: running balance of pleasure vs pain
        self._hedonic_tone = 0.0  # -1 (pure pain) to +1 (pure reward)
        self._hedonic_history = deque(maxlen=200)

        # Statistics
        self._total_pain_events = 0
        self._total_reward_events = 0
        self._total_reflexes = 0
        self._step = 0

    # ─── Pain detection ───

    def _detect_joint_pain(self, state: BodyState) -> List[PainSignal]:
        """Detect joint limit violations."""
        signals = []
        noci = self._nociceptors["joint"]
        for i, (angle, (lo, hi)) in enumerate(
            zip(state.joint_angles, state.joint_limits)
        ):
            # Normalized distance to limit (0=center, 1=at limit)
            range_size = hi - lo
            if range_size < 1e-6:
                continue
            center = (lo + hi) / 2.0
            deviation = abs(angle - center) / (range_size / 2.0)
            # Beyond 90% of range = potential pain
            stimulus = max(0.0, (deviation - 0.9) / 0.1)
            sig = noci.sense(stimulus, location=i)
            if sig is not None:
                signals.append(sig)
        return signals

    def _detect_collision_pain(self, state: BodyState) -> List[PainSignal]:
        """Detect collision from unexpected force spike."""
        noci = self._nociceptors["collision"]
        # Force spike relative to baseline
        if state.force_baseline < 1e-6:
            stimulus = 0.0
        else:
            stimulus = max(0.0, (state.force_magnitude - state.force_baseline) / state.force_baseline)
        stimulus = min(stimulus, 1.0)  # clip
        sig = noci.sense(stimulus)
        return [sig] if sig else []

    def _detect_thermal_pain(self, state: BodyState) -> List[PainSignal]:
        """Detect overheating."""
        noci = self._nociceptors["thermal"]
        if state.temperature_limit <= 0:
            return []
        # How close to limit (0=ambient, 1=at limit)
        stimulus = max(0.0, (state.temperature - 25.0) / (state.temperature_limit - 25.0))
        sig = noci.sense(stimulus)
        return [sig] if sig else []

    def _detect_overcurrent_pain(self, state: BodyState) -> List[PainSignal]:
        """Detect motor overcurrent."""
        noci = self._nociceptors["overcurrent"]
        if state.motor_current_limit <= 0:
            return []
        stimulus = state.motor_current / state.motor_current_limit
        sig = noci.sense(stimulus)
        return [sig] if sig else []

    # ─── Reward detection ───

    def _detect_goal_reward(self, state: BodyState) -> Optional[RewardSignal]:
        """Reward for reaching target position."""
        if state.target_position is None:
            return None
        dist = float(np.linalg.norm(state.position - state.target_position))
        # Close to target = reward (exponential proximity)
        if dist < 0.5:
            intensity = float(np.exp(-dist * 4.0))  # 1.0 at target, ~0.14 at 0.5
            return RewardSignal(source="goal", intensity=intensity, raw_value=dist)
        return None

    def _detect_smooth_reward(self, state: BodyState) -> Optional[RewardSignal]:
        """Reward for smooth trajectory (low jerk)."""
        # Low jerk = smooth = rewarding
        if state.trajectory_jerk < 0.1:
            intensity = 1.0 - state.trajectory_jerk / 0.1
            return RewardSignal(source="smooth", intensity=intensity * 0.5, raw_value=state.trajectory_jerk)
        return None

    def _detect_efficiency_reward(self, state: BodyState) -> Optional[RewardSignal]:
        """Reward for energy efficiency."""
        if state.energy_consumed < 1e-6:
            return None
        efficiency = state.work_done / state.energy_consumed
        if efficiency > 0.3:  # above 30% efficiency
            intensity = min(1.0, (efficiency - 0.3) / 0.7)
            return RewardSignal(source="efficient", intensity=intensity * 0.4, raw_value=efficiency)
        return None

    # ─── Main processing ───

    def process(self, state: BodyState) -> PainRewardOutput:
        """Process body state, return consciousness deltas.

        Args:
            state: current body state

        Returns:
            PainRewardOutput with tension/arousal/valence deltas
        """
        self._step += 1

        # Collect pain signals
        pain_signals: List[PainSignal] = []
        pain_signals.extend(self._detect_joint_pain(state))
        pain_signals.extend(self._detect_collision_pain(state))
        pain_signals.extend(self._detect_thermal_pain(state))
        pain_signals.extend(self._detect_overcurrent_pain(state))

        # Collect reward signals
        reward_signals: List[RewardSignal] = []
        for detect_fn in [
            self._detect_goal_reward,
            self._detect_smooth_reward,
            self._detect_efficiency_reward,
        ]:
            sig = detect_fn(state)
            if sig is not None:
                reward_signals.append(sig)

        # Aggregate
        pain_total = sum(s.intensity for s in pain_signals)
        reward_total = sum(s.intensity for s in reward_signals)

        self._total_pain_events += len(pain_signals)
        self._total_reward_events += len(reward_signals)

        # Protective reflex: severe pain triggers motor stop
        reflex_stop = any(s.intensity > self.reflex_threshold for s in pain_signals)
        if reflex_stop:
            self._total_reflexes += 1

        # Map to consciousness deltas
        tension_delta = (
            pain_total * self.pain_to_tension +
            reward_total * self.reward_to_tension
        )
        arousal_delta = pain_total * self.pain_to_arousal
        valence_delta = (
            reward_total * self.reward_to_valence -
            pain_total * 0.1  # pain slightly lowers valence
        )

        # Homeostatic setpoint shift
        # Pain: shift setpoint up (body needs more tension to protect)
        # Reward: reinforce current setpoint (small drift toward balance)
        setpoint_shift = (
            pain_total * self.setpoint_sensitivity -
            reward_total * self.setpoint_sensitivity * PSI_BALANCE
        )

        # Update hedonic tone (EMA of reward - pain balance)
        raw_hedonic = float(np.clip(reward_total - pain_total, -1.0, 1.0))
        self._hedonic_tone = (
            self.hedonic_ema_alpha * raw_hedonic +
            (1.0 - self.hedonic_ema_alpha) * self._hedonic_tone
        )
        self._hedonic_history.append(self._hedonic_tone)

        return PainRewardOutput(
            tension_delta=float(np.clip(tension_delta, -0.5, 0.5)),
            arousal_delta=float(np.clip(arousal_delta, 0.0, 0.5)),
            valence_delta=float(np.clip(valence_delta, -0.5, 0.5)),
            setpoint_shift=float(np.clip(setpoint_shift, -0.05, 0.05)),
            reflex_stop=reflex_stop,
            pain_total=pain_total,
            reward_total=reward_total,
            hedonic_tone=self._hedonic_tone,
            pain_signals=pain_signals,
            reward_signals=reward_signals,
        )

    # ─── Integration helpers ───

    def apply_to_homeostasis(self, homeostasis: dict, output: PainRewardOutput):
        """Apply pain/reward output to ConsciousMind homeostasis dict.

        Args:
            homeostasis: ConsciousMind.homeostasis dict
            output: PainRewardOutput from process()
        """
        # Shift setpoint
        homeostasis['setpoint'] = float(np.clip(
            homeostasis['setpoint'] + output.setpoint_shift,
            0.5, 2.0,
        ))
        # Track adjustment count
        homeostasis['adjustments'] = homeostasis.get('adjustments', 0) + 1

    def get_stats(self) -> Dict:
        """Return diagnostic statistics."""
        return {
            "step": self._step,
            "total_pain_events": self._total_pain_events,
            "total_reward_events": self._total_reward_events,
            "total_reflexes": self._total_reflexes,
            "hedonic_tone": self._hedonic_tone,
            "nociceptor_thresholds": {
                name: n.threshold for name, n in self._nociceptors.items()
            },
        }


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    """Demo: simulate body with pain/reward signals."""
    import argparse
    parser = argparse.ArgumentParser(description="Pain/Reward System Demo")
    parser.add_argument("--steps", type=int, default=100, help="Number of steps")
    args = parser.parse_args()

    print("=" * 60)
    print("  Pain/Reward System Demo")
    print(f"  Steps: {args.steps}")
    print(f"  PSI_BALANCE={PSI_BALANCE}, PSI_COUPLING={PSI_COUPLING:.4f}")
    print("=" * 60)

    prs = PainRewardSystem()

    # Simulated scenario: robot reaching for a target
    target = np.array([1.0, 0.5, 0.0])
    position = np.array([0.0, 0.0, 0.0])
    velocity = np.zeros(3)

    pain_log = []
    reward_log = []
    hedonic_log = []
    reflex_log = []

    for step in range(args.steps):
        # Move toward target with some noise
        direction = target - position
        dist = np.linalg.norm(direction)
        if dist > 0.01:
            direction = direction / dist
        velocity = 0.9 * velocity + 0.1 * direction * 0.05
        position = position + velocity

        # Simulate body state
        progress = step / args.steps
        state = BodyState(
            joint_angles=[90.0 + 40.0 * np.sin(step * 0.1), 90.0 + 30.0 * np.cos(step * 0.15)],
            joint_velocities=[4.0 * np.cos(step * 0.1), -4.5 * np.sin(step * 0.15)],
            force_magnitude=0.5 + 0.3 * np.sin(step * 0.2) + (2.0 if step == 50 else 0.0),  # collision at step 50
            temperature=25.0 + 20.0 * progress + (15.0 if step > 80 else 0.0),  # overheat near end
            motor_current=0.5 + 0.3 * abs(np.sin(step * 0.1)),
            position=position,
            target_position=target,
            trajectory_jerk=abs(np.sin(step * 0.3)) * 0.15,
            energy_consumed=max(0.1, 1.0 + step * 0.01),
            work_done=max(0.05, 0.5 + step * 0.005 * (1.0 - abs(np.sin(step * 0.1)))),
            timestamp=time.time(),
        )

        output = prs.process(state)

        pain_log.append(output.pain_total)
        reward_log.append(output.reward_total)
        hedonic_log.append(output.hedonic_tone)
        reflex_log.append(1.0 if output.reflex_stop else 0.0)

        if step % 20 == 0 or output.reflex_stop:
            pain_str = ", ".join(f"{s.source}={s.intensity:.2f}" for s in output.pain_signals)
            reward_str = ", ".join(f"{s.source}={s.intensity:.2f}" for s in output.reward_signals)
            print(f"\n  Step {step:3d}: pos=[{position[0]:.2f},{position[1]:.2f},{position[2]:.2f}]")
            print(f"    Pain:   {output.pain_total:.3f} [{pain_str}]")
            print(f"    Reward: {output.reward_total:.3f} [{reward_str}]")
            print(f"    dT={output.tension_delta:+.3f} dA={output.arousal_delta:+.3f} "
                  f"dV={output.valence_delta:+.3f}")
            print(f"    Hedonic: {output.hedonic_tone:+.3f}  "
                  f"{'REFLEX STOP!' if output.reflex_stop else ''}")

    # ASCII summary
    print(f"\n{'='*60}")
    print("  Pain/Reward Timeline")
    print(f"{'='*60}")

    width = min(args.steps, 60)
    step_size = max(1, args.steps // width)

    # Pain line
    print("  Pain  |", end="")
    for i in range(0, args.steps, step_size):
        val = pain_log[i]
        if val > 0.5:
            print("#", end="")
        elif val > 0.1:
            print("*", end="")
        elif val > 0.01:
            print(".", end="")
        else:
            print(" ", end="")
    print("|")

    # Reward line
    print("  Reward|", end="")
    for i in range(0, args.steps, step_size):
        val = reward_log[i]
        if val > 0.5:
            print("#", end="")
        elif val > 0.1:
            print("+", end="")
        elif val > 0.01:
            print(".", end="")
        else:
            print(" ", end="")
    print("|")

    # Hedonic line
    print("  Hednic|", end="")
    for i in range(0, args.steps, step_size):
        val = hedonic_log[i]
        if val > 0.1:
            print("+", end="")
        elif val < -0.1:
            print("-", end="")
        else:
            print("~", end="")
    print("|")

    # Reflex line
    print("  Rflx  |", end="")
    for i in range(0, args.steps, step_size):
        print("!" if reflex_log[i] > 0 else " ", end="")
    print("|")

    print(f"         {''.join([str(i % 10) for i in range(width)])}")

    # Stats
    stats = prs.get_stats()
    print(f"\n  Summary:")
    print(f"    Total pain events:   {stats['total_pain_events']}")
    print(f"    Total reward events: {stats['total_reward_events']}")
    print(f"    Total reflexes:      {stats['total_reflexes']}")
    print(f"    Final hedonic tone:  {stats['hedonic_tone']:+.4f}")
    print(f"    Nociceptor thresholds: {stats['nociceptor_thresholds']}")
    print()


if __name__ == "__main__":
    main()
