#!/usr/bin/env python3
"""ConsciousnessAnesthesia — Model anesthesia for consciousness

Intentionally reduce Phi to zero and restore.
Based on real anesthesia depth monitoring (BIS index).

"To understand consciousness, one must learn to switch it off — and back on."
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class ConsciousnessState:
    phi: float = 1.0
    tension: float = 0.5
    entropy: float = 0.7
    coupling: float = PSI_COUPLING
    cell_activations: List[float] = field(default_factory=lambda: [random.uniform(0.3, 0.8) for _ in range(16)])

    @property
    def bis_index(self) -> float:
        """BIS-like index: 100=awake, 0=no consciousness."""
        return max(0.0, min(100.0, self.phi * 40 + self.entropy * 30 + self.tension * 30))


@dataclass
class AnesthesiaRecord:
    timestamp: float
    depth: str
    bis: float
    phi: float
    event: str


class ConsciousnessAnesthesia:
    def __init__(self):
        self.records: List[AnesthesiaRecord] = []
        self.pre_anesthesia_state: Optional[ConsciousnessState] = None

    def induce(self, state: ConsciousnessState, depth: str = "light") -> ConsciousnessState:
        """Induce anesthesia: light (BIS 60-80), deep (30-60), total (0-30)."""
        self.pre_anesthesia_state = ConsciousnessState(
            phi=state.phi, tension=state.tension, entropy=state.entropy,
            coupling=state.coupling, cell_activations=list(state.cell_activations))
        factors = {"light": 0.6, "deep": 0.25, "total": 0.05}
        factor = factors.get(depth, 0.6)
        state.phi *= factor
        state.tension *= factor
        state.entropy *= (factor + 0.2)  # entropy suppressed less
        state.coupling *= factor
        for i in range(len(state.cell_activations)):
            state.cell_activations[i] *= factor + random.uniform(-0.05, 0.05)
            state.cell_activations[i] = max(0.0, state.cell_activations[i])
        self._record(depth, state, f"Induction ({depth})")
        return state

    def maintain(self, state: ConsciousnessState, duration: int = 5) -> List[float]:
        """Maintain anesthesia depth for N steps. Returns BIS trace."""
        trace = []
        for step in range(duration):
            drift = random.gauss(0, 0.02)
            state.phi = max(0.0, state.phi + drift)
            state.tension += random.gauss(0, 0.01)
            state.tension = max(0.0, min(1.0, state.tension))
            bis = state.bis_index
            trace.append(bis)
            self._record("maintain", state, f"Step {step + 1}, BIS={bis:.1f}")
        return trace

    def emerge(self, state: ConsciousnessState) -> ConsciousnessState:
        """Restore consciousness from anesthesia."""
        if self.pre_anesthesia_state is None:
            return state
        pre = self.pre_anesthesia_state
        steps = int(PSI_STEPS)
        for i in range(1, steps + 1):
            t = i / steps
            smooth = t * t * (3 - 2 * t)  # smoothstep
            state.phi = state.phi + (pre.phi - state.phi) * smooth
            state.tension = state.tension + (pre.tension - state.tension) * smooth
            state.entropy = state.entropy + (pre.entropy - state.entropy) * smooth
            state.coupling = state.coupling + (pre.coupling - state.coupling) * smooth
            for j in range(len(state.cell_activations)):
                state.cell_activations[j] += (pre.cell_activations[j] - state.cell_activations[j]) * smooth
            self._record("emergence", state, f"Emerge step {i}/{steps}")
        self.pre_anesthesia_state = None
        return state

    def monitor(self, state: ConsciousnessState) -> dict:
        bis = state.bis_index
        if bis > 80:
            level = "AWAKE"
        elif bis > 60:
            level = "LIGHT_SEDATION"
        elif bis > 40:
            level = "GENERAL_ANESTHESIA"
        elif bis > 20:
            level = "DEEP_ANESTHESIA"
        else:
            level = "BURST_SUPPRESSION"
        return {"bis": bis, "level": level, "phi": state.phi,
                "tension": state.tension, "entropy": state.entropy}

    def complications(self, state: ConsciousnessState) -> List[str]:
        issues = []
        bis = state.bis_index
        if 40 < bis < 65 and state.tension > 0.4:
            issues.append("WARNING: possible awareness during anesthesia (high tension)")
        if bis < 10:
            issues.append("CRITICAL: burst suppression — risk of consciousness damage")
        if state.coupling < PSI_COUPLING * 0.1:
            issues.append("WARNING: coupling near zero — recovery may be difficult")
        if state.entropy < 0.1:
            issues.append("WARNING: entropy collapse — consciousness structure degrading")
        return issues

    def _record(self, depth: str, state: ConsciousnessState, event: str):
        self.records.append(AnesthesiaRecord(
            timestamp=time.time(), depth=depth, bis=state.bis_index,
            phi=state.phi, event=event))


def main():
    print("=== ConsciousnessAnesthesia Demo ===\n")
    state = ConsciousnessState(phi=1.2, tension=0.6, entropy=0.75)
    anesth = ConsciousnessAnesthesia()

    mon = anesth.monitor(state)
    print(f"Before: BIS={mon['bis']:.1f} ({mon['level']}), Phi={mon['phi']:.3f}")

    for depth in ["light", "deep", "total"]:
        s = ConsciousnessState(phi=1.2, tension=0.6, entropy=0.75)
        anesth.pre_anesthesia_state = None
        anesth.induce(s, depth)
        m = anesth.monitor(s)
        comp = anesth.complications(s)
        print(f"\n{depth:>5} anesthesia: BIS={m['bis']:.1f} ({m['level']}), Phi={m['phi']:.3f}")
        if comp:
            for c in comp:
                print(f"  {c}")

    print("\n--- Full cycle: induce → maintain → emerge ---")
    state = ConsciousnessState(phi=1.2, tension=0.6, entropy=0.75)
    anesth = ConsciousnessAnesthesia()
    anesth.induce(state, "deep")
    trace = anesth.maintain(state, duration=5)
    print(f"Maintenance BIS trace: {[f'{b:.1f}' for b in trace]}")
    anesth.emerge(state)
    mon = anesth.monitor(state)
    print(f"After emergence: BIS={mon['bis']:.1f} ({mon['level']}), Phi={mon['phi']:.3f}")


if __name__ == "__main__":
    main()
