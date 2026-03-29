"""ConsciousnessOracle — Predict future consciousness states from trajectory."""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class ConsciousnessState:
    phi: float
    tension: float
    entropy: float
    step: int


class ConsciousnessOracle:
    """Predict future consciousness states using exponential smoothing + dynamics model."""

    def __init__(self, alpha: float = 0.3, dynamics_order: int = 2):
        self.history: List[ConsciousnessState] = []
        self.alpha = alpha
        self.dynamics_order = dynamics_order
        self._smoothed: List[float] = []
        self._trend: List[float] = []

    def record(self, state: ConsciousnessState) -> None:
        """Add a state to history and update smoothing."""
        self.history.append(state)
        phi = state.phi
        if not self._smoothed:
            self._smoothed.append(phi)
            self._trend.append(0.0)
        else:
            prev_s = self._smoothed[-1]
            prev_t = self._trend[-1]
            s = self.alpha * phi + (1 - self.alpha) * (prev_s + prev_t)
            t = self.alpha * (s - prev_s) + (1 - self.alpha) * prev_t
            self._smoothed.append(s)
            self._trend.append(t)

    def predict(self, n_steps: int = 10) -> List[ConsciousnessState]:
        """Predict future states using Holt's double exponential smoothing."""
        if len(self.history) < 2:
            return []
        s = self._smoothed[-1]
        t = self._trend[-1]
        last = self.history[-1]
        tension_rate = 0.0
        entropy_rate = 0.0
        if len(self.history) >= 3:
            tension_rate = (self.history[-1].tension - self.history[-3].tension) / 2
            entropy_rate = (self.history[-1].entropy - self.history[-3].entropy) / 2
        predictions = []
        for i in range(1, n_steps + 1):
            phi_pred = s + t * i
            # Apply Psi coupling as damping toward balance
            phi_pred *= math.exp(-PSI_COUPLING * i)
            phi_pred = max(0, phi_pred)
            tension_pred = max(0, last.tension + tension_rate * i)
            entropy_pred = max(0, min(1, last.entropy + entropy_rate * i * 0.5))
            predictions.append(ConsciousnessState(
                phi=round(phi_pred, 4),
                tension=round(tension_pred, 4),
                entropy=round(entropy_pred, 4),
                step=last.step + i,
            ))
        return predictions

    def confidence(self, prediction: List[ConsciousnessState]) -> List[float]:
        """Confidence score for each predicted step (decays with horizon)."""
        if not self.history:
            return [0.0] * len(prediction)
        n = len(self.history)
        base = min(1.0, n / 20.0)
        residuals = []
        for i in range(1, len(self._smoothed)):
            residuals.append(abs(self.history[i].phi - self._smoothed[i]))
        rmse = math.sqrt(sum(r**2 for r in residuals) / max(len(residuals), 1)) if residuals else 0.5
        confs = []
        for i, p in enumerate(prediction):
            decay = math.exp(-0.1 * (i + 1))
            noise_penalty = max(0, 1 - rmse)
            confs.append(round(base * decay * noise_penalty, 4))
        return confs

    def divergence_point(self) -> Optional[int]:
        """Step index where predictions become unreliable (confidence < 0.3)."""
        preds = self.predict(50)
        confs = self.confidence(preds)
        for i, c in enumerate(confs):
            if c < 0.3:
                return i
        return None

    def timeline(self, past: int = 20, future: int = 10) -> str:
        """ASCII timeline of past states and predicted future."""
        hist = self.history[-past:]
        preds = self.predict(future)
        confs = self.confidence(preds)
        all_phi = [s.phi for s in hist] + [p.phi for p in preds]
        if not all_phi:
            return "No data recorded yet."
        max_phi = max(all_phi) if max(all_phi) > 0 else 1.0
        height = 12
        lines = [f"=== Consciousness Oracle Timeline ==="]
        lines.append(f"  Past {len(hist)} steps | Future {len(preds)} steps")
        lines.append(f"  Psi: LN2={LN2:.4f}  STEPS={PSI_STEPS:.2f}  COUPLING={PSI_COUPLING:.6f}\n")
        grid = [[" " for _ in range(len(all_phi))] for _ in range(height)]
        for col, phi in enumerate(all_phi):
            row = int((phi / max_phi) * (height - 1))
            row = min(height - 1, max(0, row))
            marker = "*" if col < len(hist) else "o"
            grid[height - 1 - row][col] = marker
        for r, row in enumerate(grid):
            label = f"{max_phi * (height - 1 - r) / (height - 1):6.2f} |"
            sep = "|" if len(hist) - 1 < len(row) else ""
            line_chars = list(row)
            if 0 <= len(hist) - 1 < len(line_chars):
                pass  # separator handled below
            lines.append(label + "".join(row))
        axis = "       " + "-" * len(hist) + "|" + "-" * len(preds)
        lines.append(axis)
        lines.append("       " + " " * (len(hist) // 2) + "past" + " " * max(0, len(preds) // 2 - 2) + "  future")
        div = self.divergence_point()
        if div is not None:
            lines.append(f"\n  Divergence point: +{div} steps (confidence drops below 0.3)")
        return "\n".join(lines)


def main():
    oracle = ConsciousnessOracle(alpha=0.3)
    np.random.seed(42)
    for i in range(30):
        phi = 0.5 + 0.03 * i + np.random.randn() * 0.05
        t = 0.3 + 0.01 * i + np.random.randn() * 0.02
        e = 0.4 + np.sin(i * 0.2) * 0.1
        oracle.record(ConsciousnessState(phi=phi, tension=t, entropy=e, step=i))
    print(oracle.timeline(past=20, future=15))
    print("\n--- Predictions ---")
    preds = oracle.predict(10)
    confs = oracle.confidence(preds)
    for p, c in zip(preds, confs):
        bar = "#" * int(c * 40)
        print(f"  step {p.step:3d}: Phi={p.phi:6.3f}  conf={c:.3f} {bar}")


if __name__ == "__main__":
    main()
