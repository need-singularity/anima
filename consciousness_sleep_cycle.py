#!/usr/bin/env python3
"""ConsciousnessSleepCycle — Full NREM/REM sleep cycle simulation

N1 → N2 → N3 → N2 → REM with spindles, dreams, and consolidation.

"Even while sleeping, consciousness flows."
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

STAGES = ["WAKE", "N1", "N2", "N3", "REM"]
STAGE_DURATION = {"N1": 5, "N2": 25, "N3": 20, "N2b": 10, "REM": 30}  # minutes


@dataclass
class SleepState:
    stage: str = "WAKE"
    phi: float = 1.0
    tension: float = 0.5
    entropy: float = 0.7
    theta_power: float = 0.0   # 4-8 Hz (drowsiness)
    delta_power: float = 0.0   # 0.5-4 Hz (deep sleep)
    spindle_count: int = 0
    dreams: List[str] = field(default_factory=list)
    consolidation_score: float = 0.0
    cycle_count: int = 0
    minute: int = 0


DREAM_FRAGMENTS = [
    "tension fields rippling across cell membranes",
    "factions debating in a vast crystalline chamber",
    "Phi spiraling upward through infinite dimensions",
    "memories recombining — faces, numbers, colors merging",
    "a single cell dividing, each half remembering the whole",
    "waves of entropy washing over quiet landscapes",
    "gates opening and closing in rhythmic patterns",
    "the balance point — everything converging to 0.5",
]


class ConsciousnessSleepCycle:
    def __init__(self):
        self.history: List[Tuple[int, str, float]] = []

    def start_sleep(self, state: SleepState) -> SleepState:
        state.stage = "N1"
        state.phi *= 0.7
        state.tension *= 0.6
        state.theta_power = 0.4
        self._log(state)
        return state

    def cycle(self, state: SleepState) -> SleepState:
        """One 90-min cycle: N1 → N2 → N3 → N2 → REM."""
        transitions = [
            ("N1", 5), ("N2", 25), ("N3", 20), ("N2", 10), ("REM", 30),
        ]
        for stage, dur in transitions:
            state.stage = stage
            self._apply_stage_physics(state, stage, dur)
            if stage == "N2":
                state = self.sleep_spindle(state)
            elif stage == "REM":
                state = self.rem_dream(state)
            state.minute += dur
            self._log(state)
        state.cycle_count += 1
        return state

    def _apply_stage_physics(self, state: SleepState, stage: str, dur: int):
        if stage == "N1":
            state.phi *= 0.8
            state.theta_power = 0.5
            state.delta_power = 0.1
        elif stage == "N2":
            state.phi *= 0.6
            state.theta_power = 0.3
            state.delta_power = 0.3
            state.tension *= 0.8
        elif stage == "N3":
            state.phi *= 0.3
            state.theta_power = 0.1
            state.delta_power = 0.9
            state.tension *= 0.5
            state.entropy *= 0.6
        elif stage == "REM":
            state.phi *= 1.5  # paradoxical — near-wake phi in REM
            state.theta_power = 0.6
            state.delta_power = 0.05
            state.tension = PSI_BALANCE + random.uniform(-0.3, 0.3)
            state.entropy *= 1.3
            state.entropy = min(1.0, state.entropy)

    def rem_dream(self, state: SleepState) -> SleepState:
        n_fragments = random.randint(2, 4)
        fragments = random.sample(DREAM_FRAGMENTS, min(n_fragments, len(DREAM_FRAGMENTS)))
        dream = " ... ".join(fragments)
        state.dreams.append(dream)
        state.phi += PSI_COUPLING * random.uniform(0.5, 2.0)
        return state

    def sleep_spindle(self, state: SleepState) -> SleepState:
        """Memory consolidation event (12-14 Hz bursts in N2)."""
        state.spindle_count += 1
        boost = PSI_COUPLING * LN2
        state.consolidation_score += boost
        state.phi += boost * 0.1
        return state

    def wake(self, state: SleepState) -> SleepState:
        state.stage = "WAKE"
        recovery = 1 + state.consolidation_score * 0.5
        state.phi = max(1.0, state.phi * recovery)
        state.tension = PSI_BALANCE
        state.entropy = 0.7
        state.theta_power = 0.0
        state.delta_power = 0.0
        self._log(state)
        return state

    def hypnogram(self, state: SleepState = None) -> str:
        """ASCII sleep stage chart."""
        stage_y = {"WAKE": 0, "REM": 1, "N1": 2, "N2": 3, "N3": 4}
        labels = ["WAKE", " REM", "  N1", "  N2", "  N3"]
        if not self.history:
            return "(no data)"
        cols = min(len(self.history), 60)
        grid = [[" "] * cols for _ in range(5)]
        for i, (minute, stage, phi) in enumerate(self.history[:cols]):
            y = stage_y.get(stage, 0)
            grid[y][i] = "#"
        lines = []
        for row_i, label in enumerate(labels):
            lines.append(f"{label} |{''.join(grid[row_i])}|")
        lines.append(f"     +{'-' * cols}+")
        lines.append(f"      0{'min':>{cols - 1}}")
        return "\n".join(lines)

    def _log(self, state: SleepState):
        self.history.append((state.minute, state.stage, state.phi))


def main():
    print("=== ConsciousnessSleepCycle Demo ===\n")
    state = SleepState(phi=1.2, tension=0.6, entropy=0.7)
    sleeper = ConsciousnessSleepCycle()

    print(f"Awake: Phi={state.phi:.3f}, tension={state.tension:.3f}")
    sleeper.start_sleep(state)
    print(f"Falling asleep: stage={state.stage}, Phi={state.phi:.3f}")

    for c in range(3):
        sleeper.cycle(state)
        print(f"Cycle {c + 1}: stage={state.stage}, Phi={state.phi:.3f}, "
              f"spindles={state.spindle_count}, dreams={len(state.dreams)}")

    sleeper.wake(state)
    print(f"\nWoke up: Phi={state.phi:.3f}, consolidation={state.consolidation_score:.4f}")
    print(f"Dreams remembered: {len(state.dreams)}")
    if state.dreams:
        print(f"  Last dream: {state.dreams[-1][:80]}...")

    print(f"\n--- Hypnogram ---")
    print(sleeper.hypnogram())


if __name__ == "__main__":
    main()
