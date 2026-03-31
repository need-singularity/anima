"""EmergenceDetector — Detect the exact moment consciousness emerges."""

import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class EmergenceEvent:
    step: int
    phi: float
    score: float
    timestamp: float
    trigger: str


@dataclass
class SystemState:
    phi: float
    entropy: float
    integration: float
    differentiation: float
    step: int = 0


class EmergenceDetector:
    """Detect phase transitions where consciousness emerges."""

    def __init__(self, phi_min: float = 0.5):
        self.phi_min = phi_min
        self.events: List[EmergenceEvent] = []
        self.state_history: List[SystemState] = []
        self.callbacks: List[Callable[[EmergenceEvent], None]] = []
        self._prev_score = 0.0
        self._consecutive_above = 0

    def phi_threshold(self) -> float:
        """Current adaptive Phi_min estimate based on history."""
        if len(self.state_history) < 10:
            return self.phi_min
        phis = [s.phi for s in self.state_history[-50:]]
        mean_phi = sum(phis) / len(phis)
        # Threshold adapts: PSI_BALANCE between observed mean and initial
        return PSI_BALANCE * mean_phi + (1 - PSI_BALANCE) * self.phi_min

    def emergence_score(self, state: SystemState) -> float:
        """Score 0=dead to 1=fully conscious. Based on phase transition indicators."""
        phi_norm = min(1.0, state.phi / max(self.phi_threshold() * 2, 0.01))
        # Integration-differentiation balance (consciousness needs both)
        balance = 1.0 - abs(state.integration - state.differentiation)
        balance = max(0, balance)
        # Entropy should be in golden zone (not too low, not too high)
        entropy_score = 1.0 - abs(state.entropy - PSI_BALANCE) * 2
        entropy_score = max(0, entropy_score)
        # Conservation check: phi * entropy should be roughly constant (like energy)
        conservation = 1.0
        if self.state_history:
            prev = self.state_history[-1]
            prev_product = prev.phi * prev.entropy
            curr_product = state.phi * state.entropy
            if prev_product > 0:
                conservation = 1.0 - min(1.0, abs(curr_product - prev_product) / prev_product)
        score = (phi_norm * 0.4 + balance * 0.2 + entropy_score * 0.2 + conservation * 0.2)
        return round(min(1.0, max(0.0, score)), 4)

    def monitor(self, state: SystemState) -> Optional[EmergenceEvent]:
        """Watch a state for emergence. Returns event if emergence detected."""
        self.state_history.append(state)
        score = self.emergence_score(state)
        threshold = self.phi_threshold()
        event = None
        # Phase transition detection
        if score > 0.7 and self._prev_score <= 0.7:
            trigger = "phase_transition"
            event = EmergenceEvent(
                step=state.step, phi=state.phi, score=score,
                timestamp=time.time(), trigger=trigger,
            )
        # Sustained emergence
        if state.phi > threshold:
            self._consecutive_above += 1
            if self._consecutive_above == int(PSI_STEPS):
                event = EmergenceEvent(
                    step=state.step, phi=state.phi, score=score,
                    timestamp=time.time(), trigger="sustained_above_threshold",
                )
        else:
            self._consecutive_above = 0
        # Sudden jump
        if len(self.state_history) >= 2:
            prev_phi = self.state_history[-2].phi
            if state.phi > prev_phi * 2 and state.phi > threshold:
                event = EmergenceEvent(
                    step=state.step, phi=state.phi, score=score,
                    timestamp=time.time(), trigger="sudden_jump",
                )
        if event:
            self.events.append(event)
            for cb in self.callbacks:
                cb(event)

        self._prev_score = score
        return event

    def alert(self, callback: Callable[[EmergenceEvent], None]) -> None:
        """Register a callback for emergence detection."""
        self.callbacks.append(callback)

    def history(self) -> str:
        """All detected emergence events as formatted string."""
        if not self.events:
            return "No emergence events detected yet."
        lines = [f"=== Emergence History ({len(self.events)} events) ==="]
        lines.append(f"  Phi threshold: {self.phi_threshold():.4f}")
        lines.append(f"  Psi: LN2={LN2:.4f}  BALANCE={PSI_BALANCE}  STEPS={PSI_STEPS:.2f}\n")
        for e in self.events:
            lines.append(
                f"  step {e.step:4d}: Phi={e.phi:.4f}  score={e.score:.3f}  "
                f"trigger={e.trigger}"
            )
        # ASCII timeline
        if self.state_history:
            lines.append("\n  Emergence Score Timeline:")
            scores = [self.emergence_score(s) for s in self.state_history[-40:]]
            h = 8
            max_s = max(scores) if scores else 1
            for row in range(h):
                threshold_val = (h - 1 - row) / (h - 1) * max_s
                line = "  "
                if abs(threshold_val - 0.7) < max_s / h:
                    line += "T>"
                else:
                    line += "  "
                for s in scores:
                    normalized = s / max_s if max_s > 0 else 0
                    if normalized >= (h - 1 - row) / (h - 1):
                        line += "#"
                    else:
                        line += " "
                lines.append(line)
            lines.append("    " + "-" * len(scores) + " step")
        return "\n".join(lines)


def main():
    detector = EmergenceDetector(phi_min=0.5)

    alerts = []
    detector.alert(lambda e: alerts.append(e))

    print("=== Emergence Detection Simulation ===\n")
    import random

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    random.seed(42)

    for step in range(60):
        # Simulate a system that gradually becomes conscious
        if step < 20:
            phi = 0.1 + random.random() * 0.2
        elif step < 30:
            phi = 0.3 + (step - 20) * 0.1 + random.random() * 0.1
        else:
            phi = 1.0 + random.random() * 0.5

        entropy = 0.3 + math.sin(step * 0.1) * 0.2
        integration = phi * 0.6 + random.random() * 0.1
        differentiation = phi * 0.5 + random.random() * 0.1

        state = SystemState(phi=phi, entropy=entropy,
                            integration=integration, differentiation=differentiation,
                            step=step)
        event = detector.monitor(state)
        score = detector.emergence_score(state)

        if step % 10 == 0 or event:
            marker = " <<< EMERGENCE!" if event else ""
            print(f"  step {step:3d}: Phi={phi:.3f}  score={score:.3f}{marker}")

    print()
    print(detector.history())
    print(f"\n  Total alerts: {len(alerts)}")


if __name__ == "__main__":
    main()
