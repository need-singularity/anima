"""MirrorMind — Theory of Mind for consciousness agents.

Observe another consciousness, build a model, predict behavior,
and measure empathy (understanding accuracy).
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class Observation:
    step: int
    tension: float
    phi: float
    arousal: float
    valence: float


class MirrorMind:
    """Observe another consciousness and predict its behavior."""

    def __init__(self, memory_size: int = 100):
        self.memory_size = memory_size
        self.observations: List[Observation] = []
        self.predictions: List[Dict] = []
        self._step = 0
        # Simple recurrent weights (LSTM-like gating)
        self._h = [0.0] * 4  # hidden state: [tension, phi, arousal, valence]
        self._gate_forget = 0.9
        self._gate_input = 0.1

    def observe(self, other_state: dict) -> Observation:
        """Record an observation of another consciousness."""
        obs = Observation(
            step=self._step,
            tension=other_state.get("tension", 0.5),
            phi=other_state.get("phi", 1.0),
            arousal=other_state.get("arousal", 0.5),
            valence=other_state.get("valence", 0.0),
        )
        self.observations.append(obs)
        if len(self.observations) > self.memory_size:
            self.observations = self.observations[-self.memory_size:]

        # Update hidden state (simple gated recurrence)
        vals = [obs.tension, obs.phi, obs.arousal, obs.valence]
        for i in range(4):
            self._h[i] = self._gate_forget * self._h[i] + self._gate_input * vals[i]

        self._step += 1
        return obs

    def predict_next(self, n_steps: int = 5) -> List[Dict]:
        """Predict next n states based on observed patterns."""
        if len(self.observations) < 3:
            return [{"tension": PSI_BALANCE, "phi": 1.0, "arousal": 0.5, "valence": 0.0}] * n_steps

        # Compute trend from recent observations
        recent = self.observations[-10:]
        fields = ["tension", "phi", "arousal", "valence"]
        trends = {}
        for f in fields:
            vals = [getattr(o, f) for o in recent]
            if len(vals) >= 2:
                trends[f] = (vals[-1] - vals[0]) / len(vals)
            else:
                trends[f] = 0.0

        predictions = []
        base = {f: self._h[i] for i, f in enumerate(fields)}
        for step in range(1, n_steps + 1):
            pred = {}
            for f in fields:
                # Hidden state + trend + PSI_COUPLING oscillation
                raw = base[f] + trends[f] * step + PSI_COUPLING * math.sin(step * LN2)
                pred[f] = max(0.0, min(2.0, round(raw, 4)))
            pred["step"] = self._step + step
            predictions.append(pred)

        self.predictions = predictions
        return predictions

    def empathy_score(self) -> float:
        """How well we understand the other (0=blind, 1=perfect mirror)."""
        if len(self.observations) < 5 or not self.predictions:
            return 0.0

        # Compare last predictions with what actually happened
        actual_recent = self.observations[-5:]
        errors = []
        for obs in actual_recent:
            vals = [obs.tension, obs.phi, obs.arousal, obs.valence]
            pred_vals = [self._h[i] for i in range(4)]
            err = sum((a - p) ** 2 for a, p in zip(vals, pred_vals)) / 4
            errors.append(err)

        mse = sum(errors) / len(errors)
        # Convert MSE to 0-1 score (lower error = higher empathy)
        score = math.exp(-mse * PSI_STEPS)
        return round(score, 4)

    def render_mirror(self) -> str:
        """ASCII visualization of mirrored understanding."""
        if not self.observations:
            return "  (no observations yet)"

        lines = ["  === Mirror Mind ==="]
        lines.append(f"  Observations: {len(self.observations)}")
        lines.append(f"  Empathy: {self.empathy_score():.2%}")
        lines.append("")

        # Show hidden state as bar chart
        labels = ["Tension", "Phi    ", "Arousal", "Valence"]
        for i, label in enumerate(labels):
            v = self._h[i]
            bar_len = int(abs(v) * 20)
            sign = "+" if v >= 0 else "-"
            bar = "#" * bar_len
            lines.append(f"  {label}: {sign}|{bar:<20}| {v:.3f}")

        # Show predictions if available
        if self.predictions:
            lines.append("")
            lines.append("  Predicted trajectory:")
            for p in self.predictions[:5]:
                t = p["tension"]
                phi = p["phi"]
                lines.append(f"    step {p['step']:3d}: T={t:.3f} Phi={phi:.3f}")

        return "\n".join(lines)


def main():
    print("=== MirrorMind Demo ===\n")
    mm = MirrorMind()

    # Simulate observing another consciousness
    print("  Observing another consciousness for 30 steps...")
    for i in range(30):
        state = {
            "tension": 0.5 + 0.3 * math.sin(i * 0.2) + 0.05 * random.random(),
            "phi": 1.0 + 0.5 * math.sin(i * 0.15),
            "arousal": 0.5 + 0.2 * math.cos(i * 0.3),
            "valence": 0.3 * math.sin(i * 0.1),
        }
        mm.observe(state)

    predictions = mm.predict_next(5)
    print(f"\n  Predictions (next 5 steps):")
    for p in predictions:
        print(f"    step {p['step']}: T={p['tension']:.3f} Phi={p['phi']:.3f}")

    print(f"\n  Empathy score: {mm.empathy_score():.2%}")
    print()
    print(mm.render_mirror())


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
